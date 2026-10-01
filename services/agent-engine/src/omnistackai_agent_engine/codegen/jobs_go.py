"""R-568: the scheduler of a generated Go backend (`internal/handlers/jobs.go`).

The same scheduler as Python's (see `jobs_python.py`): a goroutine started with the server turns
due schedules into runs, claims them with SKIP LOCKED and runs each schedule's statement from
`jobs_sql`; the admin's endpoints list, run, pause and retry.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR
from . import jobs_sql as q

#: (method, path, handler) - registered in main.go behind RequireAuth; the handlers admit the admin.
GO_JOBS_ROUTES = (
    ("GET", "/scheduler/schedules", "SchedulerSchedules"),
    ("POST", "/scheduler/schedules/{name}/run", "SchedulerRunNow"),
    ("POST", "/scheduler/schedules/{name}/pause", "SchedulerPause"),
    ("POST", "/scheduler/schedules/{name}/resume", "SchedulerResume"),
    ("GET", "/scheduler/runs", "SchedulerRuns"),
    ("POST", "/scheduler/runs/{runId}/retry", "SchedulerRetry"),
)


def _go(value: str) -> str:
    """A Go raw string literal (the statements contain double quotes, never backquotes)."""
    assert "`" not in value
    return f"`{value}`"


def _go_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def go_jobs_file(ir: ApplicationIR) -> str:
    compiled = q.compiled_schedules(ir)
    schedules = "\n".join(
        f"\t{_go_str(c.name)}: {{Entity: {_go_str(c.entity)}, EverySeconds: {c.every_seconds}, "
        f"Action: {_go_str(c.action)}, Description: {_go_str(c.description)},\n\t\tSQL: {_go(c.sql)}}},"
        for c in compiled
    )
    order = ", ".join(_go_str(c.name) for c in compiled)
    sync = "\n".join(f"\t{_go(statement)}," for statement in q.sync_statements(ir))
    config = (
        "var schedulerSchedules = map[string]schedulerSchedule{\n" + schedules + "\n}\n\n"
        f"var schedulerOrder = []string{{{order}}}\n\n"
        "var schedulerSync = []string{\n" + sync + "\n}\n\n"
        f"const schedulerBatch = {q.BATCH}\n"
        f"const schedulerMaxBatches = {q.MAX_BATCHES}\n\n"
        "const (\n"
        f"\tsqlEnqueueDue = {_go(q.ENQUEUE_DUE)}\n"
        f"\tsqlClaim = {_go(q.CLAIM)}\n"
        f"\tsqlManual = {_go(q.MANUAL)}\n"
        f"\tsqlDone = {_go(q.DONE)}\n"
        f"\tsqlFailed = {_go(q.FAILED)}\n"
        f"\tsqlRecord = {_go(q.RECORD)}\n"
        f"\tsqlPrune = {_go(q.PRUNE)}\n"
        f"\tsqlSchedules = {_go(q.SCHEDULES)}\n"
        f"\tsqlRuns = {_go(q.RUNS)}\n"
        f"\tsqlRunsWithStatus = {_go(q.RUNS_WITH_STATUS)}\n"
        f"\tsqlRetry = {_go(q.RETRY)}\n"
        f"\tsqlPause = {_go(q.PAUSE)}\n"
        ")\n"
    )
    return _GO.replace("__CONFIG__", config)


_GO = r'''package handlers

// Scheduled jobs (OmniStackAI R-568): rules the app runs on its own, on a clock.
//
// Each schedule is one bounded statement over its rows. Runs are rows in scheduler_run: a failed run
// is retried with backoff and is dead after its last attempt; an admin can retry it. Rows are claimed
// with SKIP LOCKED, so several replicas share the work without running it twice.

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

type schedulerSchedule struct {
	Entity, Action, Description, SQL string
	EverySeconds                     int
}

__CONFIG__
// runSchedule runs one schedule's statement until a batch comes back short; the rows it changed.
func (h *Handlers) runSchedule(ctx context.Context, name string) (int64, error) {
	schedule, ok := schedulerSchedules[name]
	if !ok {
		return 0, fmt.Errorf("no schedule named %q in this version of the app", name)
	}
	var total int64
	for i := 0; i < schedulerMaxBatches; i++ {
		res, err := h.DB.ExecContext(ctx, schedule.SQL)
		if err != nil {
			return total, err
		}
		changed, _ := res.RowsAffected()
		total += changed
		if changed < schedulerBatch {
			break
		}
	}
	return total, nil
}

// finishRun runs a claimed run and records how it went, on the run and on its schedule.
func (h *Handlers) finishRun(ctx context.Context, runID, name string) map[string]any {
	affected, err := h.runSchedule(ctx, name)
	if err != nil {
		message := err.Error()
		if len(message) > 500 {
			message = message[:500]
		}
		status := "failed"
		if scanErr := h.DB.QueryRowContext(ctx, sqlFailed, message, runID).Scan(&status); scanErr != nil {
			log.Printf("scheduler: %v", scanErr)
		}
		if _, recErr := h.DB.ExecContext(ctx, sqlRecord, status, nil, message, name); recErr != nil {
			log.Printf("scheduler: %v", recErr)
		}
		log.Printf("job %s %s: %s", name, status, message)
		return map[string]any{"status": status, "error": message}
	}
	if _, err := h.DB.ExecContext(ctx, sqlDone, affected, runID); err != nil {
		log.Printf("scheduler: %v", err)
	}
	if _, err := h.DB.ExecContext(ctx, sqlRecord, "done", affected, nil, name); err != nil {
		log.Printf("scheduler: %v", err)
	}
	return map[string]any{"status": "done", "affected": affected}
}

// schedulerTick enqueues what is due and runs what is claimable.
func (h *Handlers) schedulerTick(ctx context.Context) error {
	if _, err := h.DB.ExecContext(ctx, sqlEnqueueDue); err != nil {
		return err
	}
	if _, err := h.DB.ExecContext(ctx, sqlPrune); err != nil {
		return err
	}
	for i := 0; i < 20; i++ {
		var id, name string
		err := h.DB.QueryRowContext(ctx, sqlClaim).Scan(&id, &name)
		if err != nil {
			if strings.Contains(err.Error(), "no rows") {
				return nil
			}
			return err
		}
		h.finishRun(ctx, id, name)
	}
	return nil
}

// RunScheduler is started by main.go: it makes the schedule table match this version of the app,
// then looks for due work every SCHEDULER_TICK_SECONDS (10 by default).
func (h *Handlers) RunScheduler() {
	switch strings.ToLower(strings.TrimSpace(os.Getenv("SCHEDULER_DISABLED"))) {
	case "1", "true", "yes":
		log.Printf("scheduler disabled here (SCHEDULER_DISABLED)")
		return
	}
	interval := 10 * time.Second
	if v, err := strconv.ParseFloat(os.Getenv("SCHEDULER_TICK_SECONDS"), 64); err == nil && v >= 1 {
		interval = time.Duration(v * float64(time.Second))
	}
	synced := false
	for {
		ctx := context.Background()
		if !synced {
			synced = true
			for _, statement := range schedulerSync {
				if _, err := h.DB.ExecContext(ctx, statement); err != nil {
					log.Printf("scheduler: %v", err)
					synced = false
					break
				}
			}
		}
		if synced {
			if err := h.schedulerTick(ctx); err != nil {
				log.Printf("scheduler: %v", err)
			}
		}
		time.Sleep(interval)
	}
}

// --- the admin's view ------------------------------------------------------------------------------

func schedulerAdmin(w http.ResponseWriter, r *http.Request) bool {
	if !SeesAll(ClaimsFrom(r)) {
		writeJSON(w, http.StatusForbidden, map[string]string{"detail": "forbidden"})
		return false
	}
	return true
}

type schedulerRun struct {
	ID          string     `json:"id"`
	Schedule    string     `json:"schedule"`
	Trigger     string     `json:"trigger"`
	Status      string     `json:"status"`
	Attempts    int        `json:"attempts"`
	MaxAttempts int        `json:"max_attempts"`
	RunAt       time.Time  `json:"run_at"`
	Affected    *int64     `json:"affected"`
	Error       *string    `json:"error"`
	CreatedAt   time.Time  `json:"created_at"`
	FinishedAt  *time.Time `json:"finished_at"`
}

func scanSchedulerRun(row interface{ Scan(...any) error }) (*schedulerRun, error) {
	var run schedulerRun
	err := row.Scan(&run.ID, &run.Schedule, &run.Trigger, &run.Status, &run.Attempts, &run.MaxAttempts,
		&run.RunAt, &run.Affected, &run.Error, &run.CreatedAt, &run.FinishedAt)
	return &run, err
}

func (h *Handlers) SchedulerSchedules(w http.ResponseWriter, r *http.Request) {
	if !schedulerAdmin(w, r) {
		return
	}
	type state struct {
		Paused       *bool      `json:"paused"`
		NextRunAt    *time.Time `json:"next_run_at"`
		LastRunAt    *time.Time `json:"last_run_at"`
		LastStatus   *string    `json:"last_status"`
		LastAffected *int64     `json:"last_affected"`
		LastError    *string    `json:"last_error"`
	}
	rows, err := h.DB.QueryContext(r.Context(), sqlSchedules)
	if err != nil {
		dbError(w, err)
		return
	}
	defer rows.Close()
	states := map[string]state{}
	for rows.Next() {
		var name string
		var every int
		var s state
		if err := rows.Scan(&name, &every, &s.Paused, &s.NextRunAt, &s.LastRunAt, &s.LastStatus, &s.LastAffected, &s.LastError); err != nil {
			dbError(w, err)
			return
		}
		states[name] = s
	}
	out := []map[string]any{}
	for _, name := range schedulerOrder {
		schedule := schedulerSchedules[name]
		s := states[name]
		out = append(out, map[string]any{
			"name": name, "entity": schedule.Entity, "action": schedule.Action, "description": schedule.Description,
			"every_seconds": schedule.EverySeconds, "paused": s.Paused, "next_run_at": s.NextRunAt,
			"last_run_at": s.LastRunAt, "last_status": s.LastStatus, "last_affected": s.LastAffected, "last_error": s.LastError,
		})
	}
	writeJSON(w, http.StatusOK, out)
}

func (h *Handlers) SchedulerRunNow(w http.ResponseWriter, r *http.Request) {
	if !schedulerAdmin(w, r) {
		return
	}
	name := r.PathValue("name")
	if _, ok := schedulerSchedules[name]; !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"detail": "not_found"})
		return
	}
	var id, schedule string
	if err := h.DB.QueryRowContext(r.Context(), sqlManual, name).Scan(&id, &schedule); err != nil {
		dbError(w, err)
		return
	}
	out := h.finishRun(r.Context(), id, name)
	out["id"], out["schedule"] = id, name
	writeJSON(w, http.StatusOK, out)
}

func (h *Handlers) schedulerPause(w http.ResponseWriter, r *http.Request, paused bool) {
	if !schedulerAdmin(w, r) {
		return
	}
	var name string
	if err := h.DB.QueryRowContext(r.Context(), sqlPause, paused, r.PathValue("name")).Scan(&name); err != nil {
		if strings.Contains(err.Error(), "no rows") {
			writeJSON(w, http.StatusNotFound, map[string]string{"detail": "not_found"})
			return
		}
		dbError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"name": name, "paused": paused})
}

func (h *Handlers) SchedulerPause(w http.ResponseWriter, r *http.Request)  { h.schedulerPause(w, r, true) }
func (h *Handlers) SchedulerResume(w http.ResponseWriter, r *http.Request) { h.schedulerPause(w, r, false) }

func (h *Handlers) SchedulerRuns(w http.ResponseWriter, r *http.Request) {
	if !schedulerAdmin(w, r) {
		return
	}
	query, args := sqlRuns, []any{}
	if status := r.URL.Query().Get("status"); status != "" {
		query, args = sqlRunsWithStatus, []any{status}
	}
	rows, err := h.DB.QueryContext(r.Context(), query, args...)
	if err != nil {
		dbError(w, err)
		return
	}
	defer rows.Close()
	out := []schedulerRun{}
	for rows.Next() {
		run, err := scanSchedulerRun(rows)
		if err != nil {
			dbError(w, err)
			return
		}
		out = append(out, *run)
	}
	writeJSON(w, http.StatusOK, out)
}

// SchedulerRetry queues a failed or dead run again with a fresh set of attempts.
func (h *Handlers) SchedulerRetry(w http.ResponseWriter, r *http.Request) {
	if !schedulerAdmin(w, r) {
		return
	}
	run, err := scanSchedulerRun(h.DB.QueryRowContext(r.Context(), sqlRetry, r.PathValue("runId")))
	if err != nil {
		if strings.Contains(err.Error(), "no rows") {
			writeJSON(w, http.StatusConflict, map[string]string{"detail": "only a failed or dead run can be retried"})
			return
		}
		dbError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, run)
}
'''

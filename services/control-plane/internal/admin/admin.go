// Package admin is the super_admin console's API (PC-011, Phase E): the accounts, their credits,
// plans and roles, what the platform is spending, and the switch that pauses paid model work.
//
// Everything here answers 404 to anyone but a super_admin — the routes do not reveal they exist —
// and every change is written to admin_audit with who made it and why.
package admin

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/plans"
)

// PaidModelWorkKey is the platform setting the kill switch writes.
const PaidModelWorkKey = "paid_model_work"

// Deps wires the admin routes.
type Deps struct {
	AuthStore auth.Store
	Pool      *pgxpool.Pool
	Logger    *slog.Logger
}

// Register adds the super_admin routes.
func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /admin/overview", only(deps, handleOverview))
	mux.HandleFunc("GET /admin/users", only(deps, handleUsers))
	mux.HandleFunc("POST /admin/users/{id}/credits", only(deps, handleCredits))
	mux.HandleFunc("PUT /admin/users/{id}/plan", only(deps, handlePlan))
	mux.HandleFunc("PUT /admin/users/{id}/role", only(deps, handleRole))
	mux.HandleFunc("PUT /admin/settings/paid-model-work", only(deps, handlePause))
	mux.HandleFunc("GET /admin/audit", only(deps, handleAudit))
}

type handler func(w http.ResponseWriter, r *http.Request, deps Deps, actor auth.User)

func only(deps Deps, h handler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil || user.Role != "super_admin" {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "not found"})
			return
		}
		h(w, r, deps, user)
	}
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func audit(ctx context.Context, q interface {
	Exec(context.Context, string, ...any) (pgconnTag, error)
}, actor auth.User, action, target string, detail map[string]any) error {
	payload, _ := json.Marshal(detail)
	var targetArg any
	if target != "" {
		targetArg = target
	}
	_, err := q.Exec(ctx, `INSERT INTO admin_audit (actor_id, action, target_user_id, detail) VALUES ($1, $2, $3, $4)`,
		actor.ID, action, targetArg, payload)
	return err
}

func handleOverview(w http.ResponseWriter, r *http.Request, deps Deps, _ auth.User) {
	ctx := r.Context()
	out := map[string]any{}
	var total int64
	_ = deps.Pool.QueryRow(ctx, `SELECT count(*) FROM users`).Scan(&total)
	out["users_total"] = total
	byPlan := map[string]int64{}
	if rows, err := deps.Pool.Query(ctx, `SELECT plan, count(*) FROM users GROUP BY plan`); err == nil {
		for rows.Next() {
			var plan string
			var n int64
			if rows.Scan(&plan, &n) == nil {
				byPlan[plan] = n
			}
		}
		rows.Close()
	}
	out["users_by_plan"] = byPlan
	spend := func(since time.Duration) int64 {
		var v int64
		_ = deps.Pool.QueryRow(ctx, `SELECT COALESCE(-SUM(delta), 0) FROM credit_ledger WHERE delta < 0 AND created_at >= $1`,
			time.Now().Add(-since)).Scan(&v)
		return v
	}
	out["credits_spent_24h"] = spend(24 * time.Hour)
	out["credits_spent_7d"] = spend(7 * 24 * time.Hour)
	var granted int64
	_ = deps.Pool.QueryRow(ctx, `SELECT COALESCE(SUM(delta), 0) FROM credit_ledger WHERE delta > 0 AND created_at >= $1`,
		time.Now().Add(-7*24*time.Hour)).Scan(&granted)
	out["credits_granted_7d"] = granted
	top := []map[string]any{}
	if rows, err := deps.Pool.Query(ctx, `
		SELECT u.email, -SUM(l.delta) AS spent FROM credit_ledger l JOIN users u ON u.id = l.user_id
		WHERE l.delta < 0 AND l.created_at >= $1 GROUP BY u.email ORDER BY spent DESC LIMIT 5`, time.Now().Add(-24*time.Hour)); err == nil {
		for rows.Next() {
			var email string
			var spent int64
			if rows.Scan(&email, &spent) == nil {
				top = append(top, map[string]any{"email": email, "spent": spent})
			}
		}
		rows.Close()
	}
	out["top_spenders_24h"] = top
	paused, _ := PaidModelWorkPaused(ctx, deps.Pool)
	out["paid_model_work"] = map[bool]string{true: "paused", false: "running"}[paused]
	writeJSON(w, http.StatusOK, out)
}

func handleUsers(w http.ResponseWriter, r *http.Request, deps Deps, _ auth.User) {
	q := strings.TrimSpace(r.URL.Query().Get("q"))
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	rows, err := deps.Pool.Query(r.Context(), `
		SELECT u.id::text, u.email, COALESCE(u.full_name, ''), u.role, u.plan, u.credit_balance, u.created_at,
		       COALESCE((SELECT -SUM(delta) FROM credit_ledger l WHERE l.user_id = u.id AND l.delta < 0
		                 AND l.created_at >= now() - interval '24 hours'), 0)
		FROM users u
		WHERE $1 = '' OR u.email ILIKE '%' || $1 || '%' OR COALESCE(u.full_name, '') ILIKE '%' || $1 || '%'
		ORDER BY u.created_at DESC LIMIT $2`, q, limit)
	if err != nil {
		deps.logger().Error("admin list users", "error", err)
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "could not list users"})
		return
	}
	defer rows.Close()
	users := []map[string]any{}
	for rows.Next() {
		var id, email, name, role, plan string
		var balance, spent int64
		var created time.Time
		if rows.Scan(&id, &email, &name, &role, &plan, &balance, &created, &spent) == nil {
			users = append(users, map[string]any{"id": id, "email": email, "name": name, "role": role, "plan": plan,
				"credit_balance": balance, "created_at": created, "spent_24h": spent})
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{"users": users})
}

func decode(r *http.Request, v any) bool {
	return json.NewDecoder(io.LimitReader(r.Body, 4096)).Decode(v) == nil
}

func handleCredits(w http.ResponseWriter, r *http.Request, deps Deps, actor auth.User) {
	var req struct {
		Amount int64  `json:"amount"`
		Reason string `json:"reason"`
	}
	if !decode(r, &req) || req.Amount == 0 || strings.TrimSpace(req.Reason) == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "an amount (not zero) and a reason are required"})
		return
	}
	target := r.PathValue("id")
	ctx := r.Context()
	tx, err := deps.Pool.Begin(ctx)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "could not start"})
		return
	}
	defer func() { _ = tx.Rollback(ctx) }()
	var balance int64
	// A deduction never takes a balance below zero.
	err = tx.QueryRow(ctx, `UPDATE users SET credit_balance = GREATEST(0, credit_balance + $2) WHERE id = $1 RETURNING credit_balance`,
		target, req.Amount).Scan(&balance)
	if errors.Is(err, pgx.ErrNoRows) {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "user not found"})
		return
	}
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "could not change credits"})
		return
	}
	if _, err := tx.Exec(ctx, `INSERT INTO credit_ledger (user_id, delta, reason, balance_after) VALUES ($1, $2, $3, $4)`,
		target, req.Amount, "admin:"+strings.TrimSpace(req.Reason), balance); err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "could not record credits"})
		return
	}
	if err := audit(ctx, txExec{tx}, actor, "credits", target, map[string]any{"amount": req.Amount, "reason": req.Reason}); err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "could not audit"})
		return
	}
	if err := tx.Commit(ctx); err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "could not save"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"credit_balance": balance})
}

func handlePlan(w http.ResponseWriter, r *http.Request, deps Deps, actor auth.User) {
	var req struct {
		Plan string `json:"plan"`
	}
	if !decode(r, &req) {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request"})
		return
	}
	if _, ok := plans.Catalogue()[req.Plan]; !ok {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "unknown plan"})
		return
	}
	change(w, r, deps, actor, "plan", `UPDATE users SET plan = $2 WHERE id = $1`, req.Plan)
}

func handleRole(w http.ResponseWriter, r *http.Request, deps Deps, actor auth.User) {
	var req struct {
		Role string `json:"role"`
	}
	if !decode(r, &req) || (req.Role != "user" && req.Role != "super_admin") {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "role must be user or super_admin"})
		return
	}
	if req.Role == "user" {
		var admins int64
		_ = deps.Pool.QueryRow(r.Context(), `SELECT count(*) FROM users WHERE role = 'super_admin' AND id <> $1`, r.PathValue("id")).Scan(&admins)
		if admins == 0 {
			writeJSON(w, http.StatusConflict, map[string]string{"error": "The platform must keep at least one super_admin."})
			return
		}
	}
	change(w, r, deps, actor, "role", `UPDATE users SET role = $2 WHERE id = $1`, req.Role)
}

func change(w http.ResponseWriter, r *http.Request, deps Deps, actor auth.User, action, sql, value string) {
	ctx := r.Context()
	target := r.PathValue("id")
	tx, err := deps.Pool.Begin(ctx)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "could not start"})
		return
	}
	defer func() { _ = tx.Rollback(ctx) }()
	tag, err := tx.Exec(ctx, sql, target, value)
	if err != nil || tag.RowsAffected() == 0 {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "user not found"})
		return
	}
	if audit(ctx, txExec{tx}, actor, action, target, map[string]any{action: value}) != nil || tx.Commit(ctx) != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "could not save"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{action: value})
}

func handlePause(w http.ResponseWriter, r *http.Request, deps Deps, actor auth.User) {
	var req struct {
		Paused bool `json:"paused"`
	}
	if !decode(r, &req) {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request"})
		return
	}
	value := map[bool]string{true: "paused", false: "running"}[req.Paused]
	ctx := r.Context()
	if _, err := deps.Pool.Exec(ctx, `
		INSERT INTO platform_settings (key, value, updated_by, updated_at) VALUES ($1, $2, $3, now())
		ON CONFLICT (key) DO UPDATE SET value = $2, updated_by = $3, updated_at = now()`,
		PaidModelWorkKey, value, actor.ID); err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "could not save"})
		return
	}
	_ = audit(ctx, poolExec{deps.Pool}, actor, "paid_model_work", "", map[string]any{"value": value})
	invalidatePause()
	writeJSON(w, http.StatusOK, map[string]string{"paid_model_work": value})
}

func handleAudit(w http.ResponseWriter, r *http.Request, deps Deps, _ auth.User) {
	rows, err := deps.Pool.Query(r.Context(), `
		SELECT a.id, COALESCE(actor.email, ''), a.action, COALESCE(target.email, ''), a.detail, a.created_at
		FROM admin_audit a
		LEFT JOIN users actor ON actor.id = a.actor_id
		LEFT JOIN users target ON target.id = a.target_user_id
		ORDER BY a.created_at DESC LIMIT 100`)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "could not read the audit log"})
		return
	}
	defer rows.Close()
	entries := []map[string]any{}
	for rows.Next() {
		var id int64
		var actor, action, target string
		var detail json.RawMessage
		var at time.Time
		if rows.Scan(&id, &actor, &action, &target, &detail, &at) == nil {
			entries = append(entries, map[string]any{"id": id, "actor": actor, "action": action, "target": target,
				"detail": detail, "at": at})
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{"entries": entries})
}

func (d Deps) logger() *slog.Logger {
	if d.Logger != nil {
		return d.Logger
	}
	return slog.Default()
}

// ── the kill switch, read by the credit guard on every paid task (cached briefly) ──

var pauseCache struct {
	sync.Mutex
	value bool
	at    time.Time
}

func invalidatePause() {
	pauseCache.Lock()
	pauseCache.at = time.Time{}
	pauseCache.Unlock()
}

// PaidModelWorkPaused reports the super_admin's switch, cached for five seconds.
func PaidModelWorkPaused(ctx context.Context, pool *pgxpool.Pool) (bool, error) {
	pauseCache.Lock()
	defer pauseCache.Unlock()
	if time.Since(pauseCache.at) < 5*time.Second {
		return pauseCache.value, nil
	}
	var value string
	err := pool.QueryRow(ctx, `SELECT value FROM platform_settings WHERE key = $1`, PaidModelWorkKey).Scan(&value)
	if errors.Is(err, pgx.ErrNoRows) {
		value, err = "running", nil
	}
	if err != nil {
		return pauseCache.value, err
	}
	pauseCache.value, pauseCache.at = value == "paused", time.Now()
	return pauseCache.value, nil
}

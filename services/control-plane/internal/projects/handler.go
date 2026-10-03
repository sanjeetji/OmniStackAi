package projects

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/account"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/credits"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/plans"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/studioauth"
	"io"
	"log/slog"
	"math"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/ai"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/skills"
)

const (
	defaultPreviewTimeout  = 60 * time.Second
	defaultProblemsTimeout = 90 * time.Second
	defaultProxyTimeout    = 15 * time.Second
)

// How long one build or chat edit may take upstream. Five minutes is right for a cloud model, but
// a local model on a laptop answers the same edit in several minutes, and when this budget expires
// the caller sees "could not reach the control-plane" while the edit is still running and the
// workspace stays locked (R-530). Set OMNISTACKAI_AGENT_CALL_TIMEOUT (for example 30m) when the
// platform runs on Ollama.
var defaultBuildTimeout = durationFromEnv("OMNISTACKAI_AGENT_CALL_TIMEOUT", 5*time.Minute)

// designTimeout bounds one page-design run (PC-098). It runs after the build, page by page, and
// waits out a model's per-minute limits, so it legitimately takes longer than a build: found live,
// the build's 5 minutes cut every run off part-way, and then 30 minutes cut a slow model's run. The
// Studio stops starting pages after 40 minutes, so its end (and its bill) arrives inside this.
var designTimeout = durationFromEnv("OMNISTACKAI_PAGE_DESIGN_TIMEOUT", 60*time.Minute)

func durationFromEnv(name string, fallback time.Duration) time.Duration {
	if raw := strings.TrimSpace(os.Getenv(name)); raw != "" {
		if parsed, err := time.ParseDuration(raw); err == nil && parsed > 0 {
			return parsed
		}
	}
	return fallback
}

type SecretsStore interface {
	ForProject(ctx context.Context, projectID string) (map[string]string, error)
}

type Deps struct {
	AuthStore      auth.Store
	ProjectStore   Store
	SkillStore     skills.Store
	SecretsStore   SecretsStore
	AIStore        ai.Store
	AgentEngineURL string
	CreditsPerUSD  float64
	// CreditGuard (PC-010) decides whether paid model work may start and its budget; nil in tests
	// that are not about credits.
	CreditGuard *credits.Guard
	Logger      *slog.Logger
	HTTPClient  *http.Client
}

func (d Deps) logger() *slog.Logger {
	if d.Logger != nil {
		return d.Logger
	}
	return slog.Default()
}

// httpClient has no overall Timeout on purpose. http.Client.Timeout also covers reading the
// response body, so the old 15 s client cut every streamed build (and every edit, preview,
// problems check, scan and test run) at 15 s - the console received an empty 200 while the
// agent-engine kept working and held the workspace lock (R-518). Each call now carries its own
// budget in its request context: quick reads keep defaultProxyTimeout, long operations get
// their own budget, and streams live until the client disconnects.
func (d Deps) httpClient() *http.Client {
	if d.HTTPClient != nil {
		return d.HTTPClient
	}
	return &http.Client{}
}

// upstreamContext bounds one upstream call. budget <= 0 means "until the caller disconnects".
func upstreamContext(parent context.Context, budget time.Duration) (context.Context, context.CancelFunc) {
	if budget <= 0 {
		return context.WithCancel(parent)
	}
	return context.WithTimeout(parent, budget)
}

// extendWriteDeadline lifts the server-wide WriteTimeout (15 s by default) for a slow route.
// budget <= 0 removes the deadline entirely, which is what an open-ended stream needs.
func extendWriteDeadline(w http.ResponseWriter, budget time.Duration) {
	controller := http.NewResponseController(w)
	if budget <= 0 {
		_ = controller.SetWriteDeadline(time.Time{})
		return
	}
	_ = controller.SetWriteDeadline(time.Now().Add(budget))
}

func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /projects", handleListProjects(deps))
	mux.HandleFunc("POST /projects", handleCreateProject(deps))
	mux.HandleFunc("GET /projects/{id}", handleGetProject(deps))
	mux.HandleFunc("PATCH /projects/{id}", handleUpdateProject(deps))
	mux.HandleFunc("DELETE /projects/{id}", handleDeleteProject(deps))

	mux.HandleFunc("POST /projects/{id}/build/stream", handleProjectBuildStream(deps))
	// PC-098: the model designs the pages after the build, as its own billed step.
	mux.HandleFunc("POST /projects/{id}/design/stream", handleProjectDesignStream(deps))
	mux.HandleFunc("POST /projects/{id}/edit", handleProjectEdit(deps))
	mux.HandleFunc("GET /projects/{id}/turns", handleProjectTurns(deps))
	mux.HandleFunc("GET /projects/{id}/files", handleProjectFiles(deps))
	mux.HandleFunc("GET /projects/{id}/file", handleProjectFile(deps))
	mux.HandleFunc("GET /projects/{id}/preview", handleProjectPreviewGet(deps))
	mux.HandleFunc("POST /projects/{id}/preview", handleProjectPreview(deps))
	mux.HandleFunc("POST /projects/{id}/preview/stop", handleProjectPreviewStop(deps))
	// PC-010: what a build or edit will cost, before it starts.
	mux.HandleFunc("GET /projects/{id}/estimate", handleProjectEstimate(deps))
	mux.HandleFunc("GET /estimate", handleProjectEstimate(deps))
	mux.HandleFunc("POST /scope", handleScope(deps))
	mux.HandleFunc("POST /brief", handleBrief(deps))
	// PC-008: the whole app (database, API, web, admin) at a live URL.
	mux.HandleFunc("GET /projects/{id}/live", handleProjectLive(deps, "", http.MethodGet))
	mux.HandleFunc("POST /projects/{id}/live", handleProjectLive(deps, "", http.MethodPost))
	mux.HandleFunc("POST /projects/{id}/live/rollback", handleProjectLive(deps, "/rollback", http.MethodPost))
	mux.HandleFunc("POST /projects/{id}/live/unpublish", handleProjectLive(deps, "/unpublish", http.MethodPost))
	mux.HandleFunc("POST /projects/{id}/stores", handleProjectStores(deps))
	registerDevice(mux, deps)
	mux.HandleFunc("POST /projects/{id}/problems", handleProjectProblemsCheck(deps))
	mux.HandleFunc("GET /projects/{id}/problems", handleProjectProblemsGet(deps))
	// POST /projects/{id}/seo/audit and POST /projects/{id}/seo/suggest are owned by the seo
	// package (internal/seo/handler.go). Registering them here too made ServeMux panic at startup
	// (R-518); cmd/control-plane/main_test.go now guards the complete route table.
	mux.HandleFunc("GET /projects/{id}/seo/audit", handleProjectSEOAudit(deps))
	mux.HandleFunc("PUT /projects/{id}/seo/page", handleProjectSEOPage(deps))
	mux.HandleFunc("POST /projects/{id}/opened", handleProjectOpened(deps))

	mux.HandleFunc("POST /projects/{id}/build/cancel", handleProjectBuildCancel(deps))
	mux.HandleFunc("GET /projects/{id}/logs", handleProjectLogs(deps))
	mux.HandleFunc("GET /projects/{id}/logs/stream", handleProjectLogsStream(deps))
	mux.HandleFunc("DELETE /projects/{id}/logs", handleProjectLogsClear(deps))

	// Database Explorer (F-09 / R-507)
	mux.HandleFunc("GET /projects/{id}/db/tables", handleProjectDBTables(deps))
	mux.HandleFunc("GET /projects/{id}/db/tables/{table}", handleProjectDBTableRows(deps))
	mux.HandleFunc("POST /projects/{id}/db/query", handleProjectDBQuery(deps))
	mux.HandleFunc("GET /projects/{id}/db/schema", handleProjectDBSchema(deps))

	// Security scan & Tests (F-10 / R-508)
	mux.HandleFunc("POST /projects/{id}/security/scan", handleProjectSecurityScan(deps))
	mux.HandleFunc("GET /projects/{id}/security", handleProjectSecurityGet(deps))
	mux.HandleFunc("POST /projects/{id}/tests/run", handleProjectTestsRun(deps))
	mux.HandleFunc("GET /projects/{id}/tests", handleProjectTestsGet(deps))
}

func handleListProjects(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		status := r.URL.Query().Get("status")
		workspaceID := r.URL.Query().Get("workspace_id")
		limit := 50
		if lStr := r.URL.Query().Get("limit"); lStr != "" {
			if parsed, err := strconv.Atoi(lStr); err == nil && parsed > 0 {
				limit = parsed
			}
		}

		var list []Project
		if workspaceID != "" {
			list, err = deps.ProjectStore.ListWorkspaceProjects(r.Context(), user.ID, workspaceID, status, limit)
		} else {
			list, err = deps.ProjectStore.ListProjects(r.Context(), user.ID, status, limit)
		}
		if err != nil {
			deps.logger().Error("list projects", "error", err)
			writeError(w, http.StatusInternalServerError, "could not list projects")
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{"projects": list})
	}
}

func handleCreateProject(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		var req struct {
			Name        string `json:"name"`
			Description string `json:"description"`
			WorkspaceID string `json:"workspace_id"`
		}
		if r.Body != nil {
			_ = json.NewDecoder(r.Body).Decode(&req)
		}

		// PC-011: projects this user owns count against their plan.
		plan := plans.For(user.Plan)
		if plan.MaxProjects > 0 {
			owned := 0
			if list, err := deps.ProjectStore.ListProjects(r.Context(), user.ID, "active", plan.MaxProjects+1); err == nil {
				for _, existing := range list {
					if existing.UserID == user.ID {
						owned++
					}
				}
			}
			if !plans.Within(owned, plan.MaxProjects) {
				plans.Refuse(w, plan, fmt.Sprintf("more than %d projects", plan.MaxProjects),
					func(p plans.Plan) bool { return p.MaxProjects == 0 || p.MaxProjects > owned })
				return
			}
		}

		var p Project
		if req.WorkspaceID != "" {
			p, err = deps.ProjectStore.CreateProjectInWorkspace(r.Context(), user.ID, req.WorkspaceID, req.Name, req.Description)
		} else {
			p, err = deps.ProjectStore.CreateProject(r.Context(), user.ID, req.Name, req.Description)
		}
		if err != nil {
			deps.logger().Error("create project", "error", err)
			writeError(w, http.StatusInternalServerError, "could not create project")
			return
		}

		writeJSON(w, http.StatusCreated, p)
	}
}

func handleGetProject(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		p, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			deps.logger().Error("get project", "error", err)
			writeError(w, http.StatusInternalServerError, "could not get project")
			return
		}

		_ = deps.ProjectStore.TouchProjectOpened(r.Context(), id, user.ID)
		writeJSON(w, http.StatusOK, p)
	}
}

func handleUpdateProject(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		var req struct {
			Name        *string `json:"name"`
			Description *string `json:"description"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeError(w, http.StatusBadRequest, "invalid request body")
			return
		}

		p, err := deps.ProjectStore.UpdateProject(r.Context(), id, user.ID, req.Name, req.Description)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			deps.logger().Error("update project", "error", err)
			writeError(w, http.StatusInternalServerError, "could not update project")
			return
		}

		writeJSON(w, http.StatusOK, p)
	}
}

func handleDeleteProject(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		purge := r.URL.Query().Get("purge") == "true"

		if purge {
			err = deps.ProjectStore.DeleteProject(r.Context(), id, user.ID)
			if errors.Is(err, ErrProjectNotFound) {
				writeError(w, http.StatusNotFound, "project not found")
				return
			}
			if err != nil {
				deps.logger().Error("delete project", "error", err)
				writeError(w, http.StatusInternalServerError, "could not delete project")
				return
			}

			// Also request agent-engine to delete the workspace directory
			go func() {
				reqURL := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id)
				purgeCtx, purgeCancel := context.WithTimeout(context.Background(), defaultProxyTimeout)
				defer purgeCancel()
				req, reqErr := http.NewRequestWithContext(purgeCtx, http.MethodDelete, reqURL, nil)
				if reqErr == nil {
					resp, doErr := deps.httpClient().Do(req)
					if doErr == nil {
						_ = resp.Body.Close()
					}
				}
			}()

			w.WriteHeader(http.StatusNoContent)
			return
		}

		// Default: archive
		err = deps.ProjectStore.ArchiveProject(r.Context(), id, user.ID)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			deps.logger().Error("archive project", "error", err)
			writeError(w, http.StatusInternalServerError, "could not archive project")
			return
		}

		w.WriteHeader(http.StatusNoContent)
	}
}

// handleProjectDesignStream (PC-098) streams the model designing a project's pages, after the
// build, while the template preview is already running. Same guards as a build (verified email,
// credits, the task budget), billed from the Studio's usage when it finishes.
func handleProjectDesignStream(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if controller := http.NewResponseController(w); controller != nil {
			_ = controller.SetWriteDeadline(time.Now().Add(designTimeout))
		}
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		var body struct {
			Pages []string `json:"pages"`
		}
		_ = json.NewDecoder(io.LimitReader(r.Body, 1<<16)).Decode(&body)
		if !account.RequireVerified(w, user) {
			return
		}
		upstreamPayload := map[string]any{}
		if len(body.Pages) > 0 {
			upstreamPayload["pages"] = body.Pages
		}
		resolved := ai.ResolveModel(r.Context(), deps.AIStore, user.ID, id)
		if resolved.ProviderID != "" {
			upstreamPayload["provider_id"] = resolved.ProviderID
		}
		if resolved.ModelID != "" {
			upstreamPayload["model_id"] = resolved.ModelID
		}
		if resolved.APIKey != "" {
			upstreamPayload["api_key"] = resolved.APIKey
		}
		if deps.CreditGuard != nil {
			plan := plans.For(user.Plan)
			decision := deps.CreditGuard.ForPlan(plan.TaskBudgetCredits, plan.DailyCreditCap).Admit(r.Context(), user.ID, user.CreditBalance, resolved.BilledTo == "platform")
			if !decision.Allowed {
				credits.Refuse(w, decision, user.CreditBalance)
				return
			}
			if decision.BudgetMicros >= 0 {
				upstreamPayload["budget_micros"] = decision.BudgetMicros
			}
		}
		reqBody, _ := json.Marshal(upstreamPayload)
		upstreamURL := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/design/stream"
		// Detached from the client: if they leave, the Studio is told to stop and what it already
		// designed is still read back and billed. Still bounded, by the design timeout.
		designCtx, designCancel := upstreamContext(context.WithoutCancel(r.Context()), designTimeout)
		defer designCancel()
		upstreamRequest, err := http.NewRequestWithContext(designCtx, http.MethodPost, upstreamURL, bytes.NewReader(reqBody))
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not build upstream request")
			return
		}
		upstreamRequest.Header.Set("Content-Type", "application/json")
		upstreamRequest.Header.Set(studioauth.UserHeader, user.ID)
		upstreamRequest.Header.Set(plans.LimitsHeader, plans.StudioLimits(plans.For(user.Plan)))
		upstreamResponse, err := deps.httpClient().Do(upstreamRequest)
		if err != nil {
			writeError(w, http.StatusBadGateway, "could not reach the build service")
			return
		}
		defer func() { _ = upstreamResponse.Body.Close() }()
		if upstreamResponse.StatusCode != http.StatusOK {
			upstreamBody, _ := io.ReadAll(io.LimitReader(upstreamResponse.Body, 1<<20))
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(upstreamResponse.StatusCode)
			_, _ = w.Write(upstreamBody)
			return
		}
		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("X-Accel-Buffering", "no")
		w.WriteHeader(http.StatusOK)
		flusher, _ := w.(http.Flusher)

		var doneUsage any
		sawDone, clientGone := false, false
		reader := bufio.NewReader(upstreamResponse.Body)
		for {
			frame, readErr := readSSEFrame(reader)
			if len(frame) > 0 && !clientGone {
				if _, writeErr := w.Write(frame); writeErr != nil {
					// The person left: the Studio stops after the page it is writing, and this keeps
					// reading so what was already designed (and kept) is still billed.
					clientGone = true
					go func() {
						cancelURL := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/cancel"
						cancelCtx, cancelDone := context.WithTimeout(context.Background(), defaultProxyTimeout)
						defer cancelDone()
						req, _ := http.NewRequestWithContext(cancelCtx, http.MethodPost, cancelURL, nil)
						if resp, doErr := deps.httpClient().Do(req); doErr == nil {
							_ = resp.Body.Close()
						}
					}()
				} else if flusher != nil {
					flusher.Flush()
				}
			}
			if len(frame) > 0 {
				if payload := parseSSEDataPayload(frame); payload != nil {
					if phase, _ := payload["phase"].(string); phase == "done" {
						sawDone = true
						doneUsage = payload["usage"]
					}
				}
			}
			if readErr != nil {
				break
			}
		}
		if !sawDone {
			return
		}
		requestedCredits := int64(0)
		if resolved.BilledTo == "platform" {
			requestedCredits = creditsForUsage(doneUsage, deps.CreditsPerUSD)
		}
		charged := int64(0)
		if requestedCredits > 0 {
			// Detached from the request: a person who closed the tab still used what was designed.
			charged, _, err = deps.ProjectStore.DebitProjectCredits(context.WithoutCancel(r.Context()), user.ID, id, requestedCredits, "project:design")
			if err != nil {
				deps.logger().Error("debit credits for page design", "error", err, "user_id", user.ID, "project_id", id)
			}
		}
		_ = ai.RecordUsageCalls(context.WithoutCancel(r.Context()), deps.AIStore, user.ID, &id, "design", resolved.BilledTo, doneUsage, charged, deps.CreditsPerUSD)
		if !clientGone {
			writeSSEEvent(w, flusher, "credits", map[string]any{"credits_spent": charged})
		}
	}
}

func handleProjectBuildStream(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if controller := http.NewResponseController(w); controller != nil {
			_ = controller.SetWriteDeadline(time.Now().Add(defaultBuildTimeout))
		}

		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		project, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			deps.logger().Error("resolve project for build stream", "error", err)
			writeError(w, http.StatusInternalServerError, "could not load project")
			return
		}

		body, err := io.ReadAll(r.Body)
		_ = r.Body.Close()
		if err != nil {
			writeError(w, http.StatusBadRequest, "could not read request body")
			return
		}

		var parsedBody struct {
			Prompt        string   `json:"prompt"`
			MentionSkills []string `json:"mention_skills"`
		}
		_ = json.Unmarshal(body, &parsedBody)

		var contextPayload any
		if deps.SkillStore != nil {
			ctxBlock, err := deps.SkillStore.ResolveContext(r.Context(), user.ID, id, parsedBody.MentionSkills)
			if err != nil {
				deps.logger().Warn("failed to resolve skills context", "error", err, "project_id", id)
			} else if ctxBlock != nil {
				contextPayload = ctxBlock
			}
		}

		var upstreamPayload map[string]any
		if err := json.Unmarshal(body, &upstreamPayload); err != nil {
			upstreamPayload = make(map[string]any)
		}
		if contextPayload != nil {
			upstreamPayload["context"] = contextPayload
		}
		resolved := ai.ResolveModel(r.Context(), deps.AIStore, user.ID, id)
		if resolved.ProviderID != "" {
			upstreamPayload["provider_id"] = resolved.ProviderID
		}
		if resolved.ModelID != "" {
			upstreamPayload["model_id"] = resolved.ModelID
		}
		if resolved.APIKey != "" {
			upstreamPayload["api_key"] = resolved.APIKey
		}
		// PC-012: building and editing wait for a verified email address.
		if !account.RequireVerified(w, user) {
			return
		}
		// PC-010: the budget is the control plane's to set, never the caller's.
		delete(upstreamPayload, "budget_micros")
		if deps.CreditGuard != nil {
			plan := plans.For(user.Plan)
			decision := deps.CreditGuard.ForPlan(plan.TaskBudgetCredits, plan.DailyCreditCap).Admit(r.Context(), user.ID, user.CreditBalance, resolved.BilledTo == "platform")
			if !decision.Allowed {
				credits.Refuse(w, decision, user.CreditBalance)
				return
			}
			if decision.BudgetMicros >= 0 {
				upstreamPayload["budget_micros"] = decision.BudgetMicros
			}
		}
		reqBody, _ := json.Marshal(upstreamPayload)

		upstreamURL := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/build/stream"
		buildCtx, buildCancel := upstreamContext(r.Context(), defaultBuildTimeout)
		defer buildCancel()
		upstreamRequest, err := http.NewRequestWithContext(buildCtx, http.MethodPost, upstreamURL, bytes.NewReader(reqBody))
		if err != nil {
			deps.logger().Error("project build stream agent-engine request", "error", err)
			writeError(w, http.StatusInternalServerError, "could not build upstream request")
			return
		}
		upstreamRequest.Header.Set("Content-Type", "application/json")
		// PC-009: whose build this is, for the Studio's per-user quotas. Set from the session, never
		// from the caller's own headers.
		upstreamRequest.Header.Set(studioauth.UserHeader, user.ID)
		upstreamRequest.Header.Set(plans.LimitsHeader, plans.StudioLimits(plans.For(user.Plan)))

		upstreamResponse, err := deps.httpClient().Do(upstreamRequest)
		if err != nil {
			deps.logger().Error("call agent-engine project build stream", "error", err)
			writeError(w, http.StatusBadGateway, "could not reach the build service")
			return
		}
		defer func() { _ = upstreamResponse.Body.Close() }()

		if upstreamResponse.StatusCode != http.StatusOK {
			upstreamBody, readErr := io.ReadAll(upstreamResponse.Body)
			if readErr != nil {
				deps.logger().Error("read agent-engine build-stream error response", "error", readErr)
				writeError(w, http.StatusBadGateway, "could not read build service response")
				return
			}
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(upstreamResponse.StatusCode)
			_, _ = w.Write(upstreamBody)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("X-Accel-Buffering", "no")
		w.WriteHeader(http.StatusOK)
		flusher, _ := w.(http.Flusher)

		var sawDone bool
		var sawCancelled bool
		var doneUsage any
		var cancelledUsage any
		var donePayload map[string]any
		reader := bufio.NewReader(upstreamResponse.Body)
		for {
			frame, readErr := readSSEFrame(reader)
			if len(frame) > 0 {
				if _, writeErr := w.Write(frame); writeErr != nil {
					go func() {
						cancelURL := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/cancel"
						cancelCtx, cancelDone := context.WithTimeout(context.Background(), defaultProxyTimeout)
						defer cancelDone()
						req, _ := http.NewRequestWithContext(cancelCtx, http.MethodPost, cancelURL, nil)
						resp, doErr := deps.httpClient().Do(req)
						if doErr == nil {
							_ = resp.Body.Close()
						}
					}()
					return
				}
				if flusher != nil {
					flusher.Flush()
				}
				if payload := parseSSEDataPayload(frame); payload != nil {
					if phase, _ := payload["phase"].(string); phase == "done" {
						sawDone = true
						donePayload = payload
						doneUsage = payload["usage"]
					} else if phase == "cancelled" {
						sawCancelled = true
						cancelledUsage = payload["usage"]
					}
				}
			}
			if readErr != nil {
				break
			}
		}

		if sawCancelled {
			requestedCredits := int64(0)
			if resolved.BilledTo == "platform" {
				requestedCredits = creditsForUsage(cancelledUsage, deps.CreditsPerUSD)
			}
			charged := int64(0)
			if requestedCredits > 0 {
				charged, _, _ = deps.ProjectStore.DebitProjectCredits(r.Context(), user.ID, id, requestedCredits, "project:build:cancelled")
			}
			_ = ai.RecordUsageCalls(r.Context(), deps.AIStore, user.ID, &id, "build", resolved.BilledTo, cancelledUsage, charged, deps.CreditsPerUSD)
			return
		}

		if !sawDone {
			return
		}

		requestedCredits := int64(0)
		if resolved.BilledTo == "platform" {
			requestedCredits = creditsForUsage(doneUsage, deps.CreditsPerUSD)
		}
		charged, newBalance := int64(0), user.CreditBalance
		if requestedCredits > 0 {
			charged, newBalance, err = deps.ProjectStore.DebitProjectCredits(r.Context(), user.ID, id, requestedCredits, "project:build:stream")
			if err != nil {
				deps.logger().Error("debit project credits for completed streamed call",
					"error", err, "user_id", user.ID, "project_id", id, "requested_credits", requestedCredits)
				writeSSEEvent(w, flusher, "credits_error", map[string]any{"error": "the call succeeded but credit accounting failed"})
				return
			}
		}
		_ = ai.RecordUsageCalls(r.Context(), deps.AIStore, user.ID, &id, "build", resolved.BilledTo, doneUsage, charged, deps.CreditsPerUSD)

		// Update project metadata from done payload
		appName, _ := donePayload["name"].(string)
		commitSHA, _ := donePayload["commit_sha"].(string)
		fileCount := 0
		if fc, ok := donePayload["file_count"].(float64); ok {
			fileCount = int(fc)
		}
		var entitiesJSON json.RawMessage
		if rawEntities, ok := donePayload["entities"]; ok {
			if eBytes, mErr := json.Marshal(rawEntities); mErr == nil {
				entitiesJSON = eBytes
			}
		}

		promptUsed := parsedBody.Prompt
		if promptUsed == "" {
			promptUsed = project.LastPrompt
		}

		_ = deps.ProjectStore.UpdateProjectBuildResult(
			r.Context(),
			id,
			user.ID,
			appName,
			promptUsed,
			commitSHA,
			entitiesJSON,
			fileCount,
			1, // 1 message added
		)

		writeSSEEvent(w, flusher, "credits", map[string]any{"credits_spent": charged, "credit_balance": newBalance})
	}
}

func handleProjectEdit(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if controller := http.NewResponseController(w); controller != nil {
			_ = controller.SetWriteDeadline(time.Now().Add(defaultBuildTimeout))
		}

		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		project, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			deps.logger().Error("resolve project for edit", "error", err)
			writeError(w, http.StatusInternalServerError, "could not load project")
			return
		}

		body, err := io.ReadAll(r.Body)
		_ = r.Body.Close()
		if err != nil {
			writeError(w, http.StatusBadRequest, "could not read request body")
			return
		}

		var parsedBody struct {
			Prompt        string   `json:"prompt"`
			MentionSkills []string `json:"mention_skills"`
		}
		_ = json.Unmarshal(body, &parsedBody)

		var contextPayload any
		if deps.SkillStore != nil {
			ctxBlock, err := deps.SkillStore.ResolveContext(r.Context(), user.ID, id, parsedBody.MentionSkills)
			if err != nil {
				deps.logger().Warn("failed to resolve skills context for edit", "error", err, "project_id", id)
			} else if ctxBlock != nil {
				contextPayload = ctxBlock
			}
		}

		var upstreamPayload map[string]any
		if err := json.Unmarshal(body, &upstreamPayload); err != nil {
			upstreamPayload = make(map[string]any)
		}
		if contextPayload != nil {
			upstreamPayload["context"] = contextPayload
		}
		resolved := ai.ResolveModel(r.Context(), deps.AIStore, user.ID, id)
		if resolved.ProviderID != "" {
			upstreamPayload["provider_id"] = resolved.ProviderID
		}
		if resolved.ModelID != "" {
			upstreamPayload["model_id"] = resolved.ModelID
		}
		if resolved.APIKey != "" {
			upstreamPayload["api_key"] = resolved.APIKey
		}
		// PC-012: building and editing wait for a verified email address.
		if !account.RequireVerified(w, user) {
			return
		}
		// PC-010: the budget is the control plane's to set, never the caller's.
		delete(upstreamPayload, "budget_micros")
		if deps.CreditGuard != nil {
			plan := plans.For(user.Plan)
			decision := deps.CreditGuard.ForPlan(plan.TaskBudgetCredits, plan.DailyCreditCap).Admit(r.Context(), user.ID, user.CreditBalance, resolved.BilledTo == "platform")
			if !decision.Allowed {
				credits.Refuse(w, decision, user.CreditBalance)
				return
			}
			if decision.BudgetMicros >= 0 {
				upstreamPayload["budget_micros"] = decision.BudgetMicros
			}
		}
		reqBody, _ := json.Marshal(upstreamPayload)

		targetURL := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/edit"
		editCtx, editCancel := upstreamContext(r.Context(), defaultBuildTimeout)
		defer editCancel()
		upstreamRequest, err := http.NewRequestWithContext(editCtx, http.MethodPost, targetURL, bytes.NewReader(reqBody))
		if err != nil {
			deps.logger().Error("build agent-engine project edit request", "error", err)
			writeError(w, http.StatusInternalServerError, "could not build upstream request")
			return
		}
		upstreamRequest.Header.Set("Content-Type", "application/json")

		upstreamResponse, err := deps.httpClient().Do(upstreamRequest)
		if err != nil {
			deps.logger().Error("call agent-engine project edit", "error", err)
			writeError(w, http.StatusBadGateway, "could not reach the build service")
			return
		}
		defer func() { _ = upstreamResponse.Body.Close() }()

		upstreamBody, err := io.ReadAll(upstreamResponse.Body)
		if err != nil {
			deps.logger().Error("read agent-engine response", "error", err)
			writeError(w, http.StatusBadGateway, "could not read build service response")
			return
		}

		if upstreamResponse.StatusCode < 200 || upstreamResponse.StatusCode >= 300 {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(upstreamResponse.StatusCode)
			_, _ = w.Write(upstreamBody)
			return
		}

		var payload map[string]any
		if err := json.Unmarshal(upstreamBody, &payload); err != nil {
			deps.logger().Error("decode agent-engine response", "error", err)
			writeError(w, http.StatusBadGateway, "build service returned a malformed response")
			return
		}

		requestedCredits := int64(0)
		if resolved.BilledTo == "platform" {
			requestedCredits = creditsForUsage(payload["usage"], deps.CreditsPerUSD)
		}
		charged, newBalance := int64(0), user.CreditBalance
		if requestedCredits > 0 {
			charged, newBalance, err = deps.ProjectStore.DebitProjectCredits(r.Context(), user.ID, id, requestedCredits, "project:edit")
			if err != nil {
				deps.logger().Error("debit project credits for completed edit",
					"error", err, "user_id", user.ID, "project_id", id, "requested_credits", requestedCredits)
				writeError(w, http.StatusInternalServerError, "the call succeeded but credit accounting failed")
				return
			}
		}
		_ = ai.RecordUsageCalls(r.Context(), deps.AIStore, user.ID, &id, "edit", resolved.BilledTo, payload["usage"], charged, deps.CreditsPerUSD)

		// Update project metadata
		commitSHA, _ := payload["commit_sha"].(string)
		fileCount := project.FileCount
		if fc, ok := payload["file_count"].(float64); ok {
			fileCount = int(fc)
		}
		var entitiesJSON json.RawMessage
		if rawEntities, ok := payload["entities"]; ok {
			if eBytes, mErr := json.Marshal(rawEntities); mErr == nil {
				entitiesJSON = eBytes
			}
		}

		promptUsed := parsedBody.Prompt
		if promptUsed == "" {
			promptUsed = project.LastPrompt
		}

		_ = deps.ProjectStore.UpdateProjectBuildResult(
			r.Context(),
			id,
			user.ID,
			"", // don't override name
			promptUsed,
			commitSHA,
			entitiesJSON,
			fileCount,
			1,
		)

		payload["credits_spent"] = charged
		payload["credit_balance"] = newBalance
		writeJSON(w, http.StatusOK, payload)
	}
}

func handleProjectTurns(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		proxyGet(w, r, deps, deps.AgentEngineURL+"/api/workspaces/"+url.PathEscape(id)+"/turns")
	}
}

func handleProjectFiles(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		proxyGet(w, r, deps, deps.AgentEngineURL+"/api/workspaces/"+url.PathEscape(id)+"/files")
	}
}

func handleProjectFile(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/file"
		if path := r.URL.Query().Get("path"); path != "" {
			target += "?" + (url.Values{"path": {path}}).Encode()
		}
		proxyGet(w, r, deps, target)
	}
}

func handleProjectPreviewGet(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/preview"
		proxyGet(w, r, deps, target)
	}
}

func handleProjectPreview(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if controller := http.NewResponseController(w); controller != nil {
			_ = controller.SetWriteDeadline(time.Now().Add(defaultPreviewTimeout))
		}
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}

		var bodyReader io.Reader
		if deps.SecretsStore != nil {
			if sec, err := deps.SecretsStore.ForProject(r.Context(), id); err == nil && len(sec) > 0 {
				payload := map[string]any{"env": sec}
				if bodyBytes, err := json.Marshal(payload); err == nil {
					bodyReader = bytes.NewReader(bodyBytes)
				}
			}
		}

		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/preview"
		proxyUpstreamWithin(w, r, deps, http.MethodPost, target, bodyReader, defaultPreviewTimeout)
	}
}

// handleScope (PC-127) answers "what will be built for this prompt?" before a build: one app, an
// app and its admin, a few apps or an ecosystem, each app with its reason. The agent-engine decides
// it without a model call, so it costs nothing; signed-in users only, like every build request.
func handleScope(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if _, err := auth.RequireUser(r.Context(), deps.AuthStore, r); err != nil {
			writeAuthError(w, deps, err)
			return
		}
		body, err := io.ReadAll(io.LimitReader(r.Body, 64*1024))
		_ = r.Body.Close()
		if err != nil {
			writeError(w, http.StatusBadRequest, "could not read request body")
			return
		}
		proxyUpstreamWithin(w, r, deps, http.MethodPost, deps.AgentEngineURL+"/api/scope", bytes.NewReader(body), defaultProxyTimeout)
	}
}

// handleBrief (PC-128) answers "what do you need to know?" after the prompt: apps, features,
// questions for what the prompt leaves open, brand, region and stack, every answer pre-filled.
// Decided by the agent-engine without a model call, so it costs nothing.
func handleBrief(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if _, err := auth.RequireUser(r.Context(), deps.AuthStore, r); err != nil {
			writeAuthError(w, deps, err)
			return
		}
		body, err := io.ReadAll(io.LimitReader(r.Body, 64*1024))
		_ = r.Body.Close()
		if err != nil {
			writeError(w, http.StatusBadRequest, "could not read request body")
			return
		}
		proxyUpstreamWithin(w, r, deps, http.MethodPost, deps.AgentEngineURL+"/api/brief", bytes.NewReader(body), defaultProxyTimeout)
	}
}

// handleProjectEstimate (PC-010) answers "what will this cost?" before a build or edit: the likely
// range in credits for the model this project would use, the balance, and whether it may start
// now (and if not, why). Work billed to the user's own model key costs no credits.
func handleProjectEstimate(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		// A new chat has no project yet: /estimate answers for the account's default model.
		id := r.PathValue("id")
		if id != "" {
			if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
				writeError(w, http.StatusNotFound, "project not found")
				return
			}
		}
		kind := r.URL.Query().Get("kind")
		if kind != "edit" {
			kind = "build"
		}
		resolved := ai.ResolveModel(r.Context(), deps.AIStore, user.ID, id)
		out := map[string]any{"kind": kind, "credit_balance": user.CreditBalance, "billed_to": resolved.BilledTo}
		if resolved.BilledTo != "platform" {
			out["credits_low"], out["credits_high"] = 0, 0
			out["can_start"] = true
			out["note"] = "Billed to your own model key: no credits are used."
			writeJSON(w, http.StatusOK, out)
			return
		}
		query := url.Values{"kind": {kind}}
		if resolved.ProviderID != "" {
			query.Set("provider_id", resolved.ProviderID)
			query.Set("model_id", resolved.ModelID)
		}
		ctx, cancel := upstreamContext(r.Context(), defaultProxyTimeout)
		defer cancel()
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, deps.AgentEngineURL+"/api/estimate?"+query.Encode(), nil)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not build the estimate request")
			return
		}
		resp, err := deps.httpClient().Do(req)
		if err != nil {
			writeError(w, http.StatusBadGateway, "could not reach the build service")
			return
		}
		defer func() { _ = resp.Body.Close() }()
		var est struct {
			Priced   bool   `json:"priced"`
			Low      int64  `json:"cost_micros_low"`
			High     int64  `json:"cost_micros_high"`
			Basis    string `json:"basis"`
			Provider string `json:"provider_id"`
			Model    string `json:"model_id"`
			// PC-098: a build's estimate includes the page design that follows it.
			Design *struct {
				Model string `json:"model_id"`
			} `json:"design"`
		}
		if resp.StatusCode != http.StatusOK || json.NewDecoder(resp.Body).Decode(&est) != nil {
			writeError(w, http.StatusBadGateway, "the build service could not estimate")
			return
		}
		out["credits_low"] = credits.MicrosToCredits(est.Low, deps.CreditsPerUSD)
		out["credits_high"] = credits.MicrosToCredits(est.High, deps.CreditsPerUSD)
		out["model"] = est.Provider + ":" + est.Model
		out["basis"] = est.Basis
		out["priced"] = est.Priced
		out["includes_page_design"] = est.Design != nil
		if !est.Priced {
			out["note"] = "This model has no configured price, so it uses no credits."
		}
		out["can_start"] = true
		if deps.CreditGuard != nil {
			decision := deps.CreditGuard.Admit(r.Context(), user.ID, user.CreditBalance, true)
			out["can_start"] = decision.Allowed
			if !decision.Allowed {
				out["reason"] = decision.Message
				out["retry_after"] = decision.RetryAfter
			} else {
				out["budget_credits"] = credits.MicrosToCredits(decision.BudgetMicros, deps.CreditsPerUSD)
			}
		}
		writeJSON(w, http.StatusOK, out)
	}
}

// storesBudget bounds a store request: the first run installs eas-cli, and an upload can take minutes.
const storesBudget = 15 * time.Minute

// handleProjectStores forwards a Google Play / App Store request for a project the user owns
// (R-574): check, build or submit its mobile app. The store credentials are the project's own
// secrets, added here exactly as a publish adds them; the reply never carries them back.
func handleProjectStores(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if controller := http.NewResponseController(w); controller != nil {
			_ = controller.SetWriteDeadline(time.Now().Add(storesBudget + time.Minute))
		}
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		var in struct {
			Platform string `json:"platform"`
			Action   string `json:"action"`
		}
		if err := json.NewDecoder(io.LimitReader(r.Body, 4096)).Decode(&in); err != nil {
			writeError(w, http.StatusBadRequest, "invalid body")
			return
		}
		if in.Action == "" {
			in.Action = "check"
		}
		// Nothing goes to a store from an unverified account (PC-012); checking is fine.
		if in.Action != "check" && !account.RequireVerified(w, user) {
			return
		}
		payload := map[string]any{"platform": in.Platform, "action": in.Action}
		if deps.SecretsStore != nil {
			if sec, err := deps.SecretsStore.ForProject(r.Context(), id); err == nil && len(sec) > 0 {
				payload["env"] = sec
			}
		}
		body, _ := json.Marshal(payload)
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/stores"
		proxyUpstreamWithin(w, r, deps, http.MethodPost, target, bytes.NewReader(body), storesBudget)
	}
}

// handleProjectLive forwards a live-publish request for a project the user owns (PC-008).
// Publishing starts the project's own secrets with it, exactly as the preview does; the reply
// never carries them back.
func handleProjectLive(deps Deps, suffix, method string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/live" + suffix
		// PC-012: nothing goes public from an unverified account.
		if method == http.MethodPost && suffix == "" && !account.RequireVerified(w, user) {
			return
		}
		if method == http.MethodGet {
			proxyGet(w, r, deps, target)
			return
		}
		var bodyReader io.Reader
		if suffix == "" {
			payload := map[string]any{}
			if deps.SecretsStore != nil {
				if sec, err := deps.SecretsStore.ForProject(r.Context(), id); err == nil && len(sec) > 0 {
					payload["env"] = sec
				}
			}
			if bodyBytes, err := json.Marshal(payload); err == nil {
				bodyReader = bytes.NewReader(bodyBytes)
			}
		} else if suffix == "/unpublish" {
			var in struct {
				DeleteData bool `json:"delete_data"`
			}
			_ = json.NewDecoder(io.LimitReader(r.Body, 4096)).Decode(&in)
			if bodyBytes, err := json.Marshal(map[string]bool{"delete_data": in.DeleteData}); err == nil {
				bodyReader = bytes.NewReader(bodyBytes)
			}
		}
		proxyUpstream(w, r, deps, http.MethodPost, target, bodyReader)
	}
}

func handleProjectPreviewStop(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/preview/stop"
		proxyUpstream(w, r, deps, http.MethodPost, target, nil)
	}
}

func handleProjectProblemsCheck(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if controller := http.NewResponseController(w); controller != nil {
			_ = controller.SetWriteDeadline(time.Now().Add(defaultProblemsTimeout))
		}
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/problems"
		proxyUpstreamWithin(w, r, deps, http.MethodPost, target, nil, defaultProblemsTimeout)
	}
}

func handleProjectProblemsGet(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/problems"
		proxyGet(w, r, deps, target)
	}
}

func proxyGet(w http.ResponseWriter, r *http.Request, deps Deps, targetURL string) {
	proxyUpstream(w, r, deps, http.MethodGet, targetURL, nil)
}

// proxyUpstream relays a quick request with the default 15 s budget.
func proxyUpstream(w http.ResponseWriter, r *http.Request, deps Deps, method string, targetURL string, body io.Reader) {
	proxyUpstreamWithin(w, r, deps, method, targetURL, body, defaultProxyTimeout)
}

// proxyUpstreamWithin relays a request that may legitimately take longer (a model call, a
// toolchain run). It also lifts the server's write deadline to match, or the response would be
// dropped at the server-wide WriteTimeout even though the upstream call succeeded.
func proxyUpstreamWithin(w http.ResponseWriter, r *http.Request, deps Deps, method string, targetURL string, body io.Reader, budget time.Duration) {
	if budget > defaultProxyTimeout {
		extendWriteDeadline(w, budget+5*time.Second)
	}
	ctx, cancel := upstreamContext(r.Context(), budget)
	defer cancel()
	upstreamRequest, err := http.NewRequestWithContext(ctx, method, targetURL, body)
	if err != nil {
		deps.logger().Error("build proxy request", "error", err)
		writeError(w, http.StatusInternalServerError, "could not build upstream request")
		return
	}
	if body != nil {
		upstreamRequest.Header.Set("Content-Type", "application/json")
	}
	// PC-009: whose request this is, for the Studio's per-user quotas. From the session only — the
	// upstream request is new, so nothing the browser sent can set it.
	if deps.AuthStore != nil {
		if user, err := auth.RequireUser(r.Context(), deps.AuthStore, r); err == nil {
			upstreamRequest.Header.Set(studioauth.UserHeader, user.ID)
			upstreamRequest.Header.Set(plans.LimitsHeader, plans.StudioLimits(plans.For(user.Plan)))
		}
	}

	upstreamResponse, err := deps.httpClient().Do(upstreamRequest)
	if err != nil {
		deps.logger().Error("call agent-engine", "error", err)
		writeError(w, http.StatusBadGateway, "could not reach the build service")
		return
	}
	defer func() { _ = upstreamResponse.Body.Close() }()

	upstreamBody, err := io.ReadAll(upstreamResponse.Body)
	if err != nil {
		deps.logger().Error("read agent-engine response", "error", err)
		writeError(w, http.StatusBadGateway, "could not read build service response")
		return
	}

	contentType := upstreamResponse.Header.Get("Content-Type")
	if contentType == "" {
		contentType = "application/json"
	}
	w.Header().Set("Content-Type", contentType)
	w.WriteHeader(upstreamResponse.StatusCode)
	_, _ = w.Write(upstreamBody)
}

func readSSEFrame(reader *bufio.Reader) ([]byte, error) {
	var buf bytes.Buffer
	for {
		line, err := reader.ReadBytes('\n')
		buf.Write(line)
		if err != nil {
			return buf.Bytes(), err
		}
		if len(line) == 1 {
			return buf.Bytes(), nil
		}
	}
}

func parseSSEDataPayload(frame []byte) map[string]any {
	for _, line := range bytes.Split(frame, []byte("\n")) {
		if data, ok := bytes.CutPrefix(line, []byte("data: ")); ok {
			var payload map[string]any
			if err := json.Unmarshal(data, &payload); err == nil {
				return payload
			}
		}
	}
	return nil
}

func writeSSEEvent(w http.ResponseWriter, flusher http.Flusher, event string, payload any) {
	body, err := json.Marshal(payload)
	if err != nil {
		return
	}
	_, _ = w.Write([]byte("event: " + event + "\ndata: " + string(body) + "\n\n"))
	if flusher != nil {
		flusher.Flush()
	}
}

func creditsForUsage(raw any, creditsPerUSD float64) int64 {
	if creditsPerUSD <= 0 {
		return 0
	}
	usageMap, ok := raw.(map[string]any)
	if !ok || usageMap == nil {
		return 0
	}
	// PC-010: the billable cost leaves out answers the platform threw away and is capped at the
	// task's budget; older payloads only carry the total.
	rawCost, ok := usageMap["billable_cost_micros_usd"]
	if !ok || rawCost == nil {
		rawCost, ok = usageMap["cost_micros_usd"]
	}
	if !ok || rawCost == nil {
		return 0
	}
	var costMicros int64
	switch v := rawCost.(type) {
	case float64:
		costMicros = int64(math.Round(v))
	case int64:
		costMicros = v
	default:
		return 0
	}
	if costMicros <= 0 {
		return 0
	}
	credits := int64(math.Ceil(float64(costMicros) * creditsPerUSD / 1_000_000.0))
	if credits < 0 {
		return 0
	}
	return credits
}

func writeJSON(w http.ResponseWriter, code int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, code int, message string) {
	writeJSON(w, code, map[string]string{"error": message})
}

func writeAuthError(w http.ResponseWriter, deps Deps, err error) {
	if errors.Is(err, auth.ErrUnauthenticated) {
		writeError(w, http.StatusUnauthorized, "missing bearer token or session not found or expired")
		return
	}
	deps.logger().Error("unexpected auth error", "error", err)
	writeError(w, http.StatusInternalServerError, "authentication check failed")
}

func handleProjectSEOAudit(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/seo/audit"
		if r.Method == http.MethodPost {
			proxyUpstream(w, r, deps, http.MethodPost, target, r.Body)
		} else {
			proxyGet(w, r, deps, target)
		}
	}
}

func handleProjectSEOPage(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/seo/page"
		proxyUpstream(w, r, deps, http.MethodPut, target, r.Body)
	}
}

// handleProjectOpened records that the user opened a project (the console calls it when the
// Studio loads one). It existed in the console client since F-01 but was never registered, so
// every Studio load logged a failed request (R-518). Ownership is checked; the answer is 204.
func handleProjectOpened(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			if errors.Is(err, ErrProjectNotFound) {
				writeError(w, http.StatusNotFound, "project not found")
				return
			}
			deps.logger().Error("opened: get project", "error", err)
			writeError(w, http.StatusInternalServerError, "could not get project")
			return
		}
		if err := deps.ProjectStore.TouchProjectOpened(r.Context(), id, user.ID); err != nil {
			deps.logger().Error("opened: touch project", "error", err)
			writeError(w, http.StatusInternalServerError, "could not record project open")
			return
		}
		w.WriteHeader(http.StatusNoContent)
	}
}

func handleProjectBuildCancel(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/cancel"
		proxyUpstream(w, r, deps, http.MethodPost, target, r.Body)
	}
}

func handleProjectLogs(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/logs"
		if r.URL.RawQuery != "" {
			target += "?" + r.URL.RawQuery
		}
		proxyGet(w, r, deps, target)
	}
}

func handleProjectLogsStream(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}

		targetURL := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/logs?follow=1"
		if r.URL.RawQuery != "" {
			targetURL += "&" + r.URL.RawQuery
		}
		// An open-ended tail: no write deadline and no call budget - it ends when the client
		// disconnects (r.Context() is cancelled) or the upstream closes the stream.
		extendWriteDeadline(w, 0)
		upstreamReq, err := http.NewRequestWithContext(r.Context(), http.MethodGet, targetURL, nil)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not build upstream request")
			return
		}

		resp, err := deps.httpClient().Do(upstreamReq)
		if err != nil {
			deps.logger().Error("call agent-engine workspace logs stream", "error", err)
			writeError(w, http.StatusBadGateway, "could not reach logs service")
			return
		}
		defer func() { _ = resp.Body.Close() }()

		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(resp.StatusCode)
			_, _ = w.Write(body)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("X-Accel-Buffering", "no")
		w.WriteHeader(http.StatusOK)
		flusher, _ := w.(http.Flusher)

		reader := bufio.NewReader(resp.Body)
		for {
			frame, readErr := readSSEFrame(reader)
			if len(frame) > 0 {
				if _, writeErr := w.Write(frame); writeErr != nil {
					return
				}
				if flusher != nil {
					flusher.Flush()
				}
			}
			if readErr != nil {
				break
			}
		}
	}
}

func handleProjectLogsClear(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/logs"
		if r.URL.RawQuery != "" {
			target += "?" + r.URL.RawQuery
		}
		proxyUpstream(w, r, deps, http.MethodDelete, target, nil)
	}
}

// ---------------------------------------------------------------------------
// Database Explorer handlers (F-09 / R-507)
// ---------------------------------------------------------------------------

func handleProjectDBTables(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/db/tables"
		proxyGet(w, r, deps, target)
	}
}

func handleProjectDBTableRows(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		table := r.PathValue("table")
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/db/tables/" + url.PathEscape(table)
		if r.URL.RawQuery != "" {
			target += "?" + r.URL.RawQuery
		}
		proxyGet(w, r, deps, target)
	}
}

func handleProjectDBQuery(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/db/query"
		proxyUpstreamWithin(w, r, deps, http.MethodPost, target, r.Body, defaultPreviewTimeout)
	}
}

func handleProjectDBSchema(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/db/schema"
		proxyGet(w, r, deps, target)
	}
}

// ---------------------------------------------------------------------------
// Security scan & Tests (F-10 / R-508)
// ---------------------------------------------------------------------------

func handleProjectSecurityScan(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/security/scan"
		proxyUpstreamWithin(w, r, deps, http.MethodPost, target, r.Body, defaultBuildTimeout)
	}
}

func handleProjectSecurityGet(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/security"
		proxyGet(w, r, deps, target)
	}
}

func handleProjectTestsRun(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/tests/run"
		proxyUpstreamWithin(w, r, deps, http.MethodPost, target, r.Body, defaultBuildTimeout)
	}
}

func handleProjectTestsGet(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/tests"
		proxyGet(w, r, deps, target)
	}
}

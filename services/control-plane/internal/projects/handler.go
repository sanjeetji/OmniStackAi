package projects

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"math"
	"net/http"
	"net/url"
	"strconv"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/ai"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/skills"
)

const (
	defaultBuildTimeout    = 5 * time.Minute
	defaultPreviewTimeout  = 60 * time.Second
	defaultProblemsTimeout = 90 * time.Second
	defaultProxyTimeout    = 15 * time.Second
)

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
	Logger         *slog.Logger
	HTTPClient     *http.Client
}

func (d Deps) logger() *slog.Logger {
	if d.Logger != nil {
		return d.Logger
	}
	return slog.Default()
}

func (d Deps) httpClient() *http.Client {
	if d.HTTPClient != nil {
		return d.HTTPClient
	}
	return &http.Client{Timeout: defaultProxyTimeout}
}

func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /projects", handleListProjects(deps))
	mux.HandleFunc("POST /projects", handleCreateProject(deps))
	mux.HandleFunc("GET /projects/{id}", handleGetProject(deps))
	mux.HandleFunc("PATCH /projects/{id}", handleUpdateProject(deps))
	mux.HandleFunc("DELETE /projects/{id}", handleDeleteProject(deps))

	mux.HandleFunc("POST /projects/{id}/build/stream", handleProjectBuildStream(deps))
	mux.HandleFunc("POST /projects/{id}/edit", handleProjectEdit(deps))
	mux.HandleFunc("GET /projects/{id}/turns", handleProjectTurns(deps))
	mux.HandleFunc("GET /projects/{id}/files", handleProjectFiles(deps))
	mux.HandleFunc("GET /projects/{id}/file", handleProjectFile(deps))
	mux.HandleFunc("GET /projects/{id}/preview", handleProjectPreviewGet(deps))
	mux.HandleFunc("POST /projects/{id}/preview", handleProjectPreview(deps))
	mux.HandleFunc("POST /projects/{id}/preview/stop", handleProjectPreviewStop(deps))
	mux.HandleFunc("POST /projects/{id}/problems", handleProjectProblemsCheck(deps))
	mux.HandleFunc("GET /projects/{id}/problems", handleProjectProblemsGet(deps))
	mux.HandleFunc("GET /projects/{id}/seo/audit", handleProjectSEOAudit(deps))
	mux.HandleFunc("POST /projects/{id}/seo/audit", handleProjectSEOAudit(deps))
	mux.HandleFunc("PUT /projects/{id}/seo/page", handleProjectSEOPage(deps))
	mux.HandleFunc("POST /projects/{id}/seo/suggest", handleProjectSEOSuggest(deps))

	mux.HandleFunc("POST /projects/{id}/build/cancel", handleProjectBuildCancel(deps))
	mux.HandleFunc("GET /projects/{id}/logs", handleProjectLogs(deps))
	mux.HandleFunc("GET /projects/{id}/logs/stream", handleProjectLogsStream(deps))
	mux.HandleFunc("DELETE /projects/{id}/logs", handleProjectLogsClear(deps))

	// Database Explorer (F-09 / R-507)
	mux.HandleFunc("GET /projects/{id}/db/tables", handleProjectDBTables(deps))
	mux.HandleFunc("GET /projects/{id}/db/tables/{table}", handleProjectDBTableRows(deps))
	mux.HandleFunc("POST /projects/{id}/db/query", handleProjectDBQuery(deps))
	mux.HandleFunc("GET /projects/{id}/db/schema", handleProjectDBSchema(deps))
}

func handleListProjects(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		status := r.URL.Query().Get("status")
		limit := 50
		if lStr := r.URL.Query().Get("limit"); lStr != "" {
			if parsed, err := strconv.Atoi(lStr); err == nil && parsed > 0 {
				limit = parsed
			}
		}

		list, err := deps.ProjectStore.ListProjects(r.Context(), user.ID, status, limit)
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
		}
		if r.Body != nil {
			_ = json.NewDecoder(r.Body).Decode(&req)
		}

		p, err := deps.ProjectStore.CreateProject(r.Context(), user.ID, req.Name, req.Description)
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
				req, reqErr := http.NewRequestWithContext(context.Background(), http.MethodDelete, reqURL, nil)
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
		reqBody, _ := json.Marshal(upstreamPayload)

		upstreamURL := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/build/stream"
		upstreamRequest, err := http.NewRequestWithContext(r.Context(), http.MethodPost, upstreamURL, bytes.NewReader(reqBody))
		if err != nil {
			deps.logger().Error("project build stream agent-engine request", "error", err)
			writeError(w, http.StatusInternalServerError, "could not build upstream request")
			return
		}
		upstreamRequest.Header.Set("Content-Type", "application/json")

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
						req, _ := http.NewRequestWithContext(context.Background(), http.MethodPost, cancelURL, nil)
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
		reqBody, _ := json.Marshal(upstreamPayload)

		targetURL := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/edit"
		upstreamRequest, err := http.NewRequestWithContext(r.Context(), http.MethodPost, targetURL, bytes.NewReader(reqBody))
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
		proxyUpstream(w, r, deps, http.MethodPost, target, nil)
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

func proxyUpstream(w http.ResponseWriter, r *http.Request, deps Deps, method string, targetURL string, body io.Reader) {
	upstreamRequest, err := http.NewRequestWithContext(r.Context(), method, targetURL, body)
	if err != nil {
		deps.logger().Error("build proxy request", "error", err)
		writeError(w, http.StatusInternalServerError, "could not build upstream request")
		return
	}
	if body != nil {
		upstreamRequest.Header.Set("Content-Type", "application/json")
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
	rawCost, ok := usageMap["cost_micros_usd"]
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

func handleProjectSEOSuggest(deps Deps) http.HandlerFunc {
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
		target := deps.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id) + "/seo/suggest"
		proxyUpstream(w, r, deps, http.MethodPost, target, r.Body)
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
		proxyUpstream(w, r, deps, http.MethodPost, target, r.Body)
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

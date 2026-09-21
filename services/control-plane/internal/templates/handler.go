// Package templates serves the template marketplace (Phase T, T-1 / R-519).
//
// A template is a hand-built application kept read-only in the agent-engine's catalogue
// (templates/catalog). "Use template" creates a normal project owned by the caller and has the
// agent-engine copy the template into that project's workspace with its own git history. The
// original never changes, and every later edit touches only the caller's copy.
package templates

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
)

const (
	catalogTimeout     = 15 * time.Second
	instantiateTimeout = 2 * time.Minute
	maxUpstreamBody    = 4 << 20
)

type Deps struct {
	AuthStore      auth.Store
	ProjectStore   projects.Store
	TemplateStore  Store
	AgentEngineURL string
	HTTPClient     *http.Client
	Logger         *slog.Logger
}

func (d Deps) logger() *slog.Logger {
	if d.Logger != nil {
		return d.Logger
	}
	return slog.Default()
}

// httpClient has no overall Timeout: each call carries its own budget in its context (see the
// projects package, R-518).
func (d Deps) httpClient() *http.Client {
	if d.HTTPClient != nil {
		return d.HTTPClient
	}
	return &http.Client{}
}

func Register(mux *http.ServeMux, deps Deps) {
	// The catalogue is public so people can browse templates before they sign up.
	mux.HandleFunc("GET /templates", handleListTemplates(deps))
	mux.HandleFunc("GET /templates/{slug}", handleGetTemplate(deps))
	mux.HandleFunc("POST /templates/{slug}/use", handleUseTemplate(deps))
	mux.HandleFunc("GET /projects/{id}/template", handleProjectTemplate(deps))
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

// callEngine performs one agent-engine request and returns its status and (bounded) body.
func callEngine(ctx context.Context, deps Deps, method, path string, body any, budget time.Duration) (int, []byte, error) {
	ctx, cancel := context.WithTimeout(ctx, budget)
	defer cancel()

	var reader io.Reader
	if body != nil {
		encoded, err := json.Marshal(body)
		if err != nil {
			return 0, nil, err
		}
		reader = bytes.NewReader(encoded)
	}
	request, err := http.NewRequestWithContext(ctx, method, deps.AgentEngineURL+path, reader)
	if err != nil {
		return 0, nil, err
	}
	if body != nil {
		request.Header.Set("Content-Type", "application/json")
	}
	response, err := deps.httpClient().Do(request)
	if err != nil {
		return 0, nil, err
	}
	defer func() { _ = response.Body.Close() }()
	payload, err := io.ReadAll(io.LimitReader(response.Body, maxUpstreamBody))
	if err != nil {
		return 0, nil, err
	}
	return response.StatusCode, payload, nil
}

func relay(w http.ResponseWriter, deps Deps, r *http.Request, path string) {
	status, payload, err := callEngine(r.Context(), deps, http.MethodGet, path, nil, catalogTimeout)
	if err != nil {
		deps.logger().Error("call agent-engine template catalogue", "error", err)
		writeError(w, http.StatusBadGateway, "could not reach the template catalogue")
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, _ = w.Write(payload)
}

func handleListTemplates(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		relay(w, deps, r, "/api/templates")
	}
}

func handleGetTemplate(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		relay(w, deps, r, "/api/templates/"+url.PathEscape(r.PathValue("slug")))
	}
}

type templateDetail struct {
	Name    string `json:"name"`
	Tagline string `json:"tagline"`
}

type instantiateResult struct {
	CommitSHA string          `json:"commit_sha"`
	FileCount int             `json:"file_count"`
	Entities  json.RawMessage `json:"entities"`
	Template  Provenance      `json:"template"`
}

func upstreamError(payload []byte, fallback string) string {
	var body struct {
		Error string `json:"error"`
	}
	if json.Unmarshal(payload, &body) == nil && strings.TrimSpace(body.Error) != "" {
		return body.Error
	}
	return fallback
}

// handleUseTemplate creates the caller's own project from a template. If any step fails after the
// project row exists, the project (and any copied workspace) is removed so no half-made project
// is left in the caller's list.
func handleUseTemplate(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		_ = http.NewResponseController(w).SetWriteDeadline(time.Now().Add(instantiateTimeout + 15*time.Second))

		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		slug := r.PathValue("slug")

		var req struct {
			Name        string `json:"name"`
			WorkspaceID string `json:"workspace_id"`
		}
		if r.Body != nil {
			if err := json.NewDecoder(io.LimitReader(r.Body, 64<<10)).Decode(&req); err != nil && !errors.Is(err, io.EOF) {
				writeError(w, http.StatusBadRequest, "invalid JSON body")
				return
			}
		}

		status, payload, err := callEngine(r.Context(), deps, http.MethodGet, "/api/templates/"+url.PathEscape(slug), nil, catalogTimeout)
		if err != nil {
			deps.logger().Error("look up template", "error", err, "slug", slug)
			writeError(w, http.StatusBadGateway, "could not reach the template catalogue")
			return
		}
		if status == http.StatusNotFound {
			writeError(w, http.StatusNotFound, "template not found")
			return
		}
		var detail templateDetail
		if status != http.StatusOK || json.Unmarshal(payload, &detail) != nil || detail.Name == "" {
			writeError(w, http.StatusBadGateway, "the template catalogue returned an unexpected response")
			return
		}

		name := strings.TrimSpace(req.Name)
		if name == "" {
			name = detail.Name
		}
		project, err := deps.ProjectStore.CreateProjectInWorkspace(r.Context(), user.ID, req.WorkspaceID, name, detail.Tagline)
		if errors.Is(err, projects.ErrUnauthorized) {
			writeError(w, http.StatusForbidden, "you are not a member of that workspace")
			return
		}
		if err != nil {
			deps.logger().Error("create project from template", "error", err, "slug", slug)
			writeError(w, http.StatusInternalServerError, "could not create project")
			return
		}

		// From here on, every failure must remove the project it just created.
		discard := func(purgeWorkspace bool) {
			cleanup := context.Background()
			if err := deps.ProjectStore.DeleteProject(cleanup, project.ID, user.ID); err != nil {
				deps.logger().Error("discard project after failed template use", "error", err, "project_id", project.ID)
			}
			if purgeWorkspace {
				if _, _, err := callEngine(cleanup, deps, http.MethodDelete, "/api/workspaces/"+url.PathEscape(project.ID), nil, catalogTimeout); err != nil {
					deps.logger().Error("purge workspace after failed template use", "error", err, "project_id", project.ID)
				}
			}
		}

		status, payload, err = callEngine(r.Context(), deps, http.MethodPost,
			"/api/workspaces/"+url.PathEscape(project.ID)+"/from-template", map[string]string{"slug": slug}, instantiateTimeout)
		if err != nil || status != http.StatusCreated {
			discard(false)
			if err != nil {
				deps.logger().Error("instantiate template", "error", err, "slug", slug)
				writeError(w, http.StatusBadGateway, "could not reach the build service")
				return
			}
			if status == http.StatusNotFound {
				writeError(w, http.StatusNotFound, "template not found")
				return
			}
			writeError(w, http.StatusBadGateway, upstreamError(payload, "the template could not be copied"))
			return
		}
		var result instantiateResult
		if err := json.Unmarshal(payload, &result); err != nil || result.CommitSHA == "" || result.Template.Slug == "" {
			discard(true)
			writeError(w, http.StatusBadGateway, "the build service returned a malformed response")
			return
		}

		if err := deps.ProjectStore.UpdateProjectBuildResult(r.Context(), project.ID, user.ID, name, "", result.CommitSHA, result.Entities, result.FileCount, 0); err != nil {
			deps.logger().Error("record template project result", "error", err, "project_id", project.ID)
			discard(true)
			writeError(w, http.StatusInternalServerError, "could not save the new project")
			return
		}
		if err := deps.TemplateStore.RecordProjectTemplate(r.Context(), project.ID, result.Template); err != nil {
			deps.logger().Error("record template provenance", "error", err, "project_id", project.ID)
			discard(true)
			writeError(w, http.StatusInternalServerError, "could not save the new project")
			return
		}

		saved, err := deps.ProjectStore.GetProject(r.Context(), project.ID, user.ID)
		if err != nil {
			deps.logger().Error("reload template project", "error", err, "project_id", project.ID)
			saved = project
		}
		provenance, err := deps.TemplateStore.GetProjectTemplate(r.Context(), project.ID)
		if err != nil {
			provenance = result.Template
		}
		writeJSON(w, http.StatusCreated, map[string]any{"project": saved, "template": provenance})
	}
}

func handleProjectTemplate(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), id, user.ID); err != nil {
			if errors.Is(err, projects.ErrProjectNotFound) {
				writeError(w, http.StatusNotFound, "project not found")
				return
			}
			deps.logger().Error("resolve project for template provenance", "error", err)
			writeError(w, http.StatusInternalServerError, "could not load project")
			return
		}
		provenance, err := deps.TemplateStore.GetProjectTemplate(r.Context(), id)
		if errors.Is(err, ErrNotFromTemplate) {
			writeError(w, http.StatusNotFound, "this project was not started from a template")
			return
		}
		if err != nil {
			deps.logger().Error("get template provenance", "error", err)
			writeError(w, http.StatusInternalServerError, "could not load template provenance")
			return
		}
		writeJSON(w, http.StatusOK, provenance)
	}
}

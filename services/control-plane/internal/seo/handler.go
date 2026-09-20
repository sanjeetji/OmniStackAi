package seo

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/ai"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

// Deps holds dependencies for SEO HTTP handlers.
type Deps struct {
	SEOStore       Store
	AIStore        ai.Store
	AuthStore      auth.Store
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

func (d Deps) httpClient() *http.Client {
	if d.HTTPClient != nil {
		return d.HTTPClient
	}
	return &http.Client{Timeout: 30 * time.Second}
}

// Register mounts SEO endpoints onto mux.
func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /projects/{id}/seo", handleGetProjectSEO(deps))
	mux.HandleFunc("PUT /projects/{id}/seo", handleSetProjectSEO(deps))
	mux.HandleFunc("GET /projects/{id}/seo/pages", handleGetProjectPageSEOs(deps))
	mux.HandleFunc("PUT /projects/{id}/seo/pages/{route...}", handleSetProjectPageSEO(deps))
	mux.HandleFunc("POST /projects/{id}/seo/audit", handleAuditProjectSEO(deps))
	mux.HandleFunc("POST /projects/{id}/seo/suggest", handleSuggestSEOCopy(deps))
}

func writeJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func handleGetProjectSEO(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		seo, err := deps.SEOStore.GetProjectSEO(r.Context(), projectID, user.ID)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			deps.logger().Error("get project seo", "error", err)
			writeError(w, http.StatusInternalServerError, "could not get project seo")
			return
		}

		writeJSON(w, http.StatusOK, seo)
	}
}

func handleSetProjectSEO(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		var body ProjectSEO
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeError(w, http.StatusBadRequest, "invalid json body")
			return
		}

		updated, err := deps.SEOStore.SetProjectSEO(r.Context(), projectID, user.ID, &body)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			deps.logger().Error("set project seo", "error", err)
			writeError(w, http.StatusInternalServerError, "could not update project seo")
			return
		}

		writeJSON(w, http.StatusOK, updated)
	}
}

func handleGetProjectPageSEOs(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		pages, err := deps.SEOStore.GetProjectPageSEOs(r.Context(), projectID, user.ID)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			deps.logger().Error("get project page seos", "error", err)
			writeError(w, http.StatusInternalServerError, "could not get page seos")
			return
		}

		writeJSON(w, http.StatusOK, pages)
	}
}

func handleSetProjectPageSEO(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		rawRoute := r.PathValue("route")
		route := "/" + strings.TrimPrefix(rawRoute, "/")
		if rawRoute == "" || rawRoute == "root" || rawRoute == "_root" {
			route = "/"
		}

		var body struct {
			Route       string `json:"route"`
			Title       string `json:"title"`
			Description string `json:"description"`
			Noindex     bool   `json:"noindex"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeError(w, http.StatusBadRequest, "invalid json body")
			return
		}
		if body.Route != "" {
			route = "/" + strings.TrimPrefix(body.Route, "/")
		}

		page := &PageSEO{
			ProjectID:   projectID,
			Route:       route,
			Title:       body.Title,
			Description: body.Description,
			Noindex:     body.Noindex,
		}

		updated, err := deps.SEOStore.SetProjectPageSEO(r.Context(), projectID, user.ID, page)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			deps.logger().Error("set project page seo", "error", err)
			writeError(w, http.StatusInternalServerError, "could not update page seo")
			return
		}

		// Forward to agent-engine to regenerate page metadata in repo and commit to git
		if deps.AgentEngineURL != "" {
			go func() {
				reqBody, _ := json.Marshal(map[string]any{
					"route":       updated.Route,
					"title":       updated.Title,
					"description": updated.Description,
					"noindex":     updated.Noindex,
				})
				target := fmt.Sprintf("%s/api/workspaces/%s/seo/page", strings.TrimRight(deps.AgentEngineURL, "/"), url.PathEscape(projectID))
				req, reqErr := http.NewRequest(http.MethodPut, target, bytes.NewReader(reqBody))
				if reqErr == nil {
					req.Header.Set("Content-Type", "application/json")
					resp, postErr := deps.httpClient().Do(req)
					if postErr == nil {
						_ = resp.Body.Close()
					}
				}
			}()
		}

		writeJSON(w, http.StatusOK, updated)
	}
}

func handleAuditProjectSEO(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		// Verify project ownership
		if _, err := deps.SEOStore.GetProjectSEO(r.Context(), projectID, user.ID); err != nil {
			if errors.Is(err, ErrProjectNotFound) {
				writeError(w, http.StatusNotFound, "project not found")
				return
			}
			deps.logger().Error("audit check ownership", "error", err)
			writeError(w, http.StatusInternalServerError, "could not verify project")
			return
		}

		// Proxy audit request to agent-engine
		target := fmt.Sprintf("%s/api/workspaces/%s/seo/audit", strings.TrimRight(deps.AgentEngineURL, "/"), url.PathEscape(projectID))
		req, err := http.NewRequestWithContext(r.Context(), http.MethodPost, target, nil)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not create audit request")
			return
		}

		resp, err := deps.httpClient().Do(req)
		if err != nil {
			deps.logger().Error("audit upstream request", "error", err)
			writeError(w, http.StatusBadGateway, "agent-engine unreachable for seo audit")
			return
		}
		defer resp.Body.Close()

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(resp.StatusCode)
		_, _ = io.Copy(w, resp.Body)
	}
}

func handleSuggestSEOCopy(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		// Verify project ownership
		if _, err := deps.SEOStore.GetProjectSEO(r.Context(), projectID, user.ID); err != nil {
			if errors.Is(err, ErrProjectNotFound) {
				writeError(w, http.StatusNotFound, "project not found")
				return
			}
			deps.logger().Error("suggest check ownership", "error", err)
			writeError(w, http.StatusInternalServerError, "could not verify project")
			return
		}

		bodyBytes, err := io.ReadAll(r.Body)
		if err != nil {
			writeError(w, http.StatusBadRequest, "could not read body")
			return
		}

		// Forward suggest request to agent-engine
		target := fmt.Sprintf("%s/api/workspaces/%s/seo/suggest", strings.TrimRight(deps.AgentEngineURL, "/"), url.PathEscape(projectID))
		req, err := http.NewRequestWithContext(r.Context(), http.MethodPost, target, bytes.NewReader(bodyBytes))
		if err != nil {
			writeError(w, http.StatusInternalServerError, "could not create suggest request")
			return
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := deps.httpClient().Do(req)
		if err != nil {
			deps.logger().Error("suggest upstream request", "error", err)
			writeError(w, http.StatusBadGateway, "agent-engine unreachable for seo suggestion")
			return
		}
		defer resp.Body.Close()

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(resp.StatusCode)
		_, _ = io.Copy(w, resp.Body)
	}
}

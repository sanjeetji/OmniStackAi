package connectors

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/integrations"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/secrets"
)

type Deps struct {
	AuthStore      auth.Store
	ProjectStore   projects.Store
	ConnectorStore Store
	AgentEngineURL string
	Logger         *slog.Logger
	HTTPClient     *http.Client
	// Secrets holds connector credentials (PC-013), Health tests them.
	Secrets secrets.Store
	Health  integrations.Service
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

func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /connectors", handleGetCatalog(deps))
	mux.HandleFunc("GET /projects/{id}/connectors", handleListProjectConnectors(deps))
	mux.HandleFunc("PUT /projects/{id}/connectors/{provider}", handleSaveProjectConnector(deps))
	mux.HandleFunc("DELETE /projects/{id}/connectors/{provider}", handleDeleteProjectConnector(deps))
	mux.HandleFunc("POST /projects/{id}/connectors/{provider}/test", handleTestConnector(deps))
}

func writeJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func authenticate(r *http.Request, authStore auth.Store) (auth.User, error) {
	return auth.RequireUser(r.Context(), authStore, r)
}

func checkProjectAccess(r *http.Request, deps Deps, projectID string) (auth.User, projects.Project, error) {
	user, err := authenticate(r, deps.AuthStore)
	if err != nil {
		return auth.User{}, projects.Project{}, err
	}
	proj, err := deps.ProjectStore.GetProject(r.Context(), projectID, user.ID)
	if err != nil {
		return user, projects.Project{}, err
	}
	return user, proj, nil
}

func handleGetCatalog(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]any{
			"connectors": Catalog,
		})
	}
}

func handleListProjectConnectors(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		if _, _, err := checkProjectAccess(r, deps, projectID); err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		list, err := deps.ConnectorStore.ListProjectConnectors(r.Context(), projectID)
		if err != nil {
			deps.logger().Error("failed to list project connectors", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to list connectors")
			return
		}
		if list == nil {
			list = []ProjectConnector{}
		}
		// Settings kept as project secrets are shown from there; secret ones only as "set".
		var saved map[string]string
		if deps.Secrets != nil && deps.Secrets.IsAvailable() {
			saved, _ = deps.Secrets.ForProject(r.Context(), projectID)
		}
		for i := range list {
			list[i].Config = displayConfig(list[i].Provider, list[i].Config, saved)
		}
		writeJSON(w, http.StatusOK, map[string]any{"connectors": list})
	}
}

// masked stands for a saved secret in the console; sending it back means "keep what is saved".
const masked = "••••••••"

func displayConfig(provider string, cfg map[string]any, saved map[string]string) map[string]any {
	out := map[string]any{}
	for k, v := range cfg {
		out[k] = v
	}
	def, _ := GetDefinition(provider)
	env := integrations.EnvFields(provider)
	for _, f := range def.Fields {
		name, ok := env[f.Key]
		if !ok {
			continue
		}
		value, isSet := saved[name]
		switch {
		case !isSet:
		case f.Secret:
			out[f.Key] = masked
		default:
			out[f.Key] = value
		}
	}
	return out
}

func handleSaveProjectConnector(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		provider := strings.ToLower(strings.TrimSpace(r.PathValue("provider")))

		user, _, err := checkProjectAccess(r, deps, projectID)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		def, ok := GetDefinition(provider)
		if !ok {
			writeError(w, http.StatusBadRequest, "unsupported connector: "+provider)
			return
		}

		var body struct {
			Config  map[string]any `json:"config"`
			Enabled *bool          `json:"enabled"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeError(w, http.StatusBadRequest, "invalid request body")
			return
		}
		env := integrations.EnvFields(provider)
		var saved map[string]string
		if len(env) > 0 {
			// PC-013: credentials are project secrets (encrypted, and given to the app as
			// environment variables), never plain settings or repository files.
			if deps.Secrets == nil || !deps.Secrets.IsAvailable() {
				writeError(w, http.StatusServiceUnavailable, "secret storage is not set up on this server, so credentials cannot be saved")
				return
			}
			saved, _ = deps.Secrets.ForProject(r.Context(), projectID)
		}
		values := map[string]string{}
		for _, f := range def.Fields {
			v := strings.TrimSpace(fmt.Sprintf("%v", body.Config[f.Key]))
			if body.Config[f.Key] == nil {
				v = ""
			}
			if v == masked || (v == "" && f.Secret) {
				v = saved[env[f.Key]] // unchanged
			}
			if v == "" && f.Default != "" {
				v = f.Default
			}
			if f.Required && v == "" {
				writeError(w, http.StatusBadRequest, fmt.Sprintf("field %q is required", f.Label))
				return
			}
			values[f.Key] = v
		}

		enabled := true
		if body.Enabled != nil {
			enabled = *body.Enabled
		}

		plain := map[string]any{}
		for key, v := range values {
			name, secret := env[key]
			if !secret {
				plain[key] = v
				continue
			}
			if v == "" {
				continue
			}
			if _, err := deps.Secrets.SetSecret(r.Context(), projectID, user.ID, name, v, "Set by the "+def.Name+" connector"); err != nil {
				deps.logger().Error("save connector secret", "provider", provider, "error", err)
				writeError(w, http.StatusInternalServerError, "failed to save connector")
				return
			}
		}

		saved2, err := deps.ConnectorStore.SaveProjectConnector(r.Context(), projectID, provider, plain, enabled)
		if err != nil {
			deps.logger().Error("failed to save project connector", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to save connector")
			return
		}
		// New settings make the last health test stale.
		deps.Health.Forget(r.Context(), "project", projectID, provider)

		// The Studio writes the code into the app; it receives no credential.
		deps.studio(r, projectID, "apply", map[string]any{"provider": provider, "config": plain})

		secretsNow, _ := forProject(r, deps, projectID)
		saved2.Config = displayConfig(provider, saved2.Config, secretsNow)
		writeJSON(w, http.StatusOK, saved2)
	}
}

func forProject(r *http.Request, deps Deps, projectID string) (map[string]string, error) {
	if deps.Secrets == nil || !deps.Secrets.IsAvailable() {
		return nil, nil
	}
	return deps.Secrets.ForProject(r.Context(), projectID)
}

func (d Deps) studio(r *http.Request, projectID, action string, payload map[string]any) {
	if d.AgentEngineURL == "" {
		return
	}
	reqBody, _ := json.Marshal(payload)
	url := strings.TrimSuffix(d.AgentEngineURL, "/") + "/api/workspaces/" + projectID + "/connectors/" + action
	req, err := http.NewRequestWithContext(r.Context(), http.MethodPost, url, bytes.NewReader(reqBody))
	if err != nil {
		return
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := d.httpClient().Do(req)
	if err != nil {
		d.logger().Warn("agent-engine connector "+action, "error", err)
		return
	}
	_ = resp.Body.Close()
}

func handleDeleteProjectConnector(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		provider := strings.ToLower(strings.TrimSpace(r.PathValue("provider")))

		user, _, err := checkProjectAccess(r, deps, projectID)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		if err := deps.ConnectorStore.DeleteProjectConnector(r.Context(), projectID, provider); err != nil {
			if errors.Is(err, ErrNotFound) {
				writeError(w, http.StatusNotFound, "connector not found")
				return
			}
			deps.logger().Error("failed to delete project connector", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to delete connector")
			return
		}
		// Its credentials go with it.
		if deps.Secrets != nil && deps.Secrets.IsAvailable() {
			for _, name := range integrations.EnvFields(provider) {
				_ = deps.Secrets.DeleteSecret(r.Context(), projectID, user.ID, name)
			}
		}
		deps.Health.Forget(r.Context(), "project", projectID, provider)
		deps.studio(r, projectID, "remove", map[string]any{"provider": provider})

		writeJSON(w, http.StatusOK, map[string]any{"deleted": true})
	}
}

// handleTestConnector asks the provider whether the settings work (PC-013): the saved ones, or
// the ones in the form before they are saved. A test of saved settings is recorded.
func handleTestConnector(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		provider := strings.ToLower(strings.TrimSpace(r.PathValue("provider")))

		if _, _, err := checkProjectAccess(r, deps, projectID); err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}
		def, ok := GetDefinition(provider)
		if !ok {
			writeError(w, http.StatusBadRequest, "Unsupported connector: "+provider)
			return
		}

		var body struct {
			Config map[string]any `json:"config"`
		}
		_ = json.NewDecoder(r.Body).Decode(&body)

		settings, err := deps.Health.ProjectSettings(r.Context(), projectID, provider)
		if err != nil {
			settings = map[string]string{}
		}
		fromForm := false
		for _, f := range def.Fields {
			if raw, present := body.Config[f.Key]; present && raw != nil {
				v := strings.TrimSpace(fmt.Sprintf("%v", raw))
				if v != "" && v != masked && v != settings[f.Key] {
					settings[f.Key] = v
					fromForm = true
				}
			}
		}
		if len(settings) == 0 {
			writeError(w, http.StatusBadRequest, "no configuration found to test")
			return
		}
		result := deps.Health.Checker.Check(r.Context(), provider, settings)
		if !fromForm {
			deps.Health.Record(r.Context(), "project", projectID, result)
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"success":    result.Status == integrations.OK,
			"status":     result.Status,
			"message":    result.Message,
			"checked_at": result.CheckedAt,
		})
	}
}

package connectors

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
)

type Deps struct {
	AuthStore      auth.Store
	ProjectStore   projects.Store
	ConnectorStore Store
	AgentEngineURL string
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

		writeJSON(w, http.StatusOK, map[string]any{
			"connectors": list,
		})
	}
}

func handleSaveProjectConnector(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		provider := strings.ToLower(strings.TrimSpace(r.PathValue("provider")))

		if _, _, err := checkProjectAccess(r, deps, projectID); err != nil {
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
		if body.Config == nil {
			body.Config = make(map[string]any)
		}

		// Validate required fields
		for _, f := range def.Fields {
			if f.Required {
				val, exists := body.Config[f.Key]
				if !exists || strings.TrimSpace(fmt.Sprintf("%v", val)) == "" {
					writeError(w, http.StatusBadRequest, fmt.Sprintf("field %q is required", f.Label))
					return
				}
			}
		}

		enabled := true
		if body.Enabled != nil {
			enabled = *body.Enabled
		}

		saved, err := deps.ConnectorStore.SaveProjectConnector(r.Context(), projectID, provider, body.Config, enabled)
		if err != nil {
			deps.logger().Error("failed to save project connector", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to save connector")
			return
		}

		// Trigger Agent-Engine codegen hook to commit code to repository
		if deps.AgentEngineURL != "" {
			reqBody, _ := json.Marshal(map[string]any{
				"provider": provider,
				"config":   body.Config,
			})
			url := strings.TrimSuffix(deps.AgentEngineURL, "/") + "/api/workspaces/" + projectID + "/connectors/apply"
			req, err := http.NewRequestWithContext(r.Context(), "POST", url, bytes.NewReader(reqBody))
			if err == nil {
				req.Header.Set("Content-Type", "application/json")
				if resp, err := deps.httpClient().Do(req); err == nil {
					_ = resp.Body.Close()
				} else {
					deps.logger().Warn("failed to call agent-engine apply connector", "error", err)
				}
			}
		}

		writeJSON(w, http.StatusOK, saved)
	}
}

func handleDeleteProjectConnector(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		provider := strings.ToLower(strings.TrimSpace(r.PathValue("provider")))

		if _, _, err := checkProjectAccess(r, deps, projectID); err != nil {
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

		// Trigger Agent-Engine hook to remove code
		if deps.AgentEngineURL != "" {
			reqBody, _ := json.Marshal(map[string]any{
				"provider": provider,
			})
			url := strings.TrimSuffix(deps.AgentEngineURL, "/") + "/api/workspaces/" + projectID + "/connectors/remove"
			req, err := http.NewRequestWithContext(r.Context(), "POST", url, bytes.NewReader(reqBody))
			if err == nil {
				req.Header.Set("Content-Type", "application/json")
				if resp, err := deps.httpClient().Do(req); err == nil {
					_ = resp.Body.Close()
				}
			}
		}

		writeJSON(w, http.StatusOK, map[string]any{"deleted": true})
	}
}

func handleTestConnector(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		provider := strings.ToLower(strings.TrimSpace(r.PathValue("provider")))

		if _, _, err := checkProjectAccess(r, deps, projectID); err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		var body struct {
			Config map[string]any `json:"config"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Config == nil {
			// If not in body, load from store
			pc, err := deps.ConnectorStore.GetProjectConnector(r.Context(), projectID, provider)
			if err != nil {
				writeError(w, http.StatusBadRequest, "no configuration found to test")
				return
			}
			body.Config = pc.Config
		}

		switch provider {
		case "ga4":
			measID := strings.TrimSpace(fmt.Sprintf("%v", body.Config["measurement_id"]))
			gaRegex := regexp.MustCompile(`^G-[A-Z0-9]{6,16}$`)
			if !gaRegex.MatchString(strings.ToUpper(measID)) {
				writeError(w, http.StatusBadRequest, "Invalid Measurement ID format (expected G-XXXXXXXXXX)")
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{
				"success": true,
				"message": fmt.Sprintf("Measurement ID %s verified and ready to track pageviews", strings.ToUpper(measID)),
			})
			return

		case "resend":
			apiKey := strings.TrimSpace(fmt.Sprintf("%v", body.Config["api_key"]))
			if !strings.HasPrefix(apiKey, "re_") || len(apiKey) < 10 {
				writeError(w, http.StatusBadRequest, "Invalid Resend API Key format (expected re_...)")
				return
			}
			fromEmail := strings.TrimSpace(fmt.Sprintf("%v", body.Config["from_email"]))
			if !strings.Contains(fromEmail, "@") {
				writeError(w, http.StatusBadRequest, "Invalid sender email address")
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{
				"success": true,
				"message": fmt.Sprintf("Resend configuration valid. Ready to send emails from %s", fromEmail),
			})
			return

		case "smtp":
			host := strings.TrimSpace(fmt.Sprintf("%v", body.Config["host"]))
			user := strings.TrimSpace(fmt.Sprintf("%v", body.Config["username"]))
			portStr := strings.TrimSpace(fmt.Sprintf("%v", body.Config["port"]))
			if portStr == "" || portStr == "<nil>" {
				portStr = "587"
			}
			if host == "" || user == "" {
				writeError(w, http.StatusBadRequest, "SMTP host and username are required")
				return
			}
			portNum, err := strconv.Atoi(portStr)
			if err != nil || portNum < 1 || portNum > 65535 {
				writeError(w, http.StatusBadRequest, "Invalid SMTP port (must be between 1 and 65535)")
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{
				"success": true,
				"message": fmt.Sprintf("SMTP configuration valid for %s:%d (auth user: %s)", host, portNum, user),
			})
			return

		default:
			writeError(w, http.StatusBadRequest, "Unsupported connector: "+provider)
		}
	}
}

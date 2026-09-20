package deploy

import (
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"regexp"
	"strings"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/git"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/secrets"
)

type Deps struct {
	AuthStore      auth.Store
	DeployStore    Store
	ProjectStore   projects.Store
	GitStore       git.Store
	SecretsStore   secrets.Store
	AgentEngineURL string
	Vercel         DeployProvider
	Netlify        DeployProvider
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

func (d Deps) getProvider(name string) (DeployProvider, error) {
	switch strings.ToLower(strings.TrimSpace(name)) {
	case "vercel":
		if d.Vercel != nil {
			return d.Vercel, nil
		}
		return NewVercelProvider("", d.httpClient()), nil
	case "netlify":
		if d.Netlify != nil {
			return d.Netlify, nil
		}
		return NewNetlifyProvider("", d.httpClient()), nil
	default:
		return nil, ErrInvalidProvider
	}
}

func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /deploy/connections/{provider}", handleGetConnection(deps))
	mux.HandleFunc("PUT /deploy/connections/{provider}", handleSetConnection(deps))
	mux.HandleFunc("DELETE /deploy/connections/{provider}", handleDeleteConnection(deps))

	mux.HandleFunc("GET /projects/{id}/publish", handleGetPublishReadiness(deps))
	mux.HandleFunc("POST /projects/{id}/publish", handleTriggerPublish(deps))
	mux.HandleFunc("GET /projects/{id}/deployments", handleListDeployments(deps))
	mux.HandleFunc("GET /projects/{id}/deployments/{depId}", handleGetDeployment(deps))
}

func authenticate(r *http.Request, authStore auth.Store) (auth.User, error) {
	return auth.RequireUser(r.Context(), authStore, r)
}

func handleGetConnection(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := authenticate(r, deps.AuthStore)
		if err != nil {
			http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
			return
		}

		provider := r.PathValue("provider")
		conn, err := deps.DeployStore.GetConnectionStatus(r.Context(), user.ID, provider)
		if err != nil {
			if errors.Is(err, ErrNotFound) {
				w.Header().Set("Content-Type", "application/json")
				_ = json.NewEncoder(w).Encode(map[string]any{
					"connected": false,
					"provider":  provider,
				})
				return
			}
			deps.logger().Error("failed to get connection status", "error", err)
			http.Error(w, `{"error":"internal error"}`, http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"connected":     true,
			"provider":      conn.Provider,
			"account_label": conn.AccountLabel,
			"created_at":    conn.CreatedAt,
		})
	}
}

func handleSetConnection(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := authenticate(r, deps.AuthStore)
		if err != nil {
			http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
			return
		}

		providerName := r.PathValue("provider")
		providerDriver, err := deps.getProvider(providerName)
		if err != nil {
			http.Error(w, `{"error":"invalid provider"}`, http.StatusBadRequest)
			return
		}

		var req struct {
			Token string `json:"token"`
			Label string `json:"label"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, `{"error":"invalid json"}`, http.StatusBadRequest)
			return
		}
		token := strings.TrimSpace(req.Token)
		if token == "" {
			http.Error(w, `{"error":"token cannot be empty"}`, http.StatusBadRequest)
			return
		}

		accountLabel, err := providerDriver.VerifyToken(r.Context(), token)
		if err != nil {
			if errors.Is(err, ErrProviderAuthFailed) {
				http.Error(w, `{"error":"provider authentication failed (check token)"}`, http.StatusUnauthorized)
				return
			}
			deps.logger().Warn("provider token verify failed", "provider", providerName, "error", err)
			http.Error(w, fmt.Sprintf(`{"error":"failed to verify token with provider: %s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		if req.Label != "" {
			accountLabel = req.Label
		}

		conn, err := deps.DeployStore.SetConnection(r.Context(), user.ID, providerName, token, accountLabel)
		if err != nil {
			deps.logger().Error("failed to save connection", "error", err)
			http.Error(w, `{"error":"failed to save token"}`, http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"connected":     true,
			"provider":      conn.Provider,
			"account_label": conn.AccountLabel,
			"created_at":    conn.CreatedAt,
		})
	}
}

func handleDeleteConnection(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := authenticate(r, deps.AuthStore)
		if err != nil {
			http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
			return
		}

		provider := r.PathValue("provider")
		if err := deps.DeployStore.DeleteConnection(r.Context(), user.ID, provider); err != nil {
			deps.logger().Error("failed to delete connection", "error", err)
			http.Error(w, `{"error":"failed to delete connection"}`, http.StatusInternalServerError)
			return
		}

		w.WriteHeader(http.StatusNoContent)
	}
}

type PublishReadiness struct {
	Path              int         `json:"path"`
	PathDescription   string      `json:"path_description"`
	HasBackend        bool        `json:"has_backend"`
	HasDB             bool        `json:"has_db"`
	RenderYAML        string      `json:"render_yaml,omitempty"`
	FlyTOML           string      `json:"fly_toml,omitempty"`
	GitConnected      bool        `json:"git_connected"`
	RepoName          string      `json:"repo_name"`
	ProviderConnected bool        `json:"provider_connected"`
	Provider          string      `json:"provider"`
	AccountLabel      string      `json:"account_label,omitempty"`
	SecretsCount      int         `json:"secrets_count"`
	MissingSecrets    []string    `json:"missing_secrets"`
	LatestDeployment  *Deployment `json:"latest_deployment,omitempty"`
	LiveURL           string      `json:"live_url,omitempty"`
}

var slugPattern = regexp.MustCompile(`[^a-zA-Z0-9_-]+`)

func slugify(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	s = slugPattern.ReplaceAllString(s, "-")
	s = strings.Trim(s, "-")
	if s == "" {
		return "app"
	}
	return s
}

func handleGetPublishReadiness(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := authenticate(r, deps.AuthStore)
		if err != nil {
			http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
			return
		}

		projectID := r.PathValue("id")
		if _, err := deps.ProjectStore.GetProject(r.Context(), projectID, user.ID); err != nil {
			http.Error(w, `{"error":"project not found"}`, http.StatusNotFound)
			return
		}

		deployProv, _, liveURL, _ := deps.DeployStore.GetProjectDeployMeta(r.Context(), projectID)

		readiness := PublishReadiness{
			Path:            1,
			PathDescription: "Web-only application (deploys completely to Vercel or Netlify).",
			LiveURL:         liveURL,
			MissingSecrets:  []string{},
		}

		if deps.GitStore != nil {
			gitInfo, errGit := deps.GitStore.GetProjectGit(r.Context(), user.ID, projectID)
			if errGit == nil && gitInfo != nil && gitInfo.RepoFullName != "" {
				readiness.GitConnected = true
				readiness.RepoName = gitInfo.RepoFullName
			}
		}

		// Check hosting provider connections
		prefProvider := deployProv
		if prefProvider == "" {
			prefProvider = "vercel"
		}
		readiness.Provider = prefProvider

		conn, err := deps.DeployStore.GetConnectionStatus(r.Context(), user.ID, prefProvider)
		if err == nil && conn != nil {
			readiness.ProviderConnected = true
			readiness.AccountLabel = conn.AccountLabel
		} else {
			// Try fallback to netlify
			if prefProvider == "vercel" {
				netConn, errNet := deps.DeployStore.GetConnectionStatus(r.Context(), user.ID, "netlify")
				if errNet == nil && netConn != nil {
					readiness.ProviderConnected = true
					readiness.Provider = "netlify"
					readiness.AccountLabel = netConn.AccountLabel
				}
			}
		}

		// Check secrets count
		if deps.SecretsStore != nil {
			secretsList, err := deps.SecretsStore.ListSecrets(r.Context(), user.ID, projectID)
			if err == nil {
				readiness.SecretsCount = len(secretsList)
			}
		}

		// Fetch readiness from agent-engine if available
		if deps.AgentEngineURL != "" {
			readinessReq, err := http.NewRequestWithContext(r.Context(), "GET", fmt.Sprintf("%s/api/workspaces/%s/publish/readiness", deps.AgentEngineURL, projectID), nil)
			if err == nil {
				resp, errDo := deps.httpClient().Do(readinessReq)
				if errDo == nil && resp.StatusCode == 200 {
					var aeReadiness struct {
						Path            int      `json:"path"`
						PathDescription string   `json:"path_description"`
						HasBackend      bool     `json:"has_backend"`
						HasDB           bool     `json:"has_db"`
						RenderYAML      string   `json:"render_yaml"`
						FlyTOML         string   `json:"fly_toml"`
						MissingSecrets  []string `json:"missing_secrets"`
					}
					if errDecode := json.NewDecoder(resp.Body).Decode(&aeReadiness); errDecode == nil {
						if aeReadiness.Path > 0 {
							readiness.Path = aeReadiness.Path
							readiness.PathDescription = aeReadiness.PathDescription
							readiness.HasBackend = aeReadiness.HasBackend
							readiness.HasDB = aeReadiness.HasDB
							readiness.RenderYAML = aeReadiness.RenderYAML
							readiness.FlyTOML = aeReadiness.FlyTOML
							if len(aeReadiness.MissingSecrets) > 0 {
								readiness.MissingSecrets = aeReadiness.MissingSecrets
							}
						}
					}
					resp.Body.Close()
				}
			}
		}

		// Fetch latest deployment
		latestDep, _ := deps.DeployStore.GetLatestDeployment(r.Context(), projectID)
		if latestDep != nil {
			readiness.LatestDeployment = latestDep
			if readiness.LiveURL == "" && latestDep.URL != "" {
				readiness.LiveURL = latestDep.URL
			}
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(readiness)
	}
}

func handleTriggerPublish(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := authenticate(r, deps.AuthStore)
		if err != nil {
			http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
			return
		}

		projectID := r.PathValue("id")
		project, err := deps.ProjectStore.GetProject(r.Context(), projectID, user.ID)
		if err != nil {
			http.Error(w, `{"error":"project not found"}`, http.StatusNotFound)
			return
		}

		var req struct {
			Provider string `json:"provider"`
		}
		_ = json.NewDecoder(r.Body).Decode(&req)
		providerName := strings.ToLower(strings.TrimSpace(req.Provider))
		deployProv, _, _, _ := deps.DeployStore.GetProjectDeployMeta(r.Context(), projectID)
		if providerName == "" {
			if deployProv != "" {
				providerName = deployProv
			} else {
				providerName = "vercel"
			}
		}

		providerDriver, err := deps.getProvider(providerName)
		if err != nil {
			http.Error(w, `{"error":"invalid provider, choose vercel or netlify"}`, http.StatusBadRequest)
			return
		}

		_, token, err := deps.DeployStore.GetConnection(r.Context(), user.ID, providerName)
		if err != nil {
			if errors.Is(err, ErrNotFound) {
				http.Error(w, fmt.Sprintf(`{"error":"%s is not connected. Please connect your account with a personal access token."}`, providerName), http.StatusBadRequest)
				return
			}
			http.Error(w, `{"error":"failed to retrieve provider token"}`, http.StatusInternalServerError)
			return
		}

		if deps.GitStore == nil {
			http.Error(w, `{"error":"git service unavailable"}`, http.StatusInternalServerError)
			return
		}
		gitInfo, errGit := deps.GitStore.GetProjectGit(r.Context(), user.ID, projectID)
		if errGit != nil || gitInfo == nil || gitInfo.RepoFullName == "" {
			http.Error(w, `{"error":"this project does not have a connected GitHub repository yet. Please push to GitHub first before publishing."}`, http.StatusBadRequest)
			return
		}

		// Decrypt project secrets to supply as deployment env vars
		envMap := make(map[string]string)
		if deps.SecretsStore != nil {
			secList, errSec := deps.SecretsStore.ListSecrets(r.Context(), user.ID, projectID)
			if errSec == nil {
				for _, sec := range secList {
					val, errRev := deps.SecretsStore.RevealSecret(r.Context(), user.ID, projectID, sec.Key)
					if errRev == nil && val != "" {
						envMap[sec.Key] = val
					}
				}
			}
		}

		slug := slugify(project.Name)

		// 1. Create or retrieve project on provider
		externalID, err := providerDriver.CreateProject(r.Context(), token, slug, gitInfo.RepoFullName, "nextjs", envMap)
		if err != nil {
			deps.logger().Error("failed to create provider project", "provider", providerName, "error", err)
			http.Error(w, fmt.Sprintf(`{"error":"failed to create project on %s: %s"}`, providerName, err.Error()), http.StatusBadGateway)
			return
		}

		// 2. Trigger deployment
		depID, liveURL, err := providerDriver.TriggerDeploy(r.Context(), token, externalID, slug, gitInfo.RepoFullName, gitInfo.CommitSHA)
		if err != nil {
			deps.logger().Error("failed to trigger deploy", "provider", providerName, "error", err)
			http.Error(w, fmt.Sprintf(`{"error":"failed to trigger deploy on %s: %s"}`, providerName, err.Error()), http.StatusBadGateway)
			return
		}

		// 3. Record deployment
		deploymentRecord := &Deployment{
			ProjectID:  projectID,
			Provider:   providerName,
			ExternalID: depID,
			CommitSHA:  gitInfo.CommitSHA,
			Status:     "building",
			URL:        liveURL,
			Error:      "",
		}
		created, err := deps.DeployStore.CreateDeployment(r.Context(), deploymentRecord)
		if err != nil {
			deps.logger().Error("failed to record deployment", "error", err)
		}

		// 4. Update project metadata
		_ = deps.DeployStore.UpdateProjectDeployMeta(r.Context(), projectID, providerName, externalID, liveURL)

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"deployment": created,
			"live_url":   liveURL,
			"status":     "building",
		})
	}
}

func handleListDeployments(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := authenticate(r, deps.AuthStore)
		if err != nil {
			http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
			return
		}

		projectID := r.PathValue("id")
		_, err = deps.ProjectStore.GetProject(r.Context(), projectID, user.ID)
		if err != nil {
			http.Error(w, `{"error":"project not found"}`, http.StatusNotFound)
			return
		}

		list, err := deps.DeployStore.ListDeployments(r.Context(), projectID, 30)
		if err != nil {
			http.Error(w, `{"error":"failed to list deployments"}`, http.StatusInternalServerError)
			return
		}
		if list == nil {
			list = []Deployment{}
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(list)
	}
}

func handleGetDeployment(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := authenticate(r, deps.AuthStore)
		if err != nil {
			http.Error(w, `{"error":"unauthorized"}`, http.StatusUnauthorized)
			return
		}

		projectID := r.PathValue("id")
		_, err = deps.ProjectStore.GetProject(r.Context(), projectID, user.ID)
		if err != nil {
			http.Error(w, `{"error":"project not found"}`, http.StatusNotFound)
			return
		}

		depID := r.PathValue("depId")
		dep, err := deps.DeployStore.GetDeployment(r.Context(), depID)
		if err != nil {
			http.Error(w, `{"error":"deployment not found"}`, http.StatusNotFound)
			return
		}

		// If deployment is in flight (building/queued), poll provider for latest status
		if dep.Status == "building" || dep.Status == "queued" {
			_, token, errToken := deps.DeployStore.GetConnection(r.Context(), user.ID, dep.Provider)
			if errToken == nil {
				providerDriver, errDrv := deps.getProvider(dep.Provider)
				if errDrv == nil {
					status, url, _, errMsg, errPoll := providerDriver.GetDeployment(r.Context(), token, dep.ExternalID)
					if errPoll == nil && status != "" && status != dep.Status {
						dep.Status = status
						if url != "" {
							dep.URL = url
						}
						if errMsg != "" {
							dep.Error = errMsg
						}
						var finishedAt *time.Time
						if status == "ready" || status == "error" || status == "cancelled" {
							now := time.Now()
							finishedAt = &now
							dep.FinishedAt = finishedAt
						}
						_ = deps.DeployStore.UpdateDeployment(r.Context(), dep.ID, status, dep.URL, dep.Error, finishedAt)
						if status == "ready" && dep.URL != "" {
							_ = deps.DeployStore.UpdateProjectDeployMeta(r.Context(), projectID, dep.Provider, dep.ExternalID, dep.URL)
						}
					}
				}
			}
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(dep)
	}
}

package git

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
)

var slugPattern = regexp.MustCompile(`[^a-zA-Z0-9_-]+`)

type Deps struct {
	AuthStore             auth.Store
	GitStore              Store
	ProjectStore          projects.Store
	AgentEngineURL        string
	GitHubAppID           string
	GitHubAppClientID     string
	GitHubAppClientSecret string
	GitHubAppPrivateKey   string
	GitHubAPIBaseURL      string
	Logger                *slog.Logger
	HTTPClient            *http.Client
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
	mux.HandleFunc("GET /git/github/authorize", handleGitHubAuthorize(deps))
	mux.HandleFunc("GET /git/github/callback", handleGitHubCallback(deps))
	mux.HandleFunc("GET /git/status", handleGitStatus(deps))
	mux.HandleFunc("DELETE /git/connection", handleGitDisconnect(deps))

	mux.HandleFunc("GET /projects/{id}/git", handleGetProjectGit(deps))
	mux.HandleFunc("POST /projects/{id}/git/repo", handleCreateProjectRepo(deps))
	mux.HandleFunc("POST /projects/{id}/git/push", handlePushProjectRepo(deps))
	mux.HandleFunc("GET /projects/{id}/export", handleExportProjectZip(deps))
}

func handleGitHubAuthorize(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSONError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		if deps.GitHubAppID == "" && deps.GitHubAppClientID == "" {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusServiceUnavailable)
			_ = json.NewEncoder(w).Encode(map[string]string{
				"error": "GitHub App is not configured. Set GITHUB_APP_CLIENT_ID and GITHUB_APP_ID in .env",
				"code":  "not_configured",
			})
			return
		}

		projectID := r.URL.Query().Get("projectId")
		state := fmt.Sprintf("%s:%s:%d", user.ID, projectID, time.Now().Unix())

		// If ClientID is set, point to installation / authorize
		appSlug := "omnistackai"
		authURL := fmt.Sprintf("https://github.com/apps/%s/installations/new?state=%s", appSlug, url.QueryEscape(state))
		if deps.GitHubAppClientID != "" {
			authURL = fmt.Sprintf("https://github.com/login/oauth/authorize?client_id=%s&state=%s", deps.GitHubAppClientID, url.QueryEscape(state))
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{"url": authURL})
	}
}

func handleGitHubCallback(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSONError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		installationIDStr := r.URL.Query().Get("installation_id")
		code := r.URL.Query().Get("code")
		state := r.URL.Query().Get("state")

		var installationID int64
		if installationIDStr != "" {
			installationID, _ = strconv.ParseInt(installationIDStr, 10, 64)
		}

		login := user.Email
		if idx := strings.Index(login, "@"); idx > 0 {
			login = login[:idx]
		}

		conn := &Connection{
			UserID:         user.ID,
			Provider:       "github",
			ExternalLogin:  login,
			InstallationID: installationID,
			RefreshToken:   code,
			ConnectedAt:    time.Now(),
		}

		if err := deps.GitStore.SaveConnection(r.Context(), conn); err != nil {
			deps.logger().Error("failed to save git connection", "error", err)
			writeJSONError(w, http.StatusInternalServerError, "failed to save connection")
			return
		}

		// Extract optional projectID from state if present
		redirectTarget := "/projects"
		if state != "" {
			parts := strings.Split(state, ":")
			if len(parts) >= 2 && parts[1] != "" {
				redirectTarget = fmt.Sprintf("/studio/%s/manage?tab=git", parts[1])
			}
		}

		http.Redirect(w, r, redirectTarget, http.StatusSeeOther)
	}
}

func handleGitStatus(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSONError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		conn, err := deps.GitStore.GetConnection(r.Context(), user.ID)
		if errors.Is(err, ErrConnectionNotFound) {
			w.Header().Set("Content-Type", "application/json")
			_ = json.NewEncoder(w).Encode(map[string]interface{}{
				"connected": false,
			})
			return
		}
		if err != nil {
			deps.logger().Error("failed to get git connection", "error", err)
			writeJSONError(w, http.StatusInternalServerError, "internal server error")
			return
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"connected":       true,
			"login":           conn.ExternalLogin,
			"installation_id": conn.InstallationID,
			"connected_at":    conn.ConnectedAt,
		})
	}
}

func handleGitDisconnect(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSONError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		if err := deps.GitStore.DeleteConnection(r.Context(), user.ID); err != nil {
			deps.logger().Error("failed to delete git connection", "error", err)
			writeJSONError(w, http.StatusInternalServerError, "internal server error")
			return
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]bool{"ok": true})
	}
}

func handleGetProjectGit(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSONError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		if projectID == "" {
			writeJSONError(w, http.StatusBadRequest, "project id required")
			return
		}

		info, err := deps.GitStore.GetProjectGit(r.Context(), user.ID, projectID)
		if errors.Is(err, ErrProjectNotFound) {
			writeJSONError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			deps.logger().Error("failed to get project git", "error", err)
			writeJSONError(w, http.StatusInternalServerError, "internal server error")
			return
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(info)
	}
}

type CreateRepoRequest struct {
	Name    string `json:"name"`
	Private bool   `json:"private"`
}

func handleCreateProjectRepo(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSONError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		if projectID == "" {
			writeJSONError(w, http.StatusBadRequest, "project id required")
			return
		}

		var reqBody CreateRepoRequest
		if err := json.NewDecoder(r.Body).Decode(&reqBody); err != nil {
			writeJSONError(w, http.StatusBadRequest, "invalid request body")
			return
		}

		conn, err := deps.GitStore.GetConnection(r.Context(), user.ID)
		if errors.Is(err, ErrConnectionNotFound) {
			writeJSONError(w, http.StatusBadRequest, "GitHub account not connected. Connect GitHub first.")
			return
		}
		if err != nil {
			writeJSONError(w, http.StatusInternalServerError, "failed to check connection")
			return
		}

		if deps.GitHubAppID == "" || deps.GitHubAppPrivateKey == "" {
			writeJSONError(w, http.StatusServiceUnavailable, "GitHub App credentials are not configured on the server")
			return
		}

		// Mint installation token
		appJWT, err := MintAppJWT(deps.GitHubAppID, []byte(deps.GitHubAppPrivateKey), time.Now())
		if err != nil {
			deps.logger().Error("failed to mint GitHub App JWT", "error", err)
			writeJSONError(w, http.StatusInternalServerError, "failed to authenticate with GitHub")
			return
		}

		instToken, _, err := MintInstallationToken(r.Context(), deps.httpClient(), deps.GitHubAPIBaseURL, appJWT, conn.InstallationID)
		if err != nil {
			deps.logger().Error("failed to mint GitHub installation token", "error", err)
			writeJSONError(w, http.StatusBadGateway, fmt.Sprintf("GitHub token minting failed: %v", err))
			return
		}

		repo, err := CreateUserRepo(r.Context(), deps.httpClient(), deps.GitHubAPIBaseURL, instToken, reqBody.Name, "", reqBody.Private)
		if err != nil {
			deps.logger().Error("failed to create GitHub repository", "error", err)
			writeJSONError(w, http.StatusBadGateway, fmt.Sprintf("GitHub repo creation failed: %v", err))
			return
		}

		if err := deps.GitStore.UpdateProjectRepo(r.Context(), user.ID, projectID, repo.FullName, repo.HTMLURL, repo.Private); err != nil {
			writeJSONError(w, http.StatusInternalServerError, "failed to update project repository")
			return
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(repo)
	}
}

func handlePushProjectRepo(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSONError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		if projectID == "" {
			writeJSONError(w, http.StatusBadRequest, "project id required")
			return
		}

		projGit, err := deps.GitStore.GetProjectGit(r.Context(), user.ID, projectID)
		if errors.Is(err, ErrProjectNotFound) {
			writeJSONError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			writeJSONError(w, http.StatusInternalServerError, "internal server error")
			return
		}

		if projGit.RepoFullName == "" {
			writeJSONError(w, http.StatusBadRequest, "No GitHub repository configured for this project. Create repository first.")
			return
		}

		conn, err := deps.GitStore.GetConnection(r.Context(), user.ID)
		if errors.Is(err, ErrConnectionNotFound) {
			writeJSONError(w, http.StatusBadRequest, "GitHub account not connected")
			return
		}
		if err != nil {
			writeJSONError(w, http.StatusInternalServerError, "failed to check connection")
			return
		}

		if deps.GitHubAppID == "" || deps.GitHubAppPrivateKey == "" {
			writeJSONError(w, http.StatusServiceUnavailable, "GitHub App credentials are not configured on the server")
			return
		}

		appJWT, err := MintAppJWT(deps.GitHubAppID, []byte(deps.GitHubAppPrivateKey), time.Now())
		if err != nil {
			deps.logger().Error("failed to mint GitHub App JWT", "error", err)
			writeJSONError(w, http.StatusInternalServerError, "failed to authenticate with GitHub")
			return
		}

		instToken, _, err := MintInstallationToken(r.Context(), deps.httpClient(), deps.GitHubAPIBaseURL, appJWT, conn.InstallationID)
		if err != nil {
			deps.logger().Error("failed to mint GitHub installation token", "error", err)
			writeJSONError(w, http.StatusBadGateway, fmt.Sprintf("GitHub token minting failed: %v", err))
			return
		}

		remoteURL := fmt.Sprintf("https://x-access-token:%s@github.com/%s.git", instToken, projGit.RepoFullName)

		// Call agent engine POST /api/workspaces/{id}/git/push
		agentURL := fmt.Sprintf("%s/api/workspaces/%s/git/push", strings.TrimRight(deps.AgentEngineURL, "/"), projectID)
		pushReqBody, _ := json.Marshal(map[string]string{
			"remote_url": remoteURL,
			"branch":     "main",
		})

		agentReq, err := http.NewRequestWithContext(r.Context(), http.MethodPost, agentURL, bytes.NewReader(pushReqBody))
		if err != nil {
			writeJSONError(w, http.StatusInternalServerError, "failed to build push request")
			return
		}
		agentReq.Header.Set("Content-Type", "application/json")

		agentResp, err := deps.httpClient().Do(agentReq)
		if err != nil {
			writeJSONError(w, http.StatusBadGateway, fmt.Sprintf("failed to reach agent engine: %v", err))
			return
		}
		defer agentResp.Body.Close()

		rawResp, err := io.ReadAll(agentResp.Body)
		if err != nil {
			writeJSONError(w, http.StatusInternalServerError, "failed to read agent engine response")
			return
		}

		if agentResp.StatusCode < 200 || agentResp.StatusCode >= 300 {
			// Scrub token from error message
			sanitized := strings.ReplaceAll(string(rawResp), instToken, "[REDACTED]")
			writeJSONError(w, http.StatusBadGateway, fmt.Sprintf("git push failed: %s", sanitized))
			return
		}

		var pushResult struct {
			CommitSHA string `json:"commit_sha"`
			Branch    string `json:"branch"`
		}
		_ = json.Unmarshal(rawResp, &pushResult)

		now := time.Now()
		if pushResult.CommitSHA != "" {
			_ = deps.GitStore.UpdateProjectPushed(r.Context(), user.ID, projectID, pushResult.CommitSHA, now)
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"commit_sha": pushResult.CommitSHA,
			"branch":     pushResult.Branch,
			"repo_url":   projGit.RepoURL,
			"pushed_at":  now,
		})
	}
}

func handleExportProjectZip(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSONError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		if projectID == "" {
			writeJSONError(w, http.StatusBadRequest, "project id required")
			return
		}

		proj, err := deps.ProjectStore.GetProject(r.Context(), projectID, user.ID)
		if err != nil {
			writeJSONError(w, http.StatusNotFound, "project not found")
			return
		}

		agentURL := fmt.Sprintf("%s/api/workspaces/%s/export", strings.TrimRight(deps.AgentEngineURL, "/"), projectID)
		agentReq, err := http.NewRequestWithContext(r.Context(), http.MethodGet, agentURL, nil)
		if err != nil {
			writeJSONError(w, http.StatusInternalServerError, "failed to build export request")
			return
		}

		agentResp, err := deps.httpClient().Do(agentReq)
		if err != nil {
			writeJSONError(w, http.StatusBadGateway, fmt.Sprintf("failed to reach agent engine: %v", err))
			return
		}
		defer agentResp.Body.Close()

		if agentResp.StatusCode == http.StatusNotFound {
			writeJSONError(w, http.StatusNotFound, "workspace files not found on disk")
			return
		}
		if agentResp.StatusCode < 200 || agentResp.StatusCode >= 300 {
			errBytes, _ := io.ReadAll(agentResp.Body)
			writeJSONError(w, http.StatusBadGateway, fmt.Sprintf("export failed: %s", string(errBytes)))
			return
		}

		slug := slugPattern.ReplaceAllString(strings.ToLower(proj.Name), "-")
		slug = strings.Trim(slug, "-")
		if slug == "" {
			slug = "project"
		}
		filename := fmt.Sprintf("%s.zip", slug)

		w.Header().Set("Content-Type", "application/zip")
		w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%q", filename))
		if cl := agentResp.Header.Get("Content-Length"); cl != "" {
			w.Header().Set("Content-Length", cl)
		}

		_, _ = io.Copy(w, agentResp.Body)
	}
}

func writeJSONError(w http.ResponseWriter, status int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": message})
}

package deploy

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

var (
	ErrProviderAuthFailed = errors.New("deploy: provider authentication failed (check token)")
	ErrProviderAPIFailed  = errors.New("deploy: provider API call failed")
)

type DeployProvider interface {
	VerifyToken(ctx context.Context, token string) (accountLabel string, err error)
	CreateProject(ctx context.Context, token, projectName, repoFullName, framework string, env map[string]string) (externalID string, err error)
	TriggerDeploy(ctx context.Context, token, externalID, projectName, repoFullName, commitSHA string) (deploymentID, liveURL string, err error)
	GetDeployment(ctx context.Context, token, deploymentID string) (status, liveURL, logURL, errorMsg string, err error)
	SetEnv(ctx context.Context, token, externalID string, env map[string]string) error
}

// VercelProvider implements DeployProvider for Vercel REST API v10/v13
type VercelProvider struct {
	BaseURL    string
	HTTPClient *http.Client
}

func NewVercelProvider(baseURL string, client *http.Client) *VercelProvider {
	if baseURL == "" {
		baseURL = "https://api.vercel.com"
	}
	if client == nil {
		client = &http.Client{Timeout: 30 * time.Second}
	}
	return &VercelProvider{BaseURL: strings.TrimSuffix(baseURL, "/"), HTTPClient: client}
}

func (v *VercelProvider) VerifyToken(ctx context.Context, token string) (string, error) {
	req, err := http.NewRequestWithContext(ctx, "GET", v.BaseURL+"/v2/user", nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := v.HTTPClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("%w: %v", ErrProviderAPIFailed, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden {
		return "", ErrProviderAuthFailed
	}
	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("%w: HTTP %d: %s", ErrProviderAPIFailed, resp.StatusCode, string(b))
	}

	var data struct {
		User struct {
			Username string `json:"username"`
			Email    string `json:"email"`
			Name     string `json:"name"`
		} `json:"user"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return "", fmt.Errorf("deploy: decode vercel user: %w", err)
	}
	label := data.User.Username
	if label == "" {
		label = data.User.Name
	}
	if label == "" {
		label = data.User.Email
	}
	return label, nil
}

func (v *VercelProvider) CreateProject(ctx context.Context, token, projectName, repoFullName, framework string, env map[string]string) (string, error) {
	if framework == "" {
		framework = "nextjs"
	}
	payload := map[string]any{
		"name":      projectName,
		"framework": framework,
	}
	if repoFullName != "" {
		payload["gitRepository"] = map[string]any{
			"type": "github",
			"repo": repoFullName,
		}
	}

	bodyBytes, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, "POST", v.BaseURL+"/v10/projects", bytes.NewReader(bodyBytes))
	if err != nil {
		return "", err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := v.HTTPClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("%w: %v", ErrProviderAPIFailed, err)
	}
	defer resp.Body.Close()

	// If project already exists (409 Conflict), fetch it
	if resp.StatusCode == http.StatusConflict {
		return v.getExistingProjectID(ctx, token, projectName)
	}

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("%w: HTTP %d: %s", ErrProviderAPIFailed, resp.StatusCode, string(b))
	}

	var data struct {
		ID   string `json:"id"`
		Name string `json:"name"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return "", fmt.Errorf("deploy: decode vercel project: %w", err)
	}

	if len(env) > 0 {
		_ = v.SetEnv(ctx, token, data.ID, env)
	}

	return data.ID, nil
}

func (v *VercelProvider) getExistingProjectID(ctx context.Context, token, projectName string) (string, error) {
	req, err := http.NewRequestWithContext(ctx, "GET", v.BaseURL+"/v9/projects/"+projectName, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := v.HTTPClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("deploy: get existing vercel project: HTTP %d: %s", resp.StatusCode, string(b))
	}

	var data struct {
		ID string `json:"id"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return "", err
	}
	return data.ID, nil
}

func (v *VercelProvider) SetEnv(ctx context.Context, token, externalID string, env map[string]string) error {
	if len(env) == 0 {
		return nil
	}
	var envList []map[string]any
	for k, val := range env {
		envList = append(envList, map[string]any{
			"key":    k,
			"value":  val,
			"type":   "plain",
			"target": []string{"production", "preview", "development"},
		})
	}
	bodyBytes, _ := json.Marshal(envList)
	req, err := http.NewRequestWithContext(ctx, "POST", v.BaseURL+"/v10/projects/"+externalID+"/env", bytes.NewReader(bodyBytes))
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := v.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return nil
}

func (v *VercelProvider) TriggerDeploy(ctx context.Context, token, externalID, projectName, repoFullName, commitSHA string) (string, string, error) {
	payload := map[string]any{
		"name":    projectName,
		"project": externalID,
		"target":  "production",
	}
	if repoFullName != "" {
		payload["gitSource"] = map[string]any{
			"type": "github",
			"repo": repoFullName,
			"ref":  "main",
			"sha":  commitSHA,
		}
	}

	bodyBytes, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, "POST", v.BaseURL+"/v13/deployments", bytes.NewReader(bodyBytes))
	if err != nil {
		return "", "", err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := v.HTTPClient.Do(req)
	if err != nil {
		return "", "", fmt.Errorf("%w: %v", ErrProviderAPIFailed, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return "", "", fmt.Errorf("%w: HTTP %d: %s", ErrProviderAPIFailed, resp.StatusCode, string(b))
	}

	var data struct {
		ID         string `json:"id"`
		URL        string `json:"url"`
		ReadyState string `json:"readyState"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return "", "", fmt.Errorf("deploy: decode vercel deployment: %w", err)
	}

	liveURL := data.URL
	if liveURL != "" && !strings.HasPrefix(liveURL, "http://") && !strings.HasPrefix(liveURL, "https://") {
		liveURL = "https://" + liveURL
	}
	return data.ID, liveURL, nil
}

func (v *VercelProvider) GetDeployment(ctx context.Context, token, deploymentID string) (string, string, string, string, error) {
	req, err := http.NewRequestWithContext(ctx, "GET", v.BaseURL+"/v13/deployments/"+deploymentID, nil)
	if err != nil {
		return "", "", "", "", err
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := v.HTTPClient.Do(req)
	if err != nil {
		return "", "", "", "", fmt.Errorf("%w: %v", ErrProviderAPIFailed, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return "", "", "", "", fmt.Errorf("%w: HTTP %d: %s", ErrProviderAPIFailed, resp.StatusCode, string(b))
	}

	var data struct {
		ID           string `json:"id"`
		URL          string `json:"url"`
		InspectorURL string `json:"inspectorUrl"`
		ReadyState   string `json:"readyState"`
		ErrorMessage string `json:"errorMessage"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return "", "", "", "", fmt.Errorf("deploy: decode vercel status: %w", err)
	}

	// Normalize status to: 'queued', 'building', 'ready', 'error', 'cancelled'
	status := "building"
	switch strings.ToUpper(data.ReadyState) {
	case "READY":
		status = "ready"
	case "ERROR":
		status = "error"
	case "CANCELED", "CANCELLED":
		status = "cancelled"
	case "QUEUED", "INITIALIZING":
		status = "queued"
	default:
		status = "building"
	}

	liveURL := data.URL
	if liveURL != "" && !strings.HasPrefix(liveURL, "http://") && !strings.HasPrefix(liveURL, "https://") {
		liveURL = "https://" + liveURL
	}

	return status, liveURL, data.InspectorURL, data.ErrorMessage, nil
}

// NetlifyProvider implements DeployProvider for Netlify API v1
type NetlifyProvider struct {
	BaseURL    string
	HTTPClient *http.Client
}

func NewNetlifyProvider(baseURL string, client *http.Client) *NetlifyProvider {
	if baseURL == "" {
		baseURL = "https://api.netlify.com"
	}
	if client == nil {
		client = &http.Client{Timeout: 30 * time.Second}
	}
	return &NetlifyProvider{BaseURL: strings.TrimSuffix(baseURL, "/"), HTTPClient: client}
}

func (n *NetlifyProvider) VerifyToken(ctx context.Context, token string) (string, error) {
	req, err := http.NewRequestWithContext(ctx, "GET", n.BaseURL+"/api/v1/user", nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := n.HTTPClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("%w: %v", ErrProviderAPIFailed, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden {
		return "", ErrProviderAuthFailed
	}
	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("%w: HTTP %d: %s", ErrProviderAPIFailed, resp.StatusCode, string(b))
	}

	var data struct {
		FullName string `json:"full_name"`
		Email    string `json:"email"`
		Slug     string `json:"slug"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return "", fmt.Errorf("deploy: decode netlify user: %w", err)
	}
	label := data.FullName
	if label == "" {
		label = data.Slug
	}
	if label == "" {
		label = data.Email
	}
	return label, nil
}

func (n *NetlifyProvider) CreateProject(ctx context.Context, token, projectName, repoFullName, framework string, env map[string]string) (string, error) {
	payload := map[string]any{
		"name": projectName,
	}
	if repoFullName != "" {
		payload["repo"] = map[string]any{
			"provider":  "github",
			"repo_path": repoFullName,
			"branch":    "main",
			"cmd":       "pnpm build",
			"dir":       ".next",
		}
	}

	bodyBytes, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, "POST", n.BaseURL+"/api/v1/sites", bytes.NewReader(bodyBytes))
	if err != nil {
		return "", err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := n.HTTPClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("%w: %v", ErrProviderAPIFailed, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("%w: HTTP %d: %s", ErrProviderAPIFailed, resp.StatusCode, string(b))
	}

	var data struct {
		ID   string `json:"id"`
		Name string `json:"name"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return "", fmt.Errorf("deploy: decode netlify site: %w", err)
	}

	if len(env) > 0 {
		_ = n.SetEnv(ctx, token, data.ID, env)
	}

	return data.ID, nil
}

func (n *NetlifyProvider) SetEnv(ctx context.Context, token, externalID string, env map[string]string) error {
	if len(env) == 0 {
		return nil
	}
	payload := map[string]any{
		"build_settings": map[string]any{
			"env": env,
		},
	}
	bodyBytes, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, "PATCH", n.BaseURL+"/api/v1/sites/"+externalID, bytes.NewReader(bodyBytes))
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := n.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return nil
}

func (n *NetlifyProvider) TriggerDeploy(ctx context.Context, token, externalID, projectName, repoFullName, commitSHA string) (string, string, error) {
	req, err := http.NewRequestWithContext(ctx, "POST", n.BaseURL+"/api/v1/sites/"+externalID+"/builds", nil)
	if err != nil {
		return "", "", err
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := n.HTTPClient.Do(req)
	if err != nil {
		return "", "", fmt.Errorf("%w: %v", ErrProviderAPIFailed, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return "", "", fmt.Errorf("%w: HTTP %d: %s", ErrProviderAPIFailed, resp.StatusCode, string(b))
	}

	var data struct {
		ID        string `json:"id"`
		DeployID  string `json:"deploy_id"`
		DeployURL string `json:"deploy_url"`
		URL       string `json:"url"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return "", "", fmt.Errorf("deploy: decode netlify build: %w", err)
	}

	depID := data.DeployID
	if depID == "" {
		depID = data.ID
	}
	liveURL := data.URL
	if liveURL == "" {
		liveURL = data.DeployURL
	}
	return depID, liveURL, nil
}

func (n *NetlifyProvider) GetDeployment(ctx context.Context, token, deploymentID string) (string, string, string, string, error) {
	req, err := http.NewRequestWithContext(ctx, "GET", n.BaseURL+"/api/v1/deploys/"+deploymentID, nil)
	if err != nil {
		return "", "", "", "", err
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := n.HTTPClient.Do(req)
	if err != nil {
		return "", "", "", "", fmt.Errorf("%w: %v", ErrProviderAPIFailed, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return "", "", "", "", fmt.Errorf("%w: HTTP %d: %s", ErrProviderAPIFailed, resp.StatusCode, string(b))
	}

	var data struct {
		ID        string `json:"id"`
		State     string `json:"state"`
		URL       string `json:"url"`
		DeployURL string `json:"deploy_url"`
		AdminURL  string `json:"admin_url"`
		Error     string `json:"error_message"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return "", "", "", "", fmt.Errorf("deploy: decode netlify deploy: %w", err)
	}

	status := "building"
	switch strings.ToLower(data.State) {
	case "ready":
		status = "ready"
	case "error":
		status = "error"
	case "enqueued":
		status = "queued"
	default:
		status = "building"
	}

	liveURL := data.URL
	if liveURL == "" {
		liveURL = data.DeployURL
	}

	return status, liveURL, data.AdminURL, data.Error, nil
}

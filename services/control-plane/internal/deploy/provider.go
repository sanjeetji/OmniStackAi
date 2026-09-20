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
	AddDomain(ctx context.Context, token, externalID, hostname string) (recordType, recordName, recordValue string, verified bool, err error)
	VerifyDomain(ctx context.Context, token, externalID, hostname string) (dnsVerified, tlsIssued bool, errorMsg string, err error)
	RemoveDomain(ctx context.Context, token, externalID, hostname string) error
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

func (v *VercelProvider) AddDomain(ctx context.Context, token, externalID, hostname string) (string, string, string, bool, error) {
	payload := map[string]any{
		"name": hostname,
	}
	bodyBytes, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, "POST", v.BaseURL+"/v9/projects/"+externalID+"/domains", bytes.NewReader(bodyBytes))
	if err != nil {
		return "", "", "", false, err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := v.HTTPClient.Do(req)
	if err != nil {
		return "", "", "", false, fmt.Errorf("%w: %v", ErrProviderAPIFailed, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 && resp.StatusCode != http.StatusConflict {
		b, _ := io.ReadAll(resp.Body)
		return "", "", "", false, fmt.Errorf("%w: HTTP %d: %s", ErrProviderAPIFailed, resp.StatusCode, string(b))
	}

	var data struct {
		Name         string `json:"name"`
		ApexName     string `json:"apexName"`
		Verified     bool   `json:"verified"`
		Verification []struct {
			Type   string `json:"type"`
			Domain string `json:"domain"`
			Value  string `json:"value"`
			Reason string `json:"reason"`
		} `json:"verification"`
	}
	if resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusCreated {
		_ = json.NewDecoder(resp.Body).Decode(&data)
	}

	isApex := data.ApexName == hostname || (data.ApexName == "" && strings.Count(hostname, ".") == 1)
	recordType := "CNAME"
	recordName := strings.Split(hostname, ".")[0]
	recordValue := "cname.vercel-dns.com"
	if isApex {
		recordType = "A"
		recordName = "@"
		recordValue = "76.76.21.21"
	}
	if len(data.Verification) > 0 {
		recordType = data.Verification[0].Type
		recordValue = data.Verification[0].Value
		recordName = data.Verification[0].Domain
	}

	return recordType, recordName, recordValue, data.Verified, nil
}

func (v *VercelProvider) VerifyDomain(ctx context.Context, token, externalID, hostname string) (bool, bool, string, error) {
	reqVerify, err := http.NewRequestWithContext(ctx, "POST", v.BaseURL+"/v9/projects/"+externalID+"/domains/"+hostname+"/verify", nil)
	if err == nil {
		reqVerify.Header.Set("Authorization", "Bearer "+token)
		if resp, err := v.HTTPClient.Do(reqVerify); err == nil {
			_ = resp.Body.Close()
		}
	}

	req, err := http.NewRequestWithContext(ctx, "GET", v.BaseURL+"/v9/projects/"+externalID+"/domains/"+hostname, nil)
	if err != nil {
		return false, false, "", err
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := v.HTTPClient.Do(req)
	if err != nil {
		return false, false, "", fmt.Errorf("%w: %v", ErrProviderAPIFailed, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return false, false, string(b), fmt.Errorf("%w: HTTP %d: %s", ErrProviderAPIFailed, resp.StatusCode, string(b))
	}

	var data struct {
		Name     string `json:"name"`
		Verified bool   `json:"verified"`
		Error    struct {
			Code    string `json:"code"`
			Message string `json:"message"`
		} `json:"error"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return false, false, "", err
	}

	if !data.Verified {
		errMsg := data.Error.Message
		if errMsg == "" {
			errMsg = "DNS records not yet propagated to Vercel"
		}
		return false, false, errMsg, nil
	}

	return true, true, "", nil
}

func (v *VercelProvider) RemoveDomain(ctx context.Context, token, externalID, hostname string) error {
	req, err := http.NewRequestWithContext(ctx, "DELETE", v.BaseURL+"/v9/projects/"+externalID+"/domains/"+hostname, nil)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := v.HTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("%w: %v", ErrProviderAPIFailed, err)
	}
	defer resp.Body.Close()
	return nil
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

func (n *NetlifyProvider) AddDomain(ctx context.Context, token, externalID, hostname string) (string, string, string, bool, error) {
	payload := map[string]any{
		"domain": hostname,
	}
	bodyBytes, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, "POST", n.BaseURL+"/api/v1/sites/"+externalID+"/domain_aliases", bytes.NewReader(bodyBytes))
	if err == nil {
		req.Header.Set("Authorization", "Bearer "+token)
		req.Header.Set("Content-Type", "application/json")
		if resp, err := n.HTTPClient.Do(req); err == nil {
			_ = resp.Body.Close()
		}
	}

	isApex := strings.Count(hostname, ".") == 1
	recordType := "CNAME"
	recordName := strings.Split(hostname, ".")[0]
	recordValue := externalID + ".netlify.app"
	if isApex {
		recordType = "A"
		recordName = "@"
		recordValue = "75.2.60.5"
	}
	return recordType, recordName, recordValue, false, nil
}

func (n *NetlifyProvider) VerifyDomain(ctx context.Context, token, externalID, hostname string) (bool, bool, string, error) {
	req, err := http.NewRequestWithContext(ctx, "GET", n.BaseURL+"/api/v1/sites/"+externalID, nil)
	if err != nil {
		return false, false, "", err
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := n.HTTPClient.Do(req)
	if err != nil {
		return false, false, "", fmt.Errorf("%w: %v", ErrProviderAPIFailed, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return false, false, string(b), fmt.Errorf("%w: HTTP %d: %s", ErrProviderAPIFailed, resp.StatusCode, string(b))
	}

	var data struct {
		CustomDomain  string   `json:"custom_domain"`
		DomainAliases []string `json:"domain_aliases"`
		SSL           bool     `json:"ssl"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return false, false, "", err
	}

	found := data.CustomDomain == hostname
	if !found {
		for _, a := range data.DomainAliases {
			if a == hostname {
				found = true
				break
			}
		}
	}

	if !found {
		return false, false, "Domain not attached to Netlify site", nil
	}
	return true, data.SSL, "", nil
}

func (n *NetlifyProvider) RemoveDomain(ctx context.Context, token, externalID, hostname string) error {
	req, err := http.NewRequestWithContext(ctx, "DELETE", n.BaseURL+"/api/v1/sites/"+externalID+"/domain_aliases/"+hostname, nil)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := n.HTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("%w: %v", ErrProviderAPIFailed, err)
	}
	defer resp.Body.Close()
	return nil
}

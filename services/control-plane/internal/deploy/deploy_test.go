package deploy

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/git"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
)

type fakeAuthStore struct {
	user auth.User
	err  error
}

func (f fakeAuthStore) CreateUser(context.Context, string, string, string, int64) (auth.User, error) {
	return f.user, f.err
}
func (f fakeAuthStore) FindUserByEmail(context.Context, string) (auth.User, string, error) {
	return f.user, "", f.err
}
func (f fakeAuthStore) FindUserByID(context.Context, string) (auth.User, error) {
	return f.user, f.err
}
func (f fakeAuthStore) CreateSession(context.Context, string, string, time.Time) error {
	return f.err
}
func (f fakeAuthStore) FindUserBySessionToken(context.Context, string) (auth.User, error) {
	if f.err != nil {
		return auth.User{}, f.err
	}
	return f.user, nil
}
func (f fakeAuthStore) DeleteSession(context.Context, string) error {
	return f.err
}

type memStore struct {
	conns       map[string]*Connection // key: userID:provider
	tokens      map[string]string      // key: userID:provider -> plaintext
	deployments map[string]*Deployment // key: depID
	projectDeps map[string][]string    // key: projectID -> [depID, ...]
	projMeta    map[string][3]string   // key: projectID -> [provider, externalID, liveURL]
}

func newMemStore() *memStore {
	return &memStore{
		conns:       make(map[string]*Connection),
		tokens:      make(map[string]string),
		deployments: make(map[string]*Deployment),
		projectDeps: make(map[string][]string),
		projMeta:    make(map[string][3]string),
	}
}

func (m *memStore) GetConnection(ctx context.Context, userID, provider string) (*Connection, string, error) {
	key := fmt.Sprintf("%s:%s", userID, provider)
	conn, ok := m.conns[key]
	if !ok {
		return nil, "", ErrNotFound
	}
	return conn, m.tokens[key], nil
}

func (m *memStore) GetConnectionStatus(ctx context.Context, userID, provider string) (*Connection, error) {
	key := fmt.Sprintf("%s:%s", userID, provider)
	conn, ok := m.conns[key]
	if !ok {
		return nil, ErrNotFound
	}
	return conn, nil
}

func (m *memStore) SetConnection(ctx context.Context, userID, provider, token, accountLabel string) (*Connection, error) {
	key := fmt.Sprintf("%s:%s", userID, provider)
	conn := &Connection{
		ID:           "conn-" + provider,
		UserID:       userID,
		Provider:     provider,
		AccountLabel: accountLabel,
		CreatedAt:    time.Now(),
	}
	m.conns[key] = conn
	m.tokens[key] = token
	return conn, nil
}

func (m *memStore) DeleteConnection(ctx context.Context, userID, provider string) error {
	key := fmt.Sprintf("%s:%s", userID, provider)
	delete(m.conns, key)
	delete(m.tokens, key)
	return nil
}

func (m *memStore) CreateDeployment(ctx context.Context, d *Deployment) (*Deployment, error) {
	id := fmt.Sprintf("dep-%d", len(m.deployments)+1)
	clone := *d
	clone.ID = id
	clone.CreatedAt = time.Now()
	m.deployments[id] = &clone
	m.projectDeps[d.ProjectID] = append([]string{id}, m.projectDeps[d.ProjectID]...)
	return &clone, nil
}

func (m *memStore) UpdateDeployment(ctx context.Context, id, status, url, errorMsg string, finishedAt *time.Time) error {
	dep, ok := m.deployments[id]
	if !ok {
		return ErrNotFound
	}
	dep.Status = status
	if url != "" {
		dep.URL = url
	}
	dep.Error = errorMsg
	dep.FinishedAt = finishedAt
	return nil
}

func (m *memStore) GetDeployment(ctx context.Context, id string) (*Deployment, error) {
	dep, ok := m.deployments[id]
	if !ok {
		return nil, ErrNotFound
	}
	return dep, nil
}

func (m *memStore) GetLatestDeployment(ctx context.Context, projectID string) (*Deployment, error) {
	ids := m.projectDeps[projectID]
	if len(ids) == 0 {
		return nil, nil
	}
	return m.deployments[ids[0]], nil
}

func (m *memStore) ListDeployments(ctx context.Context, projectID string, limit int) ([]Deployment, error) {
	ids := m.projectDeps[projectID]
	var res []Deployment
	for _, id := range ids {
		if len(res) >= limit {
			break
		}
		if dep, ok := m.deployments[id]; ok {
			res = append(res, *dep)
		}
	}
	return res, nil
}

func (m *memStore) UpdateProjectDeployMeta(ctx context.Context, projectID, provider, externalID, liveURL string) error {
	m.projMeta[projectID] = [3]string{provider, externalID, liveURL}
	return nil
}

func (m *memStore) GetProjectDeployMeta(ctx context.Context, projectID string) (string, string, string, error) {
	meta, ok := m.projMeta[projectID]
	if !ok {
		return "", "", "", nil
	}
	return meta[0], meta[1], meta[2], nil
}

type fakeProjectStore struct {
	proj projects.Project
	err  error
}

func (f fakeProjectStore) CreateProject(ctx context.Context, userID, name, description string) (projects.Project, error) {
	return f.proj, f.err
}
func (f fakeProjectStore) ListProjects(ctx context.Context, userID, status string, limit int) ([]projects.Project, error) {
	return []projects.Project{f.proj}, f.err
}
func (f fakeProjectStore) GetProject(ctx context.Context, id, userID string) (projects.Project, error) {
	return f.proj, f.err
}
func (f fakeProjectStore) UpdateProject(ctx context.Context, id, userID string, name, description *string) (projects.Project, error) {
	return f.proj, f.err
}
func (f fakeProjectStore) UpdateProjectBuildResult(ctx context.Context, id, userID string, name, prompt, commitSHA string, entities json.RawMessage, fileCount int, messageDelta int) error {
	return f.err
}
func (f fakeProjectStore) DebitProjectCredits(ctx context.Context, userID, projectID string, requested int64, reason string) (int64, int64, error) {
	return 0, 100, f.err
}
func (f fakeProjectStore) ArchiveProject(ctx context.Context, id, userID string) error {
	return f.err
}
func (f fakeProjectStore) DeleteProject(ctx context.Context, id, userID string) error {
	return f.err
}
func (f fakeProjectStore) TouchProjectOpened(ctx context.Context, id, userID string) error {
	return f.err
}

type fakeGitStore struct {
	gitInfo *git.ProjectGitInfo
	err     error
}

func (f fakeGitStore) GetConnection(ctx context.Context, userID string) (*git.Connection, error) {
	return nil, nil
}
func (f fakeGitStore) SaveConnection(ctx context.Context, conn *git.Connection) error {
	return nil
}
func (f fakeGitStore) DeleteConnection(ctx context.Context, userID string) error {
	return nil
}
func (f fakeGitStore) GetProjectGit(ctx context.Context, userID, projectID string) (*git.ProjectGitInfo, error) {
	return f.gitInfo, f.err
}
func (f fakeGitStore) UpdateProjectRepo(ctx context.Context, userID, projectID, repoFullName, repoURL string, repoPrivate bool) error {
	return nil
}
func (f fakeGitStore) UpdateProjectPushed(ctx context.Context, userID, projectID, pushedSHA string, pushedAt time.Time) error {
	return nil
}

type mockDeployProvider struct {
	accountLabel string
	projectID    string
	deployID     string
	liveURL      string
	status       string
	envPassed    map[string]string
}

func (m *mockDeployProvider) VerifyToken(ctx context.Context, token string) (string, error) {
	if token == "bad-token" {
		return "", ErrProviderAuthFailed
	}
	return m.accountLabel, nil
}
func (m *mockDeployProvider) CreateProject(ctx context.Context, token, projectName, repoFullName, framework string, env map[string]string) (string, error) {
	m.envPassed = env
	return m.projectID, nil
}
func (m *mockDeployProvider) TriggerDeploy(ctx context.Context, token, externalID, projectName, repoFullName, commitSHA string) (string, string, error) {
	return m.deployID, m.liveURL, nil
}
func (m *mockDeployProvider) GetDeployment(ctx context.Context, token, deploymentID string) (string, string, string, string, error) {
	return m.status, m.liveURL, "https://logs.example.com", "", nil
}
func (m *mockDeployProvider) SetEnv(ctx context.Context, token, externalID string, env map[string]string) error {
	m.envPassed = env
	return nil
}

func TestDeployConnectionLifecycle(t *testing.T) {
	authStore := fakeAuthStore{
		user: auth.User{ID: "usr-123", Email: "dev@example.com"},
	}
	deployStore := newMemStore()
	mockVercel := &mockDeployProvider{accountLabel: "vercel-user"}

	deps := Deps{
		AuthStore:   authStore,
		DeployStore: deployStore,
		Vercel:      mockVercel,
	}
	mux := http.NewServeMux()
	Register(mux, deps)

	// 1. Initial connection status -> disconnected
	req := httptest.NewRequest("GET", "/deploy/connections/vercel", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var st map[string]any
	_ = json.NewDecoder(rec.Body).Decode(&st)
	if st["connected"] != false {
		t.Fatalf("expected connected=false, got %v", st["connected"])
	}

	// 2. Connect with bad token -> 401
	badBody := strings.NewReader(`{"token":"bad-token"}`)
	req = httptest.NewRequest("PUT", "/deploy/connections/vercel", badBody)
	req.Header.Set("Authorization", "Bearer valid-token")
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401 for bad token, got %d", rec.Code)
	}

	// 3. Connect with valid token -> 200
	validBody := strings.NewReader(`{"token":"good-vercel-pat-123","label":"My Team"}`)
	req = httptest.NewRequest("PUT", "/deploy/connections/vercel", validBody)
	req.Header.Set("Authorization", "Bearer valid-token")
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 for good token, got %d: %s", rec.Code, rec.Body.String())
	}

	// 4. Verify connection status -> connected
	req = httptest.NewRequest("GET", "/deploy/connections/vercel", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	_ = json.NewDecoder(rec.Body).Decode(&st)
	if st["connected"] != true || st["account_label"] != "My Team" {
		t.Fatalf("expected connected=true with label 'My Team', got %v", st)
	}

	// 5. Disconnect -> 204
	req = httptest.NewRequest("DELETE", "/deploy/connections/vercel", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("expected 204 on delete, got %d", rec.Code)
	}
}

func TestPublishReadinessAndTrigger(t *testing.T) {
	authStore := fakeAuthStore{
		user: auth.User{ID: "usr-123", Email: "dev@example.com"},
	}
	deployStore := newMemStore()
	_, _ = deployStore.SetConnection(context.Background(), "usr-123", "vercel", "good-pat", "alice")

	proj := projects.Project{
		ID:     "proj-abc",
		UserID: "usr-123",
		Name:   "CRM App",
	}
	projStore := fakeProjectStore{proj: proj}
	gitStore := fakeGitStore{
		gitInfo: &git.ProjectGitInfo{
			ProjectID:    "proj-abc",
			UserID:       "usr-123",
			RepoFullName: "alice/crm-app",
			CommitSHA:    "abc1234",
		},
	}

	mockVercel := &mockDeployProvider{
		accountLabel: "alice",
		projectID:    "v-proj-1",
		deployID:     "v-dep-1",
		liveURL:      "https://crm-app.vercel.app",
		status:       "ready",
	}

	deps := Deps{
		AuthStore:    authStore,
		DeployStore:  deployStore,
		ProjectStore: projStore,
		GitStore:     gitStore,
		Vercel:       mockVercel,
	}
	mux := http.NewServeMux()
	Register(mux, deps)

	// 1. Check readiness -> Path 1 web-only, git connected, provider connected
	req := httptest.NewRequest("GET", "/projects/proj-abc/publish", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var readiness PublishReadiness
	_ = json.NewDecoder(rec.Body).Decode(&readiness)
	if readiness.Path != 1 || !readiness.GitConnected || !readiness.ProviderConnected {
		t.Fatalf("readiness mismatch: %+v", readiness)
	}

	// 2. Trigger publish -> creates deployment and returns live_url
	req = httptest.NewRequest("POST", "/projects/proj-abc/publish", strings.NewReader(`{"provider":"vercel"}`))
	req.Header.Set("Authorization", "Bearer valid-token")
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var pubResp map[string]any
	_ = json.NewDecoder(rec.Body).Decode(&pubResp)
	if pubResp["live_url"] != "https://crm-app.vercel.app" {
		t.Fatalf("expected live_url https://crm-app.vercel.app, got %v", pubResp["live_url"])
	}

	// 3. List deployments -> 1 record
	req = httptest.NewRequest("GET", "/projects/proj-abc/deployments", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	var list []Deployment
	_ = json.NewDecoder(rec.Body).Decode(&list)
	if len(list) != 1 {
		t.Fatalf("expected 1 deployment, got %d", len(list))
	}

	// 4. Poll deployment -> status updated to ready
	req = httptest.NewRequest("GET", "/projects/proj-abc/deployments/"+list[0].ID, nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	var single Deployment
	_ = json.NewDecoder(rec.Body).Decode(&single)
	if single.Status != "ready" {
		t.Fatalf("expected status 'ready' after poll, got %s", single.Status)
	}
}

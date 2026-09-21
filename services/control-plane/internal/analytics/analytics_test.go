package analytics

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/connectors"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/deploy"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
)

// ─────────────────────────────────────────────────────────────────────────────
// In-memory fakes (package-internal, matches exact interface signatures)
// ─────────────────────────────────────────────────────────────────────────────

// memAnalyticsStore implements Store.
type memAnalyticsStore struct {
	data map[string]Config
}

func newMemAnalyticsStore() *memAnalyticsStore {
	return &memAnalyticsStore{data: make(map[string]Config)}
}

func (m *memAnalyticsStore) GetAnalytics(_ context.Context, projectID, _ string) (Config, error) {
	return m.data[projectID], nil
}

func (m *memAnalyticsStore) SetAnalytics(_ context.Context, projectID, _ string, cfg Config) error {
	if cfg.Provider != "ga4" {
		return ErrInvalidProvider
	}
	if cfg.PropertyID == "" {
		return ErrInvalidPropertyID
	}
	for _, r := range cfg.PropertyID {
		if r < '0' || r > '9' {
			return ErrInvalidPropertyID
		}
	}
	m.data[projectID] = cfg
	return nil
}

func (m *memAnalyticsStore) ClearAnalytics(_ context.Context, projectID, _ string) error {
	delete(m.data, projectID)
	return nil
}

// mockAuthStore satisfies auth.Store.
type mockAuthStore struct {
	user auth.User
}

func (m mockAuthStore) CreateUser(_ context.Context, _, _, _ string, _ int64) (auth.User, error) {
	return m.user, nil
}
func (m mockAuthStore) FindUserByEmail(_ context.Context, _ string) (auth.User, string, error) {
	return m.user, "hash", nil
}
func (m mockAuthStore) FindUserByID(_ context.Context, _ string) (auth.User, error) {
	return m.user, nil
}
func (m mockAuthStore) CreateSession(_ context.Context, _, _ string, _ time.Time) error {
	return nil
}
func (m mockAuthStore) FindUserBySessionToken(_ context.Context, token string) (auth.User, error) {
	// RequireUser hashes the bearer value with SHA-256 before calling this, so we just
	// accept any non-empty hash and return the test user.
	if token != "" {
		return m.user, nil
	}
	return auth.User{}, auth.ErrUnauthenticated
}
func (m mockAuthStore) DeleteSession(_ context.Context, _ string) error { return nil }

// mockProjectStore satisfies projects.Store.
type mockProjectStore struct {
	projectID string
}

func (m mockProjectStore) CreateProject(_ context.Context, _, _, _ string) (projects.Project, error) {
	return projects.Project{}, nil
}
func (m mockProjectStore) CreateProjectInWorkspace(_ context.Context, _, _, _, _ string) (projects.Project, error) {
	return projects.Project{}, nil
}
func (m mockProjectStore) ListProjects(_ context.Context, _, _ string, _ int) ([]projects.Project, error) {
	return nil, nil
}
func (m mockProjectStore) ListWorkspaceProjects(_ context.Context, _, _, _ string, _ int) ([]projects.Project, error) {
	return nil, nil
}
func (m mockProjectStore) GetUserProjectRole(_ context.Context, _, _ string) (string, error) {
	return "owner", nil
}
func (m mockProjectStore) GetProject(_ context.Context, id, _ string) (projects.Project, error) {
	if id == m.projectID {
		return projects.Project{ID: id, Name: "test-project"}, nil
	}
	return projects.Project{}, projects.ErrProjectNotFound
}
func (m mockProjectStore) UpdateProject(_ context.Context, _, _ string, _ *string, _ *string) (projects.Project, error) {
	return projects.Project{}, nil
}
func (m mockProjectStore) UpdateProjectBuildResult(_ context.Context, _, _, _, _, _ string, _ json.RawMessage, _ int, _ int) error {
	return nil
}
func (m mockProjectStore) DebitProjectCredits(_ context.Context, _, _ string, _ int64, _ string) (int64, int64, error) {
	return 0, 0, nil
}
func (m mockProjectStore) ArchiveProject(_ context.Context, _, _ string) error     { return nil }
func (m mockProjectStore) DeleteProject(_ context.Context, _, _ string) error      { return nil }
func (m mockProjectStore) TouchProjectOpened(_ context.Context, _, _ string) error { return nil }

// noopConnectorStore satisfies connectors.Store.
type noopConnectorStore struct{}

func (n noopConnectorStore) ListProjectConnectors(_ context.Context, _ string) ([]connectors.ProjectConnector, error) {
	return nil, nil
}
func (n noopConnectorStore) GetProjectConnector(_ context.Context, _, _ string) (connectors.ProjectConnector, error) {
	return connectors.ProjectConnector{}, connectors.ErrNotFound
}
func (n noopConnectorStore) SaveProjectConnector(_ context.Context, _, _ string, _ map[string]any, _ bool) (connectors.ProjectConnector, error) {
	return connectors.ProjectConnector{}, nil
}
func (n noopConnectorStore) DeleteProjectConnector(_ context.Context, _, _ string) error {
	return nil
}

// noopDeployStore satisfies deploy.Store.
type noopDeployStore struct{}

func (n noopDeployStore) GetConnection(_ context.Context, _, _ string) (*deploy.Connection, string, error) {
	return nil, "", nil
}
func (n noopDeployStore) GetConnectionStatus(_ context.Context, _, _ string) (*deploy.Connection, error) {
	return nil, nil
}
func (n noopDeployStore) SetConnection(_ context.Context, _, _, _, _ string) (*deploy.Connection, error) {
	return nil, nil
}
func (n noopDeployStore) DeleteConnection(_ context.Context, _, _ string) error { return nil }
func (n noopDeployStore) CreateDeployment(_ context.Context, d *deploy.Deployment) (*deploy.Deployment, error) {
	return d, nil
}
func (n noopDeployStore) UpdateDeployment(_ context.Context, _, _, _, _ string, _ *time.Time) error {
	return nil
}
func (n noopDeployStore) GetDeployment(_ context.Context, _ string) (*deploy.Deployment, error) {
	return nil, nil
}
func (n noopDeployStore) GetLatestDeployment(_ context.Context, _ string) (*deploy.Deployment, error) {
	return nil, nil
}
func (n noopDeployStore) ListDeployments(_ context.Context, _ string, _ int) ([]deploy.Deployment, error) {
	return nil, nil
}
func (n noopDeployStore) UpdateProjectDeployMeta(_ context.Context, _, _, _, _ string) error {
	return nil
}
func (n noopDeployStore) GetProjectDeployMeta(_ context.Context, _ string) (string, string, string, error) {
	return "", "", "", nil
}

// ─────────────────────────────────────────────────────────────────────────────
// Test helpers
// ─────────────────────────────────────────────────────────────────────────────

const (
	testUserID    = "user-001"
	testProjectID = "proj-abc"
)

func testDeps() (Deps, *memAnalyticsStore) {
	store := newMemAnalyticsStore()
	deps := Deps{
		AuthStore:      mockAuthStore{user: auth.User{ID: testUserID, Email: "test@example.com"}},
		ProjectStore:   mockProjectStore{projectID: testProjectID},
		AnalyticsStore: store,
		ConnectorStore: noopConnectorStore{},
		DeployStore:    noopDeployStore{},
		GA4Client:      NewGA4Client(nil),
	}
	return deps, store
}

func authedRequest(method, target, body string) *http.Request {
	var b *strings.Reader
	if body != "" {
		b = strings.NewReader(body)
	} else {
		b = strings.NewReader("")
	}
	r := httptest.NewRequest(method, target, b)
	r.Header.Set("Authorization", "Bearer valid-token")
	if body != "" {
		r.Header.Set("Content-Type", "application/json")
	}
	return r
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

func TestGetAnalytics_NotConfigured(t *testing.T) {
	deps, _ := testDeps()
	mux := http.NewServeMux()
	Register(mux, deps)

	r := authedRequest("GET", "/projects/"+testProjectID+"/analytics", "")
	r.SetPathValue("id", testProjectID)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, r)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", w.Code, w.Body.String())
	}
	var resp AnalyticsStatus
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatal(err)
	}
	if resp.Connected {
		t.Error("expected Connected=false for unconfigured project")
	}
}

func TestSetAndGetAnalytics(t *testing.T) {
	deps, store := testDeps()
	mux := http.NewServeMux()
	Register(mux, deps)

	body := `{"provider":"ga4","property_id":"123456789"}`
	r := authedRequest("PUT", "/projects/"+testProjectID+"/analytics", body)
	r.SetPathValue("id", testProjectID)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, r)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 on PUT, got %d: %s", w.Code, w.Body.String())
	}

	cfg, err := store.GetAnalytics(context.Background(), testProjectID, testUserID)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Provider != "ga4" || cfg.PropertyID != "123456789" {
		t.Errorf("unexpected config: %+v", cfg)
	}
}

func TestSetAnalytics_InvalidProvider(t *testing.T) {
	deps, _ := testDeps()
	mux := http.NewServeMux()
	Register(mux, deps)

	r := authedRequest("PUT", "/projects/"+testProjectID+"/analytics", `{"provider":"mixpanel","property_id":"123"}`)
	r.SetPathValue("id", testProjectID)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, r)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for invalid provider, got %d: %s", w.Code, w.Body.String())
	}
}

func TestSetAnalytics_InvalidPropertyID(t *testing.T) {
	deps, _ := testDeps()
	mux := http.NewServeMux()
	Register(mux, deps)

	r := authedRequest("PUT", "/projects/"+testProjectID+"/analytics", `{"provider":"ga4","property_id":"not-a-number"}`)
	r.SetPathValue("id", testProjectID)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, r)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for invalid property_id, got %d: %s", w.Code, w.Body.String())
	}
}

func TestClearAnalytics(t *testing.T) {
	deps, store := testDeps()
	_ = store.SetAnalytics(context.Background(), testProjectID, testUserID, Config{Provider: "ga4", PropertyID: "111"})

	mux := http.NewServeMux()
	Register(mux, deps)

	r := authedRequest("DELETE", "/projects/"+testProjectID+"/analytics", "")
	r.SetPathValue("id", testProjectID)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, r)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 on DELETE, got %d: %s", w.Code, w.Body.String())
	}
	cfg, _ := store.GetAnalytics(context.Background(), testProjectID, testUserID)
	if cfg.Provider != "" {
		t.Errorf("expected empty config after clear, got: %+v", cfg)
	}
}

func TestGetReport_NotConfigured(t *testing.T) {
	deps, _ := testDeps()
	mux := http.NewServeMux()
	Register(mux, deps)

	r := authedRequest("GET", "/projects/"+testProjectID+"/analytics/report?range=7d", "")
	r.SetPathValue("id", testProjectID)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, r)

	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("expected 422 when analytics not configured, got %d: %s", w.Code, w.Body.String())
	}
}

func TestGetReport_InvalidRange(t *testing.T) {
	deps, store := testDeps()
	_ = store.SetAnalytics(context.Background(), testProjectID, testUserID, Config{Provider: "ga4", PropertyID: "111"})

	mux := http.NewServeMux()
	Register(mux, deps)

	r := authedRequest("GET", "/projects/"+testProjectID+"/analytics/report?range=invalid", "")
	r.SetPathValue("id", testProjectID)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, r)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for invalid range, got %d: %s", w.Code, w.Body.String())
	}
}

func TestTenantIsolation_WrongProject(t *testing.T) {
	deps, _ := testDeps()
	mux := http.NewServeMux()
	Register(mux, deps)

	r := authedRequest("GET", "/projects/other-project/analytics", "")
	r.SetPathValue("id", "other-project")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, r)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401 for wrong project, got %d: %s", w.Code, w.Body.String())
	}
}

func TestCacheInvalidation(t *testing.T) {
	ga4Client := NewGA4Client(nil)
	// Should not panic even if nothing is cached.
	ga4Client.InvalidateCache(testProjectID)
}

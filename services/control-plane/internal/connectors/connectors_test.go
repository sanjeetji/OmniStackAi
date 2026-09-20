package connectors

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
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

type fakeProjectStore struct {
	project projects.Project
	err     error
}

func (f fakeProjectStore) CreateProject(ctx context.Context, userID, name, description string) (projects.Project, error) {
	return f.project, f.err
}
func (f fakeProjectStore) ListProjects(ctx context.Context, userID, status string, limit int) ([]projects.Project, error) {
	return []projects.Project{f.project}, f.err
}
func (f fakeProjectStore) GetProject(ctx context.Context, id, userID string) (projects.Project, error) {
	if f.err != nil {
		return projects.Project{}, f.err
	}
	return f.project, nil
}
func (f fakeProjectStore) UpdateProject(ctx context.Context, id, userID string, name, description *string) (projects.Project, error) {
	return f.project, f.err
}
func (f fakeProjectStore) UpdateProjectBuildResult(ctx context.Context, id, userID string, name, prompt, commitSHA string, entities json.RawMessage, fileCount int, messageDelta int) error {
	return f.err
}
func (f fakeProjectStore) DebitProjectCredits(ctx context.Context, userID, projectID string, requested int64, reason string) (int64, int64, error) {
	return 0, 0, f.err
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

type memConnectorStore struct {
	connectors map[string]ProjectConnector // key: projectID:provider
}

func newMemConnectorStore() *memConnectorStore {
	return &memConnectorStore{connectors: make(map[string]ProjectConnector)}
}

func (m *memConnectorStore) ListProjectConnectors(ctx context.Context, projectID string) ([]ProjectConnector, error) {
	var list []ProjectConnector
	for _, pc := range m.connectors {
		if pc.ProjectID == projectID {
			list = append(list, pc)
		}
	}
	return list, nil
}

func (m *memConnectorStore) GetProjectConnector(ctx context.Context, projectID, provider string) (ProjectConnector, error) {
	key := fmt.Sprintf("%s:%s", projectID, provider)
	pc, ok := m.connectors[key]
	if !ok {
		return ProjectConnector{}, ErrNotFound
	}
	return pc, nil
}

func (m *memConnectorStore) SaveProjectConnector(ctx context.Context, projectID, provider string, config map[string]any, enabled bool) (ProjectConnector, error) {
	key := fmt.Sprintf("%s:%s", projectID, provider)
	pc := ProjectConnector{
		ID:        fmt.Sprintf("conn-%d", len(m.connectors)+1),
		ProjectID: projectID,
		Provider:  provider,
		Config:    config,
		Enabled:   enabled,
		CreatedAt: time.Now().UTC(),
	}
	m.connectors[key] = pc
	return pc, nil
}

func (m *memConnectorStore) DeleteProjectConnector(ctx context.Context, projectID, provider string) error {
	key := fmt.Sprintf("%s:%s", projectID, provider)
	if _, ok := m.connectors[key]; !ok {
		return ErrNotFound
	}
	delete(m.connectors, key)
	return nil
}

func TestCatalogDefinitions(t *testing.T) {
	ga4, ok := GetDefinition("ga4")
	if !ok || ga4.Name != "Google Analytics 4" {
		t.Fatalf("ga4 missing from catalog: %+v", ga4)
	}

	resend, ok := GetDefinition("resend")
	if !ok || resend.Name != "Resend Email" {
		t.Fatalf("resend missing from catalog: %+v", resend)
	}

	smtp, ok := GetDefinition("smtp")
	if !ok || smtp.Name != "Custom SMTP" {
		t.Fatalf("smtp missing from catalog: %+v", smtp)
	}
}

func TestProjectConnectorsLifecycle(t *testing.T) {
	authStore := fakeAuthStore{
		user: auth.User{ID: "usr-123", Email: "dev@example.com"},
	}
	projectStore := fakeProjectStore{
		project: projects.Project{ID: "proj-123", UserID: "usr-123"},
	}
	connectorStore := newMemConnectorStore()

	deps := Deps{
		AuthStore:      authStore,
		ProjectStore:   projectStore,
		ConnectorStore: connectorStore,
	}

	mux := http.NewServeMux()
	Register(mux, deps)

	// 1. Get catalogue
	req := httptest.NewRequest("GET", "/connectors", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("GET /connectors status = %d", w.Code)
	}

	// 2. Initially empty project connectors
	req = httptest.NewRequest("GET", "/projects/proj-123/connectors", nil)
	req.Header.Set("Authorization", "Bearer token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("GET /projects/proj-123/connectors status = %d", w.Code)
	}

	// 3. Test GA4 invalid measurement ID
	req = httptest.NewRequest("POST", "/projects/proj-123/connectors/ga4/test", bytes.NewReader([]byte(`{"config":{"measurement_id":"bad-id"}}`)))
	req.Header.Set("Authorization", "Bearer token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("POST /test invalid GA4 status = %d, want 400", w.Code)
	}

	// 4. Test GA4 valid measurement ID
	req = httptest.NewRequest("POST", "/projects/proj-123/connectors/ga4/test", bytes.NewReader([]byte(`{"config":{"measurement_id":"G-ABC123XYZ4"}}`)))
	req.Header.Set("Authorization", "Bearer token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("POST /test valid GA4 status = %d, want 200", w.Code)
	}

	// 5. Save GA4 connector
	saveBody := bytes.NewReader([]byte(`{"config":{"measurement_id":"G-ABC123XYZ4"}}`))
	req = httptest.NewRequest("PUT", "/projects/proj-123/connectors/ga4", saveBody)
	req.Header.Set("Authorization", "Bearer token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("PUT /connectors/ga4 status = %d, body = %s", w.Code, w.Body.String())
	}

	var saved ProjectConnector
	if err := json.Unmarshal(w.Body.Bytes(), &saved); err != nil {
		t.Fatalf("unmarshal saved connector: %v", err)
	}
	if saved.Provider != "ga4" || !saved.Enabled {
		t.Fatalf("unexpected saved connector: %+v", saved)
	}

	// 6. Delete connector
	req = httptest.NewRequest("DELETE", "/projects/proj-123/connectors/ga4", nil)
	req.Header.Set("Authorization", "Bearer token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("DELETE /connectors/ga4 status = %d", w.Code)
	}
}

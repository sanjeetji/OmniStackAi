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
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/integrations"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/secrets"
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
func (f fakeProjectStore) CreateProjectInWorkspace(ctx context.Context, userID, workspaceID, name, description string) (projects.Project, error) {
	return f.project, f.err
}
func (f fakeProjectStore) ListProjects(ctx context.Context, userID, status string, limit int) ([]projects.Project, error) {
	return []projects.Project{f.project}, f.err
}
func (f fakeProjectStore) ListWorkspaceProjects(ctx context.Context, userID, workspaceID, status string, limit int) ([]projects.Project, error) {
	return []projects.Project{f.project}, f.err
}
func (f fakeProjectStore) GetUserProjectRole(ctx context.Context, projectID, userID string) (string, error) {
	return "owner", nil
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

type memSecrets struct {
	values    map[string]string
	available bool
}

func (m *memSecrets) ListSecrets(context.Context, string, string) ([]secrets.SecretMetadata, error) {
	return nil, nil
}
func (m *memSecrets) SetSecret(_ context.Context, _, _, key, value, _ string) (*secrets.SecretMetadata, error) {
	m.values[key] = value
	return &secrets.SecretMetadata{Key: key}, nil
}
func (m *memSecrets) DeleteSecret(_ context.Context, _, _, key string) error {
	delete(m.values, key)
	return nil
}
func (m *memSecrets) RevealSecret(_ context.Context, _, _, key string) (string, error) {
	return m.values[key], nil
}
func (m *memSecrets) ForProject(context.Context, string) (map[string]string, error) {
	out := map[string]string{}
	for k, v := range m.values {
		out[k] = v
	}
	return out, nil
}
func (m *memSecrets) IsAvailable() bool { return m.available }

// PC-013: a connector's test asks the provider; its credentials are project secrets.
func TestProjectConnectorsLifecycle(t *testing.T) {
	resend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/domains" || r.Header.Get("Authorization") != "Bearer re_good_key" {
			w.WriteHeader(http.StatusUnauthorized)
			_, _ = w.Write([]byte(`{"name":"validation_error"}`))
			return
		}
		_, _ = w.Write([]byte(`{"data":[{"name":"example.com","status":"verified"},{"name":"new.example","status":"pending"}]}`))
	}))
	defer resend.Close()

	store := newMemConnectorStore()
	sec := &memSecrets{values: map[string]string{}, available: true}
	deps := Deps{
		AuthStore:      fakeAuthStore{user: auth.User{ID: "usr-123", Email: "dev@example.com"}},
		ProjectStore:   fakeProjectStore{project: projects.Project{ID: "proj-123", UserID: "usr-123"}},
		ConnectorStore: store,
		Secrets:        sec,
	}
	deps.Health = integrations.Service{
		Checker:        integrations.Checker{BaseURL: resend.URL},
		ProjectSecrets: sec.ForProject,
		ConnectorConfig: func(ctx context.Context, projectID, provider string) (map[string]any, error) {
			pc, err := store.GetProjectConnector(ctx, projectID, provider)
			return pc.Config, err
		},
	}
	mux := http.NewServeMux()
	Register(mux, deps)
	do := func(method, path, body string) (int, map[string]any) {
		t.Helper()
		req := httptest.NewRequest(method, path, bytes.NewReader([]byte(body)))
		req.Header.Set("Authorization", "Bearer token")
		w := httptest.NewRecorder()
		mux.ServeHTTP(w, req)
		var out map[string]any
		_ = json.Unmarshal(w.Body.Bytes(), &out)
		return w.Code, out
	}

	// The catalog speaks the console's field names.
	_, cat := do("GET", "/connectors", "")
	raw, _ := json.Marshal(cat)
	if !bytes.Contains(raw, []byte(`"config_fields"`)) || !bytes.Contains(raw, []byte(`"name":"api_key"`)) {
		t.Fatalf("catalog shape: %s", raw)
	}

	// GA4 can only be checked for form, and says so rather than claiming it is verified.
	if _, out := do("POST", "/projects/proj-123/connectors/ga4/test", `{"config":{"measurement_id":"bad-id"}}`); out["status"] != "failed" {
		t.Fatalf("bad GA4 id: %v", out)
	}
	if _, out := do("POST", "/projects/proj-123/connectors/ga4/test", `{"config":{"measurement_id":"G-ABC123XYZ4"}}`); out["status"] != "unchecked" || out["success"] != false {
		t.Fatalf("GA4 id: %v", out)
	}
	if code, _ := do("PUT", "/projects/proj-123/connectors/ga4", `{"config":{"measurement_id":"G-ABC123XYZ4"}}`); code != 200 {
		t.Fatalf("save ga4: %d", code)
	}

	// Resend: a made-up key that merely looks right is refused by the provider.
	if _, out := do("POST", "/projects/proj-123/connectors/resend/test", `{"config":{"api_key":"re_abcdef123456","from_email":"a@example.com"}}`); out["status"] != "failed" {
		t.Fatalf("a made-up key passed: %v", out)
	}
	if _, out := do("POST", "/projects/proj-123/connectors/resend/test", `{"config":{"api_key":"re_good_key","from_email":"a@new.example"}}`); out["status"] != "failed" {
		t.Fatalf("an unverified sending domain passed: %v", out)
	}
	if _, out := do("POST", "/projects/proj-123/connectors/resend/test", `{"config":{"api_key":"re_good_key","from_email":"a@example.com"}}`); out["status"] != "ok" {
		t.Fatalf("a good key and domain failed: %v", out)
	}

	// Saving puts the credentials in the project's secrets, not in the connector's settings.
	code, saved := do("PUT", "/projects/proj-123/connectors/resend", `{"config":{"api_key":"re_good_key","from_email":"a@example.com"}}`)
	if code != 200 || sec.values["RESEND_API_KEY"] != "re_good_key" || sec.values["RESEND_FROM_EMAIL"] != "a@example.com" {
		t.Fatalf("save resend: %d %v %v", code, saved, sec.values)
	}
	if pc, _ := store.GetProjectConnector(context.Background(), "proj-123", "resend"); pc.Config["api_key"] != nil {
		t.Fatalf("the key is in the plain settings: %v", pc.Config)
	}
	if cfg := saved["config"].(map[string]any); cfg["api_key"] != masked || cfg["from_email"] != "a@example.com" {
		t.Fatalf("shown settings: %v", cfg)
	}
	_, list := do("GET", "/projects/proj-123/connectors", "")
	if raw, _ := json.Marshal(list); bytes.Contains(raw, []byte("re_good_key")) {
		t.Fatalf("the key reached the console: %s", raw)
	}

	// The saved settings test clean; saving the masked value keeps the key.
	if _, out := do("POST", "/projects/proj-123/connectors/resend/test", `{}`); out["status"] != "ok" {
		t.Fatalf("saved settings: %v", out)
	}
	do("PUT", "/projects/proj-123/connectors/resend", `{"config":{"api_key":"`+masked+`","from_email":"b@example.com"}}`)
	if sec.values["RESEND_API_KEY"] != "re_good_key" || sec.values["RESEND_FROM_EMAIL"] != "b@example.com" {
		t.Fatalf("masked resave: %v", sec.values)
	}

	// Disconnecting removes the credentials too.
	if code, _ := do("DELETE", "/projects/proj-123/connectors/resend", ""); code != 200 {
		t.Fatalf("delete: %d", code)
	}
	if len(sec.values) != 0 {
		t.Fatalf("credentials left behind: %v", sec.values)
	}

	// Without encrypted storage, credentials are refused rather than stored in the clear.
	sec.available = false
	if code, _ := do("PUT", "/projects/proj-123/connectors/smtp", `{"config":{"host":"smtp.example.com","username":"u","password":"p","from_email":"n@example.com"}}`); code != http.StatusServiceUnavailable {
		t.Fatalf("save without secret storage: %d", code)
	}
}

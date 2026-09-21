package templates

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
)

type fakeAuthStore struct{ user auth.User }

func (fakeAuthStore) CreateUser(context.Context, string, string, string, int64) (auth.User, error) {
	panic("unused")
}
func (fakeAuthStore) FindUserByEmail(context.Context, string) (auth.User, string, error) {
	panic("unused")
}
func (fakeAuthStore) FindUserByID(context.Context, string) (auth.User, error) { panic("unused") }
func (fakeAuthStore) CreateSession(context.Context, string, string, time.Time) error {
	panic("unused")
}
func (s fakeAuthStore) FindUserBySessionToken(context.Context, string) (auth.User, error) {
	return s.user, nil
}
func (fakeAuthStore) DeleteSession(context.Context, string) error { panic("unused") }

// fakeProjects implements only what the templates package uses; anything else panics.
type fakeProjects struct {
	projects.Store
	mu        sync.Mutex
	created   []projects.Project
	deleted   []string
	updated   map[string]int
	updateErr error
}

func (f *fakeProjects) CreateProjectInWorkspace(_ context.Context, userID, workspaceID, name, description string) (projects.Project, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	if workspaceID == "not-a-member" {
		return projects.Project{}, projects.ErrUnauthorized
	}
	p := projects.Project{ID: "p-" + name, UserID: userID, Name: name, Description: description}
	f.created = append(f.created, p)
	return p, nil
}

func (f *fakeProjects) UpdateProjectBuildResult(_ context.Context, id, _ string, _, _, commitSHA string, _ json.RawMessage, fileCount int, _ int) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	if f.updateErr != nil {
		return f.updateErr
	}
	if f.updated == nil {
		f.updated = map[string]int{}
	}
	if commitSHA == "" {
		return errors.New("commit sha missing")
	}
	f.updated[id] = fileCount
	return nil
}

func (f *fakeProjects) GetProject(_ context.Context, id, userID string) (projects.Project, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	for _, p := range f.created {
		if p.ID == id && p.UserID == userID {
			p.FileCount = f.updated[id]
			return p, nil
		}
	}
	return projects.Project{}, projects.ErrProjectNotFound
}

func (f *fakeProjects) DeleteProject(_ context.Context, id, _ string) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.deleted = append(f.deleted, id)
	return nil
}

type fakeTemplateStore struct {
	mu        sync.Mutex
	rows      map[string]Provenance
	recordErr error
}

func (s *fakeTemplateStore) RecordProjectTemplate(_ context.Context, projectID string, p Provenance) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.recordErr != nil {
		return s.recordErr
	}
	if s.rows == nil {
		s.rows = map[string]Provenance{}
	}
	s.rows[projectID] = p
	return nil
}

func (s *fakeTemplateStore) GetProjectTemplate(_ context.Context, projectID string) (Provenance, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.rows[projectID]
	if !ok {
		return Provenance{}, ErrNotFromTemplate
	}
	return p, nil
}

// fakeEngine mimics the agent-engine template routes.
type fakeEngine struct {
	mu               sync.Mutex
	calls            []string
	instantiateCode  int
	instantiateBody  string
	instantiatedSlug string
}

func (e *fakeEngine) handler(t *testing.T) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		e.mu.Lock()
		e.calls = append(e.calls, r.Method+" "+r.URL.Path)
		e.mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		switch {
		case r.Method == http.MethodGet && r.URL.Path == "/api/templates":
			_, _ = io.WriteString(w, `{"templates":[{"slug":"ride-now","name":"RideNow"}]}`)
		case r.Method == http.MethodGet && r.URL.Path == "/api/templates/ride-now/assets/media/cover.png":
			w.Header().Set("Content-Type", "image/png")
			_, _ = io.WriteString(w, "PNGDATA")
		case r.Method == http.MethodGet && strings.Contains(r.URL.Path, "/assets/"):
			w.WriteHeader(http.StatusNotFound)
			_, _ = io.WriteString(w, `{"error":"asset not found"}`)
		case r.Method == http.MethodGet && r.URL.Path == "/api/templates/ride-now":
			_, _ = io.WriteString(w, `{"slug":"ride-now","name":"RideNow","tagline":"Ride-hailing for your city.","version":"1.0.0"}`)
		case r.Method == http.MethodGet && strings.HasPrefix(r.URL.Path, "/api/templates/"):
			w.WriteHeader(http.StatusNotFound)
			_, _ = io.WriteString(w, `{"error":"template not found"}`)
		case r.Method == http.MethodPost && strings.HasSuffix(r.URL.Path, "/from-template"):
			var body struct {
				Slug string `json:"slug"`
			}
			_ = json.NewDecoder(r.Body).Decode(&body)
			e.mu.Lock()
			e.instantiatedSlug = body.Slug
			code, payload := e.instantiateCode, e.instantiateBody
			e.mu.Unlock()
			if code == 0 {
				code = http.StatusCreated
				payload = `{"commit_sha":"abc1234","file_count":212,"entities":["Trip","Driver"],"template":{"slug":"ride-now","version":"1.0.0","digest":"sha256:feed"}}`
			}
			w.WriteHeader(code)
			_, _ = io.WriteString(w, payload)
		case r.Method == http.MethodDelete && strings.HasPrefix(r.URL.Path, "/api/workspaces/"):
			_, _ = io.WriteString(w, `{"status":"purged"}`)
		default:
			t.Errorf("unexpected engine call %s %s", r.Method, r.URL.Path)
			w.WriteHeader(http.StatusNotFound)
		}
	})
}

type harness struct {
	mux       *http.ServeMux
	engine    *fakeEngine
	projects  *fakeProjects
	templates *fakeTemplateStore
}

func newHarness(t *testing.T) *harness {
	t.Helper()
	engine := &fakeEngine{}
	upstream := httptest.NewServer(engine.handler(t))
	t.Cleanup(upstream.Close)
	h := &harness{mux: http.NewServeMux(), engine: engine, projects: &fakeProjects{}, templates: &fakeTemplateStore{}}
	Register(h.mux, Deps{
		AuthStore:      fakeAuthStore{user: auth.User{ID: "u1"}},
		ProjectStore:   h.projects,
		TemplateStore:  h.templates,
		AgentEngineURL: upstream.URL,
	})
	return h
}

func (h *harness) do(method, path, body string, authed bool) *httptest.ResponseRecorder {
	var reader io.Reader
	if body != "" {
		reader = strings.NewReader(body)
	}
	req := httptest.NewRequest(method, path, reader)
	if authed {
		req.Header.Set("Authorization", "Bearer token")
	}
	rec := httptest.NewRecorder()
	h.mux.ServeHTTP(rec, req)
	return rec
}

func TestCatalogueIsPublicAndProxied(t *testing.T) {
	h := newHarness(t)
	rec := h.do(http.MethodGet, "/templates", "", false)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "ride-now") {
		t.Fatalf("GET /templates = %d %s", rec.Code, rec.Body.String())
	}
	rec = h.do(http.MethodGet, "/templates/ride-now", "", false)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "RideNow") {
		t.Fatalf("GET /templates/ride-now = %d %s", rec.Code, rec.Body.String())
	}
	rec = h.do(http.MethodGet, "/templates/nope", "", false)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("GET /templates/nope = %d, want 404", rec.Code)
	}
}

func TestUseTemplateRequiresAuth(t *testing.T) {
	h := newHarness(t)
	rec := h.do(http.MethodPost, "/templates/ride-now/use", "", false)
	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", rec.Code)
	}
	if len(h.engine.calls) != 0 || len(h.projects.created) != 0 {
		t.Fatalf("unauthenticated use must not touch the engine or create a project: %v", h.engine.calls)
	}
}

func TestUseTemplateCreatesTheCallersOwnProject(t *testing.T) {
	h := newHarness(t)
	rec := h.do(http.MethodPost, "/templates/ride-now/use", "", true)
	if rec.Code != http.StatusCreated {
		t.Fatalf("status = %d %s", rec.Code, rec.Body.String())
	}
	var body struct {
		Project  projects.Project `json:"project"`
		Template Provenance       `json:"template"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body.Project.Name != "RideNow" || body.Project.UserID != "u1" || body.Project.FileCount != 212 {
		t.Fatalf("project = %+v", body.Project)
	}
	if body.Project.Description != "Ride-hailing for your city." {
		t.Fatalf("description = %q", body.Project.Description)
	}
	if body.Template.Slug != "ride-now" || body.Template.Digest != "sha256:feed" {
		t.Fatalf("template = %+v", body.Template)
	}
	if h.engine.instantiatedSlug != "ride-now" {
		t.Fatalf("engine instantiated %q", h.engine.instantiatedSlug)
	}
	if got := h.templates.rows[body.Project.ID]; got.Version != "1.0.0" {
		t.Fatalf("provenance not recorded: %+v", h.templates.rows)
	}
	if len(h.projects.deleted) != 0 {
		t.Fatalf("a successful use must not delete anything: %v", h.projects.deleted)
	}
}

func TestUseTemplateHonoursACustomName(t *testing.T) {
	h := newHarness(t)
	rec := h.do(http.MethodPost, "/templates/ride-now/use", `{"name":"  CityCabs  "}`, true)
	if rec.Code != http.StatusCreated || h.projects.created[0].Name != "CityCabs" {
		t.Fatalf("status = %d, created = %+v", rec.Code, h.projects.created)
	}
}

func TestUseUnknownTemplateCreatesNothing(t *testing.T) {
	h := newHarness(t)
	rec := h.do(http.MethodPost, "/templates/nope/use", "", true)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", rec.Code)
	}
	if len(h.projects.created) != 0 {
		t.Fatalf("no project may be created for an unknown template")
	}
}

func TestUseTemplateInAForeignWorkspaceIsForbidden(t *testing.T) {
	h := newHarness(t)
	rec := h.do(http.MethodPost, "/templates/ride-now/use", `{"workspace_id":"not-a-member"}`, true)
	if rec.Code != http.StatusForbidden {
		t.Fatalf("status = %d, want 403", rec.Code)
	}
}

func TestFailedCopyRemovesTheProject(t *testing.T) {
	h := newHarness(t)
	h.engine.instantiateCode = http.StatusBadGateway
	h.engine.instantiateBody = `{"error":"git commit failed"}`
	rec := h.do(http.MethodPost, "/templates/ride-now/use", "", true)
	if rec.Code != http.StatusBadGateway || !strings.Contains(rec.Body.String(), "git commit failed") {
		t.Fatalf("status = %d %s", rec.Code, rec.Body.String())
	}
	if len(h.projects.deleted) != 1 || h.projects.deleted[0] != h.projects.created[0].ID {
		t.Fatalf("the half-made project must be deleted: %v", h.projects.deleted)
	}
	if len(h.templates.rows) != 0 {
		t.Fatalf("no provenance may be recorded for a failed copy")
	}
}

func TestFailedBookkeepingRemovesProjectAndWorkspace(t *testing.T) {
	h := newHarness(t)
	h.templates.recordErr = errors.New("db down")
	rec := h.do(http.MethodPost, "/templates/ride-now/use", "", true)
	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500", rec.Code)
	}
	if len(h.projects.deleted) != 1 {
		t.Fatalf("project must be deleted: %v", h.projects.deleted)
	}
	purged := false
	for _, call := range h.engine.calls {
		if strings.HasPrefix(call, "DELETE /api/workspaces/") {
			purged = true
		}
	}
	if !purged {
		t.Fatalf("the copied workspace must be purged: %v", h.engine.calls)
	}
}

func TestProjectTemplateProvenance(t *testing.T) {
	h := newHarness(t)
	rec := h.do(http.MethodPost, "/templates/ride-now/use", "", true)
	if rec.Code != http.StatusCreated {
		t.Fatalf("use: %d", rec.Code)
	}
	id := h.projects.created[0].ID

	rec = h.do(http.MethodGet, "/projects/"+id+"/template", "", true)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"slug":"ride-now"`) {
		t.Fatalf("provenance = %d %s", rec.Code, rec.Body.String())
	}
	rec = h.do(http.MethodGet, "/projects/unknown/template", "", true)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("foreign/unknown project = %d, want 404", rec.Code)
	}
	h.projects.created = append(h.projects.created, projects.Project{ID: "p-prompt", UserID: "u1"})
	rec = h.do(http.MethodGet, "/projects/p-prompt/template", "", true)
	if rec.Code != http.StatusNotFound || !strings.Contains(rec.Body.String(), "not started from a template") {
		t.Fatalf("prompt project = %d %s", rec.Code, rec.Body.String())
	}
	rec = h.do(http.MethodGet, "/projects/"+id+"/template", "", false)
	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("unauthenticated = %d, want 401", rec.Code)
	}
}

func TestTemplateAssetsArePublicCacheableAndPassThroughContentType(t *testing.T) {
	h := newHarness(t)
	rec := h.do(http.MethodGet, "/templates/ride-now/assets/media/cover.png", "", false)
	if rec.Code != http.StatusOK || rec.Body.String() != "PNGDATA" {
		t.Fatalf("asset = %d %q", rec.Code, rec.Body.String())
	}
	if got := rec.Header().Get("Content-Type"); got != "image/png" {
		t.Fatalf("content type = %q", got)
	}
	if got := rec.Header().Get("Cache-Control"); !strings.Contains(got, "max-age") {
		t.Fatalf("cache control = %q", got)
	}
	if got := rec.Header().Get("X-Content-Type-Options"); got != "nosniff" {
		t.Fatalf("nosniff missing: %q", got)
	}
	rec = h.do(http.MethodGet, "/templates/ride-now/assets/template.json", "", false)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("undeclared asset = %d, want 404", rec.Code)
	}
	if rec.Header().Get("Cache-Control") != "" {
		t.Fatalf("a 404 must not be cached")
	}
}

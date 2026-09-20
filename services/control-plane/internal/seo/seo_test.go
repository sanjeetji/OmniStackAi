package seo

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

type mockSEOStore struct {
	projectSEO map[string]*ProjectSEO
	pageSEOs   map[string]map[string]*PageSEO
	owners     map[string]string // projectID -> userID
}

func newMockSEOStore() *mockSEOStore {
	return &mockSEOStore{
		projectSEO: make(map[string]*ProjectSEO),
		pageSEOs:   make(map[string]map[string]*PageSEO),
		owners:     make(map[string]string),
	}
}

func (m *mockSEOStore) GetProjectSEO(ctx context.Context, projectID, userID string) (*ProjectSEO, error) {
	owner, ok := m.owners[projectID]
	if !ok || owner != userID {
		return nil, ErrProjectNotFound
	}
	if seo, ok := m.projectSEO[projectID]; ok {
		return seo, nil
	}
	return &ProjectSEO{
		ProjectID:    projectID,
		SiteName:     "Default Site",
		DefaultTitle: "Default Title",
		UpdatedAt:    time.Now(),
	}, nil
}

func (m *mockSEOStore) SetProjectSEO(ctx context.Context, projectID, userID string, seo *ProjectSEO) (*ProjectSEO, error) {
	owner, ok := m.owners[projectID]
	if !ok || owner != userID {
		return nil, ErrProjectNotFound
	}
	seo.ProjectID = projectID
	seo.UpdatedAt = time.Now()
	m.projectSEO[projectID] = seo
	return seo, nil
}

func (m *mockSEOStore) GetProjectPageSEOs(ctx context.Context, projectID, userID string) ([]PageSEO, error) {
	owner, ok := m.owners[projectID]
	if !ok || owner != userID {
		return nil, ErrProjectNotFound
	}
	pagesMap, ok := m.pageSEOs[projectID]
	if !ok {
		return []PageSEO{}, nil
	}
	res := make([]PageSEO, 0, len(pagesMap))
	for _, p := range pagesMap {
		res = append(res, *p)
	}
	return res, nil
}

func (m *mockSEOStore) GetProjectPageSEO(ctx context.Context, projectID, userID, route string) (*PageSEO, error) {
	owner, ok := m.owners[projectID]
	if !ok || owner != userID {
		return nil, ErrProjectNotFound
	}
	pagesMap, ok := m.pageSEOs[projectID]
	if !ok {
		return nil, ErrPageNotFound
	}
	p, ok := pagesMap[route]
	if !ok {
		return nil, ErrPageNotFound
	}
	return p, nil
}

func (m *mockSEOStore) SetProjectPageSEO(ctx context.Context, projectID, userID string, page *PageSEO) (*PageSEO, error) {
	owner, ok := m.owners[projectID]
	if !ok || owner != userID {
		return nil, ErrProjectNotFound
	}
	if _, ok := m.pageSEOs[projectID]; !ok {
		m.pageSEOs[projectID] = make(map[string]*PageSEO)
	}
	page.ProjectID = projectID
	page.UpdatedAt = time.Now()
	m.pageSEOs[projectID][page.Route] = page
	return page, nil
}

func (m *mockSEOStore) DeleteProjectPageSEO(ctx context.Context, projectID, userID, route string) error {
	owner, ok := m.owners[projectID]
	if !ok || owner != userID {
		return ErrProjectNotFound
	}
	if pagesMap, ok := m.pageSEOs[projectID]; ok {
		delete(pagesMap, route)
	}
	return nil
}

type mockAuthStore struct {
	user auth.User
}

func (m *mockAuthStore) CreateUser(_ context.Context, _, _, _ string, _ int64) (auth.User, error) {
	return auth.User{}, nil
}

func (m *mockAuthStore) FindUserByEmail(_ context.Context, _ string) (auth.User, string, error) {
	return auth.User{}, "", nil
}

func (m *mockAuthStore) FindUserByID(_ context.Context, _ string) (auth.User, error) {
	return m.user, nil
}

func (m *mockAuthStore) CreateSession(_ context.Context, _, _ string, _ time.Time) error {
	return nil
}

func (m *mockAuthStore) FindUserBySessionToken(_ context.Context, _ string) (auth.User, error) {
	if m.user.ID != "" {
		return m.user, nil
	}
	return auth.User{}, auth.ErrSessionNotFound
}

func (m *mockAuthStore) DeleteSession(_ context.Context, _ string) error {
	return nil
}

func TestSEOHandlers(t *testing.T) {
	store := newMockSEOStore()
	store.owners["proj-1"] = "user-1"
	store.owners["proj-2"] = "user-2"

	authStore := &mockAuthStore{
		user: auth.User{ID: "user-1", Email: "u1@example.com"},
	}

	mux := http.NewServeMux()
	Register(mux, Deps{
		SEOStore:  store,
		AuthStore: authStore,
	})

	// 1. GET /projects/proj-1/seo (Default)
	req := httptest.NewRequest(http.MethodGet, "/projects/proj-1/seo", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", w.Code, w.Body.String())
	}
	var seo ProjectSEO
	if err := json.NewDecoder(w.Body).Decode(&seo); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if seo.SiteName != "Default Site" {
		t.Errorf("expected 'Default Site', got %q", seo.SiteName)
	}

	// 2. Tenant isolation: GET /projects/proj-2/seo as user-1 -> 404
	req = httptest.NewRequest(http.MethodGet, "/projects/proj-2/seo", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404 for foreign project, got %d", w.Code)
	}

	// 3. PUT /projects/proj-1/seo
	updateBody, _ := json.Marshal(ProjectSEO{
		SiteName:      "My Custom App",
		DefaultTitle:  "My Custom App · Home",
		Description:   "An awesome AI-generated application.",
		CanonicalHost: "https://mycustomapp.com",
		Discourage:    false,
	})
	req = httptest.NewRequest(http.MethodPut, "/projects/proj-1/seo", bytes.NewReader(updateBody))
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", w.Code, w.Body.String())
	}
	if err := json.NewDecoder(w.Body).Decode(&seo); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if seo.SiteName != "My Custom App" {
		t.Errorf("expected 'My Custom App', got %q", seo.SiteName)
	}

	// 4. PUT /projects/proj-1/seo/pages/pricing
	pageBody, _ := json.Marshal(map[string]any{
		"title":       "Pricing Plans",
		"description": "Simple transparent pricing for everyone.",
		"noindex":     false,
	})
	req = httptest.NewRequest(http.MethodPut, "/projects/proj-1/seo/pages/pricing", bytes.NewReader(pageBody))
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", w.Code, w.Body.String())
	}
	var page PageSEO
	if err := json.NewDecoder(w.Body).Decode(&page); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if page.Route != "/pricing" || page.Title != "Pricing Plans" {
		t.Errorf("unexpected page seo: %+v", page)
	}

	// 5. GET /projects/proj-1/seo/pages
	req = httptest.NewRequest(http.MethodGet, "/projects/proj-1/seo/pages", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", w.Code, w.Body.String())
	}
	var pages []PageSEO
	if err := json.NewDecoder(w.Body).Decode(&pages); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(pages) != 1 || pages[0].Route != "/pricing" {
		t.Errorf("expected 1 page (/pricing), got %+v", pages)
	}
}

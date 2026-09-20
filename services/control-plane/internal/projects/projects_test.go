package projects

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
)

type fakeAuthStore struct {
	user      auth.User
	returnErr error
}

func (fakeAuthStore) CreateUser(context.Context, string, string, string, int64) (auth.User, error) {
	panic("not used by these tests")
}

func (fakeAuthStore) FindUserByEmail(context.Context, string) (auth.User, string, error) {
	panic("not used by these tests")
}

func (fakeAuthStore) FindUserByID(context.Context, string) (auth.User, error) {
	panic("not used by these tests")
}

func (fakeAuthStore) CreateSession(context.Context, string, string, time.Time) error {
	panic("not used by these tests")
}

func (s fakeAuthStore) FindUserBySessionToken(context.Context, string) (auth.User, error) {
	if s.returnErr != nil {
		return auth.User{}, s.returnErr
	}
	return s.user, nil
}

func (fakeAuthStore) DeleteSession(context.Context, string) error {
	panic("not used by these tests")
}

type fakeProjectStore struct {
	mu           sync.Mutex
	projects     map[string]Project
	nextID       int
	debitCalls   []debitRecord
	charged      int64
	balanceAfter int64
}

type debitRecord struct {
	userID    string
	projectID string
	requested int64
	reason    string
}

func newFakeProjectStore() *fakeProjectStore {
	return &fakeProjectStore{
		projects:     make(map[string]Project),
		balanceAfter: 1000,
	}
}

func (s *fakeProjectStore) CreateProject(_ context.Context, userID, name, description string) (Project, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.nextID++
	id := "proj-" + string(rune('0'+s.nextID))
	if name == "" {
		name = "Untitled project"
	}
	p := Project{
		ID:          id,
		UserID:      userID,
		Name:        name,
		Description: description,
		Status:      "active",
		Entities:    json.RawMessage("[]"),
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}
	s.projects[id] = p
	return p, nil
}

func (s *fakeProjectStore) ListProjects(_ context.Context, userID, status string, _ int) ([]Project, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var list []Project
	for _, p := range s.projects {
		if p.UserID != userID {
			continue
		}
		if status == "archived" && p.Status != "archived" {
			continue
		}
		if status == "active" && p.Status != "active" {
			continue
		}
		list = append(list, p)
	}
	return list, nil
}

func (s *fakeProjectStore) GetProject(_ context.Context, id, userID string) (Project, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.projects[id]
	if !ok || p.UserID != userID {
		return Project{}, ErrProjectNotFound
	}
	return p, nil
}

func (s *fakeProjectStore) UpdateProject(_ context.Context, id, userID string, name, description *string) (Project, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.projects[id]
	if !ok || p.UserID != userID {
		return Project{}, ErrProjectNotFound
	}
	if name != nil {
		p.Name = *name
	}
	if description != nil {
		p.Description = *description
	}
	p.UpdatedAt = time.Now()
	s.projects[id] = p
	return p, nil
}

func (s *fakeProjectStore) TouchProjectOpened(_ context.Context, id, userID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.projects[id]
	if !ok || p.UserID != userID {
		return ErrProjectNotFound
	}
	now := time.Now()
	p.LastOpenedAt = &now
	s.projects[id] = p
	return nil
}

func (s *fakeProjectStore) UpdateProjectBuildResult(
	_ context.Context,
	id, userID string,
	name, prompt, commitSHA string,
	entities json.RawMessage,
	fileCount int,
	messageDelta int,
) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.projects[id]
	if !ok || p.UserID != userID {
		return ErrProjectNotFound
	}
	if name != "" && (p.Name == "Untitled project" || p.Name == "") {
		p.Name = name
	}
	if prompt != "" {
		p.LastPrompt = prompt
	}
	if commitSHA != "" {
		p.CommitSHA = commitSHA
	}
	if len(entities) > 0 {
		p.Entities = entities
	}
	p.FileCount = fileCount
	p.MessageCount += messageDelta
	p.UpdatedAt = time.Now()
	s.projects[id] = p
	return nil
}

func (s *fakeProjectStore) DebitProjectCredits(_ context.Context, userID, projectID string, requested int64, reason string) (int64, int64, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.debitCalls = append(s.debitCalls, debitRecord{userID, projectID, requested, reason})
	charged := requested
	if s.charged > 0 {
		charged = s.charged
	}
	s.balanceAfter -= charged
	p, ok := s.projects[projectID]
	if ok {
		p.CreditsSpent += charged
		s.projects[projectID] = p
	}
	return charged, s.balanceAfter, nil
}

func (s *fakeProjectStore) ArchiveProject(_ context.Context, id, userID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.projects[id]
	if !ok || p.UserID != userID {
		return ErrProjectNotFound
	}
	p.Status = "archived"
	s.projects[id] = p
	return nil
}

func (s *fakeProjectStore) DeleteProject(_ context.Context, id, userID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.projects[id]
	if !ok || p.UserID != userID {
		return ErrProjectNotFound
	}
	delete(s.projects, id)
	return nil
}

const testBearer = "Bearer test-session-token"

func testUser(id string) auth.User {
	return auth.User{ID: id, Email: id + "@example.com", Name: "User " + id, Role: "user", Plan: "free", CreditBalance: 1000}
}

func setupTestServer(t *testing.T, authStore auth.Store, projectStore Store, agentEngineURL string) *httptest.Server {
	t.Helper()
	mux := http.NewServeMux()
	Register(mux, Deps{
		AuthStore:      authStore,
		ProjectStore:   projectStore,
		AgentEngineURL: agentEngineURL,
		CreditsPerUSD:  1000,
	})
	server := httptest.NewServer(mux)
	t.Cleanup(server.Close)
	return server
}

func TestUnauthenticatedReturns401(t *testing.T) {
	authStore := fakeAuthStore{returnErr: auth.ErrSessionNotFound}
	pStore := newFakeProjectStore()
	server := setupTestServer(t, authStore, pStore, "http://127.0.0.1:4173")

	resp, err := http.Get(server.URL + "/projects")
	if err != nil {
		t.Fatalf("GET /projects: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("got status %d, want 401", resp.StatusCode)
	}
}

func TestCreateAndListProjects(t *testing.T) {
	userA := testUser("user-A")
	authStore := fakeAuthStore{user: userA}
	pStore := newFakeProjectStore()
	server := setupTestServer(t, authStore, pStore, "http://127.0.0.1:4173")

	// Create project
	reqBody := `{"name":"My CRM","description":"Customer manager"}`
	req, _ := http.NewRequest(http.MethodPost, server.URL+"/projects", strings.NewReader(reqBody))
	req.Header.Set("Authorization", testBearer)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("POST /projects: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("got status %d, want 201", resp.StatusCode)
	}

	var created Project
	if err := json.NewDecoder(resp.Body).Decode(&created); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if created.Name != "My CRM" || created.UserID != "user-A" {
		t.Fatalf("unexpected project: %+v", created)
	}

	// List projects
	req, _ = http.NewRequest(http.MethodGet, server.URL+"/projects", nil)
	req.Header.Set("Authorization", testBearer)
	resp, err = http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("GET /projects: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("got status %d, want 200", resp.StatusCode)
	}

	var listResult struct {
		Projects []Project `json:"projects"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&listResult); err != nil {
		t.Fatalf("decode list: %v", err)
	}
	if len(listResult.Projects) != 1 || listResult.Projects[0].ID != created.ID {
		t.Fatalf("unexpected list: %+v", listResult)
	}
}

func TestTenantIsolationCrossUser404(t *testing.T) {
	userA := testUser("user-A")
	userB := testUser("user-B")

	pStore := newFakeProjectStore()
	// userA creates project
	projA, _ := pStore.CreateProject(context.Background(), userA.ID, "Project A", "Secret App")

	// Server authenticated as userB
	authStoreB := fakeAuthStore{user: userB}
	server := setupTestServer(t, authStoreB, pStore, "http://127.0.0.1:4173")

	// User B tries to GET User A's project
	req, _ := http.NewRequest(http.MethodGet, server.URL+"/projects/"+projA.ID, nil)
	req.Header.Set("Authorization", testBearer)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("GET /projects/{id}: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("cross-tenant read: got status %d, want 404", resp.StatusCode)
	}

	// User B tries to GET User A's turns
	req, _ = http.NewRequest(http.MethodGet, server.URL+"/projects/"+projA.ID+"/turns", nil)
	req.Header.Set("Authorization", testBearer)
	resp, err = http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("GET /projects/{id}/turns: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("cross-tenant turns read: got status %d, want 404", resp.StatusCode)
	}

	// User B tries to GET User A's files
	req, _ = http.NewRequest(http.MethodGet, server.URL+"/projects/"+projA.ID+"/files", nil)
	req.Header.Set("Authorization", testBearer)
	resp, err = http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("GET /projects/{id}/files: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("cross-tenant files read: got status %d, want 404", resp.StatusCode)
	}

	// User B tries to PATCH User A's project
	req, _ = http.NewRequest(http.MethodPatch, server.URL+"/projects/"+projA.ID, strings.NewReader(`{"name":"Hacked"}`))
	req.Header.Set("Authorization", testBearer)
	resp, err = http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("PATCH /projects/{id}: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("cross-tenant patch: got status %d, want 404", resp.StatusCode)
	}
}

func TestArchiveAndDeleteProject(t *testing.T) {
	userA := testUser("user-A")
	authStore := fakeAuthStore{user: userA}
	pStore := newFakeProjectStore()
	proj, _ := pStore.CreateProject(context.Background(), userA.ID, "To Delete", "")

	deletedWorkspace := ""
	mockAgentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodDelete && strings.HasPrefix(r.URL.Path, "/api/workspaces/") {
			deletedWorkspace = strings.TrimPrefix(r.URL.Path, "/api/workspaces/")
			w.WriteHeader(http.StatusNoContent)
			return
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer mockAgentEngine.Close()

	server := setupTestServer(t, authStore, pStore, mockAgentEngine.URL)

	// Archive
	req, _ := http.NewRequest(http.MethodDelete, server.URL+"/projects/"+proj.ID, nil)
	req.Header.Set("Authorization", testBearer)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("DELETE /projects/{id}: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("archive: got status %d, want 204", resp.StatusCode)
	}

	p, _ := pStore.GetProject(context.Background(), proj.ID, userA.ID)
	if p.Status != "archived" {
		t.Fatalf("status = %q, want 'archived'", p.Status)
	}

	// Purge Delete
	req, _ = http.NewRequest(http.MethodDelete, server.URL+"/projects/"+proj.ID+"?purge=true", nil)
	req.Header.Set("Authorization", testBearer)
	resp, err = http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("DELETE /projects/{id}?purge=true: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("purge: got status %d, want 204", resp.StatusCode)
	}

	_, err = pStore.GetProject(context.Background(), proj.ID, userA.ID)
	if !errors.Is(err, ErrProjectNotFound) {
		t.Fatalf("after purge: expected ErrProjectNotFound, got %v", err)
	}
	// Give background agent-engine delete a moment
	time.Sleep(50 * time.Millisecond)
	if deletedWorkspace != proj.ID {
		t.Fatalf("agent-engine delete: got %q, want %q", deletedWorkspace, proj.ID)
	}
}

func TestProjectBuildStreamRelayAndDebiting(t *testing.T) {
	userA := testUser("user-A")
	authStore := fakeAuthStore{user: userA}
	pStore := newFakeProjectStore()
	proj, _ := pStore.CreateProject(context.Background(), userA.ID, "Untitled project", "")

	mockAgentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/workspaces/"+proj.ID+"/build/stream" {
			w.Header().Set("Content-Type", "text/event-stream")
			flusher := w.(http.Flusher)
			w.Write([]byte("event: delta\ndata: {\"phase\":\"generating_ir\",\"delta\":\"building...\"}\n\n"))
			flusher.Flush()
			w.Write([]byte("event: done\ndata: {\"phase\":\"done\",\"name\":\"Task Tracker\",\"commit_sha\":\"abc1234\",\"file_count\":42,\"entities\":[\"Task\"],\"usage\":{\"cost_micros_usd\":50000}}\n\n"))
			flusher.Flush()
			return
		}
		w.WriteHeader(http.StatusNotFound)
	}))
	defer mockAgentEngine.Close()

	server := setupTestServer(t, authStore, pStore, mockAgentEngine.URL)

	req, _ := http.NewRequest(http.MethodPost, server.URL+"/projects/"+proj.ID+"/build/stream", strings.NewReader(`{"prompt":"build task tracker"}`))
	req.Header.Set("Authorization", testBearer)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("POST build/stream: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("stream: got status %d, want 200", resp.StatusCode)
	}

	body, _ := io.ReadAll(resp.Body)
	bodyStr := string(body)

	if !strings.Contains(bodyStr, "event: delta") {
		t.Errorf("missing delta event in stream: %s", bodyStr)
	}
	if !strings.Contains(bodyStr, "event: done") {
		t.Errorf("missing done event in stream: %s", bodyStr)
	}
	if !strings.Contains(bodyStr, "event: credits") {
		t.Errorf("missing trailing credits event in stream: %s", bodyStr)
	}

	// Verify project metadata was updated
	updatedProj, _ := pStore.GetProject(context.Background(), proj.ID, userA.ID)
	if updatedProj.Name != "Task Tracker" {
		t.Errorf("project name not updated from done event: %s", updatedProj.Name)
	}
	if updatedProj.CommitSHA != "abc1234" {
		t.Errorf("commit sha not updated: %s", updatedProj.CommitSHA)
	}
	if updatedProj.FileCount != 42 {
		t.Errorf("file count not updated: %d", updatedProj.FileCount)
	}
	if len(pStore.debitCalls) != 1 {
		t.Fatalf("expected 1 debit call, got %d", len(pStore.debitCalls))
	}
	if pStore.debitCalls[0].projectID != proj.ID {
		t.Errorf("debit record project id = %s, want %s", pStore.debitCalls[0].projectID, proj.ID)
	}
}

func TestProjectPreview_Endpoints(t *testing.T) {
	pStore := newFakeProjectStore()
	userA := auth.User{ID: "usr-a", Email: "a@example.com"}
	userB := auth.User{ID: "usr-b", Email: "b@example.com"}
	authStore := fakeAuthStore{user: userA}

	projA, _ := pStore.CreateProject(context.Background(), userA.ID, "Alpha App", "")

	mockAgentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		expectedPath := "/api/workspaces/" + projA.ID + "/preview"
		if r.URL.Path == expectedPath && r.Method == http.MethodGet {
			w.Header().Set("Content-Type", "application/json")
			_ = json.NewEncoder(w).Encode(map[string]any{
				"status":     "ready",
				"phase":      "ready",
				"web_url":    "http://127.0.0.1:41001",
				"api_url":    "http://127.0.0.1:41002",
				"web_port":   41001,
				"api_port":   41002,
				"elapsed_ms": 500,
			})
			return
		}
		if r.URL.Path == expectedPath && r.Method == http.MethodPost {
			w.Header().Set("Content-Type", "application/json")
			_ = json.NewEncoder(w).Encode(map[string]any{
				"status":     "ready",
				"phase":      "ready",
				"web_url":    "http://127.0.0.1:41001",
				"api_url":    "http://127.0.0.1:41002",
				"web_port":   41001,
				"api_port":   41002,
				"elapsed_ms": 1200,
			})
			return
		}
		if r.URL.Path == expectedPath+"/stop" && r.Method == http.MethodPost {
			w.Header().Set("Content-Type", "application/json")
			_ = json.NewEncoder(w).Encode(map[string]any{
				"status": "stopped",
				"phase":  "stopped",
			})
			return
		}
		w.WriteHeader(http.StatusNotFound)
	}))
	defer mockAgentEngine.Close()

	server := setupTestServer(t, authStore, pStore, mockAgentEngine.URL)

	// 1. GET /projects/{id}/preview for owner returns 200 with preview info
	req, _ := http.NewRequest(http.MethodGet, server.URL+"/projects/"+projA.ID+"/preview", nil)
	req.Header.Set("Authorization", testBearer)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("GET preview: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("GET preview: got %d, want 200", resp.StatusCode)
	}
	var getBody map[string]any
	_ = json.NewDecoder(resp.Body).Decode(&getBody)
	if getBody["web_port"] != float64(41001) {
		t.Errorf("web_port = %v, want 41001", getBody["web_port"])
	}

	// 2. POST /projects/{id}/preview returns 200 with started preview info
	postReq, _ := http.NewRequest(http.MethodPost, server.URL+"/projects/"+projA.ID+"/preview", nil)
	postReq.Header.Set("Authorization", testBearer)
	postResp, err := http.DefaultClient.Do(postReq)
	if err != nil {
		t.Fatalf("POST preview: %v", err)
	}
	defer postResp.Body.Close()
	if postResp.StatusCode != http.StatusOK {
		t.Errorf("POST preview: got %d, want 200", postResp.StatusCode)
	}

	// 3. POST /projects/{id}/preview/stop returns 200 stopped status
	stopReq, _ := http.NewRequest(http.MethodPost, server.URL+"/projects/"+projA.ID+"/preview/stop", nil)
	stopReq.Header.Set("Authorization", testBearer)
	stopResp, err := http.DefaultClient.Do(stopReq)
	if err != nil {
		t.Fatalf("POST preview/stop: %v", err)
	}
	defer stopResp.Body.Close()
	if stopResp.StatusCode != http.StatusOK {
		t.Errorf("POST preview/stop: got %d, want 200", stopResp.StatusCode)
	}

	// 4. Foreign user (userB) requesting projA gets 404
	bServer := setupTestServer(t, fakeAuthStore{user: userB}, pStore, mockAgentEngine.URL)
	bReq, _ := http.NewRequest(http.MethodGet, bServer.URL+"/projects/"+projA.ID+"/preview", nil)
	bReq.Header.Set("Authorization", testBearer)
	bResp, err := http.DefaultClient.Do(bReq)
	if err != nil {
		t.Fatalf("foreign user GET preview: %v", err)
	}
	defer bResp.Body.Close()
	if bResp.StatusCode != http.StatusNotFound {
		t.Errorf("foreign user got %d, want 404", bResp.StatusCode)
	}
}

package git

import (
	"archive/zip"
	"bytes"
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
)

type mockAuthStore struct {
	user auth.User
	err  error
}

func (mockAuthStore) CreateUser(context.Context, string, string, string, int64) (auth.User, error) {
	panic("unused")
}
func (mockAuthStore) FindUserByEmail(context.Context, string) (auth.User, string, error) {
	panic("unused")
}
func (mockAuthStore) FindUserByID(context.Context, string) (auth.User, error) {
	panic("unused")
}
func (mockAuthStore) CreateSession(context.Context, string, string, time.Time) error {
	panic("unused")
}
func (m mockAuthStore) FindUserBySessionToken(context.Context, string) (auth.User, error) {
	if m.err != nil {
		return auth.User{}, m.err
	}
	return m.user, nil
}
func (mockAuthStore) DeleteSession(context.Context, string) error {
	panic("unused")
}

type mockGitStore struct {
	conn       *Connection
	projectGit *ProjectGitInfo
}

func (m *mockGitStore) GetConnection(ctx context.Context, userID string) (*Connection, error) {
	if m.conn == nil || m.conn.UserID != userID {
		return nil, ErrConnectionNotFound
	}
	return m.conn, nil
}

func (m *mockGitStore) SaveConnection(ctx context.Context, conn *Connection) error {
	m.conn = conn
	return nil
}

func (m *mockGitStore) DeleteConnection(ctx context.Context, userID string) error {
	if m.conn != nil && m.conn.UserID == userID {
		m.conn = nil
	}
	return nil
}

func (m *mockGitStore) GetProjectGit(ctx context.Context, userID, projectID string) (*ProjectGitInfo, error) {
	if m.projectGit == nil || m.projectGit.UserID != userID || m.projectGit.ProjectID != projectID {
		return nil, ErrProjectNotFound
	}
	return m.projectGit, nil
}

func (m *mockGitStore) UpdateProjectRepo(ctx context.Context, userID, projectID, repoFullName, repoURL string, repoPrivate bool) error {
	if m.projectGit == nil || m.projectGit.UserID != userID || m.projectGit.ProjectID != projectID {
		return ErrProjectNotFound
	}
	m.projectGit.RepoFullName = repoFullName
	m.projectGit.RepoURL = repoURL
	m.projectGit.RepoPrivate = repoPrivate
	return nil
}

func (m *mockGitStore) UpdateProjectPushed(ctx context.Context, userID, projectID, pushedSHA string, pushedAt time.Time) error {
	if m.projectGit == nil || m.projectGit.UserID != userID || m.projectGit.ProjectID != projectID {
		return ErrProjectNotFound
	}
	m.projectGit.LastPushedSHA = pushedSHA
	m.projectGit.LastPushedAt = &pushedAt
	return nil
}

type mockProjectStore struct {
	proj *projects.Project
}

func (m *mockProjectStore) CreateProject(ctx context.Context, userID, name, description string) (projects.Project, error) {
	return projects.Project{}, nil
}
func (m *mockProjectStore) ListProjects(ctx context.Context, userID, status string, limit int) ([]projects.Project, error) {
	return nil, nil
}
func (m *mockProjectStore) GetProject(ctx context.Context, id, userID string) (projects.Project, error) {
	if m.proj == nil || m.proj.UserID != userID || m.proj.ID != id {
		return projects.Project{}, projects.ErrProjectNotFound
	}
	return *m.proj, nil
}
func (m *mockProjectStore) UpdateProject(ctx context.Context, id, userID string, name, description *string) (projects.Project, error) {
	return projects.Project{}, nil
}
func (m *mockProjectStore) UpdateProjectBuildResult(ctx context.Context, id, userID string, name, prompt, commitSHA string, entities json.RawMessage, fileCount int, messageDelta int) error {
	return nil
}
func (m *mockProjectStore) DebitProjectCredits(ctx context.Context, userID, projectID string, requested int64, reason string) (int64, int64, error) {
	return 0, 0, nil
}
func (m *mockProjectStore) ArchiveProject(ctx context.Context, id, userID string) error {
	return nil
}
func (m *mockProjectStore) DeleteProject(ctx context.Context, id, userID string) error {
	return nil
}
func (m *mockProjectStore) TouchProjectOpened(ctx context.Context, id, userID string) error {
	return nil
}

func generateTestRSAPEM(t *testing.T) []byte {
	privKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatalf("rsa.GenerateKey failed: %v", err)
	}
	pkcs1Bytes := x509.MarshalPKCS1PrivateKey(privKey)
	return pem.EncodeToMemory(&pem.Block{
		Type:  "RSA PRIVATE KEY",
		Bytes: pkcs1Bytes,
	})
}

func TestMintAppJWT(t *testing.T) {
	pemBytes := generateTestRSAPEM(t)
	jwtStr, err := MintAppJWT("12345", pemBytes, time.Now())
	if err != nil {
		t.Fatalf("MintAppJWT failed: %v", err)
	}
	if len(jwtStr) < 50 {
		t.Fatalf("JWT length %d too short", len(jwtStr))
	}

	// Missing appID or key should error
	_, err = MintAppJWT("", pemBytes, time.Now())
	if err != ErrGitHubNotConfigured {
		t.Fatalf("expected ErrGitHubNotConfigured, got %v", err)
	}

	_, err = MintAppJWT("12345", nil, time.Now())
	if err != ErrGitHubNotConfigured {
		t.Fatalf("expected ErrGitHubNotConfigured, got %v", err)
	}
}

func TestExportProjectZip_StreamsZipWithCorrectHeaders(t *testing.T) {
	// Setup mock agent engine serving a zip
	agentMux := http.NewServeMux()
	agentMux.HandleFunc("GET /api/workspaces/proj-1/export", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/zip")
		buf := new(bytes.Buffer)
		zw := zip.NewWriter(buf)
		f, _ := zw.Create("hello.txt")
		_, _ = f.Write([]byte("hello from project"))
		_ = zw.Close()
		_, _ = w.Write(buf.Bytes())
	})
	agentServer := httptest.NewServer(agentMux)
	defer agentServer.Close()

	user := auth.User{ID: "user-1", Email: "dev@example.com"}
	authStore := &mockAuthStore{user: user}
	projStore := &mockProjectStore{
		proj: &projects.Project{
			ID:     "proj-1",
			UserID: "user-1",
			Name:   "My Awesome App",
		},
	}
	gitStore := &mockGitStore{}

	mux := http.NewServeMux()
	Register(mux, Deps{
		AuthStore:      authStore,
		GitStore:       gitStore,
		ProjectStore:   projStore,
		AgentEngineURL: agentServer.URL,
	})

	req := httptest.NewRequest(http.MethodGet, "/projects/proj-1/export", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	rec := httptest.NewRecorder()

	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/zip" {
		t.Fatalf("Content-Type = %q, want application/zip", ct)
	}
	if cd := rec.Header().Get("Content-Disposition"); cd != `attachment; filename="my-awesome-app.zip"` {
		t.Fatalf("Content-Disposition = %q, want attachment; filename=\"my-awesome-app.zip\"", cd)
	}

	// Verify unzippable
	zr, err := zip.NewReader(bytes.NewReader(rec.Body.Bytes()), int64(rec.Body.Len()))
	if err != nil {
		t.Fatalf("failed to parse zip: %v", err)
	}
	if len(zr.File) != 1 || zr.File[0].Name != "hello.txt" {
		t.Fatalf("unexpected files in zip: %#v", zr.File)
	}
}

func TestExportProjectZip_ForeignUserGets404(t *testing.T) {
	user := auth.User{ID: "user-attacker", Email: "attacker@example.com"}
	authStore := &mockAuthStore{user: user}
	projStore := &mockProjectStore{
		proj: &projects.Project{
			ID:     "proj-1",
			UserID: "user-victim",
			Name:   "Victim App",
		},
	}
	gitStore := &mockGitStore{}

	mux := http.NewServeMux()
	Register(mux, Deps{
		AuthStore:      authStore,
		GitStore:       gitStore,
		ProjectStore:   projStore,
		AgentEngineURL: "http://127.0.0.1:4173",
	})

	req := httptest.NewRequest(http.MethodGet, "/projects/proj-1/export", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	rec := httptest.NewRecorder()

	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404 for foreign user, got %d", rec.Code)
	}
}

func TestGitPush_SanitizesTokenOnError(t *testing.T) {
	pemBytes := generateTestRSAPEM(t)
	fakeToken := "ghs_SUPER_SECRET_TOKEN_99999"

	// Mock GitHub API server
	ghMux := http.NewServeMux()
	ghMux.HandleFunc("POST /app/installations/123/access_tokens", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(InstallationTokenResponse{
			Token:     fakeToken,
			ExpiresAt: time.Now().Add(1 * time.Hour),
		})
	})
	ghServer := httptest.NewServer(ghMux)
	defer ghServer.Close()

	// Mock Agent Engine server returning an error that echoes the token
	agentMux := http.NewServeMux()
	agentMux.HandleFunc("POST /api/workspaces/proj-1/git/push", func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		w.WriteHeader(http.StatusBadRequest)
		_, _ = w.Write([]byte(fmt.Sprintf("push error with payload: %s", string(body))))
	})
	agentServer := httptest.NewServer(agentMux)
	defer agentServer.Close()

	user := auth.User{ID: "user-1", Email: "dev@example.com"}
	authStore := &mockAuthStore{user: user}
	gitStore := &mockGitStore{
		conn: &Connection{
			UserID:         "user-1",
			Provider:       "github",
			ExternalLogin:  "dev",
			InstallationID: 123,
		},
		projectGit: &ProjectGitInfo{
			ProjectID:    "proj-1",
			UserID:       "user-1",
			RepoFullName: "dev/my-app",
			RepoURL:      "https://github.com/dev/my-app",
		},
	}
	projStore := &mockProjectStore{
		proj: &projects.Project{
			ID:     "proj-1",
			UserID: "user-1",
		},
	}

	mux := http.NewServeMux()
	Register(mux, Deps{
		AuthStore:           authStore,
		GitStore:            gitStore,
		ProjectStore:        projStore,
		AgentEngineURL:      agentServer.URL,
		GitHubAPIBaseURL:    ghServer.URL,
		GitHubAppID:         "12345",
		GitHubAppPrivateKey: string(pemBytes),
	})

	req := httptest.NewRequest(http.MethodPost, "/projects/proj-1/git/push", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	rec := httptest.NewRecorder()

	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadGateway {
		t.Fatalf("expected 502, got %d: %s", rec.Code, rec.Body.String())
	}

	// CRITICAL ASSERTION: The token must NEVER appear in the response body!
	if bytes.Contains(rec.Body.Bytes(), []byte(fakeToken)) {
		t.Fatalf("SECURITY VULNERABILITY: response body leaked GitHub access token: %s", rec.Body.String())
	}
	if !bytes.Contains(rec.Body.Bytes(), []byte("[REDACTED]")) {
		t.Fatalf("expected sanitized [REDACTED] in error response, got: %s", rec.Body.String())
	}
}

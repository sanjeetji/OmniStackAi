package jobs

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

func decodeJSON(t *testing.T, resp *http.Response, dst any) {
	t.Helper()
	if err := json.NewDecoder(resp.Body).Decode(dst); err != nil {
		t.Fatalf("decode response body: %v", err)
	}
}

// fakeAuthStore is a minimal auth.Store double: only FindUserBySessionToken is ever exercised by
// auth.RequireUser (this package's own dependency), so every other method panics if reached -
// hermetic and fast, the same "fake the narrow interface" idiom internal/auth's own tests use.
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

type debitCall struct {
	userID    string
	requested int64
	reason    string
}

type fakeCreditStore struct {
	mu        sync.Mutex
	calls     []debitCall
	charged   int64
	balance   int64
	returnErr error
}

func (s *fakeCreditStore) DebitCredits(_ context.Context, userID string, requested int64, reason string) (int64, int64, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.calls = append(s.calls, debitCall{userID, requested, reason})
	if s.returnErr != nil {
		return 0, 0, s.returnErr
	}
	return s.charged, s.balance, nil
}

func (s *fakeCreditStore) callCount() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.calls)
}

const validToken = "Bearer session-token-for-tests"

func newTestUser() auth.User {
	return auth.User{ID: "user-1", Email: "person@example.com", Name: "Person", Role: "user", Plan: "free", CreditBalance: 1000}
}

func newTestServer(t *testing.T, agentEngineURL string, authStore fakeAuthStore, creditStore CreditStore, creditsPerUSD float64) *httptest.Server {
	t.Helper()
	mux := http.NewServeMux()
	Register(mux, Deps{
		AuthStore:      authStore,
		CreditStore:    creditStore,
		AgentEngineURL: agentEngineURL,
		CreditsPerUSD:  creditsPerUSD,
	})
	server := httptest.NewServer(mux)
	t.Cleanup(server.Close)
	return server
}

func postBuild(t *testing.T, server *httptest.Server, authHeader, body string) *http.Response {
	t.Helper()
	request, err := http.NewRequest(http.MethodPost, server.URL+"/jobs/build", strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	if authHeader != "" {
		request.Header.Set("Authorization", authHeader)
	}
	request.Header.Set("Content-Type", "application/json")
	resp, err := server.Client().Do(request)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = resp.Body.Close() })
	return resp
}

func TestHandleBuildRejectsMissingOrUnknownToken(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("agent-engine must not be called for an unauthenticated request")
	}))
	defer agentEngine.Close()

	creditStore := &fakeCreditStore{}
	server := newTestServer(t, agentEngine.URL, fakeAuthStore{returnErr: auth.ErrSessionNotFound}, creditStore, 1000)

	noHeaderResp := postBuild(t, server, "", `{"prompt":"a blog"}`)
	if noHeaderResp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("no-header status = %d, want %d", noHeaderResp.StatusCode, http.StatusUnauthorized)
	}

	unknownTokenResp := postBuild(t, server, validToken, `{"prompt":"a blog"}`)
	if unknownTokenResp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("unknown-token status = %d, want %d", unknownTokenResp.StatusCode, http.StatusUnauthorized)
	}
	if creditStore.callCount() != 0 {
		t.Fatalf("DebitCredits called %d times, want 0", creditStore.callCount())
	}
}

func TestHandleBuildReturns500WhenAuthStoreFailsInternally(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("agent-engine must not be called when authentication itself fails")
	}))
	defer agentEngine.Close()

	server := newTestServer(t, agentEngine.URL, fakeAuthStore{returnErr: errors.New("database is on fire")}, &fakeCreditStore{}, 1000)

	resp := postBuild(t, server, validToken, `{"prompt":"a blog"}`)
	if resp.StatusCode != http.StatusInternalServerError {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusInternalServerError)
	}
}

func TestHandleBuildForwardsBodyVerbatimAndDebitsRealUsage(t *testing.T) {
	const requestBody = `{"prompt":"A tech blog","hybrid_ui":true}`
	var receivedBody string
	var receivedContentType string

	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		raw, err := io.ReadAll(r.Body)
		if err != nil {
			t.Fatal(err)
		}
		receivedBody = string(raw)
		receivedContentType = r.Header.Get("Content-Type")
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"name":"Tech Blog","file_count":42,"usage":{"cost_micros_usd":250000,"total_calls":2}}`))
	}))
	defer agentEngine.Close()

	creditStore := &fakeCreditStore{charged: 250, balance: 750}
	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, creditStore, 1000)

	resp := postBuild(t, server, validToken, requestBody)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusOK)
	}
	if receivedBody != requestBody {
		t.Fatalf("agent-engine received body = %q, want %q (must forward verbatim)", receivedBody, requestBody)
	}
	if receivedContentType != "application/json" {
		t.Fatalf("agent-engine received Content-Type = %q", receivedContentType)
	}

	var payload map[string]any
	decodeJSON(t, resp, &payload)
	if payload["name"] != "Tech Blog" {
		t.Fatalf("payload[name] = %v, want the agent-engine's own field to pass through", payload["name"])
	}
	if payload["credits_spent"].(float64) != 250 {
		t.Fatalf("payload[credits_spent] = %v, want 250", payload["credits_spent"])
	}
	if payload["credit_balance"].(float64) != 750 {
		t.Fatalf("payload[credit_balance] = %v, want 750", payload["credit_balance"])
	}

	if creditStore.callCount() != 1 {
		t.Fatalf("DebitCredits called %d times, want 1", creditStore.callCount())
	}
	call := creditStore.calls[0]
	if call.userID != "user-1" || call.requested != 250 || call.reason != "job:build" {
		t.Fatalf("DebitCredits call = %+v, want {user-1 250 job:build}", call)
	}
}

func TestHandleBuildDoesNotChargeWhenNoUsageIsReported(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"pack_id":"minimal-blog","file_count":150}`))
	}))
	defer agentEngine.Close()

	creditStore := &fakeCreditStore{}
	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, creditStore, 1000)

	resp := postBuild(t, server, validToken, `{"prompt":"a blog","pack_id":"minimal-blog"}`)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusOK)
	}

	var payload map[string]any
	decodeJSON(t, resp, &payload)
	if payload["credits_spent"].(float64) != 0 {
		t.Fatalf("payload[credits_spent] = %v, want 0", payload["credits_spent"])
	}
	if payload["credit_balance"].(float64) != float64(newTestUser().CreditBalance) {
		t.Fatalf("payload[credit_balance] = %v, want the user's unchanged balance %d", payload["credit_balance"], newTestUser().CreditBalance)
	}
	if creditStore.callCount() != 0 {
		t.Fatalf("DebitCredits called %d times, want 0 (no usage reported)", creditStore.callCount())
	}
}

func TestHandleBuildProxiesUpstreamErrorStatusAndBodyUnchanged(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		_, _ = w.Write([]byte(`{"error":"Unknown Solution Pack 'nope'"}`))
	}))
	defer agentEngine.Close()

	creditStore := &fakeCreditStore{}
	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, creditStore, 1000)

	resp := postBuild(t, server, validToken, `{"prompt":"a blog","pack_id":"nope"}`)
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d (proxied unchanged)", resp.StatusCode, http.StatusBadRequest)
	}
	var payload map[string]any
	decodeJSON(t, resp, &payload)
	if payload["error"] != "Unknown Solution Pack 'nope'" {
		t.Fatalf("payload[error] = %v, want the agent-engine's own error message", payload["error"])
	}
	if creditStore.callCount() != 0 {
		t.Fatalf("DebitCredits called %d times, want 0 for a failed build", creditStore.callCount())
	}
}

func TestHandleBuildReturnsBadGatewayWhenAgentEngineIsUnreachable(t *testing.T) {
	creditStore := &fakeCreditStore{}
	// A closed server's URL reliably refuses the connection.
	closedServer := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}))
	unreachableURL := closedServer.URL
	closedServer.Close()

	server := newTestServer(t, unreachableURL, fakeAuthStore{user: newTestUser()}, creditStore, 1000)

	resp := postBuild(t, server, validToken, `{"prompt":"a blog"}`)
	if resp.StatusCode != http.StatusBadGateway {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusBadGateway)
	}
	if creditStore.callCount() != 0 {
		t.Fatalf("DebitCredits called %d times, want 0", creditStore.callCount())
	}
}

func getBuildPath(t *testing.T, server *httptest.Server, authHeader, path string) *http.Response {
	t.Helper()
	request, err := http.NewRequest(http.MethodGet, server.URL+path, nil)
	if err != nil {
		t.Fatal(err)
	}
	if authHeader != "" {
		request.Header.Set("Authorization", authHeader)
	}
	resp, err := server.Client().Do(request)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = resp.Body.Close() })
	return resp
}

func TestHandleBuildFilesRejectsMissingToken(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("agent-engine must not be called for an unauthenticated request")
	}))
	defer agentEngine.Close()

	server := newTestServer(t, agentEngine.URL, fakeAuthStore{returnErr: auth.ErrSessionNotFound}, &fakeCreditStore{}, 1000)

	resp := getBuildPath(t, server, "", "/jobs/build/abc123/files")
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusUnauthorized)
	}
}

func TestHandleBuildFilesProxiesTheFileListVerbatim(t *testing.T) {
	var requestedPath string
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestedPath = r.URL.Path
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"files":["README.md","apps/web/app/page.tsx"],"truncated":false}`))
	}))
	defer agentEngine.Close()

	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, &fakeCreditStore{}, 1000)

	resp := getBuildPath(t, server, validToken, "/jobs/build/abc123/files")
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusOK)
	}
	if requestedPath != "/api/build/abc123/files" {
		t.Fatalf("agent-engine received path = %q, want %q", requestedPath, "/api/build/abc123/files")
	}
	var payload map[string]any
	decodeJSON(t, resp, &payload)
	if files, ok := payload["files"].([]any); !ok || len(files) != 2 {
		t.Fatalf("payload[files] = %v, want a 2-element list", payload["files"])
	}
}

func TestHandleBuildFilesProxiesUnknownBuildAs404(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"error":"build 'abc123' is not available in this session"}`))
	}))
	defer agentEngine.Close()

	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, &fakeCreditStore{}, 1000)

	resp := getBuildPath(t, server, validToken, "/jobs/build/abc123/files")
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("status = %d, want %d (proxied unchanged)", resp.StatusCode, http.StatusNotFound)
	}
}

func TestHandleBuildFileRejectsMissingToken(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("agent-engine must not be called for an unauthenticated request")
	}))
	defer agentEngine.Close()

	server := newTestServer(t, agentEngine.URL, fakeAuthStore{returnErr: auth.ErrSessionNotFound}, &fakeCreditStore{}, 1000)

	resp := getBuildPath(t, server, "", "/jobs/build/abc123/file?path=README.md")
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusUnauthorized)
	}
}

func TestHandleBuildFileForwardsThePathQueryParamAndProxiesContentVerbatim(t *testing.T) {
	var requestedPath, requestedQuery string
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestedPath = r.URL.Path
		requestedQuery = r.URL.Query().Get("path")
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"path":"apps/web/app/page.tsx","content":"export default function Page() {}","truncated":false,"binary":false,"size":34}`))
	}))
	defer agentEngine.Close()

	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, &fakeCreditStore{}, 1000)

	resp := getBuildPath(t, server, validToken, "/jobs/build/abc123/file?path=apps%2Fweb%2Fapp%2Fpage.tsx")
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusOK)
	}
	if requestedPath != "/api/build/abc123/file" {
		t.Fatalf("agent-engine received path = %q, want %q", requestedPath, "/api/build/abc123/file")
	}
	if requestedQuery != "apps/web/app/page.tsx" {
		t.Fatalf("agent-engine received path query = %q, want %q", requestedQuery, "apps/web/app/page.tsx")
	}
	var payload map[string]any
	decodeJSON(t, resp, &payload)
	if payload["content"] != "export default function Page() {}" {
		t.Fatalf("payload[content] = %v", payload["content"])
	}
}

func TestHandleBuildFileProxiesPathTraversalRejectionAs400(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		_, _ = w.Write([]byte(`{"error":"path escapes the build directory: ../../etc/passwd"}`))
	}))
	defer agentEngine.Close()

	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, &fakeCreditStore{}, 1000)

	resp := getBuildPath(t, server, validToken, "/jobs/build/abc123/file?path=..%2F..%2Fetc%2Fpasswd")
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d (proxied unchanged, no new traversal logic here)", resp.StatusCode, http.StatusBadRequest)
	}
}

func postPath(t *testing.T, server *httptest.Server, authHeader, path, body string) *http.Response {
	t.Helper()
	request, err := http.NewRequest(http.MethodPost, server.URL+path, strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	if authHeader != "" {
		request.Header.Set("Authorization", authHeader)
	}
	request.Header.Set("Content-Type", "application/json")
	resp, err := server.Client().Do(request)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = resp.Body.Close() })
	return resp
}

func TestHandleBuildEditRejectsMissingOrUnknownToken(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("agent-engine must not be called for an unauthenticated request")
	}))
	defer agentEngine.Close()

	creditStore := &fakeCreditStore{}
	server := newTestServer(t, agentEngine.URL, fakeAuthStore{returnErr: auth.ErrSessionNotFound}, creditStore, 1000)

	resp := postPath(t, server, "", "/jobs/build/abc123/edit", `{"prompt":"add favorites"}`)
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusUnauthorized)
	}
	if creditStore.callCount() != 0 {
		t.Fatalf("DebitCredits called %d times, want 0", creditStore.callCount())
	}
}

func TestHandleBuildEditForwardsBodyVerbatimAndDebitsRealUsage(t *testing.T) {
	const requestBody = `{"prompt":"add a favorites feature"}`
	var receivedPath, receivedBody string
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedPath = r.URL.Path
		raw, err := io.ReadAll(r.Body)
		if err != nil {
			t.Fatal(err)
		}
		receivedBody = string(raw)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"id":"abc123","entities":["Favorite"],"file_count":161,"commit_sha":"deadbeef","rationale":"Added Favorite entity.","turns":[],"usage":{"cost_micros_usd":18000,"total_calls":1}}`))
	}))
	defer agentEngine.Close()

	creditStore := &fakeCreditStore{charged: 18, balance: 82}
	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, creditStore, 1000)

	resp := postPath(t, server, validToken, "/jobs/build/abc123/edit", requestBody)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusOK)
	}
	if receivedPath != "/api/build/abc123/edit" {
		t.Fatalf("agent-engine received path = %q, want %q", receivedPath, "/api/build/abc123/edit")
	}
	if receivedBody != requestBody {
		t.Fatalf("agent-engine received body = %q, want %q (must forward verbatim)", receivedBody, requestBody)
	}

	var payload map[string]any
	decodeJSON(t, resp, &payload)
	if payload["credits_spent"].(float64) != 18 {
		t.Fatalf("payload[credits_spent] = %v, want 18", payload["credits_spent"])
	}
	if payload["credit_balance"].(float64) != 82 {
		t.Fatalf("payload[credit_balance] = %v, want 82", payload["credit_balance"])
	}
	if creditStore.callCount() != 1 {
		t.Fatalf("DebitCredits called %d times, want 1", creditStore.callCount())
	}
	call := creditStore.calls[0]
	if call.userID != "user-1" || call.requested != 18 || call.reason != "job:edit" {
		t.Fatalf("DebitCredits call = %+v, want {user-1 18 job:edit}", call)
	}
}

func TestHandleBuildEditChargesForANoOpEdit(t *testing.T) {
	// A no-op edit (the delta call still happened, it just produced no file changes) still costs
	// a real model call - creditsForUsage only ever looks at the reported cost, not the diff.
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"id":"abc123","diff":{"added":[],"modified":[],"deleted":[],"summary":"No file changes were needed."},"usage":{"cost_micros_usd":9000}}`))
	}))
	defer agentEngine.Close()

	creditStore := &fakeCreditStore{charged: 9, balance: 91}
	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, creditStore, 1000)

	resp := postPath(t, server, validToken, "/jobs/build/abc123/edit", `{"prompt":"add favorites"}`)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusOK)
	}
	var payload map[string]any
	decodeJSON(t, resp, &payload)
	if payload["credits_spent"].(float64) != 9 {
		t.Fatalf("payload[credits_spent] = %v, want 9 (a no-op edit still costs a real model call)", payload["credits_spent"])
	}
}

func TestHandleBuildEditDoesNotChargeWhenNoUsageIsReported(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"id":"abc123","entities":[]}`))
	}))
	defer agentEngine.Close()

	creditStore := &fakeCreditStore{}
	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, creditStore, 1000)

	resp := postPath(t, server, validToken, "/jobs/build/abc123/edit", `{"prompt":"add favorites"}`)
	var payload map[string]any
	decodeJSON(t, resp, &payload)
	if payload["credits_spent"].(float64) != 0 {
		t.Fatalf("payload[credits_spent] = %v, want 0", payload["credits_spent"])
	}
	if creditStore.callCount() != 0 {
		t.Fatalf("DebitCredits called %d times, want 0", creditStore.callCount())
	}
}

func TestHandleBuildEditProxiesUpstreamErrorsUnchanged(t *testing.T) {
	cases := []struct {
		name   string
		status int
		body   string
	}{
		{"unknown build (BuildNotFoundError)", http.StatusNotFound, `{"error":"build 'abc123' is not available in this session"}`},
		{"unsupported build kind (EditNotSupportedError)", http.StatusBadRequest, `{"error":"editing is not yet supported for Solution Pack builds or multi-surface Ecosystem builds"}`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(tc.status)
				_, _ = w.Write([]byte(tc.body))
			}))
			defer agentEngine.Close()

			creditStore := &fakeCreditStore{}
			server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, creditStore, 1000)

			resp := postPath(t, server, validToken, "/jobs/build/abc123/edit", `{"prompt":"add favorites"}`)
			if resp.StatusCode != tc.status {
				t.Fatalf("status = %d, want %d (proxied unchanged)", resp.StatusCode, tc.status)
			}
			if creditStore.callCount() != 0 {
				t.Fatalf("DebitCredits called %d times, want 0", creditStore.callCount())
			}
		})
	}
}

func TestHandleBuildEditReturnsBadGatewayWhenAgentEngineIsUnreachable(t *testing.T) {
	creditStore := &fakeCreditStore{}
	closedServer := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}))
	unreachableURL := closedServer.URL
	closedServer.Close()

	server := newTestServer(t, unreachableURL, fakeAuthStore{user: newTestUser()}, creditStore, 1000)

	resp := postPath(t, server, validToken, "/jobs/build/abc123/edit", `{"prompt":"add favorites"}`)
	if resp.StatusCode != http.StatusBadGateway {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusBadGateway)
	}
}

func TestHandleBuildEditReturns500WhenDebitCreditsFails(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"id":"abc123","usage":{"cost_micros_usd":9000}}`))
	}))
	defer agentEngine.Close()

	creditStore := &fakeCreditStore{returnErr: errors.New("database is on fire")}
	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, creditStore, 1000)

	resp := postPath(t, server, validToken, "/jobs/build/abc123/edit", `{"prompt":"add favorites"}`)
	if resp.StatusCode != http.StatusInternalServerError {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusInternalServerError)
	}
}

func TestHandleBuildTurnsRejectsMissingToken(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("agent-engine must not be called for an unauthenticated request")
	}))
	defer agentEngine.Close()

	server := newTestServer(t, agentEngine.URL, fakeAuthStore{returnErr: auth.ErrSessionNotFound}, &fakeCreditStore{}, 1000)

	resp := getBuildPath(t, server, "", "/jobs/build/abc123/turns")
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusUnauthorized)
	}
}

func TestHandleBuildTurnsProxiesVerbatim(t *testing.T) {
	cases := []struct {
		name string
		body string
	}{
		{"a build with real turns", `{"turns":[{"role":"user","text":"add favorites","created_at":1234.5},{"role":"assistant","text":"Added Favorite entity and API endpoint.","created_at":1235.0}]}`},
		{"an unknown build (empty turns, not an error)", `{"turns":[]}`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var requestedPath string
			agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				requestedPath = r.URL.Path
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusOK)
				_, _ = w.Write([]byte(tc.body))
			}))
			defer agentEngine.Close()

			server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, &fakeCreditStore{}, 1000)

			resp := getBuildPath(t, server, validToken, "/jobs/build/abc123/turns")
			if resp.StatusCode != http.StatusOK {
				t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusOK)
			}
			if requestedPath != "/api/build/abc123/turns" {
				t.Fatalf("agent-engine received path = %q, want %q", requestedPath, "/api/build/abc123/turns")
			}
		})
	}
}

func TestCreditsForUsage(t *testing.T) {
	cases := []struct {
		name          string
		usage         any
		creditsPerUSD float64
		want          int64
	}{
		{"typical cost rounds to nearest credit", map[string]any{"cost_micros_usd": float64(250000)}, 1000, 250},
		{"fractional result rounds half up", map[string]any{"cost_micros_usd": float64(1500)}, 1000, 2},
		{"zero cost charges nothing", map[string]any{"cost_micros_usd": float64(0)}, 1000, 0},
		{"negative cost (should not happen) charges nothing", map[string]any{"cost_micros_usd": float64(-5)}, 1000, 0},
		{"missing usage object charges nothing", nil, 1000, 0},
		{"usage object without cost_micros_usd charges nothing", map[string]any{"total_calls": float64(2)}, 1000, 0},
		{"non-numeric cost_micros_usd charges nothing", map[string]any{"cost_micros_usd": "not a number"}, 1000, 0},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := creditsForUsage(tc.usage, tc.creditsPerUSD)
			if got != tc.want {
				t.Fatalf("creditsForUsage(%v, %v) = %d, want %d", tc.usage, tc.creditsPerUSD, got, tc.want)
			}
		})
	}
}

func TestHandlePreviewStatusRejectsMissingToken(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("agent-engine must not be called for an unauthenticated request")
	}))
	defer agentEngine.Close()

	server := newTestServer(t, agentEngine.URL, fakeAuthStore{returnErr: auth.ErrSessionNotFound}, &fakeCreditStore{}, 1000)

	resp := getBuildPath(t, server, "", "/jobs/preview")
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusUnauthorized)
	}
}

func TestHandlePreviewStatusProxiesVerbatim(t *testing.T) {
	cases := []struct {
		name   string
		status int
		body   string
	}{
		{"a running preview", http.StatusOK, `{"status":"ready","url":"http://127.0.0.1:53211","web_port":53211}`},
		{"preview controls not enabled (build-only mode)", http.StatusNotFound, `{"error":"preview controls are not enabled"}`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var requestedPath string
			agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				requestedPath = r.URL.Path
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(tc.status)
				_, _ = w.Write([]byte(tc.body))
			}))
			defer agentEngine.Close()

			server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, &fakeCreditStore{}, 1000)

			resp := getBuildPath(t, server, validToken, "/jobs/preview")
			if resp.StatusCode != tc.status {
				t.Fatalf("status = %d, want %d (proxied unchanged)", resp.StatusCode, tc.status)
			}
			if requestedPath != "/api/preview" {
				t.Fatalf("agent-engine received path = %q, want %q", requestedPath, "/api/preview")
			}
		})
	}
}

func TestHandlePreviewStopAndRestartRejectMissingToken(t *testing.T) {
	for _, path := range []string{"/jobs/preview/stop", "/jobs/preview/restart"} {
		t.Run(path, func(t *testing.T) {
			agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				t.Fatal("agent-engine must not be called for an unauthenticated request")
			}))
			defer agentEngine.Close()

			server := newTestServer(t, agentEngine.URL, fakeAuthStore{returnErr: auth.ErrSessionNotFound}, &fakeCreditStore{}, 1000)

			resp := postPath(t, server, "", path, "")
			if resp.StatusCode != http.StatusUnauthorized {
				t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusUnauthorized)
			}
		})
	}
}

func TestHandlePreviewStopAndRestartProxyVerbatimAndDoNotDebit(t *testing.T) {
	cases := []struct {
		jobsPath     string
		agentPath    string
		responseBody string
	}{
		{"/jobs/preview/stop", "/api/preview/stop", `{"status":"stopped"}`},
		{"/jobs/preview/restart", "/api/preview/restart", `{"status":"ready","url":"http://127.0.0.1:53211"}`},
	}
	for _, tc := range cases {
		t.Run(tc.jobsPath, func(t *testing.T) {
			var requestedPath string
			agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				requestedPath = r.URL.Path
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusOK)
				_, _ = w.Write([]byte(tc.responseBody))
			}))
			defer agentEngine.Close()

			creditStore := &fakeCreditStore{}
			server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, creditStore, 1000)

			resp := postPath(t, server, validToken, tc.jobsPath, "")
			if resp.StatusCode != http.StatusOK {
				t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusOK)
			}
			if requestedPath != tc.agentPath {
				t.Fatalf("agent-engine received path = %q, want %q", requestedPath, tc.agentPath)
			}
			if creditStore.callCount() != 0 {
				t.Fatalf("DebitCredits called %d times, want 0 (preview control is not billable)", creditStore.callCount())
			}
		})
	}
}

func TestHandlePreviewStopProxiesNotEnabledUnchanged(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"error":"preview controls are not enabled"}`))
	}))
	defer agentEngine.Close()

	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, &fakeCreditStore{}, 1000)

	resp := postPath(t, server, validToken, "/jobs/preview/stop", "")
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("status = %d, want %d (proxied unchanged)", resp.StatusCode, http.StatusNotFound)
	}
}

func TestHandleBuildPreviewRejectsMissingToken(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("agent-engine must not be called for an unauthenticated request")
	}))
	defer agentEngine.Close()

	server := newTestServer(t, agentEngine.URL, fakeAuthStore{returnErr: auth.ErrSessionNotFound}, &fakeCreditStore{}, 1000)

	resp := postPath(t, server, "", "/jobs/build/abc123/preview", `{"id":"someone-elses-build"}`)
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusUnauthorized)
	}
}

func TestHandleBuildPreviewAlwaysSendsTheURLPathIDIgnoringTheCallersBody(t *testing.T) {
	var requestedPath, receivedBody string
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestedPath = r.URL.Path
		raw, err := io.ReadAll(r.Body)
		if err != nil {
			t.Fatal(err)
		}
		receivedBody = string(raw)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ready","url":"http://127.0.0.1:53211"}`))
	}))
	defer agentEngine.Close()

	creditStore := &fakeCreditStore{}
	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, creditStore, 1000)

	// The caller's body names a completely different build id - it must be ignored. Only the URL
	// path id is ever trusted for which build to preview.
	resp := postPath(t, server, validToken, "/jobs/build/abc123/preview", `{"id":"someone-elses-build"}`)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusOK)
	}
	if requestedPath != "/api/history/preview" {
		t.Fatalf("agent-engine received path = %q, want %q", requestedPath, "/api/history/preview")
	}
	if receivedBody != `{"id":"abc123"}` {
		t.Fatalf("agent-engine received body = %q, want %q (server-constructed from the URL path, not the caller's body)", receivedBody, `{"id":"abc123"}`)
	}
	if creditStore.callCount() != 0 {
		t.Fatalf("DebitCredits called %d times, want 0 (preview is not billable)", creditStore.callCount())
	}
}

func TestHandleBuildPreviewProxiesThe200WithErrorStatusShapeForAnUnknownBuild(t *testing.T) {
	// _preview_recorded_build (live_serve.py) has no exception path for an unknown/evicted build -
	// it returns a plain error dict, sent as a 200. This proxy must not "fix" that into a 404; it
	// forwards exactly what the agent-engine says.
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"error","message":"That build is no longer available in this session."}`))
	}))
	defer agentEngine.Close()

	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, &fakeCreditStore{}, 1000)

	resp := postPath(t, server, validToken, "/jobs/build/gone123/preview", `{}`)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want %d (the agent-engine's own shape, not a synthesized 404)", resp.StatusCode, http.StatusOK)
	}
	var payload map[string]any
	decodeJSON(t, resp, &payload)
	if payload["status"] != "error" {
		t.Fatalf("payload[status] = %v, want %q", payload["status"], "error")
	}
	if payload["message"] != "That build is no longer available in this session." {
		t.Fatalf("payload[message] = %v, want the agent-engine's own message", payload["message"])
	}
}

func TestHandleBuildPreviewProxiesNotEnabledUnchanged(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"error":"preview controls are not enabled"}`))
	}))
	defer agentEngine.Close()

	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, &fakeCreditStore{}, 1000)

	resp := postPath(t, server, validToken, "/jobs/build/abc123/preview", `{}`)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("status = %d, want %d (proxied unchanged)", resp.StatusCode, http.StatusNotFound)
	}
}

func TestHandleBuildPreviewReturnsBadGatewayWhenAgentEngineIsUnreachable(t *testing.T) {
	closedServer := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}))
	unreachableURL := closedServer.URL
	closedServer.Close()

	server := newTestServer(t, unreachableURL, fakeAuthStore{user: newTestUser()}, &fakeCreditStore{}, 1000)

	resp := postPath(t, server, validToken, "/jobs/build/abc123/preview", `{}`)
	if resp.StatusCode != http.StatusBadGateway {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusBadGateway)
	}
}

func TestHandleBuildReturns500WhenDebitCreditsFails(t *testing.T) {
	agentEngine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"name":"Tech Blog","usage":{"cost_micros_usd":250000}}`))
	}))
	defer agentEngine.Close()

	creditStore := &fakeCreditStore{returnErr: errors.New("database is on fire")}
	server := newTestServer(t, agentEngine.URL, fakeAuthStore{user: newTestUser()}, creditStore, 1000)

	resp := postBuild(t, server, validToken, `{"prompt":"a blog"}`)
	if resp.StatusCode != http.StatusInternalServerError {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusInternalServerError)
	}
}

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

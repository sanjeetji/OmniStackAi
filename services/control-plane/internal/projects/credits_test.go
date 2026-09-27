package projects

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/credits"
)

// PC-010: no paid model work at zero credits, and the task budget is the control plane's alone.
func creditServer(t *testing.T, balance int64, studio string) (*httptest.Server, string) {
	t.Helper()
	pStore := newFakeProjectStore()
	user := auth.User{ID: "usr-credit", Email: "c@example.com", CreditBalance: balance}
	project, _ := pStore.CreateProject(context.Background(), user.ID, "Credits", "")
	guard := credits.Guard{CreditsPerUSD: 1000, TaskBudgetCredits: 200}
	mux := http.NewServeMux()
	Register(mux, Deps{AuthStore: fakeAuthStore{user: user}, ProjectStore: pStore, AgentEngineURL: studio,
		CreditsPerUSD: 1000, CreditGuard: &guard})
	server := httptest.NewServer(mux)
	t.Cleanup(server.Close)
	return server, project.ID
}

func postBuild(t *testing.T, server *httptest.Server, projectID, body string) *http.Response {
	t.Helper()
	req, _ := http.NewRequest(http.MethodPost, server.URL+"/projects/"+projectID+"/build/stream", strings.NewReader(body))
	req.Header.Set("Authorization", testBearer)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	return resp
}

func TestABuildAtZeroCreditsIsRefusedBeforeAnyWork(t *testing.T) {
	called := false
	studio := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true }))
	defer studio.Close()
	server, id := creditServer(t, 0, studio.URL)
	resp := postBuild(t, server, id, `{"prompt":"a blog"}`)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusPaymentRequired {
		t.Fatalf("status %d, want 402", resp.StatusCode)
	}
	if called {
		t.Error("the Studio was called for a user with no credits")
	}
}

func TestTheBudgetIsSetHereAndNeverByTheCaller(t *testing.T) {
	var got map[string]any
	studio := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewDecoder(r.Body).Decode(&got)
		w.Header().Set("Content-Type", "text/event-stream")
	}))
	defer studio.Close()
	server, id := creditServer(t, 50, studio.URL)
	resp := postBuild(t, server, id, `{"prompt":"a blog","budget_micros":999999999}`)
	resp.Body.Close()
	want := float64(credits.CreditsToMicros(50, 1000)) // the balance, below the task budget
	if got["budget_micros"] != want {
		t.Errorf("budget_micros = %v, want %v (the caller asked for 999999999)", got["budget_micros"], want)
	}
}

func TestTheEstimateComesBeforeTheBuild(t *testing.T) {
	studio := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/estimate" || r.URL.Query().Get("kind") != "build" {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		_, _ = w.Write([]byte(`{"priced":true,"cost_micros_low":2000,"cost_micros_high":9000,"basis":"typical","provider_id":"groq","model_id":"openai/gpt-oss-120b"}`))
	}))
	defer studio.Close()
	for _, tc := range []struct {
		balance  int64
		canStart bool
	}{{500, true}, {0, false}} {
		server, id := creditServer(t, tc.balance, studio.URL)
		req, _ := http.NewRequest(http.MethodGet, server.URL+"/projects/"+id+"/estimate?kind=build", nil)
		req.Header.Set("Authorization", testBearer)
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatal(err)
		}
		var got map[string]any
		_ = json.NewDecoder(resp.Body).Decode(&got)
		resp.Body.Close()
		if got["credits_low"] != float64(2) || got["credits_high"] != float64(9) {
			t.Errorf("balance %d: credits %v-%v, want 2-9 (1000 credits per USD)", tc.balance, got["credits_low"], got["credits_high"])
		}
		if got["can_start"] != tc.canStart {
			t.Errorf("balance %d: can_start %v, want %v (%v)", tc.balance, got["can_start"], tc.canStart, got["reason"])
		}
	}
}

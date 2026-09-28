package projects

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/credits"
)

// PC-098: the model designs the pages after the build, as its own step with a build's guards and
// billing.
func designServer(t *testing.T, user auth.User, studio string) (*httptest.Server, *fakeProjectStore, string) {
	t.Helper()
	pStore := newFakeProjectStore()
	project, _ := pStore.CreateProject(context.Background(), user.ID, "Design", "")
	guard := credits.Guard{CreditsPerUSD: 1000, TaskBudgetCredits: 200}
	mux := http.NewServeMux()
	Register(mux, Deps{AuthStore: fakeAuthStore{user: user}, ProjectStore: pStore, AgentEngineURL: studio,
		CreditsPerUSD: 1000, CreditGuard: &guard})
	server := httptest.NewServer(mux)
	t.Cleanup(server.Close)
	return server, pStore, project.ID
}

func postDesign(t *testing.T, server *httptest.Server, id, body string) (*http.Response, string) {
	t.Helper()
	req, _ := http.NewRequest(http.MethodPost, server.URL+"/projects/"+id+"/design/stream", strings.NewReader(body))
	req.Header.Set("Authorization", testBearer)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	raw, _ := io.ReadAll(resp.Body)
	_ = resp.Body.Close()
	return resp, string(raw)
}

func TestPageDesignIsStreamedAndBilledLikeABuild(t *testing.T) {
	var sent map[string]any
	studio := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/workspaces/"+"p-1"+"/design/stream" && !strings.HasSuffix(r.URL.Path, "/design/stream") {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		_ = json.NewDecoder(r.Body).Decode(&sent)
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = io.WriteString(w, "data: {\"phase\":\"planned\",\"pages\":[\"apps/web/app/page.tsx\"]}\n\n")
		_, _ = io.WriteString(w, "data: {\"phase\":\"page\",\"path\":\"apps/web/app/page.tsx\",\"status\":\"designed\"}\n\n")
		_, _ = io.WriteString(w, "data: {\"phase\":\"done\",\"designed\":1,\"kept_template\":0,\"usage\":{\"billable_cost_micros_usd\":30000}}\n\n")
	}))
	defer studio.Close()
	user := auth.User{EmailVerified: true, ID: "usr-design", Email: "d@example.com", CreditBalance: 500}
	server, store, id := designServer(t, user, studio.URL)
	resp, body := postDesign(t, server, id, `{"pages":["apps/web/app/page.tsx"],"budget_micros":999999999}`)
	if resp.StatusCode != http.StatusOK || !strings.Contains(body, `"designed"`) {
		t.Fatalf("got %d %s", resp.StatusCode, body)
	}
	if got, _ := sent["budget_micros"].(float64); got <= 0 || got > float64(credits.CreditsToMicros(200, 1000)) {
		t.Errorf("budget_micros = %v: the control plane sets it (plan and task limits), never the caller", sent["budget_micros"])
	}
	if pages, _ := sent["pages"].([]any); len(pages) != 1 {
		t.Errorf("the pages named by an edit must reach the Studio: %v", sent["pages"])
	}
	if len(store.debitCalls) != 1 || store.debitCalls[0].requested != 30 || store.debitCalls[0].reason != "project:design" {
		t.Fatalf("debits = %+v, want 30 credits for project:design", store.debitCalls)
	}
	if !strings.Contains(body, "credits_spent") {
		t.Error("the person is told what the design cost")
	}
}

func TestPageDesignHasABuildsGuards(t *testing.T) {
	called := false
	studio := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true }))
	defer studio.Close()
	broke := auth.User{EmailVerified: true, ID: "usr-broke", Email: "b@example.com", CreditBalance: 0}
	server, _, id := designServer(t, broke, studio.URL)
	if resp, _ := postDesign(t, server, id, `{}`); resp.StatusCode != http.StatusPaymentRequired {
		t.Fatalf("zero credits: %d, want 402", resp.StatusCode)
	}
	unverified := auth.User{ID: "usr-new", Email: "n@example.com", CreditBalance: 100}
	server, _, id = designServer(t, unverified, studio.URL)
	if resp, _ := postDesign(t, server, id, `{}`); resp.StatusCode != http.StatusForbidden {
		t.Fatalf("unverified: %d, want 403", resp.StatusCode)
	}
	if called {
		t.Error("the Studio was called although the guards refused")
	}
}

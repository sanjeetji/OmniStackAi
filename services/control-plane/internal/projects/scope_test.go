package projects

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// PC-127: the scope proposal is the agent-engine's answer, passed through for signed-in users only.
func TestTheScopeIsProposedForSignedInUsers(t *testing.T) {
	var seen string
	studio := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/scope" || r.Method != http.MethodPost {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		body, _ := io.ReadAll(r.Body)
		seen = string(body)
		_, _ = w.Write([]byte(`{"shape":"single_admin","apps":[{"id":"web","included":true}]}`))
	}))
	defer studio.Close()
	server, _ := creditServer(t, 100, studio.URL)

	req, _ := http.NewRequest(http.MethodPost, server.URL+"/scope", strings.NewReader(`{"prompt":"A simple blog"}`))
	req.Header.Set("Authorization", testBearer)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	var got map[string]any
	_ = json.NewDecoder(resp.Body).Decode(&got)
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK || got["shape"] != "single_admin" {
		t.Fatalf("status %d, body %v", resp.StatusCode, got)
	}
	if !strings.Contains(seen, "A simple blog") {
		t.Errorf("the prompt did not reach the agent-engine: %q", seen)
	}

	anonymous, _ := http.NewRequest(http.MethodPost, server.URL+"/scope", strings.NewReader(`{"prompt":"x"}`))
	resp, err = http.DefaultClient.Do(anonymous)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusUnauthorized {
		t.Errorf("anonymous: status %d, want 401", resp.StatusCode)
	}
}

// PC-128: the brief, likewise.
func TestTheBriefIsProposedForSignedInUsers(t *testing.T) {
	studio := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/brief" {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		_, _ = w.Write([]byte(`{"questions":[{"id":"signup","answer":"anyone"}]}`))
	}))
	defer studio.Close()
	server, _ := creditServer(t, 100, studio.URL)
	req, _ := http.NewRequest(http.MethodPost, server.URL+"/brief", strings.NewReader(`{"prompt":"A shop"}`))
	req.Header.Set("Authorization", testBearer)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status %d", resp.StatusCode)
	}
}

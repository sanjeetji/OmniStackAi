package main

import (
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/config"
)

// TestNewMuxRegistersEveryRouteWithoutConflict builds the complete production route table.
// Go's ServeMux panics when two packages register the same method+pattern; before R-518 the
// projects and seo packages both registered POST /projects/{id}/seo/audit and .../seo/suggest,
// so the real server could not start even though every package's own tests passed (each
// package tests its routes on a private mux). This test is the guard for that whole class of bug.
func TestNewMuxRegistersEveryRouteWithoutConflict(t *testing.T) {
	defer func() {
		if recovered := recover(); recovered != nil {
			t.Fatalf("building the production mux panicked: %v", recovered)
		}
	}()
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	mux := newMux(nil, config.Config{AgentEngineURL: "http://127.0.0.1:0"}, logger)
	if mux == nil {
		t.Fatal("newMux returned nil")
	}
}

// TestNewMuxRoutesAreReachable spot-checks that routes owned by different packages all resolve on
// the shared mux (an unauthenticated request must reach the handler and get 401, not the mux's
// 404/405), including both SEO routes whose duplicate registration was removed in R-518 and the
// POST /projects/{id}/opened route the console calls.
func TestNewMuxRoutesAreReachable(t *testing.T) {
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	mux := newMux(nil, config.Config{AgentEngineURL: "http://127.0.0.1:0"}, logger)

	cases := []struct{ method, path string }{
		{http.MethodGet, "/projects"},
		{http.MethodPost, "/projects/abc/seo/audit"},
		{http.MethodGet, "/projects/abc/seo/audit"},
		{http.MethodPost, "/projects/abc/seo/suggest"},
		{http.MethodPost, "/projects/abc/opened"},
		{http.MethodGet, "/skills"},
		{http.MethodGet, "/workspaces"},
		{http.MethodGet, "/connectors"},
		{http.MethodGet, "/templates"},
		{http.MethodGet, "/templates/ride-now"},
		{http.MethodPost, "/templates/ride-now/use"},
		{http.MethodGet, "/projects/abc/template"},
	}
	for _, tc := range cases {
		request := httptest.NewRequest(tc.method, tc.path, nil)
		recorder := httptest.NewRecorder()
		mux.ServeHTTP(recorder, request)
		if recorder.Code == http.StatusNotFound || recorder.Code == http.StatusMethodNotAllowed {
			t.Errorf("%s %s is not routed (status %d)", tc.method, tc.path, recorder.Code)
		}
	}
}

package health

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

type fakePinger struct {
	err              error
	observedDeadline bool
}

func (pinger *fakePinger) Ping(ctx context.Context) error {
	_, pinger.observedDeadline = ctx.Deadline()
	return pinger.err
}

func newTestMux(database Pinger, pingTimeout time.Duration) *http.ServeMux {
	mux := http.NewServeMux()
	Register(mux, database, pingTimeout)
	return mux
}

func TestHealthzDoesNotRequireDatabase(t *testing.T) {
	request := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	recorder := httptest.NewRecorder()

	newTestMux(nil, time.Second).ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d", recorder.Code)
	}
	if recorder.Body.String() != "{\"service\":\"control-plane\",\"status\":\"ok\"}\n" {
		t.Fatalf("body = %q", recorder.Body.String())
	}
}

func TestReadyzReportsReadyWithBoundedPing(t *testing.T) {
	database := &fakePinger{}
	request := httptest.NewRequest(http.MethodGet, "/readyz", nil)
	recorder := httptest.NewRecorder()

	newTestMux(database, time.Second).ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK || !database.observedDeadline {
		t.Fatalf("status = %d, observed deadline = %t", recorder.Code, database.observedDeadline)
	}
	if recorder.Body.String() != "{\"service\":\"control-plane\",\"status\":\"ready\"}\n" {
		t.Fatalf("body = %q", recorder.Body.String())
	}
}

func TestReadyzHidesDatabaseError(t *testing.T) {
	database := &fakePinger{err: errors.New("credential detail must not leak")}
	request := httptest.NewRequest(http.MethodGet, "/readyz", nil)
	recorder := httptest.NewRecorder()

	newTestMux(database, time.Second).ServeHTTP(recorder, request)

	if recorder.Code != http.StatusServiceUnavailable {
		t.Fatalf("status = %d", recorder.Code)
	}
	if recorder.Body.String() != "{\"service\":\"control-plane\",\"status\":\"unavailable\"}\n" {
		t.Fatalf("body = %q", recorder.Body.String())
	}
}

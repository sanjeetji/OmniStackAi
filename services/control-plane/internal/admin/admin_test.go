package admin

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

type fakeAuth struct{ user auth.User }

func (f fakeAuth) CreateUser(context.Context, string, string, string, int64) (auth.User, error) {
	return auth.User{}, nil
}
func (f fakeAuth) FindUserByEmail(context.Context, string) (auth.User, string, error) {
	return auth.User{}, "", nil
}
func (f fakeAuth) FindUserByID(context.Context, string) (auth.User, error) { return f.user, nil }
func (f fakeAuth) CreateSession(context.Context, string, string, time.Time) error {
	return nil
}
func (f fakeAuth) FindUserBySessionToken(context.Context, string) (auth.User, error) {
	if f.user.ID == "" {
		return auth.User{}, auth.ErrSessionNotFound
	}
	return f.user, nil
}
func (f fakeAuth) DeleteSession(context.Context, string) error { return nil }

// Only a super_admin may reach the console's API, and to anyone else it does not exist.
func TestTheConsoleIsInvisibleToEveryoneElse(t *testing.T) {
	for name, user := range map[string]auth.User{
		"signed out":   {},
		"regular user": {ID: "u1", Role: "user", Plan: "enterprise"},
	} {
		mux := http.NewServeMux()
		Register(mux, Deps{AuthStore: fakeAuth{user}}) // no database: a refusal must never reach it
		for _, route := range []struct{ method, path string }{
			{"GET", "/admin/overview"}, {"GET", "/admin/users"}, {"POST", "/admin/users/x/credits"},
			{"PUT", "/admin/users/x/plan"}, {"PUT", "/admin/users/x/role"},
			{"PUT", "/admin/settings/paid-model-work"}, {"GET", "/admin/audit"},
		} {
			req := httptest.NewRequest(route.method, route.path, nil)
			req.Header.Set("Authorization", "Bearer t")
			rec := httptest.NewRecorder()
			mux.ServeHTTP(rec, req)
			if rec.Code != http.StatusNotFound {
				t.Errorf("%s %s %s: %d, want 404", name, route.method, route.path, rec.Code)
			}
		}
	}
}

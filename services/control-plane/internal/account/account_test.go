package account

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

// PC-012: the account rules that do not need a database. The flows that do (verify by link, reset
// signs every session out, export, delete) are proven live and recorded in the CHANGELOG.

type fakeStore struct {
	auth.Store
	user auth.User
}

func (f fakeStore) FindUserBySessionToken(context.Context, string) (auth.User, error) {
	return f.user, nil
}

func (f fakeStore) FindUserByEmail(context.Context, string) (auth.User, string, error) {
	return f.user, "stored-hash", nil
}

type fakeHasher struct{ accept string }

func (h fakeHasher) Hash(p string) (string, error) { return p, nil }
func (h fakeHasher) Verify(_, plain string) (bool, error) {
	return plain == h.accept, nil
}

func TestLinksCarryARandomTokenAndOnlyItsHashIsStored(t *testing.T) {
	raw1, hash1, err := newToken()
	if err != nil {
		t.Fatal(err)
	}
	raw2, _, _ := newToken()
	if raw1 == raw2 || len(raw1) < 40 {
		t.Fatalf("tokens must be long and random: %q %q", raw1, raw2)
	}
	if hash1 == raw1 || hash1 != hashOf(raw1) || len(hash1) != 64 {
		t.Fatal("the stored value must be the SHA-256 of the token, never the token")
	}
	link := Deps{PublicURL: "https://app.example/"}.link("/verify-email", "a+b/c")
	if link != "https://app.example/verify-email?token=a%2Bb%2Fc" {
		t.Fatalf("link = %q", link)
	}
}

func TestAnUnverifiedAddressIsAskedToVerify(t *testing.T) {
	rec := httptest.NewRecorder()
	if RequireVerified(rec, auth.User{Email: "a@b.test"}) {
		t.Fatal("an unverified account must be refused")
	}
	var body map[string]any
	_ = json.Unmarshal(rec.Body.Bytes(), &body)
	if rec.Code != http.StatusForbidden || body["verify_email"] != true {
		t.Fatalf("got %d %v", rec.Code, body)
	}
	if !RequireVerified(httptest.NewRecorder(), auth.User{EmailVerified: true}) {
		t.Fatal("a verified account passes")
	}
	t.Setenv("OMNISTACKAI_REQUIRE_EMAIL_VERIFICATION", "0")
	if !RequireVerified(httptest.NewRecorder(), auth.User{}) {
		t.Fatal("the operator can switch the requirement off")
	}
}

func serve(deps Deps) *httptest.Server {
	mux := http.NewServeMux()
	Register(mux, deps)
	return httptest.NewServer(mux)
}

func call(t *testing.T, srv *httptest.Server, method, path, body string) (int, map[string]any) {
	t.Helper()
	req, _ := http.NewRequest(method, srv.URL+path, strings.NewReader(body))
	req.Header.Set("Authorization", "Bearer session")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = resp.Body.Close() }()
	var out map[string]any
	_ = json.NewDecoder(resp.Body).Decode(&out)
	return resp.StatusCode, out
}

func TestALinkWithoutATokenIsRefused(t *testing.T) {
	srv := serve(Deps{})
	defer srv.Close()
	for _, path := range []string{"/auth/verify-email", "/auth/reset-password"} {
		if code, _ := call(t, srv, http.MethodPost, path, `{}`); code != http.StatusBadRequest {
			t.Fatalf("%s without a token answered %d", path, code)
		}
	}
}

func TestDeletingAnAccountNeedsItsPassword(t *testing.T) {
	// Pool is nil: a wrong password must be refused before anything is touched.
	srv := serve(Deps{AuthStore: fakeStore{user: auth.User{ID: "u1", Email: "a@b.test"}}, Hasher: fakeHasher{accept: "right"}})
	defer srv.Close()
	code, body := call(t, srv, http.MethodPost, "/auth/me/delete", `{"password":"wrong"}`)
	if code != http.StatusForbidden {
		t.Fatalf("got %d %v", code, body)
	}
}

func TestRetentionComesFromTheEnvironment(t *testing.T) {
	if RetentionFromEnv().ModelCallDays != 400 {
		t.Fatal("model call records are kept 400 days by default, as the privacy policy says")
	}
	t.Setenv("OMNISTACKAI_MODEL_CALL_RETENTION_DAYS", "30")
	if RetentionFromEnv().ModelCallDays != 30 {
		t.Fatal("the operator can shorten it")
	}
}

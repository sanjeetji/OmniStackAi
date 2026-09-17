package auth

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strconv"
	"sync"
	"testing"
	"time"
)

// fakeStore is an in-memory Store used only by these handler tests, so they run hermetically and
// fast, without a real database - the real PostgreSQL-backed Store (internal/users) is exercised
// by this task's live manual smoke test instead, matching how internal/health's tests use a fake
// Pinger rather than a real database.
type fakeStore struct {
	mu       sync.Mutex
	nextID   int
	byEmail  map[string]*fakeUser
	byID     map[string]*fakeUser
	sessions map[string]fakeSession
	clock    func() time.Time
}

type fakeUser struct {
	profile      User
	passwordHash string
}

type fakeSession struct {
	userID    string
	expiresAt time.Time
}

func newFakeStore() *fakeStore {
	return &fakeStore{
		byEmail:  map[string]*fakeUser{},
		byID:     map[string]*fakeUser{},
		sessions: map[string]fakeSession{},
		clock:    time.Now,
	}
}

func (s *fakeStore) CreateUser(_ context.Context, email, passwordHash, name string, startingCredits int64) (User, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.byEmail[email]; exists {
		return User{}, ErrEmailTaken
	}
	s.nextID++
	user := User{
		ID:            "user-" + strconv.Itoa(s.nextID),
		Email:         email,
		Name:          name,
		Role:          "user",
		Plan:          "free",
		BYOKEnabled:   false,
		CreditBalance: startingCredits,
		CreatedAt:     s.clock(),
	}
	record := &fakeUser{profile: user, passwordHash: passwordHash}
	s.byEmail[email] = record
	s.byID[user.ID] = record
	return user, nil
}

func (s *fakeStore) FindUserByEmail(_ context.Context, email string) (User, string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	record, ok := s.byEmail[email]
	if !ok {
		return User{}, "", ErrUserNotFound
	}
	return record.profile, record.passwordHash, nil
}

func (s *fakeStore) FindUserByID(_ context.Context, id string) (User, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	record, ok := s.byID[id]
	if !ok {
		return User{}, ErrUserNotFound
	}
	return record.profile, nil
}

func (s *fakeStore) CreateSession(_ context.Context, tokenHash, userID string, expiresAt time.Time) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.sessions[tokenHash] = fakeSession{userID: userID, expiresAt: expiresAt}
	return nil
}

func (s *fakeStore) FindUserBySessionToken(_ context.Context, tokenHash string) (User, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	session, ok := s.sessions[tokenHash]
	if !ok || !session.expiresAt.After(s.clock()) {
		return User{}, ErrSessionNotFound
	}
	record, ok := s.byID[session.userID]
	if !ok {
		return User{}, ErrSessionNotFound
	}
	return record.profile, nil
}

func (s *fakeStore) DeleteSession(_ context.Context, tokenHash string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	delete(s.sessions, tokenHash)
	return nil
}

// fakeHasher is fast and deterministic for tests. It is not a real cryptographic hash and must
// never be wired into production - internal/password's real Hash/Verify are used there instead.
type fakeHasher struct{}

func (fakeHasher) Hash(plain string) (string, error) {
	return "fake:" + plain, nil
}

func (fakeHasher) Verify(encoded, plain string) (bool, error) {
	return encoded == "fake:"+plain, nil
}

func testDeps(store Store, clock func() time.Time) Deps {
	return Deps{
		Store:         store,
		Hasher:        fakeHasher{},
		SessionTTL:    time.Hour,
		SignupCredits: 100,
		Clock:         clock,
	}
}

func newTestServer(deps Deps) *httptest.Server {
	mux := http.NewServeMux()
	Register(mux, deps)
	return httptest.NewServer(mux)
}

func postJSON(t *testing.T, server *httptest.Server, path string, body any) *http.Response {
	t.Helper()
	encoded, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("json.Marshal() error = %v", err)
	}
	resp, err := server.Client().Post(server.URL+path, "application/json", bytes.NewReader(encoded))
	if err != nil {
		t.Fatalf("POST %s error = %v", path, err)
	}
	return resp
}

func decodeBody(t *testing.T, resp *http.Response, dst any) {
	t.Helper()
	defer func() { _ = resp.Body.Close() }()
	if err := json.NewDecoder(resp.Body).Decode(dst); err != nil {
		t.Fatalf("decode response body: %v", err)
	}
}

func TestRegisterCreatesAccountWithFreeplanAndSignupCredits(t *testing.T) {
	store := newFakeStore()
	server := newTestServer(testDeps(store, time.Now))
	defer server.Close()

	resp := postJSON(t, server, "/auth/register", map[string]string{
		"email":    "New.User@Example.com",
		"name":     "New User",
		"password": "correct-horse-battery",
	})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusCreated)
	}

	var got authResponse
	decodeBody(t, resp, &got)
	if got.Email != "new.user@example.com" {
		t.Fatalf("Email = %q, want normalized lowercase", got.Email)
	}
	if got.Name != "New User" {
		t.Fatalf("Name = %q, want %q", got.Name, "New User")
	}
	if got.Role != "user" || got.Plan != "free" {
		t.Fatalf("Role/Plan = %q/%q, want user/free", got.Role, got.Plan)
	}
	if got.CreditBalance != 100 {
		t.Fatalf("CreditBalance = %d, want 100 (the configured signup grant)", got.CreditBalance)
	}
	if got.Token == "" {
		t.Fatal("Token is empty, want a real session token")
	}
}

func TestRegisterRejectsDuplicateEmailCaseInsensitively(t *testing.T) {
	store := newFakeStore()
	server := newTestServer(testDeps(store, time.Now))
	defer server.Close()

	first := postJSON(t, server, "/auth/register", map[string]string{"email": "dup@example.com", "name": "Dup", "password": "password123"})
	if first.StatusCode != http.StatusCreated {
		t.Fatalf("first register status = %d", first.StatusCode)
	}

	second := postJSON(t, server, "/auth/register", map[string]string{"email": "DUP@Example.com", "name": "Dup", "password": "different123"})
	if second.StatusCode != http.StatusConflict {
		t.Fatalf("second register status = %d, want %d", second.StatusCode, http.StatusConflict)
	}
}

func TestRegisterRejectsInvalidEmailAndShortPassword(t *testing.T) {
	store := newFakeStore()
	server := newTestServer(testDeps(store, time.Now))
	defer server.Close()

	cases := []struct {
		name        string
		email       string
		accountName string
		pass        string
	}{
		{"invalid email", "not-an-email", "Person", "password123"},
		{"empty email", "", "Person", "password123"},
		{"short password", "person@example.com", "Person", "short"},
		{"missing name", "person@example.com", "", "password123"},
		{"whitespace-only name", "person@example.com", "   ", "password123"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp := postJSON(t, server, "/auth/register", map[string]string{"email": tc.email, "name": tc.accountName, "password": tc.pass})
			if resp.StatusCode != http.StatusBadRequest {
				t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusBadRequest)
			}
		})
	}
}

func TestRegisterRejectsUnknownFieldsInBody(t *testing.T) {
	store := newFakeStore()
	server := newTestServer(testDeps(store, time.Now))
	defer server.Close()

	resp := postJSON(t, server, "/auth/register", map[string]string{
		"email": "person@example.com", "name": "Person", "password": "password123", "role": "super_admin",
	})
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d (role must not be settable at registration)", resp.StatusCode, http.StatusBadRequest)
	}
}

func TestLoginSucceedsWithCorrectCredentialsCaseInsensitiveEmail(t *testing.T) {
	store := newFakeStore()
	server := newTestServer(testDeps(store, time.Now))
	defer server.Close()

	postJSON(t, server, "/auth/register", map[string]string{"email": "person@example.com", "name": "Person", "password": "password123"})

	resp := postJSON(t, server, "/auth/login", map[string]string{"email": "PERSON@example.com", "password": "password123"})
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusOK)
	}
	var got authResponse
	decodeBody(t, resp, &got)
	if got.Token == "" {
		t.Fatal("Token is empty")
	}
}

func TestLoginFailsIdenticallyForWrongPasswordAndUnknownEmail(t *testing.T) {
	store := newFakeStore()
	server := newTestServer(testDeps(store, time.Now))
	defer server.Close()

	postJSON(t, server, "/auth/register", map[string]string{"email": "person@example.com", "name": "Person", "password": "password123"})

	wrongPassword := postJSON(t, server, "/auth/login", map[string]string{"email": "person@example.com", "password": "nope-wrong"})
	unknownEmail := postJSON(t, server, "/auth/login", map[string]string{"email": "ghost@example.com", "password": "whatever123"})

	if wrongPassword.StatusCode != http.StatusUnauthorized || unknownEmail.StatusCode != http.StatusUnauthorized {
		t.Fatalf("statuses = %d, %d, want both %d", wrongPassword.StatusCode, unknownEmail.StatusCode, http.StatusUnauthorized)
	}

	var wrongBody, unknownBody errorResponse
	decodeBody(t, wrongPassword, &wrongBody)
	decodeBody(t, unknownEmail, &unknownBody)
	if wrongBody.Error != unknownBody.Error {
		t.Fatalf("error messages differ (%q vs %q); this would let an attacker enumerate registered emails", wrongBody.Error, unknownBody.Error)
	}
}

func TestSessionExpiryIsComputedFromInjectedClockAndSessionTTL(t *testing.T) {
	store := newFakeStore()
	fixedNow := time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)
	deps := testDeps(store, func() time.Time { return fixedNow })
	deps.SessionTTL = 2 * time.Hour
	server := newTestServer(deps)
	defer server.Close()
	store.clock = func() time.Time { return fixedNow }

	resp := postJSON(t, server, "/auth/register", map[string]string{"email": "person@example.com", "name": "Person", "password": "password123"})
	var got authResponse
	decodeBody(t, resp, &got)

	hash := hashToken(got.Token)
	store.mu.Lock()
	session, ok := store.sessions[hash]
	store.mu.Unlock()
	if !ok {
		t.Fatal("session was not recorded in the store")
	}
	want := fixedNow.Add(2 * time.Hour)
	if !session.expiresAt.Equal(want) {
		t.Fatalf("expiresAt = %s, want %s", session.expiresAt, want)
	}
}

func TestMeReturnsProfileForValidTokenAndRejectsMissingOrUnknownToken(t *testing.T) {
	store := newFakeStore()
	server := newTestServer(testDeps(store, time.Now))
	defer server.Close()

	registerResp := postJSON(t, server, "/auth/register", map[string]string{"email": "person@example.com", "name": "Person", "password": "password123"})
	var registered authResponse
	decodeBody(t, registerResp, &registered)

	authed, err := http.NewRequest(http.MethodGet, server.URL+"/auth/me", nil)
	if err != nil {
		t.Fatal(err)
	}
	authed.Header.Set("Authorization", "Bearer "+registered.Token)
	resp, err := server.Client().Do(authed)
	if err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("authenticated /auth/me status = %d, want %d", resp.StatusCode, http.StatusOK)
	}
	var me userResponse
	decodeBody(t, resp, &me)
	if me.Email != "person@example.com" {
		t.Fatalf("me.Email = %q", me.Email)
	}
	if me.Name != "Person" {
		t.Fatalf("me.Name = %q, want %q", me.Name, "Person")
	}

	noHeader, _ := http.NewRequest(http.MethodGet, server.URL+"/auth/me", nil)
	noHeaderResp, err := server.Client().Do(noHeader)
	if err != nil {
		t.Fatal(err)
	}
	if noHeaderResp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("no-header status = %d, want %d", noHeaderResp.StatusCode, http.StatusUnauthorized)
	}

	garbage, _ := http.NewRequest(http.MethodGet, server.URL+"/auth/me", nil)
	garbage.Header.Set("Authorization", "Bearer this-token-does-not-exist")
	garbageResp, err := server.Client().Do(garbage)
	if err != nil {
		t.Fatal(err)
	}
	if garbageResp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("unknown-token status = %d, want %d", garbageResp.StatusCode, http.StatusUnauthorized)
	}
}

func TestMeRejectsExpiredSession(t *testing.T) {
	store := newFakeStore()
	server := newTestServer(testDeps(store, time.Now))
	defer server.Close()

	rawToken := randomHex(t)
	if err := store.CreateSession(context.Background(), hashToken(rawToken), "user-1", time.Now().Add(-time.Hour)); err != nil {
		t.Fatal(err)
	}
	store.byID["user-1"] = &fakeUser{profile: User{ID: "user-1", Email: "person@example.com"}}

	request, _ := http.NewRequest(http.MethodGet, server.URL+"/auth/me", nil)
	request.Header.Set("Authorization", "Bearer "+rawToken)
	resp, err := server.Client().Do(request)
	if err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d for an expired session", resp.StatusCode, http.StatusUnauthorized)
	}
}

func TestLogoutInvalidatesTheSessionAndIsIdempotent(t *testing.T) {
	store := newFakeStore()
	server := newTestServer(testDeps(store, time.Now))
	defer server.Close()

	registerResp := postJSON(t, server, "/auth/register", map[string]string{"email": "person@example.com", "name": "Person", "password": "password123"})
	var registered authResponse
	decodeBody(t, registerResp, &registered)

	logout := func() *http.Response {
		request, _ := http.NewRequest(http.MethodPost, server.URL+"/auth/logout", nil)
		request.Header.Set("Authorization", "Bearer "+registered.Token)
		resp, err := server.Client().Do(request)
		if err != nil {
			t.Fatal(err)
		}
		return resp
	}

	first := logout()
	if first.StatusCode != http.StatusNoContent {
		t.Fatalf("first logout status = %d, want %d", first.StatusCode, http.StatusNoContent)
	}
	second := logout()
	if second.StatusCode != http.StatusNoContent {
		t.Fatalf("second logout (already-invalid token) status = %d, want %d (idempotent)", second.StatusCode, http.StatusNoContent)
	}

	meRequest, _ := http.NewRequest(http.MethodGet, server.URL+"/auth/me", nil)
	meRequest.Header.Set("Authorization", "Bearer "+registered.Token)
	meResp, err := server.Client().Do(meRequest)
	if err != nil {
		t.Fatal(err)
	}
	if meResp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("/auth/me after logout status = %d, want %d (session must be gone)", meResp.StatusCode, http.StatusUnauthorized)
	}
}

func TestLogoutWithoutBearerTokenIsUnauthorized(t *testing.T) {
	store := newFakeStore()
	server := newTestServer(testDeps(store, time.Now))
	defer server.Close()

	request, _ := http.NewRequest(http.MethodPost, server.URL+"/auth/logout", nil)
	resp, err := server.Client().Do(request)
	if err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusUnauthorized)
	}
}

func TestFakeStoreCreateUserReturnsErrEmailTaken(t *testing.T) {
	store := newFakeStore()
	if _, err := store.CreateUser(context.Background(), "person@example.com", "hash", "Person", 0); err != nil {
		t.Fatal(err)
	}
	_, err := store.CreateUser(context.Background(), "person@example.com", "hash", "Person", 0)
	if !errors.Is(err, ErrEmailTaken) {
		t.Fatalf("err = %v, want ErrEmailTaken", err)
	}
}

func randomHex(t *testing.T) string {
	t.Helper()
	buf := make([]byte, 16)
	if _, err := rand.Read(buf); err != nil {
		t.Fatal(err)
	}
	return hex.EncodeToString(buf)
}

package workspaces

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

type fakeAuthStore struct {
	user auth.User
	err  error
}

func (f fakeAuthStore) CreateUser(context.Context, string, string, string, int64) (auth.User, error) {
	return f.user, f.err
}
func (f fakeAuthStore) FindUserByEmail(context.Context, string) (auth.User, string, error) {
	return f.user, "", f.err
}
func (f fakeAuthStore) FindUserByID(context.Context, string) (auth.User, error) {
	return f.user, f.err
}
func (f fakeAuthStore) CreateSession(context.Context, string, string, time.Time) error {
	return f.err
}
func (f fakeAuthStore) FindUserBySessionToken(context.Context, string) (auth.User, error) {
	if f.err != nil {
		return auth.User{}, f.err
	}
	return f.user, nil
}
func (f fakeAuthStore) DeleteSession(context.Context, string) error {
	return f.err
}

type fakeWorkspaceStore struct {
	workspaces []Workspace
	members    []WorkspaceMember
	invites    []WorkspaceInvite
	roles      map[string]Role
	err        error
}

func (f *fakeWorkspaceStore) EnsureDefaultWorkspace(ctx context.Context, userID, userName string) (Workspace, error) {
	if f.err != nil {
		return Workspace{}, f.err
	}
	if len(f.workspaces) > 0 {
		return f.workspaces[0], nil
	}
	ws := Workspace{
		ID:          "ws-1",
		OrgID:       "org-1",
		Name:        "Personal Workspace",
		Slug:        "default",
		IsDefault:   true,
		Role:        RoleOwner,
		MemberCount: 1,
	}
	f.workspaces = append(f.workspaces, ws)
	return ws, nil
}

func (f *fakeWorkspaceStore) ListUserWorkspaces(ctx context.Context, userID string) ([]Workspace, error) {
	if f.err != nil {
		return nil, f.err
	}
	return f.workspaces, nil
}

func (f *fakeWorkspaceStore) GetWorkspace(ctx context.Context, workspaceID, userID string) (Workspace, error) {
	if f.err != nil {
		return Workspace{}, f.err
	}
	for _, w := range f.workspaces {
		if w.ID == workspaceID {
			return w, nil
		}
	}
	return Workspace{}, ErrWorkspaceNotFound
}

func (f *fakeWorkspaceStore) CreateWorkspace(ctx context.Context, userID, name string) (Workspace, error) {
	if f.err != nil {
		return Workspace{}, f.err
	}
	ws := Workspace{
		ID:          "ws-new",
		OrgID:       "org-1",
		Name:        name,
		Slug:        slugify(name),
		IsDefault:   false,
		Role:        RoleOwner,
		MemberCount: 1,
	}
	f.workspaces = append(f.workspaces, ws)
	return ws, nil
}

func (f *fakeWorkspaceStore) UpdateWorkspace(ctx context.Context, workspaceID, userID, name string) (Workspace, error) {
	if f.err != nil {
		return Workspace{}, f.err
	}
	for i, w := range f.workspaces {
		if w.ID == workspaceID {
			f.workspaces[i].Name = name
			return f.workspaces[i], nil
		}
	}
	return Workspace{}, ErrWorkspaceNotFound
}

func (f *fakeWorkspaceStore) DeleteWorkspace(ctx context.Context, workspaceID, userID string) error {
	if f.err != nil {
		return f.err
	}
	for i, w := range f.workspaces {
		if w.ID == workspaceID {
			if w.IsDefault {
				return ErrCannotDeleteDefault
			}
			f.workspaces = append(f.workspaces[:i], f.workspaces[i+1:]...)
			return nil
		}
	}
	return ErrWorkspaceNotFound
}

func (f *fakeWorkspaceStore) ListMembers(ctx context.Context, workspaceID, userID string) ([]WorkspaceMember, error) {
	if f.err != nil {
		return nil, f.err
	}
	return f.members, nil
}

func (f *fakeWorkspaceStore) InviteMember(ctx context.Context, workspaceID, inviterID, email string, role Role) (WorkspaceInvite, error) {
	if f.err != nil {
		return WorkspaceInvite{}, f.err
	}
	inv := WorkspaceInvite{
		ID:          "inv-1",
		WorkspaceID: workspaceID,
		InviterID:   inviterID,
		Email:       email,
		Role:        role,
		Token:       "tok-12345",
		Status:      "pending",
		ExpiresAt:   time.Now().Add(7 * 24 * time.Hour),
	}
	f.invites = append(f.invites, inv)
	return inv, nil
}

func (f *fakeWorkspaceStore) ListInvites(ctx context.Context, workspaceID, userID string) ([]WorkspaceInvite, error) {
	if f.err != nil {
		return nil, f.err
	}
	return f.invites, nil
}

func (f *fakeWorkspaceStore) RevokeInvite(ctx context.Context, workspaceID, actorID, inviteID string) error {
	if f.err != nil {
		return f.err
	}
	for i, inv := range f.invites {
		if inv.ID == inviteID && inv.WorkspaceID == workspaceID {
			f.invites[i].Status = "revoked"
			return nil
		}
	}
	return ErrInviteNotFound
}

func (f *fakeWorkspaceStore) AcceptInvite(ctx context.Context, token, userID, userEmail string) (Workspace, error) {
	if f.err != nil {
		return Workspace{}, f.err
	}
	for i, inv := range f.invites {
		if inv.Token == token && inv.Status == "pending" {
			f.invites[i].Status = "accepted"
			ws := Workspace{
				ID:   inv.WorkspaceID,
				Name: "Accepted Workspace",
				Role: inv.Role,
			}
			return ws, nil
		}
	}
	return Workspace{}, ErrInviteNotFound
}

func (f *fakeWorkspaceStore) UpdateMemberRole(ctx context.Context, workspaceID, actorID, targetUserID string, newRole Role) error {
	if f.err != nil {
		return f.err
	}
	for i, m := range f.members {
		if m.UserID == targetUserID && m.WorkspaceID == workspaceID {
			f.members[i].Role = newRole
			return nil
		}
	}
	return errors.New("member not found")
}

func (f *fakeWorkspaceStore) RemoveMember(ctx context.Context, workspaceID, actorID, targetUserID string) error {
	if f.err != nil {
		return f.err
	}
	for i, m := range f.members {
		if m.UserID == targetUserID && m.WorkspaceID == workspaceID {
			f.members = append(f.members[:i], f.members[i+1:]...)
			return nil
		}
	}
	return errors.New("member not found")
}

func (f *fakeWorkspaceStore) GetUserWorkspaceRole(ctx context.Context, workspaceID, userID string) (Role, error) {
	if f.roles != nil {
		if r, ok := f.roles[workspaceID+":"+userID]; ok {
			return r, nil
		}
	}
	return RoleOwner, nil
}

func TestRolesAndRBAC(t *testing.T) {
	if !IsValidRole(RoleOwner) || !IsValidRole(RoleAdmin) || !IsValidRole(RoleMember) || !IsValidRole(RoleViewer) {
		t.Fatal("expected standard roles to be valid")
	}
	if IsValidRole("superman") {
		t.Fatal("expected arbitrary role to be invalid")
	}

	if !HasMinRole(RoleOwner, RoleAdmin) {
		t.Fatal("owner must satisfy admin")
	}
	if !HasMinRole(RoleAdmin, RoleMember) {
		t.Fatal("admin must satisfy member")
	}
	if !HasMinRole(RoleMember, RoleViewer) {
		t.Fatal("member must satisfy viewer")
	}
	if HasMinRole(RoleViewer, RoleMember) {
		t.Fatal("viewer must not satisfy member")
	}
	if HasMinRole(RoleMember, RoleAdmin) {
		t.Fatal("member must not satisfy admin")
	}
}

func TestSlugify(t *testing.T) {
	cases := map[string]string{
		"My Cool Team":        "my-cool-team",
		"  Acme, Inc. (2026)": "acme-inc-2026",
		"":                    "ws",
		"---":                 "ws",
	}
	for in, expected := range cases {
		got := slugify(in)
		if got != expected {
			t.Errorf("slugify(%q) = %q, expected %q", in, got, expected)
		}
	}
}

func TestWorkspaceHandlers(t *testing.T) {
	user := auth.User{ID: "usr-1", Email: "alice@example.com", Name: "Alice"}
	authStore := fakeAuthStore{user: user}

	wsStore := &fakeWorkspaceStore{
		workspaces: []Workspace{
			{ID: "ws-1", Name: "Alice's Workspace", IsDefault: true, Role: RoleOwner},
		},
		members: []WorkspaceMember{
			{ID: "m-1", WorkspaceID: "ws-1", UserID: "usr-1", UserName: "Alice", UserEmail: "alice@example.com", Role: RoleOwner},
		},
		roles: map[string]Role{
			"ws-1:usr-1": RoleOwner,
		},
	}

	mux := http.NewServeMux()
	Register(mux, Deps{
		AuthStore:      authStore,
		WorkspaceStore: wsStore,
	})

	addAuth := func(r *http.Request) *http.Request {
		r.Header.Set("Authorization", "Bearer test-token")
		return r
	}

	// 1. GET /workspaces
	req := addAuth(httptest.NewRequest(http.MethodGet, "/workspaces", nil))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var listResp map[string][]Workspace
	if err := json.NewDecoder(rec.Body).Decode(&listResp); err != nil {
		t.Fatal(err)
	}
	if len(listResp["workspaces"]) != 1 || listResp["workspaces"][0].Name != "Alice's Workspace" {
		t.Fatalf("unexpected list response: %+v", listResp)
	}

	// 2. POST /workspaces
	body := bytes.NewBufferString(`{"name":"Backend Team"}`)
	req = addAuth(httptest.NewRequest(http.MethodPost, "/workspaces", body))
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", rec.Code, rec.Body.String())
	}
	var created Workspace
	if err := json.NewDecoder(rec.Body).Decode(&created); err != nil {
		t.Fatal(err)
	}
	if created.Name != "Backend Team" {
		t.Fatalf("unexpected created name: %s", created.Name)
	}

	// 3. GET /workspaces/{id}
	req = addAuth(httptest.NewRequest(http.MethodGet, "/workspaces/ws-1", nil))
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}

	// 4. PATCH /workspaces/{id}
	body = bytes.NewBufferString(`{"name":"Core Platform"}`)
	req = addAuth(httptest.NewRequest(http.MethodPatch, "/workspaces/ws-1", body))
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
	}

	// 5. GET /workspaces/{id}/members
	req = addAuth(httptest.NewRequest(http.MethodGet, "/workspaces/ws-1/members", nil))
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}

	// 6. POST /workspaces/{id}/invites
	body = bytes.NewBufferString(`{"email":"bob@example.com","role":"member"}`)
	req = addAuth(httptest.NewRequest(http.MethodPost, "/workspaces/ws-1/invites", body))
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", rec.Code, rec.Body.String())
	}
	var inv WorkspaceInvite
	if err := json.NewDecoder(rec.Body).Decode(&inv); err != nil {
		t.Fatal(err)
	}
	if inv.Email != "bob@example.com" || inv.Role != RoleMember {
		t.Fatalf("unexpected invite payload: %+v", inv)
	}

	// 7. GET /workspaces/{id}/invites
	req = addAuth(httptest.NewRequest(http.MethodGet, "/workspaces/ws-1/invites", nil))
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}

	// 8. POST /workspaces/invites/{token}/accept
	req = addAuth(httptest.NewRequest(http.MethodPost, "/workspaces/invites/tok-12345/accept", nil))
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
	}

	// 9. DELETE /workspaces/{id} on default workspace fails
	req = addAuth(httptest.NewRequest(http.MethodDelete, "/workspaces/ws-1", nil))
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 when deleting default workspace, got %d: %s", rec.Code, rec.Body.String())
	}
}

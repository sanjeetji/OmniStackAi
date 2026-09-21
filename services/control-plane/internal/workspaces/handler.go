package workspaces

import (
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"strings"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

type Deps struct {
	AuthStore      auth.Store
	WorkspaceStore Store
	Logger         *slog.Logger
}

func (d Deps) logger() *slog.Logger {
	if d.Logger != nil {
		return d.Logger
	}
	return slog.Default()
}

func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /workspaces", handleListWorkspaces(deps))
	mux.HandleFunc("POST /workspaces", handleCreateWorkspace(deps))
	mux.HandleFunc("GET /workspaces/{id}", handleGetWorkspace(deps))
	mux.HandleFunc("PATCH /workspaces/{id}", handleUpdateWorkspace(deps))
	mux.HandleFunc("DELETE /workspaces/{id}", handleDeleteWorkspace(deps))

	mux.HandleFunc("GET /workspaces/{id}/members", handleListMembers(deps))
	mux.HandleFunc("POST /workspaces/{id}/invites", handleCreateInvite(deps))
	mux.HandleFunc("GET /workspaces/{id}/invites", handleListInvites(deps))
	mux.HandleFunc("DELETE /workspaces/{id}/invites/{inviteId}", handleRevokeInvite(deps))

	mux.HandleFunc("POST /workspaces/invites/{token}/accept", handleAcceptInvite(deps))
	mux.HandleFunc("PATCH /workspaces/{id}/members/{userId}", handleUpdateMemberRole(deps))
	mux.HandleFunc("DELETE /workspaces/{id}/members/{userId}", handleRemoveMember(deps))
}

func handleListWorkspaces(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		// Ensure user has at least a personal default workspace
		_, _ = deps.WorkspaceStore.EnsureDefaultWorkspace(r.Context(), user.ID, user.Name)

		list, err := deps.WorkspaceStore.ListUserWorkspaces(r.Context(), user.ID)
		if err != nil {
			deps.logger().Error("list workspaces", "error", err)
			writeError(w, http.StatusInternalServerError, "could not list workspaces")
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{"workspaces": list})
	}
}

func handleCreateWorkspace(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		var req struct {
			Name string `json:"name"`
		}
		if r.Body != nil {
			_ = json.NewDecoder(r.Body).Decode(&req)
		}

		name := strings.TrimSpace(req.Name)
		if name == "" {
			writeError(w, http.StatusBadRequest, "workspace name is required")
			return
		}

		ws, err := deps.WorkspaceStore.CreateWorkspace(r.Context(), user.ID, name)
		if err != nil {
			deps.logger().Error("create workspace", "error", err)
			writeError(w, http.StatusInternalServerError, "could not create workspace")
			return
		}

		writeJSON(w, http.StatusCreated, ws)
	}
}

func handleGetWorkspace(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		ws, err := deps.WorkspaceStore.GetWorkspace(r.Context(), id, user.ID)
		if errors.Is(err, ErrWorkspaceNotFound) {
			writeError(w, http.StatusNotFound, "workspace not found")
			return
		}
		if err != nil {
			deps.logger().Error("get workspace", "error", err)
			writeError(w, http.StatusInternalServerError, "could not get workspace")
			return
		}

		writeJSON(w, http.StatusOK, ws)
	}
}

func handleUpdateWorkspace(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		var req struct {
			Name string `json:"name"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeError(w, http.StatusBadRequest, "invalid request body")
			return
		}

		ws, err := deps.WorkspaceStore.UpdateWorkspace(r.Context(), id, user.ID, req.Name)
		if errors.Is(err, ErrWorkspaceNotFound) {
			writeError(w, http.StatusNotFound, "workspace not found")
			return
		}
		if errors.Is(err, ErrForbidden) {
			writeError(w, http.StatusForbidden, "only admins and owners can update workspace")
			return
		}
		if err != nil {
			deps.logger().Error("update workspace", "error", err)
			writeError(w, http.StatusInternalServerError, "could not update workspace")
			return
		}

		writeJSON(w, http.StatusOK, ws)
	}
}

func handleDeleteWorkspace(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		err = deps.WorkspaceStore.DeleteWorkspace(r.Context(), id, user.ID)
		if errors.Is(err, ErrWorkspaceNotFound) {
			writeError(w, http.StatusNotFound, "workspace not found")
			return
		}
		if errors.Is(err, ErrCannotDeleteDefault) {
			writeError(w, http.StatusBadRequest, "cannot delete default personal workspace")
			return
		}
		if errors.Is(err, ErrForbidden) {
			writeError(w, http.StatusForbidden, "only workspace owner can delete workspace")
			return
		}
		if err != nil {
			deps.logger().Error("delete workspace", "error", err)
			writeError(w, http.StatusInternalServerError, "could not delete workspace")
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{"ok": true})
	}
}

func handleListMembers(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		members, err := deps.WorkspaceStore.ListMembers(r.Context(), id, user.ID)
		if errors.Is(err, ErrWorkspaceNotFound) {
			writeError(w, http.StatusNotFound, "workspace not found")
			return
		}
		if err != nil {
			deps.logger().Error("list members", "error", err)
			writeError(w, http.StatusInternalServerError, "could not list members")
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{"members": members})
	}
}

func handleCreateInvite(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		var req struct {
			Email string `json:"email"`
			Role  string `json:"role"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeError(w, http.StatusBadRequest, "invalid request body")
			return
		}

		role := Role(req.Role)
		if role == "" {
			role = RoleMember
		}

		inv, err := deps.WorkspaceStore.InviteMember(r.Context(), id, user.ID, req.Email, role)
		if errors.Is(err, ErrWorkspaceNotFound) {
			writeError(w, http.StatusNotFound, "workspace not found")
			return
		}
		if errors.Is(err, ErrForbidden) {
			writeError(w, http.StatusForbidden, "only admins and owners can invite members")
			return
		}
		if errors.Is(err, ErrAlreadyMember) {
			writeError(w, http.StatusConflict, "user is already a member of this workspace")
			return
		}
		if errors.Is(err, ErrInvalidRole) {
			writeError(w, http.StatusBadRequest, "invalid role: choose admin, member, or viewer")
			return
		}
		if err != nil {
			deps.logger().Error("create invite", "error", err)
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}

		writeJSON(w, http.StatusCreated, inv)
	}
}

func handleListInvites(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		invites, err := deps.WorkspaceStore.ListInvites(r.Context(), id, user.ID)
		if errors.Is(err, ErrWorkspaceNotFound) {
			writeError(w, http.StatusNotFound, "workspace not found")
			return
		}
		if errors.Is(err, ErrForbidden) {
			writeError(w, http.StatusForbidden, "only admins and owners can view invites")
			return
		}
		if err != nil {
			deps.logger().Error("list invites", "error", err)
			writeError(w, http.StatusInternalServerError, "could not list invites")
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{"invites": invites})
	}
}

func handleRevokeInvite(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		inviteID := r.PathValue("inviteId")
		err = deps.WorkspaceStore.RevokeInvite(r.Context(), id, user.ID, inviteID)
		if errors.Is(err, ErrWorkspaceNotFound) {
			writeError(w, http.StatusNotFound, "workspace not found")
			return
		}
		if errors.Is(err, ErrForbidden) {
			writeError(w, http.StatusForbidden, "only admins and owners can revoke invites")
			return
		}
		if errors.Is(err, ErrInviteNotFound) {
			writeError(w, http.StatusNotFound, "invite not found or already processed")
			return
		}
		if err != nil {
			deps.logger().Error("revoke invite", "error", err)
			writeError(w, http.StatusInternalServerError, "could not revoke invite")
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{"ok": true})
	}
}

func handleAcceptInvite(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		token := r.PathValue("token")
		ws, err := deps.WorkspaceStore.AcceptInvite(r.Context(), token, user.ID, user.Email)
		if errors.Is(err, ErrInviteNotFound) {
			writeError(w, http.StatusNotFound, "invitation link is invalid or expired")
			return
		}
		if err != nil {
			deps.logger().Error("accept invite", "error", err)
			writeError(w, http.StatusInternalServerError, "could not accept invitation")
			return
		}

		writeJSON(w, http.StatusOK, ws)
	}
}

func handleUpdateMemberRole(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		targetUserID := r.PathValue("userId")

		var req struct {
			Role string `json:"role"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeError(w, http.StatusBadRequest, "invalid request body")
			return
		}

		err = deps.WorkspaceStore.UpdateMemberRole(r.Context(), id, user.ID, targetUserID, Role(req.Role))
		if errors.Is(err, ErrWorkspaceNotFound) {
			writeError(w, http.StatusNotFound, "workspace not found")
			return
		}
		if errors.Is(err, ErrForbidden) {
			writeError(w, http.StatusForbidden, "insufficient permission to update role")
			return
		}
		if errors.Is(err, ErrCannotRemoveOwner) {
			writeError(w, http.StatusBadRequest, "cannot demote the sole workspace owner")
			return
		}
		if errors.Is(err, ErrInvalidRole) {
			writeError(w, http.StatusBadRequest, "invalid role specified")
			return
		}
		if err != nil {
			deps.logger().Error("update member role", "error", err)
			writeError(w, http.StatusInternalServerError, "could not update member role")
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{"ok": true})
	}
}

func handleRemoveMember(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		targetUserID := r.PathValue("userId")

		err = deps.WorkspaceStore.RemoveMember(r.Context(), id, user.ID, targetUserID)
		if errors.Is(err, ErrWorkspaceNotFound) {
			writeError(w, http.StatusNotFound, "workspace not found")
			return
		}
		if errors.Is(err, ErrForbidden) {
			writeError(w, http.StatusForbidden, "insufficient permission to remove member")
			return
		}
		if errors.Is(err, ErrCannotRemoveOwner) {
			writeError(w, http.StatusBadRequest, "cannot remove the sole workspace owner")
			return
		}
		if err != nil {
			deps.logger().Error("remove member", "error", err)
			writeError(w, http.StatusInternalServerError, "could not remove member")
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{"ok": true})
	}
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func writeAuthError(w http.ResponseWriter, deps Deps, err error) {
	if errors.Is(err, auth.ErrUnauthenticated) {
		writeError(w, http.StatusUnauthorized, "missing bearer token or session not found or expired")
		return
	}
	writeError(w, http.StatusUnauthorized, "authentication required")
}

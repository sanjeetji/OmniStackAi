package workspaces

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

var (
	ErrWorkspaceNotFound   = errors.New("workspaces: workspace not found")
	ErrUnauthorized        = errors.New("workspaces: unauthorized")
	ErrForbidden           = errors.New("workspaces: forbidden, insufficient role")
	ErrCannotDeleteDefault = errors.New("workspaces: cannot delete default personal workspace")
	ErrCannotRemoveOwner   = errors.New("workspaces: cannot remove or demote the last workspace owner")
	ErrInviteNotFound      = errors.New("workspaces: invite not found or expired")
	ErrAlreadyMember       = errors.New("workspaces: user is already a member of this workspace")
	ErrInvalidRole         = errors.New("workspaces: invalid role")
)

type Role string

const (
	RoleOwner  Role = "owner"
	RoleAdmin  Role = "admin"
	RoleMember Role = "member"
	RoleViewer Role = "viewer"
)

func IsValidRole(r Role) bool {
	switch r {
	case RoleOwner, RoleAdmin, RoleMember, RoleViewer:
		return true
	default:
		return false
	}
}

func RoleLevel(r Role) int {
	switch r {
	case RoleOwner:
		return 4
	case RoleAdmin:
		return 3
	case RoleMember:
		return 2
	case RoleViewer:
		return 1
	default:
		return 0
	}
}

func HasMinRole(current, required Role) bool {
	return RoleLevel(current) >= RoleLevel(required)
}

type Workspace struct {
	ID           string    `json:"id"`
	OrgID        string    `json:"org_id"`
	Name         string    `json:"name"`
	Slug         string    `json:"slug"`
	IsDefault    bool      `json:"is_default"`
	Role         Role      `json:"role"`
	MemberCount  int       `json:"member_count"`
	ProjectCount int       `json:"project_count"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
}

type WorkspaceMember struct {
	ID          string    `json:"id"`
	WorkspaceID string    `json:"workspace_id"`
	UserID      string    `json:"user_id"`
	UserName    string    `json:"user_name"`
	UserEmail   string    `json:"user_email"`
	Role        Role      `json:"role"`
	CreatedAt   time.Time `json:"created_at"`
}

type WorkspaceInvite struct {
	ID          string    `json:"id"`
	WorkspaceID string    `json:"workspace_id"`
	InviterID   string    `json:"inviter_id"`
	InviterName string    `json:"inviter_name,omitempty"`
	Email       string    `json:"email"`
	Role        Role      `json:"role"`
	Token       string    `json:"token"`
	Status      string    `json:"status"`
	ExpiresAt   time.Time `json:"expires_at"`
	CreatedAt   time.Time `json:"created_at"`
}

type Store interface {
	EnsureDefaultWorkspace(ctx context.Context, userID, userName string) (Workspace, error)
	ListUserWorkspaces(ctx context.Context, userID string) ([]Workspace, error)
	GetWorkspace(ctx context.Context, workspaceID, userID string) (Workspace, error)
	CreateWorkspace(ctx context.Context, userID, name string) (Workspace, error)
	UpdateWorkspace(ctx context.Context, workspaceID, userID, name string) (Workspace, error)
	DeleteWorkspace(ctx context.Context, workspaceID, userID string) error
	ListMembers(ctx context.Context, workspaceID, userID string) ([]WorkspaceMember, error)
	InviteMember(ctx context.Context, workspaceID, inviterID, email string, role Role) (WorkspaceInvite, error)
	ListInvites(ctx context.Context, workspaceID, userID string) ([]WorkspaceInvite, error)
	RevokeInvite(ctx context.Context, workspaceID, actorID, inviteID string) error
	AcceptInvite(ctx context.Context, token, userID, userEmail string) (Workspace, error)
	UpdateMemberRole(ctx context.Context, workspaceID, actorID, targetUserID string, newRole Role) error
	RemoveMember(ctx context.Context, workspaceID, actorID, targetUserID string) error
	GetUserWorkspaceRole(ctx context.Context, workspaceID, userID string) (Role, error)
}

type PgStore struct {
	pool *pgxpool.Pool
}

var _ Store = (*PgStore)(nil)

func New(pool *pgxpool.Pool) *PgStore {
	return &PgStore{pool: pool}
}

var nonAlphanumericSlugPattern = regexp.MustCompile(`[^a-z0-9]+`)

func slugify(name string) string {
	s := strings.ToLower(strings.TrimSpace(name))
	s = nonAlphanumericSlugPattern.ReplaceAllString(s, "-")
	s = strings.Trim(s, "-")
	if s == "" {
		s = "ws"
	}
	if len(s) > 40 {
		s = s[:40]
	}
	return s
}

func generateRandomHex(byteCount int) string {
	b := make([]byte, byteCount)
	if _, err := rand.Read(b); err != nil {
		return fmt.Sprintf("%x", time.Now().UnixNano())
	}
	return hex.EncodeToString(b)
}

func (s *PgStore) EnsureDefaultWorkspace(ctx context.Context, userID, userName string) (Workspace, error) {
	// Probe if user already has a workspace
	wsList, err := s.ListUserWorkspaces(ctx, userID)
	if err == nil && len(wsList) > 0 {
		for _, w := range wsList {
			if w.IsDefault {
				return w, nil
			}
		}
		return wsList[0], nil
	}

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return Workspace{}, err
	}
	defer func() { _ = tx.Rollback(ctx) }()

	// Check/create user's organization
	var orgID string
	err = tx.QueryRow(ctx, `SELECT id FROM organizations WHERE owner_id = $1 LIMIT 1`, userID).Scan(&orgID)
	if errors.Is(err, pgx.ErrNoRows) {
		orgSlug := "org-" + generateRandomHex(6)
		orgName := strings.TrimSpace(userName)
		if orgName == "" {
			orgName = "Personal"
		}
		orgName += " Org"

		err = tx.QueryRow(ctx, `
			INSERT INTO organizations (owner_id, name, slug)
			VALUES ($1, $2, $3)
			RETURNING id
		`, userID, orgName, orgSlug).Scan(&orgID)
		if err != nil {
			return Workspace{}, fmt.Errorf("create organization: %w", err)
		}
	} else if err != nil {
		return Workspace{}, err
	}

	// Create default workspace
	var ws Workspace
	err = tx.QueryRow(ctx, `
		INSERT INTO workspaces (org_id, name, slug, is_default)
		VALUES ($1, 'Personal Workspace', 'default', true)
		ON CONFLICT (org_id, slug) DO UPDATE SET is_default = true
		RETURNING id, org_id, name, slug, is_default, created_at, updated_at
	`, orgID).Scan(
		&ws.ID, &ws.OrgID, &ws.Name, &ws.Slug, &ws.IsDefault, &ws.CreatedAt, &ws.UpdatedAt,
	)
	if err != nil {
		return Workspace{}, fmt.Errorf("create workspace: %w", err)
	}

	// Insert owner membership
	_, err = tx.Exec(ctx, `
		INSERT INTO workspace_members (workspace_id, user_id, role)
		VALUES ($1, $2, 'owner')
		ON CONFLICT (workspace_id, user_id) DO NOTHING
	`, ws.ID, userID)
	if err != nil {
		return Workspace{}, fmt.Errorf("add workspace owner: %w", err)
	}

	if err := tx.Commit(ctx); err != nil {
		return Workspace{}, err
	}

	ws.Role = RoleOwner
	ws.MemberCount = 1
	return ws, nil
}

func (s *PgStore) ListUserWorkspaces(ctx context.Context, userID string) ([]Workspace, error) {
	rows, err := s.pool.Query(ctx, `
		SELECT w.id, w.org_id, w.name, w.slug, w.is_default, wm.role,
		       (SELECT COUNT(*) FROM workspace_members WHERE workspace_id = w.id) AS member_count,
		       (SELECT COUNT(*) FROM projects WHERE workspace_id = w.id) AS project_count,
		       w.created_at, w.updated_at
		FROM workspaces w
		JOIN workspace_members wm ON wm.workspace_id = w.id AND wm.user_id = $1
		ORDER BY w.is_default DESC, w.name ASC
	`, userID)
	if err != nil {
		return nil, fmt.Errorf("list user workspaces: %w", err)
	}
	defer rows.Close()

	var result []Workspace
	for rows.Next() {
		var ws Workspace
		var roleStr string
		if err := rows.Scan(
			&ws.ID, &ws.OrgID, &ws.Name, &ws.Slug, &ws.IsDefault, &roleStr,
			&ws.MemberCount, &ws.ProjectCount, &ws.CreatedAt, &ws.UpdatedAt,
		); err != nil {
			return nil, fmt.Errorf("scan workspace: %w", err)
		}
		ws.Role = Role(roleStr)
		result = append(result, ws)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	if result == nil {
		result = []Workspace{}
	}
	return result, nil
}

func (s *PgStore) GetWorkspace(ctx context.Context, workspaceID, userID string) (Workspace, error) {
	var ws Workspace
	var roleStr string
	err := s.pool.QueryRow(ctx, `
		SELECT w.id, w.org_id, w.name, w.slug, w.is_default, wm.role,
		       (SELECT COUNT(*) FROM workspace_members WHERE workspace_id = w.id) AS member_count,
		       (SELECT COUNT(*) FROM projects WHERE workspace_id = w.id) AS project_count,
		       w.created_at, w.updated_at
		FROM workspaces w
		JOIN workspace_members wm ON wm.workspace_id = w.id AND wm.user_id = $2
		WHERE w.id = $1
	`, workspaceID, userID).Scan(
		&ws.ID, &ws.OrgID, &ws.Name, &ws.Slug, &ws.IsDefault, &roleStr,
		&ws.MemberCount, &ws.ProjectCount, &ws.CreatedAt, &ws.UpdatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return Workspace{}, ErrWorkspaceNotFound
	}
	if err != nil {
		return Workspace{}, fmt.Errorf("get workspace: %w", err)
	}
	ws.Role = Role(roleStr)
	return ws, nil
}

func (s *PgStore) CreateWorkspace(ctx context.Context, userID, name string) (Workspace, error) {
	name = strings.TrimSpace(name)
	if name == "" {
		name = "New Workspace"
	}

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return Workspace{}, err
	}
	defer func() { _ = tx.Rollback(ctx) }()

	// Find user's organization
	var orgID string
	err = tx.QueryRow(ctx, `SELECT id FROM organizations WHERE owner_id = $1 LIMIT 1`, userID).Scan(&orgID)
	if errors.Is(err, pgx.ErrNoRows) {
		// Create org
		orgSlug := "org-" + generateRandomHex(6)
		err = tx.QueryRow(ctx, `
			INSERT INTO organizations (owner_id, name, slug)
			VALUES ($1, $2, $3)
			RETURNING id
		`, userID, name+" Org", orgSlug).Scan(&orgID)
		if err != nil {
			return Workspace{}, fmt.Errorf("create organization: %w", err)
		}
	} else if err != nil {
		return Workspace{}, err
	}

	slug := slugify(name) + "-" + generateRandomHex(4)

	var ws Workspace
	err = tx.QueryRow(ctx, `
		INSERT INTO workspaces (org_id, name, slug, is_default)
		VALUES ($1, $2, $3, false)
		RETURNING id, org_id, name, slug, is_default, created_at, updated_at
	`, orgID, name, slug).Scan(
		&ws.ID, &ws.OrgID, &ws.Name, &ws.Slug, &ws.IsDefault, &ws.CreatedAt, &ws.UpdatedAt,
	)
	if err != nil {
		return Workspace{}, fmt.Errorf("insert workspace: %w", err)
	}

	// Add creator as owner
	_, err = tx.Exec(ctx, `
		INSERT INTO workspace_members (workspace_id, user_id, role)
		VALUES ($1, $2, 'owner')
	`, ws.ID, userID)
	if err != nil {
		return Workspace{}, fmt.Errorf("add owner: %w", err)
	}

	if err := tx.Commit(ctx); err != nil {
		return Workspace{}, err
	}

	ws.Role = RoleOwner
	ws.MemberCount = 1
	ws.ProjectCount = 0
	return ws, nil
}

func (s *PgStore) UpdateWorkspace(ctx context.Context, workspaceID, userID, name string) (Workspace, error) {
	name = strings.TrimSpace(name)
	if name == "" {
		return Workspace{}, errors.New("workspace name cannot be empty")
	}

	role, err := s.GetUserWorkspaceRole(ctx, workspaceID, userID)
	if err != nil {
		return Workspace{}, err
	}
	if !HasMinRole(role, RoleAdmin) {
		return Workspace{}, ErrForbidden
	}

	var ws Workspace
	err = s.pool.QueryRow(ctx, `
		UPDATE workspaces
		SET name = $1, updated_at = now()
		WHERE id = $2
		RETURNING id, org_id, name, slug, is_default, created_at, updated_at
	`, name, workspaceID).Scan(
		&ws.ID, &ws.OrgID, &ws.Name, &ws.Slug, &ws.IsDefault, &ws.CreatedAt, &ws.UpdatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return Workspace{}, ErrWorkspaceNotFound
	}
	if err != nil {
		return Workspace{}, fmt.Errorf("update workspace: %w", err)
	}
	ws.Role = role
	return ws, nil
}

func (s *PgStore) DeleteWorkspace(ctx context.Context, workspaceID, userID string) error {
	ws, err := s.GetWorkspace(ctx, workspaceID, userID)
	if err != nil {
		return err
	}
	if ws.Role != RoleOwner {
		return ErrForbidden
	}
	if ws.IsDefault {
		return ErrCannotDeleteDefault
	}

	tag, err := s.pool.Exec(ctx, `DELETE FROM workspaces WHERE id = $1`, workspaceID)
	if err != nil {
		return fmt.Errorf("delete workspace: %w", err)
	}
	if tag.RowsAffected() == 0 {
		return ErrWorkspaceNotFound
	}
	return nil
}

func (s *PgStore) ListMembers(ctx context.Context, workspaceID, userID string) ([]WorkspaceMember, error) {
	// Verify caller membership
	_, err := s.GetUserWorkspaceRole(ctx, workspaceID, userID)
	if err != nil {
		return nil, err
	}

	rows, err := s.pool.Query(ctx, `
		SELECT wm.id, wm.workspace_id, wm.user_id, COALESCE(NULLIF(u.full_name, ''), 'User') AS user_name, u.email, wm.role, wm.created_at
		FROM workspace_members wm
		JOIN users u ON u.id = wm.user_id
		WHERE wm.workspace_id = $1
		ORDER BY 
			CASE wm.role 
				WHEN 'owner' THEN 1 
				WHEN 'admin' THEN 2 
				WHEN 'member' THEN 3 
				WHEN 'viewer' THEN 4 
				ELSE 5 
			END,
			wm.created_at ASC
	`, workspaceID)
	if err != nil {
		return nil, fmt.Errorf("list members: %w", err)
	}
	defer rows.Close()

	var members []WorkspaceMember
	for rows.Next() {
		var m WorkspaceMember
		var roleStr string
		if err := rows.Scan(
			&m.ID, &m.WorkspaceID, &m.UserID, &m.UserName, &m.UserEmail, &roleStr, &m.CreatedAt,
		); err != nil {
			return nil, fmt.Errorf("scan member: %w", err)
		}
		m.Role = Role(roleStr)
		members = append(members, m)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	if members == nil {
		members = []WorkspaceMember{}
	}
	return members, nil
}

func (s *PgStore) InviteMember(ctx context.Context, workspaceID, inviterID, email string, role Role) (WorkspaceInvite, error) {
	email = strings.ToLower(strings.TrimSpace(email))
	if email == "" || !strings.Contains(email, "@") {
		return WorkspaceInvite{}, errors.New("invalid email address")
	}
	if !IsValidRole(role) || role == RoleOwner {
		return WorkspaceInvite{}, ErrInvalidRole
	}

	// Verify actor permission (admin or owner)
	actorRole, err := s.GetUserWorkspaceRole(ctx, workspaceID, inviterID)
	if err != nil {
		return WorkspaceInvite{}, err
	}
	if !HasMinRole(actorRole, RoleAdmin) {
		return WorkspaceInvite{}, ErrForbidden
	}

	// Check if already a member
	var exists bool
	err = s.pool.QueryRow(ctx, `
		SELECT EXISTS (
			SELECT 1 FROM workspace_members wm
			JOIN users u ON u.id = wm.user_id
			WHERE wm.workspace_id = $1 AND LOWER(u.email) = $2
		)
	`, workspaceID, email).Scan(&exists)
	if err != nil {
		return WorkspaceInvite{}, err
	}
	if exists {
		return WorkspaceInvite{}, ErrAlreadyMember
	}

	token := generateRandomHex(24)
	expiresAt := time.Now().Add(7 * 24 * time.Hour) // 7 days

	var inv WorkspaceInvite
	var roleStr string
	err = s.pool.QueryRow(ctx, `
		INSERT INTO workspace_invites (workspace_id, inviter_id, email, role, token, expires_at)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING id, workspace_id, inviter_id, email, role, token, status, expires_at, created_at
	`, workspaceID, inviterID, email, string(role), token, expiresAt).Scan(
		&inv.ID, &inv.WorkspaceID, &inv.InviterID, &inv.Email, &roleStr, &inv.Token, &inv.Status, &inv.ExpiresAt, &inv.CreatedAt,
	)
	if err != nil {
		return WorkspaceInvite{}, fmt.Errorf("create invite: %w", err)
	}
	inv.Role = Role(roleStr)
	return inv, nil
}

func (s *PgStore) ListInvites(ctx context.Context, workspaceID, userID string) ([]WorkspaceInvite, error) {
	actorRole, err := s.GetUserWorkspaceRole(ctx, workspaceID, userID)
	if err != nil {
		return nil, err
	}
	if !HasMinRole(actorRole, RoleAdmin) {
		return nil, ErrForbidden
	}

	rows, err := s.pool.Query(ctx, `
		SELECT wi.id, wi.workspace_id, wi.inviter_id, COALESCE(NULLIF(u.full_name, ''), 'Admin') AS inviter_name,
		       wi.email, wi.role, wi.token, wi.status, wi.expires_at, wi.created_at
		FROM workspace_invites wi
		LEFT JOIN users u ON u.id = wi.inviter_id
		WHERE wi.workspace_id = $1 AND wi.status = 'pending' AND wi.expires_at > now()
		ORDER BY wi.created_at DESC
	`, workspaceID)
	if err != nil {
		return nil, fmt.Errorf("list invites: %w", err)
	}
	defer rows.Close()

	var invites []WorkspaceInvite
	for rows.Next() {
		var inv WorkspaceInvite
		var roleStr string
		if err := rows.Scan(
			&inv.ID, &inv.WorkspaceID, &inv.InviterID, &inv.InviterName,
			&inv.Email, &roleStr, &inv.Token, &inv.Status, &inv.ExpiresAt, &inv.CreatedAt,
		); err != nil {
			return nil, fmt.Errorf("scan invite: %w", err)
		}
		inv.Role = Role(roleStr)
		invites = append(invites, inv)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	if invites == nil {
		invites = []WorkspaceInvite{}
	}
	return invites, nil
}

func (s *PgStore) RevokeInvite(ctx context.Context, workspaceID, actorID, inviteID string) error {
	actorRole, err := s.GetUserWorkspaceRole(ctx, workspaceID, actorID)
	if err != nil {
		return err
	}
	if !HasMinRole(actorRole, RoleAdmin) {
		return ErrForbidden
	}

	tag, err := s.pool.Exec(ctx, `
		UPDATE workspace_invites
		SET status = 'revoked'
		WHERE id = $1 AND workspace_id = $2 AND status = 'pending'
	`, inviteID, workspaceID)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return ErrInviteNotFound
	}
	return nil
}

func (s *PgStore) AcceptInvite(ctx context.Context, token, userID, userEmail string) (Workspace, error) {
	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return Workspace{}, err
	}
	defer func() { _ = tx.Rollback(ctx) }()

	var inv WorkspaceInvite
	var roleStr string
	err = tx.QueryRow(ctx, `
		SELECT id, workspace_id, inviter_id, email, role, token, status, expires_at, created_at
		FROM workspace_invites
		WHERE token = $1 AND status = 'pending' AND expires_at > now()
		FOR UPDATE
	`, token).Scan(
		&inv.ID, &inv.WorkspaceID, &inv.InviterID, &inv.Email, &roleStr, &inv.Token, &inv.Status, &inv.ExpiresAt, &inv.CreatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return Workspace{}, ErrInviteNotFound
	}
	if err != nil {
		return Workspace{}, fmt.Errorf("query invite: %w", err)
	}
	inv.Role = Role(roleStr)

	// Add member
	_, err = tx.Exec(ctx, `
		INSERT INTO workspace_members (workspace_id, user_id, role)
		VALUES ($1, $2, $3)
		ON CONFLICT (workspace_id, user_id) DO UPDATE SET role = EXCLUDED.role, updated_at = now()
	`, inv.WorkspaceID, userID, string(inv.Role))
	if err != nil {
		return Workspace{}, fmt.Errorf("insert member: %w", err)
	}

	// Update invite status
	_, err = tx.Exec(ctx, `
		UPDATE workspace_invites
		SET status = 'accepted'
		WHERE id = $1
	`, inv.ID)
	if err != nil {
		return Workspace{}, fmt.Errorf("update invite: %w", err)
	}

	// Fetch workspace info
	var ws Workspace
	err = tx.QueryRow(ctx, `
		SELECT w.id, w.org_id, w.name, w.slug, w.is_default,
		       (SELECT COUNT(*) FROM workspace_members WHERE workspace_id = w.id),
		       (SELECT COUNT(*) FROM projects WHERE workspace_id = w.id),
		       w.created_at, w.updated_at
		FROM workspaces w
		WHERE w.id = $1
	`, inv.WorkspaceID).Scan(
		&ws.ID, &ws.OrgID, &ws.Name, &ws.Slug, &ws.IsDefault,
		&ws.MemberCount, &ws.ProjectCount, &ws.CreatedAt, &ws.UpdatedAt,
	)
	if err != nil {
		return Workspace{}, err
	}
	ws.Role = inv.Role

	if err := tx.Commit(ctx); err != nil {
		return Workspace{}, err
	}
	return ws, nil
}

func (s *PgStore) UpdateMemberRole(ctx context.Context, workspaceID, actorID, targetUserID string, newRole Role) error {
	if !IsValidRole(newRole) {
		return ErrInvalidRole
	}

	actorRole, err := s.GetUserWorkspaceRole(ctx, workspaceID, actorID)
	if err != nil {
		return err
	}
	if !HasMinRole(actorRole, RoleAdmin) {
		return ErrForbidden
	}

	targetRole, err := s.GetUserWorkspaceRole(ctx, workspaceID, targetUserID)
	if err != nil {
		return err
	}

	// Only owner can assign or remove owner role
	if (newRole == RoleOwner || targetRole == RoleOwner) && actorRole != RoleOwner {
		return ErrForbidden
	}

	// If demoting an owner, verify there is at least one other owner
	if targetRole == RoleOwner && newRole != RoleOwner {
		var ownerCount int
		err = s.pool.QueryRow(ctx, `
			SELECT COUNT(*) FROM workspace_members
			WHERE workspace_id = $1 AND role = 'owner'
		`, workspaceID).Scan(&ownerCount)
		if err != nil {
			return err
		}
		if ownerCount <= 1 {
			return ErrCannotRemoveOwner
		}
	}

	tag, err := s.pool.Exec(ctx, `
		UPDATE workspace_members
		SET role = $1, updated_at = now()
		WHERE workspace_id = $2 AND user_id = $3
	`, string(newRole), workspaceID, targetUserID)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return errors.New("member not found")
	}
	return nil
}

func (s *PgStore) RemoveMember(ctx context.Context, workspaceID, actorID, targetUserID string) error {
	actorRole, err := s.GetUserWorkspaceRole(ctx, workspaceID, actorID)
	if err != nil {
		return err
	}

	targetRole, err := s.GetUserWorkspaceRole(ctx, workspaceID, targetUserID)
	if err != nil {
		return err
	}

	// Case 1: Member leaves on their own
	if actorID == targetUserID {
		if targetRole == RoleOwner {
			var ownerCount int
			err = s.pool.QueryRow(ctx, `
				SELECT COUNT(*) FROM workspace_members
				WHERE workspace_id = $1 AND role = 'owner'
			`, workspaceID).Scan(&ownerCount)
			if err != nil {
				return err
			}
			if ownerCount <= 1 {
				return ErrCannotRemoveOwner
			}
		}
	} else {
		// Case 2: Removing someone else requires admin/owner and cannot remove higher or equal role
		if !HasMinRole(actorRole, RoleAdmin) {
			return ErrForbidden
		}
		if targetRole == RoleOwner && actorRole != RoleOwner {
			return ErrForbidden
		}
		if targetRole == RoleAdmin && actorRole != RoleOwner {
			return ErrForbidden
		}
	}

	tag, err := s.pool.Exec(ctx, `
		DELETE FROM workspace_members
		WHERE workspace_id = $1 AND user_id = $2
	`, workspaceID, targetUserID)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return errors.New("member not found")
	}
	return nil
}

func (s *PgStore) GetUserWorkspaceRole(ctx context.Context, workspaceID, userID string) (Role, error) {
	var roleStr string
	err := s.pool.QueryRow(ctx, `
		SELECT role FROM workspace_members
		WHERE workspace_id = $1 AND user_id = $2
	`, workspaceID, userID).Scan(&roleStr)
	if errors.Is(err, pgx.ErrNoRows) {
		return "", ErrWorkspaceNotFound
	}
	if err != nil {
		return "", fmt.Errorf("get user workspace role: %w", err)
	}
	return Role(roleStr), nil
}

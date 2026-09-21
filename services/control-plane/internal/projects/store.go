package projects

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

var (
	ErrProjectNotFound = errors.New("projects: project not found")
	ErrUnauthorized    = errors.New("projects: unauthorized")
)

type Project struct {
	ID           string          `json:"id"`
	UserID       string          `json:"user_id"`
	WorkspaceID  string          `json:"workspace_id,omitempty"`
	CreatorName  string          `json:"creator_name,omitempty"`
	Name         string          `json:"name"`
	Description  string          `json:"description"`
	Status       string          `json:"status"`
	Entities     json.RawMessage `json:"entities"`
	FileCount    int             `json:"file_count"`
	CommitSHA    string          `json:"commit_sha"`
	CreditsSpent int64           `json:"credits_spent"`
	MessageCount int             `json:"message_count"`
	LastPrompt   string          `json:"last_prompt"`
	CreatedAt    time.Time       `json:"created_at"`
	UpdatedAt    time.Time       `json:"updated_at"`
	LastOpenedAt *time.Time      `json:"last_opened_at,omitempty"`
}

type Store interface {
	CreateProject(ctx context.Context, userID, name, description string) (Project, error)
	CreateProjectInWorkspace(ctx context.Context, userID, workspaceID, name, description string) (Project, error)
	ListProjects(ctx context.Context, userID, status string, limit int) ([]Project, error)
	ListWorkspaceProjects(ctx context.Context, userID, workspaceID, status string, limit int) ([]Project, error)
	GetProject(ctx context.Context, id, userID string) (Project, error)
	UpdateProject(ctx context.Context, id, userID string, name, description *string) (Project, error)
	UpdateProjectBuildResult(ctx context.Context, id, userID string, name, prompt, commitSHA string, entities json.RawMessage, fileCount int, messageDelta int) error
	DebitProjectCredits(ctx context.Context, userID, projectID string, requested int64, reason string) (charged int64, newBalance int64, err error)
	ArchiveProject(ctx context.Context, id, userID string) error
	DeleteProject(ctx context.Context, id, userID string) error
	TouchProjectOpened(ctx context.Context, id, userID string) error
	GetUserProjectRole(ctx context.Context, projectID, userID string) (string, error)
}

type PgStore struct {
	pool *pgxpool.Pool
}

var _ Store = (*PgStore)(nil)

func New(pool *pgxpool.Pool) *PgStore {
	return &PgStore{pool: pool}
}

func (s *PgStore) CreateProject(ctx context.Context, userID, name, description string) (Project, error) {
	return s.CreateProjectInWorkspace(ctx, userID, "", name, description)
}

func (s *PgStore) CreateProjectInWorkspace(ctx context.Context, userID, workspaceID, name, description string) (Project, error) {
	name = strings.TrimSpace(name)
	if name == "" {
		name = "Untitled project"
	}
	description = strings.TrimSpace(description)

	var wsID *string
	workspaceID = strings.TrimSpace(workspaceID)
	if workspaceID != "" {
		// Verify caller is member of specified workspace with at least member role
		var role string
		err := s.pool.QueryRow(ctx, `
			SELECT role FROM workspace_members
			WHERE workspace_id = $1 AND user_id = $2
		`, workspaceID, userID).Scan(&role)
		if errors.Is(err, pgx.ErrNoRows) {
			return Project{}, ErrUnauthorized
		}
		if err != nil {
			return Project{}, fmt.Errorf("projects: check workspace role: %w", err)
		}
		if role != "owner" && role != "admin" && role != "member" {
			return Project{}, errors.New("projects: viewers cannot create projects")
		}
		wsID = &workspaceID
	} else {
		// Resolve user's default workspace
		var defaultID string
		err := s.pool.QueryRow(ctx, `
			SELECT w.id FROM workspaces w
			JOIN workspace_members wm ON wm.workspace_id = w.id
			WHERE wm.user_id = $1 AND w.is_default = true
			LIMIT 1
		`, userID).Scan(&defaultID)
		if err == nil {
			wsID = &defaultID
		}
	}

	var p Project
	var entitiesBytes []byte
	var dbWsID *string
	err := s.pool.QueryRow(ctx, `
		INSERT INTO projects (user_id, workspace_id, name, description, entities)
		VALUES ($1, $2, $3, $4, '[]'::jsonb)
		RETURNING id, user_id, workspace_id, name, description, status, entities, file_count, commit_sha,
		          credits_spent, message_count, last_prompt, created_at, updated_at, last_opened_at
	`, userID, wsID, name, description).Scan(
		&p.ID, &p.UserID, &dbWsID, &p.Name, &p.Description, &p.Status, &entitiesBytes, &p.FileCount, &p.CommitSHA,
		&p.CreditsSpent, &p.MessageCount, &p.LastPrompt, &p.CreatedAt, &p.UpdatedAt, &p.LastOpenedAt,
	)
	if err != nil {
		return Project{}, fmt.Errorf("projects: create project: %w", err)
	}
	if dbWsID != nil {
		p.WorkspaceID = *dbWsID
	}
	p.Entities = entitiesBytes
	return p, nil
}

func (s *PgStore) ListProjects(ctx context.Context, userID, status string, limit int) ([]Project, error) {
	return s.ListWorkspaceProjects(ctx, userID, "", status, limit)
}

func (s *PgStore) ListWorkspaceProjects(ctx context.Context, userID, workspaceID, status string, limit int) ([]Project, error) {
	if limit <= 0 || limit > 100 {
		limit = 50
	}

	whereClause := `
		WHERE (
			p.user_id = $1
			OR (p.workspace_id IS NOT NULL AND EXISTS (
				SELECT 1 FROM workspace_members wm WHERE wm.workspace_id = p.workspace_id AND wm.user_id = $1
			))
		)
	`
	args := []any{userID, limit}

	workspaceID = strings.TrimSpace(workspaceID)
	if workspaceID != "" {
		whereClause = `
			WHERE p.workspace_id = $3 AND (
				p.user_id = $1
				OR EXISTS (
					SELECT 1 FROM workspace_members wm WHERE wm.workspace_id = $3 AND wm.user_id = $1
				)
			)
		`
		args = []any{userID, limit, workspaceID}
	}

	if status == "archived" {
		whereClause += " AND p.status = 'archived'"
	} else if status != "all" {
		whereClause += " AND p.status = 'active'"
	}

	query := fmt.Sprintf(`
		SELECT p.id, p.user_id, p.workspace_id, COALESCE(u.name, 'User'),
		       p.name, p.description, p.status, p.entities, p.file_count, p.commit_sha,
		       p.credits_spent, p.message_count, p.last_prompt, p.created_at, p.updated_at, p.last_opened_at
		FROM projects p
		LEFT JOIN users u ON u.id = p.user_id
		%s
		ORDER BY p.updated_at DESC
		LIMIT $2
	`, whereClause)

	rows, err := s.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("projects: list projects: %w", err)
	}
	defer rows.Close()

	var result []Project
	for rows.Next() {
		var p Project
		var entitiesBytes []byte
		var dbWsID *string
		var creatorName *string
		if err := rows.Scan(
			&p.ID, &p.UserID, &dbWsID, &creatorName, &p.Name, &p.Description, &p.Status, &entitiesBytes, &p.FileCount, &p.CommitSHA,
			&p.CreditsSpent, &p.MessageCount, &p.LastPrompt, &p.CreatedAt, &p.UpdatedAt, &p.LastOpenedAt,
		); err != nil {
			return nil, fmt.Errorf("projects: scan project: %w", err)
		}
		if dbWsID != nil {
			p.WorkspaceID = *dbWsID
		}
		if creatorName != nil {
			p.CreatorName = *creatorName
		}
		p.Entities = entitiesBytes
		result = append(result, p)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	if result == nil {
		result = []Project{}
	}
	return result, nil
}

func (s *PgStore) GetProject(ctx context.Context, id, userID string) (Project, error) {
	var p Project
	var entitiesBytes []byte
	var dbWsID *string
	var creatorName *string
	err := s.pool.QueryRow(ctx, `
		SELECT p.id, p.user_id, p.workspace_id, COALESCE(u.name, 'User'),
		       p.name, p.description, p.status, p.entities, p.file_count, p.commit_sha,
		       p.credits_spent, p.message_count, p.last_prompt, p.created_at, p.updated_at, p.last_opened_at
		FROM projects p
		LEFT JOIN users u ON u.id = p.user_id
		WHERE p.id = $1 AND (
			p.user_id = $2
			OR (p.workspace_id IS NOT NULL AND EXISTS (
				SELECT 1 FROM workspace_members wm WHERE wm.workspace_id = p.workspace_id AND wm.user_id = $2
			))
		)
	`, id, userID).Scan(
		&p.ID, &p.UserID, &dbWsID, &creatorName, &p.Name, &p.Description, &p.Status, &entitiesBytes, &p.FileCount, &p.CommitSHA,
		&p.CreditsSpent, &p.MessageCount, &p.LastPrompt, &p.CreatedAt, &p.UpdatedAt, &p.LastOpenedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return Project{}, ErrProjectNotFound
	}
	if err != nil {
		return Project{}, fmt.Errorf("projects: get project: %w", err)
	}
	if dbWsID != nil {
		p.WorkspaceID = *dbWsID
	}
	if creatorName != nil {
		p.CreatorName = *creatorName
	}
	p.Entities = entitiesBytes
	return p, nil
}

func (s *PgStore) UpdateProject(ctx context.Context, id, userID string, name, description *string) (Project, error) {
	current, err := s.GetProject(ctx, id, userID)
	if err != nil {
		return Project{}, err
	}

	newName := current.Name
	if name != nil && strings.TrimSpace(*name) != "" {
		newName = strings.TrimSpace(*name)
	}
	newDesc := current.Description
	if description != nil {
		newDesc = strings.TrimSpace(*description)
	}

	var p Project
	var entitiesBytes []byte
	var dbWsID *string
	err = s.pool.QueryRow(ctx, `
		UPDATE projects
		SET name = $1, description = $2, updated_at = now()
		WHERE id = $3 AND (
			user_id = $4
			OR (workspace_id IS NOT NULL AND EXISTS (
				SELECT 1 FROM workspace_members wm
				WHERE wm.workspace_id = projects.workspace_id AND wm.user_id = $4 AND wm.role IN ('owner', 'admin', 'member')
			))
		)
		RETURNING id, user_id, workspace_id, name, description, status, entities, file_count, commit_sha,
		          credits_spent, message_count, last_prompt, created_at, updated_at, last_opened_at
	`, newName, newDesc, id, userID).Scan(
		&p.ID, &p.UserID, &dbWsID, &p.Name, &p.Description, &p.Status, &entitiesBytes, &p.FileCount, &p.CommitSHA,
		&p.CreditsSpent, &p.MessageCount, &p.LastPrompt, &p.CreatedAt, &p.UpdatedAt, &p.LastOpenedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return Project{}, ErrProjectNotFound
	}
	if err != nil {
		return Project{}, fmt.Errorf("projects: update project: %w", err)
	}
	if dbWsID != nil {
		p.WorkspaceID = *dbWsID
	}
	p.CreatorName = current.CreatorName
	p.Entities = entitiesBytes
	return p, nil
}

func (s *PgStore) TouchProjectOpened(ctx context.Context, id, userID string) error {
	_, err := s.pool.Exec(ctx, `
		UPDATE projects
		SET last_opened_at = now()
		WHERE id = $1 AND (
			user_id = $2
			OR (workspace_id IS NOT NULL AND EXISTS (
				SELECT 1 FROM workspace_members wm WHERE wm.workspace_id = projects.workspace_id AND wm.user_id = $2
			))
		)
	`, id, userID)
	return err
}

func (s *PgStore) UpdateProjectBuildResult(
	ctx context.Context,
	id, userID string,
	name, prompt, commitSHA string,
	entities json.RawMessage,
	fileCount int,
	messageDelta int,
) error {
	if len(entities) == 0 {
		entities = json.RawMessage("[]")
	}

	tag, err := s.pool.Exec(ctx, `
		UPDATE projects
		SET name = CASE WHEN name = 'Untitled project' AND $1 != '' THEN $1 ELSE name END,
		    last_prompt = CASE WHEN $2 != '' THEN $2 ELSE last_prompt END,
		    commit_sha = CASE WHEN $3 != '' THEN $3 ELSE commit_sha END,
		    entities = $4,
		    file_count = $5,
		    message_count = message_count + $6,
		    updated_at = now(),
		    last_opened_at = now()
		WHERE id = $7 AND (
			user_id = $8
			OR (workspace_id IS NOT NULL AND EXISTS (
				SELECT 1 FROM workspace_members wm
				WHERE wm.workspace_id = projects.workspace_id AND wm.user_id = $8 AND wm.role IN ('owner', 'admin', 'member')
			))
		)
	`, strings.TrimSpace(name), prompt, commitSHA, entities, fileCount, messageDelta, id, userID)
	if err != nil {
		return fmt.Errorf("projects: update build result: %w", err)
	}
	if tag.RowsAffected() == 0 {
		return ErrProjectNotFound
	}
	return nil
}

func (s *PgStore) DebitProjectCredits(ctx context.Context, userID, projectID string, requested int64, reason string) (charged int64, newBalance int64, err error) {
	if requested < 0 {
		return 0, 0, fmt.Errorf("projects: requested credits must be >= 0, got %d", requested)
	}

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return 0, 0, err
	}
	defer func() { _ = tx.Rollback(ctx) }()

	var balance int64
	err = tx.QueryRow(ctx, `SELECT credit_balance FROM users WHERE id = $1 FOR UPDATE`, userID).Scan(&balance)
	if errors.Is(err, pgx.ErrNoRows) {
		return 0, 0, errors.New("user not found")
	}
	if err != nil {
		return 0, 0, err
	}

	charged = requested
	if charged > balance {
		charged = balance
	}
	if charged < 0 {
		charged = 0
	}
	newBalance = balance - charged

	if charged != 0 {
		if _, err = tx.Exec(ctx, `UPDATE users SET credit_balance = $2 WHERE id = $1`, userID, newBalance); err != nil {
			return 0, 0, err
		}
		if _, err = tx.Exec(ctx, `
			INSERT INTO credit_ledger (user_id, project_id, delta, reason, balance_after)
			VALUES ($1, $2, $3, $4, $5)
		`, userID, projectID, -charged, reason, newBalance); err != nil {
			return 0, 0, err
		}
		if _, err = tx.Exec(ctx, `
			UPDATE projects
			SET credits_spent = credits_spent + $2, updated_at = now()
			WHERE id = $1
		`, projectID, charged); err != nil {
			return 0, 0, err
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return 0, 0, err
	}
	return charged, newBalance, nil
}

func (s *PgStore) ArchiveProject(ctx context.Context, id, userID string) error {
	tag, err := s.pool.Exec(ctx, `
		UPDATE projects
		SET status = 'archived', updated_at = now()
		WHERE id = $1 AND (
			user_id = $2
			OR (workspace_id IS NOT NULL AND EXISTS (
				SELECT 1 FROM workspace_members wm
				WHERE wm.workspace_id = projects.workspace_id AND wm.user_id = $2 AND wm.role IN ('owner', 'admin')
			))
		)
	`, id, userID)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return ErrProjectNotFound
	}
	return nil
}

func (s *PgStore) DeleteProject(ctx context.Context, id, userID string) error {
	tag, err := s.pool.Exec(ctx, `
		DELETE FROM projects
		WHERE id = $1 AND (
			user_id = $2
			OR (workspace_id IS NOT NULL AND EXISTS (
				SELECT 1 FROM workspace_members wm
				WHERE wm.workspace_id = projects.workspace_id AND wm.user_id = $2 AND wm.role IN ('owner', 'admin')
			))
		)
	`, id, userID)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return ErrProjectNotFound
	}
	return nil
}

func (s *PgStore) GetUserProjectRole(ctx context.Context, projectID, userID string) (string, error) {
	var isCreator bool
	var dbWsID *string
	err := s.pool.QueryRow(ctx, `
		SELECT user_id = $2, workspace_id
		FROM projects
		WHERE id = $1
	`, projectID, userID).Scan(&isCreator, &dbWsID)
	if errors.Is(err, pgx.ErrNoRows) {
		return "", ErrProjectNotFound
	}
	if err != nil {
		return "", err
	}
	if isCreator {
		return "owner", nil
	}
	if dbWsID == nil || *dbWsID == "" {
		return "", ErrUnauthorized
	}

	var role string
	err = s.pool.QueryRow(ctx, `
		SELECT role FROM workspace_members
		WHERE workspace_id = $1 AND user_id = $2
	`, *dbWsID, userID).Scan(&role)
	if errors.Is(err, pgx.ErrNoRows) {
		return "", ErrUnauthorized
	}
	if err != nil {
		return "", err
	}
	return role, nil
}

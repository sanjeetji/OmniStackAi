package skills

import (
	"context"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
)

var (
	ErrSkillNotFound      = errors.New("skill not found")
	ErrProjectNotFound    = errors.New("project not found")
	ErrSkillAlreadyExists = errors.New("skill with this name already exists")
	ErrInvalidSkillName   = errors.New("invalid skill name: must be lower-kebab-case (a-z, 0-9, single hyphens)")
	ErrSkillBodyTooLarge  = errors.New("skill body exceeds maximum allowed size (8192 bytes)")
	ErrKnowledgeTooLarge  = errors.New("project knowledge exceeds maximum allowed size (16384 bytes)")
	ErrEmptySkillTitle    = errors.New("skill title cannot be empty")
)

var nameRegex = regexp.MustCompile(`^[a-z0-9]+(-[a-z0-9]+)*$`)

type Skill struct {
	ID           string    `json:"id"`
	UserID       string    `json:"user_id"`
	Name         string    `json:"name"`
	Title        string    `json:"title"`
	Description  string    `json:"description"`
	Body         string    `json:"body"`
	IsDefault    bool      `json:"is_default"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
	ProjectCount int       `json:"project_count,omitempty"`
}

type SkillPayload struct {
	Name string `json:"name"`
	Body string `json:"body"`
}

type ContextBlock struct {
	Knowledge string         `json:"knowledge"`
	Skills    []SkillPayload `json:"skills"`
}

type ProjectKnowledge struct {
	Knowledge string    `json:"knowledge"`
	UpdatedAt time.Time `json:"updated_at"`
}

type Store interface {
	ListSkills(ctx context.Context, userID string) ([]Skill, error)
	CreateSkill(ctx context.Context, userID, name, title, description, body string, isDefault bool) (*Skill, error)
	GetSkill(ctx context.Context, userID, skillID string) (*Skill, error)
	UpdateSkill(ctx context.Context, userID, skillID, title, description, body string, isDefault bool) (*Skill, error)
	DeleteSkill(ctx context.Context, userID, skillID string) error

	GetProjectKnowledge(ctx context.Context, userID, projectID string) (*ProjectKnowledge, error)
	UpdateProjectKnowledge(ctx context.Context, userID, projectID, knowledge string) (*ProjectKnowledge, error)

	ListProjectSkills(ctx context.Context, userID, projectID string) ([]Skill, error)
	AttachProjectSkill(ctx context.Context, userID, projectID, skillID string) error
	DetachProjectSkill(ctx context.Context, userID, projectID, skillID string) error

	ResolveContext(ctx context.Context, userID, projectID string, mentionSkillNames []string) (*ContextBlock, error)
}

type PgStore struct {
	pool *pgxpool.Pool
}

func NewPgStore(pool *pgxpool.Pool) *PgStore {
	return &PgStore{pool: pool}
}

func ValidateSkillName(name string) error {
	name = strings.TrimSpace(name)
	if !nameRegex.MatchString(name) {
		return ErrInvalidSkillName
	}
	return nil
}

func (s *PgStore) ListSkills(ctx context.Context, userID string) ([]Skill, error) {
	query := `
		SELECT s.id, s.user_id, s.name, s.title, s.description, s.body, s.is_default, s.created_at, s.updated_at,
		       COALESCE(COUNT(ps.project_id), 0) AS project_count
		FROM skills s
		LEFT JOIN project_skills ps ON s.id = ps.skill_id
		WHERE s.user_id = $1
		GROUP BY s.id
		ORDER BY s.name ASC
	`
	rows, err := s.pool.Query(ctx, query, userID)
	if err != nil {
		return nil, fmt.Errorf("list skills: %w", err)
	}
	defer rows.Close()

	var skills []Skill
	for rows.Next() {
		var sk Skill
		if err := rows.Scan(
			&sk.ID, &sk.UserID, &sk.Name, &sk.Title, &sk.Description,
			&sk.Body, &sk.IsDefault, &sk.CreatedAt, &sk.UpdatedAt, &sk.ProjectCount,
		); err != nil {
			return nil, fmt.Errorf("scan skill: %w", err)
		}
		skills = append(skills, sk)
	}
	if skills == nil {
		skills = []Skill{}
	}
	return skills, nil
}

func (s *PgStore) CreateSkill(ctx context.Context, userID, name, title, description, body string, isDefault bool) (*Skill, error) {
	name = strings.TrimSpace(strings.ToLower(name))
	title = strings.TrimSpace(title)
	description = strings.TrimSpace(description)
	body = strings.TrimSpace(body)

	if err := ValidateSkillName(name); err != nil {
		return nil, err
	}
	if title == "" {
		return nil, ErrEmptySkillTitle
	}
	if len(body) > 8192 {
		return nil, ErrSkillBodyTooLarge
	}

	query := `
		INSERT INTO skills (user_id, name, title, description, body, is_default)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING id, user_id, name, title, description, body, is_default, created_at, updated_at
	`
	var sk Skill
	err := s.pool.QueryRow(ctx, query, userID, name, title, description, body, isDefault).Scan(
		&sk.ID, &sk.UserID, &sk.Name, &sk.Title, &sk.Description,
		&sk.Body, &sk.IsDefault, &sk.CreatedAt, &sk.UpdatedAt,
	)
	if err != nil {
		var pgErr *pgconn.PgError
		if errors.As(err, &pgErr) && pgErr.Code == "23505" {
			return nil, ErrSkillAlreadyExists
		}
		return nil, fmt.Errorf("create skill: %w", err)
	}
	return &sk, nil
}

func (s *PgStore) GetSkill(ctx context.Context, userID, skillID string) (*Skill, error) {
	query := `
		SELECT s.id, s.user_id, s.name, s.title, s.description, s.body, s.is_default, s.created_at, s.updated_at,
		       COALESCE(COUNT(ps.project_id), 0) AS project_count
		FROM skills s
		LEFT JOIN project_skills ps ON s.id = ps.skill_id
		WHERE s.id = $1 AND s.user_id = $2
		GROUP BY s.id
	`
	var sk Skill
	err := s.pool.QueryRow(ctx, query, skillID, userID).Scan(
		&sk.ID, &sk.UserID, &sk.Name, &sk.Title, &sk.Description,
		&sk.Body, &sk.IsDefault, &sk.CreatedAt, &sk.UpdatedAt, &sk.ProjectCount,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrSkillNotFound
		}
		return nil, fmt.Errorf("get skill: %w", err)
	}
	return &sk, nil
}

func (s *PgStore) UpdateSkill(ctx context.Context, userID, skillID, title, description, body string, isDefault bool) (*Skill, error) {
	title = strings.TrimSpace(title)
	description = strings.TrimSpace(description)
	body = strings.TrimSpace(body)

	if title == "" {
		return nil, ErrEmptySkillTitle
	}
	if len(body) > 8192 {
		return nil, ErrSkillBodyTooLarge
	}

	query := `
		UPDATE skills
		SET title = $1, description = $2, body = $3, is_default = $4, updated_at = now()
		WHERE id = $5 AND user_id = $6
		RETURNING id, user_id, name, title, description, body, is_default, created_at, updated_at
	`
	var sk Skill
	err := s.pool.QueryRow(ctx, query, title, description, body, isDefault, skillID, userID).Scan(
		&sk.ID, &sk.UserID, &sk.Name, &sk.Title, &sk.Description,
		&sk.Body, &sk.IsDefault, &sk.CreatedAt, &sk.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrSkillNotFound
		}
		return nil, fmt.Errorf("update skill: %w", err)
	}
	return &sk, nil
}

func (s *PgStore) DeleteSkill(ctx context.Context, userID, skillID string) error {
	query := `DELETE FROM skills WHERE id = $1 AND user_id = $2`
	tag, err := s.pool.Exec(ctx, query, skillID, userID)
	if err != nil {
		return fmt.Errorf("delete skill: %w", err)
	}
	if tag.RowsAffected() == 0 {
		return ErrSkillNotFound
	}
	return nil
}

func (s *PgStore) GetProjectKnowledge(ctx context.Context, userID, projectID string) (*ProjectKnowledge, error) {
	query := `SELECT knowledge, updated_at FROM projects WHERE id = $1 AND user_id = $2`
	var pk ProjectKnowledge
	err := s.pool.QueryRow(ctx, query, projectID, userID).Scan(&pk.Knowledge, &pk.UpdatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrProjectNotFound
		}
		return nil, fmt.Errorf("get project knowledge: %w", err)
	}
	return &pk, nil
}

func (s *PgStore) UpdateProjectKnowledge(ctx context.Context, userID, projectID, knowledge string) (*ProjectKnowledge, error) {
	if len(knowledge) > 16384 {
		return nil, ErrKnowledgeTooLarge
	}

	query := `
		UPDATE projects
		SET knowledge = $1, updated_at = now()
		WHERE id = $2 AND user_id = $3
		RETURNING knowledge, updated_at
	`
	var pk ProjectKnowledge
	err := s.pool.QueryRow(ctx, query, knowledge, projectID, userID).Scan(&pk.Knowledge, &pk.UpdatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrProjectNotFound
		}
		return nil, fmt.Errorf("update project knowledge: %w", err)
	}
	return &pk, nil
}

func (s *PgStore) ListProjectSkills(ctx context.Context, userID, projectID string) ([]Skill, error) {
	// First verify project ownership
	var exists bool
	err := s.pool.QueryRow(ctx, `SELECT EXISTS(SELECT 1 FROM projects WHERE id = $1 AND user_id = $2)`, projectID, userID).Scan(&exists)
	if err != nil || !exists {
		return nil, ErrProjectNotFound
	}

	query := `
		SELECT s.id, s.user_id, s.name, s.title, s.description, s.body, s.is_default, s.created_at, s.updated_at
		FROM skills s
		JOIN project_skills ps ON s.id = ps.skill_id
		WHERE ps.project_id = $1 AND s.user_id = $2
		ORDER BY s.name ASC
	`
	rows, err := s.pool.Query(ctx, query, projectID, userID)
	if err != nil {
		return nil, fmt.Errorf("list project skills: %w", err)
	}
	defer rows.Close()

	var skills []Skill
	for rows.Next() {
		var sk Skill
		if err := rows.Scan(
			&sk.ID, &sk.UserID, &sk.Name, &sk.Title, &sk.Description,
			&sk.Body, &sk.IsDefault, &sk.CreatedAt, &sk.UpdatedAt,
		); err != nil {
			return nil, fmt.Errorf("scan project skill: %w", err)
		}
		skills = append(skills, sk)
	}
	if skills == nil {
		skills = []Skill{}
	}
	return skills, nil
}

func (s *PgStore) AttachProjectSkill(ctx context.Context, userID, projectID, skillID string) error {
	// Verify project belongs to user
	var exists bool
	err := s.pool.QueryRow(ctx, `SELECT EXISTS(SELECT 1 FROM projects WHERE id = $1 AND user_id = $2)`, projectID, userID).Scan(&exists)
	if err != nil || !exists {
		return ErrProjectNotFound
	}

	// Verify skill belongs to user
	err = s.pool.QueryRow(ctx, `SELECT EXISTS(SELECT 1 FROM skills WHERE id = $1 AND user_id = $2)`, skillID, userID).Scan(&exists)
	if err != nil || !exists {
		return ErrSkillNotFound
	}

	query := `INSERT INTO project_skills (project_id, skill_id) VALUES ($1, $2) ON CONFLICT DO NOTHING`
	_, err = s.pool.Exec(ctx, query, projectID, skillID)
	if err != nil {
		return fmt.Errorf("attach project skill: %w", err)
	}
	return nil
}

func (s *PgStore) DetachProjectSkill(ctx context.Context, userID, projectID, skillID string) error {
	var exists bool
	err := s.pool.QueryRow(ctx, `SELECT EXISTS(SELECT 1 FROM projects WHERE id = $1 AND user_id = $2)`, projectID, userID).Scan(&exists)
	if err != nil || !exists {
		return ErrProjectNotFound
	}

	query := `DELETE FROM project_skills WHERE project_id = $1 AND skill_id = $2`
	_, err = s.pool.Exec(ctx, query, projectID, skillID)
	if err != nil {
		return fmt.Errorf("detach project skill: %w", err)
	}
	return nil
}

func (s *PgStore) ResolveContext(ctx context.Context, userID, projectID string, mentionSkillNames []string) (*ContextBlock, error) {
	// 1. Fetch knowledge
	pk, err := s.GetProjectKnowledge(ctx, userID, projectID)
	if err != nil {
		return nil, err
	}

	// 2. Fetch all user skills to have their bodies and defaults
	allSkills, err := s.ListSkills(ctx, userID)
	if err != nil {
		return nil, err
	}
	skillsByName := make(map[string]Skill, len(allSkills))
	skillsByID := make(map[string]Skill, len(allSkills))
	var defaultSkills []Skill
	for _, sk := range allSkills {
		skillsByName[sk.Name] = sk
		skillsByID[sk.ID] = sk
		if sk.IsDefault {
			defaultSkills = append(defaultSkills, sk)
		}
	}

	// 3. Fetch attached skills
	attachedSkills, err := s.ListProjectSkills(ctx, userID, projectID)
	if err != nil {
		return nil, err
	}

	// 4. Assemble in strict priority order:
	//    - Explicit @mentions first
	//    - Project-attached skills second
	//    - User defaults third
	// Deduplicate preserving earliest appearance
	seen := make(map[string]bool)
	var resolved []SkillPayload

	// Mentions
	for _, rawName := range mentionSkillNames {
		cleanName := strings.TrimSpace(strings.ToLower(rawName))
		cleanName = strings.TrimPrefix(cleanName, "@")
		if cleanName == "" || seen[cleanName] {
			continue
		}
		if sk, ok := skillsByName[cleanName]; ok {
			seen[cleanName] = true
			resolved = append(resolved, SkillPayload{Name: sk.Name, Body: sk.Body})
		}
	}

	// Attached
	for _, sk := range attachedSkills {
		if !seen[sk.Name] {
			seen[sk.Name] = true
			resolved = append(resolved, SkillPayload{Name: sk.Name, Body: sk.Body})
		}
	}

	// Defaults
	for _, sk := range defaultSkills {
		if !seen[sk.Name] {
			seen[sk.Name] = true
			resolved = append(resolved, SkillPayload{Name: sk.Name, Body: sk.Body})
		}
	}

	if resolved == nil {
		resolved = []SkillPayload{}
	}

	return &ContextBlock{
		Knowledge: pk.Knowledge,
		Skills:    resolved,
	}, nil
}

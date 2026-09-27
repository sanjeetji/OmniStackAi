package connectors

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/integrations"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/secrets"
)

var (
	ErrNotFound = errors.New("connectors: not found")
)

type ProjectConnector struct {
	ID        string         `json:"id"`
	ProjectID string         `json:"project_id"`
	Provider  string         `json:"provider"`
	Config    map[string]any `json:"config"`
	Enabled   bool           `json:"enabled"`
	CreatedAt time.Time      `json:"created_at"`
}

type Store interface {
	ListProjectConnectors(ctx context.Context, projectID string) ([]ProjectConnector, error)
	GetProjectConnector(ctx context.Context, projectID, provider string) (ProjectConnector, error)
	SaveProjectConnector(ctx context.Context, projectID, provider string, config map[string]any, enabled bool) (ProjectConnector, error)
	DeleteProjectConnector(ctx context.Context, projectID, provider string) error
}

type PgStore struct {
	pool *pgxpool.Pool
}

func NewPgStore(pool *pgxpool.Pool) *PgStore {
	return &PgStore{pool: pool}
}

func (s *PgStore) ListProjectConnectors(ctx context.Context, projectID string) ([]ProjectConnector, error) {
	rows, err := s.pool.Query(ctx, `
		SELECT id, project_id, provider, config, enabled, created_at
		FROM project_connectors
		WHERE project_id = $1
		ORDER BY created_at ASC
	`, projectID)
	if err != nil {
		return nil, fmt.Errorf("connectors: list: %w", err)
	}
	defer rows.Close()

	var list []ProjectConnector
	for rows.Next() {
		var pc ProjectConnector
		var configBytes []byte
		if err := rows.Scan(&pc.ID, &pc.ProjectID, &pc.Provider, &configBytes, &pc.Enabled, &pc.CreatedAt); err != nil {
			return nil, fmt.Errorf("connectors: scan: %w", err)
		}
		if len(configBytes) > 0 {
			_ = json.Unmarshal(configBytes, &pc.Config)
		}
		if pc.Config == nil {
			pc.Config = make(map[string]any)
		}
		// Mask sensitive fields like api_key or password in list view
		masked := make(map[string]any)
		for k, v := range pc.Config {
			if (k == "api_key" || k == "password") && v != "" {
				masked[k] = "••••••••"
			} else {
				masked[k] = v
			}
		}
		pc.Config = masked
		list = append(list, pc)
	}
	return list, rows.Err()
}

func (s *PgStore) GetProjectConnector(ctx context.Context, projectID, provider string) (ProjectConnector, error) {
	var pc ProjectConnector
	var configBytes []byte
	err := s.pool.QueryRow(ctx, `
		SELECT id, project_id, provider, config, enabled, created_at
		FROM project_connectors
		WHERE project_id = $1 AND provider = $2
	`, projectID, provider).Scan(&pc.ID, &pc.ProjectID, &pc.Provider, &configBytes, &pc.Enabled, &pc.CreatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return ProjectConnector{}, ErrNotFound
		}
		return ProjectConnector{}, fmt.Errorf("connectors: get: %w", err)
	}
	if len(configBytes) > 0 {
		_ = json.Unmarshal(configBytes, &pc.Config)
	}
	if pc.Config == nil {
		pc.Config = make(map[string]any)
	}
	return pc, nil
}

func (s *PgStore) SaveProjectConnector(ctx context.Context, projectID, provider string, config map[string]any, enabled bool) (ProjectConnector, error) {
	configBytes, err := json.Marshal(config)
	if err != nil {
		return ProjectConnector{}, fmt.Errorf("connectors: marshal config: %w", err)
	}

	var pc ProjectConnector
	var resConfigBytes []byte
	err = s.pool.QueryRow(ctx, `
		INSERT INTO project_connectors (project_id, provider, config, enabled)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT (project_id, provider) DO UPDATE
		SET config = EXCLUDED.config,
		    enabled = EXCLUDED.enabled
		RETURNING id, project_id, provider, config, enabled, created_at
	`, projectID, provider, configBytes, enabled).Scan(
		&pc.ID, &pc.ProjectID, &pc.Provider, &resConfigBytes, &pc.Enabled, &pc.CreatedAt,
	)
	if err != nil {
		return ProjectConnector{}, fmt.Errorf("connectors: save: %w", err)
	}
	if len(resConfigBytes) > 0 {
		_ = json.Unmarshal(resConfigBytes, &pc.Config)
	}
	if pc.Config == nil {
		pc.Config = make(map[string]any)
	}
	return pc, nil
}

func (s *PgStore) DeleteProjectConnector(ctx context.Context, projectID, provider string) error {
	cmd, err := s.pool.Exec(ctx, `
		DELETE FROM project_connectors
		WHERE project_id = $1 AND provider = $2
	`, projectID, provider)
	if err != nil {
		return fmt.Errorf("connectors: delete: %w", err)
	}
	if cmd.RowsAffected() == 0 {
		return ErrNotFound
	}
	return nil
}

// SecretSetter is the part of the secrets store MoveCredentialsToSecrets needs.
type SecretSetter interface {
	SetSecret(ctx context.Context, projectID, userID, key, value, description string) (*secrets.SecretMetadata, error)
	IsAvailable() bool
}

// MoveCredentialsToSecrets moves credentials that connectors saved before PC-013 (in plain JSON
// settings) into the project's encrypted secrets, and removes them from the settings. It is safe
// to run on every start: once moved, nothing is left to move. It returns how many were moved.
func (s *PgStore) MoveCredentialsToSecrets(ctx context.Context, store SecretSetter) (int, error) {
	if store == nil || !store.IsAvailable() {
		return 0, nil
	}
	rows, err := s.pool.Query(ctx, `
		SELECT pc.project_id::text, p.user_id::text, pc.provider, pc.config
		FROM project_connectors pc JOIN projects p ON p.id = pc.project_id`)
	if err != nil {
		return 0, err
	}
	type row struct {
		projectID, userID, provider string
		config                      map[string]any
	}
	var todo []row
	for rows.Next() {
		var r row
		var raw []byte
		if err := rows.Scan(&r.projectID, &r.userID, &r.provider, &raw); err != nil {
			rows.Close()
			return 0, err
		}
		_ = json.Unmarshal(raw, &r.config)
		todo = append(todo, r)
	}
	rows.Close()
	moved := 0
	for _, r := range todo {
		env := integrations.EnvFields(r.provider)
		def, _ := GetDefinition(r.provider)
		changed := false
		for field, name := range env {
			value, ok := r.config[field]
			if !ok {
				continue
			}
			if v := strings.TrimSpace(fmt.Sprintf("%v", value)); v != "" && value != nil {
				if _, err := store.SetSecret(ctx, r.projectID, r.userID, name, v, "Set by the "+def.Name+" connector"); err != nil {
					return moved, err
				}
				moved++
			}
			delete(r.config, field)
			changed = true
		}
		if changed {
			raw, _ := json.Marshal(r.config)
			if _, err := s.pool.Exec(ctx, `UPDATE project_connectors SET config = $3 WHERE project_id = $1 AND provider = $2`,
				r.projectID, r.provider, raw); err != nil {
				return moved, err
			}
		}
	}
	return moved, nil
}

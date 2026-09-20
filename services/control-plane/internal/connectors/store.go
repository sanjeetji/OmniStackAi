package connectors

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
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

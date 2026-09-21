package templates

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ErrNotFromTemplate means the project was not started from a template.
var ErrNotFromTemplate = errors.New("templates: project was not started from a template")

// Provenance records the exact original a project's code was copied from.
type Provenance struct {
	Slug      string    `json:"slug"`
	Version   string    `json:"version"`
	Digest    string    `json:"digest"`
	CreatedAt time.Time `json:"created_at"`
}

// Store persists template provenance per project (table project_templates, migration 000016).
type Store interface {
	RecordProjectTemplate(ctx context.Context, projectID string, p Provenance) error
	GetProjectTemplate(ctx context.Context, projectID string) (Provenance, error)
}

type PgStore struct {
	pool *pgxpool.Pool
}

var _ Store = (*PgStore)(nil)

func New(pool *pgxpool.Pool) *PgStore {
	return &PgStore{pool: pool}
}

func (s *PgStore) RecordProjectTemplate(ctx context.Context, projectID string, p Provenance) error {
	_, err := s.pool.Exec(ctx, `
		INSERT INTO project_templates (project_id, template_slug, template_version, template_digest)
		VALUES ($1, $2, $3, $4)
	`, projectID, p.Slug, p.Version, p.Digest)
	if err != nil {
		return fmt.Errorf("templates: record provenance: %w", err)
	}
	return nil
}

func (s *PgStore) GetProjectTemplate(ctx context.Context, projectID string) (Provenance, error) {
	var p Provenance
	err := s.pool.QueryRow(ctx, `
		SELECT template_slug, template_version, template_digest, created_at
		FROM project_templates WHERE project_id = $1
	`, projectID).Scan(&p.Slug, &p.Version, &p.Digest, &p.CreatedAt)
	if errors.Is(err, pgx.ErrNoRows) {
		return Provenance{}, ErrNotFromTemplate
	}
	if err != nil {
		return Provenance{}, fmt.Errorf("templates: get provenance: %w", err)
	}
	return p, nil
}

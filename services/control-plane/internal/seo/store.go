package seo

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

var (
	// ErrProjectNotFound is returned when project does not exist or caller does not own it.
	ErrProjectNotFound = errors.New("project not found")
	// ErrPageNotFound is returned when page SEO entry does not exist.
	ErrPageNotFound = errors.New("page seo not found")
)

// ProjectSEO represents site-level SEO defaults.
type ProjectSEO struct {
	ProjectID     string    `json:"project_id"`
	SiteName      string    `json:"site_name"`
	DefaultTitle  string    `json:"default_title"`
	Description   string    `json:"description"`
	CanonicalHost string    `json:"canonical_host"`
	Discourage    bool      `json:"discourage"`
	UpdatedAt     time.Time `json:"updated_at"`
}

// PageSEO represents per-page SEO metadata and indexing flags.
type PageSEO struct {
	ID          string    `json:"id,omitempty"`
	ProjectID   string    `json:"project_id"`
	Route       string    `json:"route"`
	Title       string    `json:"title"`
	Description string    `json:"description"`
	Noindex     bool      `json:"noindex"`
	UpdatedAt   time.Time `json:"updated_at"`
}

// Store defines operations for project SEO metadata.
type Store interface {
	GetProjectSEO(ctx context.Context, projectID, userID string) (*ProjectSEO, error)
	SetProjectSEO(ctx context.Context, projectID, userID string, seo *ProjectSEO) (*ProjectSEO, error)
	GetProjectPageSEOs(ctx context.Context, projectID, userID string) ([]PageSEO, error)
	GetProjectPageSEO(ctx context.Context, projectID, userID, route string) (*PageSEO, error)
	SetProjectPageSEO(ctx context.Context, projectID, userID string, page *PageSEO) (*PageSEO, error)
	DeleteProjectPageSEO(ctx context.Context, projectID, userID, route string) error
}

// PgStore implements Store using PostgreSQL.
type PgStore struct {
	pool *pgxpool.Pool
}

// NewPgStore initializes a PgStore.
func NewPgStore(pool *pgxpool.Pool) *PgStore {
	return &PgStore{pool: pool}
}

func (s *PgStore) checkOwnership(ctx context.Context, projectID, userID string) error {
	var count int
	err := s.pool.QueryRow(ctx, "SELECT count(*) FROM projects WHERE id = $1 AND user_id = $2", projectID, userID).Scan(&count)
	if err != nil {
		return fmt.Errorf("check ownership: %w", err)
	}
	if count == 0 {
		return ErrProjectNotFound
	}
	return nil
}

// GetProjectSEO returns the site-level SEO defaults for a project.
func (s *PgStore) GetProjectSEO(ctx context.Context, projectID, userID string) (*ProjectSEO, error) {
	if err := s.checkOwnership(ctx, projectID, userID); err != nil {
		return nil, err
	}

	var seo ProjectSEO
	err := s.pool.QueryRow(ctx, `
		SELECT project_id, site_name, default_title, description, canonical_host, discourage, updated_at
		FROM project_seo
		WHERE project_id = $1
	`, projectID).Scan(
		&seo.ProjectID,
		&seo.SiteName,
		&seo.DefaultTitle,
		&seo.Description,
		&seo.CanonicalHost,
		&seo.Discourage,
		&seo.UpdatedAt,
	)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			// Return default empty SEO record if not yet configured
			var projectName string
			_ = s.pool.QueryRow(ctx, "SELECT name FROM projects WHERE id = $1", projectID).Scan(&projectName)
			return &ProjectSEO{
				ProjectID:    projectID,
				SiteName:     projectName,
				DefaultTitle: projectName,
				UpdatedAt:    time.Now(),
			}, nil
		}
		return nil, fmt.Errorf("get project seo: %w", err)
	}

	return &seo, nil
}

// SetProjectSEO upserts site-level SEO defaults.
func (s *PgStore) SetProjectSEO(ctx context.Context, projectID, userID string, seo *ProjectSEO) (*ProjectSEO, error) {
	if err := s.checkOwnership(ctx, projectID, userID); err != nil {
		return nil, err
	}

	now := time.Now()
	var result ProjectSEO
	err := s.pool.QueryRow(ctx, `
		INSERT INTO project_seo (project_id, site_name, default_title, description, canonical_host, discourage, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (project_id) DO UPDATE SET
			site_name = EXCLUDED.site_name,
			default_title = EXCLUDED.default_title,
			description = EXCLUDED.description,
			canonical_host = EXCLUDED.canonical_host,
			discourage = EXCLUDED.discourage,
			updated_at = EXCLUDED.updated_at
		RETURNING project_id, site_name, default_title, description, canonical_host, discourage, updated_at
	`, projectID, seo.SiteName, seo.DefaultTitle, seo.Description, seo.CanonicalHost, seo.Discourage, now).Scan(
		&result.ProjectID,
		&result.SiteName,
		&result.DefaultTitle,
		&result.Description,
		&result.CanonicalHost,
		&result.Discourage,
		&result.UpdatedAt,
	)

	if err != nil {
		return nil, fmt.Errorf("set project seo: %w", err)
	}
	return &result, nil
}

// GetProjectPageSEOs returns all per-page SEO records for a project.
func (s *PgStore) GetProjectPageSEOs(ctx context.Context, projectID, userID string) ([]PageSEO, error) {
	if err := s.checkOwnership(ctx, projectID, userID); err != nil {
		return nil, err
	}

	rows, err := s.pool.Query(ctx, `
		SELECT id, project_id, route, title, description, noindex, updated_at
		FROM project_page_seo
		WHERE project_id = $1
		ORDER BY route ASC
	`, projectID)
	if err != nil {
		return nil, fmt.Errorf("list page seo: %w", err)
	}
	defer rows.Close()

	pages := make([]PageSEO, 0)
	for rows.Next() {
		var p PageSEO
		if err := rows.Scan(&p.ID, &p.ProjectID, &p.Route, &p.Title, &p.Description, &p.Noindex, &p.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan page seo: %w", err)
		}
		pages = append(pages, p)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate page seo: %w", err)
	}
	return pages, nil
}

// GetProjectPageSEO returns the SEO record for a specific route.
func (s *PgStore) GetProjectPageSEO(ctx context.Context, projectID, userID, route string) (*PageSEO, error) {
	if err := s.checkOwnership(ctx, projectID, userID); err != nil {
		return nil, err
	}

	var p PageSEO
	err := s.pool.QueryRow(ctx, `
		SELECT id, project_id, route, title, description, noindex, updated_at
		FROM project_page_seo
		WHERE project_id = $1 AND route = $2
	`, projectID, route).Scan(
		&p.ID,
		&p.ProjectID,
		&p.Route,
		&p.Title,
		&p.Description,
		&p.Noindex,
		&p.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrPageNotFound
		}
		return nil, fmt.Errorf("get page seo: %w", err)
	}
	return &p, nil
}

// SetProjectPageSEO upserts per-page SEO metadata.
func (s *PgStore) SetProjectPageSEO(ctx context.Context, projectID, userID string, page *PageSEO) (*PageSEO, error) {
	if err := s.checkOwnership(ctx, projectID, userID); err != nil {
		return nil, err
	}

	now := time.Now()
	var result PageSEO
	err := s.pool.QueryRow(ctx, `
		INSERT INTO project_page_seo (project_id, route, title, description, noindex, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6)
		ON CONFLICT (project_id, route) DO UPDATE SET
			title = EXCLUDED.title,
			description = EXCLUDED.description,
			noindex = EXCLUDED.noindex,
			updated_at = EXCLUDED.updated_at
		RETURNING id, project_id, route, title, description, noindex, updated_at
	`, projectID, page.Route, page.Title, page.Description, page.Noindex, now).Scan(
		&result.ID,
		&result.ProjectID,
		&result.Route,
		&result.Title,
		&result.Description,
		&result.Noindex,
		&result.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("set page seo: %w", err)
	}
	return &result, nil
}

// DeleteProjectPageSEO removes per-page SEO metadata.
func (s *PgStore) DeleteProjectPageSEO(ctx context.Context, projectID, userID, route string) error {
	if err := s.checkOwnership(ctx, projectID, userID); err != nil {
		return err
	}

	_, err := s.pool.Exec(ctx, `
		DELETE FROM project_page_seo
		WHERE project_id = $1 AND route = $2
	`, projectID, route)
	if err != nil {
		return fmt.Errorf("delete page seo: %w", err)
	}
	return nil
}

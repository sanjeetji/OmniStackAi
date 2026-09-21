package analytics

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

var (
	// ErrProjectNotFound is returned when the project does not exist or the user
	// does not own it.
	ErrProjectNotFound = errors.New("analytics: project not found or unauthorized")

	// ErrInvalidProvider is returned when an unsupported analytics provider is
	// supplied.
	ErrInvalidProvider = errors.New("analytics: unsupported provider; must be 'ga4'")

	// ErrInvalidPropertyID is returned when the property ID fails basic sanity.
	ErrInvalidPropertyID = errors.New("analytics: invalid property_id; must be a non-empty numeric string like '123456789'")
)

// Config represents the persisted analytics configuration for one project.
type Config struct {
	Provider   string `json:"provider"`    // "" | "ga4"
	PropertyID string `json:"property_id"` // GA4 Measurement Property ID (numeric string)
}

// Store defines the persistence operations for project analytics configuration.
type Store interface {
	GetAnalytics(ctx context.Context, projectID, userID string) (Config, error)
	SetAnalytics(ctx context.Context, projectID, userID string, cfg Config) error
	ClearAnalytics(ctx context.Context, projectID, userID string) error
}

// PgStore implements Store backed by PostgreSQL.
type PgStore struct {
	pool *pgxpool.Pool
}

// NewPgStore initialises a PgStore with the given connection pool.
func NewPgStore(pool *pgxpool.Pool) *PgStore {
	return &PgStore{pool: pool}
}

// GetAnalytics retrieves the analytics configuration for the given project.
func (s *PgStore) GetAnalytics(ctx context.Context, projectID, userID string) (Config, error) {
	var cfg Config
	err := s.pool.QueryRow(ctx, `
		SELECT analytics_provider, analytics_property_id
		FROM projects
		WHERE id = $1 AND user_id = $2
	`, projectID, userID).Scan(&cfg.Provider, &cfg.PropertyID)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return Config{}, ErrProjectNotFound
		}
		return Config{}, fmt.Errorf("analytics: get: %w", err)
	}
	return cfg, nil
}

// SetAnalytics persists analytics provider and property ID for the given project.
func (s *PgStore) SetAnalytics(ctx context.Context, projectID, userID string, cfg Config) error {
	provider := strings.ToLower(strings.TrimSpace(cfg.Provider))
	if provider != "ga4" {
		return ErrInvalidProvider
	}

	propertyID := strings.TrimSpace(cfg.PropertyID)
	if propertyID == "" {
		return ErrInvalidPropertyID
	}
	// Property ID must be numeric (GA4 Measurement Property IDs are all digits).
	for _, r := range propertyID {
		if r < '0' || r > '9' {
			return ErrInvalidPropertyID
		}
	}

	res, err := s.pool.Exec(ctx, `
		UPDATE projects
		SET analytics_provider    = $1,
		    analytics_property_id = $2,
		    updated_at            = now()
		WHERE id = $3 AND user_id = $4
	`, provider, propertyID, projectID, userID)
	if err != nil {
		return fmt.Errorf("analytics: set: %w", err)
	}
	if res.RowsAffected() == 0 {
		return ErrProjectNotFound
	}
	return nil
}

// ClearAnalytics removes the analytics configuration from the given project.
func (s *PgStore) ClearAnalytics(ctx context.Context, projectID, userID string) error {
	res, err := s.pool.Exec(ctx, `
		UPDATE projects
		SET analytics_provider    = '',
		    analytics_property_id = '',
		    updated_at            = now()
		WHERE id = $1 AND user_id = $2
	`, projectID, userID)
	if err != nil {
		return fmt.Errorf("analytics: clear: %w", err)
	}
	if res.RowsAffected() == 0 {
		return ErrProjectNotFound
	}
	return nil
}

package domains

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

var (
	ErrNotFound      = errors.New("domains: not found")
	ErrAlreadyExists = errors.New("domains: hostname already registered")
)

type Domain struct {
	ID            string     `json:"id"`
	ProjectID     string     `json:"project_id"`
	Hostname      string     `json:"hostname"`
	Provider      string     `json:"provider"`
	RecordType    string     `json:"record_type"`
	RecordName    string     `json:"record_name"`
	RecordValue   string     `json:"record_value"`
	Status        string     `json:"status"`
	TLSStatus     string     `json:"tls_status"`
	IsPrimary     bool       `json:"is_primary"`
	LastCheckedAt *time.Time `json:"last_checked_at,omitempty"`
	VerifiedAt    *time.Time `json:"verified_at,omitempty"`
	Error         string     `json:"error"`
	CreatedAt     time.Time  `json:"created_at"`
}

type Store interface {
	ListProjectDomains(ctx context.Context, projectID string) ([]Domain, error)
	GetDomain(ctx context.Context, domainID string) (Domain, error)
	GetDomainByHostname(ctx context.Context, hostname string) (Domain, error)
	CreateDomain(ctx context.Context, d Domain) (Domain, error)
	UpdateDomainStatus(ctx context.Context, id, status, tlsStatus, errorMsg string, verifiedAt *time.Time) error
	SetPrimaryDomain(ctx context.Context, projectID, domainID string) error
	DeleteDomain(ctx context.Context, domainID string) error
}

type PgStore struct {
	pool *pgxpool.Pool
}

func NewPgStore(pool *pgxpool.Pool) *PgStore {
	return &PgStore{pool: pool}
}

func (s *PgStore) ListProjectDomains(ctx context.Context, projectID string) ([]Domain, error) {
	rows, err := s.pool.Query(ctx, `
		SELECT id, project_id, hostname, provider, record_type, record_name, record_value,
		       status, tls_status, is_primary, last_checked_at, verified_at, error, created_at
		FROM project_domains
		WHERE project_id = $1
		ORDER BY is_primary DESC, created_at ASC
	`, projectID)
	if err != nil {
		return nil, fmt.Errorf("domains: list: %w", err)
	}
	defer rows.Close()

	var domains []Domain
	for rows.Next() {
		var d Domain
		if err := rows.Scan(
			&d.ID, &d.ProjectID, &d.Hostname, &d.Provider, &d.RecordType, &d.RecordName, &d.RecordValue,
			&d.Status, &d.TLSStatus, &d.IsPrimary, &d.LastCheckedAt, &d.VerifiedAt, &d.Error, &d.CreatedAt,
		); err != nil {
			return nil, fmt.Errorf("domains: scan: %w", err)
		}
		domains = append(domains, d)
	}
	return domains, rows.Err()
}

func (s *PgStore) GetDomain(ctx context.Context, domainID string) (Domain, error) {
	var d Domain
	err := s.pool.QueryRow(ctx, `
		SELECT id, project_id, hostname, provider, record_type, record_name, record_value,
		       status, tls_status, is_primary, last_checked_at, verified_at, error, created_at
		FROM project_domains
		WHERE id = $1
	`, domainID).Scan(
		&d.ID, &d.ProjectID, &d.Hostname, &d.Provider, &d.RecordType, &d.RecordName, &d.RecordValue,
		&d.Status, &d.TLSStatus, &d.IsPrimary, &d.LastCheckedAt, &d.VerifiedAt, &d.Error, &d.CreatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return Domain{}, ErrNotFound
		}
		return Domain{}, fmt.Errorf("domains: get: %w", err)
	}
	return d, nil
}

func (s *PgStore) GetDomainByHostname(ctx context.Context, hostname string) (Domain, error) {
	var d Domain
	err := s.pool.QueryRow(ctx, `
		SELECT id, project_id, hostname, provider, record_type, record_name, record_value,
		       status, tls_status, is_primary, last_checked_at, verified_at, error, created_at
		FROM project_domains
		WHERE hostname = $1
	`, hostname).Scan(
		&d.ID, &d.ProjectID, &d.Hostname, &d.Provider, &d.RecordType, &d.RecordName, &d.RecordValue,
		&d.Status, &d.TLSStatus, &d.IsPrimary, &d.LastCheckedAt, &d.VerifiedAt, &d.Error, &d.CreatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return Domain{}, ErrNotFound
		}
		return Domain{}, fmt.Errorf("domains: get by hostname: %w", err)
	}
	return d, nil
}

func (s *PgStore) CreateDomain(ctx context.Context, d Domain) (Domain, error) {
	// Check if this is the first domain for the project to make it primary
	var count int
	_ = s.pool.QueryRow(ctx, `SELECT count(*) FROM project_domains WHERE project_id = $1`, d.ProjectID).Scan(&count)
	isPrimary := count == 0 || d.IsPrimary

	var created Domain
	err := s.pool.QueryRow(ctx, `
		INSERT INTO project_domains (
			project_id, hostname, provider, record_type, record_name, record_value,
			status, tls_status, is_primary, error
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
		RETURNING id, project_id, hostname, provider, record_type, record_name, record_value,
		          status, tls_status, is_primary, last_checked_at, verified_at, error, created_at
	`, d.ProjectID, d.Hostname, d.Provider, d.RecordType, d.RecordName, d.RecordValue,
		d.Status, d.TLSStatus, isPrimary, d.Error).Scan(
		&created.ID, &created.ProjectID, &created.Hostname, &created.Provider, &created.RecordType, &created.RecordName, &created.RecordValue,
		&created.Status, &created.TLSStatus, &created.IsPrimary, &created.LastCheckedAt, &created.VerifiedAt, &created.Error, &created.CreatedAt,
	)
	if err != nil {
		return Domain{}, fmt.Errorf("domains: create: %w", err)
	}
	return created, nil
}

func (s *PgStore) UpdateDomainStatus(ctx context.Context, id, status, tlsStatus, errorMsg string, verifiedAt *time.Time) error {
	now := time.Now().UTC()
	_, err := s.pool.Exec(ctx, `
		UPDATE project_domains
		SET status = $2,
		    tls_status = $3,
		    error = $4,
		    last_checked_at = $5,
		    verified_at = COALESCE($6, verified_at)
		WHERE id = $1
	`, id, status, tlsStatus, errorMsg, now, verifiedAt)
	if err != nil {
		return fmt.Errorf("domains: update status: %w", err)
	}
	return nil
}

func (s *PgStore) SetPrimaryDomain(ctx context.Context, projectID, domainID string) error {
	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback(ctx) }()

	// Unset all primary for this project
	if _, err := tx.Exec(ctx, `UPDATE project_domains SET is_primary = FALSE WHERE project_id = $1`, projectID); err != nil {
		return err
	}

	// Set this domain as primary
	cmd, err := tx.Exec(ctx, `UPDATE project_domains SET is_primary = TRUE WHERE id = $1 AND project_id = $2`, domainID, projectID)
	if err != nil {
		return err
	}
	if cmd.RowsAffected() == 0 {
		return ErrNotFound
	}

	return tx.Commit(ctx)
}

func (s *PgStore) DeleteDomain(ctx context.Context, domainID string) error {
	cmd, err := s.pool.Exec(ctx, `DELETE FROM project_domains WHERE id = $1`, domainID)
	if err != nil {
		return fmt.Errorf("domains: delete: %w", err)
	}
	if cmd.RowsAffected() == 0 {
		return ErrNotFound
	}
	return nil
}

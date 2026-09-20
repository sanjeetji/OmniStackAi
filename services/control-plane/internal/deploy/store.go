package deploy

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/crypto"
)

var (
	ErrKeyNotConfigured = errors.New("deploy: encryption key is not configured or invalid")
	ErrNotFound         = errors.New("deploy: not found")
	ErrInvalidProvider  = errors.New("deploy: invalid provider, must be 'vercel' or 'netlify'")
	ErrTokenEmpty       = errors.New("deploy: token cannot be empty")
)

type Connection struct {
	ID           string    `json:"id"`
	UserID       string    `json:"user_id"`
	Provider     string    `json:"provider"`
	AccountLabel string    `json:"account_label"`
	CreatedAt    time.Time `json:"created_at"`
}

type Deployment struct {
	ID         string     `json:"id"`
	ProjectID  string     `json:"project_id"`
	Provider   string     `json:"provider"`
	ExternalID string     `json:"external_id"`
	CommitSHA  string     `json:"commit_sha"`
	Status     string     `json:"status"` // 'queued', 'building', 'ready', 'error', 'cancelled'
	URL        string     `json:"url"`
	Error      string     `json:"error"`
	CreatedAt  time.Time  `json:"created_at"`
	FinishedAt *time.Time `json:"finished_at,omitempty"`
}

type Store interface {
	GetConnection(ctx context.Context, userID, provider string) (*Connection, string, error)
	GetConnectionStatus(ctx context.Context, userID, provider string) (*Connection, error)
	SetConnection(ctx context.Context, userID, provider, token, accountLabel string) (*Connection, error)
	DeleteConnection(ctx context.Context, userID, provider string) error

	CreateDeployment(ctx context.Context, d *Deployment) (*Deployment, error)
	UpdateDeployment(ctx context.Context, id, status, url, errorMsg string, finishedAt *time.Time) error
	GetDeployment(ctx context.Context, id string) (*Deployment, error)
	GetLatestDeployment(ctx context.Context, projectID string) (*Deployment, error)
	ListDeployments(ctx context.Context, projectID string, limit int) ([]Deployment, error)

	UpdateProjectDeployMeta(ctx context.Context, projectID, provider, externalID, liveURL string) error
	GetProjectDeployMeta(ctx context.Context, projectID string) (provider, externalID, liveURL string, err error)
}

type PgStore struct {
	pool        *pgxpool.Pool
	key         []byte
	keyPrevious []byte
}

func NewPgStore(pool *pgxpool.Pool, key, keyPrevious []byte) *PgStore {
	return &PgStore{
		pool:        pool,
		key:         key,
		keyPrevious: keyPrevious,
	}
}

func (s *PgStore) aad(userID, provider string) []byte {
	return []byte(fmt.Sprintf("%s:%s", userID, provider))
}

func (s *PgStore) GetConnection(ctx context.Context, userID, provider string) (*Connection, string, error) {
	if len(s.key) != 32 {
		return nil, "", ErrKeyNotConfigured
	}
	provider = strings.ToLower(strings.TrimSpace(provider))
	if provider != "vercel" && provider != "netlify" {
		return nil, "", ErrInvalidProvider
	}

	query := `
		SELECT id, user_id, provider, token_ciphertext, account_label, created_at
		FROM deploy_connections
		WHERE user_id = $1 AND provider = $2
	`
	var (
		conn       Connection
		ciphertext []byte
	)
	err := s.pool.QueryRow(ctx, query, userID, provider).Scan(
		&conn.ID,
		&conn.UserID,
		&conn.Provider,
		&ciphertext,
		&conn.AccountLabel,
		&conn.CreatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, "", ErrNotFound
		}
		return nil, "", fmt.Errorf("deploy: get connection: %w", err)
	}

	aad := s.aad(userID, provider)
	plaintext, err := crypto.Decrypt(s.key, ciphertext, aad)
	if err != nil && len(s.keyPrevious) == 32 {
		plaintextPrev, errPrev := crypto.Decrypt(s.keyPrevious, ciphertext, aad)
		if errPrev == nil {
			plaintext = plaintextPrev
			if newCiphertext, encErr := crypto.Encrypt(s.key, plaintext, aad); encErr == nil {
				_, _ = s.pool.Exec(ctx, `UPDATE deploy_connections SET token_ciphertext = $1 WHERE id = $2`, newCiphertext, conn.ID)
			}
		}
	}
	if len(plaintext) == 0 {
		return nil, "", fmt.Errorf("deploy: decrypt token: %w", err)
	}

	return &conn, string(plaintext), nil
}

func (s *PgStore) GetConnectionStatus(ctx context.Context, userID, provider string) (*Connection, error) {
	provider = strings.ToLower(strings.TrimSpace(provider))
	if provider != "vercel" && provider != "netlify" {
		return nil, ErrInvalidProvider
	}

	query := `
		SELECT id, user_id, provider, account_label, created_at
		FROM deploy_connections
		WHERE user_id = $1 AND provider = $2
	`
	var conn Connection
	err := s.pool.QueryRow(ctx, query, userID, provider).Scan(
		&conn.ID,
		&conn.UserID,
		&conn.Provider,
		&conn.AccountLabel,
		&conn.CreatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("deploy: get connection status: %w", err)
	}
	return &conn, nil
}

func (s *PgStore) SetConnection(ctx context.Context, userID, provider, token, accountLabel string) (*Connection, error) {
	if len(s.key) != 32 {
		return nil, ErrKeyNotConfigured
	}
	provider = strings.ToLower(strings.TrimSpace(provider))
	if provider != "vercel" && provider != "netlify" {
		return nil, ErrInvalidProvider
	}
	token = strings.TrimSpace(token)
	if token == "" {
		return nil, ErrTokenEmpty
	}

	aad := s.aad(userID, provider)
	ciphertext, err := crypto.Encrypt(s.key, []byte(token), aad)
	if err != nil {
		return nil, fmt.Errorf("deploy: encrypt token: %w", err)
	}

	query := `
		INSERT INTO deploy_connections (user_id, provider, token_ciphertext, account_label, created_at)
		VALUES ($1, $2, $3, $4, now())
		ON CONFLICT (user_id, provider) DO UPDATE
		SET token_ciphertext = EXCLUDED.token_ciphertext,
		    account_label = EXCLUDED.account_label,
		    created_at = now()
		RETURNING id, user_id, provider, account_label, created_at
	`
	var conn Connection
	err = s.pool.QueryRow(ctx, query, userID, provider, ciphertext, accountLabel).Scan(
		&conn.ID,
		&conn.UserID,
		&conn.Provider,
		&conn.AccountLabel,
		&conn.CreatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("deploy: set connection: %w", err)
	}
	return &conn, nil
}

func (s *PgStore) DeleteConnection(ctx context.Context, userID, provider string) error {
	provider = strings.ToLower(strings.TrimSpace(provider))
	query := `DELETE FROM deploy_connections WHERE user_id = $1 AND provider = $2`
	_, err := s.pool.Exec(ctx, query, userID, provider)
	if err != nil {
		return fmt.Errorf("deploy: delete connection: %w", err)
	}
	return nil
}

func (s *PgStore) CreateDeployment(ctx context.Context, d *Deployment) (*Deployment, error) {
	query := `
		INSERT INTO deployments (project_id, provider, external_id, commit_sha, status, url, error, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, now())
		RETURNING id, project_id, provider, external_id, commit_sha, status, url, error, created_at, finished_at
	`
	var created Deployment
	err := s.pool.QueryRow(
		ctx,
		query,
		d.ProjectID,
		d.Provider,
		d.ExternalID,
		d.CommitSHA,
		d.Status,
		d.URL,
		d.Error,
	).Scan(
		&created.ID,
		&created.ProjectID,
		&created.Provider,
		&created.ExternalID,
		&created.CommitSHA,
		&created.Status,
		&created.URL,
		&created.Error,
		&created.CreatedAt,
		&created.FinishedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("deploy: create deployment: %w", err)
	}
	return &created, nil
}

func (s *PgStore) UpdateDeployment(ctx context.Context, id, status, url, errorMsg string, finishedAt *time.Time) error {
	query := `
		UPDATE deployments
		SET status = $2,
		    url = CASE WHEN $3 != '' THEN $3 ELSE url END,
		    error = $4,
		    finished_at = COALESCE($5, finished_at)
		WHERE id = $1
	`
	_, err := s.pool.Exec(ctx, query, id, status, url, errorMsg, finishedAt)
	if err != nil {
		return fmt.Errorf("deploy: update deployment: %w", err)
	}
	return nil
}

func (s *PgStore) GetDeployment(ctx context.Context, id string) (*Deployment, error) {
	query := `
		SELECT id, project_id, provider, external_id, commit_sha, status, url, error, created_at, finished_at
		FROM deployments
		WHERE id = $1
	`
	var d Deployment
	err := s.pool.QueryRow(ctx, query, id).Scan(
		&d.ID,
		&d.ProjectID,
		&d.Provider,
		&d.ExternalID,
		&d.CommitSHA,
		&d.Status,
		&d.URL,
		&d.Error,
		&d.CreatedAt,
		&d.FinishedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("deploy: get deployment: %w", err)
	}
	return &d, nil
}

func (s *PgStore) GetLatestDeployment(ctx context.Context, projectID string) (*Deployment, error) {
	query := `
		SELECT id, project_id, provider, external_id, commit_sha, status, url, error, created_at, finished_at
		FROM deployments
		WHERE project_id = $1
		ORDER BY created_at DESC
		LIMIT 1
	`
	var d Deployment
	err := s.pool.QueryRow(ctx, query, projectID).Scan(
		&d.ID,
		&d.ProjectID,
		&d.Provider,
		&d.ExternalID,
		&d.CommitSHA,
		&d.Status,
		&d.URL,
		&d.Error,
		&d.CreatedAt,
		&d.FinishedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil // None yet
		}
		return nil, fmt.Errorf("deploy: get latest deployment: %w", err)
	}
	return &d, nil
}

func (s *PgStore) ListDeployments(ctx context.Context, projectID string, limit int) ([]Deployment, error) {
	if limit <= 0 || limit > 100 {
		limit = 30
	}
	query := `
		SELECT id, project_id, provider, external_id, commit_sha, status, url, error, created_at, finished_at
		FROM deployments
		WHERE project_id = $1
		ORDER BY created_at DESC
		LIMIT $2
	`
	rows, err := s.pool.Query(ctx, query, projectID, limit)
	if err != nil {
		return nil, fmt.Errorf("deploy: list deployments: %w", err)
	}
	defer rows.Close()

	var list []Deployment
	for rows.Next() {
		var d Deployment
		if err := rows.Scan(
			&d.ID,
			&d.ProjectID,
			&d.Provider,
			&d.ExternalID,
			&d.CommitSHA,
			&d.Status,
			&d.URL,
			&d.Error,
			&d.CreatedAt,
			&d.FinishedAt,
		); err != nil {
			return nil, fmt.Errorf("deploy: scan deployment: %w", err)
		}
		list = append(list, d)
	}
	return list, nil
}

func (s *PgStore) UpdateProjectDeployMeta(ctx context.Context, projectID, provider, externalID, liveURL string) error {
	query := `
		UPDATE projects
		SET deploy_provider = $2,
		    deploy_external_id = $3,
		    live_url = $4
		WHERE id = $1
	`
	_, err := s.pool.Exec(ctx, query, projectID, provider, externalID, liveURL)
	if err != nil {
		return fmt.Errorf("deploy: update project deploy meta: %w", err)
	}
	return nil
}

func (s *PgStore) GetProjectDeployMeta(ctx context.Context, projectID string) (string, string, string, error) {
	query := `
		SELECT deploy_provider, deploy_external_id, live_url
		FROM projects
		WHERE id = $1
	`
	var prov, extID, url string
	err := s.pool.QueryRow(ctx, query, projectID).Scan(&prov, &extID, &url)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return "", "", "", ErrNotFound
		}
		return "", "", "", fmt.Errorf("deploy: get project deploy meta: %w", err)
	}
	return prov, extID, url, nil
}

package git

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/crypto"
)

var (
	ErrConnectionNotFound = errors.New("git: connection not found")
	ErrProjectNotFound    = errors.New("git: project not found")
)

type Connection struct {
	ID             string    `json:"id"`
	UserID         string    `json:"user_id"`
	Provider       string    `json:"provider"`
	ExternalLogin  string    `json:"external_login"`
	InstallationID int64     `json:"installation_id"`
	RefreshToken   string    `json:"-"`
	Scopes         string    `json:"scopes"`
	ConnectedAt    time.Time `json:"connected_at"`
}

type ProjectGitInfo struct {
	ProjectID     string     `json:"project_id"`
	UserID        string     `json:"user_id"`
	Connected     bool       `json:"connected"`
	RepoFullName  string     `json:"repo_full_name"`
	RepoURL       string     `json:"repo_url"`
	RepoPrivate   bool       `json:"repo_private"`
	LastPushedSHA string     `json:"last_pushed_sha"`
	LastPushedAt  *time.Time `json:"last_pushed_at"`
	CommitSHA     string     `json:"commit_sha"`
	AheadBy       int        `json:"ahead_by"`
}

type Store interface {
	GetConnection(ctx context.Context, userID string) (*Connection, error)
	SaveConnection(ctx context.Context, conn *Connection) error
	DeleteConnection(ctx context.Context, userID string) error
	GetProjectGit(ctx context.Context, userID, projectID string) (*ProjectGitInfo, error)
	UpdateProjectRepo(ctx context.Context, userID, projectID, repoFullName, repoURL string, repoPrivate bool) error
	UpdateProjectPushed(ctx context.Context, userID, projectID, pushedSHA string, pushedAt time.Time) error
}

type PgStore struct {
	pool       *pgxpool.Pool
	secretsKey []byte
}

func NewPgStore(pool *pgxpool.Pool, secretsKey []byte) *PgStore {
	return &PgStore{pool: pool, secretsKey: secretsKey}
}

func (s *PgStore) GetConnection(ctx context.Context, userID string) (*Connection, error) {
	query := `
		SELECT id, user_id, provider, external_login, installation_id, refresh_token_encrypted, scopes, connected_at
		FROM git_connections
		WHERE user_id = $1 AND provider = 'github'
	`
	var c Connection
	var encToken []byte
	err := s.pool.QueryRow(ctx, query, userID).Scan(
		&c.ID, &c.UserID, &c.Provider, &c.ExternalLogin, &c.InstallationID, &encToken, &c.Scopes, &c.ConnectedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, ErrConnectionNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("git: get connection: %w", err)
	}

	if len(encToken) > 0 && len(s.secretsKey) == 32 {
		aad := []byte(c.UserID + ":github:token")
		decrypted, err := crypto.Decrypt(s.secretsKey, encToken, aad)
		if err == nil {
			c.RefreshToken = string(decrypted)
		}
	}

	return &c, nil
}

func (s *PgStore) SaveConnection(ctx context.Context, conn *Connection) error {
	var encToken []byte
	if conn.RefreshToken != "" && len(s.secretsKey) == 32 {
		aad := []byte(conn.UserID + ":github:token")
		enc, err := crypto.Encrypt(s.secretsKey, []byte(conn.RefreshToken), aad)
		if err != nil {
			return fmt.Errorf("git: encrypt refresh token: %w", err)
		}
		encToken = enc
	}

	query := `
		INSERT INTO git_connections (
			user_id, provider, external_login, installation_id, refresh_token_encrypted, scopes, connected_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (user_id, provider) DO UPDATE SET
			external_login = EXCLUDED.external_login,
			installation_id = EXCLUDED.installation_id,
			refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
			scopes = EXCLUDED.scopes,
			connected_at = EXCLUDED.connected_at
		RETURNING id
	`
	connectedAt := conn.ConnectedAt
	if connectedAt.IsZero() {
		connectedAt = time.Now()
	}

	var id string
	err := s.pool.QueryRow(ctx, query,
		conn.UserID, conn.Provider, conn.ExternalLogin, conn.InstallationID, encToken, conn.Scopes, connectedAt,
	).Scan(&id)
	if err != nil {
		return fmt.Errorf("git: save connection: %w", err)
	}
	conn.ID = id
	return nil
}

func (s *PgStore) DeleteConnection(ctx context.Context, userID string) error {
	query := `DELETE FROM git_connections WHERE user_id = $1 AND provider = 'github'`
	_, err := s.pool.Exec(ctx, query, userID)
	if err != nil {
		return fmt.Errorf("git: delete connection: %w", err)
	}
	return nil
}

func (s *PgStore) GetProjectGit(ctx context.Context, userID, projectID string) (*ProjectGitInfo, error) {
	query := `
		SELECT p.id, p.user_id, p.commit_sha, p.repo_full_name, p.repo_url, p.repo_private, p.last_pushed_sha, p.last_pushed_at,
		       EXISTS(SELECT 1 FROM git_connections gc WHERE gc.user_id = p.user_id AND gc.provider = 'github') AS connected
		FROM projects p
		WHERE p.id = $1 AND p.user_id = $2
	`
	var info ProjectGitInfo
	var lastPushedAt *time.Time
	err := s.pool.QueryRow(ctx, query, projectID, userID).Scan(
		&info.ProjectID, &info.UserID, &info.CommitSHA, &info.RepoFullName, &info.RepoURL,
		&info.RepoPrivate, &info.LastPushedSHA, &lastPushedAt, &info.Connected,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, ErrProjectNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("git: get project git: %w", err)
	}
	info.LastPushedAt = lastPushedAt

	// Compute basic ahead heuristic: if last_pushed_sha is empty and commit_sha non-empty, ahead by 1+
	if info.CommitSHA != "" && info.CommitSHA != info.LastPushedSHA {
		info.AheadBy = 1
	}

	return &info, nil
}

func (s *PgStore) UpdateProjectRepo(ctx context.Context, userID, projectID, repoFullName, repoURL string, repoPrivate bool) error {
	query := `
		UPDATE projects
		SET repo_full_name = $1, repo_url = $2, repo_private = $3, updated_at = now()
		WHERE id = $4 AND user_id = $5
	`
	cmdTag, err := s.pool.Exec(ctx, query, repoFullName, repoURL, repoPrivate, projectID, userID)
	if err != nil {
		return fmt.Errorf("git: update project repo: %w", err)
	}
	if cmdTag.RowsAffected() == 0 {
		return ErrProjectNotFound
	}
	return nil
}

func (s *PgStore) UpdateProjectPushed(ctx context.Context, userID, projectID, pushedSHA string, pushedAt time.Time) error {
	query := `
		UPDATE projects
		SET last_pushed_sha = $1, last_pushed_at = $2, updated_at = now()
		WHERE id = $3 AND user_id = $4
	`
	cmdTag, err := s.pool.Exec(ctx, query, pushedSHA, pushedAt, projectID, userID)
	if err != nil {
		return fmt.Errorf("git: update project pushed: %w", err)
	}
	if cmdTag.RowsAffected() == 0 {
		return ErrProjectNotFound
	}
	return nil
}

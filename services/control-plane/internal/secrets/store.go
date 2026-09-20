package secrets

import (
	"context"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/crypto"
)

var (
	// ErrKeyNotConfigured is returned when the master encryption key is missing or invalid.
	ErrKeyNotConfigured = errors.New("secrets encryption key is not configured or invalid")
	// ErrInvalidKeyFormat is returned when secret key does not match UPPER_SNAKE_CASE.
	ErrInvalidKeyFormat = errors.New("secret key must be UPPER_SNAKE_CASE (^[A-Z][A-Z0-9_]*$)")
	// ErrSecretNotFound is returned when the requested secret does not exist.
	ErrSecretNotFound = errors.New("secret not found")
	// ErrProjectNotFound is returned when project does not exist or caller does not own it.
	ErrProjectNotFound = errors.New("project not found")
	// ErrValueTooLarge is returned when secret value exceeds 64 KB.
	ErrValueTooLarge = errors.New("secret value exceeds maximum size of 64 KB")
)

var keyPattern = regexp.MustCompile(`^[A-Z][A-Z0-9_]*$`)

// SecretMetadata describes a secret without its plaintext or ciphertext value.
type SecretMetadata struct {
	Key         string     `json:"key"`
	Description string     `json:"description"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
	LastUsedAt  *time.Time `json:"last_used_at,omitempty"`
}

// Store defines operations for managing project secrets.
type Store interface {
	ListSecrets(ctx context.Context, projectID, userID string) ([]SecretMetadata, error)
	SetSecret(ctx context.Context, projectID, userID, key, value, description string) (*SecretMetadata, error)
	DeleteSecret(ctx context.Context, projectID, userID, key string) error
	RevealSecret(ctx context.Context, projectID, userID, key string) (string, error)
	ForProject(ctx context.Context, projectID string) (map[string]string, error)
	IsAvailable() bool
}

// PgStore implements Store using PostgreSQL and AES-256-GCM encryption.
type PgStore struct {
	pool        *pgxpool.Pool
	masterKey   []byte
	previousKey []byte
}

// NewPgStore initializes a PgStore.
func NewPgStore(pool *pgxpool.Pool, masterKey, previousKey []byte) *PgStore {
	return &PgStore{
		pool:        pool,
		masterKey:   masterKey,
		previousKey: previousKey,
	}
}

// IsAvailable reports whether the store has a valid 32-byte master encryption key configured.
func (s *PgStore) IsAvailable() bool {
	return len(s.masterKey) == 32
}

func (s *PgStore) checkOwnership(ctx context.Context, projectID, userID string) error {
	var id string
	err := s.pool.QueryRow(ctx, "SELECT id FROM projects WHERE id = $1 AND user_id = $2 AND status != 'deleted'", projectID, userID).Scan(&id)
	if errors.Is(err, pgx.ErrNoRows) {
		return ErrProjectNotFound
	}
	return err
}

func aad(projectID, key string) []byte {
	return []byte(projectID + ":" + key)
}

// ListSecrets returns metadata for all secrets in a project. Never returns values.
func (s *PgStore) ListSecrets(ctx context.Context, projectID, userID string) ([]SecretMetadata, error) {
	if err := s.checkOwnership(ctx, projectID, userID); err != nil {
		return nil, err
	}

	rows, err := s.pool.Query(ctx, `
		SELECT key, description, created_at, updated_at, last_used_at
		FROM project_secrets
		WHERE project_id = $1
		ORDER BY key ASC
	`, projectID)
	if err != nil {
		return nil, fmt.Errorf("list secrets: %w", err)
	}
	defer rows.Close()

	var result []SecretMetadata
	for rows.Next() {
		var sm SecretMetadata
		if err := rows.Scan(&sm.Key, &sm.Description, &sm.CreatedAt, &sm.UpdatedAt, &sm.LastUsedAt); err != nil {
			return nil, fmt.Errorf("scan secret metadata: %w", err)
		}
		result = append(result, sm)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows error: %w", err)
	}

	if result == nil {
		result = []SecretMetadata{}
	}
	return result, nil
}

// SetSecret encrypts and stores a project secret.
func (s *PgStore) SetSecret(ctx context.Context, projectID, userID, key, value, description string) (*SecretMetadata, error) {
	if !s.IsAvailable() {
		return nil, ErrKeyNotConfigured
	}
	key = strings.TrimSpace(key)
	if !keyPattern.MatchString(key) {
		return nil, ErrInvalidKeyFormat
	}
	if len(value) > 65536 {
		return nil, ErrValueTooLarge
	}
	if err := s.checkOwnership(ctx, projectID, userID); err != nil {
		return nil, err
	}

	ciphertext, err := crypto.Encrypt(s.masterKey, []byte(value), aad(projectID, key))
	if err != nil {
		return nil, fmt.Errorf("encrypt secret: %w", err)
	}

	var sm SecretMetadata
	err = s.pool.QueryRow(ctx, `
		INSERT INTO project_secrets (project_id, key, value_ciphertext, description, updated_at)
		VALUES ($1, $2, $3, $4, now())
		ON CONFLICT (project_id, key) DO UPDATE
		SET value_ciphertext = EXCLUDED.value_ciphertext,
		    description = EXCLUDED.description,
		    updated_at = now()
		RETURNING key, description, created_at, updated_at, last_used_at
	`, projectID, key, ciphertext, description).Scan(
		&sm.Key, &sm.Description, &sm.CreatedAt, &sm.UpdatedAt, &sm.LastUsedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("upsert secret: %w", err)
	}

	return &sm, nil
}

// DeleteSecret removes a secret from a project.
func (s *PgStore) DeleteSecret(ctx context.Context, projectID, userID, key string) error {
	if err := s.checkOwnership(ctx, projectID, userID); err != nil {
		return err
	}

	res, err := s.pool.Exec(ctx, `
		DELETE FROM project_secrets
		WHERE project_id = $1 AND key = $2
	`, projectID, key)
	if err != nil {
		return fmt.Errorf("delete secret: %w", err)
	}
	if res.RowsAffected() == 0 {
		return ErrSecretNotFound
	}
	return nil
}

// RevealSecret decrypts and returns a single secret value for display.
// Updates last_used_at timestamp. Performs transparent re-encryption if decrypted with previousKey.
func (s *PgStore) RevealSecret(ctx context.Context, projectID, userID, key string) (string, error) {
	if !s.IsAvailable() {
		return "", ErrKeyNotConfigured
	}
	if err := s.checkOwnership(ctx, projectID, userID); err != nil {
		return "", err
	}

	var (
		rowID      string
		ciphertext []byte
	)
	err := s.pool.QueryRow(ctx, `
		SELECT id, value_ciphertext
		FROM project_secrets
		WHERE project_id = $1 AND key = $2
	`, projectID, key).Scan(&rowID, &ciphertext)
	if errors.Is(err, pgx.ErrNoRows) {
		return "", ErrSecretNotFound
	}
	if err != nil {
		return "", fmt.Errorf("query secret: %w", err)
	}

	// Try current master key first
	plaintext, err := crypto.Decrypt(s.masterKey, ciphertext, aad(projectID, key))
	if err != nil && len(s.previousKey) == 32 {
		// Try previous key for rotation
		if pt, prevErr := crypto.Decrypt(s.previousKey, ciphertext, aad(projectID, key)); prevErr == nil {
			plaintext = pt
			err = nil
			// Re-encrypt with current master key
			if newCiphertext, reEncErr := crypto.Encrypt(s.masterKey, pt, aad(projectID, key)); reEncErr == nil {
				_, _ = s.pool.Exec(ctx, `
					UPDATE project_secrets
					SET value_ciphertext = $1, updated_at = now()
					WHERE id = $2
				`, newCiphertext, rowID)
			}
		}
	}
	if err != nil {
		return "", fmt.Errorf("decrypt secret: %w", err)
	}

	// Update last_used_at
	_, _ = s.pool.Exec(ctx, `
		UPDATE project_secrets
		SET last_used_at = now()
		WHERE id = $1
	`, rowID)

	return string(plaintext), nil
}

// ForProject returns all decrypted secrets for a project as a key-value map.
// This is used internally by the preview runner and deployment engine.
func (s *PgStore) ForProject(ctx context.Context, projectID string) (map[string]string, error) {
	if !s.IsAvailable() {
		return nil, ErrKeyNotConfigured
	}

	rows, err := s.pool.Query(ctx, `
		SELECT id, key, value_ciphertext
		FROM project_secrets
		WHERE project_id = $1
	`, projectID)
	if err != nil {
		return nil, fmt.Errorf("query project secrets: %w", err)
	}
	defer rows.Close()

	result := make(map[string]string)
	for rows.Next() {
		var (
			rowID      string
			key        string
			ciphertext []byte
		)
		if err := rows.Scan(&rowID, &key, &ciphertext); err != nil {
			return nil, fmt.Errorf("scan secret: %w", err)
		}

		plaintext, decErr := crypto.Decrypt(s.masterKey, ciphertext, aad(projectID, key))
		if decErr != nil && len(s.previousKey) == 32 {
			if pt, prevErr := crypto.Decrypt(s.previousKey, ciphertext, aad(projectID, key)); prevErr == nil {
				plaintext = pt
				decErr = nil
				// Transparent re-encryption
				if newCiphertext, reEncErr := crypto.Encrypt(s.masterKey, pt, aad(projectID, key)); reEncErr == nil {
					_, _ = s.pool.Exec(ctx, `
						UPDATE project_secrets
						SET value_ciphertext = $1, updated_at = now()
						WHERE id = $2
					`, newCiphertext, rowID)
				}
			}
		}
		if decErr != nil {
			continue // Skip corrupted or unreadable secret rather than failing entire run
		}
		result[key] = string(plaintext)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows error: %w", err)
	}

	return result, nil
}

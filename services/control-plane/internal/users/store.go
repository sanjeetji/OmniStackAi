// Package users provides the PostgreSQL-backed implementation of auth.Store. It is kept separate
// from internal/auth so the HTTP handler package depends only on the narrow Store interface it
// declares, never on pgx directly - the same boundary internal/health already draws between its
// Pinger interface and the concrete *pgxpool.Pool that satisfies it.
package users

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

const uniqueViolation = "23505"

// Store implements auth.Store against the control-plane's PostgreSQL database.
type Store struct {
	pool *pgxpool.Pool
}

var _ auth.Store = (*Store)(nil)

// New returns a Store backed by pool.
func New(pool *pgxpool.Pool) *Store {
	return &Store{pool: pool}
}

// CreateUser inserts a new user and, if startingCredits is non-zero, an accompanying
// credit_ledger row recording the signup grant - in one transaction, so a user's credit_balance
// and its ledger history can never disagree.
func (s *Store) CreateUser(ctx context.Context, email, passwordHash, name string, startingCredits int64) (auth.User, error) {
	email = normalizeEmail(email)

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return auth.User{}, err
	}
	defer func() { _ = tx.Rollback(ctx) }()

	var user auth.User
	err = tx.QueryRow(ctx, `
		INSERT INTO users (email, password_hash, full_name, credit_balance)
		VALUES ($1, $2, $3, $4)
		RETURNING id, email, full_name, role, plan, byok_enabled, credit_balance, created_at
	`, email, passwordHash, name, startingCredits).Scan(
		&user.ID, &user.Email, &user.Name, &user.Role, &user.Plan, &user.BYOKEnabled, &user.CreditBalance, &user.CreatedAt,
	)
	if err != nil {
		var pgErr *pgconn.PgError
		if errors.As(err, &pgErr) && pgErr.Code == uniqueViolation {
			return auth.User{}, auth.ErrEmailTaken
		}
		return auth.User{}, err
	}

	if startingCredits != 0 {
		_, err = tx.Exec(ctx, `
			INSERT INTO credit_ledger (user_id, delta, reason, balance_after)
			VALUES ($1, $2, 'signup_grant', $3)
		`, user.ID, startingCredits, startingCredits)
		if err != nil {
			return auth.User{}, err
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return auth.User{}, err
	}
	return user, nil
}

// FindUserByEmail returns the user and their stored password hash. Verifying the password is the
// caller's responsibility (internal/auth) - a persistence layer should not also be a business
// logic layer.
func (s *Store) FindUserByEmail(ctx context.Context, email string) (auth.User, string, error) {
	var user auth.User
	var passwordHash string
	err := s.pool.QueryRow(ctx, `
		SELECT id, email, password_hash, full_name, role, plan, byok_enabled, credit_balance, created_at
		FROM users
		WHERE email = $1
	`, normalizeEmail(email)).Scan(
		&user.ID, &user.Email, &passwordHash, &user.Name, &user.Role, &user.Plan, &user.BYOKEnabled, &user.CreditBalance, &user.CreatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return auth.User{}, "", auth.ErrUserNotFound
	}
	if err != nil {
		return auth.User{}, "", err
	}
	return user, passwordHash, nil
}

// FindUserByID returns the user's public profile.
func (s *Store) FindUserByID(ctx context.Context, id string) (auth.User, error) {
	var user auth.User
	err := s.pool.QueryRow(ctx, `
		SELECT id, email, full_name, role, plan, byok_enabled, credit_balance, created_at
		FROM users
		WHERE id = $1
	`, id).Scan(&user.ID, &user.Email, &user.Name, &user.Role, &user.Plan, &user.BYOKEnabled, &user.CreditBalance, &user.CreatedAt)
	if errors.Is(err, pgx.ErrNoRows) {
		return auth.User{}, auth.ErrUserNotFound
	}
	return user, err
}

// CreateSession records a new session. tokenHash must already be the SHA-256 hash of the raw
// bearer token - the raw token itself is never persisted.
func (s *Store) CreateSession(ctx context.Context, tokenHash, userID string, expiresAt time.Time) error {
	_, err := s.pool.Exec(ctx, `
		INSERT INTO sessions (token_hash, user_id, expires_at)
		VALUES ($1, $2, $3)
	`, tokenHash, userID, expiresAt)
	return err
}

// FindUserBySessionToken returns the user for a still-valid session token hash.
func (s *Store) FindUserBySessionToken(ctx context.Context, tokenHash string) (auth.User, error) {
	var user auth.User
	err := s.pool.QueryRow(ctx, `
		SELECT u.id, u.email, u.full_name, u.role, u.plan, u.byok_enabled, u.credit_balance, u.created_at
		FROM sessions s
		JOIN users u ON u.id = s.user_id
		WHERE s.token_hash = $1 AND s.expires_at > now()
	`, tokenHash).Scan(&user.ID, &user.Email, &user.Name, &user.Role, &user.Plan, &user.BYOKEnabled, &user.CreditBalance, &user.CreatedAt)
	if errors.Is(err, pgx.ErrNoRows) {
		return auth.User{}, auth.ErrSessionNotFound
	}
	return user, err
}

// DeleteSession removes a session. Deleting a token that does not exist is not an error - logout
// is idempotent.
func (s *Store) DeleteSession(ctx context.Context, tokenHash string) error {
	_, err := s.pool.Exec(ctx, `DELETE FROM sessions WHERE token_hash = $1`, tokenHash)
	return err
}

// DebitCredits atomically charges up to `requested` credits against userID's balance, row-locking
// the user for the duration of the transaction so concurrent debits never race. The charge is
// clamped to whatever balance actually exists (v1 policy, R-472: never block a build attempt for
// insufficient credits - only the amount charged is clamped, so credit_balance never goes
// negative; hard pre-flight blocking is a deliberately deferred follow-up). It returns the amount
// actually charged (0 <= charged <= requested) and the resulting balance, and - only when
// charged != 0 - records one append-only credit_ledger row, mirroring CreateUser's signup-grant
// row.
func (s *Store) DebitCredits(ctx context.Context, userID string, requested int64, reason string) (charged int64, newBalance int64, err error) {
	if requested < 0 {
		return 0, 0, fmt.Errorf("users: DebitCredits requested must be >= 0, got %d", requested)
	}
	if strings.TrimSpace(reason) == "" {
		return 0, 0, errors.New("users: DebitCredits reason must not be empty")
	}

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return 0, 0, err
	}
	defer func() { _ = tx.Rollback(ctx) }()

	var balance int64
	err = tx.QueryRow(ctx, `SELECT credit_balance FROM users WHERE id = $1 FOR UPDATE`, userID).Scan(&balance)
	if errors.Is(err, pgx.ErrNoRows) {
		return 0, 0, auth.ErrUserNotFound
	}
	if err != nil {
		return 0, 0, err
	}

	charged, newBalance = clampCharge(balance, requested)

	if charged != 0 {
		if _, err = tx.Exec(ctx, `UPDATE users SET credit_balance = $2 WHERE id = $1`, userID, newBalance); err != nil {
			return 0, 0, err
		}
		if _, err = tx.Exec(ctx, `
			INSERT INTO credit_ledger (user_id, delta, reason, balance_after)
			VALUES ($1, $2, $3, $4)
		`, userID, -charged, reason, newBalance); err != nil {
			return 0, 0, err
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return 0, 0, err
	}
	return charged, newBalance, nil
}

func normalizeEmail(email string) string {
	return strings.ToLower(strings.TrimSpace(email))
}

// clampCharge is the pure arithmetic at the heart of DebitCredits's v1 never-block policy: charge
// whatever is requested, but never more than the balance actually has, and never let the
// resulting balance go negative even if balance itself is already negative (which should not
// happen, but a defensive floor here costs nothing). Split out from DebitCredits so this rule can
// be unit-tested without a database.
func clampCharge(balance, requested int64) (charged, newBalance int64) {
	charged = requested
	if charged > balance {
		charged = balance
	}
	if charged < 0 {
		charged = 0
	}
	return charged, balance - charged
}

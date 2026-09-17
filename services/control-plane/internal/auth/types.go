// Package auth implements the control-plane's HTTP authentication surface: register, login,
// logout, and "who am I". It depends only on narrow interfaces (Store, Hasher) it defines itself
// — the real PostgreSQL-backed store (internal/users) and the real password hasher
// (internal/password) are wired in by cmd/control-plane/main.go, the same "accept an interface,
// wire the real implementation at the edge" shape internal/health already uses for its Pinger.
package auth

import (
	"context"
	"errors"
	"log/slog"
	"time"
)

// User is the public profile of an account. It never carries the password hash.
type User struct {
	ID            string
	Email         string
	Name          string
	Role          string
	Plan          string
	BYOKEnabled   bool
	CreditBalance int64
	CreatedAt     time.Time
}

// Sentinel errors Store implementations return so the HTTP layer can map them to the right
// status code without knowing anything about the underlying storage engine.
var (
	ErrEmailTaken      = errors.New("auth: email already registered")
	ErrUserNotFound    = errors.New("auth: user not found")
	ErrSessionNotFound = errors.New("auth: session not found or expired")
)

// Store is the narrow persistence capability the auth handlers need. FindUserByEmail returns the
// stored password hash alongside the profile because verifying a password is business logic that
// belongs in the handler layer, not the storage layer.
type Store interface {
	CreateUser(ctx context.Context, email, passwordHash, name string, startingCredits int64) (User, error)
	FindUserByEmail(ctx context.Context, email string) (user User, passwordHash string, err error)
	FindUserByID(ctx context.Context, id string) (User, error)
	CreateSession(ctx context.Context, tokenHash, userID string, expiresAt time.Time) error
	FindUserBySessionToken(ctx context.Context, tokenHash string) (User, error)
	DeleteSession(ctx context.Context, tokenHash string) error
}

// Hasher is the narrow password-hashing capability. It is an interface (rather than calling
// internal/password directly) so handler tests can inject a fast fake instead of paying the real
// PBKDF2 iteration cost on every test run.
type Hasher interface {
	Hash(plain string) (string, error)
	Verify(encoded, plain string) (bool, error)
}

// Deps are the dependencies Register needs. SignupCredits is the number of credits granted to a
// new account's free plan on registration.
type Deps struct {
	Store         Store
	Hasher        Hasher
	SessionTTL    time.Duration
	SignupCredits int64
	Logger        *slog.Logger
	// Clock returns the current time; defaults to time.Now. Overridable so tests can assert an
	// exact session expiry without flakiness.
	Clock func() time.Time
}

func (d Deps) now() time.Time {
	if d.Clock == nil {
		return time.Now()
	}
	return d.Clock()
}

func (d Deps) logger() *slog.Logger {
	if d.Logger == nil {
		return slog.Default()
	}
	return d.Logger
}

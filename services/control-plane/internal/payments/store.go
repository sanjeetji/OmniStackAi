package payments

import (
	"context"
	"errors"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

var (
	ErrInvalidGateway  = errors.New("invalid payment gateway: must be 'stripe' or 'razorpay'")
	ErrProjectNotFound = errors.New("project not found or unauthorized")
)

// Store defines operations for managing project payment gateway configuration.
type Store interface {
	GetPaymentGateway(ctx context.Context, projectID, userID string) (string, error)
	SetPaymentGateway(ctx context.Context, projectID, userID, gateway string) error
	ClearPaymentGateway(ctx context.Context, projectID, userID string) error
}

// PgStore implements Store backed by PostgreSQL.
type PgStore struct {
	pool *pgxpool.Pool
}

// NewPgStore initializes a PgStore.
func NewPgStore(pool *pgxpool.Pool) *PgStore {
	return &PgStore{pool: pool}
}

// GetPaymentGateway retrieves the enabled payment gateway for a project.
func (s *PgStore) GetPaymentGateway(ctx context.Context, projectID, userID string) (string, error) {
	var gateway string
	err := s.pool.QueryRow(ctx, `
		SELECT payment_gateway
		FROM projects
		WHERE id = $1 AND user_id = $2
	`, projectID, userID).Scan(&gateway)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return "", ErrProjectNotFound
		}
		return "", fmt.Errorf("failed to get payment gateway: %w", err)
	}

	return gateway, nil
}

// SetPaymentGateway sets the enabled payment gateway for a project.
func (s *PgStore) SetPaymentGateway(ctx context.Context, projectID, userID, gateway string) error {
	if gateway != "stripe" && gateway != "razorpay" {
		return ErrInvalidGateway
	}

	res, err := s.pool.Exec(ctx, `
		UPDATE projects
		SET payment_gateway = $1, updated_at = now()
		WHERE id = $2 AND user_id = $3
	`, gateway, projectID, userID)

	if err != nil {
		return fmt.Errorf("failed to set payment gateway: %w", err)
	}

	if res.RowsAffected() == 0 {
		return ErrProjectNotFound
	}

	return nil
}

// ClearPaymentGateway disables the payment gateway for a project.
func (s *PgStore) ClearPaymentGateway(ctx context.Context, projectID, userID string) error {
	res, err := s.pool.Exec(ctx, `
		UPDATE projects
		SET payment_gateway = '', updated_at = now()
		WHERE id = $1 AND user_id = $2
	`, projectID, userID)

	if err != nil {
		return fmt.Errorf("failed to clear payment gateway: %w", err)
	}

	if res.RowsAffected() == 0 {
		return ErrProjectNotFound
	}

	return nil
}

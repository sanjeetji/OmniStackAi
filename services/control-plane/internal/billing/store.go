package billing

import (
	"context"
	"errors"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Order is one checkout the platform created.
type Order struct {
	ID          string
	Provider    string
	UserID      string
	Kind        string // "credits" | "plan"
	ItemID      string
	Credits     int64
	AmountMinor int64
	Currency    string
	Status      string
}

// Store persists orders and applies payments exactly once.
type Store interface {
	RecordOrder(ctx context.Context, o Order) error
	OrderByID(ctx context.Context, id string) (Order, error)
	SubscriptionOwner(ctx context.Context, provider, subscriptionID string) (userID, plan string, err error)
	// ApplyOnce runs apply inside a transaction the first time (provider, key) is seen, and does
	// nothing for a repeat. It reports whether apply ran.
	ApplyOnce(ctx context.Context, provider, key, kind, userID string, apply func(Tx) error) (bool, error)
}

// Tx is what a payment may change, all in one transaction.
type Tx interface {
	GrantCredits(ctx context.Context, userID string, credits int64, reason string) error
	SetPlan(ctx context.Context, userID, plan string) error
	SaveSubscription(ctx context.Context, userID, provider, subscriptionID, customerID, plan, status string) error
	MarkOrderPaid(ctx context.Context, orderID string) error
}

var ErrOrderNotFound = errors.New("billing: order not found")

// PgStore is the PostgreSQL Store.
type PgStore struct{ pool *pgxpool.Pool }

func NewPgStore(pool *pgxpool.Pool) *PgStore { return &PgStore{pool: pool} }

func (s *PgStore) RecordOrder(ctx context.Context, o Order) error {
	_, err := s.pool.Exec(ctx, `
		INSERT INTO billing_orders (id, provider, user_id, kind, item_id, credits, amount_minor, currency)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8) ON CONFLICT (id) DO NOTHING`,
		o.ID, o.Provider, o.UserID, o.Kind, o.ItemID, o.Credits, o.AmountMinor, o.Currency)
	return err
}

func (s *PgStore) OrderByID(ctx context.Context, id string) (Order, error) {
	var o Order
	err := s.pool.QueryRow(ctx, `
		SELECT id, provider, user_id::text, kind, item_id, credits, amount_minor, currency, status
		FROM billing_orders WHERE id = $1`, id).Scan(
		&o.ID, &o.Provider, &o.UserID, &o.Kind, &o.ItemID, &o.Credits, &o.AmountMinor, &o.Currency, &o.Status)
	if errors.Is(err, pgx.ErrNoRows) {
		return Order{}, ErrOrderNotFound
	}
	return o, err
}

func (s *PgStore) SubscriptionOwner(ctx context.Context, provider, subscriptionID string) (string, string, error) {
	var userID, plan string
	err := s.pool.QueryRow(ctx, `SELECT user_id::text, plan FROM billing_subscriptions WHERE provider = $1 AND subscription_id = $2`,
		provider, subscriptionID).Scan(&userID, &plan)
	if errors.Is(err, pgx.ErrNoRows) {
		return "", "", ErrOrderNotFound
	}
	return userID, plan, err
}

func (s *PgStore) ApplyOnce(ctx context.Context, provider, key, kind, userID string, apply func(Tx) error) (bool, error) {
	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return false, err
	}
	defer func() { _ = tx.Rollback(ctx) }()
	var user any
	if userID != "" {
		user = userID
	}
	tag, err := tx.Exec(ctx, `INSERT INTO billing_events (provider, event_id, kind, user_id) VALUES ($1, $2, $3, $4)
		ON CONFLICT (provider, event_id) DO NOTHING`, provider, key, kind, user)
	if err != nil {
		return false, err
	}
	if tag.RowsAffected() == 0 {
		return false, nil // seen before: a redelivery changes nothing
	}
	if err := apply(pgTx{tx}); err != nil {
		return false, err
	}
	return true, tx.Commit(ctx)
}

type pgTx struct{ tx pgx.Tx }

func (t pgTx) GrantCredits(ctx context.Context, userID string, credits int64, reason string) error {
	if credits <= 0 {
		return nil
	}
	var balance int64
	if err := t.tx.QueryRow(ctx, `UPDATE users SET credit_balance = credit_balance + $2 WHERE id = $1 RETURNING credit_balance`,
		userID, credits).Scan(&balance); err != nil {
		return fmt.Errorf("billing: grant credits: %w", err)
	}
	_, err := t.tx.Exec(ctx, `INSERT INTO credit_ledger (user_id, delta, reason, balance_after) VALUES ($1, $2, $3, $4)`,
		userID, credits, reason, balance)
	return err
}

func (t pgTx) SetPlan(ctx context.Context, userID, plan string) error {
	_, err := t.tx.Exec(ctx, `UPDATE users SET plan = $2 WHERE id = $1`, userID, plan)
	return err
}

func (t pgTx) SaveSubscription(ctx context.Context, userID, provider, subscriptionID, customerID, plan, status string) error {
	_, err := t.tx.Exec(ctx, `
		INSERT INTO billing_subscriptions (user_id, provider, subscription_id, customer_id, plan, status, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, now())
		ON CONFLICT (user_id) DO UPDATE SET provider = $2, subscription_id = $3,
			customer_id = COALESCE(NULLIF($4, ''), billing_subscriptions.customer_id), plan = $5, status = $6, updated_at = now()`,
		userID, provider, subscriptionID, customerID, plan, status)
	return err
}

func (t pgTx) MarkOrderPaid(ctx context.Context, orderID string) error {
	_, err := t.tx.Exec(ctx, `UPDATE billing_orders SET status = 'paid', paid_at = now() WHERE id = $1`, orderID)
	return err
}

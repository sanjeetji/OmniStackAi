package ai

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
	// ErrKeyNotConfigured is returned when the master encryption key is missing or invalid.
	ErrKeyNotConfigured = errors.New("ai: encryption key is not configured or invalid")
	// ErrKeyNotFound is returned when the requested provider key does not exist.
	ErrKeyNotFound = errors.New("ai: provider key not found")
	// ErrProjectNotFound is returned when the requested project does not exist or caller does not own it.
	ErrProjectNotFound = errors.New("ai: project not found")
	// ErrInvalidProvider is returned when provider ID is empty.
	ErrInvalidProvider = errors.New("ai: invalid provider ID")
	// ErrKeyEmpty is returned when API key is empty.
	ErrKeyEmpty = errors.New("ai: API key cannot be empty")
)

// KeyMetadata describes a user's BYOK key without exposing its value.
type KeyMetadata struct {
	ProviderID string     `json:"provider_id"`
	Label      string     `json:"label"`
	CreatedAt  time.Time  `json:"created_at"`
	LastUsedAt *time.Time `json:"last_used_at,omitempty"`
}

// ModelCall represents one row in model_calls table.
type ModelCall struct {
	ID            int64     `json:"id,omitempty"`
	UserID        string    `json:"user_id"`
	ProjectID     *string   `json:"project_id,omitempty"`
	ProviderID    string    `json:"provider_id"`
	ModelID       string    `json:"model_id"`
	Tier          string    `json:"tier"`    // 'local' | 'cloud'
	Purpose       string    `json:"purpose"` // 'build' | 'edit' | 'ui_synthesis' | 'problems'
	InputTokens   int64     `json:"input_tokens"`
	OutputTokens  int64     `json:"output_tokens"`
	CostMicrosUSD int64     `json:"cost_micros_usd"`
	CreditsSpent  int64     `json:"credits_spent"`
	BilledTo      string    `json:"billed_to"` // 'platform' | 'byok' | 'local'
	Success       bool      `json:"success"`
	ErrorCode     string    `json:"error_code"`
	LatencyMS     int       `json:"latency_ms"`
	CreatedAt     time.Time `json:"created_at"`
}

// UsageTotals aggregates usage metrics.
type UsageTotals struct {
	TotalCalls      int64 `json:"total_calls"`
	SuccessfulCalls int64 `json:"successful_calls"`
	FailedCalls     int64 `json:"failed_calls"`
	InputTokens     int64 `json:"input_tokens"`
	OutputTokens    int64 `json:"output_tokens"`
	CostMicrosUSD   int64 `json:"cost_micros_usd"`
	CreditsSpent    int64 `json:"credits_spent"`
	UnpricedCalls   int64 `json:"unpriced_calls"`
}

// DailyUsage groups usage by calendar day.
type DailyUsage struct {
	Date          string `json:"date"` // YYYY-MM-DD
	Calls         int64  `json:"calls"`
	InputTokens   int64  `json:"input_tokens"`
	OutputTokens  int64  `json:"output_tokens"`
	CostMicrosUSD int64  `json:"cost_micros_usd"`
	CreditsSpent  int64  `json:"credits_spent"`
}

// PurposeUsage groups usage by call purpose.
type PurposeUsage struct {
	Purpose       string `json:"purpose"`
	Calls         int64  `json:"calls"`
	InputTokens   int64  `json:"input_tokens"`
	OutputTokens  int64  `json:"output_tokens"`
	CostMicrosUSD int64  `json:"cost_micros_usd"`
	CreditsSpent  int64  `json:"credits_spent"`
}

// ProjectUsageReport contains usage data for a single project.
type ProjectUsageReport struct {
	ProjectID string                  `json:"project_id"`
	RangeDays int                     `json:"range_days"`
	Totals    UsageTotals             `json:"totals"`
	ByDay     []DailyUsage            `json:"by_day"`
	ByPurpose map[string]PurposeUsage `json:"by_purpose"`
}

// ProjectSummaryUsage represents usage for one project in account overview.
type ProjectSummaryUsage struct {
	ProjectID     string `json:"project_id"`
	ProjectName   string `json:"project_name"`
	Calls         int64  `json:"calls"`
	CostMicrosUSD int64  `json:"cost_micros_usd"`
	CreditsSpent  int64  `json:"credits_spent"`
}

// AccountUsageReport contains account-wide usage data.
type AccountUsageReport struct {
	RangeDays     int                   `json:"range_days"`
	Totals        UsageTotals           `json:"totals"`
	ByDay         []DailyUsage          `json:"by_day"`
	ByProject     []ProjectSummaryUsage `json:"by_project"`
	CreditBalance int64                 `json:"credit_balance"`
}

// ProjectModelConfig describes a project's pinned model settings.
type ProjectModelConfig struct {
	ProjectID       string `json:"project_id"`
	ModelProviderID string `json:"model_provider_id"`
	ModelID         string `json:"model_id"`
}

// Store defines operations for managing AI keys, model settings, and usage logs.
type Store interface {
	ListUserKeys(ctx context.Context, userID string) ([]KeyMetadata, error)
	GetUserKey(ctx context.Context, userID, providerID string) (apiKey string, label string, err error)
	SetUserKey(ctx context.Context, userID, providerID, apiKey, label string) error
	DeleteUserKey(ctx context.Context, userID, providerID string) error
	RecordModelCalls(ctx context.Context, calls []ModelCall) error
	GetProjectUsage(ctx context.Context, userID, projectID string, days int) (*ProjectUsageReport, error)
	GetAccountUsage(ctx context.Context, userID string, days int) (*AccountUsageReport, error)
	GetProjectModel(ctx context.Context, userID, projectID string) (*ProjectModelConfig, error)
	SetProjectModel(ctx context.Context, userID, projectID, providerID, modelID string) error
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

func aad(userID, providerID string) []byte {
	return []byte(userID + ":" + strings.ToLower(providerID))
}

func (s *PgStore) checkProjectOwnership(ctx context.Context, projectID, userID string) error {
	var id string
	err := s.pool.QueryRow(ctx, "SELECT id FROM projects WHERE id = $1 AND user_id = $2 AND status != 'deleted'", projectID, userID).Scan(&id)
	if errors.Is(err, pgx.ErrNoRows) {
		return ErrProjectNotFound
	}
	return err
}

// ListUserKeys returns metadata for all BYOK keys owned by the user. Values are never returned.
func (s *PgStore) ListUserKeys(ctx context.Context, userID string) ([]KeyMetadata, error) {
	rows, err := s.pool.Query(ctx, `
		SELECT provider_id, label, created_at, last_used_at
		FROM user_provider_keys
		WHERE user_id = $1
		ORDER BY provider_id ASC
	`, userID)
	if err != nil {
		return nil, fmt.Errorf("list user keys: %w", err)
	}
	defer rows.Close()

	var keys []KeyMetadata
	for rows.Next() {
		var km KeyMetadata
		if err := rows.Scan(&km.ProviderID, &km.Label, &km.CreatedAt, &km.LastUsedAt); err != nil {
			return nil, fmt.Errorf("scan user key: %w", err)
		}
		keys = append(keys, km)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate user keys: %w", err)
	}
	return keys, nil
}

// GetUserKey decrypts and returns the user's API key for a provider.
func (s *PgStore) GetUserKey(ctx context.Context, userID, providerID string) (string, string, error) {
	if !s.IsAvailable() {
		return "", "", ErrKeyNotConfigured
	}
	providerID = strings.ToLower(strings.TrimSpace(providerID))
	if providerID == "" {
		return "", "", ErrInvalidProvider
	}

	var ciphertext []byte
	var label string
	err := s.pool.QueryRow(ctx, `
		SELECT key_ciphertext, label
		FROM user_provider_keys
		WHERE user_id = $1 AND provider_id = $2
	`, userID, providerID).Scan(&ciphertext, &label)
	if errors.Is(err, pgx.ErrNoRows) {
		return "", "", ErrKeyNotFound
	}
	if err != nil {
		return "", "", fmt.Errorf("get user key: %w", err)
	}

	authData := aad(userID, providerID)
	plaintext, err := crypto.Decrypt(s.masterKey, ciphertext, authData)
	if err == nil {
		return string(plaintext), label, nil
	}

	// Try previous key for transparent rotation
	if len(s.previousKey) == 32 {
		plaintext, prevErr := crypto.Decrypt(s.previousKey, ciphertext, authData)
		if prevErr == nil {
			// Re-encrypt with master key
			if newCiphertext, encErr := crypto.Encrypt(s.masterKey, plaintext, authData); encErr == nil {
				_, _ = s.pool.Exec(ctx, `
					UPDATE user_provider_keys
					SET key_ciphertext = $1
					WHERE user_id = $2 AND provider_id = $3
				`, newCiphertext, userID, providerID)
			}
			return string(plaintext), label, nil
		}
	}

	return "", "", fmt.Errorf("decrypt user key: %w", err)
}

// SetUserKey encrypts and stores the user's API key for a provider.
func (s *PgStore) SetUserKey(ctx context.Context, userID, providerID, apiKey, label string) error {
	if !s.IsAvailable() {
		return ErrKeyNotConfigured
	}
	providerID = strings.ToLower(strings.TrimSpace(providerID))
	if providerID == "" {
		return ErrInvalidProvider
	}
	apiKey = strings.TrimSpace(apiKey)
	if apiKey == "" {
		return ErrKeyEmpty
	}

	ciphertext, err := crypto.Encrypt(s.masterKey, []byte(apiKey), aad(userID, providerID))
	if err != nil {
		return fmt.Errorf("encrypt user key: %w", err)
	}

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("begin set key tx: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	_, err = tx.Exec(ctx, `
		INSERT INTO user_provider_keys (user_id, provider_id, key_ciphertext, label, created_at)
		VALUES ($1, $2, $3, $4, now())
		ON CONFLICT (user_id, provider_id)
		DO UPDATE SET
			key_ciphertext = EXCLUDED.key_ciphertext,
			label = EXCLUDED.label
	`, userID, providerID, ciphertext, label)
	if err != nil {
		return fmt.Errorf("upsert user key: %w", err)
	}

	// Set users.byok_enabled = true
	_, err = tx.Exec(ctx, `UPDATE users SET byok_enabled = true WHERE id = $1`, userID)
	if err != nil {
		return fmt.Errorf("update user byok_enabled: %w", err)
	}

	return tx.Commit(ctx)
}

// DeleteUserKey removes a user's BYOK key for a provider.
func (s *PgStore) DeleteUserKey(ctx context.Context, userID, providerID string) error {
	providerID = strings.ToLower(strings.TrimSpace(providerID))
	if providerID == "" {
		return ErrInvalidProvider
	}

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("begin delete key tx: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	res, err := tx.Exec(ctx, `
		DELETE FROM user_provider_keys
		WHERE user_id = $1 AND provider_id = $2
	`, userID, providerID)
	if err != nil {
		return fmt.Errorf("delete user key: %w", err)
	}
	if res.RowsAffected() == 0 {
		return ErrKeyNotFound
	}

	// If user has no more BYOK keys, update users.byok_enabled = false
	var count int
	if err := tx.QueryRow(ctx, `SELECT COUNT(*) FROM user_provider_keys WHERE user_id = $1`, userID).Scan(&count); err == nil {
		if count == 0 {
			_, _ = tx.Exec(ctx, `UPDATE users SET byok_enabled = false WHERE id = $1`, userID)
		}
	}

	return tx.Commit(ctx)
}

// RecordModelCalls inserts call records into model_calls.
func (s *PgStore) RecordModelCalls(ctx context.Context, calls []ModelCall) error {
	if len(calls) == 0 {
		return nil
	}

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("begin record model calls tx: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	for _, call := range calls {
		tier := call.Tier
		if tier != "local" && tier != "cloud" {
			tier = "cloud"
		}
		billedTo := call.BilledTo
		if billedTo != "platform" && billedTo != "byok" && billedTo != "local" {
			billedTo = "platform"
		}
		purpose := call.Purpose
		if purpose == "" {
			purpose = "build"
		}

		_, err := tx.Exec(ctx, `
			INSERT INTO model_calls (
				user_id, project_id, provider_id, model_id, tier, purpose,
				input_tokens, output_tokens, cost_micros_usd, credits_spent,
				billed_to, success, error_code, latency_ms, created_at
			) VALUES (
				$1, $2, $3, $4, $5, $6,
				$7, $8, $9, $10,
				$11, $12, $13, $14, now()
			)
		`,
			call.UserID, call.ProjectID, call.ProviderID, call.ModelID, tier, purpose,
			call.InputTokens, call.OutputTokens, call.CostMicrosUSD, call.CreditsSpent,
			billedTo, call.Success, call.ErrorCode, call.LatencyMS,
		)
		if err != nil {
			return fmt.Errorf("insert model call: %w", err)
		}

		// If billed to BYOK, update last_used_at on user_provider_keys
		if billedTo == "byok" {
			_, _ = tx.Exec(ctx, `
				UPDATE user_provider_keys
				SET last_used_at = now()
				WHERE user_id = $1 AND provider_id = $2
			`, call.UserID, strings.ToLower(call.ProviderID))
		}
	}

	return tx.Commit(ctx)
}

// GetProjectUsage retrieves aggregated usage data for a project over the specified range.
func (s *PgStore) GetProjectUsage(ctx context.Context, userID, projectID string, days int) (*ProjectUsageReport, error) {
	if err := s.checkProjectOwnership(ctx, projectID, userID); err != nil {
		return nil, err
	}

	if days <= 0 {
		days = 7
	}
	cutoff := time.Now().AddDate(0, 0, -days)

	report := &ProjectUsageReport{
		ProjectID: projectID,
		RangeDays: days,
		ByPurpose: make(map[string]PurposeUsage),
	}

	// Totals
	err := s.pool.QueryRow(ctx, `
		SELECT
			COALESCE(COUNT(*), 0),
			COALESCE(COUNT(*) FILTER (WHERE success = true), 0),
			COALESCE(COUNT(*) FILTER (WHERE success = false), 0),
			COALESCE(SUM(input_tokens), 0),
			COALESCE(SUM(output_tokens), 0),
			COALESCE(SUM(cost_micros_usd), 0),
			COALESCE(SUM(credits_spent), 0),
			COALESCE(COUNT(*) FILTER (WHERE cost_micros_usd = 0 AND tier = 'cloud'), 0)
		FROM model_calls
		WHERE user_id = $1 AND project_id = $2 AND created_at >= $3
	`, userID, projectID, cutoff).Scan(
		&report.Totals.TotalCalls,
		&report.Totals.SuccessfulCalls,
		&report.Totals.FailedCalls,
		&report.Totals.InputTokens,
		&report.Totals.OutputTokens,
		&report.Totals.CostMicrosUSD,
		&report.Totals.CreditsSpent,
		&report.Totals.UnpricedCalls,
	)
	if err != nil {
		return nil, fmt.Errorf("project usage totals: %w", err)
	}

	// By Day
	dayRows, err := s.pool.Query(ctx, `
		SELECT
			TO_CHAR(created_at, 'YYYY-MM-DD') AS day,
			COUNT(*),
			COALESCE(SUM(input_tokens), 0),
			COALESCE(SUM(output_tokens), 0),
			COALESCE(SUM(cost_micros_usd), 0),
			COALESCE(SUM(credits_spent), 0)
		FROM model_calls
		WHERE user_id = $1 AND project_id = $2 AND created_at >= $3
		GROUP BY day
		ORDER BY day ASC
	`, userID, projectID, cutoff)
	if err != nil {
		return nil, fmt.Errorf("project usage by day: %w", err)
	}
	defer dayRows.Close()

	for dayRows.Next() {
		var du DailyUsage
		if err := dayRows.Scan(&du.Date, &du.Calls, &du.InputTokens, &du.OutputTokens, &du.CostMicrosUSD, &du.CreditsSpent); err != nil {
			return nil, fmt.Errorf("scan daily usage: %w", err)
		}
		report.ByDay = append(report.ByDay, du)
	}

	// By Purpose
	purpRows, err := s.pool.Query(ctx, `
		SELECT
			purpose,
			COUNT(*),
			COALESCE(SUM(input_tokens), 0),
			COALESCE(SUM(output_tokens), 0),
			COALESCE(SUM(cost_micros_usd), 0),
			COALESCE(SUM(credits_spent), 0)
		FROM model_calls
		WHERE user_id = $1 AND project_id = $2 AND created_at >= $3
		GROUP BY purpose
		ORDER BY purpose ASC
	`, userID, projectID, cutoff)
	if err != nil {
		return nil, fmt.Errorf("project usage by purpose: %w", err)
	}
	defer purpRows.Close()

	for purpRows.Next() {
		var pu PurposeUsage
		if err := purpRows.Scan(&pu.Purpose, &pu.Calls, &pu.InputTokens, &pu.OutputTokens, &pu.CostMicrosUSD, &pu.CreditsSpent); err != nil {
			return nil, fmt.Errorf("scan purpose usage: %w", err)
		}
		report.ByPurpose[pu.Purpose] = pu
	}

	return report, nil
}

// GetAccountUsage retrieves account-wide usage metrics and per-project breakdowns.
func (s *PgStore) GetAccountUsage(ctx context.Context, userID string, days int) (*AccountUsageReport, error) {
	if days <= 0 {
		days = 30
	}
	cutoff := time.Now().AddDate(0, 0, -days)

	report := &AccountUsageReport{
		RangeDays: days,
	}

	// Get credit balance
	_ = s.pool.QueryRow(ctx, `SELECT credit_balance FROM users WHERE id = $1`, userID).Scan(&report.CreditBalance)

	// Totals
	err := s.pool.QueryRow(ctx, `
		SELECT
			COALESCE(COUNT(*), 0),
			COALESCE(COUNT(*) FILTER (WHERE success = true), 0),
			COALESCE(COUNT(*) FILTER (WHERE success = false), 0),
			COALESCE(SUM(input_tokens), 0),
			COALESCE(SUM(output_tokens), 0),
			COALESCE(SUM(cost_micros_usd), 0),
			COALESCE(SUM(credits_spent), 0),
			COALESCE(COUNT(*) FILTER (WHERE cost_micros_usd = 0 AND tier = 'cloud'), 0)
		FROM model_calls
		WHERE user_id = $1 AND created_at >= $2
	`, userID, cutoff).Scan(
		&report.Totals.TotalCalls,
		&report.Totals.SuccessfulCalls,
		&report.Totals.FailedCalls,
		&report.Totals.InputTokens,
		&report.Totals.OutputTokens,
		&report.Totals.CostMicrosUSD,
		&report.Totals.CreditsSpent,
		&report.Totals.UnpricedCalls,
	)
	if err != nil {
		return nil, fmt.Errorf("account usage totals: %w", err)
	}

	// By Day
	dayRows, err := s.pool.Query(ctx, `
		SELECT
			TO_CHAR(created_at, 'YYYY-MM-DD') AS day,
			COUNT(*),
			COALESCE(SUM(input_tokens), 0),
			COALESCE(SUM(output_tokens), 0),
			COALESCE(SUM(cost_micros_usd), 0),
			COALESCE(SUM(credits_spent), 0)
		FROM model_calls
		WHERE user_id = $1 AND created_at >= $2
		GROUP BY day
		ORDER BY day ASC
	`, userID, cutoff)
	if err != nil {
		return nil, fmt.Errorf("account usage by day: %w", err)
	}
	defer dayRows.Close()

	for dayRows.Next() {
		var du DailyUsage
		if err := dayRows.Scan(&du.Date, &du.Calls, &du.InputTokens, &du.OutputTokens, &du.CostMicrosUSD, &du.CreditsSpent); err != nil {
			return nil, fmt.Errorf("scan daily usage: %w", err)
		}
		report.ByDay = append(report.ByDay, du)
	}

	// By Project
	projRows, err := s.pool.Query(ctx, `
		SELECT
			COALESCE(m.project_id::text, ''),
			COALESCE(p.name, 'No project'),
			COUNT(*),
			COALESCE(SUM(m.cost_micros_usd), 0),
			COALESCE(SUM(m.credits_spent), 0)
		FROM model_calls m
		LEFT JOIN projects p ON m.project_id = p.id
		WHERE m.user_id = $1 AND m.created_at >= $2
		GROUP BY m.project_id, p.name
		ORDER BY SUM(m.credits_spent) DESC, COUNT(*) DESC
	`, userID, cutoff)
	if err != nil {
		return nil, fmt.Errorf("account usage by project: %w", err)
	}
	defer projRows.Close()

	for projRows.Next() {
		var psu ProjectSummaryUsage
		if err := projRows.Scan(&psu.ProjectID, &psu.ProjectName, &psu.Calls, &psu.CostMicrosUSD, &psu.CreditsSpent); err != nil {
			return nil, fmt.Errorf("scan project summary usage: %w", err)
		}
		report.ByProject = append(report.ByProject, psu)
	}

	return report, nil
}

// GetProjectModel returns the pinned model configuration for a project.
func (s *PgStore) GetProjectModel(ctx context.Context, userID, projectID string) (*ProjectModelConfig, error) {
	var cfg ProjectModelConfig
	cfg.ProjectID = projectID
	err := s.pool.QueryRow(ctx, `
		SELECT model_provider_id, model_id
		FROM projects
		WHERE id = $1 AND user_id = $2 AND status != 'deleted'
	`, projectID, userID).Scan(&cfg.ModelProviderID, &cfg.ModelID)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, ErrProjectNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("get project model: %w", err)
	}
	return &cfg, nil
}

// SetProjectModel updates the pinned model configuration for a project.
func (s *PgStore) SetProjectModel(ctx context.Context, userID, projectID, providerID, modelID string) error {
	res, err := s.pool.Exec(ctx, `
		UPDATE projects
		SET model_provider_id = $1, model_id = $2, updated_at = now()
		WHERE id = $3 AND user_id = $4 AND status != 'deleted'
	`, strings.TrimSpace(providerID), strings.TrimSpace(modelID), projectID, userID)
	if err != nil {
		return fmt.Errorf("set project model: %w", err)
	}
	if res.RowsAffected() == 0 {
		return ErrProjectNotFound
	}
	return nil
}

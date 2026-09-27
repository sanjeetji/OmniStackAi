// Package account is what a person can do with their own OmniStackAI account beyond signing in
// (PC-012, D-4): prove their email, reset a forgotten password, take their data with them, and
// delete the account. It also keeps data only as long as the privacy policy says (Sweep).
package account

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/mail"
)

const (
	purposeVerify = "verify_email"
	purposeReset  = "reset_password"
	verifyTTL     = 24 * time.Hour
	resetTTL      = time.Hour
)

// Deps wires the account routes.
type Deps struct {
	Pool           *pgxpool.Pool
	AuthStore      auth.Store
	Hasher         auth.Hasher
	Mailer         mail.Mailer
	PublicURL      string // the console, where links land
	TermsVersion   string
	AgentEngineURL string // to remove a deleted account's workspaces and live apps
	HTTPClient     *http.Client
	Logger         *slog.Logger
	// CancelSubscription ends a paid plan at its provider before the account is deleted.
	CancelSubscription func(ctx context.Context, provider, subscriptionID string) error
}

func (d Deps) logger() *slog.Logger {
	if d.Logger != nil {
		return d.Logger
	}
	return slog.Default()
}

// RequireVerification is on unless OMNISTACKAI_REQUIRE_EMAIL_VERIFICATION=0.
func RequireVerification() bool { return os.Getenv("OMNISTACKAI_REQUIRE_EMAIL_VERIFICATION") != "0" }

// RequireVerified refuses paid or public work (building, editing, publishing) until the address
// is proven. It answers 403 with a flag the console uses to offer "send the link again".
func RequireVerified(w http.ResponseWriter, user auth.User) bool {
	if user.EmailVerified || !RequireVerification() {
		return true
	}
	writeJSON(w, http.StatusForbidden, map[string]any{
		"error":        fmt.Sprintf("Please verify your email first. We sent a link to %s.", user.Email),
		"verify_email": true,
	})
	return false
}

// Register adds the account routes.
func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("POST /auth/verify-email", handleVerify(deps))
	mux.HandleFunc("POST /auth/verify-email/resend", handleResend(deps))
	mux.HandleFunc("POST /auth/forgot-password", handleForgot(deps))
	mux.HandleFunc("POST /auth/reset-password", handleReset(deps))
	mux.HandleFunc("GET /auth/me/export", handleExport(deps))
	mux.HandleFunc("POST /auth/me/delete", handleDelete(deps))
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func decode(r *http.Request, v any) bool {
	return json.NewDecoder(io.LimitReader(r.Body, 8192)).Decode(v) == nil
}

func newToken() (raw, hash string, err error) {
	buf := make([]byte, 32)
	if _, err := rand.Read(buf); err != nil {
		return "", "", err
	}
	raw = base64.RawURLEncoding.EncodeToString(buf)
	return raw, hashOf(raw), nil
}

func hashOf(raw string) string {
	sum := sha256.Sum256([]byte(raw))
	return hex.EncodeToString(sum[:])
}

func (d Deps) issue(ctx context.Context, userID, purpose string, ttl time.Duration) (string, error) {
	raw, hash, err := newToken()
	if err != nil {
		return "", err
	}
	// A new link replaces any older one of the same kind.
	if _, err := d.Pool.Exec(ctx, `UPDATE account_tokens SET used_at = now() WHERE user_id = $1 AND purpose = $2 AND used_at IS NULL`,
		userID, purpose); err != nil {
		return "", err
	}
	_, err = d.Pool.Exec(ctx, `INSERT INTO account_tokens (user_id, purpose, token_hash, expires_at) VALUES ($1, $2, $3, $4)`,
		userID, purpose, hash, time.Now().Add(ttl))
	return raw, err
}

// redeem marks a live token used and returns its user; one use only.
func (d Deps) redeem(ctx context.Context, tx pgx.Tx, raw, purpose string) (string, error) {
	var userID string
	err := tx.QueryRow(ctx, `
		UPDATE account_tokens SET used_at = now()
		WHERE token_hash = $1 AND purpose = $2 AND used_at IS NULL AND expires_at > now()
		RETURNING user_id::text`, hashOf(raw), purpose).Scan(&userID)
	return userID, err
}

func (d Deps) link(path, token string) string {
	return strings.TrimRight(d.PublicURL, "/") + path + "?token=" + url.QueryEscape(token)
}

// OnRegistered records the accepted terms and sends the verification link (auth.Deps.OnRegistered).
func (d Deps) OnRegistered(ctx context.Context, user auth.User) {
	if d.TermsVersion != "" {
		if _, err := d.Pool.Exec(ctx, `UPDATE users SET terms_version = $2, terms_accepted_at = now() WHERE id = $1`,
			user.ID, d.TermsVersion); err != nil {
			d.logger().Error("record terms acceptance", "error", err)
		}
	}
	if err := d.sendVerification(ctx, user); err != nil {
		d.logger().Error("send verification email", "error", err)
	}
}

func (d Deps) sendVerification(ctx context.Context, user auth.User) error {
	token, err := d.issue(ctx, user.ID, purposeVerify, verifyTTL)
	if err != nil {
		return err
	}
	return d.Mailer.Send(ctx, user.Email, "Verify your email for OmniStackAI",
		"Hello"+greeting(user.Name)+",\n\nConfirm this address to start building:\n\n"+d.link("/verify-email", token)+
			"\n\nThe link works for 24 hours. If you did not create an account, ignore this email.\n")
}

func greeting(name string) string {
	if strings.TrimSpace(name) == "" {
		return ""
	}
	return " " + strings.TrimSpace(name)
}

func handleVerify(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			Token string `json:"token"`
		}
		if !decode(r, &req) || req.Token == "" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "missing token"})
			return
		}
		ctx := r.Context()
		tx, err := deps.Pool.Begin(ctx)
		if err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "try again"})
			return
		}
		defer func() { _ = tx.Rollback(ctx) }()
		userID, err := deps.redeem(ctx, tx, req.Token, purposeVerify)
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "This link has expired or was already used. Send a new one from Settings."})
			return
		}
		if _, err := tx.Exec(ctx, `UPDATE users SET email_verified_at = COALESCE(email_verified_at, now()) WHERE id = $1`, userID); err != nil || tx.Commit(ctx) != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "try again"})
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "verified"})
	}
}

func handleResend(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "not signed in"})
			return
		}
		if user.EmailVerified {
			writeJSON(w, http.StatusOK, map[string]string{"status": "already verified"})
			return
		}
		// One link a minute is plenty, and keeps this from being a way to flood someone's inbox.
		var recent bool
		_ = deps.Pool.QueryRow(r.Context(), `SELECT EXISTS (SELECT 1 FROM account_tokens WHERE user_id = $1 AND purpose = $2
			AND created_at > now() - interval '1 minute')`, user.ID, purposeVerify).Scan(&recent)
		if recent {
			writeJSON(w, http.StatusTooManyRequests, map[string]string{"error": "A link was just sent. Please wait a minute."})
			return
		}
		if err := deps.sendVerification(r.Context(), user); err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "The email could not be sent."})
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "sent"})
	}
}

func handleForgot(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			Email string `json:"email"`
		}
		_ = decode(r, &req)
		// The same answer whether or not the address has an account: this cannot be used to find
		// out who is registered.
		answer := map[string]string{"status": "If that address has an account, a reset link is on its way."}
		user, _, err := deps.AuthStore.FindUserByEmail(r.Context(), strings.TrimSpace(req.Email))
		if err != nil {
			writeJSON(w, http.StatusOK, answer)
			return
		}
		token, err := deps.issue(r.Context(), user.ID, purposeReset, resetTTL)
		if err == nil {
			err = deps.Mailer.Send(r.Context(), user.Email, "Reset your OmniStackAI password",
				"Hello"+greeting(user.Name)+",\n\nChoose a new password here:\n\n"+deps.link("/reset-password", token)+
					"\n\nThe link works for one hour and only once. If you did not ask for this, ignore this email;\nyour password is unchanged.\n")
		}
		if err != nil {
			deps.logger().Error("send reset email", "error", err)
		}
		writeJSON(w, http.StatusOK, answer)
	}
}

func handleReset(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			Token       string `json:"token"`
			NewPassword string `json:"new_password"`
		}
		if !decode(r, &req) || req.Token == "" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "missing token"})
			return
		}
		if err := auth.ValidatePassword(req.NewPassword); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		hash, err := deps.Hasher.Hash(req.NewPassword)
		if err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "try again"})
			return
		}
		ctx := r.Context()
		tx, err := deps.Pool.Begin(ctx)
		if err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "try again"})
			return
		}
		defer func() { _ = tx.Rollback(ctx) }()
		userID, err := deps.redeem(ctx, tx, req.Token, purposeReset)
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "This link has expired or was already used. Ask for a new one."})
			return
		}
		// Receiving the link also proves the address. Every session ends: whoever had the old
		// password is signed out everywhere.
		_, err1 := tx.Exec(ctx, `UPDATE users SET password_hash = $2, email_verified_at = COALESCE(email_verified_at, now()) WHERE id = $1`, userID, hash)
		_, err2 := tx.Exec(ctx, `DELETE FROM sessions WHERE user_id = $1`, userID)
		if err1 != nil || err2 != nil || tx.Commit(ctx) != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "try again"})
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "Your password is changed. Sign in with it."})
	}
}

// ── export ──

func rows(ctx context.Context, pool *pgxpool.Pool, sql string, args ...any) []map[string]any {
	out := []map[string]any{}
	result, err := pool.Query(ctx, sql, args...)
	if err != nil {
		return out
	}
	defer result.Close()
	fields := result.FieldDescriptions()
	for result.Next() {
		values, err := result.Values()
		if err != nil {
			continue
		}
		row := map[string]any{}
		for i, f := range fields {
			row[f.Name] = values[i]
		}
		out = append(out, row)
	}
	return out
}

func handleExport(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "not signed in"})
			return
		}
		ctx := r.Context()
		// Everything the platform holds about this person — never a password hash, a token or a
		// stored key's value.
		export := map[string]any{
			"exported_at": time.Now().UTC(),
			"account": rows(ctx, deps.Pool, `SELECT id, email, full_name, role, plan, credit_balance, created_at,
				email_verified_at, terms_version, terms_accepted_at FROM users WHERE id = $1`, user.ID),
			"projects": rows(ctx, deps.Pool, `SELECT id, name, description, status, created_at, updated_at, credits_spent
				FROM projects WHERE user_id = $1 ORDER BY created_at`, user.ID),
			"credit_ledger": rows(ctx, deps.Pool, `SELECT delta, reason, balance_after, created_at FROM credit_ledger
				WHERE user_id = $1 ORDER BY created_at`, user.ID),
			"model_calls": rows(ctx, deps.Pool, `SELECT * FROM model_calls WHERE user_id = $1 ORDER BY created_at DESC LIMIT 5000`, user.ID),
			"billing_orders": rows(ctx, deps.Pool, `SELECT id, provider, kind, item_id, credits, amount_minor, currency, status,
				created_at, paid_at FROM billing_orders WHERE user_id = $1 ORDER BY created_at`, user.ID),
			"workspace_memberships": rows(ctx, deps.Pool, `SELECT workspace_id, role, created_at FROM workspace_members WHERE user_id = $1`, user.ID),
			"model_keys":            rows(ctx, deps.Pool, `SELECT provider_id, created_at FROM user_provider_keys WHERE user_id = $1`, user.ID),
			"note":                  "Each project's code can be downloaded from the Studio (Download code). Stored model keys are listed by provider only.",
		}
		w.Header().Set("Content-Disposition", `attachment; filename="omnistackai-account-export.json"`)
		writeJSON(w, http.StatusOK, export)
	}
}

// ── delete ──

func handleDelete(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "not signed in"})
			return
		}
		var req struct {
			Password string `json:"password"`
		}
		if !decode(r, &req) {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request"})
			return
		}
		_, hash, err := deps.AuthStore.FindUserByEmail(r.Context(), user.Email)
		ok := false
		if err == nil {
			ok, _ = deps.Hasher.Verify(hash, req.Password)
		}
		if !ok {
			writeJSON(w, http.StatusForbidden, map[string]string{"error": "That password is not right."})
			return
		}
		ctx := r.Context()
		var shared int
		_ = deps.Pool.QueryRow(ctx, `
			SELECT count(*) FROM workspace_members m JOIN workspaces ws ON ws.id = m.workspace_id
			JOIN organizations o ON o.id = ws.org_id
			WHERE o.owner_id = $1 AND m.user_id <> $1`, user.ID).Scan(&shared)
		if shared > 0 {
			writeJSON(w, http.StatusConflict, map[string]string{"error": "You own a workspace other people use. Remove them or hand it over first, so their projects are not deleted with your account."})
			return
		}
		// A paid plan that still renews is cancelled at the provider first: a deleted account must
		// never be charged again. If that fails, nothing is deleted.
		var provider, subscriptionID string
		if err := deps.Pool.QueryRow(ctx, `SELECT provider, subscription_id FROM billing_subscriptions
			WHERE user_id = $1 AND status = 'active'`, user.ID).Scan(&provider, &subscriptionID); err == nil {
			if deps.CancelSubscription == nil || deps.CancelSubscription(ctx, provider, subscriptionID) != nil {
				writeJSON(w, http.StatusBadGateway, map[string]string{"error": "Your paid plan could not be cancelled just now, so nothing was deleted. Try again in a few minutes."})
				return
			}
		}
		var projectIDs []string
		for _, row := range rows(ctx, deps.Pool, `
			SELECT p.id::text AS id FROM projects p
			LEFT JOIN workspaces ws ON ws.id = p.workspace_id LEFT JOIN organizations o ON o.id = ws.org_id
			WHERE p.user_id = $1 OR o.owner_id = $1`, user.ID) {
			if id, ok := row["id"].(string); ok {
				projectIDs = append(projectIDs, id)
			}
		}
		tx, err := deps.Pool.Begin(ctx)
		if err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "try again"})
			return
		}
		defer func() { _ = tx.Rollback(ctx) }()
		_, err1 := tx.Exec(ctx, `DELETE FROM organizations WHERE owner_id = $1`, user.ID) // their workspaces and projects with them
		_, err2 := tx.Exec(ctx, `DELETE FROM users WHERE id = $1`, user.ID)               // sessions, ledger, keys, … cascade
		if err1 != nil || err2 != nil || tx.Commit(ctx) != nil {
			deps.logger().Error("delete account", "error", errors.Join(err1, err2))
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "The account could not be deleted. Nothing was removed."})
			return
		}
		// The code, previews and published apps live in the Studio; they go too.
		go deps.removeWorkspaces(projectIDs)
		writeJSON(w, http.StatusOK, map[string]any{"status": "deleted", "projects_removed": len(projectIDs)})
	}
}

func (d Deps) removeWorkspaces(ids []string) {
	client := d.HTTPClient
	if client == nil {
		client = &http.Client{Timeout: 5 * time.Minute}
	}
	for _, id := range ids {
		base := d.AgentEngineURL + "/api/workspaces/" + url.PathEscape(id)
		for _, step := range []struct{ method, path, body string }{
			{http.MethodPost, "/live/unpublish", `{"delete_data":true}`},
			{http.MethodDelete, "", ""},
		} {
			req, err := http.NewRequest(step.method, base+step.path, strings.NewReader(step.body))
			if err != nil {
				continue
			}
			req.Header.Set("Content-Type", "application/json")
			if resp, err := client.Do(req); err == nil {
				_ = resp.Body.Close()
			}
		}
	}
}

// ── retention ──

// Retention is how long the platform keeps what it no longer needs; the privacy policy states
// the same numbers.
type Retention struct {
	ModelCallDays int // per-call usage records (default 400: a year of statements, plus margin)
}

// RetentionFromEnv reads OMNISTACKAI_MODEL_CALL_RETENTION_DAYS.
func RetentionFromEnv() Retention {
	days := 400
	if v := os.Getenv("OMNISTACKAI_MODEL_CALL_RETENTION_DAYS"); v != "" {
		fmt.Sscanf(v, "%d", &days)
	}
	return Retention{ModelCallDays: days}
}

// Sweep removes expired sessions and links, and usage records past their retention.
func Sweep(ctx context.Context, pool *pgxpool.Pool, keep Retention) (map[string]int64, error) {
	out := map[string]int64{}
	for name, sql := range map[string]string{
		"sessions":       `DELETE FROM sessions WHERE expires_at < now()`,
		"account_tokens": `DELETE FROM account_tokens WHERE expires_at < now() - interval '7 days'`,
		"model_calls":    fmt.Sprintf(`DELETE FROM model_calls WHERE created_at < now() - interval '%d days'`, keep.ModelCallDays),
	} {
		tag, err := pool.Exec(ctx, sql)
		if err != nil {
			return out, fmt.Errorf("retention %s: %w", name, err)
		}
		out[name] = tag.RowsAffected()
	}
	return out, nil
}

// StartSweeper runs Sweep hourly until ctx ends.
func StartSweeper(ctx context.Context, pool *pgxpool.Pool, logger *slog.Logger) {
	keep := RetentionFromEnv()
	go func() {
		ticker := time.NewTicker(time.Hour)
		defer ticker.Stop()
		for {
			if removed, err := Sweep(ctx, pool, keep); err != nil {
				logger.Error("retention sweep", "error", err)
			} else {
				logger.Info("retention sweep", "removed", removed)
			}
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
			}
		}
	}()
}

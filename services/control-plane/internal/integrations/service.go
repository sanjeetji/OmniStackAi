package integrations

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

// Service runs health tests with saved credentials and remembers the answers.
type Service struct {
	Pool    *pgxpool.Pool
	Checker Checker
	// ProjectSecrets returns a project's decrypted secrets (where integration credentials live).
	ProjectSecrets func(ctx context.Context, projectID string) (map[string]string, error)
	// ConnectorConfig returns a connector's non-secret settings (the GA4 Measurement ID).
	ConnectorConfig func(ctx context.Context, projectID, provider string) (map[string]any, error)
	// UserKey returns a user's saved model key for a provider.
	UserKey func(ctx context.Context, userID, provider string) (string, error)
	Logger  *slog.Logger
}

func (s Service) logger() *slog.Logger {
	if s.Logger != nil {
		return s.Logger
	}
	return slog.Default()
}

// ErrNotConnected means the project has no saved settings for the integration.
var ErrNotConnected = errors.New("integration not connected")

// ProjectSettings gathers a project integration's saved settings.
func (s Service) ProjectSettings(ctx context.Context, projectID, integration string) (map[string]string, error) {
	settings := map[string]string{}
	if EnvFields(integration) != nil && s.ProjectSecrets != nil {
		secrets, err := s.ProjectSecrets(ctx, projectID)
		if err != nil {
			return nil, err
		}
		settings = SettingsFromSecrets(integration, secrets)
	}
	if s.ConnectorConfig != nil {
		if cfg, err := s.ConnectorConfig(ctx, projectID, integration); err == nil {
			for k, v := range cfg {
				if _, taken := settings[k]; !taken && v != nil {
					settings[k] = fmt.Sprintf("%v", v)
				}
			}
		}
	}
	if len(settings) == 0 {
		return nil, ErrNotConnected
	}
	return settings, nil
}

// CheckProject tests a project integration with its saved settings and records the answer.
func (s Service) CheckProject(ctx context.Context, projectID, integration string) (Result, error) {
	settings, err := s.ProjectSettings(ctx, projectID, integration)
	if err != nil {
		return Result{}, err
	}
	result := s.Checker.Check(ctx, integration, settings)
	s.Record(ctx, "project", projectID, result)
	return result, nil
}

// CheckUserKey tests a user's saved model key and records the answer.
func (s Service) CheckUserKey(ctx context.Context, userID, provider string) (Result, error) {
	if s.UserKey == nil {
		return Result{}, ErrNotConnected
	}
	key, err := s.UserKey(ctx, userID, provider)
	if err != nil {
		return Result{}, err
	}
	result := s.Checker.Check(ctx, "ai:"+strings.ToLower(provider), map[string]string{"api_key": key})
	s.Record(ctx, "user", userID, result)
	return result, nil
}

// Record remembers a health test's answer (the message never holds a credential).
func (s Service) Record(ctx context.Context, ownerKind, ownerID string, r Result) {
	if s.Pool == nil {
		return
	}
	if _, err := s.Pool.Exec(ctx, `
		INSERT INTO integration_checks (owner_kind, owner_id, integration, status, message, checked_at)
		VALUES ($1, $2, $3, $4, $5, $6)
		ON CONFLICT (owner_kind, owner_id, integration) DO UPDATE
		SET status = EXCLUDED.status, message = EXCLUDED.message, checked_at = EXCLUDED.checked_at`,
		ownerKind, ownerID, r.Integration, string(r.Status), r.Message, r.CheckedAt); err != nil {
		s.logger().Warn("record integration check", "integration", r.Integration, "error", err)
	}
}

// Forget drops a recorded answer (the integration was disconnected).
func (s Service) Forget(ctx context.Context, ownerKind, ownerID, integration string) {
	if s.Pool != nil {
		_, _ = s.Pool.Exec(ctx, `DELETE FROM integration_checks WHERE owner_kind = $1 AND owner_id = $2 AND integration = $3`,
			ownerKind, ownerID, integration)
	}
}

// Latest returns the recorded answers for one owner.
func (s Service) Latest(ctx context.Context, ownerKind, ownerID string) ([]Result, error) {
	out := []Result{}
	if s.Pool == nil {
		return out, nil
	}
	rows, err := s.Pool.Query(ctx, `SELECT integration, status, message, checked_at FROM integration_checks
		WHERE owner_kind = $1 AND owner_id = $2 ORDER BY integration`, ownerKind, ownerID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var r Result
		var status string
		if err := rows.Scan(&r.Integration, &status, &r.Message, &r.CheckedAt); err != nil {
			return nil, err
		}
		r.Status = Status(status)
		out = append(out, r)
	}
	return out, rows.Err()
}

// Sweep re-tests every connected integration, so a revoked or expired credential shows up
// before the app's users find it. It returns how many were tested.
func (s Service) Sweep(ctx context.Context) int {
	if s.Pool == nil {
		return 0
	}
	type item struct{ kind, owner, integration string }
	var items []item
	collect := func(kind, sql string) {
		rows, err := s.Pool.Query(ctx, sql)
		if err != nil {
			s.logger().Warn("integration sweep", "error", err)
			return
		}
		defer rows.Close()
		for rows.Next() {
			var owner, integration string
			if rows.Scan(&owner, &integration) == nil {
				items = append(items, item{kind, owner, integration})
			}
		}
	}
	collect("project", `SELECT project_id::text, provider FROM project_connectors WHERE enabled`)
	// PC-115: a project's payment keys are its secrets (R-567), so a project with them is checked.
	collect("project", `SELECT DISTINCT s.project_id::text, CASE s.key WHEN 'STRIPE_SECRET_KEY' THEN 'stripe' ELSE 'razorpay' END
		FROM project_secrets s JOIN projects p ON p.id = s.project_id
		WHERE s.key IN ('STRIPE_SECRET_KEY', 'RAZORPAY_KEY_ID') AND p.status = 'active'`)
	collect("user", `SELECT user_id::text, provider_id FROM user_provider_keys`)
	checked := 0
	for _, it := range items {
		if ctx.Err() != nil {
			break
		}
		var err error
		if it.kind == "project" {
			_, err = s.CheckProject(ctx, it.owner, it.integration)
		} else {
			_, err = s.CheckUserKey(ctx, it.owner, it.integration)
		}
		if err == nil {
			checked++
		}
		time.Sleep(200 * time.Millisecond) // gentle on the providers
	}
	return checked
}

// StartSweeper re-tests everything once a day (the first run an hour after start).
func (s Service) StartSweeper(ctx context.Context, every time.Duration) {
	go func() {
		timer := time.NewTimer(time.Hour)
		defer timer.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-timer.C:
				s.logger().Info("integration health sweep", "checked", s.Sweep(ctx))
				timer.Reset(every)
			}
		}
	}()
}

// ── HTTP ──

// Deps wires the routes.
type Deps struct {
	Service   Service
	AuthStore auth.Store
	// CanUse reports whether the user may use the project (the projects store's own check).
	CanUse func(ctx context.Context, projectID, userID string) bool
}

// Register adds the catalog and health routes.
func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /integrations", func(w http.ResponseWriter, r *http.Request) {
		if _, err := auth.RequireUser(r.Context(), deps.AuthStore, r); err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "not signed in"})
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"integrations": Catalog})
	})
	mux.HandleFunc("GET /projects/{id}/integrations/health", func(w http.ResponseWriter, r *http.Request) {
		user, ok := owned(w, r, deps)
		if !ok {
			return
		}
		project, err1 := deps.Service.Latest(r.Context(), "project", r.PathValue("id"))
		account, err2 := deps.Service.Latest(r.Context(), "user", user.ID)
		if err := errors.Join(err1, err2); err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "could not read the health tests"})
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"project": project, "account": account})
	})
	mux.HandleFunc("POST /projects/{id}/integrations/{integration}/check", func(w http.ResponseWriter, r *http.Request) {
		if _, ok := owned(w, r, deps); !ok {
			return
		}
		result, err := deps.Service.CheckProject(r.Context(), r.PathValue("id"), r.PathValue("integration"))
		if errors.Is(err, ErrNotConnected) {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "This integration is not connected to the project."})
			return
		}
		if err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "The saved settings could not be read."})
			return
		}
		writeJSON(w, http.StatusOK, result)
	})
}

func owned(w http.ResponseWriter, r *http.Request, deps Deps) (auth.User, bool) {
	user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
	if err != nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "not signed in"})
		return auth.User{}, false
	}
	if deps.CanUse == nil || !deps.CanUse(r.Context(), r.PathValue("id"), user.ID) {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "project not found"})
		return auth.User{}, false
	}
	return user, true
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

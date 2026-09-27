package main

import (
	"context"
	"errors"
	"fmt"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/account"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/admin"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/billing"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/credits"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/mail"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/studioauth"
	"log/slog"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/ai"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/analytics"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/config"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/connectors"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/deploy"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/domains"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/git"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/health"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/integrations"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/jobs"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/password"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/payments"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/secrets"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/seo"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/skills"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/templates"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/users"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/workspaces"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/migrations"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil)).With("service", "control-plane")
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if err := run(ctx, logger); err != nil {
		logger.Error("control-plane stopped", "error", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, logger *slog.Logger) error {
	runtimeConfig, err := config.Load(os.LookupEnv)
	if err != nil {
		return err
	}
	// PC-009: every request to the Studio carries the service token.
	studioauth.Install(runtimeConfig.AgentEngineURL, runtimeConfig.StudioToken)

	pool, err := pgxpool.New(context.Background(), postgresURL(runtimeConfig))
	if err != nil {
		return err
	}
	defer pool.Close()

	if err := migrations.Apply(ctx, pool); err != nil {
		return fmt.Errorf("apply migrations: %w", err)
	}

	mux := newMux(pool, runtimeConfig, logger)
	// PC-012: expired sessions and links, and usage records past retention, removed hourly.
	account.StartSweeper(ctx, pool, logger)
	// PC-013: credentials older connectors kept in plain settings move to encrypted secrets, and
	// every connected integration is re-tested daily.
	if moved, err := connectors.NewPgStore(pool).MoveCredentialsToSecrets(ctx,
		secrets.NewPgStore(pool, runtimeConfig.SecretsKey, runtimeConfig.SecretsKeyPrevious)); err != nil {
		logger.Error("move connector credentials to secrets", "error", err)
	} else if moved > 0 {
		logger.Info("moved connector credentials to encrypted secrets", "count", moved)
	}
	newIntegrationHealth(pool, runtimeConfig, logger).StartSweeper(ctx, 24*time.Hour)

	server := &http.Server{
		Addr:              runtimeConfig.HTTPAddress,
		Handler:           mux,
		ReadHeaderTimeout: runtimeConfig.ReadHeaderTimeout,
		ReadTimeout:       runtimeConfig.ReadTimeout,
		WriteTimeout:      runtimeConfig.WriteTimeout,
		IdleTimeout:       runtimeConfig.IdleTimeout,
		ErrorLog:          slog.NewLogLogger(logger.Handler(), slog.LevelError),
	}

	serverErrors := make(chan error, 1)
	go func() {
		logger.Info("control-plane listening", "address", runtimeConfig.HTTPAddress)
		serverErrors <- server.ListenAndServe()
	}()

	select {
	case <-ctx.Done():
		shutdownContext, cancel := context.WithTimeout(context.Background(), runtimeConfig.ShutdownTimeout)
		defer cancel()
		if err := server.Shutdown(shutdownContext); err != nil {
			return err
		}
		logger.Info("control-plane shutdown complete")
		return nil
	case err := <-serverErrors:
		if errors.Is(err, http.ErrServerClosed) {
			return nil
		}
		return err
	}
}

// newMux wires every package's routes onto one ServeMux. It is separate from run() so a test can
// build the real, complete route table without a database: Go's ServeMux panics when two packages
// register the same pattern, and that must fail a unit test rather than the container at startup
// (R-518). Stores only hold the pool; nothing here touches the database.
func newMux(pool *pgxpool.Pool, runtimeConfig config.Config, logger *slog.Logger) *http.ServeMux {
	userStore := users.New(pool)
	projectStore := projects.New(pool)
	aiStore := ai.NewPgStore(pool, runtimeConfig.SecretsKey, runtimeConfig.SecretsKeyPrevious)
	// PC-013: health tests of every connected integration, with the saved credentials.
	integrationHealth := newIntegrationHealth(pool, runtimeConfig, logger)

	mux := http.NewServeMux()
	health.Register(mux, pool, runtimeConfig.DatabasePingTimeout)
	// PC-012: verification, password reset, export, deletion and retention for platform accounts.
	termsVersion := strings.TrimSpace(os.Getenv("OMNISTACKAI_TERMS_VERSION"))
	if termsVersion == "" {
		termsVersion = "2026-09-27"
	}
	stripe, razorpay := billing.StripeFromEnv(), billing.RazorpayFromEnv()
	accountDeps := account.Deps{
		Pool:           pool,
		AuthStore:      userStore,
		Hasher:         passwordHasher{},
		Mailer:         mail.FromEnv(logger),
		PublicURL:      billing.PublicURLFromEnv(),
		TermsVersion:   termsVersion,
		AgentEngineURL: runtimeConfig.AgentEngineURL,
		Logger:         logger,
		CancelSubscription: func(ctx context.Context, provider, subscriptionID string) error {
			return billing.CancelSubscription(ctx, stripe, razorpay, provider, subscriptionID)
		},
	}
	account.Register(mux, accountDeps)
	auth.Register(mux, auth.Deps{
		Store:         userStore,
		Hasher:        passwordHasher{},
		SessionTTL:    runtimeConfig.SessionTTL,
		SignupCredits: runtimeConfig.SignupCreditGrant,
		Logger:        logger,
		TermsVersion:  termsVersion,
		OnRegistered:  accountDeps.OnRegistered,
	})
	ai.Register(mux, ai.Deps{
		AuthStore:      userStore,
		AIStore:        aiStore,
		AgentEngineURL: runtimeConfig.AgentEngineURL,
		Logger:         logger,
		KeyCheck: func(ctx context.Context, userID, providerID, key string) integrations.Result {
			result := integrationHealth.Checker.Check(ctx, "ai:"+strings.ToLower(providerID), map[string]string{"api_key": key})
			integrationHealth.Record(ctx, "user", userID, result)
			return result
		},
		KeyChanged: func(ctx context.Context, userID, providerID string) {
			integrationHealth.Forget(ctx, "user", userID, "ai:"+strings.ToLower(providerID))
		},
	})
	integrations.Register(mux, integrations.Deps{
		Service:   integrationHealth,
		AuthStore: userStore,
		CanUse: func(ctx context.Context, projectID, userID string) bool {
			_, err := projectStore.GetProject(ctx, projectID, userID)
			return err == nil
		},
	})
	// PC-010: no paid model work at zero credits; per-task budgets; per-user and platform caps.
	creditGuard := credits.FromEnv(runtimeConfig.CreditsPerUSD, projectStore)
	creditGuard.PausedNow = func(ctx context.Context) bool {
		paused, _ := admin.PaidModelWorkPaused(ctx, pool)
		return paused
	}
	jobs.Register(mux, jobs.Deps{
		AuthStore:      userStore,
		CreditStore:    userStore,
		AIStore:        aiStore,
		AgentEngineURL: runtimeConfig.AgentEngineURL,
		CreditsPerUSD:  runtimeConfig.CreditsPerUSD,
		Logger:         logger,
		CreditGuard:    &creditGuard,
	})
	skillsStore := skills.NewPgStore(pool)
	skills.Register(mux, skills.Deps{
		AuthStore:  userStore,
		SkillStore: skillsStore,
		Logger:     logger,
	})
	secretsStore := secrets.NewPgStore(pool, runtimeConfig.SecretsKey, runtimeConfig.SecretsKeyPrevious)
	secrets.Register(mux, secrets.Deps{
		SecretsStore: secretsStore,
		AuthStore:    userStore,
		Logger:       logger,
	})
	workspacesStore := workspaces.New(pool)
	workspaces.Register(mux, workspaces.Deps{
		AuthStore:      userStore,
		WorkspaceStore: workspacesStore,
		Logger:         logger,
	})
	projects.Register(mux, projects.Deps{
		AuthStore:      userStore,
		ProjectStore:   projectStore,
		SkillStore:     skillsStore,
		SecretsStore:   secretsStore,
		AIStore:        aiStore,
		AgentEngineURL: runtimeConfig.AgentEngineURL,
		CreditsPerUSD:  runtimeConfig.CreditsPerUSD,
		CreditGuard:    &creditGuard,
		Logger:         logger,
	})
	// PC-011: the super_admin console's API.
	admin.Register(mux, admin.Deps{AuthStore: userStore, Pool: pool, Logger: logger})
	// PC-011: plans, credit top-ups and plan purchases (Stripe, Razorpay; keys at PC-070).
	billing.Register(mux, billing.Deps{
		AuthStore: userStore,
		Store:     billing.NewPgStore(pool),
		Stripe:    stripe,
		Razorpay:  razorpay,
		CountProjects: func(ctx context.Context, userID string) int {
			list, err := projectStore.ListProjects(ctx, userID, "active", 1000)
			if err != nil {
				return 0
			}
			owned := 0
			for _, p := range list {
				if p.UserID == userID {
					owned++
				}
			}
			return owned
		},
		PublicURL: billing.PublicURLFromEnv(),
		Logger:    logger,
	})
	// Template marketplace (Phase T, T-1 / R-519)
	templates.Register(mux, templates.Deps{
		AuthStore:      userStore,
		ProjectStore:   projectStore,
		TemplateStore:  templates.New(pool),
		AgentEngineURL: runtimeConfig.AgentEngineURL,
		Logger:         logger,
	})
	gitStore := git.NewPgStore(pool, runtimeConfig.SecretsKey)
	git.Register(mux, git.Deps{
		AuthStore:             userStore,
		GitStore:              gitStore,
		ProjectStore:          projectStore,
		AgentEngineURL:        runtimeConfig.AgentEngineURL,
		GitHubAppID:           runtimeConfig.GitHubAppID,
		GitHubAppClientID:     runtimeConfig.GitHubAppClientID,
		GitHubAppClientSecret: runtimeConfig.GitHubAppClientSecret,
		GitHubAppPrivateKey:   runtimeConfig.GitHubAppPrivateKey,
		Logger:                logger,
	})
	seoStore := seo.NewPgStore(pool)
	seo.Register(mux, seo.Deps{
		SEOStore:       seoStore,
		AIStore:        aiStore,
		AuthStore:      userStore,
		AgentEngineURL: runtimeConfig.AgentEngineURL,
		Logger:         logger,
	})
	deployStore := deploy.NewPgStore(pool, runtimeConfig.SecretsKey, runtimeConfig.SecretsKeyPrevious)
	deploy.Register(mux, deploy.Deps{
		AuthStore:      userStore,
		DeployStore:    deployStore,
		ProjectStore:   projectStore,
		GitStore:       gitStore,
		SecretsStore:   secretsStore,
		AgentEngineURL: runtimeConfig.AgentEngineURL,
		Logger:         logger,
	})
	domainStore := domains.NewPgStore(pool)
	domains.Register(mux, domains.Deps{
		AuthStore:    userStore,
		ProjectStore: projectStore,
		DomainStore:  domainStore,
		DeployStore:  deployStore,
		Logger:       logger,
	})
	connectorStore := connectors.NewPgStore(pool)
	connectors.Register(mux, connectors.Deps{
		AuthStore:      userStore,
		ProjectStore:   projectStore,
		ConnectorStore: connectorStore,
		AgentEngineURL: runtimeConfig.AgentEngineURL,
		Logger:         logger,
		Secrets:        secretsStore,
		Health:         integrationHealth,
	})
	paymentsStore := payments.NewPgStore(pool)
	payments.Register(mux, payments.Deps{
		AuthStore:      userStore,
		ProjectStore:   projectStore,
		PaymentsStore:  paymentsStore,
		SecretsStore:   secretsStore,
		AgentEngineURL: runtimeConfig.AgentEngineURL,
		Logger:         logger,
	})
	analyticsStore := analytics.NewPgStore(pool)
	ga4Client := analytics.NewGA4Client(nil)
	analytics.Register(mux, analytics.Deps{
		AuthStore:      userStore,
		ProjectStore:   projectStore,
		AnalyticsStore: analyticsStore,
		ConnectorStore: connectorStore,
		DeployStore:    deployStore,
		GA4Client:      ga4Client,
		Logger:         logger,
	})
	return mux
}

// passwordHasher adapts the internal/password package's functions to the auth.Hasher interface,
// so internal/auth stays decoupled from the specific hashing implementation.
type passwordHasher struct{}

func (passwordHasher) Hash(plain string) (string, error) {
	return password.Hash(plain)
}

func (passwordHasher) Verify(encoded, plain string) (bool, error) {
	return password.Verify(encoded, plain)
}

func postgresURL(runtimeConfig config.Config) string {
	databaseURL := &url.URL{
		Scheme: "postgres",
		User:   url.UserPassword(runtimeConfig.PostgresUser, runtimeConfig.PostgresPassword),
		Host:   net.JoinHostPort(runtimeConfig.PostgresHost, strconv.Itoa(int(runtimeConfig.PostgresPort))),
		Path:   runtimeConfig.PostgresDatabase,
	}
	query := databaseURL.Query()
	query.Set("sslmode", "disable")
	databaseURL.RawQuery = query.Encode()
	return databaseURL.String()
}

// newIntegrationHealth builds the integration health tests (PC-013) over the stores that hold the
// credentials. A mail server on a private address may be tested only in local development.
func newIntegrationHealth(pool *pgxpool.Pool, runtimeConfig config.Config, logger *slog.Logger) integrations.Service {
	secretsStore := secrets.NewPgStore(pool, runtimeConfig.SecretsKey, runtimeConfig.SecretsKeyPrevious)
	aiStore := ai.NewPgStore(pool, runtimeConfig.SecretsKey, runtimeConfig.SecretsKeyPrevious)
	connectorStore := connectors.NewPgStore(pool)
	return integrations.Service{
		Pool:    pool,
		Checker: integrations.Checker{AllowPrivate: os.Getenv("OMNISTACKAI_DEV_MODE") == "1"},
		ProjectSecrets: func(ctx context.Context, projectID string) (map[string]string, error) {
			if !secretsStore.IsAvailable() {
				return map[string]string{}, nil
			}
			return secretsStore.ForProject(ctx, projectID)
		},
		ConnectorConfig: func(ctx context.Context, projectID, provider string) (map[string]any, error) {
			pc, err := connectorStore.GetProjectConnector(ctx, projectID, provider)
			return pc.Config, err
		},
		UserKey: func(ctx context.Context, userID, provider string) (string, error) {
			key, _, err := aiStore.GetUserKey(ctx, userID, provider)
			return key, err
		},
		Logger: logger,
	}
}

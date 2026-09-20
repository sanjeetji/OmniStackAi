package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strconv"
	"syscall"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/ai"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/config"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/connectors"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/deploy"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/domains"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/git"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/health"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/jobs"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/password"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/secrets"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/seo"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/skills"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/users"
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

	pool, err := pgxpool.New(context.Background(), postgresURL(runtimeConfig))
	if err != nil {
		return err
	}
	defer pool.Close()

	if err := migrations.Apply(ctx, pool); err != nil {
		return fmt.Errorf("apply migrations: %w", err)
	}

	userStore := users.New(pool)
	projectStore := projects.New(pool)
	aiStore := ai.NewPgStore(pool, runtimeConfig.SecretsKey, runtimeConfig.SecretsKeyPrevious)

	mux := http.NewServeMux()
	health.Register(mux, pool, runtimeConfig.DatabasePingTimeout)
	auth.Register(mux, auth.Deps{
		Store:         userStore,
		Hasher:        passwordHasher{},
		SessionTTL:    runtimeConfig.SessionTTL,
		SignupCredits: runtimeConfig.SignupCreditGrant,
		Logger:        logger,
	})
	ai.Register(mux, ai.Deps{
		AuthStore:      userStore,
		AIStore:        aiStore,
		AgentEngineURL: runtimeConfig.AgentEngineURL,
		Logger:         logger,
	})
	jobs.Register(mux, jobs.Deps{
		AuthStore:      userStore,
		CreditStore:    userStore,
		AIStore:        aiStore,
		AgentEngineURL: runtimeConfig.AgentEngineURL,
		CreditsPerUSD:  runtimeConfig.CreditsPerUSD,
		Logger:         logger,
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
	projects.Register(mux, projects.Deps{
		AuthStore:      userStore,
		ProjectStore:   projectStore,
		SkillStore:     skillsStore,
		SecretsStore:   secretsStore,
		AIStore:        aiStore,
		AgentEngineURL: runtimeConfig.AgentEngineURL,
		CreditsPerUSD:  runtimeConfig.CreditsPerUSD,
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
	})

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

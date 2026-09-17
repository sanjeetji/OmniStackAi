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

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/config"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/health"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/password"
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

	mux := http.NewServeMux()
	health.Register(mux, pool, runtimeConfig.DatabasePingTimeout)
	auth.Register(mux, auth.Deps{
		Store:         users.New(pool),
		Hasher:        passwordHasher{},
		SessionTTL:    runtimeConfig.SessionTTL,
		SignupCredits: runtimeConfig.SignupCreditGrant,
		Logger:        logger,
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

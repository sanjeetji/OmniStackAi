package main

import (
	"context"
	"errors"
	"log/slog"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strconv"
	"syscall"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/config"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/health"
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

	server := &http.Server{
		Addr:              runtimeConfig.HTTPAddress,
		Handler:           health.NewHandler(pool, runtimeConfig.DatabasePingTimeout),
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

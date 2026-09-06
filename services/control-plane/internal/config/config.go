package config

import (
	"errors"
	"fmt"
	"net"
	"strconv"
	"strings"
	"time"
)

const (
	defaultHTTPAddress         = "127.0.0.1:8080"
	defaultPostgresHost        = "127.0.0.1"
	defaultPostgresPort        = "5432"
	defaultReadHeaderTimeout   = "5s"
	defaultReadTimeout         = "15s"
	defaultWriteTimeout        = "15s"
	defaultIdleTimeout         = "60s"
	defaultShutdownTimeout     = "10s"
	defaultDatabasePingTimeout = "2s"
)

// Config contains the complete Stage 0 control-plane runtime configuration.
type Config struct {
	HTTPAddress         string
	PostgresHost        string
	PostgresPort        uint16
	PostgresDatabase    string
	PostgresUser        string
	PostgresPassword    string
	ReadHeaderTimeout   time.Duration
	ReadTimeout         time.Duration
	WriteTimeout        time.Duration
	IdleTimeout         time.Duration
	ShutdownTimeout     time.Duration
	DatabasePingTimeout time.Duration
}

// Lookup matches os.LookupEnv and makes configuration loading deterministic in tests.
type Lookup func(string) (string, bool)

// Load reads, validates, and types all environment configuration.
func Load(lookup Lookup) (Config, error) {
	if lookup == nil {
		return Config{}, errors.New("environment lookup is required")
	}

	httpAddress := valueOrDefault(lookup, "OMNISTACKAI_CONTROL_PLANE_ADDRESS", defaultHTTPAddress)
	if err := validateAddress(httpAddress); err != nil {
		return Config{}, fmt.Errorf("OMNISTACKAI_CONTROL_PLANE_ADDRESS: %w", err)
	}

	postgresPort, err := parsePort(valueOrDefault(lookup, "OMNISTACKAI_POSTGRES_PORT", defaultPostgresPort))
	if err != nil {
		return Config{}, fmt.Errorf("OMNISTACKAI_POSTGRES_PORT: %w", err)
	}

	postgresDatabase, err := required(lookup, "OMNISTACKAI_POSTGRES_DB")
	if err != nil {
		return Config{}, err
	}
	postgresUser, err := required(lookup, "OMNISTACKAI_POSTGRES_USER")
	if err != nil {
		return Config{}, err
	}
	postgresPassword, err := required(lookup, "OMNISTACKAI_POSTGRES_PASSWORD")
	if err != nil {
		return Config{}, err
	}

	config := Config{
		HTTPAddress:      httpAddress,
		PostgresHost:     valueOrDefault(lookup, "OMNISTACKAI_POSTGRES_HOST", defaultPostgresHost),
		PostgresPort:     postgresPort,
		PostgresDatabase: postgresDatabase,
		PostgresUser:     postgresUser,
		PostgresPassword: postgresPassword,
	}

	durations := []struct {
		name         string
		defaultValue string
		destination  *time.Duration
	}{
		{"OMNISTACKAI_HTTP_READ_HEADER_TIMEOUT", defaultReadHeaderTimeout, &config.ReadHeaderTimeout},
		{"OMNISTACKAI_HTTP_READ_TIMEOUT", defaultReadTimeout, &config.ReadTimeout},
		{"OMNISTACKAI_HTTP_WRITE_TIMEOUT", defaultWriteTimeout, &config.WriteTimeout},
		{"OMNISTACKAI_HTTP_IDLE_TIMEOUT", defaultIdleTimeout, &config.IdleTimeout},
		{"OMNISTACKAI_SHUTDOWN_TIMEOUT", defaultShutdownTimeout, &config.ShutdownTimeout},
		{"OMNISTACKAI_DATABASE_PING_TIMEOUT", defaultDatabasePingTimeout, &config.DatabasePingTimeout},
	}
	for _, item := range durations {
		value, parseErr := parsePositiveDuration(valueOrDefault(lookup, item.name, item.defaultValue))
		if parseErr != nil {
			return Config{}, fmt.Errorf("%s: %w", item.name, parseErr)
		}
		*item.destination = value
	}

	return config, nil
}

func required(lookup Lookup, name string) (string, error) {
	value, ok := lookup(name)
	value = strings.TrimSpace(value)
	if !ok || value == "" {
		return "", fmt.Errorf("%s is required", name)
	}
	return value, nil
}

func valueOrDefault(lookup Lookup, name, defaultValue string) string {
	value, ok := lookup(name)
	value = strings.TrimSpace(value)
	if !ok || value == "" {
		return defaultValue
	}
	return value
}

func validateAddress(address string) error {
	host, port, err := net.SplitHostPort(address)
	if err != nil {
		return fmt.Errorf("must be host:port: %w", err)
	}
	if strings.TrimSpace(host) == "" {
		return errors.New("host is required")
	}
	_, err = parsePort(port)
	return err
}

func parsePort(value string) (uint16, error) {
	port, err := strconv.ParseUint(value, 10, 16)
	if err != nil || port == 0 {
		return 0, fmt.Errorf("must be an integer from 1 to 65535")
	}
	return uint16(port), nil
}

func parsePositiveDuration(value string) (time.Duration, error) {
	duration, err := time.ParseDuration(value)
	if err != nil {
		return 0, fmt.Errorf("invalid duration %q: %w", value, err)
	}
	if duration <= 0 {
		return 0, errors.New("duration must be positive")
	}
	return duration, nil
}

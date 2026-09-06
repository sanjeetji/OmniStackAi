package config

import (
	"strings"
	"testing"
	"time"
)

func TestLoadUsesTypedDefaults(t *testing.T) {
	environment := map[string]string{
		"OMNISTACKAI_POSTGRES_DB":       "omnistackai",
		"OMNISTACKAI_POSTGRES_USER":     "omnistackai",
		"OMNISTACKAI_POSTGRES_PASSWORD": "local-only",
	}

	config, err := Load(mapLookup(environment))
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}
	if config.HTTPAddress != "127.0.0.1:8080" {
		t.Fatalf("HTTPAddress = %q", config.HTTPAddress)
	}
	if config.PostgresHost != "127.0.0.1" || config.PostgresPort != 5432 {
		t.Fatalf("database address = %s:%d", config.PostgresHost, config.PostgresPort)
	}
	if config.DatabasePingTimeout != 2*time.Second {
		t.Fatalf("DatabasePingTimeout = %s", config.DatabasePingTimeout)
	}
}

func TestLoadRejectsInvalidConfiguration(t *testing.T) {
	base := map[string]string{
		"OMNISTACKAI_POSTGRES_DB":       "omnistackai",
		"OMNISTACKAI_POSTGRES_USER":     "omnistackai",
		"OMNISTACKAI_POSTGRES_PASSWORD": "local-only",
	}

	tests := []struct {
		name      string
		key       string
		value     string
		wantError string
	}{
		{"missing password", "OMNISTACKAI_POSTGRES_PASSWORD", "", "is required"},
		{"bad address", "OMNISTACKAI_CONTROL_PLANE_ADDRESS", "localhost", "host:port"},
		{"bad port", "OMNISTACKAI_POSTGRES_PORT", "70000", "1 to 65535"},
		{"bad duration", "OMNISTACKAI_DATABASE_PING_TIMEOUT", "soon", "invalid duration"},
		{"zero duration", "OMNISTACKAI_SHUTDOWN_TIMEOUT", "0s", "must be positive"},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			environment := clone(base)
			environment[test.key] = test.value
			_, err := Load(mapLookup(environment))
			if err == nil || !strings.Contains(err.Error(), test.wantError) {
				t.Fatalf("Load() error = %v, want substring %q", err, test.wantError)
			}
		})
	}
}

func mapLookup(values map[string]string) Lookup {
	return func(name string) (string, bool) {
		value, ok := values[name]
		return value, ok
	}
}

func clone(source map[string]string) map[string]string {
	result := make(map[string]string, len(source))
	for key, value := range source {
		result[key] = value
	}
	return result
}

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
	if config.SessionTTL != 720*time.Hour {
		t.Fatalf("SessionTTL = %s, want 720h", config.SessionTTL)
	}
	if config.SignupCreditGrant != 100 {
		t.Fatalf("SignupCreditGrant = %d, want 100", config.SignupCreditGrant)
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
		{"bad session ttl", "OMNISTACKAI_SESSION_TTL", "forever", "invalid duration"},
		{"negative signup credit grant", "OMNISTACKAI_SIGNUP_CREDIT_GRANT", "-1", "non-negative integer"},
		{"non-numeric signup credit grant", "OMNISTACKAI_SIGNUP_CREDIT_GRANT", "many", "non-negative integer"},
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

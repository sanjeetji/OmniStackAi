package jobs

import (
	"testing"
	"time"
)

// PC-118: the job build reads the same budget setting as the project build.
func TestBuildBudgetFromEnv(t *testing.T) {
	t.Setenv("OMNISTACKAI_AGENT_CALL_TIMEOUT", "30m")
	if got := durationFromEnv("OMNISTACKAI_AGENT_CALL_TIMEOUT", 5*time.Minute); got != 30*time.Minute {
		t.Fatalf("budget = %v, want 30m", got)
	}
	for _, raw := range []string{"", "soon", "-1m", "0s"} {
		t.Setenv("OMNISTACKAI_AGENT_CALL_TIMEOUT", raw)
		if got := durationFromEnv("OMNISTACKAI_AGENT_CALL_TIMEOUT", 5*time.Minute); got != 5*time.Minute {
			t.Fatalf("%q: budget = %v, want the 5m default", raw, got)
		}
	}
}

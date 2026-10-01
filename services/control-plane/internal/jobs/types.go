// Package jobs proxies "build this app" requests from an authenticated caller to the agent-engine's
// Studio HTTP API, then debits the caller's credit balance by the real cost the agent-engine
// reports (R-472). Billing enforcement lives entirely here - the agent-engine itself stays
// credit-agnostic (R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md: "agents depend on provider
// interfaces, not billing logic").
package jobs

import (
	"context"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/credits"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/ai"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

// CreditStore is the narrow persistence capability this package needs: charge a user for one real
// build. The concrete *users.Store already satisfies this by structural typing - internal/jobs
// never imports internal/users, the same "accept an interface, wire the real implementation at the
// edge" boundary internal/auth already draws around its own Store.
type CreditStore interface {
	DebitCredits(ctx context.Context, userID string, requested int64, reason string) (charged int64, newBalance int64, err error)
}

// Deps are the dependencies Register needs.
type Deps struct {
	// AuthStore resolves the authenticated caller - auth.RequireUser's own dependency, reused here
	// so this package never re-implements bearer-token/session lookup.
	AuthStore      auth.Store
	CreditStore    CreditStore
	AIStore        ai.Store
	AgentEngineURL string
	// CreditsPerUSD converts a real dollar cost into a credit charge: credits = cost_usd * CreditsPerUSD.
	CreditsPerUSD float64
	// HTTPClient makes the outbound call to the agent-engine. Defaults to a client with a generous
	// fixed timeout (defaultBuildTimeout) when nil - app generation is a slow, multi-model-call
	// operation, not a quick API round trip.
	HTTPClient *http.Client
	Logger     *slog.Logger
	// CreditGuard (PC-010): zero-balance refusal, per-task budget, caps. Nil disables it.
	CreditGuard *credits.Guard
}

func (d Deps) httpClient() *http.Client {
	if d.HTTPClient != nil {
		return d.HTTPClient
	}
	return &http.Client{Timeout: defaultBuildTimeout}
}

func (d Deps) logger() *slog.Logger {
	if d.Logger == nil {
		return slog.Default()
	}
	return d.Logger
}

// defaultBuildTimeout is the job build's budget. PC-118: it was a fixed five minutes while the
// project build (R-530) read OMNISTACKAI_AGENT_CALL_TIMEOUT, so a multi-app build that the project
// path would have finished failed here with a 502. Both read the same setting now.
var defaultBuildTimeout = durationFromEnv("OMNISTACKAI_AGENT_CALL_TIMEOUT", 5*time.Minute)

func durationFromEnv(name string, fallback time.Duration) time.Duration {
	if raw := strings.TrimSpace(os.Getenv(name)); raw != "" {
		if parsed, err := time.ParseDuration(raw); err == nil && parsed > 0 {
			return parsed
		}
	}
	return fallback
}

// defaultPreviewTimeout extends the write deadline for the one preview route that can trigger a
// real cold start (POST /jobs/build/{id}/preview, via StudioPreviewManager.replace()) - sized just
// above the agent-engine's own real preview-readiness wait (localrun/run.py's
// health_timeout_seconds default of 45s), not the much larger defaultBuildTimeout, which is
// oversized for this.
const defaultPreviewTimeout = 60 * time.Second

// defaultProblemsTimeout extends the write deadline for POST /jobs/build/{id}/problems, which runs
// a real `tsc --noEmit` on the generated app - a local compile, not a model call, but one that can
// still take real time on a larger app. Sized well above ordinary single-app compile times observed
// in this codebase's own generated fixtures, well below verify/compile.py's own much larger internal
// default (600s), which exists for pathological cases this route does not need to wait out.
const defaultProblemsTimeout = 90 * time.Second

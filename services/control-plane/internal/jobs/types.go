// Package jobs proxies "build this app" requests from an authenticated caller to the agent-engine's
// Studio HTTP API, then debits the caller's credit balance by the real cost the agent-engine
// reports (R-472). Billing enforcement lives entirely here - the agent-engine itself stays
// credit-agnostic (R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md: "agents depend on provider
// interfaces, not billing logic").
package jobs

import (
	"context"
	"log/slog"
	"net/http"
	"time"

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
	AgentEngineURL string
	// CreditsPerUSD converts a real dollar cost into a credit charge: credits = cost_usd * CreditsPerUSD.
	CreditsPerUSD float64
	// HTTPClient makes the outbound call to the agent-engine. Defaults to a client with a generous
	// fixed timeout (defaultBuildTimeout) when nil - app generation is a slow, multi-model-call
	// operation, not a quick API round trip.
	HTTPClient *http.Client
	Logger     *slog.Logger
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

const defaultBuildTimeout = 5 * time.Minute

// defaultPreviewTimeout extends the write deadline for the one preview route that can trigger a
// real cold start (POST /jobs/build/{id}/preview, via StudioPreviewManager.replace()) - sized just
// above the agent-engine's own real preview-readiness wait (localrun/run.py's
// health_timeout_seconds default of 45s), not the much larger defaultBuildTimeout, which is
// oversized for this.
const defaultPreviewTimeout = 60 * time.Second

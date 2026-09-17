package jobs

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"math"
	"net/http"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

// Register mounts POST /jobs/build onto mux.
func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("POST /jobs/build", handleBuild(deps))
}

// handleBuild authenticates the caller, forwards their JSON body verbatim to the agent-engine's
// own /api/build, and - only on a successful (2xx) build that reports real usage - debits the
// caller's credit balance by the real cost incurred, returning the agent-engine's response
// augmented with credits_spent/credit_balance. It never inspects the build's shape (plain prompt,
// Solution Pack, Ecosystem) beyond the optional top-level "usage" object, so it needs no changes
// as the agent-engine's build kinds evolve.
func handleBuild(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// A build proxies a slow, multi-model-call upstream operation that can easily run past the
		// control-plane server's global WriteTimeout (tuned short for every other, fast route like
		// /auth/*). Extending the write deadline for just this response - rather than raising the
		// server-wide timeout - keeps that slow-loris protection intact everywhere else.
		if controller := http.NewResponseController(w); controller != nil {
			_ = controller.SetWriteDeadline(time.Now().Add(defaultBuildTimeout))
		}

		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			if errors.Is(err, auth.ErrUnauthenticated) {
				writeError(w, http.StatusUnauthorized, "missing bearer token or session not found or expired")
				return
			}
			deps.logger().Error("resolve authenticated user", "error", err)
			writeError(w, http.StatusInternalServerError, "could not authenticate request")
			return
		}

		body, err := io.ReadAll(r.Body)
		_ = r.Body.Close()
		if err != nil {
			writeError(w, http.StatusBadRequest, "could not read request body")
			return
		}

		upstreamRequest, err := http.NewRequestWithContext(
			r.Context(), http.MethodPost, deps.AgentEngineURL+"/api/build", bytes.NewReader(body),
		)
		if err != nil {
			deps.logger().Error("build agent-engine request", "error", err)
			writeError(w, http.StatusInternalServerError, "could not build upstream request")
			return
		}
		upstreamRequest.Header.Set("Content-Type", "application/json")

		upstreamResponse, err := deps.httpClient().Do(upstreamRequest)
		if err != nil {
			deps.logger().Error("call agent-engine", "error", err)
			writeError(w, http.StatusBadGateway, "could not reach the build service")
			return
		}
		defer func() { _ = upstreamResponse.Body.Close() }()

		upstreamBody, err := io.ReadAll(upstreamResponse.Body)
		if err != nil {
			deps.logger().Error("read agent-engine response", "error", err)
			writeError(w, http.StatusBadGateway, "could not read build service response")
			return
		}

		if upstreamResponse.StatusCode < 200 || upstreamResponse.StatusCode >= 300 {
			// The build itself failed or was rejected upstream - proxy that outcome through
			// unchanged rather than swallowing it. No credits are charged for a non-2xx response.
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(upstreamResponse.StatusCode)
			_, _ = w.Write(upstreamBody)
			return
		}

		var payload map[string]any
		if err := json.Unmarshal(upstreamBody, &payload); err != nil {
			deps.logger().Error("decode agent-engine response", "error", err)
			writeError(w, http.StatusBadGateway, "build service returned a malformed response")
			return
		}

		requestedCredits := creditsForUsage(payload["usage"], deps.CreditsPerUSD)
		charged, newBalance := int64(0), user.CreditBalance
		if requestedCredits > 0 {
			charged, newBalance, err = deps.CreditStore.DebitCredits(r.Context(), user.ID, requestedCredits, "job:build")
			if err != nil {
				// The build already happened and cost real money upstream; there is no way to
				// undo it from here. Logging loudly (rather than silently dropping the charge) is
				// the honest v1 answer - reconciling a missed debit is a named follow-up, not
				// silently swallowed.
				deps.logger().Error("debit credits for a completed build",
					"error", err, "user_id", user.ID, "requested_credits", requestedCredits)
				writeError(w, http.StatusInternalServerError, "build succeeded but credit accounting failed")
				return
			}
		}

		payload["credits_spent"] = charged
		payload["credit_balance"] = newBalance
		writeJSON(w, http.StatusOK, payload)
	}
}

// creditsForUsage extracts cost_micros_usd from a build response's optional "usage" object (as
// produced by studio/live_serve.py's _usage_summary_to_dict, R-472) and converts it to a whole
// number of credits. Any missing or malformed usage is treated as zero cost - a build with no
// usage key (e.g. today's Solution Pack/Ecosystem paths, which R-472 deliberately does not thread
// a ledger through yet) charges nothing rather than guessing.
func creditsForUsage(usage any, creditsPerUSD float64) int64 {
	usageObject, ok := usage.(map[string]any)
	if !ok {
		return 0
	}
	costMicros, ok := usageObject["cost_micros_usd"].(float64) // encoding/json decodes JSON numbers as float64
	if !ok || costMicros <= 0 {
		return 0
	}
	return int64(math.Round(costMicros * creditsPerUSD / 1_000_000))
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

type errorResponse struct {
	Error string `json:"error"`
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, errorResponse{Error: message})
}

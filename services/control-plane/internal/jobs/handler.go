package jobs

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"math"
	"net/http"
	"net/url"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

// Register mounts the Job API: building an app, following up with an edit, read-only browsing of
// what a build produced, and controlling the trusted-local live preview.
func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("POST /jobs/build", handleBuild(deps))
	mux.HandleFunc("POST /jobs/build/{id}/edit", handleBuildEdit(deps))
	mux.HandleFunc("GET /jobs/build/{id}/turns", handleBuildTurns(deps))
	mux.HandleFunc("GET /jobs/build/{id}/files", handleBuildFiles(deps))
	mux.HandleFunc("GET /jobs/build/{id}/file", handleBuildFile(deps))
	mux.HandleFunc("GET /jobs/preview", handlePreviewStatus(deps))
	mux.HandleFunc("POST /jobs/preview/stop", handlePreviewStop(deps))
	mux.HandleFunc("POST /jobs/preview/restart", handlePreviewRestart(deps))
	mux.HandleFunc("POST /jobs/build/{id}/preview", handleBuildPreview(deps))
}

// handleBuild authenticates the caller and forwards their JSON body verbatim to the agent-engine's
// own /api/build via proxyAndDebit. It never inspects the build's shape (plain prompt, Solution
// Pack, Ecosystem) beyond the optional top-level "usage" object, so it needs no changes as the
// agent-engine's build kinds evolve.
func handleBuild(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if controller := http.NewResponseController(w); controller != nil {
			_ = controller.SetWriteDeadline(time.Now().Add(defaultBuildTimeout))
		}

		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		body, err := io.ReadAll(r.Body)
		_ = r.Body.Close()
		if err != nil {
			writeError(w, http.StatusBadRequest, "could not read request body")
			return
		}

		proxyAndDebit(w, r, deps, user, deps.AgentEngineURL+"/api/build", body, "job:build")
	}
}

// handleBuildEdit authenticates the caller and forwards their JSON body verbatim to the
// agent-engine's existing POST /api/build/{id}/edit (R-468) via proxyAndDebit - same auth,
// write-deadline, and debit shape as handleBuild, since an edit is just as slow and just as real a
// model call as the initial build. A no-op edit (the delta call still happened even if it produced
// no file changes) still debits real credits, by design - creditsForUsage only cares about the
// reported cost, not whether files changed.
func handleBuildEdit(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if controller := http.NewResponseController(w); controller != nil {
			_ = controller.SetWriteDeadline(time.Now().Add(defaultBuildTimeout))
		}

		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeAuthError(w, deps, err)
			return
		}

		id := r.PathValue("id")
		if id == "" {
			writeError(w, http.StatusBadRequest, "build id is required")
			return
		}

		body, err := io.ReadAll(r.Body)
		_ = r.Body.Close()
		if err != nil {
			writeError(w, http.StatusBadRequest, "could not read request body")
			return
		}

		target := deps.AgentEngineURL + "/api/build/" + url.PathEscape(id) + "/edit"
		proxyAndDebit(w, r, deps, user, target, body, "job:edit")
	}
}

// handleBuildTurns proxies GET /api/build/{id}/turns (R-468) verbatim, same auth/no-debit shape as
// handleBuildFiles - reading chat history isn't a billable model call. An unknown build id returns
// an empty {"turns": []} from the agent-engine itself, never an error.
func handleBuildTurns(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if _, err := auth.RequireUser(r.Context(), deps.AuthStore, r); err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if id == "" {
			writeError(w, http.StatusBadRequest, "build id is required")
			return
		}
		proxyGet(w, r, deps, deps.AgentEngineURL+"/api/build/"+url.PathEscape(id)+"/turns")
	}
}

// proxyAndDebit forwards body via POST to targetURL and - only on a successful (2xx) response that
// reports real usage - debits the caller's credit balance by the real cost incurred (reason is the
// credit_ledger entry's reason string), returning the upstream response augmented with
// credits_spent/credit_balance. Shared by handleBuild and handleBuildEdit so the "forward, decode,
// debit, inject" shape lives in exactly one place.
func proxyAndDebit(w http.ResponseWriter, r *http.Request, deps Deps, user auth.User, targetURL string, body []byte, reason string) {
	upstreamRequest, err := http.NewRequestWithContext(r.Context(), http.MethodPost, targetURL, bytes.NewReader(body))
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
		// The call itself failed or was rejected upstream - proxy that outcome through unchanged
		// rather than swallowing it. No credits are charged for a non-2xx response.
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
		charged, newBalance, err = deps.CreditStore.DebitCredits(r.Context(), user.ID, requestedCredits, reason)
		if err != nil {
			// The call already happened and cost real money upstream; there is no way to undo it
			// from here. Logging loudly (rather than silently dropping the charge) is the honest
			// v1 answer - reconciling a missed debit is a named follow-up, not silently swallowed.
			deps.logger().Error("debit credits for a completed call",
				"error", err, "user_id", user.ID, "requested_credits", requestedCredits, "reason", reason)
			writeError(w, http.StatusInternalServerError, "the call succeeded but credit accounting failed")
			return
		}
	}

	payload["credits_spent"] = charged
	payload["credit_balance"] = newBalance
	writeJSON(w, http.StatusOK, payload)
}

// handleBuildFiles proxies GET /api/build/{id}/files (R-467) verbatim, requiring an authenticated
// caller but never debiting credits - browsing already-generated files is not a billable model
// call. Known limitation, unchanged from R-467: the agent-engine's Studio server has no per-user
// build scoping, so any authenticated caller who knows a build id can browse its files, exactly as
// any local Studio user already could before this proxy existed.
func handleBuildFiles(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if _, err := auth.RequireUser(r.Context(), deps.AuthStore, r); err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if id == "" {
			writeError(w, http.StatusBadRequest, "build id is required")
			return
		}
		proxyGet(w, r, deps, deps.AgentEngineURL+"/api/build/"+url.PathEscape(id)+"/files")
	}
}

// handleBuildFile proxies GET /api/build/{id}/file?path=... (R-467) verbatim, same auth/no-debit
// shape as handleBuildFiles. Path-traversal safety is entirely the agent-engine's own
// (studio/files.py's already-tested _safe_destination-style check) - this proxy adds no new logic
// over the path, it only forwards it.
func handleBuildFile(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if _, err := auth.RequireUser(r.Context(), deps.AuthStore, r); err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if id == "" {
			writeError(w, http.StatusBadRequest, "build id is required")
			return
		}
		target := deps.AgentEngineURL + "/api/build/" + url.PathEscape(id) + "/file"
		if path := r.URL.Query().Get("path"); path != "" {
			target += "?" + (url.Values{"path": {path}}).Encode()
		}
		proxyGet(w, r, deps, target)
	}
}

// proxyGet makes a GET request to targetURL and copies the upstream status code and body back to
// w unchanged - a thin wrapper over proxyUpstream, kept so every existing GET call site stays as
// simple as it was before R-478 generalized the POST case too.
func proxyGet(w http.ResponseWriter, r *http.Request, deps Deps, targetURL string) {
	proxyUpstream(w, r, deps, http.MethodGet, targetURL, nil)
}

// proxyUpstream makes an HTTP request to targetURL using method (forwarding body, or none for a
// nil body) and copies the upstream status code and body back to w unchanged - the same "dumb
// pipe" shape for both the read-only GET routes and the credit-free preview-control POST routes
// (status/stop/restart/build-preview), none of which need proxyAndDebit's decode-and-charge logic.
func proxyUpstream(w http.ResponseWriter, r *http.Request, deps Deps, method string, targetURL string, body io.Reader) {
	upstreamRequest, err := http.NewRequestWithContext(r.Context(), method, targetURL, body)
	if err != nil {
		deps.logger().Error("build proxy request", "error", err)
		writeError(w, http.StatusInternalServerError, "could not build upstream request")
		return
	}
	if body != nil {
		upstreamRequest.Header.Set("Content-Type", "application/json")
	}

	upstreamResponse, err := deps.httpClient().Do(upstreamRequest)
	if err != nil {
		deps.logger().Error("call agent-engine", "error", err)
		writeError(w, http.StatusBadGateway, "could not reach the build service")
		return
	}
	defer func() { _ = upstreamResponse.Body.Close() }()

	respBody, err := io.ReadAll(upstreamResponse.Body)
	if err != nil {
		deps.logger().Error("read agent-engine response", "error", err)
		writeError(w, http.StatusBadGateway, "could not read build service response")
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(upstreamResponse.StatusCode)
	_, _ = w.Write(respBody)
}

// handlePreviewStatus proxies GET /api/preview verbatim - the singleton preview's current
// status ("whichever preview is currently running"). No debit: checking status isn't a billable
// model call.
func handlePreviewStatus(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if _, err := auth.RequireUser(r.Context(), deps.AuthStore, r); err != nil {
			writeAuthError(w, deps, err)
			return
		}
		proxyGet(w, r, deps, deps.AgentEngineURL+"/api/preview")
	}
}

// handlePreviewStop proxies POST /api/preview/stop verbatim, forwarding whatever body the caller
// sent (the agent-engine treats an empty body as {} - an ecosystem caller may include
// surface_slug, out of scope for today's console UI but not worth rejecting here). No debit:
// stopping a local process isn't a billable model call.
func handlePreviewStop(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if _, err := auth.RequireUser(r.Context(), deps.AuthStore, r); err != nil {
			writeAuthError(w, deps, err)
			return
		}
		body, err := io.ReadAll(r.Body)
		_ = r.Body.Close()
		if err != nil {
			writeError(w, http.StatusBadRequest, "could not read request body")
			return
		}
		proxyUpstream(w, r, deps, http.MethodPost, deps.AgentEngineURL+"/api/preview/stop", bytes.NewReader(body))
	}
}

// handlePreviewRestart proxies POST /api/preview/restart verbatim, same body-forwarding shape as
// handlePreviewStop. Write deadline is extended via defaultPreviewTimeout: restarting the
// currently-running preview can itself trigger a real cold start, the same real wait
// handleBuildPreview can hit.
func handlePreviewRestart(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if controller := http.NewResponseController(w); controller != nil {
			_ = controller.SetWriteDeadline(time.Now().Add(defaultPreviewTimeout))
		}
		if _, err := auth.RequireUser(r.Context(), deps.AuthStore, r); err != nil {
			writeAuthError(w, deps, err)
			return
		}
		body, err := io.ReadAll(r.Body)
		_ = r.Body.Close()
		if err != nil {
			writeError(w, http.StatusBadRequest, "could not read request body")
			return
		}
		proxyUpstream(w, r, deps, http.MethodPost, deps.AgentEngineURL+"/api/preview/restart", bytes.NewReader(body))
	}
}

// handleBuildPreview proxies POST /api/history/preview - the build-scoped preview a chat-per-build
// UI actually needs ("show me *this* build's preview"), verbatim except for the outgoing body:
// the id always comes from the URL path, never the caller's own body, matching every other
// build-scoped route in this package. Write deadline is extended via defaultPreviewTimeout since
// this can trigger a real cold start (StudioPreviewManager.replace()).
//
// An unknown/evicted build id is NOT proxied as a 404 - the agent-engine's own
// _preview_recorded_build returns a plain 200 {"status":"error","message":"..."} for that case
// (verified by reading live_serve.py before this task's tests were written), and this proxy
// deliberately makes no attempt to "fix" that shape into a 404 - it forwards exactly what the
// agent-engine says.
func handleBuildPreview(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if controller := http.NewResponseController(w); controller != nil {
			_ = controller.SetWriteDeadline(time.Now().Add(defaultPreviewTimeout))
		}
		if _, err := auth.RequireUser(r.Context(), deps.AuthStore, r); err != nil {
			writeAuthError(w, deps, err)
			return
		}
		id := r.PathValue("id")
		if id == "" {
			writeError(w, http.StatusBadRequest, "build id is required")
			return
		}
		body, err := json.Marshal(map[string]string{"id": id})
		if err != nil {
			deps.logger().Error("build preview request body", "error", err)
			writeError(w, http.StatusInternalServerError, "could not build upstream request")
			return
		}
		proxyUpstream(w, r, deps, http.MethodPost, deps.AgentEngineURL+"/api/history/preview", bytes.NewReader(body))
	}
}

// writeAuthError maps auth.RequireUser's error to the right HTTP status - shared by every Job API
// handler so the mapping is written, and can change, in exactly one place.
func writeAuthError(w http.ResponseWriter, deps Deps, err error) {
	if errors.Is(err, auth.ErrUnauthenticated) {
		writeError(w, http.StatusUnauthorized, "missing bearer token or session not found or expired")
		return
	}
	deps.logger().Error("resolve authenticated user", "error", err)
	writeError(w, http.StatusInternalServerError, "could not authenticate request")
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

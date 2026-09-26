package ai

import (
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"strconv"
	"strings"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

// Deps captures the dependencies required by the AI API handlers.
type Deps struct {
	AuthStore      auth.Store
	AIStore        Store
	AgentEngineURL string
	HTTPClient     *http.Client
	Logger         *slog.Logger
}

func (d Deps) logger() *slog.Logger {
	if d.Logger != nil {
		return d.Logger
	}
	return slog.Default()
}

func (d Deps) httpClient() *http.Client {
	if d.HTTPClient != nil {
		return d.HTTPClient
	}
	return http.DefaultClient
}

// Register mounts the AI & model management REST endpoints onto mux.
func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /ai/providers", handleGetProviders(deps))
	mux.HandleFunc("GET /ai/keys/{providerId}", handleGetUserKey(deps))
	mux.HandleFunc("PUT /ai/keys/{providerId}", handleSetUserKey(deps))
	mux.HandleFunc("DELETE /ai/keys/{providerId}", handleDeleteUserKey(deps))
	mux.HandleFunc("POST /ai/keys/{providerId}/test", handleTestUserKey(deps))
	mux.HandleFunc("GET /ai/models", handleGetModels(deps))
	mux.HandleFunc("GET /projects/{id}/model", handleGetProjectModel(deps))
	mux.HandleFunc("PUT /projects/{id}/model", handleSetProjectModel(deps))
	mux.HandleFunc("GET /projects/{id}/usage", handleGetProjectUsage(deps))
	mux.HandleFunc("GET /usage", handleGetAccountUsage(deps))
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func parseRangeDays(r *http.Request, defaultDays int) int {
	raw := strings.TrimSpace(r.URL.Query().Get("range"))
	raw = strings.TrimSuffix(raw, "d")
	if raw == "" {
		return defaultDays
	}
	days, err := strconv.Atoi(raw)
	if err != nil || days <= 0 {
		return defaultDays
	}
	return days
}

// handleGetProviders combines agent-engine provider status with user's BYOK keys.
func handleGetProviders(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		// Fetch provider status from agent-engine
		upstreamReq, err := http.NewRequestWithContext(r.Context(), http.MethodGet, deps.AgentEngineURL+"/api/providers", nil)
		if err != nil {
			deps.logger().Error("create providers request", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to query providers")
			return
		}
		upstreamResp, err := deps.httpClient().Do(upstreamReq)
		if err != nil {
			deps.logger().Error("fetch providers from agent-engine", "error", err)
			writeError(w, http.StatusBadGateway, "failed to reach agent-engine")
			return
		}
		defer func() { _ = upstreamResp.Body.Close() }()

		var statusPayload map[string]any
		if err := json.NewDecoder(upstreamResp.Body).Decode(&statusPayload); err != nil {
			writeError(w, http.StatusBadGateway, "failed to decode agent-engine providers response")
			return
		}

		// Query user's BYOK keys
		userKeys, err := deps.AIStore.ListUserKeys(r.Context(), user.ID)
		if err != nil {
			deps.logger().Error("list user keys", "error", err)
			userKeys = nil
		}
		keyMap := make(map[string]KeyMetadata)
		for _, k := range userKeys {
			keyMap[strings.ToLower(k.ProviderID)] = k
		}

		// Annotate providers array
		if providers, ok := statusPayload["providers"].([]any); ok {
			for i, p := range providers {
				if pMap, ok := p.(map[string]any); ok {
					pID, _ := pMap["providerId"].(string)
					pIDLower := strings.ToLower(pID)
					tier, _ := pMap["tier"].(string)
					active, _ := pMap["active"].(bool)

					kMeta, hasUserKey := keyMap[pIDLower]
					pMap["has_user_key"] = hasUserKey
					if hasUserKey {
						pMap["user_key_label"] = kMeta.Label
						pMap["user_key_last_used_at"] = kMeta.LastUsedAt
						pMap["effective_source"] = "byok"
						pMap["effective_reason"] = "Using your " + pID + " key (BYOK - 0 credits)"
					} else if active && tier == "cloud" {
						pMap["effective_source"] = "platform"
						pMap["effective_reason"] = "Using platform credits"
					} else if tier == "local" {
						pMap["effective_source"] = "local"
						pMap["effective_reason"] = "Using local model (free)"
					} else {
						pMap["effective_source"] = "none"
						pMap["effective_reason"] = "Needs API key"
					}
					providers[i] = pMap
				}
			}
			statusPayload["providers"] = providers
		}

		writeJSON(w, http.StatusOK, statusPayload)
	}
}

// handleGetUserKey returns metadata for a user's BYOK key.
func handleGetUserKey(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		providerID := r.PathValue("providerId")
		keys, err := deps.AIStore.ListUserKeys(r.Context(), user.ID)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to list keys")
			return
		}

		for _, k := range keys {
			if strings.EqualFold(k.ProviderID, providerID) {
				writeJSON(w, http.StatusOK, k)
				return
			}
		}

		writeError(w, http.StatusNotFound, "provider key not found")
	}
}

// handleSetUserKey saves a user's BYOK key.
func handleSetUserKey(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		if !deps.AIStore.IsAvailable() {
			writeError(w, http.StatusServiceUnavailable, "secrets encryption is not configured")
			return
		}

		providerID := r.PathValue("providerId")
		body, err := io.ReadAll(r.Body)
		_ = r.Body.Close()
		if err != nil {
			writeError(w, http.StatusBadRequest, "failed to read body")
			return
		}

		var req struct {
			APIKey string `json:"api_key"`
			Label  string `json:"label"`
		}
		if err := json.Unmarshal(body, &req); err != nil {
			writeError(w, http.StatusBadRequest, "invalid json")
			return
		}

		if strings.TrimSpace(req.APIKey) == "" {
			writeError(w, http.StatusBadRequest, "api_key is required")
			return
		}

		err = deps.AIStore.SetUserKey(r.Context(), user.ID, providerID, req.APIKey, req.Label)
		if err != nil {
			deps.logger().Error("save user key", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to save key")
			return
		}

		writeJSON(w, http.StatusOK, map[string]string{
			"status":      "saved",
			"provider_id": providerID,
		})
	}
}

// handleDeleteUserKey deletes a user's BYOK key.
func handleDeleteUserKey(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		providerID := r.PathValue("providerId")
		err = deps.AIStore.DeleteUserKey(r.Context(), user.ID, providerID)
		if errors.Is(err, ErrKeyNotFound) {
			writeError(w, http.StatusNotFound, "key not found")
			return
		}
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to delete key")
			return
		}

		writeJSON(w, http.StatusOK, map[string]string{
			"status":      "deleted",
			"provider_id": providerID,
		})
	}
}

// handleTestUserKey performs a lightweight test call with the user's BYOK key.
func handleTestUserKey(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		providerID := r.PathValue("providerId")
		key, _, err := deps.AIStore.GetUserKey(r.Context(), user.ID, providerID)
		if errors.Is(err, ErrKeyNotFound) {
			writeError(w, http.StatusNotFound, "no key configured for provider")
			return
		}
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to retrieve key")
			return
		}

		// Validate key is non-empty
		if strings.TrimSpace(key) == "" {
			writeError(w, http.StatusBadRequest, "empty key")
			return
		}

		// Simple honesty validation based on provider prefix/format
		validFormat := true
		providerLower := strings.ToLower(providerID)
		switch providerLower {
		case "openai":
			validFormat = strings.HasPrefix(key, "sk-")
		case "anthropic":
			validFormat = strings.HasPrefix(key, "sk-ant-")
		case "groq":
			validFormat = strings.HasPrefix(key, "gsk_")
		case "nvidia":
			validFormat = strings.HasPrefix(key, "nvapi-")
		}

		if !validFormat {
			writeJSON(w, http.StatusOK, map[string]any{
				"valid":   false,
				"message": "Key does not match expected prefix for " + providerID,
			})
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{
			"valid":   true,
			"message": "Key is configured and format is valid",
		})
	}
}

// ModelInfo describes an available model.
type ModelInfo struct {
	ProviderID      string `json:"provider_id"`
	ModelID         string `json:"model_id"`
	Name            string `json:"name"`
	Tier            string `json:"tier"`
	CostPer1kInput  string `json:"cost_per_1k_input,omitempty"`
	CostPer1kOutput string `json:"cost_per_1k_output,omitempty"`
}

// handleGetModels returns a list of supported models across providers.
func handleGetModels(deps Deps) http.HandlerFunc {
	models := []ModelInfo{
		{ProviderID: "ollama", ModelID: "qwen2.5-coder:14b", Name: "Qwen 2.5 Coder 14B (Local)", Tier: "local", CostPer1kInput: "$0.00", CostPer1kOutput: "$0.00"},
		{ProviderID: "groq", ModelID: "llama-3.3-70b-versatile", Name: "Llama 3.3 70B Versatile", Tier: "cloud", CostPer1kInput: "$0.00059", CostPer1kOutput: "$0.00079"},
		{ProviderID: "openai", ModelID: "gpt-4o", Name: "GPT-4o", Tier: "cloud", CostPer1kInput: "$0.0025", CostPer1kOutput: "$0.0100"},
		{ProviderID: "openai", ModelID: "gpt-4o-mini", Name: "GPT-4o Mini", Tier: "cloud", CostPer1kInput: "$0.00015", CostPer1kOutput: "$0.0006"},
		{ProviderID: "anthropic", ModelID: "claude-3-5-sonnet-20241022", Name: "Claude 3.5 Sonnet", Tier: "cloud", CostPer1kInput: "$0.0030", CostPer1kOutput: "$0.0150"},
		{ProviderID: "anthropic", ModelID: "claude-3-5-haiku-20241022", Name: "Claude 3.5 Haiku", Tier: "cloud", CostPer1kInput: "$0.0008", CostPer1kOutput: "$0.0040"},
		{ProviderID: "google", ModelID: "gemini-2.0-flash", Name: "Gemini 2.0 Flash", Tier: "cloud", CostPer1kInput: "$0.0001", CostPer1kOutput: "$0.0004"},
		{ProviderID: "deepseek", ModelID: "deepseek-chat", Name: "DeepSeek V3", Tier: "cloud", CostPer1kInput: "$0.00014", CostPer1kOutput: "$0.00028"},
		// PC-047: unpriced on purpose — no published per-token price was verified, and a guessed one
		// would mis-charge credits. The cost columns stay empty until a real price is known.
		{ProviderID: "nvidia", ModelID: "nvidia/nemotron-3-ultra-550b-a55b", Name: "NVIDIA Nemotron 3 Ultra", Tier: "cloud"},
	}

	return func(w http.ResponseWriter, r *http.Request) {
		if _, err := auth.RequireUser(r.Context(), deps.AuthStore, r); err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"models": models})
	}
}

// handleGetProjectModel returns project's pinned model settings.
func handleGetProjectModel(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		cfg, err := deps.AIStore.GetProjectModel(r.Context(), user.ID, projectID)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to get project model")
			return
		}

		writeJSON(w, http.StatusOK, cfg)
	}
}

// handleSetProjectModel updates project's pinned model settings.
func handleSetProjectModel(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		body, err := io.ReadAll(r.Body)
		_ = r.Body.Close()
		if err != nil {
			writeError(w, http.StatusBadRequest, "failed to read body")
			return
		}

		var req struct {
			ModelProviderID string `json:"model_provider_id"`
			ModelID         string `json:"model_id"`
		}
		if err := json.Unmarshal(body, &req); err != nil {
			writeError(w, http.StatusBadRequest, "invalid json")
			return
		}

		err = deps.AIStore.SetProjectModel(r.Context(), user.ID, projectID, req.ModelProviderID, req.ModelID)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to set project model")
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{
			"status":            "updated",
			"project_id":        projectID,
			"model_provider_id": req.ModelProviderID,
			"model_id":          req.ModelID,
		})
	}
}

// handleGetProjectUsage returns usage report for a project.
func handleGetProjectUsage(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		days := parseRangeDays(r, 7)
		report, err := deps.AIStore.GetProjectUsage(r.Context(), user.ID, projectID, days)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			deps.logger().Error("get project usage", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to get project usage")
			return
		}

		writeJSON(w, http.StatusOK, report)
	}
}

// handleGetAccountUsage returns usage report across all projects for a user.
func handleGetAccountUsage(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		days := parseRangeDays(r, 30)
		report, err := deps.AIStore.GetAccountUsage(r.Context(), user.ID, days)
		if err != nil {
			deps.logger().Error("get account usage", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to get account usage")
			return
		}

		writeJSON(w, http.StatusOK, report)
	}
}

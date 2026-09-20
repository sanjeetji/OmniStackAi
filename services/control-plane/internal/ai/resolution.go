package ai

import (
	"context"
	"math"
	"strings"
)

// ResolvedModel encapsulates the resolved provider, model, API key, and billing classification.
type ResolvedModel struct {
	ProviderID string `json:"provider_id,omitempty"`
	ModelID    string `json:"model_id,omitempty"`
	APIKey     string `json:"api_key,omitempty"`
	BilledTo   string `json:"billed_to"` // "byok" | "local" | "platform"
}

// ResolveModel implements model resolution precedence:
// 1. Project pinned model (if set)
// 2. User BYOK key (if configured for provider)
// 3. Platform cloud provider (credits charged)
// 4. Local Ollama (zero credits)
func ResolveModel(ctx context.Context, store Store, userID, projectID string) ResolvedModel {
	if store == nil {
		return ResolvedModel{BilledTo: "platform"}
	}

	if projectID != "" {
		cfg, err := store.GetProjectModel(ctx, userID, projectID)
		if err == nil && cfg != nil && cfg.ModelProviderID != "" {
			providerID := strings.ToLower(strings.TrimSpace(cfg.ModelProviderID))
			modelID := strings.TrimSpace(cfg.ModelID)

			if providerID == "ollama" || providerID == "local" {
				return ResolvedModel{
					ProviderID: providerID,
					ModelID:    modelID,
					BilledTo:   "local",
				}
			}

			// Check for user BYOK key for this pinned provider
			apiKey, _, err := store.GetUserKey(ctx, userID, providerID)
			if err == nil && apiKey != "" {
				return ResolvedModel{
					ProviderID: providerID,
					ModelID:    modelID,
					APIKey:     apiKey,
					BilledTo:   "byok",
				}
			}

			// Pinned cloud provider without BYOK key -> platform cloud
			return ResolvedModel{
				ProviderID: providerID,
				ModelID:    modelID,
				BilledTo:   "platform",
			}
		}
	}

	// No project-level pin: check if user has ANY BYOK key
	keys, err := store.ListUserKeys(ctx, userID)
	if err == nil && len(keys) > 0 {
		// Prefer standard providers in priority order
		for _, pref := range []string{"groq", "openai", "anthropic"} {
			for _, k := range keys {
				if strings.EqualFold(k.ProviderID, pref) {
					apiKey, _, err := store.GetUserKey(ctx, userID, k.ProviderID)
					if err == nil && apiKey != "" {
						return ResolvedModel{
							ProviderID: k.ProviderID,
							APIKey:     apiKey,
							BilledTo:   "byok",
						}
					}
				}
			}
		}

		// Otherwise pick first available
		firstKey := keys[0]
		apiKey, _, err := store.GetUserKey(ctx, userID, firstKey.ProviderID)
		if err == nil && apiKey != "" {
			return ResolvedModel{
				ProviderID: firstKey.ProviderID,
				APIKey:     apiKey,
				BilledTo:   "byok",
			}
		}
	}

	return ResolvedModel{BilledTo: "platform"}
}

// RecordUsageCalls parses an agent-engine usage payload and writes immutable rows to model_calls.
func RecordUsageCalls(
	ctx context.Context,
	store Store,
	userID string,
	projectID *string,
	purpose string,
	billedTo string,
	usage any,
	creditsSpent int64,
	creditsPerUSD float64,
) error {
	if store == nil || usage == nil {
		return nil
	}

	uMap, ok := usage.(map[string]any)
	if !ok {
		return nil
	}

	var calls []ModelCall
	rawCalls, hasCalls := uMap["calls"].([]any)
	if hasCalls && len(rawCalls) > 0 {
		for _, raw := range rawCalls {
			cMap, ok := raw.(map[string]any)
			if !ok {
				continue
			}
			providerID, _ := cMap["provider_id"].(string)
			modelID, _ := cMap["model_id"].(string)
			tier, _ := cMap["tier"].(string)
			if tier == "" {
				if billedTo == "local" || providerID == "ollama" || providerID == "ollama-local" {
					tier = "local"
				} else {
					tier = "cloud"
				}
			}
			inputTokens := int64(asFloat(cMap["input_tokens"]))
			outputTokens := int64(asFloat(cMap["output_tokens"]))
			latencyMS := int(asFloat(cMap["latency_ms"]))
			costMicros := int64(asFloat(cMap["cost_micros_usd"]))
			success := true
			if s, ok := cMap["success"].(bool); ok {
				success = s
			}
			errorCode, _ := cMap["error_code"].(string)

			callCredits := int64(0)
			if billedTo == "platform" && creditsPerUSD > 0 && costMicros > 0 {
				callCredits = int64(math.Ceil(float64(costMicros) / 1_000_000.0 * creditsPerUSD))
			}

			calls = append(calls, ModelCall{
				UserID:        userID,
				ProjectID:     projectID,
				ProviderID:    providerID,
				ModelID:       modelID,
				Tier:          tier,
				Purpose:       purpose,
				InputTokens:   inputTokens,
				OutputTokens:  outputTokens,
				CostMicrosUSD: costMicros,
				CreditsSpent:  callCredits,
				BilledTo:      billedTo,
				Success:       success,
				ErrorCode:     errorCode,
				LatencyMS:     latencyMS,
			})
		}
	} else {
		totalCalls := int64(asFloat(uMap["total_calls"]))
		costMicros := int64(asFloat(uMap["cost_micros_usd"]))
		inputTokens := int64(asFloat(uMap["input_tokens"]))
		outputTokens := int64(asFloat(uMap["output_tokens"]))
		if totalCalls > 0 || costMicros > 0 || inputTokens > 0 || outputTokens > 0 {
			tier := "cloud"
			if billedTo == "local" {
				tier = "local"
			}
			calls = append(calls, ModelCall{
				UserID:        userID,
				ProjectID:     projectID,
				ProviderID:    "unknown",
				ModelID:       "unknown",
				Tier:          tier,
				Purpose:       purpose,
				InputTokens:   inputTokens,
				OutputTokens:  outputTokens,
				CostMicrosUSD: costMicros,
				CreditsSpent:  creditsSpent,
				BilledTo:      billedTo,
				Success:       true,
			})
		}
	}

	if len(calls) == 0 {
		return nil
	}
	return store.RecordModelCalls(ctx, calls)
}

func asFloat(v any) float64 {
	switch n := v.(type) {
	case float64:
		return n
	case int64:
		return float64(n)
	case int:
		return float64(n)
	default:
		return 0
	}
}

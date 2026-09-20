package payments

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/secrets"
)

type Deps struct {
	AuthStore      auth.Store
	ProjectStore   projects.Store
	PaymentsStore  Store
	SecretsStore   secrets.Store
	AgentEngineURL string
	Logger         *slog.Logger
	HTTPClient     *http.Client
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
	return &http.Client{Timeout: 30 * time.Second}
}

func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /projects/{id}/payments", handleGetProjectPayments(deps))
	mux.HandleFunc("PUT /projects/{id}/payments", handleSetProjectPayments(deps))
	mux.HandleFunc("DELETE /projects/{id}/payments", handleClearProjectPayments(deps))
}

func writeJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func authenticate(r *http.Request, authStore auth.Store) (auth.User, error) {
	return auth.RequireUser(r.Context(), authStore, r)
}

func checkProjectAccess(r *http.Request, deps Deps, projectID string) (auth.User, projects.Project, error) {
	user, err := authenticate(r, deps.AuthStore)
	if err != nil {
		return auth.User{}, projects.Project{}, err
	}
	proj, err := deps.ProjectStore.GetProject(r.Context(), projectID, user.ID)
	if err != nil {
		return user, projects.Project{}, err
	}
	return user, proj, nil
}

type KeyStatus struct {
	Key           string `json:"key"`
	Label         string `json:"label"`
	Required      bool   `json:"required"`
	Status        string `json:"status"` // "set" | "not_set"
	LastUpdatedAt string `json:"last_updated_at,omitempty"`
}

type PaymentsResponse struct {
	ProjectID      string      `json:"project_id"`
	PaymentGateway string      `json:"payment_gateway"`
	WebhookURL     string      `json:"webhook_url"`
	RequiredKeys   []KeyStatus `json:"required_keys"`
	TestMode       bool        `json:"test_mode"`
}

func getRequiredKeysForGateway(gateway string, existingSecrets []secrets.SecretMetadata) ([]KeyStatus, bool) {
	var definitions []struct {
		Key      string
		Label    string
		Required bool
	}

	if gateway == "stripe" {
		definitions = []struct {
			Key      string
			Label    string
			Required bool
		}{
			{"STRIPE_SECRET_KEY", "Stripe Secret Key (sk_test_... / sk_live_...)", true},
			{"STRIPE_WEBHOOK_SECRET", "Stripe Webhook Signing Secret (whsec_...)", true},
			{"NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY", "Stripe Publishable Key (pk_test_... / pk_live_...)", false},
		}
	} else if gateway == "razorpay" {
		definitions = []struct {
			Key      string
			Label    string
			Required bool
		}{
			{"RAZORPAY_KEY_ID", "Razorpay Key ID (rzp_test_... / rzp_live_...)", true},
			{"RAZORPAY_KEY_SECRET", "Razorpay Key Secret", true},
			{"RAZORPAY_WEBHOOK_SECRET", "Razorpay Webhook Secret", true},
		}
	} else {
		return []KeyStatus{}, true
	}

	secretMap := make(map[string]secrets.SecretMetadata)
	for _, s := range existingSecrets {
		secretMap[s.Key] = s
	}

	results := make([]KeyStatus, 0, len(definitions))
	for _, d := range definitions {
		ks := KeyStatus{
			Key:      d.Key,
			Label:    d.Label,
			Required: d.Required,
			Status:   "not_set",
		}
		if s, ok := secretMap[d.Key]; ok {
			ks.Status = "set"
			ks.LastUpdatedAt = s.UpdatedAt.Format(time.RFC3339)
		}
		results = append(results, ks)
	}

	return results, true
}

func handleGetProjectPayments(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		user, proj, err := checkProjectAccess(r, deps, projectID)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		gateway, err := deps.PaymentsStore.GetPaymentGateway(r.Context(), projectID, user.ID)
		if err != nil {
			deps.logger().Error("failed to get project payment gateway", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to get payment gateway")
			return
		}

		var existingSecrets []secrets.SecretMetadata
		if deps.SecretsStore != nil {
			existingSecrets, _ = deps.SecretsStore.ListSecrets(r.Context(), projectID, user.ID)
		}

		keys, testMode := getRequiredKeysForGateway(gateway, existingSecrets)

		// Calculate webhook URL
		webhookURL := ""
		if gateway != "" {
			if proj.Name != "" {
				webhookURL = fmt.Sprintf("/api/webhooks/%s", gateway)
			}
		}

		writeJSON(w, http.StatusOK, PaymentsResponse{
			ProjectID:      projectID,
			PaymentGateway: gateway,
			WebhookURL:     webhookURL,
			RequiredKeys:   keys,
			TestMode:       testMode,
		})
	}
}

func handleSetProjectPayments(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		user, _, err := checkProjectAccess(r, deps, projectID)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		var body struct {
			Gateway string `json:"gateway"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeError(w, http.StatusBadRequest, "invalid request body")
			return
		}

		gateway := strings.ToLower(strings.TrimSpace(body.Gateway))
		if gateway != "stripe" && gateway != "razorpay" {
			writeError(w, http.StatusBadRequest, "invalid gateway: must be 'stripe' or 'razorpay'")
			return
		}

		// Trigger agent-engine codegen hook if available
		if deps.AgentEngineURL != "" {
			applyURL := fmt.Sprintf("%s/api/workspaces/%s/payments/apply", deps.AgentEngineURL, projectID)
			payload, _ := json.Marshal(map[string]any{
				"gateway": gateway,
			})
			req, err := http.NewRequestWithContext(r.Context(), http.MethodPost, applyURL, bytes.NewReader(payload))
			if err == nil {
				req.Header.Set("Content-Type", "application/json")
				resp, err := deps.httpClient().Do(req)
				if err != nil {
					deps.logger().Warn("agent-engine payments apply failed", "error", err)
				} else {
					_ = resp.Body.Close()
				}
			}
		}

		if err := deps.PaymentsStore.SetPaymentGateway(r.Context(), projectID, user.ID, gateway); err != nil {
			deps.logger().Error("failed to set payment gateway", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to set payment gateway")
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{
			"project_id":      projectID,
			"payment_gateway": gateway,
			"status":          "enabled",
		})
	}
}

func handleClearProjectPayments(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		user, _, err := checkProjectAccess(r, deps, projectID)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		currentGateway, _ := deps.PaymentsStore.GetPaymentGateway(r.Context(), projectID, user.ID)

		// Trigger agent-engine codegen removal hook if available
		if deps.AgentEngineURL != "" && currentGateway != "" {
			removeURL := fmt.Sprintf("%s/api/workspaces/%s/payments/remove", deps.AgentEngineURL, projectID)
			payload, _ := json.Marshal(map[string]any{
				"gateway": currentGateway,
			})
			req, err := http.NewRequestWithContext(r.Context(), http.MethodPost, removeURL, bytes.NewReader(payload))
			if err == nil {
				req.Header.Set("Content-Type", "application/json")
				resp, err := deps.httpClient().Do(req)
				if err != nil {
					deps.logger().Warn("agent-engine payments remove failed", "error", err)
				} else {
					_ = resp.Body.Close()
				}
			}
		}

		if err := deps.PaymentsStore.ClearPaymentGateway(r.Context(), projectID, user.ID); err != nil {
			deps.logger().Error("failed to clear payment gateway", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to clear payment gateway")
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{
			"deleted": true,
		})
	}
}

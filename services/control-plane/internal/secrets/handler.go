package secrets

import (
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

// Deps holds dependencies for secrets HTTP handlers.
type Deps struct {
	SecretsStore Store
	AuthStore    auth.Store
	Logger       *slog.Logger
}

func (d Deps) logger() *slog.Logger {
	if d.Logger != nil {
		return d.Logger
	}
	return slog.Default()
}

// Register mounts secrets endpoints onto mux.
func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /projects/{id}/secrets", handleListSecrets(deps))
	mux.HandleFunc("PUT /projects/{id}/secrets/{key}", handleSetSecret(deps))
	mux.HandleFunc("DELETE /projects/{id}/secrets/{key}", handleDeleteSecret(deps))
	mux.HandleFunc("POST /projects/{id}/secrets/reveal/{key}", handleRevealSecret(deps))
}

func writeJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func handleListSecrets(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		list, err := deps.SecretsStore.ListSecrets(r.Context(), projectID, user.ID)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if err != nil {
			deps.logger().Error("list secrets", "error", err)
			writeError(w, http.StatusInternalServerError, "could not list secrets")
			return
		}

		writeJSON(w, http.StatusOK, list)
	}
}

func handleSetSecret(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		if !deps.SecretsStore.IsAvailable() {
			writeError(w, http.StatusServiceUnavailable, "secrets encryption key is not configured")
			return
		}

		projectID := r.PathValue("id")
		key := r.PathValue("key")

		var req struct {
			Value       string `json:"value"`
			Description string `json:"description"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeError(w, http.StatusBadRequest, "invalid request body")
			return
		}

		sm, err := deps.SecretsStore.SetSecret(r.Context(), projectID, user.ID, key, req.Value, req.Description)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if errors.Is(err, ErrInvalidKeyFormat) {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		if errors.Is(err, ErrValueTooLarge) {
			writeError(w, http.StatusRequestEntityTooLarge, err.Error())
			return
		}
		if errors.Is(err, ErrKeyNotConfigured) {
			writeError(w, http.StatusServiceUnavailable, err.Error())
			return
		}
		if err != nil {
			deps.logger().Error("set secret", "error", err)
			writeError(w, http.StatusInternalServerError, "could not set secret")
			return
		}

		writeJSON(w, http.StatusOK, sm)
	}
}

func handleDeleteSecret(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		projectID := r.PathValue("id")
		key := r.PathValue("key")

		err = deps.SecretsStore.DeleteSecret(r.Context(), projectID, user.ID, key)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if errors.Is(err, ErrSecretNotFound) {
			writeError(w, http.StatusNotFound, "secret not found")
			return
		}
		if err != nil {
			deps.logger().Error("delete secret", "error", err)
			writeError(w, http.StatusInternalServerError, "could not delete secret")
			return
		}

		w.WriteHeader(http.StatusNoContent)
	}
}

func handleRevealSecret(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}

		if !deps.SecretsStore.IsAvailable() {
			writeError(w, http.StatusServiceUnavailable, "secrets encryption key is not configured")
			return
		}

		projectID := r.PathValue("id")
		key := r.PathValue("key")

		val, err := deps.SecretsStore.RevealSecret(r.Context(), projectID, user.ID, key)
		if errors.Is(err, ErrProjectNotFound) {
			writeError(w, http.StatusNotFound, "project not found")
			return
		}
		if errors.Is(err, ErrSecretNotFound) {
			writeError(w, http.StatusNotFound, "secret not found")
			return
		}
		if errors.Is(err, ErrKeyNotConfigured) {
			writeError(w, http.StatusServiceUnavailable, err.Error())
			return
		}
		if err != nil {
			deps.logger().Error("reveal secret", "error", err)
			writeError(w, http.StatusInternalServerError, "could not reveal secret")
			return
		}

		writeJSON(w, http.StatusOK, map[string]string{
			"key":   key,
			"value": val,
		})
	}
}

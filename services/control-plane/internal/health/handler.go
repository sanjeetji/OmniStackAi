package health

import (
	"context"
	"encoding/json"
	"net/http"
	"time"
)

const serviceName = "control-plane"

// Pinger is the narrow database capability needed by readiness checks.
type Pinger interface {
	Ping(context.Context) error
}

type response struct {
	Service string `json:"service"`
	Status  string `json:"status"`
}

// Register mounts /healthz and /readyz onto mux, so the control-plane can combine health routes
// with other route groups (e.g. internal/auth) on a single http.ServeMux/http.Server.
func Register(mux *http.ServeMux, database Pinger, pingTimeout time.Duration) {
	mux.HandleFunc("GET /healthz", func(writer http.ResponseWriter, _ *http.Request) {
		writeJSON(writer, http.StatusOK, response{Service: serviceName, Status: "ok"})
	})
	mux.HandleFunc("GET /readyz", func(writer http.ResponseWriter, request *http.Request) {
		ctx, cancel := context.WithTimeout(request.Context(), pingTimeout)
		defer cancel()

		if database == nil || database.Ping(ctx) != nil {
			writeJSON(writer, http.StatusServiceUnavailable, response{Service: serviceName, Status: "unavailable"})
			return
		}
		writeJSON(writer, http.StatusOK, response{Service: serviceName, Status: "ready"})
	})
}

func writeJSON(writer http.ResponseWriter, status int, payload response) {
	writer.Header().Set("Cache-Control", "no-store")
	writer.Header().Set("Content-Type", "application/json")
	writer.WriteHeader(status)
	_ = json.NewEncoder(writer).Encode(payload)
}

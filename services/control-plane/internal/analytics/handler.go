package analytics

import (
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"strings"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/connectors"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/deploy"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
)

// Deps holds all dependencies for the analytics HTTP handlers.
type Deps struct {
	AuthStore      auth.Store
	ProjectStore   projects.Store
	AnalyticsStore Store
	ConnectorStore connectors.Store
	DeployStore    deploy.Store
	GA4Client      *GA4Client
	Logger         *slog.Logger
}

func (d Deps) logger() *slog.Logger {
	if d.Logger != nil {
		return d.Logger
	}
	return slog.Default()
}

// Register mounts the analytics routes on the provided mux.
func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /projects/{id}/analytics", handleGetAnalytics(deps))
	mux.HandleFunc("PUT /projects/{id}/analytics", handleSetAnalytics(deps))
	mux.HandleFunc("DELETE /projects/{id}/analytics", handleClearAnalytics(deps))
	mux.HandleFunc("GET /projects/{id}/analytics/report", handleGetAnalyticsReport(deps))
}

// ─────────────────────────────────────────────────────────────────────────────
// Response types
// ─────────────────────────────────────────────────────────────────────────────

// AnalyticsStatus is the response body for GET /projects/{id}/analytics.
type AnalyticsStatus struct {
	ProjectID  string `json:"project_id"`
	Provider   string `json:"provider"` // "" | "ga4"
	PropertyID string `json:"property_id"`
	Connected  bool   `json:"connected"`  // true when provider != "" && property_id != ""
	GA4Linked  bool   `json:"ga4_linked"` // true when the GA4 OAuth connector is active
	Published  bool   `json:"published"`  // true when the project has at least one live deployment
	LiveURL    string `json:"live_url"`   // current live URL of the published project
}

// ─────────────────────────────────────────────────────────────────────────────
// Handlers
// ─────────────────────────────────────────────────────────────────────────────

func handleGetAnalytics(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		user, _, err := checkProjectAccess(r, deps, projectID)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		cfg, err := deps.AnalyticsStore.GetAnalytics(r.Context(), projectID, user.ID)
		if err != nil {
			deps.logger().Error("analytics: get config failed", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to get analytics configuration")
			return
		}

		// Check whether a GA4 connector is linked.
		ga4Linked := false
		if deps.ConnectorStore != nil {
			c, cErr := deps.ConnectorStore.GetProjectConnector(r.Context(), projectID, "google_analytics")
			if cErr == nil && c.Enabled {
				ga4Linked = true
			}
		}

		// Check publication status via project deploy metadata.
		liveURL := ""
		published := false
		if deps.DeployStore != nil {
			_, _, url, dErr := deps.DeployStore.GetProjectDeployMeta(r.Context(), projectID)
			if dErr == nil && url != "" {
				published = true
				liveURL = url
			}
		}

		writeJSON(w, http.StatusOK, AnalyticsStatus{
			ProjectID:  projectID,
			Provider:   cfg.Provider,
			PropertyID: cfg.PropertyID,
			Connected:  cfg.Provider != "" && cfg.PropertyID != "",
			GA4Linked:  ga4Linked,
			Published:  published,
			LiveURL:    liveURL,
		})
	}
}

func handleSetAnalytics(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		user, _, err := checkProjectAccess(r, deps, projectID)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		var body struct {
			Provider   string `json:"provider"`
			PropertyID string `json:"property_id"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeError(w, http.StatusBadRequest, "invalid request body")
			return
		}

		cfg := Config{
			Provider:   strings.ToLower(strings.TrimSpace(body.Provider)),
			PropertyID: strings.TrimSpace(body.PropertyID),
		}

		if err := deps.AnalyticsStore.SetAnalytics(r.Context(), projectID, user.ID, cfg); err != nil {
			switch {
			case errors.Is(err, ErrInvalidProvider):
				writeError(w, http.StatusBadRequest, err.Error())
			case errors.Is(err, ErrInvalidPropertyID):
				writeError(w, http.StatusBadRequest, err.Error())
			case errors.Is(err, ErrProjectNotFound):
				writeError(w, http.StatusNotFound, "project not found")
			default:
				deps.logger().Error("analytics: set config failed", "error", err)
				writeError(w, http.StatusInternalServerError, "failed to save analytics configuration")
			}
			return
		}

		// Invalidate any cached reports for this project.
		if deps.GA4Client != nil {
			deps.GA4Client.InvalidateCache(projectID)
		}

		writeJSON(w, http.StatusOK, map[string]any{
			"project_id":  projectID,
			"provider":    cfg.Provider,
			"property_id": cfg.PropertyID,
			"status":      "connected",
		})
	}
}

func handleClearAnalytics(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		user, _, err := checkProjectAccess(r, deps, projectID)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		if err := deps.AnalyticsStore.ClearAnalytics(r.Context(), projectID, user.ID); err != nil {
			if errors.Is(err, ErrProjectNotFound) {
				writeError(w, http.StatusNotFound, "project not found")
				return
			}
			deps.logger().Error("analytics: clear config failed", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to clear analytics configuration")
			return
		}

		// Invalidate cached reports.
		if deps.GA4Client != nil {
			deps.GA4Client.InvalidateCache(projectID)
		}

		writeJSON(w, http.StatusOK, map[string]any{"deleted": true})
	}
}

func handleGetAnalyticsReport(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		user, _, err := checkProjectAccess(r, deps, projectID)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		rangeKey := r.URL.Query().Get("range")
		if rangeKey == "" {
			rangeKey = "7d"
		}
		if rangeKey != "24h" && rangeKey != "7d" && rangeKey != "30d" {
			writeError(w, http.StatusBadRequest, "invalid range; must be '24h', '7d', or '30d'")
			return
		}

		cfg, err := deps.AnalyticsStore.GetAnalytics(r.Context(), projectID, user.ID)
		if err != nil || cfg.Provider == "" || cfg.PropertyID == "" {
			writeError(w, http.StatusUnprocessableEntity, "analytics not configured for this project")
			return
		}

		// Retrieve the GA4 OAuth access token from the connector store.
		accessToken := ""
		if deps.ConnectorStore != nil {
			c, cErr := deps.ConnectorStore.GetProjectConnector(r.Context(), projectID, "google_analytics")
			if cErr == nil && c.Enabled {
				if tok, ok := c.Config["access_token"].(string); ok {
					accessToken = tok
				}
			}
		}

		if deps.GA4Client == nil {
			writeError(w, http.StatusInternalServerError, "analytics client not initialised")
			return
		}

		// Fetch primary metrics report.
		report, err := deps.GA4Client.FetchReport(r.Context(), projectID, cfg.PropertyID, accessToken, rangeKey)
		if err != nil {
			deps.logger().Error("analytics: fetch report failed", "error", err, "project_id", projectID)
			writeError(w, http.StatusBadGateway, fmt.Sprintf("failed to fetch GA4 report: %s", err.Error()))
			return
		}

		// Enrich with dimension breakdowns (best-effort — never fail the whole request).
		if !report.Empty {
			report.TopPages, _ = fetchTopItems(r, deps, cfg.PropertyID, accessToken, rangeKey, "pagePath", 10)
			report.TopRefs, _ = fetchTopItems(r, deps, cfg.PropertyID, accessToken, rangeKey, "sessionSource", 10)
			report.Devices, report.Countries = fetchDevicesAndCountries(r, deps, cfg.PropertyID, accessToken, rangeKey, report.Sessions)
		}

		writeJSON(w, http.StatusOK, report)
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers used by handleGetAnalyticsReport
// ─────────────────────────────────────────────────────────────────────────────

func fetchTopItems(r *http.Request, deps Deps, propertyID, accessToken, rangeKey, dimension string, limit int) ([]TopItem, error) {
	rows, err := deps.GA4Client.FetchDimensionReport(r.Context(), propertyID, accessToken, rangeKey, dimension, limit)
	if err != nil {
		return nil, err
	}
	var total int64
	for _, row := range rows {
		total += row.Value
	}
	items := make([]TopItem, 0, len(rows))
	for _, row := range rows {
		var frac float64
		if total > 0 {
			frac = float64(row.Value) / float64(total)
		}
		items = append(items, TopItem{Label: row.Label, Value: row.Value, Fraction: frac})
	}
	return items, nil
}

func fetchDevicesAndCountries(r *http.Request, deps Deps, propertyID, accessToken, rangeKey string, totalSessions int64) (DeviceSplit, []CountryItem) {
	var devices DeviceSplit
	var countries []CountryItem

	deviceRows, err := deps.GA4Client.FetchDimensionReport(r.Context(), propertyID, accessToken, rangeKey, "deviceCategory", 5)
	if err == nil {
		for _, row := range deviceRows {
			switch strings.ToLower(row.Label) {
			case "mobile":
				devices.Mobile = row.Value
			case "desktop":
				devices.Desktop = row.Value
			case "tablet":
				devices.Tablet = row.Value
			}
		}
	}

	countryRows, err := deps.GA4Client.FetchDimensionReport(r.Context(), propertyID, accessToken, rangeKey, "country", 10)
	if err == nil {
		countries = make([]CountryItem, 0, len(countryRows))
		for _, row := range countryRows {
			var frac float64
			if totalSessions > 0 {
				frac = float64(row.Value) / float64(totalSessions)
			}
			countries = append(countries, CountryItem{Country: row.Label, Sessions: row.Value, Fraction: frac})
		}
	}
	return devices, countries
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared auth / response utilities
// ─────────────────────────────────────────────────────────────────────────────

func writeJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func checkProjectAccess(r *http.Request, deps Deps, projectID string) (auth.User, projects.Project, error) {
	user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
	if err != nil {
		return auth.User{}, projects.Project{}, err
	}
	proj, err := deps.ProjectStore.GetProject(r.Context(), projectID, user.ID)
	if err != nil {
		return user, projects.Project{}, err
	}
	return user, proj, nil
}

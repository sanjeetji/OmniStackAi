package analytics

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"
)

// ─────────────────────────────────────────────────────────────────────────────
// Public report types
// ─────────────────────────────────────────────────────────────────────────────

// DailyPoint is a single day's visitor count on the traffic timeline.
type DailyPoint struct {
	Date     string `json:"date"` // "2024-01-15"
	Sessions int64  `json:"sessions"`
	Users    int64  `json:"users"`
}

// TopItem is one entry in a ranked list (pages, referrers).
type TopItem struct {
	Label    string  `json:"label"`
	Value    int64   `json:"value"`
	Fraction float64 `json:"fraction"` // 0..1
}

// DeviceSplit is the breakdown of sessions by device category.
type DeviceSplit struct {
	Mobile  int64 `json:"mobile"`
	Desktop int64 `json:"desktop"`
	Tablet  int64 `json:"tablet"`
}

// CountryItem is one country entry ranked by sessions.
type CountryItem struct {
	Country  string  `json:"country"`
	Sessions int64   `json:"sessions"`
	Fraction float64 `json:"fraction"`
}

// Report is the full analytics report returned to callers.
type Report struct {
	Range       string        `json:"range"` // "24h" | "7d" | "30d"
	PropertyID  string        `json:"property_id"`
	CachedAt    time.Time     `json:"cached_at"`
	Empty       bool          `json:"empty"` // true when no data at all
	ActiveUsers int64         `json:"active_users"`
	Sessions    int64         `json:"sessions"`
	Pageviews   int64         `json:"pageviews"`
	EngagementS float64       `json:"avg_engagement_seconds"` // average engagement time per session
	BounceRate  float64       `json:"bounce_rate"`            // 0..1
	Timeline    []DailyPoint  `json:"timeline"`
	TopPages    []TopItem     `json:"top_pages"`
	TopRefs     []TopItem     `json:"top_referrers"`
	Devices     DeviceSplit   `json:"devices"`
	Countries   []CountryItem `json:"countries"`
}

// ─────────────────────────────────────────────────────────────────────────────
// GA4 client + in-memory cache
// ─────────────────────────────────────────────────────────────────────────────

const cacheTTL = 5 * time.Minute

type cacheEntry struct {
	report    Report
	expiresAt time.Time
}

// GA4Client fetches reports from the Google Analytics Data API v1.
// It maintains a per-project, per-range in-memory cache with a 5-minute TTL
// so that we stay well within GA4's per-property quota limits.
type GA4Client struct {
	httpClient *http.Client
	mu         sync.Mutex
	cache      map[string]cacheEntry // key = "<projectID>:<propertyID>:<range>"
}

// NewGA4Client creates a GA4Client.
func NewGA4Client(httpClient *http.Client) *GA4Client {
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 20 * time.Second}
	}
	return &GA4Client{
		httpClient: httpClient,
		cache:      make(map[string]cacheEntry),
	}
}

// FetchReport returns an analytics report for the given property.
// accessToken must be a valid Google OAuth2 bearer token with the
// analytics.readonly scope.
func (c *GA4Client) FetchReport(ctx context.Context, projectID, propertyID, accessToken, rangeKey string) (Report, error) {
	if accessToken == "" {
		return Report{}, errors.New("analytics: no GA4 access token available; reconnect Google Analytics connector")
	}

	cacheKey := fmt.Sprintf("%s:%s:%s", projectID, propertyID, rangeKey)

	// Check cache first.
	c.mu.Lock()
	entry, ok := c.cache[cacheKey]
	c.mu.Unlock()
	if ok && time.Now().Before(entry.expiresAt) {
		return entry.report, nil
	}

	// Build the Data API request body.
	reqBody, err := buildRunReportBody(rangeKey)
	if err != nil {
		return Report{}, err
	}

	url := fmt.Sprintf("https://analyticsdata.googleapis.com/v1beta/properties/%s:runReport", propertyID)
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(reqBody))
	if err != nil {
		return Report{}, fmt.Errorf("analytics: create request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", "Bearer "+accessToken)

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return Report{}, fmt.Errorf("analytics: GA4 API call failed: %w", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)

	if resp.StatusCode == http.StatusTooManyRequests {
		return Report{}, errors.New("analytics: GA4 quota exceeded; retry after a few minutes")
	}
	if resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden {
		return Report{}, errors.New("analytics: GA4 access denied; token may have expired — reconnect Google Analytics connector")
	}
	if resp.StatusCode != http.StatusOK {
		return Report{}, fmt.Errorf("analytics: GA4 API returned status %d: %s", resp.StatusCode, truncate(string(body), 200))
	}

	report, err := parseRunReport(body, propertyID, rangeKey)
	if err != nil {
		return Report{}, err
	}
	report.CachedAt = time.Now()

	// Store in cache.
	c.mu.Lock()
	c.cache[cacheKey] = cacheEntry{report: report, expiresAt: time.Now().Add(cacheTTL)}
	c.mu.Unlock()

	return report, nil
}

// InvalidateCache removes all cached entries for a given project.
func (c *GA4Client) InvalidateCache(projectID string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	prefix := projectID + ":"
	for k := range c.cache {
		if len(k) >= len(prefix) && k[:len(prefix)] == prefix {
			delete(c.cache, k)
		}
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// GA4 Data API request / response helpers
// ─────────────────────────────────────────────────────────────────────────────

func buildRunReportBody(rangeKey string) ([]byte, error) {
	var startDate string
	switch rangeKey {
	case "24h":
		startDate = "yesterday"
	case "7d":
		startDate = "7daysAgo"
	case "30d":
		startDate = "30daysAgo"
	default:
		return nil, fmt.Errorf("analytics: unsupported range %q; use '24h', '7d', or '30d'", rangeKey)
	}

	body := map[string]any{
		"dateRanges": []map[string]any{
			{"startDate": startDate, "endDate": "today"},
		},
		"metrics": []map[string]any{
			{"name": "activeUsers"},
			{"name": "sessions"},
			{"name": "screenPageViews"},
			{"name": "averageSessionDuration"},
			{"name": "bounceRate"},
		},
		"dimensions": []map[string]any{
			{"name": "date"},
		},
		"limit": 90,
	}
	return json.Marshal(body)
}

// ga4RunReportResponse is a partial unmarshal of the GA4 runReport response.
type ga4RunReportResponse struct {
	DimensionHeaders []struct {
		Name string `json:"name"`
	} `json:"dimensionHeaders"`
	MetricHeaders []struct {
		Name string `json:"name"`
		Type string `json:"metricType"`
	} `json:"metricHeaders"`
	Rows []struct {
		DimensionValues []struct {
			Value string `json:"value"`
		} `json:"dimensionValues"`
		MetricValues []struct {
			Value string `json:"value"`
		} `json:"metricValues"`
	} `json:"rows"`
	Totals []struct {
		MetricValues []struct {
			Value string `json:"value"`
		} `json:"metricValues"`
	} `json:"totals"`
}

func parseRunReport(body []byte, propertyID, rangeKey string) (Report, error) {
	var raw ga4RunReportResponse
	if err := json.Unmarshal(body, &raw); err != nil {
		return Report{}, fmt.Errorf("analytics: parse GA4 response: %w", err)
	}

	report := Report{
		Range:      rangeKey,
		PropertyID: propertyID,
		Timeline:   []DailyPoint{},
		TopPages:   []TopItem{},
		TopRefs:    []TopItem{},
		Countries:  []CountryItem{},
	}

	if len(raw.Rows) == 0 {
		report.Empty = true
		return report, nil
	}

	// Build metric index map from headers.
	metricIdx := map[string]int{}
	for i, h := range raw.MetricHeaders {
		metricIdx[h.Name] = i
	}

	var totalUsers, totalSessions, totalPageviews int64
	var totalEngagement, totalBounce float64
	var engagementCount int

	for _, row := range raw.Rows {
		date := safeStr(row.DimensionValues, 0)

		users := safeInt(row.MetricValues, metricIdx["activeUsers"])
		sessions := safeInt(row.MetricValues, metricIdx["sessions"])
		pageviews := safeInt(row.MetricValues, metricIdx["screenPageViews"])
		engagement := safeFloat(row.MetricValues, metricIdx["averageSessionDuration"])
		bounce := safeFloat(row.MetricValues, metricIdx["bounceRate"])

		totalUsers += users
		totalSessions += sessions
		totalPageviews += pageviews
		if sessions > 0 {
			totalEngagement += engagement * float64(sessions)
			totalBounce += bounce * float64(sessions)
			engagementCount += int(sessions)
		}

		report.Timeline = append(report.Timeline, DailyPoint{
			Date:     formatGA4Date(date),
			Sessions: sessions,
			Users:    users,
		})
	}

	report.ActiveUsers = totalUsers
	report.Sessions = totalSessions
	report.Pageviews = totalPageviews
	if engagementCount > 0 {
		report.EngagementS = totalEngagement / float64(engagementCount)
		report.BounceRate = totalBounce / float64(engagementCount)
	}

	report.Empty = totalSessions == 0

	return report, nil
}

// ─────────────────────────────────────────────────────────────────────────────
// Secondary report: top pages, referrers, devices, countries
// ─────────────────────────────────────────────────────────────────────────────

// FetchDimensionReport fetches a single-dimension breakdown (pages, referrers,
// devices, or countries) from the GA4 Data API.
func (c *GA4Client) FetchDimensionReport(ctx context.Context, propertyID, accessToken, rangeKey, dimension string, limit int) ([]struct {
	Label string
	Value int64
}, error) {
	var startDate string
	switch rangeKey {
	case "24h":
		startDate = "yesterday"
	case "7d":
		startDate = "7daysAgo"
	case "30d":
		startDate = "30daysAgo"
	default:
		return nil, fmt.Errorf("analytics: unsupported range %q", rangeKey)
	}

	body := map[string]any{
		"dateRanges": []map[string]any{{"startDate": startDate, "endDate": "today"}},
		"metrics":    []map[string]any{{"name": "sessions"}},
		"dimensions": []map[string]any{{"name": dimension}},
		"orderBys": []map[string]any{{
			"metric":     map[string]any{"metricName": "sessions"},
			"descending": true,
		}},
		"limit": limit,
	}
	reqBody, _ := json.Marshal(body)

	url := fmt.Sprintf("https://analyticsdata.googleapis.com/v1beta/properties/%s:runReport", propertyID)
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(reqBody))
	if err != nil {
		return nil, fmt.Errorf("analytics: dimension request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", "Bearer "+accessToken)

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("analytics: dimension API call: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("analytics: dimension API status %d", resp.StatusCode)
	}

	var raw ga4RunReportResponse
	if err := json.NewDecoder(resp.Body).Decode(&raw); err != nil {
		return nil, fmt.Errorf("analytics: parse dimension response: %w", err)
	}

	result := make([]struct {
		Label string
		Value int64
	}, 0, len(raw.Rows))
	for _, row := range raw.Rows {
		label := safeStr(row.DimensionValues, 0)
		value := safeInt(row.MetricValues, 0)
		result = append(result, struct {
			Label string
			Value int64
		}{Label: label, Value: value})
	}
	return result, nil
}

// ─────────────────────────────────────────────────────────────────────────────
// Utility helpers
// ─────────────────────────────────────────────────────────────────────────────

func safeStr(vals []struct {
	Value string `json:"value"`
}, idx int) string {
	if idx < len(vals) {
		return vals[idx].Value
	}
	return ""
}

func safeInt(vals []struct {
	Value string `json:"value"`
}, idx int) int64 {
	s := safeStr(vals, idx)
	var n int64
	fmt.Sscanf(s, "%d", &n)
	return n
}

func safeFloat(vals []struct {
	Value string `json:"value"`
}, idx int) float64 {
	s := safeStr(vals, idx)
	var f float64
	fmt.Sscanf(s, "%f", &f)
	return f
}

// formatGA4Date converts "20240115" → "2024-01-15".
func formatGA4Date(d string) string {
	if len(d) == 8 {
		return d[:4] + "-" + d[4:6] + "-" + d[6:8]
	}
	return d
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}

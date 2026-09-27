// Package plans is what each plan includes, and the one place that refuses what a plan does not
// (PC-011, R-109).
//
// The five plans existed since R-469 (free, developer, pro, agency, enterprise) but nothing
// depended on them: every account could do everything. The numbers below are the beta defaults
// (D-1: 100 signup credits, 1 credit = $0.001, paid prices after beta usage) and every one of them
// is configuration — OMNISTACKAI_PLANS overrides any field of any plan, prices and payment ids
// included — so pricing is a founder decision, not a code change. A limit of 0 means unlimited.
package plans

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"sort"
)

// Plan is what one plan includes.
type Plan struct {
	ID                string  `json:"id"`
	Name              string  `json:"name"`
	Rank              int     `json:"rank"`
	MonthlyCredits    int64   `json:"monthly_credits"`
	MaxProjects       int     `json:"max_projects"`
	MaxPublishedApps  int     `json:"max_published_apps"`
	PreviewsPerUser   int     `json:"previews_per_user"`
	BuildsPerHour     int     `json:"builds_per_hour"`
	TaskBudgetCredits int64   `json:"task_budget_credits"`
	DailyCreditCap    int64   `json:"daily_credit_cap"`
	TeamMembers       int     `json:"team_members"`
	CustomDomains     bool    `json:"custom_domains"`
	OwnModelKeys      bool    `json:"own_model_keys"`
	PriceUSDMonthly   float64 `json:"price_usd_monthly"`
	PriceINRMonthly   float64 `json:"price_inr_monthly"`
	StripePriceID     string  `json:"stripe_price_id,omitempty"`
	RazorpayPlanID    string  `json:"razorpay_plan_id,omitempty"`
}

// ForSale reports whether the plan can be bought yet (it has a price).
func (p Plan) ForSale() bool { return p.PriceUSDMonthly > 0 || p.PriceINRMonthly > 0 }

var defaults = []Plan{
	{ID: "free", Name: "Free", Rank: 0, MonthlyCredits: 0, MaxProjects: 5, MaxPublishedApps: 1, PreviewsPerUser: 1,
		BuildsPerHour: 10, TaskBudgetCredits: 100, DailyCreditCap: 300, TeamMembers: 1},
	{ID: "developer", Name: "Developer", Rank: 1, MonthlyCredits: 2000, MaxProjects: 20, MaxPublishedApps: 3,
		PreviewsPerUser: 2, BuildsPerHour: 30, TaskBudgetCredits: 200, DailyCreditCap: 1500, TeamMembers: 1,
		CustomDomains: true, OwnModelKeys: true},
	{ID: "pro", Name: "Pro", Rank: 2, MonthlyCredits: 10000, MaxProjects: 100, MaxPublishedApps: 10,
		PreviewsPerUser: 3, BuildsPerHour: 60, TaskBudgetCredits: 500, DailyCreditCap: 5000, TeamMembers: 5,
		CustomDomains: true, OwnModelKeys: true},
	{ID: "agency", Name: "Agency", Rank: 3, MonthlyCredits: 40000, MaxProjects: 500, MaxPublishedApps: 50,
		PreviewsPerUser: 5, BuildsPerHour: 120, TaskBudgetCredits: 1000, DailyCreditCap: 20000, TeamMembers: 25,
		CustomDomains: true, OwnModelKeys: true},
	{ID: "enterprise", Name: "Enterprise", Rank: 4, MonthlyCredits: 100000, TaskBudgetCredits: 2000,
		PreviewsPerUser: 10, CustomDomains: true, OwnModelKeys: true},
}

// Catalogue is every plan, defaults overlaid with OMNISTACKAI_PLANS (a JSON object of plan id to
// the fields to change). A malformed override is ignored rather than breaking sign-in.
func Catalogue() map[string]Plan {
	out := map[string]Plan{}
	for _, p := range defaults {
		out[p.ID] = p
	}
	raw := os.Getenv("OMNISTACKAI_PLANS")
	if raw == "" {
		return out
	}
	var overrides map[string]json.RawMessage
	if json.Unmarshal([]byte(raw), &overrides) != nil {
		return out
	}
	for id, patch := range overrides {
		plan, ok := out[id]
		if !ok {
			continue
		}
		if json.Unmarshal(patch, &plan) == nil {
			plan.ID = id
			out[id] = plan
		}
	}
	return out
}

// For returns the plan with that id, or Free for an unknown one.
func For(id string) Plan {
	if plan, ok := Catalogue()[id]; ok {
		return plan
	}
	return Catalogue()["free"]
}

// Ordered is the catalogue in rank order, for the plans page.
func Ordered() []Plan {
	list := make([]Plan, 0, len(defaults))
	for _, p := range Catalogue() {
		list = append(list, p)
	}
	sort.Slice(list, func(i, j int) bool { return list[i].Rank < list[j].Rank })
	return list
}

// Cheapest returns the lowest-ranked plan that satisfies ok, for "upgrade to X" messages.
func Cheapest(ok func(Plan) bool) (Plan, bool) {
	for _, p := range Ordered() {
		if ok(p) {
			return p, true
		}
	}
	return Plan{}, false
}

// Within reports whether used is under a limit, where 0 means unlimited.
func Within(used, limit int) bool { return limit <= 0 || used < limit }

// Refuse answers 403 with what the plan allows and the cheapest plan that allows more.
func Refuse(w http.ResponseWriter, current Plan, what string, allows func(Plan) bool) {
	body := map[string]any{"error": fmt.Sprintf("Your %s plan does not include %s.", current.Name, what),
		"plan": current.ID}
	if next, ok := Cheapest(func(p Plan) bool { return p.Rank > current.Rank && allows(p) }); ok {
		body["error"] = fmt.Sprintf("Your %s plan does not include %s. The %s plan does.", current.Name, what, next.Name)
		body["upgrade_to"] = next.ID
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusForbidden)
	_ = json.NewEncoder(w).Encode(body)
}

// LimitsHeader is how the control plane tells the Studio a user's limits (believed only with the
// Studio's service token).
const LimitsHeader = "X-OmniStack-Limits"

// StudioLimits is the header value for a plan.
func StudioLimits(p Plan) string {
	return fmt.Sprintf("previews_per_user=%d;builds_per_hour=%d;max_published_apps=%d",
		p.PreviewsPerUser, p.BuildsPerHour, p.MaxPublishedApps)
}

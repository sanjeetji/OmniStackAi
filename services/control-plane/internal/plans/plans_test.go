package plans

import (
	"encoding/json"
	"net/http/httptest"
	"testing"
)

func TestEveryPlanExistsAndRanksUp(t *testing.T) {
	list := Ordered()
	if len(list) != 5 || list[0].ID != "free" || list[4].ID != "enterprise" {
		t.Fatalf("catalogue = %v", list)
	}
	if For("nonsense").ID != "free" {
		t.Error("an unknown plan must fall back to free")
	}
}

func TestPricesAndLimitsAreConfiguration(t *testing.T) {
	t.Setenv("OMNISTACKAI_PLANS", `{"pro":{"price_usd_monthly":29,"stripe_price_id":"price_123","max_projects":150}}`)
	pro := For("pro")
	if pro.PriceUSDMonthly != 29 || pro.StripePriceID != "price_123" || pro.MaxProjects != 150 || !pro.ForSale() {
		t.Errorf("override not applied: %+v", pro)
	}
	if pro.MonthlyCredits != 10000 {
		t.Error("fields not overridden must keep their defaults")
	}
	t.Setenv("OMNISTACKAI_PLANS", "{broken")
	if For("pro").MaxProjects != 100 {
		t.Error("a malformed override must be ignored")
	}
}

func TestBetaPlansAreNotForSaleUntilPriced(t *testing.T) {
	for _, p := range Ordered() {
		if p.ForSale() {
			t.Errorf("%s has a price before the founder set one (D-1)", p.ID)
		}
	}
}

func TestARefusalNamesThePlanThatAllowsIt(t *testing.T) {
	rec := httptest.NewRecorder()
	Refuse(rec, For("free"), "custom domains", func(p Plan) bool { return p.CustomDomains })
	var body map[string]any
	_ = json.NewDecoder(rec.Body).Decode(&body)
	if rec.Code != 403 || body["upgrade_to"] != "developer" {
		t.Errorf("got %d %v", rec.Code, body)
	}
}

func TestZeroMeansUnlimited(t *testing.T) {
	if !Within(10000, 0) || Within(5, 5) || !Within(4, 5) {
		t.Error("Within is wrong")
	}
}

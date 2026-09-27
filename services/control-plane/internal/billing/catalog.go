// Package billing sells credits and plans through Stripe (global) and Razorpay (India) (PC-011,
// D-3), and applies each payment exactly once.
//
// Keys last (PC-070): with no STRIPE_* / RAZORPAY_* keys the checkout answers "payments are not
// set up yet" and nothing else changes; super_admins can still grant credits. With test keys
// (sk_test_, rzp_test_) everything runs against the providers' test modes.
package billing

import (
	"encoding/json"
	"math"
	"os"
)

// Pack is a credit top-up.
type Pack struct {
	ID       string  `json:"id"`
	Name     string  `json:"name"`
	Credits  int64   `json:"credits"`
	PriceUSD float64 `json:"price_usd"`
	PriceINR float64 `json:"price_inr"`
}

// Defaults follow D-1 (1 credit = $0.001) with no markup; OMNISTACKAI_CREDIT_PACKS replaces them.
var defaultPacks = []Pack{
	{ID: "starter", Name: "5,000 credits", Credits: 5000, PriceUSD: 5, PriceINR: 420},
	{ID: "builder", Name: "25,000 credits", Credits: 25000, PriceUSD: 25, PriceINR: 2100},
	{ID: "studio", Name: "100,000 credits", Credits: 100000, PriceUSD: 100, PriceINR: 8400},
}

// Packs is the credit packs on sale.
func Packs() []Pack {
	if raw := os.Getenv("OMNISTACKAI_CREDIT_PACKS"); raw != "" {
		var packs []Pack
		if json.Unmarshal([]byte(raw), &packs) == nil && len(packs) > 0 {
			return packs
		}
	}
	return defaultPacks
}

// PackByID finds a pack.
func PackByID(id string) (Pack, bool) {
	for _, p := range Packs() {
		if p.ID == id {
			return p, true
		}
	}
	return Pack{}, false
}

// minorUnits converts a price to cents or paise.
func minorUnits(price float64) int64 { return int64(math.Round(price * 100)) }

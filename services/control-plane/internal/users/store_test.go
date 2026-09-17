package users

import "testing"

// TestClampCharge exercises DebitCredits's core arithmetic (R-472's v1 never-block-a-build
// policy) without a database - the real Store is instead proven against a live PostgreSQL in this
// task's manual smoke test, matching how CreateUser/FindUserByEmail etc. are already left
// untested here in go test (see this package's doc comment).
func TestClampCharge(t *testing.T) {
	cases := []struct {
		name           string
		balance        int64
		requested      int64
		wantCharged    int64
		wantNewBalance int64
	}{
		{"sufficient balance charges the full request", 500, 120, 120, 380},
		{"exact balance charges everything, leaves zero", 100, 100, 100, 0},
		{"insufficient balance clamps to whatever is left", 50, 200, 50, 0},
		{"zero balance charges nothing", 0, 75, 0, 0},
		{"zero requested charges nothing regardless of balance", 500, 0, 0, 500},
		{"already-negative balance (should not happen) never charges further", -10, 50, 0, -10},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			charged, newBalance := clampCharge(tc.balance, tc.requested)
			if charged != tc.wantCharged {
				t.Fatalf("charged = %d, want %d", charged, tc.wantCharged)
			}
			if newBalance != tc.wantNewBalance {
				t.Fatalf("newBalance = %d, want %d", newBalance, tc.wantNewBalance)
			}
			if newBalance < 0 && tc.balance >= 0 {
				t.Fatalf("newBalance = %d must never go negative from a non-negative balance", newBalance)
			}
			if charged < 0 {
				t.Fatalf("charged = %d must never be negative", charged)
			}
			if charged > tc.requested {
				t.Fatalf("charged = %d must never exceed requested = %d", charged, tc.requested)
			}
		})
	}
}

package credits

import (
	"context"
	"net/http"
	"testing"
	"time"
)

type fakeSpend map[string]int64 // key: userID|"hour"/"day"

func (f fakeSpend) SpentSince(_ context.Context, userID string, since time.Time) (int64, error) {
	window := "day"
	if time.Since(since) <= time.Hour+time.Minute {
		window = "hour"
	}
	return f[userID+"|"+window], nil
}

func guard(spend fakeSpend) Guard {
	return Guard{CreditsPerUSD: 1000, TaskBudgetCredits: 200, UserHourlyCap: 300, UserDailyCap: 1500,
		PlatformDailyCap: 100000, Spend: spend}
}

func TestZeroBalanceIsRefused(t *testing.T) {
	d := guard(fakeSpend{}).Admit(context.Background(), "u1", 0, true)
	if d.Allowed || d.Status != http.StatusPaymentRequired {
		t.Fatalf("got %+v, want 402", d)
	}
}

func TestTheBudgetIsTheSmallerOfTaskBudgetAndBalance(t *testing.T) {
	g := guard(fakeSpend{})
	if d := g.Admit(context.Background(), "u1", 50, true); d.BudgetMicros != CreditsToMicros(50, 1000) {
		t.Errorf("balance 50: budget %d, want the balance", d.BudgetMicros)
	}
	if d := g.Admit(context.Background(), "u1", 5000, true); d.BudgetMicros != CreditsToMicros(200, 1000) {
		t.Errorf("balance 5000: budget %d, want the task budget", d.BudgetMicros)
	}
}

func TestCapsStopARunawayUser(t *testing.T) {
	d := guard(fakeSpend{"u1|hour": 300}).Admit(context.Background(), "u1", 1000, true)
	if d.Status != http.StatusTooManyRequests || d.RetryAfter == 0 {
		t.Fatalf("hourly: got %+v", d)
	}
	d = guard(fakeSpend{"u1|day": 1500}).Admit(context.Background(), "u1", 1000, true)
	if d.Status != http.StatusTooManyRequests {
		t.Fatalf("daily: got %+v", d)
	}
	if d := guard(fakeSpend{"u1|hour": 300}).Admit(context.Background(), "u2", 1000, true); !d.Allowed {
		t.Error("another user must not be affected")
	}
}

func TestThePlatformCapAndKillSwitchPauseEveryone(t *testing.T) {
	if d := guard(fakeSpend{"|day": 100000}).Admit(context.Background(), "u1", 1000, true); d.Status != http.StatusServiceUnavailable {
		t.Errorf("platform cap: got %+v", d)
	}
	g := guard(fakeSpend{})
	g.Paused = true
	if d := g.Admit(context.Background(), "u1", 1000, true); d.Status != http.StatusServiceUnavailable {
		t.Errorf("kill switch: got %+v", d)
	}
}

func TestOwnKeyWorkIsNotLimited(t *testing.T) {
	g := guard(fakeSpend{"u1|hour": 99999})
	g.Paused = true
	if d := g.Admit(context.Background(), "u1", 0, false); !d.Allowed || d.BudgetMicros != -1 {
		t.Errorf("BYO key: got %+v", d)
	}
}

func TestConversionsNeverOverspend(t *testing.T) {
	if got := MicrosToCredits(CreditsToMicros(7, 1000), 1000); got > 7 {
		t.Errorf("round trip gave %d credits, more than the 7 budgeted", got)
	}
}

func TestAPlanCanOnlyTightenTheOperatorsCeiling(t *testing.T) {
	g := Guard{TaskBudgetCredits: 300, UserDailyCap: 0}
	if got := g.ForPlan(100, 500); got.TaskBudgetCredits != 100 || got.UserDailyCap != 500 {
		t.Errorf("stricter plan: %+v", got)
	}
	if got := g.ForPlan(2000, 0); got.TaskBudgetCredits != 300 || got.UserDailyCap != 0 {
		t.Errorf("looser plan must not lift the operator's ceiling: %+v", got)
	}
}

func TestTheConsoleSwitchPausesPaidWorkLive(t *testing.T) {
	paused := false
	g := guard(fakeSpend{})
	g.PausedNow = func(context.Context) bool { return paused }
	if d := g.Admit(context.Background(), "u1", 100, true); !d.Allowed {
		t.Fatal("running: refused")
	}
	paused = true
	if d := g.Admit(context.Background(), "u1", 100, true); d.Status != http.StatusServiceUnavailable {
		t.Errorf("paused from the console: got %+v", d)
	}
}

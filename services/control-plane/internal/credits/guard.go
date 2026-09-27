// Package credits decides whether paid model work may start, and how much it may spend (PC-010).
//
// Before this, a build was charged after the fact from its real model cost, clamped to the
// balance — so a user at zero credits could build for free, forever, on the platform's bill, and
// nothing bounded one task, one user or one bad day. The rules, each overridable per deployment:
//
//   - no work at zero credits (402, with the balance);
//   - a per-task budget: OMNISTACKAI_TASK_BUDGET_CREDITS (200), and never more than the balance.
//     The Studio stops making model calls when it is reached; the build finishes on templates;
//   - per-user caps: OMNISTACKAI_USER_HOURLY_CREDIT_CAP (300) and OMNISTACKAI_USER_DAILY_CREDIT_CAP
//     (1500) — a runaway loop or a stolen session is stopped, with the time it resets (429);
//   - a platform daily cap, OMNISTACKAI_PLATFORM_DAILY_CREDIT_CAP (0 = none), and a kill switch,
//     OMNISTACKAI_PAID_MODEL_WORK=paused, that pause all paid model work at once (503).
//
// Work billed to the user's own model key (BYO key) costs the platform nothing and is not limited.
package credits

import (
	"context"
	"fmt"
	"math"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

// SpendReader reports credits spent since a time — by one user, or by everyone when userID is "".
type SpendReader interface {
	SpentSince(ctx context.Context, userID string, since time.Time) (int64, error)
}

// Guard holds the limits. Zero-valued caps mean "no cap".
type Guard struct {
	CreditsPerUSD     float64
	TaskBudgetCredits int64
	UserHourlyCap     int64
	UserDailyCap      int64
	PlatformDailyCap  int64
	Paused            bool
	// PausedNow (PC-011) reads the super_admin console's live switch; nil means only Paused.
	PausedNow func(ctx context.Context) bool
	Spend     SpendReader
	Now       func() time.Time
}

// Decision is the answer for one task.
type Decision struct {
	Allowed      bool
	Status       int
	Message      string
	RetryAfter   int   // seconds, when known
	BudgetMicros int64 // USD micros the task may bill; -1 when not limited (BYO key)
}

// ForPlan narrows the guard to a plan's task budget and daily cap (PC-011). The operator's own
// settings stay a ceiling over every plan: the stricter of the two applies, and 0 means no limit.
func (g Guard) ForPlan(taskBudgetCredits, dailyCreditCap int64) Guard {
	g.TaskBudgetCredits = stricter(g.TaskBudgetCredits, taskBudgetCredits)
	g.UserDailyCap = stricter(g.UserDailyCap, dailyCreditCap)
	return g
}

func stricter(a, b int64) int64 {
	switch {
	case a <= 0:
		return b
	case b <= 0 || a < b:
		return a
	default:
		return b
	}
}

// FromEnv reads the limits from the process environment.
func FromEnv(creditsPerUSD float64, spend SpendReader) Guard {
	return Guard{
		CreditsPerUSD:     creditsPerUSD,
		TaskBudgetCredits: envInt("OMNISTACKAI_TASK_BUDGET_CREDITS", 200),
		UserHourlyCap:     envInt("OMNISTACKAI_USER_HOURLY_CREDIT_CAP", 300),
		UserDailyCap:      envInt("OMNISTACKAI_USER_DAILY_CREDIT_CAP", 1500),
		PlatformDailyCap:  envInt("OMNISTACKAI_PLATFORM_DAILY_CREDIT_CAP", 0),
		Paused:            strings.EqualFold(strings.TrimSpace(os.Getenv("OMNISTACKAI_PAID_MODEL_WORK")), "paused"),
		Spend:             spend,
	}
}

func envInt(name string, fallback int64) int64 {
	if v, err := strconv.ParseInt(strings.TrimSpace(os.Getenv(name)), 10, 64); err == nil && v >= 0 {
		return v
	}
	return fallback
}

func (g Guard) now() time.Time {
	if g.Now != nil {
		return g.Now()
	}
	return time.Now()
}

// Admit decides whether a task for a user with balance may start, and its budget.
func (g Guard) Admit(ctx context.Context, userID string, balance int64, billedToPlatform bool) Decision {
	if !billedToPlatform {
		return Decision{Allowed: true, BudgetMicros: -1}
	}
	if g.Paused || (g.PausedNow != nil && g.PausedNow(ctx)) {
		return Decision{Status: http.StatusServiceUnavailable, RetryAfter: 900,
			Message: "Building is paused for a short while by the platform operator. Please try again later."}
	}
	if balance <= 0 {
		return Decision{Status: http.StatusPaymentRequired,
			Message: "You are out of credits. Add credits to keep building."}
	}
	now := g.now()
	if g.Spend != nil {
		if g.PlatformDailyCap > 0 {
			if spent, err := g.Spend.SpentSince(ctx, "", startOfDay(now)); err == nil && spent >= g.PlatformDailyCap {
				return Decision{Status: http.StatusServiceUnavailable, RetryAfter: secondsUntil(now, startOfDay(now).Add(24*time.Hour)),
					Message: "The platform has reached today's spending limit. Building resumes tomorrow (UTC)."}
			}
		}
		if g.UserHourlyCap > 0 {
			if spent, err := g.Spend.SpentSince(ctx, userID, now.Add(-time.Hour)); err == nil && spent >= g.UserHourlyCap {
				return Decision{Status: http.StatusTooManyRequests, RetryAfter: 900,
					Message: fmt.Sprintf("You have used %d credits in the last hour, the hourly limit. Try again in a little while.", spent)}
			}
		}
		if g.UserDailyCap > 0 {
			if spent, err := g.Spend.SpentSince(ctx, userID, startOfDay(now)); err == nil && spent >= g.UserDailyCap {
				return Decision{Status: http.StatusTooManyRequests, RetryAfter: secondsUntil(now, startOfDay(now).Add(24*time.Hour)),
					Message: fmt.Sprintf("You have used %d credits today, the daily limit. It resets at midnight (UTC).", spent)}
			}
		}
	}
	budget := balance
	if g.TaskBudgetCredits > 0 && g.TaskBudgetCredits < budget {
		budget = g.TaskBudgetCredits
	}
	return Decision{Allowed: true, BudgetMicros: CreditsToMicros(budget, g.CreditsPerUSD)}
}

// CreditsToMicros converts credits to USD micros (rounded down, so a budget is never exceeded).
func CreditsToMicros(credits int64, creditsPerUSD float64) int64 {
	if creditsPerUSD <= 0 || credits <= 0 {
		return 0
	}
	return int64(math.Floor(float64(credits) * 1_000_000.0 / creditsPerUSD))
}

// MicrosToCredits converts USD micros to credits (rounded up, as charging does).
func MicrosToCredits(micros int64, creditsPerUSD float64) int64 {
	if creditsPerUSD <= 0 || micros <= 0 {
		return 0
	}
	return int64(math.Ceil(float64(micros) * creditsPerUSD / 1_000_000.0))
}

func startOfDay(t time.Time) time.Time {
	u := t.UTC()
	return time.Date(u.Year(), u.Month(), u.Day(), 0, 0, 0, 0, time.UTC)
}

func secondsUntil(now, then time.Time) int {
	if d := int(then.Sub(now).Seconds()); d > 0 {
		return d
	}
	return 1
}

// Refuse writes the decision as a JSON error with Retry-After when known.
func Refuse(w http.ResponseWriter, d Decision, balance int64) {
	w.Header().Set("Content-Type", "application/json")
	if d.RetryAfter > 0 {
		w.Header().Set("Retry-After", strconv.Itoa(d.RetryAfter))
	}
	w.WriteHeader(d.Status)
	_, _ = fmt.Fprintf(w, `{"error":%q,"credit_balance":%d,"retry_after":%d}`, d.Message, balance, d.RetryAfter)
}

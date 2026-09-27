package billing

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/plans"
)

// Deps wires the billing routes.
type Deps struct {
	AuthStore auth.Store
	Store     Store
	Stripe    *Stripe
	Razorpay  *Razorpay
	// CountProjects reports how many projects a user owns, for the plan page.
	CountProjects func(ctx context.Context, userID string) int
	// PublicURL is where a buyer returns after a hosted checkout (the console).
	PublicURL string
	Now       func() time.Time
	Logger    *slog.Logger
}

func (d Deps) logger() *slog.Logger {
	if d.Logger != nil {
		return d.Logger
	}
	return slog.Default()
}

func (d Deps) now() time.Time {
	if d.Now != nil {
		return d.Now()
	}
	return time.Now()
}

// Register adds the billing routes. The two webhooks are unauthenticated by design: the
// providers call them, and each request is proven by its signature instead.
func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /billing/plan", handlePlan(deps))
	mux.HandleFunc("POST /billing/checkout", handleCheckout(deps))
	mux.HandleFunc("POST /billing/razorpay/verify", handleRazorpayVerify(deps))
	mux.HandleFunc("POST /billing/webhooks/stripe", handleStripeWebhook(deps))
	mux.HandleFunc("POST /billing/webhooks/razorpay", handleRazorpayWebhook(deps))
}

// PublicURLFromEnv is OMNISTACKAI_PUBLIC_URL, or the local console.
func PublicURLFromEnv() string {
	if v := strings.TrimRight(strings.TrimSpace(os.Getenv("OMNISTACKAI_PUBLIC_URL")), "/"); v != "" {
		return v
	}
	return "http://127.0.0.1:4321"
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func handlePlan(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "not signed in"})
			return
		}
		projects := 0
		if deps.CountProjects != nil {
			projects = deps.CountProjects(r.Context(), user.ID)
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"plan":      plans.For(user.Plan),
			"usage":     map[string]any{"projects": projects, "credit_balance": user.CreditBalance},
			"plans":     plans.Ordered(),
			"packs":     Packs(),
			"providers": map[string]bool{"stripe": deps.Stripe.Configured(), "razorpay": deps.Razorpay.Configured()},
		})
	}
}

func handleCheckout(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "not signed in"})
			return
		}
		var req struct {
			Kind     string `json:"kind"`     // credits | plan
			ID       string `json:"id"`       // pack id or plan id
			Provider string `json:"provider"` // stripe | razorpay
		}
		if json.NewDecoder(io.LimitReader(r.Body, 4096)).Decode(&req) != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request"})
			return
		}
		notes := map[string]string{"user_id": user.ID, "kind": req.Kind, "item_id": req.ID}
		success := deps.PublicURL + "/settings/billing?paid=1"
		cancel := deps.PublicURL + "/settings/billing?cancelled=1"
		switch {
		case req.Kind == "credits":
			pack, ok := PackByID(req.ID)
			if !ok {
				writeJSON(w, http.StatusBadRequest, map[string]string{"error": "no such credit pack"})
				return
			}
			notes["credits"] = strconv.FormatInt(pack.Credits, 10)
			if req.Provider == "razorpay" {
				amount := minorUnits(pack.PriceINR)
				id, err := deps.Razorpay.CreateOrder(r.Context(), amount, "INR", "credits-"+pack.ID, notes)
				if !checkoutOK(w, deps, err) {
					return
				}
				_ = deps.Store.RecordOrder(r.Context(), Order{ID: id, Provider: "razorpay", UserID: user.ID, Kind: "credits",
					ItemID: pack.ID, Credits: pack.Credits, AmountMinor: amount, Currency: "INR"})
				writeJSON(w, http.StatusOK, map[string]any{"provider": "razorpay", "key_id": deps.Razorpay.KeyID,
					"order_id": id, "amount": amount, "currency": "INR", "name": pack.Name})
				return
			}
			amount := minorUnits(pack.PriceUSD)
			session, err := deps.Stripe.CreateCheckout(r.Context(), "", pack.Name, amount, "usd", success, cancel, notes)
			if !checkoutOK(w, deps, err) {
				return
			}
			_ = deps.Store.RecordOrder(r.Context(), Order{ID: session.ID, Provider: "stripe", UserID: user.ID, Kind: "credits",
				ItemID: pack.ID, Credits: pack.Credits, AmountMinor: amount, Currency: "USD"})
			writeJSON(w, http.StatusOK, map[string]any{"provider": "stripe", "redirect_url": session.URL})
		case req.Kind == "plan":
			plan, ok := plans.Catalogue()[req.ID]
			if !ok || !plan.ForSale() {
				writeJSON(w, http.StatusBadRequest, map[string]string{"error": "This plan is not on sale yet."})
				return
			}
			if req.Provider == "razorpay" {
				if plan.RazorpayPlanID == "" {
					writeJSON(w, http.StatusBadRequest, map[string]string{"error": "This plan is not sold through Razorpay yet."})
					return
				}
				id, err := deps.Razorpay.CreateSubscription(r.Context(), plan.RazorpayPlanID, notes)
				if !checkoutOK(w, deps, err) {
					return
				}
				_ = deps.Store.RecordOrder(r.Context(), Order{ID: id, Provider: "razorpay", UserID: user.ID, Kind: "plan",
					ItemID: plan.ID, AmountMinor: minorUnits(plan.PriceINRMonthly), Currency: "INR"})
				writeJSON(w, http.StatusOK, map[string]any{"provider": "razorpay", "key_id": deps.Razorpay.KeyID,
					"subscription_id": id, "name": plan.Name + " plan"})
				return
			}
			if plan.StripePriceID == "" {
				writeJSON(w, http.StatusBadRequest, map[string]string{"error": "This plan is not sold through Stripe yet."})
				return
			}
			session, err := deps.Stripe.CreateCheckout(r.Context(), plan.StripePriceID, "", 0, "usd", success, cancel, notes)
			if !checkoutOK(w, deps, err) {
				return
			}
			_ = deps.Store.RecordOrder(r.Context(), Order{ID: session.ID, Provider: "stripe", UserID: user.ID, Kind: "plan",
				ItemID: plan.ID, AmountMinor: minorUnits(plan.PriceUSDMonthly), Currency: "USD"})
			writeJSON(w, http.StatusOK, map[string]any{"provider": "stripe", "redirect_url": session.URL})
		default:
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "kind must be credits or plan"})
		}
	}
}

func checkoutOK(w http.ResponseWriter, deps Deps, err error) bool {
	if err == nil {
		return true
	}
	if errors.Is(err, ErrNotConfigured) {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{
			"error": "Payments are not set up yet. Ask the platform owner to add credits to your account."})
		return false
	}
	deps.logger().Error("billing checkout", "error", err)
	writeJSON(w, http.StatusBadGateway, map[string]string{"error": "The payment provider could not start a checkout."})
	return false
}

// fulfil applies a paid order once: credits for a pack; the plan and the subscription for a plan,
// with the first month's credits when grantFirstMonth (Stripe). Razorpay reports every charge,
// the first included, as subscription.charged, which grants each month's credits itself.
func fulfil(ctx context.Context, deps Deps, provider, key string, order Order, subscriptionID, customerID string, grantFirstMonth bool) (bool, error) {
	return deps.Store.ApplyOnce(ctx, provider, key, order.Kind, order.UserID, func(tx Tx) error {
		if err := tx.MarkOrderPaid(ctx, order.ID); err != nil {
			return err
		}
		if order.Kind == "credits" {
			return tx.GrantCredits(ctx, order.UserID, order.Credits, fmt.Sprintf("billing:%s:credits:%s", provider, order.ItemID))
		}
		plan := plans.For(order.ItemID)
		if err := tx.SetPlan(ctx, order.UserID, plan.ID); err != nil {
			return err
		}
		if err := tx.SaveSubscription(ctx, order.UserID, provider, subscriptionID, customerID, plan.ID, "active"); err != nil {
			return err
		}
		if !grantFirstMonth {
			return nil
		}
		return tx.GrantCredits(ctx, order.UserID, plan.MonthlyCredits, fmt.Sprintf("billing:%s:plan:%s", provider, plan.ID))
	})
}

func handleRazorpayVerify(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
		if err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "not signed in"})
			return
		}
		var req struct {
			OrderID        string `json:"razorpay_order_id"`
			SubscriptionID string `json:"razorpay_subscription_id"`
			PaymentID      string `json:"razorpay_payment_id"`
			Signature      string `json:"razorpay_signature"`
		}
		if json.NewDecoder(io.LimitReader(r.Body, 4096)).Decode(&req) != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request"})
			return
		}
		orderID, valid := req.OrderID, false
		if req.SubscriptionID != "" {
			orderID = req.SubscriptionID
			valid = VerifyRazorpayPayment(req.PaymentID, req.SubscriptionID, req.Signature, deps.Razorpay.KeySecret)
		} else {
			valid = VerifyRazorpayPayment(req.OrderID, req.PaymentID, req.Signature, deps.Razorpay.KeySecret)
		}
		if !valid {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "The payment could not be verified."})
			return
		}
		order, err := deps.Store.OrderByID(r.Context(), orderID)
		if err != nil || order.UserID != user.ID {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "order not found"})
			return
		}
		// The same key the webhook uses, so whichever arrives first grants and the other does nothing.
		if _, err := fulfil(r.Context(), deps, "razorpay", "order:"+order.ID, order, req.SubscriptionID, "", false); err != nil {
			deps.logger().Error("billing razorpay fulfil", "error", err)
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "The payment was received but could not be applied yet."})
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "paid"})
	}
}

func handleStripeWebhook(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		payload, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "unreadable body"})
			return
		}
		if err := VerifyStripeSignature(payload, r.Header.Get("Stripe-Signature"), deps.Stripe.WebhookSecret, deps.now(), 5*time.Minute); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid signature"})
			return
		}
		var event struct {
			ID   string `json:"id"`
			Type string `json:"type"`
			Data struct {
				Object struct {
					ID            string `json:"id"`
					Mode          string `json:"mode"`
					PaymentStatus string `json:"payment_status"`
					Subscription  string `json:"subscription"`
					Customer      string `json:"customer"`
					BillingReason string `json:"billing_reason"`
				} `json:"object"`
			} `json:"data"`
		}
		if json.Unmarshal(payload, &event) != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "malformed event"})
			return
		}
		obj := event.Data.Object
		ctx := r.Context()
		switch event.Type {
		case "checkout.session.completed":
			if obj.Mode == "payment" && obj.PaymentStatus != "paid" {
				break
			}
			order, err := deps.Store.OrderByID(ctx, obj.ID)
			if err != nil {
				deps.logger().Warn("stripe webhook for an unknown checkout", "session", obj.ID)
				break
			}
			if _, err := fulfil(ctx, deps, "stripe", "checkout:"+obj.ID, order, obj.Subscription, obj.Customer, true); err != nil {
				deps.logger().Error("billing stripe fulfil", "error", err)
				writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "retry"}) // Stripe retries
				return
			}
		case "invoice.paid":
			if obj.BillingReason != "subscription_cycle" || obj.Subscription == "" {
				break // the first invoice is covered by checkout.session.completed
			}
			userID, planID, err := deps.Store.SubscriptionOwner(ctx, "stripe", obj.Subscription)
			if err != nil {
				break
			}
			plan := plans.For(planID)
			_, err = deps.Store.ApplyOnce(ctx, "stripe", "invoice:"+obj.ID, "renewal", userID, func(tx Tx) error {
				return tx.GrantCredits(ctx, userID, plan.MonthlyCredits, "billing:stripe:renewal:"+plan.ID)
			})
			if err != nil {
				writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "retry"})
				return
			}
		case "customer.subscription.deleted":
			if userID, _, err := deps.Store.SubscriptionOwner(ctx, "stripe", obj.ID); err == nil {
				_, _ = deps.Store.ApplyOnce(ctx, "stripe", "ended:"+obj.ID, "cancel", userID, func(tx Tx) error {
					if err := tx.SaveSubscription(ctx, userID, "stripe", obj.ID, "", "free", "canceled"); err != nil {
						return err
					}
					return tx.SetPlan(ctx, userID, "free")
				})
			}
		}
		writeJSON(w, http.StatusOK, map[string]string{"received": event.Type})
	}
}

func handleRazorpayWebhook(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		payload, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
		if err != nil || !VerifyRazorpayWebhook(payload, r.Header.Get("X-Razorpay-Signature"), deps.Razorpay.WebhookSecret) {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid signature"})
			return
		}
		var event struct {
			Event   string `json:"event"`
			Payload struct {
				Order struct {
					Entity struct {
						ID string `json:"id"`
					} `json:"entity"`
				} `json:"order"`
				Payment struct {
					Entity struct {
						ID      string `json:"id"`
						OrderID string `json:"order_id"`
					} `json:"entity"`
				} `json:"payment"`
				Subscription struct {
					Entity struct {
						ID string `json:"id"`
					} `json:"entity"`
				} `json:"subscription"`
			} `json:"payload"`
		}
		if json.Unmarshal(payload, &event) != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "malformed event"})
			return
		}
		ctx := r.Context()
		switch event.Event {
		case "order.paid", "payment.captured":
			orderID := event.Payload.Order.Entity.ID
			if orderID == "" {
				orderID = event.Payload.Payment.Entity.OrderID
			}
			if order, err := deps.Store.OrderByID(ctx, orderID); err == nil {
				if _, err := fulfil(ctx, deps, "razorpay", "order:"+order.ID, order, "", "", false); err != nil {
					writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "retry"})
					return
				}
			}
		case "subscription.activated", "subscription.charged":
			subID := event.Payload.Subscription.Entity.ID
			order, err := deps.Store.OrderByID(ctx, subID) // who bought which plan, whatever the event order
			if err != nil {
				break
			}
			if _, err := fulfil(ctx, deps, "razorpay", "order:"+order.ID, order, subID, "", false); err != nil {
				writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "retry"})
				return
			}
			if paymentID := event.Payload.Payment.Entity.ID; event.Event == "subscription.charged" && paymentID != "" {
				plan := plans.For(order.ItemID)
				if _, err := deps.Store.ApplyOnce(ctx, "razorpay", "charge:"+paymentID, "renewal", order.UserID, func(tx Tx) error {
					return tx.GrantCredits(ctx, order.UserID, plan.MonthlyCredits, "billing:razorpay:month:"+plan.ID)
				}); err != nil {
					writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "retry"})
					return
				}
			}
		case "subscription.cancelled", "subscription.halted", "subscription.completed":
			subID := event.Payload.Subscription.Entity.ID
			if userID, _, err := deps.Store.SubscriptionOwner(ctx, "razorpay", subID); err == nil {
				_, _ = deps.Store.ApplyOnce(ctx, "razorpay", "ended:"+subID, "cancel", userID, func(tx Tx) error {
					if err := tx.SaveSubscription(ctx, userID, "razorpay", subID, "", "free", "canceled"); err != nil {
						return err
					}
					return tx.SetPlan(ctx, userID, "free")
				})
			}
		}
		writeJSON(w, http.StatusOK, map[string]string{"received": event.Event})
	}
}

package billing

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"
)

// ErrNotConfigured means the provider's keys are not set yet (keys last: PC-070).
var ErrNotConfigured = errors.New("billing: payment provider not configured")

// ── Stripe ────────────────────────────────────────────────────────────────────────────────────

// Stripe talks to Stripe's REST API with a secret key (sk_test_… until go-live).
type Stripe struct {
	SecretKey     string
	WebhookSecret string
	BaseURL       string
	Client        *http.Client
}

// StripeFromEnv reads STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET.
func StripeFromEnv() *Stripe {
	return &Stripe{SecretKey: strings.TrimSpace(os.Getenv("STRIPE_SECRET_KEY")),
		WebhookSecret: strings.TrimSpace(os.Getenv("STRIPE_WEBHOOK_SECRET")), BaseURL: "https://api.stripe.com"}
}

func (s *Stripe) Configured() bool { return s != nil && s.SecretKey != "" }

// CheckoutSession is the part of Stripe's answer the platform uses.
type CheckoutSession struct {
	ID  string `json:"id"`
	URL string `json:"url"`
}

// CreateCheckout starts a hosted Stripe Checkout: a one-off payment for credits (priceMinor in
// cents, name shown to the buyer), or a subscription to a plan's Stripe price.
func (s *Stripe) CreateCheckout(ctx context.Context, subscriptionPriceID, name string, priceMinor int64,
	currency, successURL, cancelURL string, metadata map[string]string) (CheckoutSession, error) {
	if !s.Configured() {
		return CheckoutSession{}, ErrNotConfigured
	}
	form := url.Values{"success_url": {successURL}, "cancel_url": {cancelURL},
		"client_reference_id": {metadata["user_id"]}, "line_items[0][quantity]": {"1"}}
	if subscriptionPriceID != "" {
		form.Set("mode", "subscription")
		form.Set("line_items[0][price]", subscriptionPriceID)
		for k, v := range metadata {
			form.Set("subscription_data[metadata]["+k+"]", v)
		}
	} else {
		form.Set("mode", "payment")
		form.Set("line_items[0][price_data][currency]", strings.ToLower(currency))
		form.Set("line_items[0][price_data][unit_amount]", strconv.FormatInt(priceMinor, 10))
		form.Set("line_items[0][price_data][product_data][name]", name)
	}
	for k, v := range metadata {
		form.Set("metadata["+k+"]", v)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, s.BaseURL+"/v1/checkout/sessions", strings.NewReader(form.Encode()))
	if err != nil {
		return CheckoutSession{}, err
	}
	req.SetBasicAuth(s.SecretKey, "")
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	var out CheckoutSession
	return out, doJSON(s.client(), req, &out)
}

func (s *Stripe) client() *http.Client {
	if s.Client != nil {
		return s.Client
	}
	return &http.Client{Timeout: 20 * time.Second}
}

// VerifyStripeSignature checks a webhook's Stripe-Signature header ("t=…,v1=…") against the
// endpoint secret, rejecting anything older than tolerance.
func VerifyStripeSignature(payload []byte, header, secret string, now time.Time, tolerance time.Duration) error {
	if secret == "" {
		return ErrNotConfigured
	}
	var timestamp string
	var signatures []string
	for _, part := range strings.Split(header, ",") {
		key, value, _ := strings.Cut(strings.TrimSpace(part), "=")
		switch key {
		case "t":
			timestamp = value
		case "v1":
			signatures = append(signatures, value)
		}
	}
	ts, err := strconv.ParseInt(timestamp, 10, 64)
	if err != nil || len(signatures) == 0 {
		return errors.New("billing: malformed Stripe-Signature")
	}
	if age := now.Sub(time.Unix(ts, 0)); age > tolerance || age < -tolerance {
		return errors.New("billing: Stripe webhook is too old")
	}
	expected := hmacHex(secret, timestamp+"."+string(payload))
	for _, sig := range signatures {
		if hmac.Equal([]byte(sig), []byte(expected)) {
			return nil
		}
	}
	return errors.New("billing: Stripe signature does not match")
}

// ── Razorpay ──────────────────────────────────────────────────────────────────────────────────

// Razorpay talks to Razorpay's REST API with a key id and secret (rzp_test_… until go-live).
type Razorpay struct {
	KeyID         string
	KeySecret     string
	WebhookSecret string
	BaseURL       string
	Client        *http.Client
}

// RazorpayFromEnv reads RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET and RAZORPAY_WEBHOOK_SECRET.
func RazorpayFromEnv() *Razorpay {
	return &Razorpay{KeyID: strings.TrimSpace(os.Getenv("RAZORPAY_KEY_ID")),
		KeySecret:     strings.TrimSpace(os.Getenv("RAZORPAY_KEY_SECRET")),
		WebhookSecret: strings.TrimSpace(os.Getenv("RAZORPAY_WEBHOOK_SECRET")), BaseURL: "https://api.razorpay.com"}
}

func (r *Razorpay) Configured() bool { return r != nil && r.KeyID != "" && r.KeySecret != "" }

func (r *Razorpay) post(ctx context.Context, path string, body any, out any) error {
	if !r.Configured() {
		return ErrNotConfigured
	}
	payload, _ := json.Marshal(body)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, r.BaseURL+path, bytes.NewReader(payload))
	if err != nil {
		return err
	}
	req.SetBasicAuth(r.KeyID, r.KeySecret)
	req.Header.Set("Content-Type", "application/json")
	client := r.Client
	if client == nil {
		client = &http.Client{Timeout: 20 * time.Second}
	}
	return doJSON(client, req, out)
}

// CreateOrder creates a one-off order (amount in paise) for Razorpay Checkout.
func (r *Razorpay) CreateOrder(ctx context.Context, amountMinor int64, currency, receipt string, notes map[string]string) (string, error) {
	var out struct {
		ID string `json:"id"`
	}
	err := r.post(ctx, "/v1/orders", map[string]any{"amount": amountMinor, "currency": currency, "receipt": receipt, "notes": notes}, &out)
	return out.ID, err
}

// CreateSubscription subscribes to a Razorpay plan; the buyer completes it in Razorpay Checkout.
func (r *Razorpay) CreateSubscription(ctx context.Context, planID string, notes map[string]string) (string, error) {
	var out struct {
		ID string `json:"id"`
	}
	err := r.post(ctx, "/v1/subscriptions", map[string]any{"plan_id": planID, "total_count": 120, "customer_notify": 1, "notes": notes}, &out)
	return out.ID, err
}

// VerifyRazorpayPayment checks the signature Razorpay Checkout returns to the browser: the HMAC of
// "<order or subscription id>|<payment id>" (payment id first for subscriptions) with the key secret.
func VerifyRazorpayPayment(first, second, signature, keySecret string) bool {
	if keySecret == "" || signature == "" {
		return false
	}
	return hmac.Equal([]byte(hmacHex(keySecret, first+"|"+second)), []byte(signature))
}

// VerifyRazorpayWebhook checks X-Razorpay-Signature: the HMAC of the raw body with the webhook secret.
func VerifyRazorpayWebhook(body []byte, signature, secret string) bool {
	if secret == "" || signature == "" {
		return false
	}
	return hmac.Equal([]byte(hmacHex(secret, string(body))), []byte(signature))
}

// ── shared ────────────────────────────────────────────────────────────────────────────────────

func hmacHex(secret, message string) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(message))
	return hex.EncodeToString(mac.Sum(nil))
}

func doJSON(client *http.Client, req *http.Request, out any) error {
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer func() { _ = resp.Body.Close() }()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if resp.StatusCode/100 != 2 {
		// The provider's own message, never the request (which holds nothing secret anyway).
		var failure struct {
			Error struct {
				Message     string `json:"message"`
				Description string `json:"description"`
			} `json:"error"`
		}
		_ = json.Unmarshal(body, &failure)
		msg := failure.Error.Message
		if msg == "" {
			msg = failure.Error.Description
		}
		return fmt.Errorf("billing: provider answered %d: %s", resp.StatusCode, msg)
	}
	return json.Unmarshal(body, out)
}

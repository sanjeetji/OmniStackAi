package billing

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

// ── fakes ──

type memStore struct {
	mu      sync.Mutex
	orders  map[string]Order
	events  map[string]bool
	balance map[string]int64
	plan    map[string]string
	subs    map[string][2]string // subID -> user, plan
}

func newMem() *memStore {
	return &memStore{orders: map[string]Order{}, events: map[string]bool{}, balance: map[string]int64{},
		plan: map[string]string{}, subs: map[string][2]string{}}
}
func (m *memStore) RecordOrder(_ context.Context, o Order) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	o.Status = "created"
	m.orders[o.ID] = o
	return nil
}
func (m *memStore) OrderByID(_ context.Context, id string) (Order, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	o, ok := m.orders[id]
	if !ok {
		return Order{}, ErrOrderNotFound
	}
	return o, nil
}
func (m *memStore) SubscriptionOwner(_ context.Context, _ string, id string) (string, string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	s, ok := m.subs[id]
	if !ok {
		return "", "", ErrOrderNotFound
	}
	return s[0], s[1], nil
}
func (m *memStore) ApplyOnce(_ context.Context, provider, key, _ string, _ string, apply func(Tx) error) (bool, error) {
	m.mu.Lock()
	if m.events[provider+"|"+key] {
		m.mu.Unlock()
		return false, nil
	}
	m.events[provider+"|"+key] = true
	m.mu.Unlock()
	return true, apply(memTx{m})
}

type memTx struct{ m *memStore }

func (t memTx) GrantCredits(_ context.Context, u string, c int64, _ string) error {
	t.m.mu.Lock()
	t.m.balance[u] += c
	t.m.mu.Unlock()
	return nil
}
func (t memTx) SetPlan(_ context.Context, u, p string) error {
	t.m.mu.Lock()
	t.m.plan[u] = p
	t.m.mu.Unlock()
	return nil
}
func (t memTx) SaveSubscription(_ context.Context, u, _, id, _, p, _ string) error {
	t.m.mu.Lock()
	t.m.subs[id] = [2]string{u, p}
	t.m.mu.Unlock()
	return nil
}
func (t memTx) MarkOrderPaid(context.Context, string) error { return nil }

type fakeAuth struct{ user auth.User }

func (f fakeAuth) CreateUser(context.Context, string, string, string, int64) (auth.User, error) {
	return auth.User{}, nil
}
func (f fakeAuth) FindUserByEmail(context.Context, string) (auth.User, string, error) {
	return auth.User{}, "", nil
}
func (f fakeAuth) FindUserBySessionToken(context.Context, string) (auth.User, error) {
	return f.user, nil
}
func (f fakeAuth) FindUserByID(context.Context, string) (auth.User, error)        { return f.user, nil }
func (f fakeAuth) CreateSession(context.Context, string, string, time.Time) error { return nil }
func (f fakeAuth) DeleteSession(context.Context, string) error                    { return nil }

const userID = "11111111-1111-1111-1111-111111111111"

func server(t *testing.T, stripe *Stripe, razorpay *Razorpay, store *memStore) *httptest.Server {
	t.Helper()
	mux := http.NewServeMux()
	Register(mux, Deps{AuthStore: fakeAuth{auth.User{ID: userID, Plan: "free"}}, Store: store, Stripe: stripe,
		Razorpay: razorpay, PublicURL: "https://console.example"})
	srv := httptest.NewServer(mux)
	t.Cleanup(srv.Close)
	return srv
}

func post(t *testing.T, url, body string, headers map[string]string) (int, map[string]any) {
	t.Helper()
	req, _ := http.NewRequest(http.MethodPost, url, strings.NewReader(body))
	req.Header.Set("Authorization", "Bearer x")
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var out map[string]any
	_ = json.NewDecoder(resp.Body).Decode(&out)
	return resp.StatusCode, out
}

func stripeSigned(secret string, payload string, at time.Time) string {
	ts := fmt.Sprint(at.Unix())
	return "t=" + ts + ",v1=" + hmacHex(secret, ts+"."+payload)
}

// ── tests ──

func TestWithoutKeysACheckoutSaysSoAndNothingElseHappens(t *testing.T) {
	store := newMem()
	srv := server(t, &Stripe{}, &Razorpay{}, store)
	code, body := post(t, srv.URL+"/billing/checkout", `{"kind":"credits","id":"starter","provider":"stripe"}`, nil)
	if code != http.StatusServiceUnavailable || !strings.Contains(body["error"].(string), "not set up") {
		t.Fatalf("got %d %v", code, body)
	}
	if len(store.orders) != 0 {
		t.Error("an order was recorded without a checkout")
	}
}

func TestAStripeTopUpGrantsCreditsExactlyOnce(t *testing.T) {
	var form url.Values
	api := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if user, _, _ := r.BasicAuth(); user != "sk_test_x" || r.URL.Path != "/v1/checkout/sessions" {
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		body, _ := io.ReadAll(r.Body)
		form, _ = url.ParseQuery(string(body))
		_, _ = w.Write([]byte(`{"id":"cs_test_1","url":"https://checkout.stripe.test/cs_test_1"}`))
	}))
	defer api.Close()
	store := newMem()
	stripe := &Stripe{SecretKey: "sk_test_x", WebhookSecret: "whsec_test", BaseURL: api.URL}
	srv := server(t, stripe, &Razorpay{}, store)

	code, body := post(t, srv.URL+"/billing/checkout", `{"kind":"credits","id":"starter","provider":"stripe"}`, nil)
	if code != 200 || body["redirect_url"] != "https://checkout.stripe.test/cs_test_1" {
		t.Fatalf("checkout: %d %v", code, body)
	}
	if form.Get("mode") != "payment" || form.Get("line_items[0][price_data][unit_amount]") != "500" ||
		form.Get("metadata[user_id]") != userID {
		t.Errorf("Stripe was asked for %v", form)
	}

	event := `{"id":"evt_1","type":"checkout.session.completed","data":{"object":{"id":"cs_test_1","mode":"payment","payment_status":"paid"}}}`
	for i := 0; i < 2; i++ { // Stripe may deliver an event more than once
		code, _ = post(t, srv.URL+"/billing/webhooks/stripe", event, map[string]string{"Stripe-Signature": stripeSigned("whsec_test", event, time.Now())})
		if code != 200 {
			t.Fatalf("webhook %d: %d", i, code)
		}
	}
	if store.balance[userID] != 5000 {
		t.Errorf("balance %d, want 5000 granted once", store.balance[userID])
	}
}

func TestAForgedOrStaleStripeWebhookIsRejected(t *testing.T) {
	store := newMem()
	store.orders["cs_1"] = Order{ID: "cs_1", UserID: userID, Kind: "credits", Credits: 5000}
	srv := server(t, &Stripe{SecretKey: "sk_test_x", WebhookSecret: "whsec_test"}, &Razorpay{}, store)
	event := `{"id":"evt_1","type":"checkout.session.completed","data":{"object":{"id":"cs_1","mode":"payment","payment_status":"paid"}}}`
	for name, sig := range map[string]string{
		"wrong secret": stripeSigned("whsec_other", event, time.Now()),
		"stale":        stripeSigned("whsec_test", event, time.Now().Add(-time.Hour)),
		"missing":      "",
	} {
		if code, _ := post(t, srv.URL+"/billing/webhooks/stripe", event, map[string]string{"Stripe-Signature": sig}); code != 400 {
			t.Errorf("%s: got %d, want 400", name, code)
		}
	}
	if store.balance[userID] != 0 {
		t.Error("credits were granted for an unproven webhook")
	}
}

func TestARazorpayTopUpIsVerifiedAndGrantedOnceWhicheverPathArrivesFirst(t *testing.T) {
	var sent map[string]any
	api := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewDecoder(r.Body).Decode(&sent)
		_, _ = w.Write([]byte(`{"id":"order_test_1"}`))
	}))
	defer api.Close()
	store := newMem()
	rzp := &Razorpay{KeyID: "rzp_test_id", KeySecret: "rzp_secret", WebhookSecret: "rzp_whsec", BaseURL: api.URL}
	srv := server(t, &Stripe{}, rzp, store)
	code, body := post(t, srv.URL+"/billing/checkout", `{"kind":"credits","id":"starter","provider":"razorpay"}`, nil)
	if code != 200 || body["order_id"] != "order_test_1" || body["key_id"] != "rzp_test_id" || sent["amount"] != float64(42000) {
		t.Fatalf("checkout: %d %v, sent %v", code, body, sent)
	}
	if _, leaked := body["key_secret"]; leaked {
		t.Fatal("the key secret reached the browser")
	}
	sig := hmacHex("rzp_secret", "order_test_1|pay_1")
	if code, _ := post(t, srv.URL+"/billing/razorpay/verify", `{"razorpay_order_id":"order_test_1","razorpay_payment_id":"pay_1","razorpay_signature":"bad"}`, nil); code != 400 {
		t.Errorf("a bad signature was accepted: %d", code)
	}
	post(t, srv.URL+"/billing/razorpay/verify", fmt.Sprintf(`{"razorpay_order_id":"order_test_1","razorpay_payment_id":"pay_1","razorpay_signature":%q}`, sig), nil)
	hook := `{"event":"order.paid","payload":{"order":{"entity":{"id":"order_test_1"}},"payment":{"entity":{"id":"pay_1","order_id":"order_test_1"}}}}`
	post(t, srv.URL+"/billing/webhooks/razorpay", hook, map[string]string{"X-Razorpay-Signature": hmacHex("rzp_whsec", hook)})
	if store.balance[userID] != 5000 {
		t.Errorf("balance %d, want 5000 once (browser and webhook both reported it)", store.balance[userID])
	}
}

func TestPlansAreBoughtOnlyWhenPricedAndRenewMonthly(t *testing.T) {
	store := newMem()
	srv := server(t, &Stripe{SecretKey: "sk_test_x", WebhookSecret: "whsec_test"}, &Razorpay{}, store)
	if code, _ := post(t, srv.URL+"/billing/checkout", `{"kind":"plan","id":"pro","provider":"stripe"}`, nil); code != 400 {
		t.Errorf("an unpriced plan was sold: %d", code)
	}

	t.Setenv("OMNISTACKAI_PLANS", `{"pro":{"price_usd_monthly":29,"stripe_price_id":"price_pro"}}`)
	store.orders["cs_sub"] = Order{ID: "cs_sub", UserID: userID, Kind: "plan", ItemID: "pro"}
	send := func(event string) {
		post(t, srv.URL+"/billing/webhooks/stripe", event, map[string]string{"Stripe-Signature": stripeSigned("whsec_test", event, time.Now())})
	}
	send(`{"id":"e1","type":"checkout.session.completed","data":{"object":{"id":"cs_sub","mode":"subscription","subscription":"sub_1","customer":"cus_1"}}}`)
	if store.plan[userID] != "pro" || store.balance[userID] != 10000 {
		t.Fatalf("after purchase: plan %q balance %d", store.plan[userID], store.balance[userID])
	}
	send(`{"id":"e2","type":"invoice.paid","data":{"object":{"id":"in_1","billing_reason":"subscription_create","subscription":"sub_1"}}}`)
	send(`{"id":"e3","type":"invoice.paid","data":{"object":{"id":"in_2","billing_reason":"subscription_cycle","subscription":"sub_1"}}}`)
	send(`{"id":"e3","type":"invoice.paid","data":{"object":{"id":"in_2","billing_reason":"subscription_cycle","subscription":"sub_1"}}}`)
	if store.balance[userID] != 20000 {
		t.Errorf("balance %d, want first month + one renewal = 20000", store.balance[userID])
	}
	send(`{"id":"e4","type":"customer.subscription.deleted","data":{"object":{"id":"sub_1"}}}`)
	if store.plan[userID] != "free" {
		t.Errorf("plan %q after cancellation, want free", store.plan[userID])
	}
}

func TestARazorpaySubscriptionGrantsEachMonthOnce(t *testing.T) {
	store := newMem()
	store.orders["sub_rzp"] = Order{ID: "sub_rzp", UserID: userID, Kind: "plan", ItemID: "developer"}
	srv := server(t, &Stripe{}, &Razorpay{KeyID: "k", KeySecret: "s", WebhookSecret: "w"}, store)
	send := func(event string) {
		post(t, srv.URL+"/billing/webhooks/razorpay", event, map[string]string{"X-Razorpay-Signature": hmacHex("w", event)})
	}
	charged := func(pay string) string {
		return `{"event":"subscription.charged","payload":{"subscription":{"entity":{"id":"sub_rzp"}},"payment":{"entity":{"id":"` + pay + `"}}}}`
	}
	send(`{"event":"subscription.activated","payload":{"subscription":{"entity":{"id":"sub_rzp"}}}}`)
	send(charged("pay_m1"))
	send(charged("pay_m1")) // redelivered
	if store.plan[userID] != "developer" || store.balance[userID] != 2000 {
		t.Fatalf("first month: plan %q balance %d, want developer and 2000 once", store.plan[userID], store.balance[userID])
	}
	send(charged("pay_m2"))
	if store.balance[userID] != 4000 {
		t.Errorf("after the second month: %d, want 4000", store.balance[userID])
	}
}

// PC-012: deleting an account cancels its paid plan at the provider first.
func TestCancellingAPlanReachesTheProvider(t *testing.T) {
	var seen []string
	api := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seen = append(seen, r.Method+" "+r.URL.Path)
		_, _ = w.Write([]byte(`{"id":"x","status":"cancelled"}`))
	}))
	defer api.Close()
	stripe := &Stripe{SecretKey: "sk_test_x", BaseURL: api.URL}
	razorpay := &Razorpay{KeyID: "rzp_test", KeySecret: "s", BaseURL: api.URL}
	ctx := context.Background()
	if err := CancelSubscription(ctx, stripe, razorpay, "stripe", "sub_1"); err != nil {
		t.Fatal(err)
	}
	if err := CancelSubscription(ctx, stripe, razorpay, "razorpay", "sub_2"); err != nil {
		t.Fatal(err)
	}
	want := []string{"DELETE /v1/subscriptions/sub_1", "POST /v1/subscriptions/sub_2/cancel"}
	if strings.Join(seen, ",") != strings.Join(want, ",") {
		t.Fatalf("calls = %v", seen)
	}
	if CancelSubscription(ctx, &Stripe{}, razorpay, "stripe", "sub_1") == nil {
		t.Fatal("an unconfigured provider cannot report a cancellation")
	}
}

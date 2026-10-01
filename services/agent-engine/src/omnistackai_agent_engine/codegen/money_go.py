"""R-567: the money handlers of a generated Go backend (`internal/handlers/money.go`).

The same books as the Python module (see `money_python.py` and `application_ir/money.py`): integer
minor units, a double-entry ledger whose sums are the balances, the amount read from the record,
the mock provider offline and Stripe / Razorpay with verified, idempotent webhooks.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR
from ..application_ir.money import money_of
from ..application_ir.ownership import ownership_for_entity
from .schema_sql import sql_identifier, table_name

#: (method, path, handler, guarded) - registered in main.go.
GO_MONEY_ROUTES = (
    ("POST", "/payments/checkout", "MoneyCheckout", True),
    ("POST", "/payments/{paymentId}/confirm", "MoneyConfirm", True),
    ("POST", "/payments/{paymentId}/refund", "MoneyRefund", True),
    ("GET", "/payments", "MoneyPayments", True),
    ("POST", "/payments/webhooks/stripe", "MoneyStripeWebhook", False),
    ("POST", "/payments/webhooks/razorpay", "MoneyRazorpayWebhook", False),
    ("GET", "/money/balance", "MoneyBalance", True),
    ("GET", "/money/ledger", "MoneyLedger", True),
    ("GET", "/money/summary", "MoneySummary", True),
    ("POST", "/money/payouts", "MoneyRequestPayout", True),
    ("GET", "/money/payouts", "MoneyPayouts", True),
    ("POST", "/money/payouts/{payoutId}/pay", "MoneyPayPayout", True),
    ("POST", "/money/payouts/{payoutId}/reject", "MoneyRejectPayout", True),
)


def _go_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def go_money_file(ir: ApplicationIR) -> str:
    money = money_of(ir)
    assert money is not None
    charges = []
    for charge in money.charges:
        entity = next(e for e in ir.entities if e.name == charge.entity)
        rule = ownership_for_entity(ir, charge.entity)
        paid = next((f.name for f in entity.fields if f.name in ("paid", "is_paid") and f.type.value == "bool"), None)
        see_all = ", ".join(_go_str(r) for r in (rule.bypass_roles if rule else ()))
        charges.append(
            f"\t{_go_str(table_name(charge.entity))}: {{Entity: {_go_str(charge.entity)}, "
            f"Table: {_go_str(sql_identifier(table_name(charge.entity)))}, Amount: {_go_str(sql_identifier(charge.amount))}, "
            f"Payee: {_go_str(sql_identifier(charge.payee) if charge.payee else '')}, "
            f"Paid: {_go_str(sql_identifier(paid) if paid else '')}, "
            f"Assignee: {_go_str(sql_identifier(rule.assignee) if rule and rule.assignee else '')}, "
            f"Owned: {'true' if rule is not None and rule.reads_own else 'false'}, SeeAll: []string{{{see_all}}}}},"
        )
    config = (
        f"const moneyCurrency = {_go_str(money.currency)}\n"
        f"const moneyMinor = {money.minor_unit}\n"
        f"const commissionBps = {money.commission_bps}\n\n"
        f"var refunders = []string{{{', '.join(_go_str(r) for r in money.refunders)}}}\n\n"
        "var moneyCharges = map[string]moneyCharge{\n" + "\n".join(charges) + "\n}\n"
    )
    return _GO.replace("__CONFIG__", config)


_GO = r'''package handlers

// Money: payments, a double-entry ledger, refunds, commission and payouts (OmniStackAI R-567).
//
// Amounts are integers in the currency's minor unit. Every ledger entry moves `amount` from the
// `debit` account to the `credit` account; a balance is credits minus debits, so the books always sum
// to zero. The amount to pay is read from the stored record, never the client. PAYMENT_PROVIDER picks
// mock (the default with no keys), stripe or razorpay; real providers mark a payment paid only from
// their signed webhook.

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"database/sql"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"math/big"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"
)

type moneyCharge struct {
	Entity, Table, Amount, Payee, Paid, Assignee string
	Owned                                        bool
	SeeAll                                       []string
}

__CONFIG__
const webhookToleranceSeconds = 300

type querier interface {
	QueryRowContext(ctx context.Context, query string, args ...any) *sql.Row
	ExecContext(ctx context.Context, query string, args ...any) (sql.Result, error)
	QueryContext(ctx context.Context, query string, args ...any) (*sql.Rows, error)
}

type moneyFail struct {
	status int
	msg    string
}

func (e moneyFail) Error() string { return e.msg }

func moneyRespond(w http.ResponseWriter, err error) {
	if f, ok := err.(moneyFail); ok {
		writeJSON(w, f.status, map[string]string{"detail": f.msg})
		return
	}
	dbError(w, err)
}

func paymentProvider() string {
	if chosen := strings.ToLower(strings.TrimSpace(os.Getenv("PAYMENT_PROVIDER"))); chosen != "" {
		return chosen
	}
	if os.Getenv("STRIPE_SECRET_KEY") != "" {
		return "stripe"
	}
	if os.Getenv("RAZORPAY_KEY_ID") != "" {
		return "razorpay"
	}
	return "mock"
}

// toMinor turns a stored price ("499.5") into minor units (49950), rounding half up, without floats.
func toMinor(text string) int64 {
	r, ok := new(big.Rat).SetString(strings.TrimSpace(text))
	if !ok || r.Sign() <= 0 {
		return 0
	}
	r.Mul(r, big.NewRat(moneyMinor, 1))
	num := new(big.Int).Mul(r.Num(), big.NewInt(2))
	num.Add(num, r.Denom())
	den := new(big.Int).Mul(r.Denom(), big.NewInt(2))
	return new(big.Int).Quo(num, den).Int64()
}

func moneyAccount(ctx context.Context, q querier, kind, holder string) (string, error) {
	var id string
	if kind == "user" {
		if _, err := q.ExecContext(ctx, `INSERT INTO money_account (kind, holder_id) VALUES ('user', $1) ON CONFLICT (kind, COALESCE(holder_id, '00000000-0000-0000-0000-000000000000'::uuid)) DO NOTHING`, holder); err != nil {
			return "", err
		}
		err := q.QueryRowContext(ctx, `SELECT id FROM money_account WHERE kind = 'user' AND holder_id = $1`, holder).Scan(&id)
		return id, err
	}
	err := q.QueryRowContext(ctx, `SELECT id FROM money_account WHERE kind = $1 AND holder_id IS NULL`, kind).Scan(&id)
	return id, err
}

func postEntry(ctx context.Context, q querier, debit, credit string, amount int64, kind, paymentID, payoutID string) error {
	if amount <= 0 {
		return nil
	}
	_, err := q.ExecContext(ctx, `INSERT INTO ledger_entry (debit, credit, amount, kind, payment_id, payout_id) VALUES ($1, $2, $3, $4, NULLIF($5, '')::uuid, NULLIF($6, '')::uuid)`,
		debit, credit, amount, kind, paymentID, payoutID)
	return err
}

func accountBalance(ctx context.Context, q querier, id string) (int64, error) {
	var b int64
	err := q.QueryRowContext(ctx, `SELECT COALESCE(SUM(CASE WHEN credit = $1 THEN amount ELSE -amount END), 0) FROM ledger_entry WHERE credit = $1 OR debit = $1`, id).Scan(&b)
	return b, err
}

type paymentRow struct {
	ID          string    `json:"id"`
	Entity      string    `json:"entity"`
	RecordID    string    `json:"record_id"`
	PayerID     *string   `json:"payer_id"`
	PayeeID     *string   `json:"payee_id"`
	Amount      int64     `json:"amount"`
	Commission  int64     `json:"commission"`
	Currency    string    `json:"currency"`
	Status      string    `json:"status"`
	Refunded    int64     `json:"refunded"`
	Provider    string    `json:"provider"`
	ProviderRef *string   `json:"provider_ref"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

const paymentCols = `id, entity, record_id, payer_id, payee_id, amount, commission, currency, status, refunded, provider, provider_ref, created_at, updated_at`

func scanPayment(row interface{ Scan(...any) error }) (*paymentRow, error) {
	var p paymentRow
	err := row.Scan(&p.ID, &p.Entity, &p.RecordID, &p.PayerID, &p.PayeeID, &p.Amount, &p.Commission, &p.Currency,
		&p.Status, &p.Refunded, &p.Provider, &p.ProviderRef, &p.CreatedAt, &p.UpdatedAt)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	return &p, err
}

func chargeFor(entity string) (moneyCharge, bool) {
	key := strings.ToLower(entity)
	if c, ok := moneyCharges[key]; ok {
		return c, true
	}
	for _, c := range moneyCharges {
		if strings.ToLower(c.Entity) == key {
			return c, true
		}
	}
	return moneyCharge{}, false
}

func colOrNull(col string) string {
	if col == "" {
		return "NULL"
	}
	return col
}

// --- paying -------------------------------------------------------------------------------------

func (h *Handlers) MoneyCheckout(w http.ResponseWriter, r *http.Request) {
	var in struct {
		Entity   string `json:"entity"`
		RecordID string `json:"record_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		http.Error(w, "invalid body", http.StatusBadRequest)
		return
	}
	charge, ok := chargeFor(in.Entity)
	if !ok {
		moneyRespond(w, moneyFail{http.StatusNotFound, "nothing to pay for"})
		return
	}
	claims := ClaimsFrom(r)
	ctx := r.Context()
	var amountText, payee, createdBy, assignee string
	query := fmt.Sprintf(`SELECT %s::text, COALESCE(%s::text, ''), COALESCE("created_by"::text, ''), COALESCE(%s::text, '') FROM %s WHERE "id" = $1`,
		charge.Amount, colOrNull(charge.Payee), colOrNull(charge.Assignee), charge.Table)
	err := h.DB.QueryRowContext(ctx, query, in.RecordID).Scan(&amountText, &payee, &createdBy, &assignee)
	if err == sql.ErrNoRows || (err == nil && charge.Owned && !CanTouchAssigned(claims, createdBy, assignee, charge.SeeAll...)) {
		moneyRespond(w, moneyFail{http.StatusNotFound, "not_found"})
		return
	}
	if err != nil {
		dbError(w, err)
		return
	}
	var paid bool
	if err := h.DB.QueryRowContext(ctx, `SELECT EXISTS (SELECT 1 FROM payment WHERE entity = $1 AND record_id = $2 AND status = 'succeeded')`,
		charge.Entity, in.RecordID).Scan(&paid); err != nil {
		dbError(w, err)
		return
	}
	if paid {
		moneyRespond(w, moneyFail{http.StatusConflict, "already paid"})
		return
	}
	amount := toMinor(amountText) // from the record, never the client
	if amount <= 0 {
		moneyRespond(w, moneyFail{http.StatusUnprocessableEntity, "nothing to pay: the amount is zero"})
		return
	}
	commission := amount
	if payee != "" {
		commission = amount * commissionBps / 10000
	}
	provider := paymentProvider()
	var paymentID string
	if err := h.DB.QueryRowContext(ctx, `INSERT INTO payment (entity, record_id, payer_id, payee_id, amount, commission, currency, provider) VALUES ($1, $2, NULLIF($3, '')::uuid, NULLIF($4, '')::uuid, $5, $6, $7, $8) RETURNING id`,
		charge.Entity, in.RecordID, OwnerOf(claims), payee, amount, commission, moneyCurrency, provider).Scan(&paymentID); err != nil {
		dbError(w, err)
		return
	}
	out := map[string]any{"payment_id": paymentID, "amount": amount, "currency": moneyCurrency, "provider": provider}
	switch provider {
	case "mock":
		out["confirm"] = "/payments/" + paymentID + "/confirm"
	case "stripe":
		form := url.Values{}
		form.Set("mode", "payment")
		form.Set("line_items[0][quantity]", "1")
		form.Set("line_items[0][price_data][currency]", strings.ToLower(moneyCurrency))
		form.Set("line_items[0][price_data][unit_amount]", strconv.FormatInt(amount, 10))
		form.Set("line_items[0][price_data][product_data][name]", charge.Entity+" "+in.RecordID[:8])
		form.Set("metadata[payment_id]", paymentID)
		form.Set("payment_intent_data[metadata][payment_id]", paymentID)
		form.Set("success_url", envOr("PAYMENT_SUCCESS_URL", "http://localhost:3000/checkout/success"))
		form.Set("cancel_url", envOr("PAYMENT_CANCEL_URL", "http://localhost:3000/checkout/cancel"))
		session, err := stripeRequest("/v1/checkout/sessions", form)
		if err != nil {
			moneyRespond(w, err)
			return
		}
		if _, err := h.DB.ExecContext(ctx, `UPDATE payment SET provider_ref = $1 WHERE id = $2`, session["id"], paymentID); err != nil {
			dbError(w, err)
			return
		}
		out["url"] = session["url"]
	case "razorpay":
		order, err := razorpayRequest("/v1/orders", map[string]any{"amount": amount, "currency": moneyCurrency, "receipt": paymentID,
			"notes": map[string]string{"payment_id": paymentID}})
		if err != nil {
			moneyRespond(w, err)
			return
		}
		if _, err := h.DB.ExecContext(ctx, `UPDATE payment SET provider_ref = $1 WHERE id = $2`, order["id"], paymentID); err != nil {
			dbError(w, err)
			return
		}
		out["order_id"] = order["id"]
		out["key_id"] = os.Getenv("RAZORPAY_KEY_ID")
	default:
		moneyRespond(w, moneyFail{http.StatusInternalServerError, "unknown PAYMENT_PROVIDER " + provider})
		return
	}
	writeJSON(w, http.StatusOK, out)
}

func envOr(name, fallback string) string {
	if v := os.Getenv(name); v != "" {
		return v
	}
	return fallback
}

// MoneyConfirm is the mock provider's "payment succeeded"; real providers confirm only by webhook.
func (h *Handlers) MoneyConfirm(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	p, err := scanPayment(h.DB.QueryRowContext(ctx, `SELECT `+paymentCols+` FROM payment WHERE id = $1`, r.PathValue("paymentId")))
	if err != nil {
		dbError(w, err)
		return
	}
	me := OwnerOf(ClaimsFrom(r))
	if p == nil || p.Provider != "mock" || p.PayerID == nil || *p.PayerID != me || me == "" {
		moneyRespond(w, moneyFail{http.StatusNotFound, "not_found"})
		return
	}
	settled, err := h.settle(ctx, p.ID, "mock_"+p.ID)
	if err != nil {
		moneyRespond(w, err)
		return
	}
	writeJSON(w, http.StatusOK, settled)
}

// settle marks a payment succeeded and books it: cash in, then the commission and the payee's share.
func (h *Handlers) settle(ctx context.Context, paymentID, ref string) (*paymentRow, error) {
	tx, err := h.DB.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	p, err := scanPayment(tx.QueryRowContext(ctx, `SELECT `+paymentCols+` FROM payment WHERE id = $1 FOR UPDATE`, paymentID))
	if err != nil {
		return nil, err
	}
	if p == nil {
		return nil, moneyFail{http.StatusNotFound, "not_found"}
	}
	if p.Status == "succeeded" {
		return p, tx.Commit() // a retried webhook: already booked
	}
	if p, err = scanPayment(tx.QueryRowContext(ctx, `UPDATE payment SET status = 'succeeded', provider_ref = $1, updated_at = NOW() WHERE id = $2 RETURNING `+paymentCols, ref, paymentID)); err != nil {
		return nil, err
	}
	external, err := moneyAccount(ctx, tx, "external", "")
	if err != nil {
		return nil, err
	}
	escrow, err := moneyAccount(ctx, tx, "escrow", "")
	if err != nil {
		return nil, err
	}
	revenue, err := moneyAccount(ctx, tx, "revenue", "")
	if err != nil {
		return nil, err
	}
	if err := postEntry(ctx, tx, external, escrow, p.Amount, "payment", p.ID, ""); err != nil {
		return nil, err
	}
	if err := postEntry(ctx, tx, escrow, revenue, p.Commission, "commission", p.ID, ""); err != nil {
		return nil, err
	}
	if p.PayeeID != nil {
		payee, err := moneyAccount(ctx, tx, "user", *p.PayeeID)
		if err != nil {
			return nil, err
		}
		if err := postEntry(ctx, tx, escrow, payee, p.Amount-p.Commission, "sale", p.ID, ""); err != nil {
			return nil, err
		}
	}
	if charge, ok := chargeFor(p.Entity); ok && charge.Paid != "" {
		if _, err := tx.ExecContext(ctx, fmt.Sprintf(`UPDATE %s SET %s = TRUE WHERE "id" = $1`, charge.Table, charge.Paid), p.RecordID); err != nil {
			return nil, err
		}
	}
	return p, tx.Commit()
}

// --- real providers ---------------------------------------------------------------------------------

func providerCall(req *http.Request) (map[string]any, error) {
	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, moneyFail{http.StatusBadGateway, "payment provider unreachable"}
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if resp.StatusCode >= 300 {
		return nil, moneyFail{http.StatusBadGateway, "payment provider refused: " + string(body[:min(len(body), 300)])}
	}
	out := map[string]any{}
	return out, json.Unmarshal(body, &out)
}

func stripeRequest(path string, form url.Values) (map[string]any, error) {
	key := os.Getenv("STRIPE_SECRET_KEY")
	if key == "" {
		return nil, moneyFail{http.StatusServiceUnavailable, "STRIPE_SECRET_KEY is not set"}
	}
	req, _ := http.NewRequest(http.MethodPost, "https://api.stripe.com"+path, strings.NewReader(form.Encode()))
	req.Header.Set("Authorization", "Bearer "+key)
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	return providerCall(req)
}

func razorpayRequest(path string, body map[string]any) (map[string]any, error) {
	key, secret := os.Getenv("RAZORPAY_KEY_ID"), os.Getenv("RAZORPAY_KEY_SECRET")
	if key == "" || secret == "" {
		return nil, moneyFail{http.StatusServiceUnavailable, "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are not set"}
	}
	raw, _ := json.Marshal(body)
	req, _ := http.NewRequest(http.MethodPost, "https://api.razorpay.com"+path, bytes.NewReader(raw))
	req.Header.Set("Authorization", "Basic "+base64.StdEncoding.EncodeToString([]byte(key+":"+secret)))
	req.Header.Set("Content-Type", "application/json")
	return providerCall(req)
}

// VerifyStripe checks a Stripe-Signature header, refusing events older than the tolerance (replays).
func VerifyStripe(payload []byte, header, secret string, now time.Time) bool {
	var timestamp, signature string
	for _, part := range strings.Split(header, ",") {
		if k, v, ok := strings.Cut(part, "="); ok {
			switch k {
			case "t":
				timestamp = v
			case "v1":
				signature = v
			}
		}
	}
	ts, err := strconv.ParseInt(timestamp, 10, 64)
	if err != nil || signature == "" {
		return false
	}
	if d := now.Unix() - ts; d > webhookToleranceSeconds || d < -webhookToleranceSeconds {
		return false
	}
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(timestamp + "."))
	mac.Write(payload)
	return hmac.Equal([]byte(hex.EncodeToString(mac.Sum(nil))), []byte(signature))
}

func VerifyRazorpay(payload []byte, signature, secret string) bool {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(payload)
	return signature != "" && hmac.Equal([]byte(hex.EncodeToString(mac.Sum(nil))), []byte(signature))
}

func (h *Handlers) firstTime(ctx context.Context, provider, eventID string) (bool, error) {
	res, err := h.DB.ExecContext(ctx, `INSERT INTO processed_event (provider, event_id) VALUES ($1, $2) ON CONFLICT DO NOTHING`, provider, eventID)
	if err != nil {
		return false, err
	}
	n, _ := res.RowsAffected()
	return n == 1, nil
}

func (h *Handlers) settleChecked(ctx context.Context, paymentID string, amount int64, currency, ref string) error {
	var want int64
	var cur string
	err := h.DB.QueryRowContext(ctx, `SELECT amount, currency FROM payment WHERE id = $1`, paymentID).Scan(&want, &cur)
	if err != nil || want != amount || !strings.EqualFold(cur, currency) {
		return moneyFail{http.StatusBadRequest, "payment does not match"} // what was charged must be what we asked
	}
	_, err = h.settle(ctx, paymentID, ref)
	return err
}

func (h *Handlers) MoneyStripeWebhook(w http.ResponseWriter, r *http.Request) {
	payload, _ := io.ReadAll(http.MaxBytesReader(w, r.Body, 1<<20))
	secret := os.Getenv("STRIPE_WEBHOOK_SECRET")
	if secret == "" || !VerifyStripe(payload, r.Header.Get("Stripe-Signature"), secret, time.Now()) {
		moneyRespond(w, moneyFail{http.StatusBadRequest, "invalid signature"})
		return
	}
	var event struct {
		ID   string `json:"id"`
		Type string `json:"type"`
		Data struct {
			Object struct {
				ID            string            `json:"id"`
				AmountTotal   int64             `json:"amount_total"`
				Currency      string            `json:"currency"`
				PaymentIntent string            `json:"payment_intent"`
				Metadata      map[string]string `json:"metadata"`
			} `json:"object"`
		} `json:"data"`
	}
	if err := json.Unmarshal(payload, &event); err != nil {
		moneyRespond(w, moneyFail{http.StatusBadRequest, "invalid event"})
		return
	}
	first, err := h.firstTime(r.Context(), "stripe", event.ID)
	if err != nil {
		dbError(w, err)
		return
	}
	if !first {
		writeJSON(w, http.StatusOK, map[string]any{"received": true, "duplicate": true})
		return
	}
	if event.Type == "checkout.session.completed" {
		o := event.Data.Object
		ref := o.PaymentIntent
		if ref == "" {
			ref = o.ID
		}
		if err := h.settleChecked(r.Context(), o.Metadata["payment_id"], o.AmountTotal, o.Currency, ref); err != nil {
			moneyRespond(w, err)
			return
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{"received": true})
}

func (h *Handlers) MoneyRazorpayWebhook(w http.ResponseWriter, r *http.Request) {
	payload, _ := io.ReadAll(http.MaxBytesReader(w, r.Body, 1<<20))
	secret := os.Getenv("RAZORPAY_WEBHOOK_SECRET")
	if secret == "" || !VerifyRazorpay(payload, r.Header.Get("X-Razorpay-Signature"), secret) {
		moneyRespond(w, moneyFail{http.StatusBadRequest, "invalid signature"})
		return
	}
	var event struct {
		Event     string `json:"event"`
		CreatedAt int64  `json:"created_at"`
		Payload   struct {
			Payment struct {
				Entity struct {
					ID       string            `json:"id"`
					Amount   int64             `json:"amount"`
					Currency string            `json:"currency"`
					Notes    map[string]string `json:"notes"`
				} `json:"entity"`
			} `json:"payment"`
		} `json:"payload"`
	}
	if err := json.Unmarshal(payload, &event); err != nil {
		moneyRespond(w, moneyFail{http.StatusBadRequest, "invalid event"})
		return
	}
	eventID := r.Header.Get("X-Razorpay-Event-Id")
	if eventID == "" {
		eventID = strconv.FormatInt(event.CreatedAt, 10)
	}
	first, err := h.firstTime(r.Context(), "razorpay", eventID)
	if err != nil {
		dbError(w, err)
		return
	}
	if !first {
		writeJSON(w, http.StatusOK, map[string]any{"received": true, "duplicate": true})
		return
	}
	if event.Event == "payment.captured" || event.Event == "order.paid" {
		e := event.Payload.Payment.Entity
		if err := h.settleChecked(r.Context(), e.Notes["payment_id"], e.Amount, e.Currency, e.ID); err != nil {
			moneyRespond(w, err)
			return
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{"received": true})
}

// --- refunds --------------------------------------------------------------------------------------

func (h *Handlers) MoneyRefund(w http.ResponseWriter, r *http.Request) {
	claims := ClaimsFrom(r)
	if !SeesAll(claims, refunders...) {
		moneyRespond(w, moneyFail{http.StatusForbidden, "forbidden"})
		return
	}
	var in struct {
		Amount *int64 `json:"amount"`
	}
	_ = json.NewDecoder(r.Body).Decode(&in)
	ctx := r.Context()
	updated, err := func() (*paymentRow, error) {
		tx, err := h.DB.BeginTx(ctx, nil)
		if err != nil {
			return nil, err
		}
		defer tx.Rollback()
		p, err := scanPayment(tx.QueryRowContext(ctx, `SELECT `+paymentCols+` FROM payment WHERE id = $1 FOR UPDATE`, r.PathValue("paymentId")))
		if err != nil {
			return nil, err
		}
		if p == nil || p.Status != "succeeded" {
			return nil, moneyFail{http.StatusNotFound, "not_found"}
		}
		remaining := p.Amount - p.Refunded
		amount := remaining
		if in.Amount != nil {
			amount = *in.Amount
		}
		if amount <= 0 || amount > remaining {
			return nil, moneyFail{http.StatusUnprocessableEntity, fmt.Sprintf("refund 1..%d", remaining)}
		}
		switch p.Provider {
		case "stripe":
			form := url.Values{}
			form.Set("payment_intent", deref(p.ProviderRef))
			form.Set("amount", strconv.FormatInt(amount, 10))
			if _, err := stripeRequest("/v1/refunds", form); err != nil {
				return nil, err
			}
		case "razorpay":
			if _, err := razorpayRequest("/v1/payments/"+deref(p.ProviderRef)+"/refund", map[string]any{"amount": amount}); err != nil {
				return nil, err
			}
		}
		external, err := moneyAccount(ctx, tx, "external", "")
		if err != nil {
			return nil, err
		}
		var payeeShare int64
		if p.PayeeID != nil {
			// Taken back in proportion: the payee's share from the payee, the rest from revenue.
			payeeShare = amount * (p.Amount - p.Commission) / p.Amount
			payee, err := moneyAccount(ctx, tx, "user", *p.PayeeID)
			if err != nil {
				return nil, err
			}
			if err := postEntry(ctx, tx, payee, external, payeeShare, "refund", p.ID, ""); err != nil {
				return nil, err
			}
		}
		revenue, err := moneyAccount(ctx, tx, "revenue", "")
		if err != nil {
			return nil, err
		}
		if err := postEntry(ctx, tx, revenue, external, amount-payeeShare, "refund", p.ID, ""); err != nil {
			return nil, err
		}
		if p, err = scanPayment(tx.QueryRowContext(ctx, `UPDATE payment SET refunded = refunded + $1, updated_at = NOW() WHERE id = $2 RETURNING `+paymentCols, amount, p.ID)); err != nil {
			return nil, err
		}
		if charge, ok := chargeFor(p.Entity); ok && charge.Paid != "" && p.Refunded == p.Amount {
			if _, err := tx.ExecContext(ctx, fmt.Sprintf(`UPDATE %s SET %s = FALSE WHERE "id" = $1`, charge.Table, charge.Paid), p.RecordID); err != nil {
				return nil, err
			}
		}
		return p, tx.Commit()
	}()
	if err != nil {
		moneyRespond(w, err)
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func deref(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

func (h *Handlers) MoneyPayments(w http.ResponseWriter, r *http.Request) {
	claims := ClaimsFrom(r)
	conds, args := []string{}, []any{}
	if !SeesAll(claims, refunders...) {
		me := OwnerOf(claims)
		if me == "" {
			me = "00000000-0000-0000-0000-000000000000"
		}
		args = append(args, me)
		conds = append(conds, fmt.Sprintf("(payer_id = $%d OR payee_id = $%d)", len(args), len(args)))
	}
	if v := r.URL.Query().Get("entity"); v != "" {
		args = append(args, v)
		conds = append(conds, fmt.Sprintf("lower(entity) = lower($%d)", len(args)))
	}
	if v := r.URL.Query().Get("record_id"); v != "" {
		args = append(args, v)
		conds = append(conds, fmt.Sprintf("record_id = $%d", len(args)))
	}
	where := ""
	if len(conds) > 0 {
		where = " WHERE " + strings.Join(conds, " AND ")
	}
	rows, err := h.DB.QueryContext(r.Context(), `SELECT `+paymentCols+` FROM payment`+where+` ORDER BY created_at DESC LIMIT 200`, args...)
	if err != nil {
		dbError(w, err)
		return
	}
	defer rows.Close()
	out := []paymentRow{}
	for rows.Next() {
		p, err := scanPayment(rows)
		if err != nil {
			dbError(w, err)
			return
		}
		out = append(out, *p)
	}
	writeJSON(w, http.StatusOK, out)
}

// --- balances, the ledger and payouts ------------------------------------------------------------------

func (h *Handlers) pendingPayouts(ctx context.Context, q querier, holder string) (int64, error) {
	var p int64
	err := q.QueryRowContext(ctx, `SELECT COALESCE(SUM(amount), 0) FROM payout WHERE holder_id = $1 AND status = 'requested'`, holder).Scan(&p)
	return p, err
}

func (h *Handlers) MoneyBalance(w http.ResponseWriter, r *http.Request) {
	me := OwnerOf(ClaimsFrom(r))
	out := map[string]any{"currency": moneyCurrency, "minor_unit": moneyMinor, "balance": 0, "pending_payouts": 0, "available": 0}
	if me != "" {
		ctx := r.Context()
		mine, err := moneyAccount(ctx, h.DB, "user", me)
		if err != nil {
			dbError(w, err)
			return
		}
		total, err := accountBalance(ctx, h.DB, mine)
		if err != nil {
			dbError(w, err)
			return
		}
		pending, err := h.pendingPayouts(ctx, h.DB, me)
		if err != nil {
			dbError(w, err)
			return
		}
		out["balance"], out["pending_payouts"], out["available"] = total, pending, total-pending
	}
	writeJSON(w, http.StatusOK, out)
}

func (h *Handlers) MoneyLedger(w http.ResponseWriter, r *http.Request) {
	type entry struct {
		ID        string    `json:"id"`
		Kind      string    `json:"kind"`
		PaymentID *string   `json:"payment_id"`
		PayoutID  *string   `json:"payout_id"`
		CreatedAt time.Time `json:"created_at"`
		Amount    int64     `json:"amount"`
	}
	out := []entry{}
	me := OwnerOf(ClaimsFrom(r))
	if me != "" {
		ctx := r.Context()
		mine, err := moneyAccount(ctx, h.DB, "user", me)
		if err != nil {
			dbError(w, err)
			return
		}
		rows, err := h.DB.QueryContext(ctx, `SELECT id, kind, payment_id, payout_id, created_at, CASE WHEN credit = $1 THEN amount ELSE -amount END FROM ledger_entry WHERE credit = $1 OR debit = $1 ORDER BY created_at DESC LIMIT 200`, mine)
		if err != nil {
			dbError(w, err)
			return
		}
		defer rows.Close()
		for rows.Next() {
			var e entry
			if err := rows.Scan(&e.ID, &e.Kind, &e.PaymentID, &e.PayoutID, &e.CreatedAt, &e.Amount); err != nil {
				dbError(w, err)
				return
			}
			out = append(out, e)
		}
	}
	writeJSON(w, http.StatusOK, out)
}

// MoneySummary is the platform's books: what it holds, what it earned, what users are owed - balanced.
func (h *Handlers) MoneySummary(w http.ResponseWriter, r *http.Request) {
	if !SeesAll(ClaimsFrom(r), refunders...) {
		moneyRespond(w, moneyFail{http.StatusForbidden, "forbidden"})
		return
	}
	ctx := r.Context()
	out := map[string]any{"currency": moneyCurrency, "minor_unit": moneyMinor}
	var total int64
	for _, kind := range []string{"external", "escrow", "revenue"} {
		id, err := moneyAccount(ctx, h.DB, kind, "")
		if err != nil {
			dbError(w, err)
			return
		}
		b, err := accountBalance(ctx, h.DB, id)
		if err != nil {
			dbError(w, err)
			return
		}
		out[kind] = b
		total += b
	}
	var owed int64
	if err := h.DB.QueryRowContext(ctx, `SELECT COALESCE(SUM(CASE WHEN l.credit = a.id THEN l.amount ELSE -l.amount END), 0) FROM money_account a JOIN ledger_entry l ON l.credit = a.id OR l.debit = a.id WHERE a.kind = 'user'`).Scan(&owed); err != nil {
		dbError(w, err)
		return
	}
	out["owed_to_users"] = owed
	out["balanced"] = total+owed == 0
	writeJSON(w, http.StatusOK, out)
}

type payoutRow struct {
	ID        string     `json:"id"`
	HolderID  string     `json:"holder_id"`
	Amount    int64      `json:"amount"`
	Status    string     `json:"status"`
	Reference *string    `json:"reference"`
	CreatedAt time.Time  `json:"created_at"`
	DecidedAt *time.Time `json:"decided_at"`
}

const payoutCols = `id, holder_id, amount, status, reference, created_at, decided_at`

func scanPayout(row interface{ Scan(...any) error }) (*payoutRow, error) {
	var p payoutRow
	err := row.Scan(&p.ID, &p.HolderID, &p.Amount, &p.Status, &p.Reference, &p.CreatedAt, &p.DecidedAt)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	return &p, err
}

func (h *Handlers) MoneyRequestPayout(w http.ResponseWriter, r *http.Request) {
	me := OwnerOf(ClaimsFrom(r))
	if me == "" {
		moneyRespond(w, moneyFail{http.StatusUnprocessableEntity, "nothing to pay out"})
		return
	}
	var in struct {
		Amount *int64 `json:"amount"`
	}
	_ = json.NewDecoder(r.Body).Decode(&in)
	ctx := r.Context()
	payout, err := func() (*payoutRow, error) {
		tx, err := h.DB.BeginTx(ctx, nil)
		if err != nil {
			return nil, err
		}
		defer tx.Rollback()
		mine, err := moneyAccount(ctx, tx, "user", me)
		if err != nil {
			return nil, err
		}
		if _, err := tx.ExecContext(ctx, `SELECT id FROM money_account WHERE id = $1 FOR UPDATE`, mine); err != nil {
			return nil, err
		}
		total, err := accountBalance(ctx, tx, mine)
		if err != nil {
			return nil, err
		}
		pending, err := h.pendingPayouts(ctx, tx, me)
		if err != nil {
			return nil, err
		}
		available := total - pending
		amount := available
		if in.Amount != nil {
			amount = *in.Amount
		}
		if amount <= 0 || amount > available {
			return nil, moneyFail{http.StatusUnprocessableEntity, fmt.Sprintf("payout 1..%d", max(available, 0))}
		}
		p, err := scanPayout(tx.QueryRowContext(ctx, `INSERT INTO payout (holder_id, amount) VALUES ($1, $2) RETURNING `+payoutCols, me, amount))
		if err != nil {
			return nil, err
		}
		return p, tx.Commit()
	}()
	if err != nil {
		moneyRespond(w, err)
		return
	}
	writeJSON(w, http.StatusOK, payout)
}

func (h *Handlers) MoneyPayouts(w http.ResponseWriter, r *http.Request) {
	claims := ClaimsFrom(r)
	var rows *sql.Rows
	var err error
	if SeesAll(claims, refunders...) {
		rows, err = h.DB.QueryContext(r.Context(), `SELECT `+payoutCols+` FROM payout ORDER BY created_at DESC LIMIT 200`)
	} else {
		me := OwnerOf(claims)
		if me == "" {
			me = "00000000-0000-0000-0000-000000000000"
		}
		rows, err = h.DB.QueryContext(r.Context(), `SELECT `+payoutCols+` FROM payout WHERE holder_id = $1 ORDER BY created_at DESC LIMIT 200`, me)
	}
	if err != nil {
		dbError(w, err)
		return
	}
	defer rows.Close()
	out := []payoutRow{}
	for rows.Next() {
		p, err := scanPayout(rows)
		if err != nil {
			dbError(w, err)
			return
		}
		out = append(out, *p)
	}
	writeJSON(w, http.StatusOK, out)
}

func (h *Handlers) decidePayout(w http.ResponseWriter, r *http.Request, status string) {
	if !SeesAll(ClaimsFrom(r), refunders...) {
		moneyRespond(w, moneyFail{http.StatusForbidden, "forbidden"})
		return
	}
	var in struct {
		Reference *string `json:"reference"`
	}
	_ = json.NewDecoder(r.Body).Decode(&in)
	ctx := r.Context()
	payout, err := func() (*payoutRow, error) {
		tx, err := h.DB.BeginTx(ctx, nil)
		if err != nil {
			return nil, err
		}
		defer tx.Rollback()
		p, err := scanPayout(tx.QueryRowContext(ctx, `SELECT `+payoutCols+` FROM payout WHERE id = $1 FOR UPDATE`, r.PathValue("payoutId")))
		if err != nil {
			return nil, err
		}
		if p == nil {
			return nil, moneyFail{http.StatusNotFound, "not_found"}
		}
		if p.Status != "requested" {
			return nil, moneyFail{http.StatusConflict, "payout already " + p.Status}
		}
		if status == "paid" {
			holder, err := moneyAccount(ctx, tx, "user", p.HolderID)
			if err != nil {
				return nil, err
			}
			external, err := moneyAccount(ctx, tx, "external", "")
			if err != nil {
				return nil, err
			}
			if err := postEntry(ctx, tx, holder, external, p.Amount, "payout", "", p.ID); err != nil {
				return nil, err
			}
		}
		if p, err = scanPayout(tx.QueryRowContext(ctx, `UPDATE payout SET status = $1, reference = $2, decided_at = NOW() WHERE id = $3 RETURNING `+payoutCols, status, in.Reference, p.ID)); err != nil {
			return nil, err
		}
		return p, tx.Commit()
	}()
	if err != nil {
		moneyRespond(w, err)
		return
	}
	writeJSON(w, http.StatusOK, payout)
}

func (h *Handlers) MoneyPayPayout(w http.ResponseWriter, r *http.Request) {
	h.decidePayout(w, r, "paid")
}

func (h *Handlers) MoneyRejectPayout(w http.ResponseWriter, r *http.Request) {
	h.decidePayout(w, r, "rejected")
}
'''

"""R-567: the money module of a generated FastAPI backend (`app/money.py`).

Mostly fixed code - the books work the same for every app - with the app's own configuration on
top: its currency, what can be paid for (table, price column, payee column, who may pay), the
commission and who may refund. See `application_ir/money.py` for the model and the decisions.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR
from ..application_ir.money import Money, money_of
from ..application_ir.ownership import ownership_for_entity
from .schema_sql import sql_identifier, table_name


#: Every backend's .env.example lines for money (the keys are the app owner's, added last).
MONEY_ENV_EXAMPLE = (
    "# Payments (R-567): mock works offline with no keys. Set the keys to switch provider.\n"
    "PAYMENT_PROVIDER=\n"
    "STRIPE_SECRET_KEY=\nSTRIPE_WEBHOOK_SECRET=\n"
    "RAZORPAY_KEY_ID=\nRAZORPAY_KEY_SECRET=\nRAZORPAY_WEBHOOK_SECRET=\n"
    "PAYMENT_SUCCESS_URL=\nPAYMENT_CANCEL_URL=\n"
)


def _charge_table(ir: ApplicationIR, money: Money) -> str:
    rows = []
    for charge in money.charges:
        entity = next(e for e in ir.entities if e.name == charge.entity)
        rule = ownership_for_entity(ir, charge.entity)
        paid = next((f.name for f in entity.fields if f.name in ("paid", "is_paid") and f.type.value == "bool"), None)
        rows.append(
            f"    {table_name(charge.entity)!r}: {{\n"
            f"        \"entity\": {charge.entity!r},\n"
            f"        \"table\": {sql_identifier(table_name(charge.entity))!r},\n"
            f"        \"amount\": {sql_identifier(charge.amount)!r},\n"
            f"        \"payee\": {sql_identifier(charge.payee) if charge.payee else None!r},\n"
            f"        \"paid\": {sql_identifier(paid) if paid else None!r},\n"
            # Who may pay for a record: whoever may see it under its ownership rule (R-570).
            f"        \"owned\": {rule is not None and rule.reads_own!r},\n"
            f"        \"see_all\": {tuple(rule.bypass_roles) if rule else ()!r},\n"
            f"        \"assignee\": {rule.assignee if rule else None!r},\n"
            "    },"
        )
    return "CHARGES = {\n" + "\n".join(rows) + "\n}\n"


def python_money_file(ir: ApplicationIR) -> str:
    money = money_of(ir)
    assert money is not None
    return (
        '"""Money: payments, a double-entry ledger, refunds, commission and payouts (OmniStackAI R-567).\n\n'
        "Amounts are integers in the currency's minor unit. Every movement is a ledger entry that moves\n"
        "`amount` from the `debit` account to the `credit` account; a balance is credits minus debits, so\n"
        "the books always sum to zero. The amount to pay is read from the stored record, never the client.\n\n"
        "PAYMENT_PROVIDER picks the provider: `mock` (the default with no keys - works offline), `stripe`\n"
        "(STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET) or `razorpay` (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET,\n"
        "RAZORPAY_WEBHOOK_SECRET). Real providers mark a payment paid only from their signed webhook.\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        "import base64\n"
        "import hashlib\n"
        "import hmac\n"
        "import json\n"
        "import os\n"
        "import time\n"
        "import urllib.error\n"
        "import urllib.parse\n"
        "import urllib.request\n"
        "from decimal import ROUND_HALF_UP, Decimal\n"
        "from typing import Any\n\n"
        "from fastapi import APIRouter, Depends, HTTPException, Request\n"
        "from pydantic import BaseModel\n\n"
        "from app.auth import can_touch, owner_of, require_auth, sees_all\n"
        "from app.db import connect\n\n"
        f"CURRENCY = {money.currency!r}\n"
        f"MINOR = {money.minor_unit}  # minor units per major unit\n"
        f"COMMISSION_BPS = {money.commission_bps}  # the platform's share of a sale with a payee\n"
        f"REFUNDERS = {money.refunders!r}  # who may refund and settle payouts\n"
        f"{_charge_table(ir, money)}"
        "WEBHOOK_TOLERANCE_SECONDS = 300  # a signed Stripe event older than this is refused (replay)\n\n"
        "router = APIRouter(tags=[\"money\"])\n\n\n"
        + _BODY
    )


_BODY = r'''def provider() -> str:
    chosen = os.environ.get("PAYMENT_PROVIDER", "").strip().lower()
    if chosen:
        return chosen
    if os.environ.get("STRIPE_SECRET_KEY"):
        return "stripe"
    if os.environ.get("RAZORPAY_KEY_ID"):
        return "razorpay"
    return "mock"


def to_minor(value: Any) -> int:
    return int((Decimal(str(value)) * MINOR).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


async def account(cur, kind: str, holder: str | None = None) -> str:
    """The id of a money account, creating a user's on first use."""
    if kind == "user":
        await cur.execute(
            "INSERT INTO money_account (kind, holder_id) VALUES ('user', %s) "
            "ON CONFLICT (kind, COALESCE(holder_id, '00000000-0000-0000-0000-000000000000'::uuid)) DO NOTHING",
            (holder,),
        )
        await cur.execute("SELECT id FROM money_account WHERE kind = 'user' AND holder_id = %s", (holder,))
    else:
        await cur.execute("SELECT id FROM money_account WHERE kind = %s AND holder_id IS NULL", (kind,))
    return str((await cur.fetchone())["id"])


async def post(cur, debit: str, credit: str, amount: int, kind: str, payment_id=None, payout_id=None) -> None:
    if amount > 0:
        await cur.execute(
            "INSERT INTO ledger_entry (debit, credit, amount, kind, payment_id, payout_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (debit, credit, amount, kind, payment_id, payout_id),
        )


async def balance(cur, account_id: str) -> int:
    await cur.execute(
        "SELECT COALESCE(SUM(CASE WHEN credit = %s THEN amount ELSE -amount END), 0) AS b "
        "FROM ledger_entry WHERE credit = %s OR debit = %s",
        (account_id, account_id, account_id),
    )
    return int((await cur.fetchone())["b"])


# --- paying -----------------------------------------------------------------------------------

class CheckoutIn(BaseModel):
    entity: str
    record_id: str


@router.post("/payments/checkout")
async def checkout(body: CheckoutIn, claims: dict = Depends(require_auth)) -> dict:
    charge = CHARGES.get(body.entity.lower()) or next(
        (c for c in CHARGES.values() if c["entity"].lower() == body.entity.lower()), None)
    if charge is None:
        raise HTTPException(status_code=404, detail="nothing to pay for")
    payer = owner_of(claims)
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(f"SELECT * FROM {charge['table']} WHERE id = %s", (body.record_id,))
        row = await cur.fetchone()
        if row is None or (charge["owned"] and not can_touch(row, claims, charge["see_all"], charge["assignee"])):
            raise HTTPException(status_code=404, detail="not_found")
        await cur.execute(
            "SELECT 1 FROM payment WHERE entity = %s AND record_id = %s AND status = 'succeeded'",
            (charge["entity"], body.record_id),
        )
        if await cur.fetchone():
            raise HTTPException(status_code=409, detail="already paid")
        amount = to_minor(row.get(charge["amount"].strip('"')) or 0)  # from the record, never the client
        if amount <= 0:
            raise HTTPException(status_code=422, detail="nothing to pay: the amount is zero")
        payee = row.get(charge["payee"].strip('"')) if charge["payee"] else None
        commission = amount * COMMISSION_BPS // 10000 if payee else amount
        chosen = provider()
        await cur.execute(
            "INSERT INTO payment (entity, record_id, payer_id, payee_id, amount, commission, currency, provider) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (charge["entity"], body.record_id, payer, payee, amount, commission, CURRENCY, chosen),
        )
        payment_id = str((await cur.fetchone())["id"])
        out = {"payment_id": payment_id, "amount": amount, "currency": CURRENCY, "provider": chosen}
        if chosen == "mock":
            out["confirm"] = f"/payments/{payment_id}/confirm"
        elif chosen == "stripe":
            session = stripe_request("/v1/checkout/sessions", {
                "mode": "payment",
                "line_items[0][quantity]": "1",
                "line_items[0][price_data][currency]": CURRENCY.lower(),
                "line_items[0][price_data][unit_amount]": str(amount),
                "line_items[0][price_data][product_data][name]": f"{charge['entity']} {body.record_id[:8]}",
                "metadata[payment_id]": payment_id,
                "payment_intent_data[metadata][payment_id]": payment_id,
                "success_url": os.environ.get("PAYMENT_SUCCESS_URL", "http://localhost:3000/checkout/success"),
                "cancel_url": os.environ.get("PAYMENT_CANCEL_URL", "http://localhost:3000/checkout/cancel"),
            })
            await cur.execute("UPDATE payment SET provider_ref = %s WHERE id = %s", (session["id"], payment_id))
            out["url"] = session["url"]
        elif chosen == "razorpay":
            order = razorpay_request("/v1/orders", {"amount": amount, "currency": CURRENCY, "receipt": payment_id,
                                                    "notes": {"payment_id": payment_id}})
            await cur.execute("UPDATE payment SET provider_ref = %s WHERE id = %s", (order["id"], payment_id))
            out.update({"order_id": order["id"], "key_id": os.environ.get("RAZORPAY_KEY_ID", "")})
        else:
            raise HTTPException(status_code=500, detail=f"unknown PAYMENT_PROVIDER {chosen!r}")
        return out


@router.post("/payments/{payment_id}/confirm")
async def confirm_mock(payment_id: str, claims: dict = Depends(require_auth)) -> dict:
    """The mock provider's 'payment succeeded'. Real providers only confirm through their webhook."""
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute("SELECT * FROM payment WHERE id = %s", (payment_id,))
        payment = await cur.fetchone()
        if payment is None or payment["provider"] != "mock" or str(payment["payer_id"] or "") != (owner_of(claims) or "-"):
            raise HTTPException(status_code=404, detail="not_found")
    return await settle(payment_id, f"mock_{payment_id}")


async def settle(payment_id: str, provider_ref: str) -> dict:
    """Mark a payment succeeded and book it: cash in, then the commission and the payee's share."""
    async with await connect() as conn:
        async with conn.transaction(), conn.cursor() as cur:
            await cur.execute("SELECT * FROM payment WHERE id = %s FOR UPDATE", (payment_id,))
            payment = await cur.fetchone()
            if payment is None:
                raise HTTPException(status_code=404, detail="not_found")
            if payment["status"] == "succeeded":
                return dict(payment)  # a retried webhook: already booked
            await cur.execute(
                "UPDATE payment SET status = 'succeeded', provider_ref = %s, updated_at = NOW() WHERE id = %s RETURNING *",
                (provider_ref, payment_id),
            )
            payment = await cur.fetchone()
            external = await account(cur, "external")
            escrow = await account(cur, "escrow")
            revenue = await account(cur, "revenue")
            amount, commission = payment["amount"], payment["commission"]
            await post(cur, external, escrow, amount, "payment", payment_id)
            await post(cur, escrow, revenue, commission, "commission", payment_id)
            if payment["payee_id"]:
                await post(cur, escrow, await account(cur, "user", str(payment["payee_id"])), amount - commission,
                           "sale", payment_id)
            charge = next(c for c in CHARGES.values() if c["entity"] == payment["entity"])
            if charge["paid"]:
                await cur.execute(f"UPDATE {charge['table']} SET {charge['paid']} = TRUE WHERE id = %s",
                                  (payment["record_id"],))
            return dict(payment)


# --- real providers -----------------------------------------------------------------------------

def _post_form(url: str, data: dict, auth_header: str) -> dict:
    body = urllib.parse.urlencode(data).encode() if not isinstance(data, bytes) else data
    req = urllib.request.Request(url, data=body, method="POST", headers={"Authorization": auth_header})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"payment provider refused: {error.read()[:300]!r}") from error


def stripe_request(path: str, data: dict) -> dict:
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="STRIPE_SECRET_KEY is not set")
    return _post_form("https://api.stripe.com" + path, data, f"Bearer {key}")


def razorpay_request(path: str, data: dict) -> dict:
    key, secret = os.environ.get("RAZORPAY_KEY_ID", ""), os.environ.get("RAZORPAY_KEY_SECRET", "")
    if not (key and secret):
        raise HTTPException(status_code=503, detail="RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are not set")
    token = base64.b64encode(f"{key}:{secret}".encode()).decode()
    req = urllib.request.Request("https://api.razorpay.com" + path, data=json.dumps(data).encode(), method="POST",
                                 headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"payment provider refused: {error.read()[:300]!r}") from error


def verify_stripe(payload: bytes, header: str, secret: str, now: float | None = None) -> bool:
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    timestamp, signature = parts.get("t", ""), parts.get("v1", "")
    if not timestamp.isdigit() or not signature:
        return False
    if abs((now or time.time()) - int(timestamp)) > WEBHOOK_TOLERANCE_SECONDS:
        return False
    expected = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_razorpay(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)


async def first_time(provider_name: str, event_id: str) -> bool:
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO processed_event (provider, event_id) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING event_id",
            (provider_name, event_id),
        )
        return await cur.fetchone() is not None


@router.post("/payments/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict:
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    payload = await request.body()
    if not secret or not verify_stripe(payload, request.headers.get("stripe-signature", ""), secret):
        raise HTTPException(status_code=400, detail="invalid signature")
    event = json.loads(payload)
    if not await first_time("stripe", str(event.get("id"))):
        return {"received": True, "duplicate": True}
    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        payment_id = (session.get("metadata") or {}).get("payment_id")
        await _settle_checked(payment_id, int(session.get("amount_total") or 0), str(session.get("currency") or ""),
                              str(session.get("payment_intent") or session.get("id")))
    return {"received": True}


@router.post("/payments/webhooks/razorpay")
async def razorpay_webhook(request: Request) -> dict:
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
    payload = await request.body()
    if not secret or not verify_razorpay(payload, request.headers.get("x-razorpay-signature", ""), secret):
        raise HTTPException(status_code=400, detail="invalid signature")
    event = json.loads(payload)
    event_id = request.headers.get("x-razorpay-event-id") or str(event.get("created_at"))
    if not await first_time("razorpay", event_id):
        return {"received": True, "duplicate": True}
    if event.get("event") in ("payment.captured", "order.paid"):
        entity = event["payload"]["payment"]["entity"]
        payment_id = (entity.get("notes") or {}).get("payment_id")
        await _settle_checked(payment_id, int(entity.get("amount") or 0), str(entity.get("currency") or ""),
                              str(entity.get("id")))
    return {"received": True}


async def _settle_checked(payment_id: str | None, amount: int, currency: str, ref: str) -> None:
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute("SELECT amount, currency FROM payment WHERE id = %s", (payment_id,))
        payment = await cur.fetchone()
    # What the provider charged must be what we asked for.
    if payment is None or payment["amount"] != amount or payment["currency"].lower() != currency.lower():
        raise HTTPException(status_code=400, detail="payment does not match")
    await settle(payment_id, ref)


# --- refunds ------------------------------------------------------------------------------------

class RefundIn(BaseModel):
    amount: int | None = None  # minor units; the whole remainder when left out


@router.post("/payments/{payment_id}/refund")
async def refund(payment_id: str, body: RefundIn, claims: dict = Depends(require_auth)) -> dict:
    if not sees_all(claims, REFUNDERS):
        raise HTTPException(status_code=403, detail="forbidden")
    async with await connect() as conn:
        async with conn.transaction(), conn.cursor() as cur:
            await cur.execute("SELECT * FROM payment WHERE id = %s FOR UPDATE", (payment_id,))
            payment = await cur.fetchone()
            if payment is None or payment["status"] != "succeeded":
                raise HTTPException(status_code=404, detail="not_found")
            remaining = payment["amount"] - payment["refunded"]
            amount = remaining if body.amount is None else body.amount
            if amount <= 0 or amount > remaining:
                raise HTTPException(status_code=422, detail=f"refund 1..{remaining}")
            if payment["provider"] == "stripe":
                stripe_request("/v1/refunds", {"payment_intent": payment["provider_ref"], "amount": str(amount)})
            elif payment["provider"] == "razorpay":
                razorpay_request(f"/v1/payments/{payment['provider_ref']}/refund", {"amount": amount})
            # Taken back in proportion: the payee's share from the payee, the rest from revenue.
            payee_share = 0
            if payment["payee_id"]:
                payee_share = amount * (payment["amount"] - payment["commission"]) // payment["amount"]
                await post(cur, await account(cur, "user", str(payment["payee_id"])), await account(cur, "external"),
                           payee_share, "refund", payment_id)
            await post(cur, await account(cur, "revenue"), await account(cur, "external"), amount - payee_share,
                       "refund", payment_id)
            await cur.execute("UPDATE payment SET refunded = refunded + %s, updated_at = NOW() WHERE id = %s RETURNING *",
                              (amount, payment_id))
            updated = await cur.fetchone()
            charge = next(c for c in CHARGES.values() if c["entity"] == payment["entity"])
            if charge["paid"] and updated["refunded"] == updated["amount"]:
                await cur.execute(f"UPDATE {charge['table']} SET {charge['paid']} = FALSE WHERE id = %s",
                                  (payment["record_id"],))
            return dict(updated)


@router.get("/payments")
async def list_payments(entity: str | None = None, record_id: str | None = None,
                        claims: dict = Depends(require_auth)) -> list[dict]:
    me = owner_of(claims) or "00000000-0000-0000-0000-000000000000"
    conditions, params = [], []
    if not sees_all(claims, REFUNDERS):
        conditions.append("(payer_id = %s OR payee_id = %s)")
        params += [me, me]
    if entity:
        conditions.append("lower(entity) = lower(%s)")
        params.append(entity)
    if record_id:
        conditions.append("record_id = %s")
        params.append(record_id)
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(f"SELECT * FROM payment{where} ORDER BY created_at DESC LIMIT 200", tuple(params))
        return [dict(r) for r in await cur.fetchall()]


# --- balances, the ledger and payouts --------------------------------------------------------------

@router.get("/money/balance")
async def my_balance(claims: dict = Depends(require_auth)) -> dict:
    me = owner_of(claims)
    if me is None:
        return {"currency": CURRENCY, "minor_unit": MINOR, "balance": 0, "pending_payouts": 0, "available": 0}
    async with await connect() as conn, conn.cursor() as cur:
        mine = await account(cur, "user", me)
        total = await balance(cur, mine)
        await cur.execute("SELECT COALESCE(SUM(amount), 0) AS p FROM payout WHERE holder_id = %s AND status = 'requested'", (me,))
        pending = int((await cur.fetchone())["p"])
    return {"currency": CURRENCY, "minor_unit": MINOR, "balance": total, "pending_payouts": pending,
            "available": total - pending}


@router.get("/money/ledger")
async def my_ledger(claims: dict = Depends(require_auth)) -> list[dict]:
    me = owner_of(claims)
    if me is None:
        return []
    async with await connect() as conn, conn.cursor() as cur:
        mine = await account(cur, "user", me)
        await cur.execute(
            "SELECT id, kind, payment_id, payout_id, created_at, "
            "CASE WHEN credit = %s THEN amount ELSE -amount END AS amount "
            "FROM ledger_entry WHERE credit = %s OR debit = %s ORDER BY created_at DESC LIMIT 200",
            (mine, mine, mine),
        )
        return [dict(r) for r in await cur.fetchall()]


@router.get("/money/summary")
async def summary(claims: dict = Depends(require_auth)) -> dict:
    """The platform's books: what it holds, what it earned, what users are owed - and that it balances."""
    if not sees_all(claims, REFUNDERS):
        raise HTTPException(status_code=403, detail="forbidden")
    async with await connect() as conn, conn.cursor() as cur:
        out = {"currency": CURRENCY, "minor_unit": MINOR}
        for kind in ("external", "escrow", "revenue"):
            out[kind] = await balance(cur, await account(cur, kind))
        await cur.execute(
            "SELECT COALESCE(SUM(CASE WHEN l.credit = a.id THEN l.amount ELSE -l.amount END), 0) AS owed "
            "FROM money_account a JOIN ledger_entry l ON l.credit = a.id OR l.debit = a.id WHERE a.kind = 'user'"
        )
        out["owed_to_users"] = int((await cur.fetchone())["owed"])
        out["balanced"] = out["external"] + out["escrow"] + out["revenue"] + out["owed_to_users"] == 0
        return out


class PayoutIn(BaseModel):
    amount: int | None = None  # minor units; everything available when left out


@router.post("/money/payouts")
async def request_payout(body: PayoutIn, claims: dict = Depends(require_auth)) -> dict:
    me = owner_of(claims)
    if me is None:
        raise HTTPException(status_code=422, detail="nothing to pay out")
    async with await connect() as conn:
        async with conn.transaction(), conn.cursor() as cur:
            mine = await account(cur, "user", me)
            await cur.execute("SELECT id FROM money_account WHERE id = %s FOR UPDATE", (mine,))
            await cur.execute("SELECT COALESCE(SUM(amount), 0) AS p FROM payout WHERE holder_id = %s AND status = 'requested'", (me,))
            pending = int((await cur.fetchone())["p"])
            available = await balance(cur, mine) - pending
            amount = available if body.amount is None else body.amount
            if amount <= 0 or amount > available:
                raise HTTPException(status_code=422, detail=f"payout 1..{max(available, 0)}")
            await cur.execute("INSERT INTO payout (holder_id, amount) VALUES (%s, %s) RETURNING *", (me, amount))
            return dict(await cur.fetchone())


@router.get("/money/payouts")
async def list_payouts(claims: dict = Depends(require_auth)) -> list[dict]:
    async with await connect() as conn, conn.cursor() as cur:
        if sees_all(claims, REFUNDERS):
            await cur.execute("SELECT * FROM payout ORDER BY created_at DESC LIMIT 200")
        else:
            await cur.execute("SELECT * FROM payout WHERE holder_id = %s ORDER BY created_at DESC LIMIT 200",
                              (owner_of(claims) or "00000000-0000-0000-0000-000000000000",))
        return [dict(r) for r in await cur.fetchall()]


class DecisionIn(BaseModel):
    reference: str | None = None  # the bank transfer's reference


async def _decide(payout_id: str, claims: dict, status: str, reference: str | None) -> dict:
    if not sees_all(claims, REFUNDERS):
        raise HTTPException(status_code=403, detail="forbidden")
    async with await connect() as conn:
        async with conn.transaction(), conn.cursor() as cur:
            await cur.execute("SELECT * FROM payout WHERE id = %s FOR UPDATE", (payout_id,))
            payout = await cur.fetchone()
            if payout is None:
                raise HTTPException(status_code=404, detail="not_found")
            if payout["status"] != "requested":
                raise HTTPException(status_code=409, detail=f"payout already {payout['status']}")
            if status == "paid":
                holder = await account(cur, "user", str(payout["holder_id"]))
                await post(cur, holder, await account(cur, "external"), payout["amount"], "payout", payout_id=payout_id)
            await cur.execute("UPDATE payout SET status = %s, reference = %s, decided_at = NOW() WHERE id = %s RETURNING *",
                              (status, reference, payout_id))
            return dict(await cur.fetchone())


@router.post("/money/payouts/{payout_id}/pay")
async def pay_payout(payout_id: str, body: DecisionIn, claims: dict = Depends(require_auth)) -> dict:
    return await _decide(payout_id, claims, "paid", body.reference)


@router.post("/money/payouts/{payout_id}/reject")
async def reject_payout(payout_id: str, body: DecisionIn, claims: dict = Depends(require_auth)) -> dict:
    return await _decide(payout_id, claims, "rejected", body.reference)
'''

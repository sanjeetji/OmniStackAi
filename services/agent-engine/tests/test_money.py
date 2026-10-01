"""R-567: money in generated apps - payments, a double-entry ledger, refunds, commission, payouts.

These check the plan, the shared schema, each backend's code and the planner. The live proof ran a
marketplace on every backend through the platform's runner (33 checks each: pay, the split, a
partial refund, payouts, signed Stripe and Razorpay webhooks, books balanced after every step).
"""

import ast
import hashlib
import hmac
import json
import time
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR, InvalidIRError
from omnistackai_agent_engine.application_ir.money import money_of
from omnistackai_agent_engine.codegen.backend_go import GoBackendAdapter
from omnistackai_agent_engine.codegen.backend_node import ExpressBackendAdapter, HonoBackendAdapter
from omnistackai_agent_engine.codegen.backend_python import PythonBackendAdapter
from omnistackai_agent_engine.codegen.schema_sql import render_postgres_schema
from omnistackai_agent_engine.intake.ir_repair import repair_ir_dict
from omnistackai_agent_engine.intake.money_intent import money_from_prompt

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"
MARKET = {"currency": "INR", "commission_bps": 1000, "refund_roles": ["manager"],
          "charges": [{"entity": "Order", "amount": "total_amount", "payee": "vendor_id"}]}


def _plan(money: dict | None = None) -> dict:
    data = json.loads(FIXTURE.read_text())
    data["roles"] += [{"id": "vendor", "permissions": []}, {"id": "manager", "permissions": []}]
    order = next(e for e in data["entities"] if e["name"] == "Order")
    order["fields"] += [{"name": "vendor_id", "type": "uuid", "required": False},
                        {"name": "paid", "type": "bool", "required": False}]
    data["capabilities"] = [{"kind": "money", "name": "m", "config": money if money is not None else MARKET}]
    return data


def _files(adapter, money: dict | None = None) -> dict[str, str]:
    return {f.path: f.content for f in adapter.generate(ApplicationIR.from_dict(_plan(money))).files()}


class TheMoneyRuleIsPartOfThePlan(TestCase):
    def test_round_trip(self) -> None:
        money = money_of(ApplicationIR.from_dict(ApplicationIR.from_dict(_plan()).to_dict()))
        self.assertEqual((money.currency, money.commission_bps, money.refunders, money.minor_unit),
                         ("INR", 1000, ("manager", "admin"), 100))
        self.assertEqual(money.charge_for("Order").payee, "vendor_id")
        self.assertEqual(money_of(ApplicationIR.from_dict(_plan({**MARKET, "currency": "JPY"}))).minor_unit, 1)

    def test_bad_rules_are_refused(self) -> None:
        for bad in ({**MARKET, "currency": "rupees"}, {**MARKET, "commission_bps": 20000}, {**MARKET, "charges": []},
                    {**MARKET, "charges": [{"entity": "Ghost", "amount": "x"}]},
                    {**MARKET, "charges": [{"entity": "Order", "amount": "status"}]},
                    {**MARKET, "charges": [{"entity": "Order", "amount": "total_amount", "payee": "paid"}]},
                    {**MARKET, "refund_roles": ["nobody"]}, {**MARKET, "tip": 1}):
            with self.subTest(bad=bad), self.assertRaises(InvalidIRError):
                ApplicationIR.from_dict(_plan(bad))


class TheBooksLiveInTheDatabase(TestCase):
    def test_schema(self) -> None:
        sql = render_postgres_schema(ApplicationIR.from_dict(_plan()))
        for fragment in ('CREATE TABLE IF NOT EXISTS "ledger_entry"', 'CHECK ("debit" <> "credit")',
                         '"amount"     BIGINT NOT NULL CHECK ("amount" > 0)', 'WHERE "status" = \'succeeded\'',
                         'PRIMARY KEY ("provider", "event_id")', "INSERT INTO \"money_account\" (\"kind\") VALUES ('external'), ('escrow'), ('revenue')"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, sql)

    def test_money_implies_sign_in(self) -> None:
        data = _plan()
        for api in data["apis"]:
            api["auth"] = False
        self.assertIn('CREATE TABLE IF NOT EXISTS "users"', render_postgres_schema(ApplicationIR.from_dict(data)))


class Python(TestCase):
    def setUp(self) -> None:
        self.files = _files(PythonBackendAdapter())
        self.money = self.files["app/money.py"]
        ast.parse(self.money)

    def test_wired(self) -> None:
        self.assertIn("app.include_router(money.router)", self.files["app/main.py"])
        self.assertIn("PAYMENT_PROVIDER=", self.files[".env.example"])
        self.assertIn("STRIPE_WEBHOOK_SECRET=", self.files[".env.example"])

    def test_the_amount_is_the_records(self) -> None:
        checkout = self.money.split("async def checkout(")[1].split("\n\n\n")[0]
        self.assertIn('amount = to_minor(row.get(charge["amount"]', checkout)
        self.assertNotIn("body.amount", checkout)

    def _helpers(self) -> dict:
        """Run the generated pure helpers (no database) to check their arithmetic and signatures."""
        tree = ast.parse(self.money)
        wanted = {"to_minor", "verify_stripe", "verify_razorpay"}
        code = "\n".join(ast.get_source_segment(self.money, node) for node in tree.body
                         if isinstance(node, ast.FunctionDef) and node.name in wanted)
        scope = {"Decimal": Decimal, "ROUND_HALF_UP": ROUND_HALF_UP, "MINOR": 100, "hmac": hmac, "hashlib": hashlib,
                 "time": time, "WEBHOOK_TOLERANCE_SECONDS": 300, "Any": object}
        exec(compile(code, "money_helpers", "exec"), scope)  # noqa: S102 - generated code under test
        return scope

    def test_minor_units(self) -> None:
        to_minor = self._helpers()["to_minor"]
        self.assertEqual([to_minor(v) for v in (499.5, "0.29", 10, 0.005, 1234.565)], [49950, 29, 1000, 1, 123457])

    def test_webhook_signatures(self) -> None:
        h = self._helpers()
        body, secret, now = b'{"id":"evt_1"}', "whsec_x", 1_800_000_000
        sig = hmac.new(secret.encode(), f"{now}.".encode() + body, hashlib.sha256).hexdigest()
        self.assertTrue(h["verify_stripe"](body, f"t={now},v1={sig}", secret, now=now + 10))
        self.assertFalse(h["verify_stripe"](body, f"t={now},v1={sig}", secret, now=now + 3600), "a replay is refused")
        self.assertFalse(h["verify_stripe"](body + b" ", f"t={now},v1={sig}", secret, now=now))
        self.assertFalse(h["verify_stripe"](body, "garbage", secret, now=now))
        rz = hmac.new(b"rzp", body, hashlib.sha256).hexdigest()
        self.assertTrue(h["verify_razorpay"](body, rz, "rzp"))
        self.assertFalse(h["verify_razorpay"](body, "", "rzp"))

    def test_refunds_and_payouts_are_guarded(self) -> None:
        for fn in ("refund", "summary", "_decide"):
            with self.subTest(fn=fn):
                body = self.money.split(f"async def {fn}(")[1].split("\n\n\n")[0]
                self.assertIn("if not sees_all(claims, REFUNDERS):", body)


class Go(TestCase):
    def test_wired_and_guarded(self) -> None:
        files = _files(GoBackendAdapter())
        money, main = files["internal/handlers/money.go"], files["main.go"]
        self.assertIn('mux.HandleFunc("POST /payments/checkout", handlers.RequireAuth(h.MoneyCheckout))', main)
        self.assertIn('mux.HandleFunc("POST /payments/webhooks/stripe", h.MoneyStripeWebhook)', main)
        self.assertIn("amount := toMinor(amountText) // from the record, never the client", money)
        self.assertIn("d > webhookToleranceSeconds", money)
        self.assertIn("const commissionBps = 1000", money)
        self.assertIn('Payee: "\\"vendor_id\\""', money)


class Node(TestCase):
    def test_express_and_hono(self) -> None:
        for adapter in (ExpressBackendAdapter(), HonoBackendAdapter()):
            with self.subTest(adapter=type(adapter).__name__):
                files = _files(adapter)
                self.assertIn("const amount = toMinor(row.amount); // from the record, never the client", files["src/money/service.ts"])
                self.assertIn("router.post('/payments/webhooks/stripe', async", files["src/money/router.ts"])
                self.assertIn("router.post('/payments/checkout', requireAuth, async", files["src/money/router.ts"])
                self.assertIn("moneyRouter", files["src/app.ts"])
        express = _files(ExpressBackendAdapter())
        self.assertIn("(req as any).rawBody = buf", express["src/app.ts"], "signatures need the exact bytes")


class ThePlannerPlansIt(TestCase):
    def _money(self, prompt: str, entities: list, roles: list) -> dict | None:
        data = {"entities": entities, "roles": [{"id": r} for r in roles], "capabilities": []}
        money_from_prompt(prompt, data)
        return data["capabilities"][0]["config"] if data["capabilities"] else None

    def test_a_marketplace(self) -> None:
        order = {"name": "Order", "fields": [{"name": "total_amount", "type": "float"}]}
        config = self._money("Customers pay for orders and we take a 10% commission (rupees)", [order], ["customer", "vendor"])
        self.assertEqual(config, {"currency": "INR", "commission_bps": 1000, "refund_roles": [],
                                  "charges": [{"entity": "Order", "amount": "total_amount", "payee": "vendor_id"}]})
        self.assertIn("vendor_id", [f["name"] for f in order["fields"]])

    def test_nothing_paid_nothing_added(self) -> None:
        self.assertIsNone(self._money("A notes app", [{"name": "Note", "fields": [{"name": "total", "type": "float"}]}], ["user"]))

    def test_repair(self) -> None:
        data = _plan({"currency": "INR", "charges": [{"entity": "orders", "amount": "cost", "payee": "paid"}],
                      "refund_roles": ["manager", "wizard"]})
        data, notes = repair_ir_dict(data)
        config = next(c for c in data["capabilities"] if c["kind"] == "money")["config"]
        self.assertEqual(config["charges"], [{"entity": "Order", "amount": "total_amount"}])
        self.assertEqual(config["refund_roles"], ["manager"])
        ApplicationIR.from_dict(data)

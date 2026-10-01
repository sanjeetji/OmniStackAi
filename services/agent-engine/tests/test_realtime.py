"""R-569: live updates in generated apps.

These check the plan, the trigger, each backend's stream, the pages' hooks and the planner. The live
proof ran the same plan on Python, Go, Express and Hono through the platform's runner (19 checks
each): a stream needs a valid ticket; a customer hears of their own order and not another's; staff
who see all hear of every order; a courier hears of the order once it is assigned to them; a
change made in the database itself is heard; a stream can ask for one entity.
"""

import ast
import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR, InvalidIRError
from omnistackai_agent_engine.application_ir.realtime import live_entities
from omnistackai_agent_engine.codegen import NextjsAdminAdapter, NextjsWebAdapter
from omnistackai_agent_engine.codegen.auth_guard import needs_auth
from omnistackai_agent_engine.codegen.backend_go import GoBackendAdapter
from omnistackai_agent_engine.codegen.backend_node import ExpressBackendAdapter, HonoBackendAdapter
from omnistackai_agent_engine.codegen.backend_python import PythonBackendAdapter
from omnistackai_agent_engine.codegen.realtime_sql import live_tables
from omnistackai_agent_engine.codegen.schema_sql import render_postgres_schema
from omnistackai_agent_engine.intake.ir_repair import repair_ir_dict
from omnistackai_agent_engine.intake.realtime_intent import realtime_from_prompt

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"


def _plan(live: tuple | None = ("Order", "Product")) -> dict:
    data = json.loads(FIXTURE.read_text())
    data["roles"] += [{"id": "staff", "permissions": []}, {"id": "courier", "permissions": []}]
    order = next(e for e in data["entities"] if e["name"] == "Order")
    order["fields"] += [{"name": "courier_id", "type": "uuid", "required": False},
                        {"name": "latitude", "type": "float", "required": False},
                        {"name": "longitude", "type": "float", "required": False}]
    data["capabilities"] = [
        {"kind": "workflow", "name": "order_flow", "config": {
            "entity": "Order", "field": "status", "states": ["pending", "shipped"], "initial": "pending",
            "transitions": [{"name": "ship", "to": "shipped", "from": ["pending"], "roles": ["staff"]}]}},
        {"kind": "ownership", "name": "order_ownership", "config": {
            "entity": "Order", "read": "own", "write": "own", "see_all": ["staff"], "assignee": "courier_id"}},
    ]
    if live is not None:
        data["capabilities"].append({"kind": "realtime", "name": "live_updates", "config": {"entities": list(live)}})
    return data


def _ir(live: tuple | None = ("Order", "Product")) -> ApplicationIR:
    return ApplicationIR.from_dict(_plan(live))


def _files(adapter) -> dict[str, str]:
    return {f.path: f.content for f in adapter.generate(_ir()).files()}


class LiveEntitiesArePartOfThePlan(TestCase):
    def test_round_trip_and_sign_in(self) -> None:
        ir = ApplicationIR.from_dict(_ir().to_dict())
        self.assertEqual(live_entities(ir), {"Order", "Product"})
        self.assertTrue(needs_auth(ir), "a stream is for signed-in people")

    def test_bad_plans_are_refused(self) -> None:
        for live in ((), ("Ghost",), ("Order", "Order")):
            with self.subTest(live=live), self.assertRaises(InvalidIRError):
                _ir(live)
        data = _plan()
        data["apis"].append({"method": "GET", "path": "/realtime/feed", "auth": False})
        with self.assertRaises(InvalidIRError):
            ApplicationIR.from_dict(data)

    def test_who_may_hear(self) -> None:
        tables = {t.entity: t for t in live_tables(_ir())}
        self.assertEqual((tables["Order"].owned, tables["Order"].see_all, tables["Order"].assignee),
                         (True, ("staff", "admin"), "courier_id"))
        self.assertFalse(tables["Product"].owned)


class TheDatabasePublishesChanges(TestCase):
    def test_triggers(self) -> None:
        schema = render_postgres_schema(_ir())
        self.assertIn('CREATE OR REPLACE FUNCTION "realtime_notify"() RETURNS trigger AS $$', schema)
        self.assertIn("PERFORM pg_notify('app_changes'", schema)
        self.assertIn('CREATE TRIGGER "realtime_order" AFTER INSERT OR UPDATE OR DELETE ON "order" '
                      'FOR EACH ROW EXECUTE FUNCTION "realtime_notify"(\'courier_id\');', schema)
        self.assertIn('EXECUTE FUNCTION "realtime_notify"();', schema.split('"realtime_product"')[-1])
        self.assertIn('DROP TRIGGER IF EXISTS "realtime_order" ON "order";', schema)
        self.assertNotIn("realtime_notify", render_postgres_schema(_ir(None)))


class Python(TestCase):
    def setUp(self) -> None:
        self.files = _files(PythonBackendAdapter())
        self.live = self.files["app/realtime.py"]
        ast.parse(self.live)

    def test_started_with_the_app(self) -> None:
        main = self.files["app/main.py"]
        self.assertIn("await realtime.start()", main)
        self.assertIn("app.include_router(realtime.router)", main)

    def _helpers(self) -> dict:
        tree = ast.parse(self.live)
        wanted = {"_b64", "_sign", "make_ticket", "read_ticket", "may_hear"}
        code = "\n".join(ast.get_source_segment(self.live, node) for node in tree.body
                         if isinstance(node, ast.FunctionDef) and node.name in wanted)
        live = {"order": {"entity": "Order", "owned": True, "see_all": ("staff",)},
                "product": {"entity": "Product", "owned": False, "see_all": ()}}
        scope = {"base64": base64, "hashlib": hashlib, "hmac": hmac, "json": json, "time": time,
                 "_secret": lambda: "s3cret", "owner_of": lambda c: c.get("sub"), "TICKET_SECONDS": 60, "LIVE": live}
        exec(compile(code, "realtime_helpers", "exec"), scope)  # noqa: S102 - generated code under test
        return scope

    def test_tickets(self) -> None:
        h = self._helpers()
        ticket = h["make_ticket"]({"sub": "u1", "roles": ["staff"]}, now=1000)
        self.assertEqual(h["read_ticket"](ticket, now=1030)["roles"], ["staff"])
        self.assertIsNone(h["read_ticket"](ticket, now=1061), "a ticket lives a minute")
        payload, _, signature = ticket.partition(".")
        self.assertIsNone(h["read_ticket"](payload + "." + "0" * len(signature), now=1030))
        forged = base64.urlsafe_b64encode(json.dumps({"sub": "u1", "roles": ["admin"], "exp": 9999}).encode()).decode().rstrip("=")
        self.assertIsNone(h["read_ticket"](forged + "." + signature, now=1030))

    def test_only_those_who_may_see_the_row_hear_of_it(self) -> None:
        may_hear = self._helpers()["may_hear"]
        change = {"t": "order", "op": "update", "id": "o1", "o": "creator", "a": "courier"}
        self.assertTrue(may_hear({"sub": "creator", "roles": []}, change))
        self.assertTrue(may_hear({"sub": "courier", "roles": ["courier"]}, change))
        self.assertTrue(may_hear({"sub": "x", "roles": ["staff"]}, change))
        self.assertTrue(may_hear({"sub": "x", "roles": ["admin"]}, change))
        self.assertFalse(may_hear({"sub": "someone", "roles": ["customer"]}, change))
        self.assertFalse(may_hear({"sub": "", "roles": []}, {**change, "o": None, "a": None}))
        self.assertTrue(may_hear({"sub": "someone", "roles": []}, {"t": "product", "op": "insert", "id": "p"}))
        self.assertFalse(may_hear({"sub": "creator", "roles": []}, {"t": "customer", "op": "insert", "id": "c"}))


class Go(TestCase):
    def test_wired(self) -> None:
        files = _files(GoBackendAdapter())
        main, live = files["main.go"], files["internal/handlers/realtime.go"]
        self.assertIn("\tgo h.RunRealtime()", main)
        self.assertIn('mux.HandleFunc("POST /realtime/ticket", handlers.RequireAuth(h.RealtimeTicket))', main)
        self.assertIn('mux.HandleFunc("GET /realtime/stream", h.RealtimeStream)', main)
        self.assertIn('"order": {Entity: "Order", Owned: true, SeeAll: []string{"staff", "admin"}},', live)
        self.assertIn("hmac.Equal(", live)


class Node(TestCase):
    def test_wired(self) -> None:
        for adapter, mount in ((ExpressBackendAdapter(), "app.use(realtimeRouter);"), (HonoBackendAdapter(), "app.route('/', realtimeRouter);")):
            files = _files(adapter)
            with self.subTest(adapter=type(adapter).__name__):
                self.assertIn("startRealtime();", files["src/index.ts"])
                self.assertIn(mount, files["src/app.ts"])
                self.assertIn("router.post('/realtime/ticket', requireAuth,", files["src/realtime/router.ts"])
                self.assertIn("crypto.timingSafeEqual(", files["src/realtime/service.ts"])


class ThePagesRefreshThemselves(TestCase):
    def test_hooks_of_live_entities(self) -> None:
        project = NextjsWebAdapter().generate(_ir())
        hooks = project.get("lib/hooks.ts").content
        self.assertIn('import { useLive } from "./realtime";', hooks)
        self.assertIn('useLive("Order", () => { void refetch(true); });', hooks)
        self.assertIn('useLive("Order", () => { void refetch(true); }, id ?? undefined);', hooks)
        self.assertIn("if (quiet !== true) setLoading(true);", hooks)
        self.assertNotIn('useLive("Customer"', hooks, "only live entities listen")
        self.assertIn("/realtime/ticket", project.get("lib/realtime.ts").content)

    def test_admin_tables(self) -> None:
        project = NextjsAdminAdapter().generate(_ir())
        orders = project.get("app/manage/orders/page.tsx").content
        self.assertIn('const LIVE = (onChange: () => void) => subscribe("Order", onChange);', orders)
        self.assertIn("live={LIVE}", orders)
        self.assertNotIn("subscribe(", project.get("app/manage/customers/page.tsx").content)

    def test_no_live_entities_no_stream(self) -> None:
        project = NextjsWebAdapter().generate(_ir(None))
        self.assertNotIn("useLive", project.get("lib/hooks.ts").content)
        self.assertNotIn("lib/realtime.ts", {f.path for f in project.files()})


class ThePlannerReadsThePrompt(TestCase):
    def _live(self, prompt: str) -> list:
        data = _plan(None)
        realtime_from_prompt(prompt, data)
        live = next((c for c in data["capabilities"] if c["kind"] == "realtime"), None)
        return live["config"]["entities"] if live else []

    def test_named_entities(self) -> None:
        self.assertEqual(self._live("Customers see live order status."), ["Order"])
        self.assertEqual(self._live("Customers can track their orders in real time."), ["Order"])

    def test_unnamed_means_what_changes(self) -> None:
        self.assertEqual(self._live("Everything updates in real time, without refreshing."), ["Order"])

    def test_not_live_updates(self) -> None:
        for prompt in ("A place to find live music near where you live.", "A shop for products."):
            with self.subTest(prompt=prompt):
                self.assertEqual(self._live(prompt), [])

    def test_repair(self) -> None:
        data = _plan(("orders", "Ghost"))
        data["capabilities"].append({"kind": "realtime", "name": "more", "config": {"entities": ["Product", "Order"]}})
        repaired, notes = repair_ir_dict(data)
        self.assertEqual(live_entities(ApplicationIR.from_dict(repaired)), {"Order", "Product"})
        self.assertTrue(any("Ghost" in n for n in notes))

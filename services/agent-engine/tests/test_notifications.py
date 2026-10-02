"""PC-053: notifications in generated apps - in-app and email, with each person's preferences.

These check the plan, the database side (the send function, the triggers, reminders), each backend's
API and outbox, the pages and the planner. The live proof ran the same plan on Python, Go, Express and
Hono through the platform's runner (27 checks each, a stand-in email provider) and the bell in a
browser (6 checks).
"""

import ast
import copy
import json
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR, InvalidIRError
from omnistackai_agent_engine.application_ir.notifications import has_notifications, notifications_of
from omnistackai_agent_engine.codegen import NextjsAdminAdapter, NextjsWebAdapter
from omnistackai_agent_engine.codegen.auth_guard import needs_auth
from omnistackai_agent_engine.codegen.backend_go import GoBackendAdapter
from omnistackai_agent_engine.codegen.backend_node import ExpressBackendAdapter, HonoBackendAdapter
from omnistackai_agent_engine.codegen.backend_python import PythonBackendAdapter
from omnistackai_agent_engine.codegen.jobs_sql import compiled_schedules
from omnistackai_agent_engine.codegen.notifications_sql import rule_catalogue, text_expression
from omnistackai_agent_engine.codegen.realtime_sql import live_tables
from omnistackai_agent_engine.codegen.schema_sql import render_postgres_schema
from omnistackai_agent_engine.intake.ir_repair import repair_ir_dict
from omnistackai_agent_engine.intake.notifications_intent import notifications_from_prompt

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"
SHIPPED = {"name": "order_shipped", "entity": "Order", "when": {"field": "status", "becomes": "shipped"},
           "to": ["creator"], "title": "Your order is on its way", "body": "Total: {total_amount}", "channels": ["in_app", "email"]}
ASSIGNED = {"name": "order_assigned", "entity": "Order", "when": "assigned", "to": ["assignee"],
            "title": "Order {status} is assigned to you", "channels": ["in_app"]}
NEW = {"name": "new_order", "entity": "Order", "when": "created", "to": ["role:staff"], "title": "New order: {total_amount}",
       "channels": ["in_app", "email"]}
REMINDER = {"name": "visit_reminder", "entity": "Visit", "every": "1m", "due_within": {"field": "starts_at", "age": "1d"},
            "do": {"notify": {"to": ["creator"], "title": "Reminder: your visit at {starts_at}", "channels": ["in_app", "email"]}}}


def _plan(rules=None, reminder=True) -> dict:
    data = json.loads(FIXTURE.read_text())
    data["roles"] += [{"id": "staff", "permissions": []}, {"id": "courier", "permissions": []}]
    order = next(e for e in data["entities"] if e["name"] == "Order")
    order["fields"] += [{"name": "courier_id", "type": "uuid", "required": False}]
    data["entities"].append({"name": "Visit", "fields": [{"name": "id", "type": "uuid", "required": True},
                                                          {"name": "starts_at", "type": "datetime", "required": True}], "relations": []})
    data["capabilities"] = [
        {"kind": "workflow", "name": "order_flow", "config": {"entity": "Order", "field": "status", "states": ["pending", "shipped"],
         "initial": "pending", "transitions": [{"name": "ship", "to": "shipped", "from": ["pending"], "roles": ["staff"]}]}},
        {"kind": "ownership", "name": "order_ownership", "config": {"entity": "Order", "read": "own", "write": "own",
         "see_all": ["staff"], "assignee": "courier_id"}},
        {"kind": "notifications", "name": "app_notifications", "config": {"rules": rules if rules is not None else [SHIPPED, ASSIGNED, NEW]}},
    ]
    if reminder:
        data["capabilities"].append({"kind": "jobs", "name": "app_jobs", "config": {"schedules": [REMINDER]}})
    return data


def _ir(**kwargs) -> ApplicationIR:
    return ApplicationIR.from_dict(_plan(**kwargs))


def _files(adapter) -> dict[str, str]:
    return {f.path: f.content for f in adapter.generate(_ir()).files()}


class RulesArePartOfThePlan(TestCase):
    def test_round_trip(self) -> None:
        rules = notifications_of(ApplicationIR.from_dict(_ir().to_dict()))
        self.assertEqual([(r.name, r.when) for r in rules.rules], [("order_shipped", "becomes"), ("order_assigned", "assigned"),
                                                                   ("new_order", "created")])
        self.assertTrue(has_notifications(_ir(rules=[])), "a reminder alone is a notification")
        self.assertTrue(needs_auth(_ir()))

    def test_bad_rules_are_refused(self) -> None:
        for bad in ({**SHIPPED, "entity": "Ghost"}, {**SHIPPED, "to": []}, {**SHIPPED, "to": ["nobody"]},
                    {**SHIPPED, "to": ["role:pilot"]}, {**SHIPPED, "title": "Your {colour} order"},
                    {**SHIPPED, "channels": ["sms"]}, {**SHIPPED, "when": "exploded"},
                    {**SHIPPED, "when": {"field": "status", "becomes": True}},     # status is text
                    {**SHIPPED, "when": {"field": "colour", "becomes": "red"}},
                    {**ASSIGNED, "entity": "Product"},                             # Product has no assignee
                    {**SHIPPED, "entity": "Product", "to": ["assignee"], "when": "created", "title": "x"},
                    {**SHIPPED, "to": ["total_amount"]}):                          # not a user field
            with self.subTest(bad=bad), self.assertRaises(InvalidIRError):
                _ir(rules=[bad])
        with self.assertRaises(InvalidIRError):
            _ir(rules=[SHIPPED, SHIPPED])

    def test_the_tables_and_routes_are_the_platforms(self) -> None:
        data = _plan()
        data["apis"].append({"method": "GET", "path": "/notifications/feed", "auth": True})
        with self.assertRaises(InvalidIRError):
            ApplicationIR.from_dict(data)


class TheDatabaseWritesThem(TestCase):
    def setUp(self) -> None:
        self.schema = render_postgres_schema(_ir())

    def test_tables_and_send(self) -> None:
        for fragment in ('CREATE TABLE IF NOT EXISTS "notification"', 'CREATE TABLE IF NOT EXISTS "notification_mute"',
                         'CREATE OR REPLACE FUNCTION "notification_send"', "\"m\".\"rule\" IN ('*', \"rule_name\")",
                         '"uq_notification_reminder"'):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.schema)

    def test_triggers(self) -> None:
        self.assertIn('CREATE TRIGGER "notify_order" AFTER INSERT OR UPDATE OR DELETE ON "order"', self.schema)
        self.assertIn("(TG_OP = 'UPDATE' AND NEW.\"status\" = 'shipped' AND OLD.\"status\" IS DISTINCT FROM 'shipped')", self.schema)
        self.assertIn("NEW.\"courier_id\" IS NOT NULL AND (TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND NEW.\"courier_id\" IS DISTINCT FROM OLD.\"courier_id\"))",
                      self.schema, "an assignment is told once, not on every change")
        self.assertIn("SELECT \"id\" AS \"uid\" FROM \"users\" WHERE \"role\" = 'staff'", self.schema)
        self.assertIn("'Total: ' || COALESCE(NEW.\"total_amount\"::text, '')", self.schema)

    def test_text_is_quoted(self) -> None:
        self.assertEqual(text_expression("It's {status}!", "NEW"), "'It''s ' || COALESCE(NEW.\"status\"::text, '') || '!'")

    def test_reminders(self) -> None:
        (reminder,) = compiled_schedules(_ir())
        self.assertEqual(reminder.action, "notify")
        self.assertIn('"starts_at" BETWEEN NOW() AND NOW() + make_interval(secs => 86400)', reminder.sql)
        self.assertIn("NOT EXISTS (SELECT 1 FROM \"notification\" \"n\" WHERE \"n\".\"rule\" = 'reminder:visit_reminder'", reminder.sql)
        self.assertTrue(reminder.sql.startswith('SELECT 1 FROM (SELECT "t".*, "who"."uid" AS "notify_uid"'), "one row back per notification")

    def test_live_to_their_recipient_alone(self) -> None:
        notification = next(t for t in live_tables(_ir()) if t.table == "notification")
        self.assertEqual((notification.strict, notification.assignee, notification.see_all), (True, "user_id", ()))
        self.assertIn('ON "notification" FOR EACH ROW EXECUTE FUNCTION "realtime_notify"(\'user_id\')', self.schema)

    def test_catalogue(self) -> None:
        self.assertEqual([(r.rule, r.label, r.only_roles) for r in rule_catalogue(_ir())],
                         [("order_shipped", "Your order is on its way", ()), ("order_assigned", "Order … is assigned to you", ()),
                          ("new_order", "New order: …", ("staff",)), ("reminder:visit_reminder", "Reminder: your visit at …", ())])


class EveryBackendServesThem(TestCase):
    def test_python(self) -> None:
        files = _files(PythonBackendAdapter())
        ast.parse(files["app/notifications.py"])
        self.assertIn("await notifications.start()", files["app/main.py"])
        self.assertIn("EMAIL_API_URL=", files[".env.example"])
        self.assertIn('"only_roles": [\'staff\']', files["app/notifications.py"])

    def test_go(self) -> None:
        files = _files(GoBackendAdapter())
        self.assertIn("\tgo h.RunNotifications()", files["main.go"])
        self.assertIn('mux.HandleFunc("PUT /notifications/preferences", handlers.RequireAuth(h.NotificationsSetPreference))', files["main.go"])
        self.assertIn('"notification": {Entity: "Notification", Owned: true, SeeAll: []string{}, Strict: true},',
                      files["internal/handlers/realtime.go"])

    def test_node(self) -> None:
        for adapter, mount in ((ExpressBackendAdapter(), "app.use(notificationsRouter);"), (HonoBackendAdapter(), "app.route('/', notificationsRouter);")):
            files = _files(adapter)
            with self.subTest(adapter=type(adapter).__name__):
                self.assertIn("startNotifications();", files["src/index.ts"])
                self.assertIn(mount, files["src/app.ts"])
                router = files["src/notifications/router.ts"]
                self.assertLess(router.index("'/notifications/read-all'"), router.index("'/notifications/:notificationId/read'"))


class ThePagesShowThem(TestCase):
    def test_bell_and_page(self) -> None:
        web = NextjsWebAdapter().generate(_ir())
        self.assertIn("<NotificationBell />", web.get("components/navbar.tsx").content)
        self.assertIn('useLive("Notification"', web.get("components/notification-bell.tsx").content)
        self.assertIn("setPreference", web.get("app/notifications/page.tsx").content)
        self.assertIn("lib/realtime.ts", {f.path for f in web.files()})
        admin = NextjsAdminAdapter().generate(_ir())
        self.assertIn('"/notifications"', admin.get("components/admin/nav.ts").content)

    def test_none_without_rules(self) -> None:
        data = _plan(rules=[], reminder=False)
        data["capabilities"] = [c for c in data["capabilities"] if c["kind"] != "notifications"]
        web = NextjsWebAdapter().generate(ApplicationIR.from_dict(data))
        self.assertNotIn("components/notification-bell.tsx", {f.path for f in web.files()})


class ThePlannerReadsThePrompt(TestCase):
    def _data(self) -> dict:
        data = _plan(rules=[], reminder=False)
        data["capabilities"] = [c for c in data["capabilities"] if c["kind"] != "notifications"]
        return data

    def _caps(self, prompt: str) -> dict:
        data = self._data()
        notifications_from_prompt(prompt, data)
        return {c["kind"]: c["config"] for c in data["capabilities"]}

    def test_rules(self) -> None:
        cases = (("Notify the customer when their order is shipped.", {"field": "status", "becomes": "shipped"}, ["creator"], ["in_app"]),
                 ("Email staff when a new order is placed.", "created", ["role:staff"], ["in_app", "email"]),
                 ("Tell the courier when an order is assigned to them.", "assigned", ["assignee"], ["in_app"]))
        for prompt, when, to, channels in cases:
            with self.subTest(prompt=prompt):
                (rule,) = self._caps(prompt)["notifications"]["rules"]
                self.assertEqual((rule["when"], rule["to"], rule["channels"]), (when, to, channels))

    def test_a_plain_status_without_a_lifecycle(self) -> None:
        data = self._data()
        data["capabilities"] = [c for c in data["capabilities"] if c["kind"] != "workflow"]
        notifications_from_prompt("Email the customer when their order is delivered. Email staff when a new order is placed.", data)
        rules = next(c for c in data["capabilities"] if c["kind"] == "notifications")["config"]["rules"]
        self.assertEqual([r["when"] for r in rules], [{"field": "status", "becomes": "delivered"}, "created"],
                         "'placed' is a new order, not a status")

    def test_reminder(self) -> None:
        (schedule,) = self._caps("Remind customers a day before their visit by email.")["jobs"]["schedules"]
        self.assertEqual((schedule["entity"], schedule["due_within"], schedule["do"]["notify"]["channels"]),
                         ("Visit", {"field": "starts_at", "age": "1d"}, ["in_app", "email"]))

    def test_nothing_invented(self) -> None:
        for prompt in ("Customers can track their orders.", "Notify the pilot when the rocket lands."):
            with self.subTest(prompt=prompt):
                self.assertNotIn("notifications", self._caps(prompt))

    def test_repair(self) -> None:
        data = _plan(rules=[SHIPPED, {**NEW, "entity": "orders"}, {**ASSIGNED, "entity": "Product"}, {**NEW, "to": ["role:pilot"]}])
        data["capabilities"].append({"kind": "notifications", "name": "more", "config": {"rules": [copy.deepcopy({**SHIPPED, "name": "again"})]}})
        repaired, notes = repair_ir_dict(data)
        rules = notifications_of(ApplicationIR.from_dict(repaired))
        self.assertEqual([r.name for r in rules.rules], ["order_shipped", "new_order", "again"])
        self.assertTrue(any("merged" in n for n in notes))


class PushToThePhone(TestCase):
    """PC-121: the push channel, devices, the sender, and the phone app's registration."""

    def _ir(self):
        return _ir(rules=[{**SHIPPED, "channels": ["in_app", "push"]}, NEW])

    def test_the_channel_and_the_database(self) -> None:
        schema = render_postgres_schema(self._ir())
        for fragment in ('CREATE TABLE IF NOT EXISTS "push_device"', 'ADD COLUMN IF NOT EXISTS "push_status"',
                         "CHECK (\"channel\" IN ('in_app', 'email', 'push'))", '"want_push" boolean',
                         'DROP FUNCTION IF EXISTS "notification_send"(uuid, varchar, varchar, uuid, text, text, boolean, boolean);'):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, schema)
        self.assertIn("'', TRUE, FALSE, TRUE)", schema.replace("'Total: ' || COALESCE(NEW.\"total_amount\"::text, '')", "''"))
        with self.assertRaises(InvalidIRError):
            _ir(rules=[{**SHIPPED, "channels": ["pigeon"]}])

    def test_every_backend_sends(self) -> None:
        python = {f.path: f.content for f in PythonBackendAdapter().generate(self._ir()).files()}
        ast.parse(python["app/notifications.py"])
        self.assertIn("await send_due_pushes()", python["app/notifications.py"])
        self.assertIn('"DeviceNotRegistered"', python["app/notifications.py"])
        go = {f.path: f.content for f in GoBackendAdapter().generate(self._ir()).files()}
        self.assertIn('mux.HandleFunc("POST /notifications/devices", handlers.RequireAuth(h.NotificationsRegisterDevice))', go["main.go"])
        node = {f.path: f.content for f in ExpressBackendAdapter().generate(self._ir()).files()}
        self.assertIn("router.delete('/notifications/devices/:token', requireAuth,", node["src/notifications/router.ts"])
        self.assertIn("EXPO_PUSH_URL=", python[".env.example"])

    def test_the_phone_registers_after_sign_in(self) -> None:
        from omnistackai_agent_engine.codegen.react_native import ReactNativeAdapter

        files = {f.path: f.content for f in ReactNativeAdapter().generate(self._ir()).files()}
        self.assertIn('"expo-notifications": "~0.28.19"', files["package.json"])
        self.assertIn("<PushRegistration />", files["src/app/App.tsx"])
        module = files["src/shared/notifications/PushRegistration.tsx"]
        self.assertIn("getExpoPushTokenAsync({ projectId })", module)
        self.assertIn("apiClient.post('/notifications/devices'", module)
        plain = {f.path for f in ReactNativeAdapter().generate(_ir()).files()}
        self.assertNotIn("src/shared/notifications/PushRegistration.tsx", plain, "no push channel, no push code")

    def test_the_prompt(self) -> None:
        data = _plan(rules=[], reminder=False)
        data["capabilities"] = [c for c in data["capabilities"] if c["kind"] != "notifications"]
        notifications_from_prompt("Send a push notification to the customer's phone when their order is shipped.", data)
        (rule,) = next(c for c in data["capabilities"] if c["kind"] == "notifications")["config"]["rules"]
        self.assertEqual(rule["channels"], ["in_app", "push"])

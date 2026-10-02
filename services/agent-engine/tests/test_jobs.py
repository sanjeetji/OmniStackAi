"""R-568: background jobs and scheduling in generated apps.

These check the plan, the shared SQL, each backend's scheduler, the admin page and the planner. The
live proof ran the same plan on Python, Go, Express and Hono through the platform's runner: a
schedule cancelled only the unpaid orders past their time, runs were recorded, a failing schedule
was retried and ended dead, and an admin retried it.
"""

import ast
import copy
import json
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR, InvalidIRError
from omnistackai_agent_engine.application_ir.jobs import jobs_of
from omnistackai_agent_engine.codegen import NextjsAdminAdapter
from omnistackai_agent_engine.codegen import jobs_sql
from omnistackai_agent_engine.codegen.auth_guard import needs_auth
from omnistackai_agent_engine.codegen.backend_go import GoBackendAdapter
from omnistackai_agent_engine.codegen.backend_node import ExpressBackendAdapter, HonoBackendAdapter
from omnistackai_agent_engine.codegen.backend_python import PythonBackendAdapter
from omnistackai_agent_engine.codegen.schema_sql import render_postgres_schema
from omnistackai_agent_engine.intake.ir_repair import repair_ir_dict
from omnistackai_agent_engine.intake.jobs_intent import jobs_from_prompt

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"
CANCEL = {"name": "cancel_unpaid_orders", "entity": "Order", "every": "1m", "where": {"paid": [False]},
          "older_than": {"field": "created_at", "age": "30m"}, "do": {"transition": "cancel"}}
FLAG = {"name": "flag_late_orders", "entity": "Order", "every": "5m",
        "older_than": {"field": "order_date", "age": "0m"}, "do": {"set": {"is_late": True}}}
PURGE = {"name": "purge_old_products", "entity": "Product", "every": "1d",
         "older_than": {"field": "created_at", "age": "365d"}, "do": {"delete": True}}


def _plan(schedules: list | None = None, jobs: bool = True) -> dict:
    data = json.loads(FIXTURE.read_text())
    order = next(e for e in data["entities"] if e["name"] == "Order")
    order["fields"] += [{"name": "paid", "type": "bool", "required": False},
                        {"name": "is_late", "type": "bool", "required": False}]
    data["entities"].append({"name": "Invoice", "fields": [
        {"name": "id", "type": "uuid", "required": True},
        {"name": "due_date", "type": "datetime", "required": False},
        {"name": "is_overdue", "type": "bool", "required": False}], "relations": []})
    data["capabilities"] = [{"kind": "workflow", "name": "order_flow", "config": {
        "entity": "Order", "field": "status", "states": ["pending", "paid", "shipped", "cancelled"], "initial": "pending",
        "transitions": [{"name": "pay", "to": "paid", "from": ["pending"]},
                        {"name": "ship", "to": "shipped", "from": ["paid"], "roles": ["admin"]},
                        {"name": "cancel", "to": "cancelled", "from": ["pending"]}]}}]
    if jobs:
        data["capabilities"].append({"kind": "jobs", "name": "app_jobs", "config": {
            "schedules": schedules if schedules is not None else [CANCEL, FLAG, PURGE]}})
    return data


def _ir(schedules: list | None = None) -> ApplicationIR:
    return ApplicationIR.from_dict(_plan(schedules))


def _files(adapter) -> dict[str, str]:
    return {f.path: f.content for f in adapter.generate(_ir()).files()}


class TheScheduleIsPartOfThePlan(TestCase):
    def test_round_trip(self) -> None:
        jobs = jobs_of(ApplicationIR.from_dict(_ir().to_dict()))
        self.assertEqual([s.name for s in jobs.schedules], ["cancel_unpaid_orders", "flag_late_orders", "purge_old_products"])
        self.assertEqual([(s.action, s.every_seconds) for s in jobs.schedules],
                         [("transition", 60), ("set", 300), ("delete", 86400)])
        self.assertTrue(needs_auth(_ir()), "an admin watches the jobs, so the app has accounts")

    def test_bad_schedules_are_refused(self) -> None:
        for bad in ({**CANCEL, "where": {}, "older_than": None},          # every row, every minute
                    {**CANCEL, "every": "10s"}, {**CANCEL, "every": "30d"},
                    {**CANCEL, "entity": "Ghost"},
                    {**CANCEL, "do": {"transition": "refund"}},           # not a transition of Order
                    {**CANCEL, "do": {"set": {"status": "cancelled"}}},   # the lifecycle is the workflow's
                    {**CANCEL, "do": {"transition": "cancel", "delete": True}},
                    {**CANCEL, "where": {"paid": ["no"]}},                # a bool field, a string value
                    {**CANCEL, "where": {"colour": ["red"]}},
                    {**CANCEL, "older_than": {"field": "status", "age": "30m"}},
                    {**PURGE, "entity": "Invoice", "do": {"set": {"id": "x"}}},
                    {**CANCEL, "do": {"delete": False}}, {**CANCEL, "cron": "* * * * *"}):
            with self.subTest(bad=bad), self.assertRaises(InvalidIRError):
                _ir([{k: v for k, v in bad.items() if v is not None}])
        with self.assertRaises(InvalidIRError):
            _ir([CANCEL, CANCEL])

    def test_the_scheduler_owns_its_routes_and_tables(self) -> None:
        data = _plan()
        data["apis"].append({"method": "GET", "path": "/scheduler/status", "auth": False})
        with self.assertRaises(InvalidIRError):
            ApplicationIR.from_dict(data)
        data = _plan()
        data["entities"].append({"name": "SchedulerRun", "fields": [{"name": "id", "type": "uuid", "required": True}]})
        with self.assertRaises(InvalidIRError):
            ApplicationIR.from_dict(data)


class OneStatementPerSchedule(TestCase):
    def setUp(self) -> None:
        self.compiled = {c.name: c for c in jobs_sql.compiled_schedules(_ir())}

    def test_a_transition_moves_only_rows_the_workflow_allows(self) -> None:
        sql = self.compiled["cancel_unpaid_orders"].sql
        self.assertTrue(sql.startswith('UPDATE "order" SET "status" = \'cancelled\', "updated_at" = NOW() WHERE "id" IN ('))
        for fragment in ('"paid" = FALSE', '"status" IN (\'pending\')', '"created_at" < NOW() - make_interval(secs => 1800)',
                         f"LIMIT {jobs_sql.BATCH} FOR UPDATE SKIP LOCKED"):
            self.assertIn(fragment, sql)
        self.assertEqual(self.compiled["cancel_unpaid_orders"].description,
                         "Every minute: cancel Orders where paid is false and status is pending, 30 minutes after created_at.")

    def test_set_leaves_rows_that_already_hold_the_value(self) -> None:
        sql = self.compiled["flag_late_orders"].sql
        self.assertIn('"is_late" IS DISTINCT FROM TRUE', sql)
        self.assertIn('"order_date" < NOW() ORDER BY', sql, "an age of 0m is a time that has passed")

    def test_delete_is_bounded(self) -> None:
        sql = self.compiled["purge_old_products"].sql
        self.assertTrue(sql.startswith('DELETE FROM "product" WHERE "id" IN (SELECT "id" FROM "product" WHERE'))
        self.assertIn("LIMIT 500", sql)

    def test_values_are_quoted(self) -> None:
        schedule = {**PURGE, "entity": "Order", "where": {"status": ["it's"]}}
        sql = jobs_sql.compiled_schedules(_ir([schedule]))[0].sql
        self.assertIn("\"status\" = 'it''s'", sql)

    def test_schema_and_sync(self) -> None:
        schema = render_postgres_schema(_ir())
        for fragment in ('CREATE TABLE IF NOT EXISTS "scheduler_schedule"', 'CREATE TABLE IF NOT EXISTS "scheduler_run"',
                         "CHECK (\"status\" IN ('queued', 'running', 'done', 'failed', 'dead'))"):
            self.assertIn(fragment, schema)
        self.assertNotIn("scheduler_run", render_postgres_schema(ApplicationIR.from_dict(_plan(jobs=False))))
        sync = jobs_sql.sync_statements(_ir())
        self.assertIn("ON CONFLICT (\"name\") DO UPDATE SET \"every_seconds\" = EXCLUDED.\"every_seconds\"", sync[0])
        self.assertTrue(sync[-1].endswith("NOT IN ('cancel_unpaid_orders', 'flag_late_orders', 'purge_old_products')"))

    def test_runs_are_claimed_once_and_retried_then_dead(self) -> None:
        self.assertIn("FOR UPDATE SKIP LOCKED", jobs_sql.CLAIM)
        self.assertIn("\"locked_until\" < NOW()", jobs_sql.CLAIM, "a run whose worker died is taken again")
        self.assertIn("WHEN \"attempts\" >= \"max_attempts\" THEN 'dead' ELSE 'failed'", jobs_sql.FAILED)
        self.assertIn("make_interval(secs => 10 * power(2, \"attempts\"))", jobs_sql.FAILED)
        self.assertIn("\"status\" IN ('failed', 'dead')", jobs_sql.RETRY)

    def test_placeholders_in_order_for_every_driver(self) -> None:
        for name in ("MANUAL", "DONE", "FAILED", "RECORD", "PAUSE", "RETRY", "RUNS_WITH_STATUS"):
            jobs_sql.python_placeholders(getattr(jobs_sql, name))
        with self.assertRaises(ValueError):
            jobs_sql.python_placeholders("UPDATE t SET a = $2 WHERE b = $1")


class Python(TestCase):
    def setUp(self) -> None:
        self.files = _files(PythonBackendAdapter())
        self.jobs = self.files["app/jobs.py"]
        ast.parse(self.jobs)

    def test_started_with_the_app(self) -> None:
        main = self.files["app/main.py"]
        ast.parse(main)
        self.assertIn("await jobs.start()", main)
        self.assertIn('app = FastAPI(title="Hiring Portal", lifespan=lifespan)', main)
        self.assertIn("app.include_router(jobs.router)", main)
        self.assertIn("SCHEDULER_TICK_SECONDS=", self.files[".env.example"])

    def test_admin_only(self) -> None:
        for route in ("/scheduler/schedules", "/scheduler/schedules/{name}/run", "/scheduler/runs",
                      "/scheduler/runs/{run_id}/retry"):
            body = self.jobs.split(f'"{route}")')[1].split("\n\n\n")[0]
            with self.subTest(route=route):
                self.assertIn("_admin(claims)", body)

    def test_python_placeholders(self) -> None:
        self.assertNotIn("$1", self.jobs)


class Go(TestCase):
    def test_wired(self) -> None:
        files = _files(GoBackendAdapter())
        main, jobs = files["main.go"], files["internal/handlers/jobs.go"]
        self.assertIn("\tgo h.RunScheduler()", main)
        self.assertIn('mux.HandleFunc("POST /scheduler/runs/{runId}/retry", handlers.RequireAuth(h.SchedulerRetry))', main)
        self.assertIn("if !SeesAll(ClaimsFrom(r)) {", jobs)
        self.assertIn('"cancel_unpaid_orders": {Entity: "Order", EverySeconds: 60', jobs)
        self.assertIn("SCHEDULER_DISABLED=", files[".env.example"])


class Node(TestCase):
    def test_wired(self) -> None:
        for adapter, mount in ((ExpressBackendAdapter(), "app.use(jobsRouter);"), (HonoBackendAdapter(), "app.route('/', jobsRouter);")):
            files = _files(adapter)
            with self.subTest(adapter=type(adapter).__name__):
                self.assertIn("startScheduler();", files["src/index.ts"])
                self.assertIn(mount, files["src/app.ts"])
                self.assertIn("router.post('/scheduler/runs/:runId/retry', requireAuth,", files["src/jobs/router.ts"])
                self.assertIn('"cancel_unpaid_orders": {', files["src/jobs/service.ts"])
                self.assertIn("if (!seesAll(claims, [])) return forbidden;", files["src/jobs/service.ts"])


class TheAdminSeesThem(TestCase):
    def test_page_and_navigation(self) -> None:
        project = NextjsAdminAdapter().generate(_ir())
        paths = {f.path for f in project.files()}
        self.assertIn("app/scheduled-jobs/page.tsx", paths)
        self.assertIn("lib/jobs.ts", paths)
        self.assertIn('"/scheduled-jobs"', project.get("components/admin/nav.ts").content)


class ThePlannerReadsThePrompt(TestCase):
    def _data(self) -> dict:
        return _plan(jobs=False)

    def _schedules(self, prompt: str) -> list:
        data = self._data()
        jobs_from_prompt(prompt, data)
        jobs = next((c for c in data.get("capabilities") or () if c.get("kind") == "jobs"), None)
        return jobs["config"]["schedules"] if jobs else []

    def test_age_rules(self) -> None:
        for prompt in ("Cancel unpaid orders after 30 minutes.", "Orders not paid within 30 minutes are cancelled."):
            with self.subTest(prompt=prompt):
                (schedule,) = self._schedules(prompt)
                self.assertEqual((schedule["entity"], schedule["do"], schedule["where"], schedule["older_than"]),
                                 ("Order", {"transition": "cancel"}, {"paid": [False]}, {"field": "created_at", "age": "30m"}))
        (purge,) = self._schedules("Delete products older than 1 year.")
        self.assertEqual((purge["do"], purge["older_than"]["age"], purge["every"]), ({"delete": True}, "365d", "1h"))

    def test_due_dates(self) -> None:
        (schedule,) = self._schedules("Mark invoices as overdue when the due date passes.")
        self.assertEqual((schedule["entity"], schedule["do"], schedule["older_than"]),
                         ("Invoice", {"set": {"is_overdue": True}}, {"field": "due_date", "age": "0m"}))

    def test_what_people_do_is_not_a_job(self) -> None:
        for prompt in ("Customers can cancel an order within 2 hours.", "A simple shop with orders.",
                       "Expire listings after 30 days."):  # no Listing in the plan
            with self.subTest(prompt=prompt):
                self.assertEqual(self._schedules(prompt), [])

    def test_the_result_is_a_valid_plan(self) -> None:
        data = self._data()
        jobs_from_prompt("Cancel unpaid orders after 30 minutes. Mark invoices overdue after the due date.", data)
        self.assertEqual(len(jobs_of(ApplicationIR.from_dict(data)).schedules), 2)

    def test_repair_drops_what_cannot_run(self) -> None:
        data = _plan([CANCEL, {**FLAG, "entity": "Ghost"}, {**PURGE, "do": {"transition": "archive"}},
                      {**CANCEL, "name": "x", "entity": "orders"}])
        data["capabilities"].append({"kind": "jobs", "name": "more_jobs", "config": {"schedules": [copy.deepcopy(PURGE)]}})
        repaired, notes = repair_ir_dict(data)
        jobs = jobs_of(ApplicationIR.from_dict(repaired))
        self.assertEqual([s.name for s in jobs.schedules], ["cancel_unpaid_orders", "x", "purge_old_products"])
        self.assertEqual(jobs.schedules[1].entity, "Order", "'orders' resolved to the entity")
        self.assertTrue(any("Ghost" in n for n in notes))
        self.assertTrue(any("merged" in n for n in notes))


class AnEcosystemGetsThemToo(TestCase):
    def test_from_the_prompt_to_the_shared_backend_and_the_admin(self) -> None:
        from omnistackai_agent_engine.codegen.ecosystem_assembler import assemble_ecosystem
        from omnistackai_agent_engine.intake.build_app import _with_prompt_rules_for_plan
        from omnistackai_agent_engine.intake.ecosystem import plan_ecosystem_from_prompt
        from omnistackai_agent_engine.intake.ecosystem_intent import detect_ecosystem_intent

        prompt = ("Bazaar Lite: a small marketplace where vendors list products and customers place orders and pay "
                  "online in rupees. Listings are deleted after 90 days.")
        plan = _with_prompt_rules_for_plan(plan_ecosystem_from_prompt(prompt, detect_ecosystem_intent(prompt).option_id), prompt)
        for app in plan.apps:
            with self.subTest(app=app.ir.name):
                (schedule,) = jobs_of(app.ir).schedules
                self.assertEqual((schedule.entity, schedule.action, schedule.older_than), ("Listing", "delete", ("created_at", "90d")))
        files = {f.path for f in assemble_ecosystem(plan, prompt=prompt).files()}
        self.assertLessEqual({"services/api/app/jobs.py", "apps/admin/app/scheduled-jobs/page.tsx"}, files)


class AtATimeOfDay(TestCase):
    """PC-117: 'every night at 2am', 'every Monday at 9am', in the app's time zone."""

    def _ir(self, *schedules, timezone=None):
        data = _plan(list(schedules))
        if timezone:
            next(c for c in data["capabilities"] if c["kind"] == "jobs")["config"]["timezone"] = timezone
        return ApplicationIR.from_dict(data)

    def test_the_plan(self) -> None:
        jobs = jobs_of(self._ir({**PURGE, "at": "02:30"}, {**CANCEL, "every": "7d", "at": "09:00", "on": "monday"},
                                timezone="Asia/Kolkata"))
        self.assertEqual(jobs.timezone, "Asia/Kolkata")
        self.assertEqual([(s.at_minutes, s.on_day) for s in jobs.schedules], [(150, None), (540, 0)])
        self.assertEqual(jobs_of(ApplicationIR.from_dict(_ir().to_dict())).timezone, "UTC")

    def test_bad_times_are_refused(self) -> None:
        for bad, zone in (({**PURGE, "at": "2am"}, None), ({**PURGE, "at": "24:00"}, None),
                          ({**CANCEL, "at": "02:00"}, None),                      # every minute, at 2am?
                          ({**PURGE, "on": "monday"}, None),                      # a weekday needs a time
                          ({**PURGE, "at": "02:00", "on": "monday"}, None),       # ... and every 7d
                          ({**PURGE, "every": "7d", "at": "02:00", "on": "funday"}, None),
                          ({**PURGE, "at": "02:00"}, "Mars/Olympus")):
            with self.subTest(bad=bad, zone=zone), self.assertRaises(InvalidIRError):
                self._ir(bad, timezone=zone)

    def test_the_next_run_is_computed_in_the_database(self) -> None:
        ir = self._ir({**PURGE, "at": "02:30"}, {**CANCEL, "every": "7d", "at": "09:00", "on": "monday"}, timezone="Asia/Kolkata")
        self.assertIn('CREATE OR REPLACE FUNCTION "scheduler_next_at"', render_postgres_schema(ir))
        self.assertIn('ADD COLUMN IF NOT EXISTS "timezone"', render_postgres_schema(ir))
        sync = jobs_sql.sync_statements(ir)
        self.assertIn("VALUES ('purge_old_products', 86400, 150, NULL, 'Asia/Kolkata', \"scheduler_next_at\"(150, NULL, 86400, 'Asia/Kolkata'))", sync[0])
        self.assertIn("VALUES ('cancel_unpaid_orders', 604800, 540, 0, 'Asia/Kolkata', ", sync[1])
        self.assertIn("THEN EXCLUDED.\"next_run_at\" ELSE \"scheduler_schedule\".\"next_run_at\" END", sync[0])
        self.assertIn('ELSE "scheduler_next_at"("at_minutes", "on_day", "every_seconds", "timezone") END', jobs_sql.ENQUEUE_DUE)
        self.assertEqual([c.description.split(":")[0] + ":" + c.description.split(":")[1] for c in jobs_sql.compiled_schedules(ir)],
                         ["Every day at 02:30 (Asia/Kolkata)", "Every Monday at 09:00 (Asia/Kolkata)"])

    def test_a_schedule_without_a_time_runs_at_start_up(self) -> None:
        self.assertIn("NULL, NULL, 'UTC', NOW())", jobs_sql.sync_statements(_ir())[0])

    def test_the_prompt(self) -> None:
        cases = (("Every night at 2am delete products older than 1 year. Prices in rupees.", ("1d", "02:00", None), "Asia/Kolkata"),
                 ("Every Monday at 9:30 am, cancel unpaid orders older than 2 hours.", ("7d", "09:30", "monday"), None),
                 ("Daily at 23:15 mark invoices overdue once the due date passes.", ("1d", "23:15", None), None),
                 ("At midnight every day, delete products older than 90 days.", ("1d", "00:00", None), None))
        for prompt, (every, at, on), zone in cases:
            with self.subTest(prompt=prompt):
                data = _plan(jobs=False)
                jobs_from_prompt(prompt, data)
                config = next(c for c in data["capabilities"] if c["kind"] == "jobs")["config"]
                (schedule,) = config["schedules"]
                self.assertEqual((schedule["every"], schedule.get("at"), schedule.get("on")), (every, at, on))
                self.assertEqual(config.get("timezone"), zone)
                ApplicationIR.from_dict(data)

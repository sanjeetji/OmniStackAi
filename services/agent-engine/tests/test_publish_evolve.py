"""PC-049: a published app's database keeps up with its project, and never loses data doing so.

The live proof ran the publisher's migrate step against a real Postgres (plan v1, data, plan v2 with
a new field, a required field, a relation, an entity, notifications, a lifecycle state, a dropped
field; 17 checks) and a real publish and republish of a generated app.
"""

import json
import re
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR
from omnistackai_agent_engine.codegen.schema_sql import render_postgres_schema
from omnistackai_agent_engine.publish.evolve import Column, evolve_sql, parse_columns, plan_evolution, shadow_sql

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"


def col(table, name, type_="text", default="", not_null=False, fk=""):
    return Column(table, name, type_, default, not_null, fk)


class EverySchemaStatementIsSafeToRunAgain(TestCase):
    def test_no_statement_creates_or_adds_without_a_guard(self) -> None:
        data = json.loads(FIXTURE.read_text())
        data["capabilities"] = [{"kind": "workflow", "name": "flow", "config": {"entity": "Order", "field": "status",
                                 "states": ["pending", "shipped"], "initial": "pending", "transitions": []}}]
        sql = render_postgres_schema(ApplicationIR.from_dict(data))
        lines = sql.splitlines()
        for i, line in enumerate(lines):
            text = line.strip()
            if re.match(r"CREATE TABLE ", text):
                self.assertIn("IF NOT EXISTS", text)
            if text.startswith("CREATE TRIGGER"):
                name = text.split()[2]
                self.assertTrue(any(f"DROP TRIGGER IF EXISTS {name}" in prior for prior in lines[:i]), name)
        self.assertIn('ALTER TABLE "order" DROP CONSTRAINT IF EXISTS "chk_order_status";', sql)
        self.assertIn("CHECK (\"status\" IN ('pending', 'shipped')) NOT VALID;", sql)


class ThePlanAddsAndNeverDrops(TestCase):
    def test_columns(self) -> None:
        live = [col("order", "id", "uuid"), col("order", "status"), col("order", "old_note"), col("legacy", "id", "uuid")]
        wanted = [col("order", "id", "uuid"), col("order", "status", "integer"),
                  col("order", "priority", "integer", "0", True),
                  col("order", "gift_note", "text", "", True),
                  col("order", "product_id", "uuid", fk="FOREIGN KEY (product_id) REFERENCES _omnistack_shadow.product(id)"),
                  col("visit", "id", "uuid")]
        plan = plan_evolution(live, wanted)
        self.assertEqual(plan.added, ["order.priority", "order.gift_note", "order.product_id"])
        self.assertIn('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS "priority" integer DEFAULT 0 NOT NULL;', plan.statements)
        self.assertIn('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS "gift_note" text;', plan.statements, "no value for old rows")
        self.assertIn('ALTER TABLE "order" ADD CONSTRAINT "fk_order_product_id" FOREIGN KEY (product_id) REFERENCES product(id) NOT VALID;',
                      plan.statements)
        notes = " | ".join(plan.notes)
        for expected in ("order.status is text live and integer in the plan; left as it is",
                         "order.old_note is no longer in the plan; kept with its data",
                         "table legacy is no longer in the plan; kept with its data",
                         "order.gift_note added without NOT NULL"):
            self.assertIn(expected, notes)
        self.assertFalse(any("DROP COLUMN" in s or "DROP TABLE" in s for s in plan.statements))
        self.assertNotIn("visit", " ".join(plan.statements), "a new table is created whole by the schema")

    def test_nothing_to_do(self) -> None:
        same = [col("order", "id", "uuid")]
        self.assertEqual(plan_evolution(same, same).summary, "no column changes")

    def test_the_sql_around_it(self) -> None:
        self.assertTrue(shadow_sql("SELECT 1;").startswith("DROP SCHEMA IF EXISTS _omnistack_shadow CASCADE;\nCREATE SCHEMA _omnistack_shadow;"))
        self.assertTrue(evolve_sql(plan_evolution([], []), "SELECT 1;").startswith("SET search_path TO public;"))
        self.assertEqual(parse_columns("order\tid\tuuid\tgen_random_uuid()\tt\t\nbad line"),
                         [Column("order", "id", "uuid", "gen_random_uuid()", True, "")])


class AnUnpublishedAppLeavesNoImages(TestCase):
    """Found live (2026-10-02): unpublished apps' images filled Docker's disk and stopped the platform's database."""

    def test_its_images_are_removed(self) -> None:
        import subprocess
        import tempfile

        from omnistackai_agent_engine.publish.stack import StackPublisher

        calls = []

        def runner(args, **kwargs):
            calls.append(args)
            out = "omnistackai/shop-a1-web:1\nomnistackai/shop-a1-api:2\nomnistackai/other-b2-web:1\npostgres:16\n" if args[1:2] == ["images"] else ""
            return subprocess.CompletedProcess(args, 0, stdout=out, stderr="")

        with tempfile.TemporaryDirectory() as root:
            publisher = StackPublisher(Path(root), runner=runner)
            (Path(root) / "app1").mkdir()
            (Path(root) / "app1" / "state.json").write_text(json.dumps({"slug": "shop-a1", "releases": []}))
            publisher.unpublish("app1", root)
        removed = [c[-1] for c in calls if c[1:4] == ["image", "rm", "-f"]]
        self.assertEqual(removed, ["omnistackai/shop-a1-web:1", "omnistackai/shop-a1-api:2"], "only this app's, not another's")

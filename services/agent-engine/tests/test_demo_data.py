"""PC-077: realistic demo rows for the preview - linked, deterministic, and never published."""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import ApplicationIR
from omnistackai_agent_engine.codegen import demo_data

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"


def _ir(**changes) -> ApplicationIR:
    data = json.loads(FIXTURE.read_text())
    data.update(changes)
    return ApplicationIR.from_dict(data)


class TheRows(TestCase):
    def test_every_table_linked_and_deterministic(self) -> None:
        rows = demo_data.plan_rows(_ir())
        self.assertEqual(set(rows), {"Customer", "Order", "OrderItem", "Product"})
        self.assertTrue(all(len(t) == demo_data.ROWS for t in rows.values()))
        customers = {r["id"] for r in rows["Customer"]}
        self.assertTrue(all(o["customer_id"] in customers for o in rows["Order"]), "an order belongs to a customer")
        self.assertEqual(rows, demo_data.plan_rows(_ir()), "the same plan, the same rows")
        first = rows["Customer"][0]
        self.assertTrue(first["email"].startswith(first["first_name"].lower()), "a row's name and email belong together")

    def test_a_lifecycles_states(self) -> None:
        ir = _ir(capabilities=[{"kind": "workflow", "name": "flow", "config": {"entity": "Order", "field": "status",
                 "states": ["placed", "baking", "delivered"], "initial": "placed", "transitions": []}}])
        self.assertEqual([r["status"] for r in demo_data.plan_rows(ir)["Order"]][:3], ["placed", "baking", "delivered"])

    def test_the_models_values_where_they_fit(self) -> None:
        written = {"Product": [{"name": "Lemon Drizzle Cake", "price": 12.5, "sku": "CAKE-1"},
                               {"name": "", "price": "free"}]}
        products = demo_data.plan_rows(_ir(), written)["Product"]
        self.assertEqual((products[0]["name"], products[0]["price"]), ("Lemon Drizzle Cake", 12.5))
        self.assertNotEqual(products[1]["name"], "", "a value that does not fit is generated instead")
        self.assertIsInstance(products[1]["price"], float)

    def test_no_markup_in_plain_text(self) -> None:
        written = {"Product": [{"name": "French <strong>Butter</strong> Croissant"}]}
        self.assertEqual(demo_data.plan_rows(_ir(), written)["Product"][0]["name"], "French Butter Croissant")

    def test_sql(self) -> None:
        sql = demo_data.render_sql(_ir(), demo_data.plan_rows(_ir()))
        self.assertTrue(sql.startswith("-- Demo data") and "BEGIN;" in sql and sql.rstrip().endswith("COMMIT;"))
        self.assertIn('INSERT INTO "order"', sql)
        self.assertIn("ON CONFLICT DO NOTHING", sql)


class PreviewOnly(TestCase):
    def test_the_preview_loads_it_and_publishing_does_not(self) -> None:
        from omnistackai_agent_engine.localrun.plan import build_run_plan
        from omnistackai_agent_engine.publish.bundle import migrations

        with tempfile.TemporaryDirectory() as tmp:
            api = Path(tmp) / "services" / "api"
            (api / "migrations").mkdir(parents=True)
            (api / "demo").mkdir()
            (api / "requirements.txt").write_text("fastapi\n")
            (api / "migrations" / "0001_init.sql").write_text("select 1;")
            (api / "demo" / "demo_data.sql").write_text("select 2;")
            steps = build_run_plan(tmp).steps
            labels = [s.label for s in steps]
            demo = next(s for s in steps if "demo data" in s.label)
            self.assertGreater(labels.index(demo.label), labels.index("apply migration 0001_init.sql"))
            self.assertTrue(demo.tolerate_failure, "demo data never stops a preview")
            published = [str(p) for p in migrations(Path(tmp))]
        self.assertFalse(any("demo" in p for p in published), published)


class TheBuildWritesIt(TestCase):
    def test_with_and_without_a_confirmed_brief(self) -> None:
        from omnistackai_agent_engine.intake.build_app import build_app_from_prompt
        from omnistackai_agent_engine.intake.scope import propose_scope

        class Model:
            provider_id = "fake"

            async def generate(self, request):
                text = request.messages[-1].content
                if "demo data" in text:
                    return SimpleNamespace(text=json.dumps({"Product": [{"name": "Masala Chai", "price": 4.5}]}))
                return SimpleNamespace(text=FIXTURE.read_text())

        prompt = "A shop where customers order products."
        for scope, by in ((None, "generated"), (propose_scope(prompt).to_dict(), "model")):
            with self.subTest(by=by), tempfile.TemporaryDirectory() as tmp, \
                    mock.patch.dict(os.environ, {"OMNISTACKAI_PLAN_REVIEW": "0", "OMNISTACKAI_BUILD_VERIFY": "off"}):
                built = asyncio.run(build_app_from_prompt(prompt, Model(), Path(tmp) / "repo", model_id="m",
                                                          author_name="t", author_email="t@example.com", scope=scope))
                sql = (Path(tmp) / "repo" / demo_data.PATH).read_text()
                self.assertEqual(built.scope["demo_data"]["values_by"], by)
                self.assertEqual("Masala Chai" in sql, by == "model")


class NeverFailsABuild(TestCase):
    """Found live: a plan whose tables referred to each other in a cycle failed the whole build."""

    def test_a_cycle(self) -> None:
        data = json.loads(FIXTURE.read_text())
        customer = next(e for e in data["entities"] if e["name"] == "Customer")
        customer.setdefault("relations", []).append({"kind": "many_to_one", "name": "last_order", "target_entity": "Order"})
        ir = ApplicationIR.from_dict(data)
        sql = demo_data.demo_sql(ir)
        self.assertTrue(sql and 'INSERT INTO "customer"' in sql)

    def test_anything_else(self) -> None:
        with mock.patch.object(demo_data, "plan_rows", side_effect=RuntimeError("boom")):
            self.assertIsNone(demo_data.demo_sql(_ir()))

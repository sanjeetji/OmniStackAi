"""R-582: the plan is checked against the prompt, and revised once when it lacks something."""

import asyncio
import copy
import json
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR
from omnistackai_agent_engine.intake.nl_to_ir import generate_ir
from omnistackai_agent_engine.intake.plan_critique import accept, critique
from types import SimpleNamespace

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"
SHOP = "A shop where customers order products and leave reviews with photos. Admins see a sales dashboard."


def _plan() -> dict:
    return json.loads(FIXTURE.read_text())


def _with_reviews(data: dict) -> dict:
    data = copy.deepcopy(data)
    data["entities"].append({"name": "Review", "fields": [
        {"name": "id", "type": "uuid", "required": True}, {"name": "rating", "type": "int", "required": True},
        {"name": "comment", "type": "text", "required": False}],
        "relations": [{"kind": "many_to_one", "name": "product", "target_entity": "Product"}]})
    data["apis"] += [{"method": "GET", "path": "/reviews", "auth": False}, {"method": "POST", "path": "/reviews", "auth": True},
                     {"method": "GET", "path": "/reviews/{reviewId}", "auth": False}]
    return data


class TheCritique(TestCase):
    def test_what_the_prompt_names_and_the_plan_lacks(self) -> None:
        gaps = critique("Patients book appointments with doctors, upload reports and chat with their doctor.",
                        ApplicationIR.from_dict(_plan()))
        texts = " | ".join(g.text for g in gaps)
        for expected in ("no Appointment entity", "no Report entity", "messages: a Message entity", "no doctor role", "no patient role"):
            self.assertIn(expected, texts)

    def test_no_false_alarms(self) -> None:
        ir = ApplicationIR.from_dict(_plan())
        self.assertEqual(critique("Sales analytics dashboard for a small online shop showing orders, customers and "
                                  "revenue by product.", ir), [], "customers are data here; the dashboard exists")
        self.assertEqual([g.text for g in critique(SHOP, ir)], ['the prompt says "leave reviews" but the plan has no Review entity'],
                         "photos: the plan has attachments; the review is asked for once")

    def test_accept_only_what_loses_nothing(self) -> None:
        first = ApplicationIR.from_dict(_plan())
        gaps = critique(SHOP, first)
        self.assertTrue(accept(first, ApplicationIR.from_dict(_with_reviews(_plan())), gaps, SHOP)[0])
        dropped = _with_reviews(_plan())
        dropped["entities"] = [e for e in dropped["entities"] if e["name"] != "OrderItem"]
        dropped["apis"] = [a for a in dropped["apis"] if "order-items" not in a["path"] and "items" not in a["path"]]
        ok, why = accept(first, ApplicationIR.from_dict(dropped), gaps, SHOP)
        self.assertFalse(ok)
        self.assertIn("dropped OrderItem", why)
        self.assertFalse(accept(first, first, gaps, SHOP)[0], "closing nothing is not a revision")


class _Model:
    provider_id = "fake"

    def __init__(self, *answers: str) -> None:
        self.answers = list(answers)
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        return SimpleNamespace(text=self.answers.pop(0))


class ThePlannerRevises(TestCase):
    def _run(self, model):
        return asyncio.run(generate_ir(SHOP, model, model_id="fake-model"))

    def test_a_revision_that_closes_the_gap_is_kept(self) -> None:
        model = _Model(json.dumps(_plan()), json.dumps(_with_reviews(_plan())))
        result = self._run(model)
        self.assertIn("Review", [e.name for e in result.ir.entities])
        self.assertEqual(len(model.requests), 2)
        self.assertIn("no Review entity", model.requests[1].messages[-1].content)
        self.assertTrue(any(r.startswith("plan review: closed 1 of 1") for r in result.repairs), result.repairs)

    def test_a_bad_revision_keeps_the_first_plan(self) -> None:
        result = self._run(_Model(json.dumps(_plan()), "not json at all"))
        self.assertNotIn("Review", [e.name for e in result.ir.entities])
        self.assertTrue(any("plan review kept the first plan" in r for r in result.repairs), result.repairs)
        self.assertTrue(any("no Review entity" in r for r in result.repairs), "the gap is still reported")

    def test_no_gap_no_second_call(self) -> None:
        model = _Model(json.dumps(_with_reviews(_plan())))
        self._run(model)
        self.assertEqual(len(model.requests), 1)

    def test_it_can_be_turned_off(self) -> None:
        import os

        model = _Model(json.dumps(_plan()))
        os.environ["OMNISTACKAI_PLAN_REVIEW"] = "0"
        try:
            self._run(model)
        finally:
            del os.environ["OMNISTACKAI_PLAN_REVIEW"]
        self.assertEqual(len(model.requests), 1)


class WhatNeedsNoModel(TestCase):
    def test_an_entity_nobody_can_reach_gets_its_endpoints(self) -> None:
        from omnistackai_agent_engine.intake.plan_critique import with_endpoints

        data = _plan()
        data["entities"].append({"name": "ServiceCategory", "fields": [{"name": "id", "type": "uuid", "required": True},
                                                                        {"name": "name", "type": "string", "required": True}]})
        ir, notes = with_endpoints(ApplicationIR.from_dict(data))
        paths = {(a.method.value, a.path) for a in ir.apis if a.response_schema == "ServiceCategory" or a.request_schema == "ServiceCategory"}
        self.assertEqual(paths, {("GET", "/service_categories"), ("POST", "/service_categories"),
                                 ("GET", "/service_categories/{serviceCategoryId}"), ("PUT", "/service_categories/{serviceCategoryId}")})
        self.assertTrue(any(a.method.value == "DELETE" and a.path == "/service_categories/{serviceCategoryId}" for a in ir.apis))
        self.assertEqual(notes, ("ServiceCategory had no endpoints; the standard five were added",))

    def test_british_spelling_is_not_a_gap(self) -> None:
        data = _plan()
        data["entities"].append({"name": "Favorite", "fields": [{"name": "id", "type": "uuid", "required": True}]})
        data["apis"].append({"method": "GET", "path": "/favorites", "auth": True, "response_schema": "Favorite"})
        self.assertEqual(critique("Customers save favourites.", ApplicationIR.from_dict(data)), [])


class ARelationToNothingIsRepaired(TestCase):
    """Found in R-582's live proof: Enrollment.student -> User failed the whole build."""

    def test_person_misnamed_and_missing(self) -> None:
        from omnistackai_agent_engine.intake.ir_repair import repair_ir_dict

        data = _plan()
        order = next(e for e in data["entities"] if e["name"] == "Order")
        order["relations"] += [{"kind": "many_to_one", "name": "student", "target_entity": "User"},
                               {"kind": "many_to_one", "name": "thing", "target_entity": "Gizmo"},
                               {"kind": "many_to_one", "name": "item", "target_entity": "products"}]
        repaired, notes = repair_ir_dict(data)
        ir = ApplicationIR.from_dict(repaired)
        order = next(e for e in ir.entities if e.name == "Order")
        self.assertIn("student_id", [f.name for f in order.fields])
        self.assertEqual(sorted((r.name, r.target_entity) for r in order.relations),
                         [("customer", "Customer"), ("item", "Product")])
        self.assertEqual(len([n for n in notes if "Order." in n]), 3)

    def test_an_ownership_value_that_does_not_exist(self) -> None:
        from omnistackai_agent_engine.intake.ir_repair import repair_ir_dict

        data = _plan()
        data["capabilities"] = [{"kind": "ownership", "name": "o", "config": {"entity": "Order", "read": "all", "write": "none"}}]
        repaired, notes = repair_ir_dict(data)
        self.assertEqual(ApplicationIR.from_dict(repaired).capabilities[0].config["write"], "own")
        self.assertTrue(any("'none' read as 'own'" in n for n in notes))


class ABlankValidationRuleIsDropped(TestCase):
    """Found live in PC-130: one "" in a field's validation list failed a whole build."""

    def test_blank_rules(self) -> None:
        from omnistackai_agent_engine.intake.ir_repair import repair_ir_dict

        data = _plan()
        field = next(e for e in data["entities"] if e["name"] == "Order")["fields"][0]
        field["validation"] = ["", "  min:0  ", None, "max:10"]
        repaired, notes = repair_ir_dict(data)
        ir = ApplicationIR.from_dict(repaired)
        order = next(e for e in ir.entities if e.name == "Order")
        self.assertEqual(list(order.fields[0].validation), ["min:0", "max:10"])
        self.assertTrue(any("empty validation rule" in n for n in notes))

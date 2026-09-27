"""PC-094: intake repairs, round two — the shapes weaker models got wrong on 2026-09-26.

* qwen2.5-coder:7b declared the role `user` twice, and the whole plan was rejected;
* nemotron wrote a lifecycle for `Orders` when the entity was `Order`, and one for an entity the
  plan never declared;
* qwen3.8-27b sent a malformed part and intake crashed with an AttributeError instead of a clean
  error the fallback chain and the user can act on.

As in PC-093, no repair is silent: each one is reported.
"""

import json
from unittest import TestCase

from omnistackai_agent_engine.application_ir.workflow import workflows_of
from omnistackai_agent_engine.intake.nl_to_ir import IntakeResponseError, parse_ir_response_with_repairs
from test_intake_repair import _plan


def _workflow(entity="Order", field="status", roles=("author",), name="order_lifecycle") -> dict:
    return {"kind": "workflow", "name": name, "config": {
        "entity": entity, "field": field, "states": ["placed", "accepted", "delivered"], "initial": "placed",
        "transitions": [{"name": "accept", "from": ["placed"], "to": "accepted", "roles": list(roles)},
                        {"name": "deliver", "from": ["accepted"], "to": "delivered", "roles": list(roles)}],
    }}


def _parse(data: dict):
    return parse_ir_response_with_repairs(json.dumps(data))


class DuplicatesCollapseToOne(TestCase):
    def test_a_role_declared_twice(self) -> None:
        data = _plan()
        data["roles"].append(dict(data["roles"][0]))
        ir, repairs = _parse(data)
        self.assertEqual([r.id for r in ir.roles], ["author", "reader"])
        self.assertIn("role 'author' was declared more than once; kept one", repairs)

    def test_an_entity_declared_twice_keeps_both_halves(self) -> None:
        data = _plan()
        data["entities"].append({"name": "Order", "fields": [
            {"name": "id", "type": "uuid", "primary_key": True}, {"name": "total", "type": "float"}]})
        ir, repairs = _parse(data)
        order = next(e for e in ir.entities if e.name == "Order")
        self.assertEqual([f.name for f in order.fields], ["id", "item", "status", "total"])
        self.assertTrue(any("entity 'Order'" in r for r in repairs))

    def test_screens_endpoints_and_fields(self) -> None:
        data = _plan()
        data["screens"].append(dict(data["screens"][0]))
        data["apis"].append(dict(data["apis"][0]))
        data["entities"][0]["fields"].append(dict(data["entities"][0]["fields"][1]))
        ir, repairs = _parse(data)
        self.assertEqual(len(repairs), 3)

    def test_a_clean_plan_is_untouched(self) -> None:
        _, repairs = _parse(_plan())
        self.assertEqual(repairs, ())


class LifecyclesNameWhatThePlanHas(TestCase):
    def test_a_plural_or_suffixed_entity_is_resolved(self) -> None:
        ir, repairs = _parse(_plan(capabilities=[_workflow(entity="Orders")]))
        self.assertEqual([w.entity for w in workflows_of(ir)], ["Order"])
        self.assertIn("lifecycle 'order_lifecycle': entity 'Orders' resolved to Order", repairs)

    def test_an_undeclared_entity_removes_the_lifecycle_not_the_build(self) -> None:
        ir, repairs = _parse(_plan(capabilities=[_workflow(entity="Shipment", name="shipment_lifecycle")]))
        self.assertEqual(workflows_of(ir), ())
        self.assertIn("lifecycle 'shipment_lifecycle': entity 'Shipment' is not in the plan; removed", repairs)

    def test_a_missing_field_removes_the_lifecycle(self) -> None:
        ir, repairs = _parse(_plan(capabilities=[_workflow(field="stage")]))
        self.assertEqual(workflows_of(ir), ())
        self.assertTrue(any("has no field 'stage'" in r for r in repairs))

    def test_undeclared_roles_leave_the_transition(self) -> None:
        ir, repairs = _parse(_plan(capabilities=[_workflow(roles=("author", "courier"))]))
        (workflow,) = workflows_of(ir)
        self.assertEqual({r for t in workflow.transitions for r in t.roles}, {"author"})
        self.assertTrue(any("courier" in r for r in repairs))


class AMalformedPartIsACleanError(TestCase):
    def test_no_attribute_error_escapes(self) -> None:
        for broken in (
            {"roles": ["author", "reader"]},                     # strings where objects belong
            {"entities": [{"name": "Post", "fields": "id, title"}]},
            {"capabilities": [{"kind": "workflow", "name": "x", "config": "Order"}]},
            {"apis": [{"method": ["GET"], "path": "/posts"}]},
        ):
            with self.subTest(part=next(iter(broken))):
                try:
                    _parse(_plan(**broken))
                except IntakeResponseError:
                    pass  # a clean, catchable rejection
                # anything else propagates and fails the test

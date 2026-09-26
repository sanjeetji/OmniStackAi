"""PC-093: intake repairs the model's two commonest mistakes instead of rejecting the build.

Each case below is the shape of a real rejection from PC-047's comparison run on 2026-09-26:
`PATCH /appointments/{appointmentId}/status` with a request body naming a type nobody declared,
`PATCH /orders/{orderId}/status` with a body of `'json'`, and `POST /tasks/{taskId}/transition`
with a body of `'TaskTransition'`. Three of six real runs, on two different models, failed this
way — so it was the platform, not the model.

The rule these tests hold: a repair is never silent. Every change is reported in
`IntakeResult.repairs`, and a plan that needed nothing comes through untouched.
"""

import asyncio
import copy
import json
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.application_ir.validate import has_errors, validate_ir
from omnistackai_agent_engine.application_ir.workflow import workflows_of
from omnistackai_agent_engine.codegen.workflow_routes import transition_routes
from omnistackai_agent_engine.intake.ir_repair import repair_ir_dict, resolve_entity_reference
from omnistackai_agent_engine.intake.nl_to_ir import (
    generate_ir,
    parse_ir_response,
    parse_ir_response_with_repairs,
)
from omnistackai_agent_engine.model_gateway import FinishReason, GenerateResponse, TokenUsage


def _plan(**changes) -> dict:
    """The minimal-blog IR as a model would send it, with an Order entity added."""
    data = example_ir("minimal-blog").to_dict()
    data["entities"].append({
        "name": "Order",
        "fields": [
            {"name": "id", "type": "uuid", "primary_key": True},
            {"name": "item", "type": "string"},
            {"name": "status", "type": "string", "validation": ["enum:placed|accepted|delivered"]},
        ],
    })
    data["apis"].append({"method": "GET", "path": "/orders", "auth": True, "response_schema": "Order"})
    data.update(changes)
    return data


def _with_api(api: dict, *, status_values: bool = True) -> dict:
    data = _plan()
    if not status_values:
        data["entities"][-1]["fields"][-1]["validation"] = []
    data["apis"].append(api)
    return data


def _status_api(body, path="/orders/{orderId}/status", method="PATCH", roles=("author",)) -> dict:
    return {"method": method, "path": path, "auth": True, "request_schema": body,
            "response_schema": "Order", "required_roles": list(roles)}


class TheRealFailuresNowBuild(TestCase):
    def test_a_status_endpoint_with_an_undeclared_body_becomes_a_lifecycle(self) -> None:
        ir, repairs = parse_ir_response_with_repairs(json.dumps(_with_api(_status_api("OrderStatusUpdate"))))
        self.assertFalse(has_errors(validate_ir(ir)))
        workflows = workflows_of(ir)
        self.assertEqual([w.entity for w in workflows], ["Order"])
        self.assertEqual(workflows[0].states, ("placed", "accepted", "delivered"))
        self.assertTrue(any("replaced by a Order lifecycle" in note for note in repairs))

    def test_a_body_of_json_is_repaired_the_same_way(self) -> None:
        ir, _ = parse_ir_response_with_repairs(json.dumps(_with_api(_status_api("json"))))
        self.assertFalse(has_errors(validate_ir(ir)))

    def test_a_transition_endpoint_on_an_entity_without_states_keeps_the_endpoint_untyped(self) -> None:
        # No enum on the field: we do not invent a lifecycle nobody described.
        data = _with_api(_status_api("TaskTransition", path="/orders/{orderId}/transition", method="POST"),
                         status_values=False)
        ir, repairs = parse_ir_response_with_repairs(json.dumps(data))
        self.assertFalse(has_errors(validate_ir(ir)))
        self.assertEqual(workflows_of(ir), ())
        endpoint = next(a for a in ir.apis if a.path.endswith("/transition"))
        self.assertIsNone(endpoint.request_schema)
        self.assertTrue(any("'TaskTransition' names no entity; removed" in note for note in repairs))


class TheLifecycleIsReal(TestCase):
    def test_it_generates_role_checked_transition_endpoints(self) -> None:
        ir, _ = parse_ir_response_with_repairs(json.dumps(_with_api(_status_api("OrderStatusUpdate"))))
        routes = transition_routes(ir)
        self.assertEqual([r.path for r in routes],
                         ["/orders/{orderId}/mark_accepted", "/orders/{orderId}/mark_delivered"])
        self.assertTrue(all(r.roles == ("author",) for r in routes))

    def test_the_ad_hoc_endpoint_is_gone(self) -> None:
        ir, _ = parse_ir_response_with_repairs(json.dumps(_with_api(_status_api("OrderStatusUpdate"))))
        self.assertNotIn("/orders/{orderId}/status", [a.path for a in ir.apis])

    def test_an_existing_workflow_makes_the_endpoint_redundant(self) -> None:
        data = _with_api(_status_api("json"))
        data["capabilities"] = [{"kind": "workflow", "name": "order_flow", "config": {
            "entity": "Order", "field": "status", "states": ["placed", "delivered"], "initial": "placed",
            "transitions": [{"name": "deliver", "to": "delivered", "from": ["placed"], "roles": []}]}}]
        ir, repairs = parse_ir_response_with_repairs(json.dumps(data))
        self.assertEqual(len(workflows_of(ir)), 1, "no second lifecycle is added")
        self.assertNotIn("/orders/{orderId}/status", [a.path for a in ir.apis])
        self.assertTrue(any("already has a lifecycle" in note for note in repairs))

    def test_unknown_roles_are_not_copied_onto_transitions(self) -> None:
        ir, _ = parse_ir_response_with_repairs(json.dumps(_with_api(_status_api("json", roles=("ghost",)))))
        self.assertTrue(all(r.roles == () for r in transition_routes(ir)))


class SchemaNamesAreResolvedOrDropped(TestCase):
    ENTITIES = ["Order", "Category", "Address", "Post"]

    def test_views_of_an_entity_resolve_to_it(self) -> None:
        for reference, expected in [("OrderStatusUpdate", "Order"), ("OrdersResponse", "Order"),
                                    ("order_dto", "Order"), ("orders", "Order"), ("Categories", "Category"),
                                    ("CategoryList", "Category"), ("Addresses", "Address"), ("PostCreate", "Post")]:
            with self.subTest(reference=reference):
                self.assertEqual(resolve_entity_reference(reference, self.ENTITIES), expected)

    def test_names_that_mean_nothing_resolve_to_nothing(self) -> None:
        for reference in ("json", "StatusPayload", "TaskTransition", "Posting"):
            with self.subTest(reference=reference):
                self.assertIsNone(resolve_entity_reference(reference, self.ENTITIES))

    def test_a_resolved_name_is_reported(self) -> None:
        data = _plan()
        data["apis"].append({"method": "POST", "path": "/posts/drafts", "auth": True,
                             "request_schema": "PostCreate", "response_schema": "PostResponse"})
        ir, repairs = parse_ir_response_with_repairs(json.dumps(data))
        endpoint = next(a for a in ir.apis if a.path == "/posts/drafts")
        self.assertEqual((endpoint.request_schema, endpoint.response_schema), ("Post", "Post"))
        self.assertEqual(len(repairs), 2)


class NothingChangesWhenNothingIsWrong(TestCase):
    def test_a_clean_plan_has_no_repairs_and_is_unchanged(self) -> None:
        data = _plan()
        before = copy.deepcopy(data)
        _, notes = repair_ir_dict(data)
        self.assertEqual(notes, ())
        self.assertEqual(data, before)

    def test_parse_ir_response_still_returns_just_the_ir(self) -> None:
        ir = parse_ir_response(json.dumps(_plan()))
        self.assertEqual(ir.name, example_ir("minimal-blog").name)


class TheRepairsReachTheCaller(TestCase):
    def test_generate_ir_reports_them(self) -> None:
        text = json.dumps(_with_api(_status_api("OrderStatusUpdate")))

        class _Provider:
            provider_id = "fake"

            async def generate(self, request):
                return GenerateResponse(request.request_id, request.model, text, FinishReason.STOP,
                                        TokenUsage(1, 1), 1)

        result = asyncio.run(generate_ir("an order app", _Provider(), model_id="m"))
        self.assertTrue(result.repairs)
        self.assertEqual(len(workflows_of(result.ir)), 1)


class NormalizeIsLossless(TestCase):
    """normalize_ir rebuilt the IR field by field and left out `capabilities` and `brand`, so every
    lifecycle a model declared vanished at intake. This guards every field, including future ones."""

    def test_every_field_survives(self) -> None:
        import dataclasses

        from omnistackai_agent_engine.application_ir import ApplicationIR
        from omnistackai_agent_engine.application_ir.validate import normalize_ir

        ir, _ = parse_ir_response_with_repairs(json.dumps(_with_api(_status_api("OrderStatusUpdate"))))
        self.assertTrue(ir.capabilities, "the parsed plan must carry its lifecycle")
        normalized = normalize_ir(ir)
        for f in dataclasses.fields(ApplicationIR):
            with self.subTest(field=f.name):
                before, after = getattr(ir, f.name), getattr(normalized, f.name)
                if isinstance(before, tuple):
                    self.assertEqual(sorted(map(repr, before)), sorted(map(repr, after)))
                else:
                    self.assertEqual(before, after)

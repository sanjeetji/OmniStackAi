"""R-432: opt-in model refinement over deterministic ecosystem scope/data models.

All model behavior is represented by an in-memory provider. No real model or network is used.
"""

from __future__ import annotations

import asyncio
import json
import unittest

from omnistackai_agent_engine.application_ir import has_errors, validate_ir
from omnistackai_agent_engine.codegen.route_wiring import Op, wire_endpoint
from omnistackai_agent_engine.intake import (
    DOMAIN_ENTITIES,
    IntakeError,
    IntakeResponseError,
    ScopeRefinementResult,
    build_scope_refinement_messages,
    parse_scope_refinement_response,
    plan_ecosystem,
    plan_refined_ecosystem,
    propose_ecosystem,
    refine_ecosystem,
)
from omnistackai_agent_engine.model_gateway import (
    ChatRole,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    TokenUsage,
)


VALID_REFINEMENT = {
    "domain": "pet-care",
    "domain_confidence": 0.86,
    "business_model": "Marketplace connecting pet owners with trusted caregivers",
    "actors": [
        {"name": "Owner", "description": "Books care for a pet"},
        {"name": "Caregiver", "description": "Provides boarding and walking"},
        {"name": "Admin", "description": "Operates the marketplace"},
    ],
    "surfaces": [
        {
            "kind": "customer_web",
            "name": "Pet Owner App",
            "audience": "customer",
            "actor": "Owner",
            "description": "Manage pets and book trusted care.",
        },
        {
            "kind": "provider_portal",
            "name": "Caregiver Portal",
            "audience": "operator",
            "actor": "Caregiver",
            "description": "Manage availability and booking requests.",
        },
        {
            "kind": "admin_dashboard",
            "name": "Marketplace Admin",
            "audience": "operator",
            "actor": "Admin",
            "description": "Review caregivers, bookings, and disputes.",
        },
    ],
    "questions": ["Should caregivers require approval before accepting bookings?"],
    "entities": [
        {
            "name": "Owner",
            "fields": [
                {"name": "id", "type": "uuid", "required": True},
                {"name": "name", "type": "string", "required": True},
            ],
            "relations": [],
        },
        {
            "name": "Pet",
            "fields": [
                {"name": "id", "type": "uuid", "required": True},
                {"name": "name", "type": "string", "required": True},
                {"name": "species", "type": "string", "required": True},
            ],
            "relations": [
                {"name": "owner", "target_entity": "Owner", "kind": "many_to_one"}
            ],
        },
        {
            "name": "Booking",
            "fields": [
                {"name": "id", "type": "uuid", "required": True},
                {"name": "status", "type": "string", "required": True},
                {"name": "starts_at", "type": "datetime", "required": True},
            ],
            "relations": [
                {"name": "pet", "target_entity": "Pet", "kind": "many_to_one"}
            ],
        },
    ],
}


class StubProvider:
    def __init__(self, text: str) -> None:
        self._text = text
        self.requests: list[GenerateRequest] = []

    @property
    def provider_id(self) -> str:
        return "ollama"

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        self.requests.append(request)
        return GenerateResponse(
            request.request_id,
            request.model,
            self._text,
            FinishReason.STOP,
            TokenUsage(100, 200),
            3,
        )


def run(coro):
    return asyncio.run(coro)


class ScopeRefinementMessageTests(unittest.TestCase):
    def test_messages_embed_deterministic_first_pass_and_bounded_schema(self) -> None:
        messages = build_scope_refinement_messages("Build software for pet carers to look after animals")
        self.assertEqual([m.role for m in messages], [ChatRole.SYSTEM, ChatRole.USER])
        self.assertIn('"domain": "custom-application"', messages[0].content)
        self.assertIn("1-8 entities", messages[0].content)
        self.assertIn("uuid", messages[0].content)
        self.assertIn("Build software for pet carers to look after animals", messages[1].content)

    def test_empty_or_oversized_prompt_is_rejected_before_provider_use(self) -> None:
        with self.assertRaises(IntakeError):
            build_scope_refinement_messages("  ")
        with self.assertRaises(IntakeError):
            build_scope_refinement_messages("x" * 4001)


class ScopeRefinementParserTests(unittest.TestCase):
    def test_valid_response_builds_bounded_proposal_and_entities(self) -> None:
        result = parse_scope_refinement_response(
            json.dumps(VALID_REFINEMENT), prompt="Build a pet boarding marketplace"
        )
        self.assertIsInstance(result, ScopeRefinementResult)
        self.assertEqual(result.source, "model")
        self.assertEqual(result.proposal.domain, "pet-care")
        self.assertEqual({e.name for e in result.entities}, {"Owner", "Pet", "Booking"})
        self.assertEqual(result.proposal.options[0].id, "complete")
        self.assertTrue(result.proposal.options[0].recommended)

    def test_fenced_json_is_accepted_but_unknown_keys_fail_closed(self) -> None:
        fenced = "```json\n" + json.dumps(VALID_REFINEMENT) + "\n```"
        self.assertEqual(
            parse_scope_refinement_response(fenced, prompt="pet care").proposal.domain,
            "pet-care",
        )
        extra = dict(VALID_REFINEMENT, secret="must-not-pass")
        with self.assertRaises(IntakeResponseError):
            parse_scope_refinement_response(json.dumps(extra), prompt="pet care")

    def test_omitted_empty_relations_normalizes_to_empty_tuple(self) -> None:
        no_relations_key = json.loads(json.dumps(VALID_REFINEMENT))
        del no_relations_key["entities"][0]["relations"]
        result = parse_scope_refinement_response(json.dumps(no_relations_key), prompt="pet care")
        owner = next(entity for entity in result.entities if entity.name == "Owner")
        self.assertEqual(owner.relations, ())

    def test_every_application_ir_relation_kind_is_accepted(self) -> None:
        for kind in ("one_to_one", "one_to_many", "many_to_one", "many_to_many"):
            payload = json.loads(json.dumps(VALID_REFINEMENT))
            payload["entities"][1]["relations"][0]["kind"] = kind
            result = parse_scope_refinement_response(json.dumps(payload), prompt="pet care")
            pet = next(entity for entity in result.entities if entity.name == "Pet")
            self.assertEqual(pet.relations[0].kind.value, kind)

    def test_invalid_actor_reference_and_too_many_questions_fail_closed(self) -> None:
        bad_actor = json.loads(json.dumps(VALID_REFINEMENT))
        bad_actor["surfaces"][0]["actor"] = "Ghost"
        with self.assertRaises(IntakeResponseError):
            parse_scope_refinement_response(json.dumps(bad_actor), prompt="pet care")
        too_many = json.loads(json.dumps(VALID_REFINEMENT))
        too_many["questions"] = ["q1?", "q2?", "q3?", "q4?"]
        with self.assertRaises(IntakeResponseError):
            parse_scope_refinement_response(json.dumps(too_many), prompt="pet care")

    def test_bad_field_type_missing_uuid_id_and_relation_target_fail_closed(self) -> None:
        bad_type = json.loads(json.dumps(VALID_REFINEMENT))
        bad_type["entities"][0]["fields"][1]["type"] = "money"
        missing_id = json.loads(json.dumps(VALID_REFINEMENT))
        missing_id["entities"][0]["fields"] = missing_id["entities"][0]["fields"][1:]
        bad_target = json.loads(json.dumps(VALID_REFINEMENT))
        bad_target["entities"][1]["relations"][0]["target_entity"] = "Missing"
        for payload in (bad_type, missing_id, bad_target):
            with self.assertRaises(IntakeResponseError):
                parse_scope_refinement_response(json.dumps(payload), prompt="pet care")

    def test_credential_fields_fk_collisions_and_unknown_validation_fail_closed(self) -> None:
        credential = json.loads(json.dumps(VALID_REFINEMENT))
        credential["entities"][0]["fields"].append(
            {"name": "password", "type": "string", "required": True}
        )
        fk_collision = json.loads(json.dumps(VALID_REFINEMENT))
        fk_collision["entities"][1]["fields"].append(
            {"name": "owner_id", "type": "uuid", "required": True}
        )
        unknown_rule = json.loads(json.dumps(VALID_REFINEMENT))
        unknown_rule["entities"][0]["fields"][1]["validation"] = ["must_be_nice"]
        for payload in (credential, fk_collision, unknown_rule):
            with self.assertRaises(IntakeResponseError):
                parse_scope_refinement_response(json.dumps(payload), prompt="pet care")

    def test_malformed_json_and_oversized_collections_fail_closed(self) -> None:
        with self.assertRaises(IntakeResponseError):
            parse_scope_refinement_response("not json", prompt="pet care")
        oversized = json.loads(json.dumps(VALID_REFINEMENT))
        oversized["actors"] = oversized["actors"] * 3
        with self.assertRaises(IntakeResponseError):
            parse_scope_refinement_response(json.dumps(oversized), prompt="pet care")


class ScopeRefinementFlowTests(unittest.TestCase):
    def test_unknown_domain_calls_provider_once_and_plans_valid_tailored_apps(self) -> None:
        provider = StubProvider(json.dumps(VALID_REFINEMENT))
        result = run(
            refine_ecosystem(
                "Build a pet boarding service connecting owners with trusted caregivers",
                provider,
                model_id="qwen2.5-coder:14b",
            )
        )
        self.assertEqual(result.source, "model")
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(provider.requests[0].model.provider_id, "ollama")
        plan = plan_refined_ecosystem(result)
        self.assertEqual(plan.domain, "pet-care")
        self.assertEqual(len(plan.apps), 3)
        for app in plan.apps:
            self.assertFalse(has_errors(validate_ir(app.ir)))
            self.assertEqual({e.name for e in app.ir.entities}, {"Owner", "Pet", "Booking"})

    def test_known_domain_bypasses_provider_and_preserves_curated_model(self) -> None:
        provider = StubProvider("this must never be read")
        prompt = "Create a food delivery app with restaurants and couriers"
        result = run(
            refine_ecosystem(
                prompt,
                provider,
                model_id="qwen2.5-coder:14b",
            )
        )
        self.assertEqual(result.source, "curated")
        self.assertEqual(provider.requests, [])
        self.assertEqual(result.entities, DOMAIN_ENTITIES["food-delivery"])
        self.assertEqual(
            plan_refined_ecosystem(result).to_dict(),
            plan_ecosystem(propose_ecosystem(prompt)).to_dict(),
        )

    def test_refined_crud_endpoints_still_wire_to_repositories(self) -> None:
        result = parse_scope_refinement_response(
            json.dumps(VALID_REFINEMENT), prompt="Build a pet boarding marketplace"
        )
        ir = plan_refined_ecosystem(result).apps[0].ir
        repo_entities = frozenset(e.name for e in ir.entities)
        fk_by_entity = {e.name: tuple(r.name for r in e.relations) for e in ir.entities}
        ops = {
            wiring.op
            for api in ir.apis
            if (wiring := wire_endpoint(api, repo_entities, fk_by_entity)) is not None
        }
        for expected in (Op.LIST, Op.GET, Op.CREATE, Op.UPDATE, Op.DELETE, Op.LIST_BY):
            self.assertIn(expected, ops)

    def test_public_api_is_exported(self) -> None:
        import omnistackai_agent_engine.intake as intake

        for name in (
            "ScopeRefinementResult",
            "build_scope_refinement_messages",
            "parse_scope_refinement_response",
            "refine_ecosystem",
            "plan_refined_ecosystem",
        ):
            self.assertIn(name, intake.__all__)
            self.assertTrue(hasattr(intake, name))


if __name__ == "__main__":
    unittest.main()

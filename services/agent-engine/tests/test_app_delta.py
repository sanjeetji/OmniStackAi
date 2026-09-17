"""R-468: generic follow-up delta proposal + merge (intake/app_delta.py).

Stub providers, 0 real model calls. Mirrors solution_packs/ai_delta.py's shape without pack coupling.
"""

from __future__ import annotations

import asyncio
import json
import unittest
from types import SimpleNamespace

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.intake.app_delta import (
    AppDeltaError,
    AppDeltaProposal,
    apply_app_delta,
    build_app_delta_messages,
    generate_app_delta_proposal,
    parse_app_delta_proposal,
)
from omnistackai_agent_engine.model_gateway import ChatRole

_VALID_DELTA = json.dumps({
    "entities": [
        {
            "name": "Favorite",
            "fields": [
                {"name": "id", "type": "uuid", "required": True},
                {"name": "post_id", "type": "uuid", "required": True},
            ],
            "relations": [{"name": "post", "target_entity": "Post", "kind": "many_to_one"}],
        }
    ],
    "apis": [{"method": "POST", "path": "/favorites", "auth": True}],
    "screens": [{"id": "favorites_list", "role": "reader"}],
    "rationale": "Adds a favorites feature.",
})


class SequenceStubProvider:
    provider_id = "stub"

    def __init__(self, responses: list, *, fail: Exception | None = None) -> None:
        self._responses = list(responses)
        self._fail = fail
        self.requests: list = []

    async def generate(self, request):  # noqa: ANN001
        self.requests.append(request)
        if self._fail is not None:
            raise self._fail
        return SimpleNamespace(text=self._responses.pop(0))


class AppDeltaProposalTests(unittest.TestCase):
    def test_defaults_are_empty_and_valid(self) -> None:
        proposal = AppDeltaProposal()
        self.assertEqual(proposal.entities, ())
        self.assertEqual(proposal.to_dict(), {"entities": [], "apis": [], "screens": [], "rationale": ""})

    def test_rejects_duplicate_entity_names_within_the_proposal(self) -> None:
        ir = example_ir("minimal-blog")
        with self.assertRaises(AppDeltaError):
            AppDeltaProposal(entities=(ir.entities[0], ir.entities[0]))

    def test_rejects_too_many_entities(self) -> None:
        from omnistackai_agent_engine.application_ir import Entity, Field, FieldType

        many = tuple(
            Entity(name=f"E{i}", fields=(Field(name="id", type=FieldType.UUID, required=True),)) for i in range(9)
        )
        with self.assertRaises(AppDeltaError):
            AppDeltaProposal(entities=many)

    def test_rejects_control_characters_in_rationale(self) -> None:
        with self.assertRaises(AppDeltaError):
            AppDeltaProposal(rationale="bad\x00text")


class BuildMessagesTests(unittest.TestCase):
    def test_lists_existing_state_and_forbids_restating_it(self) -> None:
        ir = example_ir("minimal-blog")
        system, user = build_app_delta_messages(ir, "add a favorites feature")
        self.assertEqual(system.role, ChatRole.SYSTEM)
        self.assertEqual(user.role, ChatRole.USER)
        self.assertIn("MUST NOT collide", system.content)
        for entity in ir.entities:
            self.assertIn(entity.name, user.content)
        self.assertIn("add a favorites feature", user.content)

    def test_empty_prompt_is_rejected(self) -> None:
        ir = example_ir("minimal-blog")
        with self.assertRaises(AppDeltaError):
            build_app_delta_messages(ir, "   ")


class ParseProposalTests(unittest.TestCase):
    def test_parses_a_valid_delta(self) -> None:
        ir = example_ir("minimal-blog")
        proposal = parse_app_delta_proposal(_VALID_DELTA, base_ir=ir)
        self.assertEqual(proposal.entities[0].name, "Favorite")
        self.assertEqual(proposal.apis[0].path, "/favorites")
        self.assertEqual(proposal.screens[0].id, "favorites_list")

    def test_markdown_fenced_json_is_accepted(self) -> None:
        ir = example_ir("minimal-blog")
        fenced = f"```json\n{_VALID_DELTA}\n```"
        proposal = parse_app_delta_proposal(fenced, base_ir=ir)
        self.assertEqual(proposal.entities[0].name, "Favorite")

    def test_colliding_entity_name_is_rejected_at_parse_time(self) -> None:
        ir = example_ir("minimal-blog")
        colliding = json.dumps({
            "entities": [{"name": ir.entities[0].name, "fields": [{"name": "id", "type": "uuid", "required": True}]}],
            "apis": [], "screens": [], "rationale": "",
        })
        with self.assertRaises(AppDeltaError):
            parse_app_delta_proposal(colliding, base_ir=ir)

    def test_colliding_api_and_screen_are_rejected(self) -> None:
        ir = example_ir("minimal-blog")
        api = ir.apis[0]
        colliding_api = json.dumps({
            "entities": [], "screens": [], "rationale": "",
            "apis": [{"method": api.method.value, "path": api.path, "auth": True}],
        })
        with self.assertRaises(AppDeltaError):
            parse_app_delta_proposal(colliding_api, base_ir=ir)
        screen = ir.screens[0]
        colliding_screen = json.dumps({
            "entities": [], "apis": [], "rationale": "",
            "screens": [{"id": screen.id, "role": "reader"}],
        })
        with self.assertRaises(AppDeltaError):
            parse_app_delta_proposal(colliding_screen, base_ir=ir)

    def test_screen_role_must_be_an_existing_role(self) -> None:
        ir = example_ir("minimal-blog")
        self.assertEqual({r.id for r in ir.roles}, {"author", "reader"})
        bad_role = json.dumps({
            "entities": [], "apis": [], "rationale": "",
            "screens": [{"id": "moderation_queue", "role": "moderator"}],
        })
        with self.assertRaises(AppDeltaError):
            parse_app_delta_proposal(bad_role, base_ir=ir)

    def test_screen_with_an_existing_role_is_accepted(self) -> None:
        ir = example_ir("minimal-blog")
        ok = json.dumps({
            "entities": [], "apis": [], "rationale": "",
            "screens": [{"id": "favorites_list", "role": "reader"}],
        })
        proposal = parse_app_delta_proposal(ok, base_ir=ir)
        self.assertEqual(proposal.screens[0].role, "reader")

    def test_missing_id_field_is_rejected(self) -> None:
        ir = example_ir("minimal-blog")
        no_id = json.dumps({
            "entities": [{"name": "Favorite", "fields": [{"name": "note", "type": "string", "required": True}]}],
            "apis": [], "screens": [], "rationale": "",
        })
        with self.assertRaises(AppDeltaError):
            parse_app_delta_proposal(no_id, base_ir=ir)

    def test_credential_field_name_is_rejected(self) -> None:
        ir = example_ir("minimal-blog")
        bad = json.dumps({
            "entities": [{"name": "Favorite", "fields": [
                {"name": "id", "type": "uuid", "required": True},
                {"name": "api_key", "type": "string", "required": True},
            ]}],
            "apis": [], "screens": [], "rationale": "",
        })
        with self.assertRaises(AppDeltaError):
            parse_app_delta_proposal(bad, base_ir=ir)

    def test_unknown_top_level_key_is_rejected(self) -> None:
        ir = example_ir("minimal-blog")
        bad = json.dumps({"entities": [], "apis": [], "screens": [], "rationale": "", "pack_id": "x"})
        with self.assertRaises(AppDeltaError):
            parse_app_delta_proposal(bad, base_ir=ir)

    def test_not_json_is_rejected(self) -> None:
        ir = example_ir("minimal-blog")
        with self.assertRaises(AppDeltaError):
            parse_app_delta_proposal("not json at all", base_ir=ir)

    def test_empty_response_is_rejected(self) -> None:
        ir = example_ir("minimal-blog")
        with self.assertRaises(AppDeltaError):
            parse_app_delta_proposal("   ", base_ir=ir)


class ApplyDeltaTests(unittest.TestCase):
    def test_merges_entities_apis_screens(self) -> None:
        ir = example_ir("minimal-blog")
        proposal = parse_app_delta_proposal(_VALID_DELTA, base_ir=ir)
        merged = apply_app_delta(ir, proposal)
        self.assertEqual(len(merged.entities), len(ir.entities) + 1)
        self.assertIn("Favorite", [e.name for e in merged.entities])
        self.assertEqual(len(merged.apis), len(ir.apis) + 1)
        self.assertEqual(len(merged.screens), len(ir.screens) + 1)
        # Original IR is untouched.
        self.assertEqual(len(ir.entities), len(ir.entities))
        self.assertNotIn("Favorite", [e.name for e in ir.entities])

    def test_relation_may_target_a_new_entity_in_the_same_proposal(self) -> None:
        from omnistackai_agent_engine.application_ir import Entity, Field, FieldType, Relation, RelationKind

        ir = example_ir("minimal-blog")
        a = Entity(name="Alpha", fields=(Field(name="id", type=FieldType.UUID, required=True),))
        b = Entity(
            name="Beta",
            fields=(Field(name="id", type=FieldType.UUID, required=True),),
            relations=(Relation(name="alpha", target_entity="Alpha", kind=RelationKind.MANY_TO_ONE),),
        )
        proposal = AppDeltaProposal(entities=(a, b))
        merged = apply_app_delta(ir, proposal)
        self.assertIn("Alpha", [e.name for e in merged.entities])
        self.assertIn("Beta", [e.name for e in merged.entities])

    def test_relation_targeting_an_undeclared_entity_is_rejected(self) -> None:
        from omnistackai_agent_engine.application_ir import Entity, Field, FieldType, Relation, RelationKind

        ir = example_ir("minimal-blog")
        orphan = Entity(
            name="Orphan",
            fields=(Field(name="id", type=FieldType.UUID, required=True),),
            relations=(Relation(name="ghost", target_entity="DoesNotExist", kind=RelationKind.MANY_TO_ONE),),
        )
        with self.assertRaises(AppDeltaError):
            apply_app_delta(ir, AppDeltaProposal(entities=(orphan,)))

    def test_defense_in_depth_role_check_at_merge_time(self) -> None:
        from omnistackai_agent_engine.application_ir import Screen

        ir = example_ir("minimal-blog")
        bad = AppDeltaProposal(screens=(Screen(id="mod_queue", role="moderator"),))
        with self.assertRaises(AppDeltaError):
            apply_app_delta(ir, bad)

    def test_defense_in_depth_collision_check_at_merge_time(self) -> None:
        # A hand-built proposal bypassing parse_app_delta_proposal must still be rejected at merge time.
        ir = example_ir("minimal-blog")
        colliding = AppDeltaProposal(entities=(ir.entities[0],))
        with self.assertRaises(AppDeltaError):
            apply_app_delta(ir, colliding)

    def test_wrong_argument_types_are_rejected(self) -> None:
        ir = example_ir("minimal-blog")
        with self.assertRaises(AppDeltaError):
            apply_app_delta(ir, "not a proposal")
        with self.assertRaises(AppDeltaError):
            apply_app_delta("not an ir", AppDeltaProposal())

    def test_empty_delta_is_a_valid_no_op_merge(self) -> None:
        ir = example_ir("minimal-blog")
        merged = apply_app_delta(ir, AppDeltaProposal())
        self.assertEqual(merged.entities, ir.entities)
        self.assertEqual(merged.apis, ir.apis)
        self.assertEqual(merged.screens, ir.screens)


class GenerateProposalTests(unittest.TestCase):
    def test_succeeds_on_first_attempt(self) -> None:
        ir = example_ir("minimal-blog")
        provider = SequenceStubProvider([_VALID_DELTA])
        proposal = asyncio.run(generate_app_delta_proposal(ir, "add favorites", provider, model_id="m"))
        self.assertEqual(proposal.entities[0].name, "Favorite")
        self.assertEqual(len(provider.requests), 1)

    def test_retries_on_validation_rejection_with_the_reason_fed_back(self) -> None:
        ir = example_ir("minimal-blog")
        bad = json.dumps({"entities": [], "apis": [], "screens": [], "rationale": "", "extra": 1})
        provider = SequenceStubProvider([bad, _VALID_DELTA])
        proposal = asyncio.run(
            generate_app_delta_proposal(ir, "add favorites", provider, model_id="m", max_attempts=3)
        )
        self.assertEqual(proposal.entities[0].name, "Favorite")
        self.assertEqual(len(provider.requests), 2)
        second = provider.requests[1].messages
        self.assertEqual([m.role for m in second], [ChatRole.SYSTEM, ChatRole.USER, ChatRole.ASSISTANT, ChatRole.USER])
        self.assertIn("REJECTED", second[-1].content)

    def test_exhaustion_raises_the_last_reason(self) -> None:
        ir = example_ir("minimal-blog")
        provider = SequenceStubProvider(["not json", "still not json", "nope"])
        with self.assertRaises(AppDeltaError):
            asyncio.run(generate_app_delta_proposal(ir, "add favorites", provider, model_id="m", max_attempts=3))
        self.assertEqual(len(provider.requests), 3)

    def test_provider_exception_is_never_retried(self) -> None:
        ir = example_ir("minimal-blog")
        provider = SequenceStubProvider([], fail=RuntimeError("boom"))
        with self.assertRaises(RuntimeError):
            asyncio.run(generate_app_delta_proposal(ir, "add favorites", provider, model_id="m", max_attempts=3))
        self.assertEqual(len(provider.requests), 1)


if __name__ == "__main__":
    unittest.main()

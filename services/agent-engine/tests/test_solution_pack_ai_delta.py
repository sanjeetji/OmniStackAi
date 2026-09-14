"""R-438: Bounded Typed Solution Pack AI-Delta Proposal Schema & Local ModelProvider Boundary."""

from __future__ import annotations

import json
from asyncio import run
from dataclasses import FrozenInstanceError
from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    ApiEndpoint,
    ApplicationIR,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    Relation,
    RelationKind,
    Screen,
)
from omnistackai_agent_engine.model_gateway import (
    ChatRole,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    Message,
    ModelProvider,
    ModelRef,
    TokenUsage,
)
from omnistackai_agent_engine.solution_packs import (
    DEFAULT_SOLUTION_PACK_REGISTRY,
    MINIMAL_BLOG_PACK,
    ChangeArea,
    ChangeOperation,
    ChangeSource,
    SolutionPackChange,
    SolutionPackError,
    create_solution_pack_manifest,
)
from omnistackai_agent_engine.solution_packs.ai_delta import (
    AIDeltaProposal,
    build_ai_delta_messages,
    generate_ai_delta_proposal,
    parse_ai_delta_proposal,
)


class MockModelProvider:
    provider_id = "test-provider"

    def __init__(self, response_text: str = "") -> None:
        self.response_text = response_text
        self.requests: list[GenerateRequest] = []

    def model_ref(self) -> ModelRef:
        return ModelRef("test-provider", "test-model")

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        self.requests.append(request)
        return GenerateResponse(
            request_id=request.request_id,
            model=request.model,
            text=self.response_text,
            finish_reason=FinishReason.STOP,
            usage=TokenUsage(input_tokens=10, output_tokens=20),
            latency_ms=5,
        )


def _blog_recommendation():
    return DEFAULT_SOLUTION_PACK_REGISTRY.recommend(
        "blog-cms",
        required_targets=("nextjs-web", "backend-python"),
    )


def _base_blog_ir() -> ApplicationIR:
    return DEFAULT_SOLUTION_PACK_REGISTRY.load_ir("minimal-blog")


def _sample_ai_delta_manifest():
    rec = _blog_recommendation()
    return create_solution_pack_manifest(
        rec,
        changes=(
            SolutionPackChange(
                change_id="ai-tags",
                source=ChangeSource.AI_DELTA,
                operation=ChangeOperation.ADD,
                area=ChangeArea.DATA_MODEL,
                target="entity:Tag",
                summary="Add tags entity for post categorization",
                acceptance_criteria=("Tags can be created and linked to posts",),
            ),
        ),
    )


def _no_delta_manifest():
    rec = _blog_recommendation()
    return create_solution_pack_manifest(
        rec,
        changes=(
            SolutionPackChange(
                change_id="cfg-name",
                source=ChangeSource.CONFIGURATION,
                operation=ChangeOperation.UPDATE,
                area=ChangeArea.PROJECT,
                target="project:name",
                desired_text="Custom Blog",
                summary="Rename blog",
                acceptance_criteria=("Name updated",),
            ),
        ),
    )


class TestSolutionPackAIDelta(TestCase):
    def test_proposal_frozen_and_attributes(self) -> None:
        base_ir = _base_blog_ir()
        tag_entity = Entity(
            name="Tag",
            fields=(
                Field(name="id", type=FieldType.UUID, required=True),
                Field(name="name", type=FieldType.STRING, required=True),
            ),
        )
        proposal = AIDeltaProposal(
            pack_id="minimal-blog",
            pack_version="1.0.0",
            base_ir_sha256=MINIMAL_BLOG_PACK.ir_sha256,
            addressed_change_ids=("ai-tags",),
            entities=(tag_entity,),
            apis=(
                ApiEndpoint(
                    method=HttpMethod.GET,
                    path="/tags",
                    auth=False,
                ),
            ),
            screens=(
                Screen(
                    id="tag_list",
                    role="admin",
                ),
            ),
            capabilities=("tagging",),
            rationale="Adds taxonomy tagging support.",
        )
        self.assertEqual(proposal.pack_id, "minimal-blog")
        self.assertEqual(proposal.entities[0].name, "Tag")
        self.assertEqual(proposal.capabilities, ("tagging",))
        with self.assertRaises(FrozenInstanceError):
            proposal.rationale = "mutate"  # type: ignore

        d = proposal.to_dict()
        self.assertEqual(d["pack_id"], "minimal-blog")
        self.assertEqual(d["addressed_change_ids"], ["ai-tags"])
        self.assertEqual(len(d["entities"]), 1)
        self.assertEqual(d["entities"][0]["name"], "Tag")

        j = proposal.to_json()
        self.assertIn('"pack_id":"minimal-blog"', j)

    def test_no_delta_manifest_makes_zero_provider_calls(self) -> None:
        manifest = _no_delta_manifest()
        base_ir = _base_blog_ir()
        provider = MockModelProvider('{"should":"never_be_called"}')

        proposal = run(generate_ai_delta_proposal(manifest, base_ir, provider))
        self.assertEqual(len(provider.requests), 0)
        self.assertEqual(proposal.pack_id, "minimal-blog")
        self.assertEqual(proposal.addressed_change_ids, ())
        self.assertEqual(proposal.entities, ())
        self.assertEqual(proposal.apis, ())
        self.assertEqual(proposal.screens, ())
        self.assertEqual(proposal.capabilities, ())

    def test_build_messages_structure(self) -> None:
        manifest = _sample_ai_delta_manifest()
        base_ir = _base_blog_ir()
        messages = build_ai_delta_messages(manifest, base_ir)
        self.assertGreaterEqual(len(messages), 2)
        system_msg = messages[0]
        user_msg = messages[1]
        self.assertEqual(system_msg.role, ChatRole.SYSTEM)
        self.assertEqual(user_msg.role, ChatRole.USER)
        self.assertIn("ai-tags", user_msg.content)
        self.assertIn("minimal-blog", user_msg.content)
        self.assertIn("Post", user_msg.content)

    def test_parse_valid_proposal_json(self) -> None:
        manifest = _sample_ai_delta_manifest()
        base_ir = _base_blog_ir()
        valid_json = json.dumps({
            "addressed_change_ids": ["ai-tags"],
            "entities": [
                {
                    "name": "Tag",
                    "fields": [
                        {"name": "id", "type": "uuid", "required": True},
                        {"name": "label", "type": "string", "required": True},
                    ],
                    "relations": [],
                }
            ],
            "apis": [
                {
                    "method": "GET",
                    "path": "/tags",
                    "auth": False,
                }
            ],
            "screens": [
                {
                    "id": "tag_overview",
                    "role": "public",
                }
            ],
            "capabilities": ["tagging"],
            "rationale": "Add tags entity and endpoints.",
        })
        proposal = parse_ai_delta_proposal(valid_json, manifest=manifest, base_ir=base_ir)
        self.assertEqual(proposal.addressed_change_ids, ("ai-tags",))
        self.assertEqual(len(proposal.entities), 1)
        self.assertEqual(proposal.entities[0].name, "Tag")
        self.assertEqual(proposal.capabilities, ("tagging",))

    def test_parse_rejects_credential_fields(self) -> None:
        manifest = _sample_ai_delta_manifest()
        base_ir = _base_blog_ir()
        for bad_field in ("password", "secret", "token", "api_key", "jwt"):
            bad_json = json.dumps({
                "addressed_change_ids": ["ai-tags"],
                "entities": [
                    {
                        "name": "ApiKey",
                        "fields": [
                            {"name": "id", "type": "uuid", "required": True},
                            {"name": bad_field, "type": "string", "required": True},
                        ],
                    }
                ],
            })
            with self.assertRaises(SolutionPackError) as cm:
                parse_ai_delta_proposal(bad_json, manifest=manifest, base_ir=base_ir)
            self.assertIn("credential", str(cm.exception).lower())

    def test_parse_rejects_unknown_keys(self) -> None:
        manifest = _sample_ai_delta_manifest()
        base_ir = _base_blog_ir()
        bad_json = json.dumps({
            "addressed_change_ids": ["ai-tags"],
            "entities": [],
            "unknown_extra_field": "disallowed",
        })
        with self.assertRaises(SolutionPackError):
            parse_ai_delta_proposal(bad_json, manifest=manifest, base_ir=base_ir)

    def test_parse_rejects_unregistered_change_ids(self) -> None:
        manifest = _sample_ai_delta_manifest()
        base_ir = _base_blog_ir()
        bad_json = json.dumps({
            "addressed_change_ids": ["non-existent-change"],
            "entities": [],
        })
        with self.assertRaises(SolutionPackError):
            parse_ai_delta_proposal(bad_json, manifest=manifest, base_ir=base_ir)

    def test_parse_rejects_entity_name_collision_with_base_ir(self) -> None:
        manifest = _sample_ai_delta_manifest()
        base_ir = _base_blog_ir()  # Already has "Post" and "Comment"
        bad_json = json.dumps({
            "addressed_change_ids": ["ai-tags"],
            "entities": [
                {
                    "name": "Post",
                    "fields": [
                        {"name": "id", "type": "uuid", "required": True},
                    ],
                }
            ],
        })
        with self.assertRaises(SolutionPackError) as cm:
            parse_ai_delta_proposal(bad_json, manifest=manifest, base_ir=base_ir)
        self.assertIn("already exists", str(cm.exception).lower())

    def test_generate_ai_delta_proposal_with_mock_provider(self) -> None:
        manifest = _sample_ai_delta_manifest()
        base_ir = _base_blog_ir()
        response_text = json.dumps({
            "addressed_change_ids": ["ai-tags"],
            "entities": [
                {
                    "name": "Tag",
                    "fields": [
                        {"name": "id", "type": "uuid", "required": True},
                        {"name": "name", "type": "string", "required": True},
                    ],
                    "relations": [],
                }
            ],
            "apis": [
                {"method": "GET", "path": "/tags", "auth": False},
            ],
            "screens": [
                {"id": "tags", "role": "admin"},
            ],
            "capabilities": ["tag-categorization"],
            "rationale": "Add tags.",
        })
        provider = MockModelProvider(response_text)
        proposal = run(generate_ai_delta_proposal(manifest, base_ir, provider))
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(proposal.pack_id, "minimal-blog")
        self.assertEqual(proposal.entities[0].name, "Tag")
        self.assertEqual(proposal.capabilities, ("tag-categorization",))

    def test_build_messages_fails_on_no_delta_manifest(self) -> None:
        manifest = _no_delta_manifest()
        base_ir = _base_blog_ir()
        with self.assertRaises(SolutionPackError) as cm:
            build_ai_delta_messages(manifest, base_ir)
        self.assertIn("does not contain any pending ai-delta", str(cm.exception).lower())

    def test_parse_rejects_missing_id_field_in_entity(self) -> None:
        manifest = _sample_ai_delta_manifest()
        base_ir = _base_blog_ir()
        bad_json = json.dumps({
            "addressed_change_ids": ["ai-tags"],
            "entities": [
                {
                    "name": "Tag",
                    "fields": [
                        {"name": "name", "type": "string", "required": True},
                    ],
                }
            ],
        })
        with self.assertRaises(SolutionPackError) as cm:
            parse_ai_delta_proposal(bad_json, manifest=manifest, base_ir=base_ir)
        self.assertIn("required uuid id field", str(cm.exception).lower())

    def test_parse_rejects_non_uuid_id_field(self) -> None:
        manifest = _sample_ai_delta_manifest()
        base_ir = _base_blog_ir()
        bad_json = json.dumps({
            "addressed_change_ids": ["ai-tags"],
            "entities": [
                {
                    "name": "Tag",
                    "fields": [
                        {"name": "id", "type": "string", "required": True},
                    ],
                }
            ],
        })
        with self.assertRaises(SolutionPackError) as cm:
            parse_ai_delta_proposal(bad_json, manifest=manifest, base_ir=base_ir)
        self.assertIn("required uuid", str(cm.exception).lower())

    def test_parse_rejects_screen_and_api_collisions_with_base_ir(self) -> None:
        manifest = _sample_ai_delta_manifest()
        base_ir = _base_blog_ir()
        # base_ir has /posts endpoint and post_list screen
        bad_json_api = json.dumps({
            "addressed_change_ids": ["ai-tags"],
            "apis": [{"method": "GET", "path": "/posts", "auth": True}],
        })
        with self.assertRaises(SolutionPackError) as cm:
            parse_ai_delta_proposal(bad_json_api, manifest=manifest, base_ir=base_ir)
        self.assertIn("already exists in base ir", str(cm.exception).lower())

        bad_json_screen = json.dumps({
            "addressed_change_ids": ["ai-tags"],
            "screens": [{"id": "post_list", "role": "reader"}],
        })
        with self.assertRaises(SolutionPackError) as cm:
            parse_ai_delta_proposal(bad_json_screen, manifest=manifest, base_ir=base_ir)
        self.assertIn("already exists in base ir", str(cm.exception).lower())

    def test_parse_rejects_long_rationale_and_control_chars(self) -> None:
        manifest = _sample_ai_delta_manifest()
        base_ir = _base_blog_ir()
        bad_json_len = json.dumps({
            "addressed_change_ids": ["ai-tags"],
            "rationale": "x" * 501,
        })
        with self.assertRaises(SolutionPackError) as cm:
            parse_ai_delta_proposal(bad_json_len, manifest=manifest, base_ir=base_ir)
        self.assertIn("cannot exceed 500", str(cm.exception).lower())

        bad_json_ctrl = json.dumps({
            "addressed_change_ids": ["ai-tags"],
            "rationale": "bad\x00char",
        })
        with self.assertRaises(SolutionPackError) as cm:
            parse_ai_delta_proposal(bad_json_ctrl, manifest=manifest, base_ir=base_ir)
        self.assertIn("control characters", str(cm.exception).lower())

    def test_exports_in_solution_packs_package(self) -> None:
        import omnistackai_agent_engine.solution_packs as sp

        for name in (
            "AIDeltaProposal",
            "build_ai_delta_messages",
            "generate_ai_delta_proposal",
            "parse_ai_delta_proposal",
        ):
            self.assertIn(name, sp.__all__)
            self.assertTrue(hasattr(sp, name))


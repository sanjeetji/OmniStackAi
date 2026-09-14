"""R-437: deterministic Solution Pack configuration application."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
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
    validate_ir,
)
from omnistackai_agent_engine.application_ir.validate import has_errors
from omnistackai_agent_engine.solution_packs import (
    BASELINE_SOLUTION_PACKS,
    DEFAULT_SOLUTION_PACK_REGISTRY,
    LEGACY_MANIFEST_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    MINIMAL_BLOG_PACK,
    AIDeltaProposal,
    ChangeArea,
    ChangeOperation,
    ChangeSource,
    SolutionPackApplicationResult,
    SolutionPackChange,
    SolutionPackError,
    SolutionPackRegistry,
    apply_solution_pack_manifest,
    canonical_ir_digest,
    create_solution_pack_manifest,
    parse_solution_pack_manifest,
)


def _recommendation():
    return DEFAULT_SOLUTION_PACK_REGISTRY.recommend(
        "blog-cms",
        required_targets=("nextjs-web", "backend-python"),
    )


def _project_change(
    change_id: str,
    target: str,
    desired_text: str | None,
) -> SolutionPackChange:
    return SolutionPackChange(
        change_id=change_id,
        source=ChangeSource.CONFIGURATION,
        operation=ChangeOperation.UPDATE,
        area=ChangeArea.PROJECT,
        target=target,
        desired_text=desired_text,
        summary=f"Update {target} from accepted configuration.",
        acceptance_criteria=(f"{target} matches the accepted value.",),
    )


def _ai_delta() -> SolutionPackChange:
    return SolutionPackChange(
        change_id="add-editorial-flow",
        source=ChangeSource.AI_DELTA,
        operation=ChangeOperation.ADD,
        area=ChangeArea.SCREEN,
        target="screen:EditorialWorkflow",
        desired_text=None,
        summary="Add a differentiated editorial approval flow.",
        acceptance_criteria=("Editors can request approval.",),
    )


def _manifest(*changes: SolutionPackChange):
    return create_solution_pack_manifest(_recommendation(), changes=changes)


class DeterministicApplicationTests(TestCase):
    def test_project_metadata_is_applied_to_a_fresh_valid_ir_with_provenance(self) -> None:
        before = DEFAULT_SOLUTION_PACK_REGISTRY.load_ir("minimal-blog", "1.0.0")
        manifest = _manifest(
            _project_change("rename-product", "project:name", "Northstar Editorial"),
            _project_change(
                "update-description",
                "project:description",
                "A verified publishing workspace for editors and readers.",
            ),
            _ai_delta(),
        )

        result = apply_solution_pack_manifest(manifest)

        self.assertIsInstance(result, SolutionPackApplicationResult)
        self.assertEqual(result.ir.name, "Northstar Editorial")
        self.assertEqual(
            result.ir.description,
            "A verified publishing workspace for editors and readers.",
        )
        self.assertFalse(has_errors(validate_ir(result.ir)))
        self.assertEqual(result.base_ir_sha256, MINIMAL_BLOG_PACK.ir_sha256)
        self.assertNotEqual(result.derived_ir_sha256, result.base_ir_sha256)
        self.assertEqual(
            result.applied_configuration_change_ids,
            ("rename-product", "update-description"),
        )
        self.assertEqual(
            result.unapplied_ai_delta_change_ids,
            ("add-editorial-flow",),
        )
        self.assertEqual(before.name, "Minimal Blog")
        self.assertEqual(
            canonical_ir_digest(DEFAULT_SOLUTION_PACK_REGISTRY.load_ir("minimal-blog")),
            MINIMAL_BLOG_PACK.ir_sha256,
        )

    def test_application_is_repeatable_frozen_and_canonical_json_safe(self) -> None:
        manifest = _manifest(
            _project_change("rename-product", "project:name", "Northstar Editorial"),
            _ai_delta(),
        )
        first = apply_solution_pack_manifest(manifest)
        second = apply_solution_pack_manifest(manifest)
        self.assertEqual(first, second)
        self.assertIsNot(first.ir, second.ir)
        self.assertEqual(
            first.to_json(),
            json.dumps(
                first.to_dict(),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.to_dict()["derived_ir"]["name"], "Northstar Editorial")
        with self.assertRaises(FrozenInstanceError):
            first.derived_ir_sha256 = "0" * 64  # type: ignore[misc]

    def test_empty_and_ai_only_manifests_preserve_the_base_digest(self) -> None:
        empty = apply_solution_pack_manifest(_manifest())
        ai_only = apply_solution_pack_manifest(_manifest(_ai_delta()))
        self.assertEqual(empty.derived_ir_sha256, MINIMAL_BLOG_PACK.ir_sha256)
        self.assertEqual(empty.applied_configuration_change_ids, ())
        self.assertEqual(empty.unapplied_ai_delta_change_ids, ())
        self.assertEqual(ai_only.derived_ir_sha256, MINIMAL_BLOG_PACK.ir_sha256)
        self.assertEqual(
            ai_only.unapplied_ai_delta_change_ids,
            ("add-editorial-flow",),
        )


class FailClosedApplicationTests(TestCase):
    def test_applicable_configuration_requires_explicit_bounded_text(self) -> None:
        for target, value in (
            ("project:name", None),
            ("project:name", " "),
            ("project:name", "x" * 129),
            ("project:description", "x" * 4001),
            ("project:description", "unsafe\x00text"),
        ):
            with self.subTest(target=target, value=value), self.assertRaises(
                SolutionPackError
            ):
                _project_change("invalid-value", target, value)

    def test_desired_text_is_forbidden_outside_allowlisted_project_updates(self) -> None:
        cases = (
            {
                "source": ChangeSource.AI_DELTA,
                "area": ChangeArea.SCREEN,
                "operation": ChangeOperation.ADD,
                "target": "screen:Editor",
            },
            {
                "source": ChangeSource.CONFIGURATION,
                "area": ChangeArea.DATA_MODEL,
                "operation": ChangeOperation.UPDATE,
                "target": "entity:Post",
            },
            {
                "source": ChangeSource.CONFIGURATION,
                "area": ChangeArea.PROJECT,
                "operation": ChangeOperation.ADD,
                "target": "project:name",
            },
        )
        for values in cases:
            with self.subTest(values=values), self.assertRaisesRegex(
                SolutionPackError, "desired_text"
            ):
                SolutionPackChange(
                    change_id="invalid-desired-text",
                    desired_text="Not allowed here",
                    summary="Invalid desired text placement.",
                    acceptance_criteria=("This must fail.",),
                    **values,
                )

    def test_unsupported_configuration_intent_fails_without_partial_result(self) -> None:
        unsupported = SolutionPackChange(
            change_id="update-post",
            source=ChangeSource.CONFIGURATION,
            operation=ChangeOperation.UPDATE,
            area=ChangeArea.DATA_MODEL,
            target="entity:Post",
            desired_text=None,
            summary="Change the post model.",
            acceptance_criteria=("The model reflects accepted requirements.",),
        )
        manifest = _manifest(
            _project_change("rename-product", "project:name", "Would Be Partial"),
            unsupported,
        )
        with self.assertRaisesRegex(SolutionPackError, "unsupported"):
            apply_solution_pack_manifest(manifest)

    def test_duplicate_configuration_target_is_rejected(self) -> None:
        manifest = _manifest(
            _project_change("name-one", "project:name", "First Name"),
            _project_change("name-two", "project:name", "Second Name"),
        )
        with self.assertRaisesRegex(SolutionPackError, "duplicate.*project:name"):
            apply_solution_pack_manifest(manifest)

    def test_application_revalidates_the_exact_recommendation_pin(self) -> None:
        manifest = _manifest(
            _project_change("rename-product", "project:name", "Northstar Editorial")
        )
        newer = replace(MINIMAL_BLOG_PACK, version="2.0.0")
        changed_registry = SolutionPackRegistry((*BASELINE_SOLUTION_PACKS, newer))
        with self.assertRaisesRegex(SolutionPackError, "pin"):
            apply_solution_pack_manifest(manifest, registry=changed_registry)


class ManifestCompatibilityTests(TestCase):
    def test_current_schema_round_trips_desired_text(self) -> None:
        manifest = _manifest(
            _project_change("rename-product", "project:name", "Northstar Editorial"),
            _ai_delta(),
        )
        payload = manifest.to_dict()
        self.assertEqual(payload["schema_version"], MANIFEST_SCHEMA_VERSION)
        self.assertEqual(payload["changes"][1]["desired_text"], "Northstar Editorial")
        self.assertIsNone(payload["changes"][0]["desired_text"])
        self.assertEqual(parse_solution_pack_manifest(manifest.to_json()), manifest)

    def test_legacy_r436_json_remains_lossless_but_unvalued_config_cannot_apply(self) -> None:
        manifest = _manifest(
            _project_change("rename-product", "project:name", "Northstar Editorial"),
            _ai_delta(),
        )
        legacy = manifest.to_dict()
        legacy["schema_version"] = LEGACY_MANIFEST_SCHEMA_VERSION
        for change in legacy["changes"]:
            del change["desired_text"]

        parsed = parse_solution_pack_manifest(legacy)
        self.assertEqual(parsed.schema_version, LEGACY_MANIFEST_SCHEMA_VERSION)
        self.assertEqual(parsed.to_dict(), legacy)
        with self.assertRaisesRegex(SolutionPackError, "explicit desired_text"):
            apply_solution_pack_manifest(parsed)


class AIDeltaProposalApplicationTests(TestCase):
    def _sample_tag_proposal(
        self,
        *,
        pack_id: str = "minimal-blog",
        pack_version: str = "1.0.0",
        base_ir_sha256: str = MINIMAL_BLOG_PACK.ir_sha256,
        addressed_change_ids: tuple[str, ...] = ("ai-tags",),
        entities: tuple[Entity, ...] | None = None,
        apis: tuple[ApiEndpoint, ...] | None = None,
        screens: tuple[Screen, ...] | None = None,
        capabilities: tuple[str, ...] = ("tagging",),
        rationale: str = "Add taxonomy tagging for posts.",
    ) -> AIDeltaProposal:
        if entities is None:
            entities = (
                Entity(
                    name="Tag",
                    fields=(
                        Field(name="id", type=FieldType.UUID, required=True),
                        Field(name="name", type=FieldType.STRING, required=True),
                    ),
                    relations=(
                        Relation(name="post", kind=RelationKind.MANY_TO_ONE, target_entity="Post"),
                    ),
                ),
            )
        if apis is None:
            apis = (
                ApiEndpoint(
                    method=HttpMethod.GET,
                    path="/tags",
                    auth=False,
                    response_schema="Tag",
                ),
            )
        if screens is None:
            screens = (
                Screen(
                    id="tag_list",
                    role="author",
                ),
            )
        return AIDeltaProposal(
            pack_id=pack_id,
            pack_version=pack_version,
            base_ir_sha256=base_ir_sha256,
            addressed_change_ids=addressed_change_ids,
            entities=entities,
            apis=apis,
            screens=screens,
            capabilities=capabilities,
            rationale=rationale,
        )

    def test_apply_ai_delta_proposal_success(self) -> None:
        manifest = _manifest(
            _project_change("rename-product", "project:name", "Northstar Editorial"),
            SolutionPackChange(
                change_id="ai-tags",
                source=ChangeSource.AI_DELTA,
                operation=ChangeOperation.ADD,
                area=ChangeArea.DATA_MODEL,
                target="entity:Tag",
                summary="Add tags entity for post categorization",
                acceptance_criteria=("Tags can be created and linked to posts",),
            ),
        )
        proposal = self._sample_tag_proposal(addressed_change_ids=("ai-tags",))

        result = apply_solution_pack_manifest(manifest, proposal=proposal)

        self.assertIsInstance(result, SolutionPackApplicationResult)
        self.assertEqual(result.ir.name, "Northstar Editorial")
        self.assertEqual(result.applied_configuration_change_ids, ("rename-product",))
        self.assertEqual(result.applied_ai_delta_change_ids, ("ai-tags",))
        self.assertEqual(result.unapplied_ai_delta_change_ids, ())
        self.assertEqual(result.base_ir_sha256, MINIMAL_BLOG_PACK.ir_sha256)
        self.assertNotEqual(result.derived_ir_sha256, result.base_ir_sha256)
        self.assertEqual(result.derived_ir_sha256, canonical_ir_digest(result.ir))

        entity_names = [e.name for e in result.ir.entities]
        self.assertIn("Post", entity_names)
        self.assertIn("Comment", entity_names)
        self.assertIn("Tag", entity_names)

        api_paths = [(a.method.value, a.path) for a in result.ir.apis]
        self.assertIn(("GET", "/tags"), api_paths)

        screen_ids = [s.id for s in result.ir.screens]
        self.assertIn("tag_list", screen_ids)

        self.assertFalse(has_errors(validate_ir(result.ir)))

        d = result.to_dict()
        self.assertEqual(d["applied_ai_delta_change_ids"], ["ai-tags"])
        self.assertEqual(d["unapplied_ai_delta_change_ids"], [])
        j = result.to_json()
        self.assertIn('"applied_ai_delta_change_ids":["ai-tags"]', j)

    def test_apply_ai_delta_proposal_partial(self) -> None:
        manifest = _manifest(
            SolutionPackChange(
                change_id="ai-tags",
                source=ChangeSource.AI_DELTA,
                operation=ChangeOperation.ADD,
                area=ChangeArea.DATA_MODEL,
                target="entity:Tag",
                summary="Add tags entity for post categorization",
                acceptance_criteria=("Tags can be created and linked to posts",),
            ),
            SolutionPackChange(
                change_id="ai-workflow",
                source=ChangeSource.AI_DELTA,
                operation=ChangeOperation.ADD,
                area=ChangeArea.SCREEN,
                target="screen:Workflow",
                summary="Add workflow screen",
                acceptance_criteria=("Workflow screen is visible",),
            ),
        )
        proposal = self._sample_tag_proposal(addressed_change_ids=("ai-tags",))

        result = apply_solution_pack_manifest(manifest, proposal=proposal)

        self.assertEqual(result.applied_ai_delta_change_ids, ("ai-tags",))
        self.assertEqual(result.unapplied_ai_delta_change_ids, ("ai-workflow",))

    def test_backward_compatibility_when_proposal_is_none(self) -> None:
        manifest = _manifest(
            _project_change("rename-product", "project:name", "Northstar Editorial"),
            SolutionPackChange(
                change_id="ai-tags",
                source=ChangeSource.AI_DELTA,
                operation=ChangeOperation.ADD,
                area=ChangeArea.DATA_MODEL,
                target="entity:Tag",
                summary="Add tags entity",
                acceptance_criteria=("Tags can be created",),
            ),
        )
        result = apply_solution_pack_manifest(manifest, proposal=None)

        self.assertEqual(result.applied_configuration_change_ids, ("rename-product",))
        self.assertEqual(result.applied_ai_delta_change_ids, ())
        self.assertEqual(result.unapplied_ai_delta_change_ids, ("ai-tags",))
        self.assertEqual(result.ir.name, "Northstar Editorial")
        self.assertEqual(len(result.ir.entities), 2)  # Post, Comment only

    def test_proposal_pin_mismatch_pack_id(self) -> None:
        manifest = _manifest(_ai_delta())
        proposal = self._sample_tag_proposal(
            pack_id="other-pack",
            addressed_change_ids=("add-editorial-flow",),
        )
        with self.assertRaisesRegex(SolutionPackError, "pack_id.*does not match"):
            apply_solution_pack_manifest(manifest, proposal=proposal)

    def test_proposal_pin_mismatch_pack_version(self) -> None:
        manifest = _manifest(_ai_delta())
        proposal = self._sample_tag_proposal(
            pack_version="2.0.0",
            addressed_change_ids=("add-editorial-flow",),
        )
        with self.assertRaisesRegex(SolutionPackError, "pack_version.*does not match"):
            apply_solution_pack_manifest(manifest, proposal=proposal)

    def test_proposal_pin_mismatch_base_ir_digest(self) -> None:
        manifest = _manifest(_ai_delta())
        proposal = self._sample_tag_proposal(
            base_ir_sha256="0" * 64,
            addressed_change_ids=("add-editorial-flow",),
        )
        with self.assertRaisesRegex(SolutionPackError, "base_ir_sha256.*does not match"):
            apply_solution_pack_manifest(manifest, proposal=proposal)

    def test_proposal_addresses_unmapped_change_id(self) -> None:
        manifest = _manifest(_ai_delta())
        proposal = self._sample_tag_proposal(
            addressed_change_ids=("unknown-change-id",),
        )
        with self.assertRaisesRegex(SolutionPackError, "unknown AI-delta change"):
            apply_solution_pack_manifest(manifest, proposal=proposal)

    def test_proposal_addresses_configuration_change_id(self) -> None:
        manifest = _manifest(
            _project_change("rename-product", "project:name", "Northstar Editorial"),
            _ai_delta(),
        )
        proposal = self._sample_tag_proposal(
            addressed_change_ids=("rename-product",),
        )
        with self.assertRaisesRegex(SolutionPackError, "unknown AI-delta change"):
            apply_solution_pack_manifest(manifest, proposal=proposal)

    def test_proposal_collides_with_base_entity_name(self) -> None:
        manifest = _manifest(_ai_delta())
        colliding_entity = Entity(
            name="Post",  # Already exists in minimal-blog
            fields=(Field(name="id", type=FieldType.UUID, required=True),),
        )
        proposal = self._sample_tag_proposal(
            addressed_change_ids=("add-editorial-flow",),
            entities=(colliding_entity,),
        )
        with self.assertRaisesRegex(SolutionPackError, "entity.*collides"):
            apply_solution_pack_manifest(manifest, proposal=proposal)

    def test_proposal_collides_with_base_api_endpoint(self) -> None:
        manifest = _manifest(_ai_delta())
        colliding_api = ApiEndpoint(
            method=HttpMethod.GET,
            path="/posts",  # Already exists in minimal-blog
            auth=False,
        )
        proposal = self._sample_tag_proposal(
            addressed_change_ids=("add-editorial-flow",),
            apis=(colliding_api,),
        )
        with self.assertRaisesRegex(SolutionPackError, "API endpoint.*collides"):
            apply_solution_pack_manifest(manifest, proposal=proposal)

    def test_proposal_collides_with_base_screen_id(self) -> None:
        manifest = _manifest(_ai_delta())
        colliding_screen = Screen(
            id="post_list",  # Already exists in minimal-blog
            role="reader",
        )
        proposal = self._sample_tag_proposal(
            addressed_change_ids=("add-editorial-flow",),
            screens=(colliding_screen,),
        )
        with self.assertRaisesRegex(SolutionPackError, "screen.*collides"):
            apply_solution_pack_manifest(manifest, proposal=proposal)

    def test_proposal_relation_targets_unknown_entity(self) -> None:
        manifest = _manifest(_ai_delta())
        broken_entity = Entity(
            name="Broken",
            fields=(Field(name="id", type=FieldType.UUID, required=True),),
            relations=(
                Relation(name="target", kind=RelationKind.MANY_TO_ONE, target_entity="DoesNotExist"),
            ),
        )
        proposal = self._sample_tag_proposal(
            addressed_change_ids=("add-editorial-flow",),
            entities=(broken_entity,),
        )
        with self.assertRaisesRegex(SolutionPackError, "relation targets undeclared entity"):
            apply_solution_pack_manifest(manifest, proposal=proposal)

    def test_proposal_derived_ir_semantic_validation_failure(self) -> None:
        manifest = _manifest(_ai_delta())
        invalid_api = ApiEndpoint(
            method=HttpMethod.GET,
            path="/tags",
            auth=False,
            response_schema="UndeclaredEntity",
        )
        proposal = self._sample_tag_proposal(
            addressed_change_ids=("add-editorial-flow",),
            apis=(invalid_api,),
        )
        with self.assertRaisesRegex(SolutionPackError, "invalid Application IR|semantic validation"):
            apply_solution_pack_manifest(manifest, proposal=proposal)

    def test_proposal_application_is_repeatable_and_byte_stable(self) -> None:
        manifest = _manifest(
            _project_change("rename-product", "project:name", "Northstar Editorial"),
            SolutionPackChange(
                change_id="ai-tags",
                source=ChangeSource.AI_DELTA,
                operation=ChangeOperation.ADD,
                area=ChangeArea.DATA_MODEL,
                target="entity:Tag",
                summary="Add tags entity",
                acceptance_criteria=("Tags can be created",),
            ),
        )
        proposal = self._sample_tag_proposal(addressed_change_ids=("ai-tags",))
        first = apply_solution_pack_manifest(manifest, proposal=proposal)
        second = apply_solution_pack_manifest(manifest, proposal=proposal)
        self.assertEqual(first, second)
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(
            DEFAULT_SOLUTION_PACK_REGISTRY.load_ir("minimal-blog").name,
            "Minimal Blog",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()

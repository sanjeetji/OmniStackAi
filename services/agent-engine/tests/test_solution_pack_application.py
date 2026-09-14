"""R-437: deterministic Solution Pack configuration application."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from unittest import TestCase

from omnistackai_agent_engine.application_ir import validate_ir
from omnistackai_agent_engine.application_ir.validate import has_errors
from omnistackai_agent_engine.solution_packs import (
    BASELINE_SOLUTION_PACKS,
    DEFAULT_SOLUTION_PACK_REGISTRY,
    LEGACY_MANIFEST_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    MINIMAL_BLOG_PACK,
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


if __name__ == "__main__":
    import unittest

    unittest.main()

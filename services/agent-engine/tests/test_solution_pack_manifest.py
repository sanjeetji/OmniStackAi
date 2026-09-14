"""R-436: pinned declarative Solution Pack customization manifests."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from unittest import TestCase

from omnistackai_agent_engine.solution_packs import (
    DEFAULT_SOLUTION_PACK_REGISTRY,
    MANIFEST_SCHEMA_VERSION,
    MAX_MANIFEST_CHANGES,
    MINIMAL_BLOG_PACK,
    ChangeArea,
    ChangeOperation,
    ChangeSource,
    SolutionPackChange,
    SolutionPackError,
    SolutionPackManifest,
    canonical_ir_digest,
    create_solution_pack_manifest,
    parse_solution_pack_manifest,
)


def _blog_recommendation():
    return DEFAULT_SOLUTION_PACK_REGISTRY.recommend(
        "blog-cms",
        required_targets=("nextjs-web", "backend-python"),
    )


def _configuration_change(**changes: object) -> SolutionPackChange:
    values: dict[str, object] = {
        "change_id": "rename-product",
        "source": ChangeSource.CONFIGURATION,
        "operation": ChangeOperation.UPDATE,
        "area": ChangeArea.PROJECT,
        "target": "project:name",
        "desired_text": "Editorial Workspace",
        "summary": "Use the accepted customer-facing product name.",
        "acceptance_criteria": ("The product name is shown consistently.",),
    }
    values.update(changes)
    return SolutionPackChange(**values)  # type: ignore[arg-type]


def _ai_delta_change(**changes: object) -> SolutionPackChange:
    values: dict[str, object] = {
        "change_id": "add-editor-workflow",
        "source": ChangeSource.AI_DELTA,
        "operation": ChangeOperation.ADD,
        "area": ChangeArea.SCREEN,
        "target": "screen:EditorialWorkflow",
        "summary": "Add the differentiated editorial approval experience.",
        "acceptance_criteria": (
            "Editors can request approval.",
            "Publishers can approve or reject a request.",
        ),
    }
    values.update(changes)
    return SolutionPackChange(**values)  # type: ignore[arg-type]


class ManifestConstructionTests(TestCase):
    def test_selected_recommendation_creates_an_exact_frozen_pin(self) -> None:
        manifest = create_solution_pack_manifest(
            _blog_recommendation(),
            changes=(_configuration_change(), _ai_delta_change()),
        )

        self.assertIsInstance(manifest, SolutionPackManifest)
        self.assertEqual(manifest.schema_version, MANIFEST_SCHEMA_VERSION)
        self.assertEqual(manifest.pack_id, "minimal-blog")
        self.assertEqual(manifest.pack_version, "1.0.0")
        self.assertEqual(manifest.pack_ir_sha256, MINIMAL_BLOG_PACK.ir_sha256)
        self.assertEqual(manifest.domain, "blog-cms")
        self.assertEqual(manifest.required_capabilities, ())
        self.assertEqual(manifest.required_targets, ("backend-python", "nextjs-web"))
        self.assertEqual(
            canonical_ir_digest(DEFAULT_SOLUTION_PACK_REGISTRY.load_ir("minimal-blog")),
            manifest.pack_ir_sha256,
        )
        with self.assertRaises(FrozenInstanceError):
            manifest.pack_version = "2.0.0"  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            manifest.changes[0].summary = "changed"  # type: ignore[misc]

    def test_no_match_recommendation_is_rejected(self) -> None:
        recommendation = DEFAULT_SOLUTION_PACK_REGISTRY.recommend(
            "rideshare",
            required_targets=("backend-python", "nextjs-web"),
        )
        self.assertIsNone(recommendation.selection)
        with self.assertRaisesRegex(SolutionPackError, "selected"):
            create_solution_pack_manifest(recommendation)

    def test_changes_are_canonicalized_and_duplicate_ids_rejected(self) -> None:
        first = _configuration_change(change_id="z-last")
        second = _ai_delta_change(change_id="a-first")
        manifest = create_solution_pack_manifest(
            _blog_recommendation(),
            changes=(first, second),
        )
        self.assertEqual(
            tuple(change.change_id for change in manifest.changes),
            ("a-first", "z-last"),
        )
        with self.assertRaisesRegex(SolutionPackError, "duplicate"):
            create_solution_pack_manifest(
                _blog_recommendation(),
                changes=(first, replace(first)),
            )
        with self.assertRaisesRegex(SolutionPackError, "SolutionPackChange"):
            create_solution_pack_manifest(
                _blog_recommendation(),
                changes=("not-a-change",),  # type: ignore[arg-type]
            )


class TypedChangeValidationTests(TestCase):
    def test_configuration_and_ai_delta_changes_are_typed(self) -> None:
        configuration = _configuration_change()
        delta = _ai_delta_change()
        self.assertEqual(configuration.source, ChangeSource.CONFIGURATION)
        self.assertEqual(delta.source, ChangeSource.AI_DELTA)
        self.assertEqual(configuration.operation, ChangeOperation.UPDATE)
        self.assertEqual(delta.area, ChangeArea.SCREEN)

    def test_every_area_accepts_only_its_semantic_target_kinds(self) -> None:
        valid = (
            (ChangeArea.PROJECT, "project:name"),
            (ChangeArea.DATA_MODEL, "entity:Post"),
            (ChangeArea.DATA_MODEL, "field:Post.status"),
            (ChangeArea.API, "api:Post.publish"),
            (ChangeArea.SCREEN, "screen:PostEditor"),
            (ChangeArea.DESIGN, "design:tokens"),
            (ChangeArea.CAPABILITY, "capability:editorial-approval"),
        )
        for area, target in valid:
            with self.subTest(area=area, target=target):
                self.assertEqual(
                    _configuration_change(
                        area=area,
                        target=target,
                        desired_text=(
                            "Editorial Workspace" if area is ChangeArea.PROJECT else None
                        ),
                    ).target,
                    target,
                )

        with self.assertRaisesRegex(SolutionPackError, "target"):
            _configuration_change(area=ChangeArea.API, target="screen:PostEditor")
        with self.assertRaisesRegex(SolutionPackError, "semantic"):
            _configuration_change(target="../../apps/web/page.tsx")

    def test_wrong_enums_types_controls_and_bounds_fail_closed(self) -> None:
        cases = (
            {"source": "ai-delta"},
            {"operation": "execute"},
            {"area": "file"},
            {"summary": "unsafe\ncommand"},
            {"summary": "x" * 241},
            {"acceptance_criteria": ()},
            {"acceptance_criteria": ("x" * 241,)},
            {"acceptance_criteria": tuple(f"criterion {index}" for index in range(9))},
        )
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(SolutionPackError):
                _configuration_change(**changes)

    def test_total_change_count_is_bounded(self) -> None:
        changes = tuple(
            _configuration_change(change_id=f"change-{index}")
            for index in range(MAX_MANIFEST_CHANGES + 1)
        )
        with self.assertRaisesRegex(SolutionPackError, "at most"):
            create_solution_pack_manifest(_blog_recommendation(), changes=changes)


class ManifestJsonTests(TestCase):
    def _manifest(self) -> SolutionPackManifest:
        return create_solution_pack_manifest(
            _blog_recommendation(),
            changes=(_configuration_change(), _ai_delta_change()),
        )

    def test_canonical_json_is_byte_stable_and_declarative_only(self) -> None:
        manifest = self._manifest()
        first = manifest.to_json()
        second = manifest.to_json()
        self.assertEqual(first, second)
        self.assertEqual(
            first,
            json.dumps(manifest.to_dict(), separators=(",", ":"), sort_keys=True),
        )
        payload = json.loads(first)
        self.assertEqual(payload["base_pack"]["pack_id"], "minimal-blog")
        self.assertEqual(payload["changes"][0]["change_id"], "add-editor-workflow")
        self.assertEqual(payload["changes"][0]["source"], "ai-delta")
        forbidden_keys = {
            "path",
            "patch",
            "source_code",
            "command",
            "model_output",
            "secret_value",
        }
        observed_keys: set[str] = set()

        def collect(value: object) -> None:
            if isinstance(value, dict):
                observed_keys.update(value)
                for nested in value.values():
                    collect(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)

        collect(payload)
        self.assertTrue(forbidden_keys.isdisjoint(observed_keys))

    def test_strict_json_round_trip_revalidates_the_registered_pin(self) -> None:
        manifest = self._manifest()
        self.assertEqual(parse_solution_pack_manifest(manifest.to_json()), manifest)
        self.assertEqual(parse_solution_pack_manifest(manifest.to_dict()), manifest)

        drifted = manifest.to_dict()
        drifted["base_pack"]["ir_sha256"] = "0" * 64
        with self.assertRaisesRegex(SolutionPackError, "pin"):
            parse_solution_pack_manifest(drifted)

    def test_strict_parser_rejects_unknown_missing_and_malformed_fields(self) -> None:
        unknown = self._manifest().to_dict()
        unknown["patch"] = "not allowed"
        with self.assertRaisesRegex(SolutionPackError, "keys"):
            parse_solution_pack_manifest(unknown)

        missing = self._manifest().to_dict()
        del missing["query"]
        with self.assertRaisesRegex(SolutionPackError, "keys"):
            parse_solution_pack_manifest(missing)

        for document in ("not-json", "[]", {"schema_version": 1}):
            with self.subTest(document=document), self.assertRaises(SolutionPackError):
                parse_solution_pack_manifest(document)

    def test_parser_rejects_query_or_version_that_does_not_recommend_exact_pin(self) -> None:
        wrong_query = self._manifest().to_dict()
        wrong_query["query"]["required_targets"] = ["backend-go", "nextjs-web"]
        with self.assertRaisesRegex(SolutionPackError, "pin"):
            parse_solution_pack_manifest(wrong_query)

        wrong_version = self._manifest().to_dict()
        wrong_version["base_pack"]["version"] = "2.0.0"
        with self.assertRaisesRegex(SolutionPackError, "pin"):
            parse_solution_pack_manifest(wrong_version)


if __name__ == "__main__":
    import unittest

    unittest.main()

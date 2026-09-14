"""Tests for Solution Pack builder pipelines and multi-repo project generation (R-440)."""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from omnistackai_agent_engine.solution_packs import build_cli

from omnistackai_agent_engine.application_ir import (
    ApiEndpoint,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    Screen,
)
from omnistackai_agent_engine.intake import (
    ScopeProposal,
    build_ecosystem,
    plan_ecosystem,
    propose_ecosystem,
)
from omnistackai_agent_engine.solution_packs import (
    AIDeltaProposal,
    ChangeArea,
    ChangeOperation,
    ChangeSource,
    DEFAULT_SOLUTION_PACK_REGISTRY,
    SolutionPackApplicationResult,
    SolutionPackBuildResult,
    SolutionPackChange,
    SolutionPackError,
    SolutionPackManifest,
    apply_solution_pack_manifest,
    build_solution_pack_project,
    create_solution_pack_manifest,
)

_AUTHOR_NAME = "sanjeetji"
_AUTHOR_EMAIL = "sk698166@gmail.com"


def _make_sample_manifest(
    new_name: str = "Customized Blog",
) -> tuple[SolutionPackManifest, AIDeltaProposal]:
    rec = DEFAULT_SOLUTION_PACK_REGISTRY.recommend(
        "blog-cms",
        required_targets=("backend-python", "nextjs-web"),
    )
    assert rec.selection is not None
    config_change = SolutionPackChange(
        change_id="cfg-rename",
        source=ChangeSource.CONFIGURATION,
        operation=ChangeOperation.UPDATE,
        area=ChangeArea.PROJECT,
        target="project:name",
        summary="Rename blog project",
        acceptance_criteria=("Project name is updated",),
        desired_text=new_name,
    )
    ai_change = SolutionPackChange(
        change_id="ai-newsletter",
        source=ChangeSource.AI_DELTA,
        operation=ChangeOperation.ADD,
        area=ChangeArea.DATA_MODEL,
        target="entity:Subscriber",
        summary="Add newsletter subscriber entity",
        acceptance_criteria=("Subscribers can be registered",),
    )
    manifest = create_solution_pack_manifest(rec, changes=(config_change, ai_change))
    proposal = AIDeltaProposal(
        pack_id="minimal-blog",
        pack_version="1.0.0",
        base_ir_sha256=rec.selection.ir_sha256,
        addressed_change_ids=("ai-newsletter",),
        entities=(
            Entity(
                name="Subscriber",
                fields=(
                    Field(name="id", type=FieldType.UUID, required=True),
                    Field(name="email", type=FieldType.STRING, required=True),
                ),
            ),
        ),
        apis=(
            ApiEndpoint(
                method=HttpMethod.POST,
                path="/subscribers",
                request_schema="Subscriber",
                response_schema="Subscriber",
                auth=False,
            ),
        ),
        screens=(
            Screen(
                id="newsletter_signup",
                role="reader",
            ),
        ),
        capabilities=("newsletter",),
        rationale="Adds newsletter subscriber management.",
    )
    return manifest, proposal


class TestSolutionPackBuilder(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = os.path.realpath(tempfile.mkdtemp(prefix="omnistackai-sp-build-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_solution_pack_project_from_application_result(self) -> None:
        manifest, proposal = _make_sample_manifest("Engineering Journal")
        app_result = apply_solution_pack_manifest(manifest, proposal=proposal)
        target = os.path.join(self.temp_dir, "eng-journal")

        build_result = build_solution_pack_project(
            app_result,
            target,
            author_name=_AUTHOR_NAME,
            author_email=_AUTHOR_EMAIL,
        )

        self.assertIsInstance(build_result, SolutionPackBuildResult)
        self.assertEqual(build_result.pack_id, "minimal-blog")
        self.assertEqual(build_result.pack_version, "1.0.0")
        self.assertEqual(build_result.app_name, "Engineering Journal")
        self.assertEqual(build_result.applied_configuration_change_ids, ("cfg-rename",))
        self.assertEqual(build_result.applied_ai_delta_change_ids, ("ai-newsletter",))
        self.assertEqual(build_result.unapplied_ai_delta_change_ids, ())
        self.assertEqual(build_result.target_dir, target)
        self.assertGreater(build_result.file_count, 100)
        self.assertEqual(len(build_result.commit_sha), 40)
        self.assertIn("nextjs-web", build_result.verify_targets)
        self.assertIn("backend-python", build_result.verify_targets)

        # Check repository files on disk
        target_path = Path(target)
        self.assertTrue((target_path / ".git").is_dir())
        self.assertTrue((target_path / "apps" / "web" / "package.json").is_file())
        self.assertTrue((target_path / "services" / "api" / "requirements.txt").is_file())

    def test_build_solution_pack_project_directly_from_manifest_and_proposal(self) -> None:
        manifest, proposal = _make_sample_manifest("Tech Chronicles")
        target = os.path.join(self.temp_dir, "tech-chronicles")

        build_result = build_solution_pack_project(
            manifest,
            target,
            proposal=proposal,
            author_name=_AUTHOR_NAME,
            author_email=_AUTHOR_EMAIL,
        )

        self.assertEqual(build_result.app_name, "Tech Chronicles")
        self.assertEqual(build_result.applied_configuration_change_ids, ("cfg-rename",))
        self.assertEqual(build_result.applied_ai_delta_change_ids, ("ai-newsletter",))

    def test_build_solution_pack_project_without_proposal_backward_compatibility(self) -> None:
        manifest, _ = _make_sample_manifest("Configuration Only Blog")
        target = os.path.join(self.temp_dir, "config-blog")

        build_result = build_solution_pack_project(
            manifest,
            target,
            proposal=None,
            author_name=_AUTHOR_NAME,
            author_email=_AUTHOR_EMAIL,
        )

        self.assertEqual(build_result.app_name, "Configuration Only Blog")
        self.assertEqual(build_result.applied_configuration_change_ids, ("cfg-rename",))
        self.assertEqual(build_result.applied_ai_delta_change_ids, ())
        self.assertEqual(build_result.unapplied_ai_delta_change_ids, ("ai-newsletter",))

    def test_build_result_serialization_and_byte_stability(self) -> None:
        manifest, proposal = _make_sample_manifest("Deterministic Serialized")
        app_result = apply_solution_pack_manifest(manifest, proposal=proposal)
        target = os.path.join(self.temp_dir, "det-blog")

        build_result = build_solution_pack_project(
            app_result,
            target,
            author_name=_AUTHOR_NAME,
            author_email=_AUTHOR_EMAIL,
        )

        d = build_result.to_dict()
        self.assertEqual(d["pack_id"], "minimal-blog")
        self.assertEqual(d["pack_version"], "1.0.0")
        self.assertEqual(d["app_name"], "Deterministic Serialized")
        self.assertEqual(d["applied_configuration_change_ids"], ["cfg-rename"])
        self.assertEqual(d["applied_ai_delta_change_ids"], ["ai-newsletter"])
        self.assertEqual(d["unapplied_ai_delta_change_ids"], [])
        self.assertEqual(d["verify_targets"], sorted(list(build_result.verify_targets)))

        # Byte stable JSON
        json_str1 = build_result.to_json()
        json_str2 = build_result.to_json()
        self.assertEqual(json_str1, json_str2)
        parsed = json.loads(json_str1)
        self.assertEqual(parsed["pack_id"], "minimal-blog")

    def test_plan_ecosystem_with_pack_result(self) -> None:
        proposal = propose_ecosystem("Create a blog and CMS platform for writers and readers")
        manifest, ai_proposal = _make_sample_manifest("Enterprise Blog")
        app_result = apply_solution_pack_manifest(manifest, proposal=ai_proposal)

        plan = plan_ecosystem(proposal, "complete", pack_result=app_result)

        # In blog-cms, surfaces are Reader App, Author Studio, Editorial Admin.
        # The primary customer/reader or author surface is backed by the pack IR.
        pack_apps = [a for a in plan.apps if a.pack_result is not None]
        self.assertEqual(len(pack_apps), 1)
        backed_app = pack_apps[0]
        self.assertEqual(backed_app.ir.name, "Enterprise Blog")
        self.assertIn("Subscriber", [e.name for e in backed_app.ir.entities])

        # Serialized plan reflects pack provenance
        plan_dict = plan.to_dict()
        backed_dict = [a for a in plan_dict["apps"] if a.get("pack_result") is not None][0]
        self.assertEqual(backed_dict["pack_result"]["base_pack"]["pack_id"], "minimal-blog")
        self.assertEqual(backed_dict["pack_result"]["applied_ai_delta_change_ids"], ["ai-newsletter"])

    def test_plan_ecosystem_with_manifest_and_proposal(self) -> None:
        proposal = propose_ecosystem("Create a blog and CMS platform for writers and readers")
        manifest, ai_proposal = _make_sample_manifest("Direct Manifest Blog")

        plan = plan_ecosystem(
            proposal,
            "complete",
            pack_manifest=manifest,
            pack_proposal=ai_proposal,
        )

        pack_apps = [a for a in plan.apps if a.pack_result is not None]
        self.assertEqual(len(pack_apps), 1)
        self.assertEqual(pack_apps[0].ir.name, "Direct Manifest Blog")

    def test_plan_ecosystem_rejects_incompatible_pack(self) -> None:
        # Rideshare proposal with minimal-blog pack
        proposal = propose_ecosystem("Create a rideshare app for passengers and drivers")
        manifest, ai_proposal = _make_sample_manifest("Mismatched Blog")
        app_result = apply_solution_pack_manifest(manifest, proposal=ai_proposal)

        with self.assertRaisesRegex(SolutionPackError, "does not match ecosystem domain"):
            plan_ecosystem(proposal, "complete", pack_result=app_result)

    def test_build_ecosystem_with_pack_wires_provenance_and_verifies(self) -> None:
        proposal = propose_ecosystem("Create a blog and CMS platform for writers and readers")
        manifest, ai_proposal = _make_sample_manifest("Wired Ecosystem Blog")
        app_result = apply_solution_pack_manifest(manifest, proposal=ai_proposal)

        plan = plan_ecosystem(proposal, "complete", pack_result=app_result)
        out_dir = os.path.join(self.temp_dir, "ecosystem-out")

        eco_result = build_ecosystem(
            plan,
            out_dir,
            author_name=_AUTHOR_NAME,
            author_email=_AUTHOR_EMAIL,
            overwrite=True,
        )

        self.assertEqual(len(eco_result.apps), len(plan.apps))
        # Find the app that was pack-backed
        pack_builds = [b for b in eco_result.apps if b.pack_id is not None]
        self.assertEqual(len(pack_builds), 1)
        pack_build = pack_builds[0]
        self.assertEqual(pack_build.pack_id, "minimal-blog")
        self.assertEqual(pack_build.pack_version, "1.0.0")
        self.assertEqual(pack_build.derived_ir_sha256, app_result.derived_ir_sha256)
        self.assertEqual(pack_build.applied_change_ids, ("cfg-rename", "ai-newsletter"))
        self.assertIn("nextjs-web", pack_build.verify_targets)
        self.assertIn("backend-python", pack_build.verify_targets)

        # Check all apps have verify_targets
        for app_build in eco_result.apps:
            self.assertTrue(len(app_build.verify_targets) > 0)

        # JSON serialization includes pack fields
        eco_dict = eco_result.to_dict()
        pack_dict = [b for b in eco_dict["apps"] if b.get("pack_id") is not None][0]
        self.assertEqual(pack_dict["pack_id"], "minimal-blog")
        self.assertEqual(pack_dict["applied_change_ids"], ["cfg-rename", "ai-newsletter"])

    def test_build_cli_with_pack_id(self) -> None:
        target = os.path.join(self.temp_dir, "cli-pack-blog")
        buf = io.StringIO()
        exit_code = build_cli.main(["minimal-blog", target], stdout=buf)
        self.assertEqual(exit_code, 0)
        output = buf.getvalue()
        self.assertIn("minimal-blog v1.0.0", output)
        self.assertIn("SolutionPackBuildResult (JSON)", output)
        self.assertTrue((Path(target) / ".git").is_dir())

    def test_build_cli_with_manifest_file(self) -> None:
        manifest, proposal = _make_sample_manifest("CLI Manifest Blog")
        manifest_file = os.path.join(self.temp_dir, "manifest.json")
        Path(manifest_file).write_text(manifest.to_json(), encoding="utf-8")

        target = os.path.join(self.temp_dir, "cli-manifest-blog")
        buf = io.StringIO()
        exit_code = build_cli.main([manifest_file, target], stdout=buf)
        self.assertEqual(exit_code, 0)
        output = buf.getvalue()
        self.assertIn("CLI Manifest Blog", output)
        self.assertTrue((Path(target) / ".git").is_dir())

    def test_build_cli_unknown_pack_exits_2(self) -> None:
        err_buf = io.StringIO()
        stderr_orig = build_cli.sys.stderr
        try:
            build_cli.sys.stderr = err_buf
            exit_code = build_cli.main(["nonexistent-pack", self.temp_dir])
        finally:
            build_cli.sys.stderr = stderr_orig
        self.assertEqual(exit_code, 2)
        self.assertIn("Error: Unknown solution pack or file 'nonexistent-pack'", err_buf.getvalue())


if __name__ == "__main__":
    unittest.main()

"""Tests for R-444 Solution Pack Multi-Surface Ecosystem Pack Synthesis."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from omnistackai_agent_engine.application_ir import (
    ApiEndpoint,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    Screen,
    has_errors,
    validate_ir,
)
from omnistackai_agent_engine.intake import (
    EcosystemPlan,
    SurfaceApp,
    plan_ecosystem,
    propose_ecosystem,
)
from omnistackai_agent_engine.solution_packs import (
    AIDeltaProposal,
    DEFAULT_SOLUTION_PACK_REGISTRY,
    ECOSYSTEM_PACK_SCHEMA_VERSION,
    ChangeArea,
    ChangeOperation,
    ChangeSource,
    EcosystemPackPackage,
    EcosystemSurfacePackage,
    SolutionPackChange,
    SolutionPackError,
    create_solution_pack_manifest,
    apply_solution_pack_manifest,
    parse_ecosystem_pack_package,
    synthesize_ecosystem_pack,
    verify_ecosystem_pack,
)
from omnistackai_agent_engine.solution_packs.ecosystem_cli import main as ecosystem_cli_main


class TestSolutionPackEcosystemSynthesis(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = DEFAULT_SOLUTION_PACK_REGISTRY

    def test_synthesize_minimal_blog_ecosystem(self) -> None:
        """minimal-blog pack synthesizes all 3 blog surfaces sharing Post & Comment entities."""
        pack = self.registry.get("minimal-blog")
        self.assertIsNotNone(pack)

        eco_pkg = synthesize_ecosystem_pack(pack, registry=self.registry)
        self.assertIsInstance(eco_pkg, EcosystemPackPackage)
        self.assertEqual(eco_pkg.schema_version, ECOSYSTEM_PACK_SCHEMA_VERSION)
        self.assertEqual(eco_pkg.base_pack_id, "minimal-blog")
        self.assertEqual(eco_pkg.domain, "blog-cms")
        self.assertEqual(len(eco_pkg.surfaces), 3)

        kinds = [s.surface_kind for s in eco_pkg.surfaces]
        self.assertIn("public_web", kinds)
        self.assertIn("provider_portal", kinds)
        self.assertIn("admin_dashboard", kinds)

        for surface in eco_pkg.surfaces:
            ir = surface.to_application_ir()
            issues = validate_ir(ir)
            self.assertFalse(has_errors(issues), f"Surface {surface.surface_kind} had IR errors")
            # All surfaces must share Post and Comment
            entity_names = {e.name for e in ir.entities}
            self.assertIn("Post", entity_names)
            self.assertIn("Comment", entity_names)
            # Must NOT contain the fallback static domain entity 'Article'
            self.assertNotIn("Article", entity_names)
            self.assertEqual(ir.project_strategy.database_strategy.name, "POSTGRES")

    def test_synthesize_rideshare_favourites_ecosystem(self) -> None:
        """rideshare-favourites pack synthesizes all 3 surfaces sharing Driver and FavouriteDriver."""
        pack = self.registry.get("rideshare-favourites")
        self.assertIsNotNone(pack)

        eco_pkg = synthesize_ecosystem_pack(pack, registry=self.registry)
        self.assertEqual(eco_pkg.base_pack_id, "rideshare-favourites")
        self.assertEqual(eco_pkg.domain, "rideshare")
        self.assertEqual(len(eco_pkg.surfaces), 3)

        kinds = [s.surface_kind for s in eco_pkg.surfaces]
        self.assertIn("customer_pwa", kinds)
        self.assertIn("driver_portal", kinds)
        self.assertIn("admin_dashboard", kinds)

        for surface in eco_pkg.surfaces:
            ir = surface.to_application_ir()
            issues = validate_ir(ir)
            self.assertFalse(has_errors(issues), f"Surface {surface.surface_kind} had IR errors")
            entity_names = {e.name for e in ir.entities}
            self.assertIn("Driver", entity_names)
            self.assertEqual(ir.project_strategy.backend_strategy.name, "GO")

    def test_synthesize_from_pack_application_result(self) -> None:
        """Synthesizing from a SolutionPackApplicationResult with custom metadata preserves customizations."""
        rec = self.registry.recommend("blog-cms", required_targets=("nextjs-web", "backend-python"))
        change1 = SolutionPackChange(
            change_id="custom-name",
            source=ChangeSource.CONFIGURATION,
            operation=ChangeOperation.UPDATE,
            area=ChangeArea.PROJECT,
            target="project:name",
            desired_text="Custom Blog",
            summary="Update project name",
            acceptance_criteria=("project name updated",),
        )
        change2 = SolutionPackChange(
            change_id="custom-desc",
            source=ChangeSource.CONFIGURATION,
            operation=ChangeOperation.UPDATE,
            area=ChangeArea.PROJECT,
            target="project:description",
            desired_text="Custom Blog Platform",
            summary="Update project description",
            acceptance_criteria=("project description updated",),
        )
        manifest = create_solution_pack_manifest(
            rec,
            changes=(change1, change2),
        )
        app_result = apply_solution_pack_manifest(manifest, registry=self.registry)

        eco_pkg = synthesize_ecosystem_pack(app_result, registry=self.registry)
        self.assertEqual(eco_pkg.base_pack_id, "minimal-blog")
        self.assertIn("Custom Blog", eco_pkg.display_name)
        # Primary surface should have custom name
        primary_surface = next(s for s in eco_pkg.surfaces if s.surface_kind == "public_web")
        primary_ir = primary_surface.to_application_ir()
        self.assertEqual(primary_ir.name, "Custom Blog")
        self.assertEqual(primary_ir.description, "Custom Blog Platform")

    def test_canonical_json_determinism_and_roundtrip(self) -> None:
        """EcosystemPackPackage to_json produces byte-identical determinism and round-trips."""
        pack = self.registry.get("minimal-blog")
        eco_pkg = synthesize_ecosystem_pack(pack, registry=self.registry)

        json_str_1 = eco_pkg.to_json()
        json_str_2 = eco_pkg.to_json()
        self.assertEqual(json_str_1, json_str_2)

        # Roundtrip parse
        reparsed = parse_ecosystem_pack_package(json_str_1)
        self.assertEqual(reparsed.schema_version, eco_pkg.schema_version)
        self.assertEqual(reparsed.ecosystem_id, eco_pkg.ecosystem_id)
        self.assertEqual(reparsed.domain, eco_pkg.domain)
        self.assertEqual(reparsed.package_sha256, eco_pkg.package_sha256)
        self.assertEqual(len(reparsed.surfaces), len(eco_pkg.surfaces))
        self.assertEqual(reparsed.to_json(), json_str_1)

    def test_tampered_surface_ir_fails_closed(self) -> None:
        """Tampering with an embedded surface IR fails closed with SolutionPackError."""
        pack = self.registry.get("minimal-blog")
        eco_pkg = synthesize_ecosystem_pack(pack, registry=self.registry)
        data = eco_pkg.to_dict()

        # Tamper with the first surface IR
        data["surfaces"][0]["ir_dict"]["name"] = "Tampered App Name"

        with self.assertRaises(SolutionPackError) as ctx:
            parse_ecosystem_pack_package(data)
        self.assertIn("checksum", str(ctx.exception).lower())

    def test_tampered_package_checksum_fails_closed(self) -> None:
        """Tampering with the package checksum fails closed."""
        pack = self.registry.get("minimal-blog")
        eco_pkg = synthesize_ecosystem_pack(pack, registry=self.registry)
        data = eco_pkg.to_dict()
        data["package_sha256"] = "0" * 64

        with self.assertRaises(SolutionPackError) as ctx:
            parse_ecosystem_pack_package(data)
        self.assertIn("checksum", str(ctx.exception).lower())

    def test_verify_ecosystem_pack_function(self) -> None:
        """verify_ecosystem_pack correctly diagnoses valid and invalid packages."""
        pack = self.registry.get("minimal-blog")
        eco_pkg = synthesize_ecosystem_pack(pack, registry=self.registry)

        valid, diags = verify_ecosystem_pack(eco_pkg)
        self.assertTrue(valid)
        self.assertEqual(len(diags), 0)

        # Corrupted
        data = eco_pkg.to_dict()
        data["package_sha256"] = "badchecksum"
        valid, diags = verify_ecosystem_pack(data)
        self.assertFalse(valid)
        self.assertGreater(len(diags), 0)

    def test_plan_ecosystem_with_pack_result_synthesizes_all_surfaces(self) -> None:
        """plan_ecosystem synthesizes secondary surfaces from pack_result data model."""
        rec = self.registry.recommend("blog-cms", required_targets=("nextjs-web", "backend-python"))
        manifest = create_solution_pack_manifest(rec)
        app_result = apply_solution_pack_manifest(manifest, registry=self.registry)

        proposal = propose_ecosystem("Create a blog platform for publishing articles")
        plan = plan_ecosystem(proposal, pack_result=app_result, registry=self.registry)

        self.assertEqual(len(plan.apps), 3)
        for app in plan.apps:
            self.assertIsInstance(app, SurfaceApp)
            entity_names = {e.name for e in app.ir.entities}
            self.assertIn("Post", entity_names)
            self.assertIn("Comment", entity_names)
            self.assertNotIn("Article", entity_names)

        # Check synthesis flags
        primary = plan.apps[0]
        self.assertIsNotNone(primary.pack_result)

        secondary = plan.apps[1]
        self.assertTrue(getattr(secondary, "is_synthesized", False))

    def test_cli_synthesize_inspect_and_verify(self) -> None:
        """CLI synthesize, inspect, and verify subcommands work end-to-end."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "test.ecosystem.pack.json")

            # 1. Synthesize
            rc = ecosystem_cli_main(["synthesize", "--pack", "minimal-blog", "--output", out_file])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(out_file))

            # 2. Verify
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = ecosystem_cli_main(["verify", out_file])
            self.assertEqual(rc, 0)
            self.assertIn("is valid (verified)", buf.getvalue())

            # 3. Inspect
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = ecosystem_cli_main(["inspect", out_file])
            self.assertEqual(rc, 0)
            output = buf.getvalue()
            self.assertIn("Ecosystem Pack: minimal-blog-ecosystem", output)
            self.assertIn("Surfaces: 3", output)
            self.assertIn("Integrity: VERIFIED", output)

    def test_cli_build_subcommand(self) -> None:
        """CLI build subcommand materializes all surfaces into owned Git repos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_file = os.path.join(tmpdir, "test.ecosystem.pack.json")
            build_out = os.path.join(tmpdir, "repos")

            rc = ecosystem_cli_main(["synthesize", "--pack", "minimal-blog", "--output", pack_file])
            self.assertEqual(rc, 0)

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = ecosystem_cli_main(["build", pack_file, "--out-dir", build_out])
            self.assertEqual(rc, 0)
            output = buf.getvalue()
            self.assertIn("Materialized 3 ecosystem applications", output)

            # Confirm directories were created
            created_dirs = os.listdir(build_out)
            self.assertEqual(len(created_dirs), 3)
            for d in created_dirs:
                git_dir = os.path.join(build_out, d, ".git")
                self.assertTrue(os.path.exists(git_dir), f"Directory {d} missing .git")

    def test_synthesize_with_ai_delta_entities(self) -> None:
        """Synthesized ecosystem surfaces incorporate AI-delta entities."""
        rec = self.registry.recommend("blog-cms", required_targets=("nextjs-web", "backend-python"))
        ai_change = SolutionPackChange(
            change_id="ai-newsletter",
            source=ChangeSource.AI_DELTA,
            operation=ChangeOperation.ADD,
            area=ChangeArea.DATA_MODEL,
            target="entity:Subscriber",
            summary="Add newsletter subscriber entity",
            acceptance_criteria=("Subscribers can be registered",),
        )
        manifest = create_solution_pack_manifest(rec, changes=(ai_change,))
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
            rationale="Adds newsletter subscriber capabilities",
        )
        app_result = apply_solution_pack_manifest(manifest, proposal=proposal, registry=self.registry)
        eco_pkg = synthesize_ecosystem_pack(app_result, registry=self.registry)

        admin_surface = next(s for s in eco_pkg.surfaces if s.surface_kind == "admin_dashboard")
        admin_ir = admin_surface.to_application_ir()
        admin_entities = {e.name for e in admin_ir.entities}
        self.assertIn("Subscriber", admin_entities)
        self.assertIn("Post", admin_entities)
        self.assertIn("Comment", admin_entities)

    def test_parse_ecosystem_pack_missing_keys_fails(self) -> None:
        """Missing required keys fails closed."""
        pack = self.registry.get("minimal-blog")
        eco_pkg = synthesize_ecosystem_pack(pack, registry=self.registry)
        data = eco_pkg.to_dict()
        del data["domain"]

        with self.assertRaisesRegex(SolutionPackError, "missing required keys"):
            parse_ecosystem_pack_package(data)

    def test_parse_ecosystem_pack_unsupported_schema_version_fails(self) -> None:
        """Unsupported schema version fails closed."""
        pack = self.registry.get("minimal-blog")
        eco_pkg = synthesize_ecosystem_pack(pack, registry=self.registry)
        data = eco_pkg.to_dict()
        data["schema_version"] = "99.0"

        with self.assertRaisesRegex(SolutionPackError, "Unsupported ecosystem package schema version"):
            parse_ecosystem_pack_package(data)

    def test_parse_ecosystem_pack_invalid_semver_fails(self) -> None:
        """Invalid semver fails closed."""
        pack = self.registry.get("minimal-blog")
        eco_pkg = synthesize_ecosystem_pack(pack, registry=self.registry)
        data = eco_pkg.to_dict()
        data["version"] = "not-semver"

        with self.assertRaisesRegex(SolutionPackError, "Invalid semver version format"):
            parse_ecosystem_pack_package(data)

    def test_cli_synthesize_unknown_pack_fails(self) -> None:
        """CLI synthesize with unknown pack exits with error code 1."""
        rc = ecosystem_cli_main(["synthesize", "--pack", "unknown-pack"])
        self.assertEqual(rc, 1)

    def test_cli_verify_nonexistent_file_fails(self) -> None:
        """CLI verify with nonexistent file exits with error code 1."""
        rc = ecosystem_cli_main(["verify", "/nonexistent/file.json"])
        self.assertEqual(rc, 1)

    def test_cli_inspect_nonexistent_file_fails(self) -> None:
        """CLI inspect with nonexistent file exits with error code 1."""
        rc = ecosystem_cli_main(["inspect", "/nonexistent/file.json"])
        self.assertEqual(rc, 1)

    def test_cli_build_nonexistent_file_fails(self) -> None:
        """CLI build with nonexistent file exits with error code 1."""
        rc = ecosystem_cli_main(["build", "/nonexistent/file.json", "--out-dir", "/tmp"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()

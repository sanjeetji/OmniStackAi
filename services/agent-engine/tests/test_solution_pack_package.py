"""R-443: Solution Pack packaging, verification, and export CLI tests."""

from __future__ import annotations

import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR, validate_ir
from omnistackai_agent_engine.application_ir.validate import has_errors
from omnistackai_agent_engine.solution_packs import (
    DEFAULT_SOLUTION_PACK_REGISTRY,
    MINIMAL_BLOG_PACK,
    RIDESHARE_FAVOURITES_PACK,
    SolutionPackError,
    SolutionPackRegistry,
)
from omnistackai_agent_engine.solution_packs.package import (
    SolutionPackPackage,
    parse_solution_pack_package,
    verify_package,
)
from omnistackai_agent_engine.solution_packs.package_cli import main as package_cli_main


class SolutionPackPackageTests(TestCase):
    def test_package_from_registered_packs(self) -> None:
        for pack in (MINIMAL_BLOG_PACK, RIDESHARE_FAVOURITES_PACK):
            pkg = SolutionPackPackage.from_solution_pack(pack)
            self.assertEqual(pkg.schema_version, "1.0")
            self.assertEqual(pkg.pack_id, pack.pack_id)
            self.assertEqual(pkg.version, pack.version)
            self.assertEqual(pkg.display_name, pack.display_name)
            self.assertEqual(pkg.description, pack.description)
            self.assertEqual(pkg.domains, pack.domains)
            self.assertEqual(pkg.capabilities, pack.capabilities)
            self.assertEqual(pkg.targets, pack.targets)
            self.assertEqual(pkg.verify_targets, pack.targets)
            self.assertEqual(pkg.ir_sha256, pack.ir_sha256)
            self.assertIsInstance(pkg.ir_dict, dict)
            self.assertIsInstance(pkg.verify_plans, dict)
            self.assertEqual(len(pkg.package_sha256), 64)

            ir = pkg.to_application_ir()
            self.assertIsInstance(ir, ApplicationIR)
            self.assertFalse(has_errors(validate_ir(ir)))

    def test_canonical_json_roundtrip_and_determinism(self) -> None:
        pkg = SolutionPackPackage.from_solution_pack(MINIMAL_BLOG_PACK)
        json_1 = pkg.to_json()
        json_2 = pkg.to_json()
        self.assertEqual(json_1, json_2)

        parsed = parse_solution_pack_package(json_1)
        self.assertEqual(parsed, pkg)
        self.assertEqual(parsed.to_dict(), pkg.to_dict())

    def test_tampered_ir_fails_closed(self) -> None:
        pkg = SolutionPackPackage.from_solution_pack(MINIMAL_BLOG_PACK)
        data = pkg.to_dict()

        # Tamper with IR content and recompute package checksum so package checksum passes
        # but IR digest check catches the tampering
        from omnistackai_agent_engine.solution_packs.package import compute_package_checksum

        ir_dict = dict(data["ir_dict"])  # type: ignore[arg-type]
        ir_dict["name"] = "Tampered Blog Name"
        data["ir_dict"] = ir_dict
        data["package_sha256"] = compute_package_checksum(data)

        with self.assertRaises(SolutionPackError) as ctx:
            parse_solution_pack_package(data)
        self.assertIn("digest", str(ctx.exception).lower())

    def test_tampered_checksum_fails_closed(self) -> None:
        pkg = SolutionPackPackage.from_solution_pack(MINIMAL_BLOG_PACK)
        data = pkg.to_dict()
        data["package_sha256"] = "0" * 64

        with self.assertRaises(SolutionPackError) as ctx:
            parse_solution_pack_package(data)
        self.assertIn("checksum", str(ctx.exception).lower())

    def test_verify_package_function(self) -> None:
        pkg = SolutionPackPackage.from_solution_pack(MINIMAL_BLOG_PACK)
        valid, reason = verify_package(pkg.to_json())
        self.assertTrue(valid)
        self.assertIn("valid", reason.lower())

        # Corrupted payload
        corrupted = pkg.to_dict()
        corrupted["version"] = "not-a-semver"
        valid, reason = verify_package(corrupted)
        self.assertFalse(valid)
        self.assertIn("version", reason.lower())

    def test_register_package_in_registry(self) -> None:
        pkg = SolutionPackPackage.from_solution_pack(MINIMAL_BLOG_PACK)
        empty_reg = SolutionPackRegistry(())
        self.assertIsNone(empty_reg.get(pkg.pack_id, pkg.version))

        updated_reg = empty_reg.register_package(pkg)
        self.assertEqual(len(updated_reg.packs), 1)

        pack = updated_reg.get(pkg.pack_id, pkg.version)
        self.assertIsNotNone(pack)
        assert pack is not None
        self.assertEqual(pack.pack_id, pkg.pack_id)
        self.assertEqual(pack.version, pkg.version)

        # Selectable
        selected = updated_reg.select(
            "blog-cms",
            required_capabilities=("content-publishing",),
            required_targets=pack.targets,
        )
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual(selected.pack_id, pkg.pack_id)

        # Load IR from package-backed pack
        loaded_ir = updated_reg.load_ir(pkg.pack_id, pkg.version)
        self.assertFalse(has_errors(validate_ir(loaded_ir)))


class SolutionPackPackageCliTests(TestCase):
    def test_cli_export_and_inspect_stdout(self) -> None:
        out = StringIO()
        exit_code = package_cli_main(["export", "--pack", "minimal-blog"], stdout=out)
        self.assertEqual(exit_code, 0)
        json_output = out.getvalue()
        self.assertIn('"pack_id": "minimal-blog"', json_output)

        parsed = json.loads(json_output)
        self.assertEqual(parsed["pack_id"], "minimal-blog")

    def test_cli_export_to_file_and_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = str(Path(tmpdir) / "minimal-blog.pack.json")
            exit_code = package_cli_main(
                ["export", "--pack", "minimal-blog", "--output", file_path]
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(Path(file_path).is_file())

            # Verify command
            out = StringIO()
            verify_exit = package_cli_main(["verify", file_path], stdout=out)
            self.assertEqual(verify_exit, 0)
            self.assertIn("verified", out.getvalue().lower())

            # Inspect command
            inspect_out = StringIO()
            inspect_exit = package_cli_main(["inspect", file_path], stdout=inspect_out)
            self.assertEqual(inspect_exit, 0)
            self.assertIn("minimal-blog", inspect_out.getvalue())
            self.assertIn("1.0.0", inspect_out.getvalue())

    def test_cli_verify_corrupted_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = str(Path(tmpdir) / "corrupted.pack.json")
            Path(file_path).write_text('{"pack_id": "minimal-blog"}', encoding="utf-8")

            out = StringIO()
            err = StringIO()
            verify_exit = package_cli_main(["verify", file_path], stdout=out, stderr=err)
            self.assertEqual(verify_exit, 1)
            self.assertIn("invalid", (err.getvalue() + out.getvalue()).lower())

    def test_cli_export_unknown_pack_fails(self) -> None:
        err = StringIO()
        exit_code = package_cli_main(["export", "--pack", "unknown-pack"], stderr=err)
        self.assertEqual(exit_code, 1)
        self.assertIn("unknown solution pack", err.getvalue().lower())

    def test_cli_verify_nonexistent_file_fails(self) -> None:
        err = StringIO()
        exit_code = package_cli_main(["verify", "/non/existent/file.pack.json"], stderr=err)
        self.assertEqual(exit_code, 1)
        self.assertIn("does not exist", err.getvalue().lower())

    def test_cli_inspect_nonexistent_file_fails(self) -> None:
        err = StringIO()
        exit_code = package_cli_main(["inspect", "/non/existent/file.pack.json"], stderr=err)
        self.assertEqual(exit_code, 1)
        self.assertIn("does not exist", err.getvalue().lower())

    def test_parse_missing_keys_fails(self) -> None:
        with self.assertRaises(SolutionPackError) as ctx:
            parse_solution_pack_package({"pack_id": "test"})
        self.assertIn("missing required keys", str(ctx.exception).lower())

    def test_parse_unsupported_schema_version_fails(self) -> None:
        pkg = SolutionPackPackage.from_solution_pack(MINIMAL_BLOG_PACK)
        data = pkg.to_dict()
        data["schema_version"] = "99.0"
        with self.assertRaises(SolutionPackError) as ctx:
            parse_solution_pack_package(data)
        self.assertIn("unsupported package schema version", str(ctx.exception).lower())

    def test_parse_invalid_semver_fails(self) -> None:
        pkg = SolutionPackPackage.from_solution_pack(MINIMAL_BLOG_PACK)
        data = pkg.to_dict()
        data["version"] = "beta"
        with self.assertRaises(SolutionPackError) as ctx:
            parse_solution_pack_package(data)
        self.assertIn("semantic versioning", str(ctx.exception).lower())

    def test_register_package_newest_version_selection(self) -> None:
        pkg1 = SolutionPackPackage.from_solution_pack(MINIMAL_BLOG_PACK)
        data2 = pkg1.to_dict()
        data2["version"] = "1.1.0"
        from omnistackai_agent_engine.solution_packs.package import compute_package_checksum
        data2["package_sha256"] = compute_package_checksum(data2)
        pkg2 = parse_solution_pack_package(data2, verify_integrity=True)

        reg = SolutionPackRegistry(()).register_package(pkg1).register_package(pkg2)
        self.assertEqual(len(reg.packs), 2)
        # Without version specified, should select newest (1.1.0)
        newest = reg.get("minimal-blog")
        self.assertIsNotNone(newest)
        assert newest is not None
        self.assertEqual(newest.version, "1.1.0")

        # Querying exact 1.0.0 returns 1.0.0
        v1 = reg.get("minimal-blog", "1.0.0")
        self.assertIsNotNone(v1)
        assert v1 is not None
        self.assertEqual(v1.version, "1.0.0")


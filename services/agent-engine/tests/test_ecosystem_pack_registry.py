"""Unit tests for EcosystemPack, EcosystemPackRegistry, and catalog CLI (R-445).

Deterministic and offline: tests registry querying, dynamic registration, surface IR loading,
and CLI catalog output with 0 model calls and 0 network requests.
"""

from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from omnistackai_agent_engine.application_ir import ApplicationIR, validate_ir
from omnistackai_agent_engine.solution_packs import (
    DEFAULT_ECOSYSTEM_PACK_REGISTRY,
    EcosystemPack,
    EcosystemPackPackage,
    EcosystemPackRecommendation,
    EcosystemPackRegistry,
    SolutionPackError,
    synthesize_ecosystem_pack,
)
from omnistackai_agent_engine.solution_packs.ecosystem_cli import build_parser, run_catalog


class TestEcosystemPackRegistry(unittest.TestCase):
    def test_default_ecosystem_registry_contains_baselines(self) -> None:
        registry = DEFAULT_ECOSYSTEM_PACK_REGISTRY
        packs = registry.list_packs()
        self.assertGreaterEqual(len(packs), 2)
        pack_ids = [p.ecosystem_id for p in packs]
        self.assertIn("minimal-blog-ecosystem", pack_ids)
        self.assertIn("rideshare-favourites-ecosystem", pack_ids)

    def test_get_exact_and_newest(self) -> None:
        registry = DEFAULT_ECOSYSTEM_PACK_REGISTRY
        pack = registry.get("minimal-blog-ecosystem")
        self.assertIsNotNone(pack)
        self.assertEqual(pack.ecosystem_id, "minimal-blog-ecosystem")
        self.assertEqual(pack.version, "1.0.0")
        self.assertEqual(pack.domain, "blog-cms")
        self.assertEqual(pack.base_pack_id, "minimal-blog")
        self.assertEqual(pack.surface_count, 3)

        # Exact version
        pack_v1 = registry.get("minimal-blog-ecosystem", version="1.0.0")
        self.assertIsNotNone(pack_v1)
        self.assertEqual(pack_v1.version, "1.0.0")

        # Unknown pack
        self.assertIsNone(registry.get("unknown-ecosystem"))
        # Unknown version
        self.assertIsNone(registry.get("minimal-blog-ecosystem", version="9.9.9"))

    def test_select_by_domain_and_surfaces(self) -> None:
        registry = DEFAULT_ECOSYSTEM_PACK_REGISTRY
        pack = registry.select("blog-cms")
        self.assertIsNotNone(pack)
        self.assertEqual(pack.ecosystem_id, "minimal-blog-ecosystem")

        pack_rs = registry.select("rideshare")
        self.assertIsNotNone(pack_rs)
        self.assertEqual(pack_rs.ecosystem_id, "rideshare-favourites-ecosystem")

        # Select with required surfaces
        pack_matched = registry.select("blog-cms", required_surfaces=("provider_portal", "admin_dashboard"))
        self.assertIsNotNone(pack_matched)

        # Unsupported domain
        self.assertIsNone(registry.select("space-mining"))

    def test_recommend_ecosystem(self) -> None:
        registry = DEFAULT_ECOSYSTEM_PACK_REGISTRY
        rec = registry.recommend("blog-cms")
        self.assertIsInstance(rec, EcosystemPackRecommendation)
        self.assertEqual(rec.status, "selected")
        self.assertIsNotNone(rec.ecosystem)
        self.assertEqual(rec.ecosystem.ecosystem_id, "minimal-blog-ecosystem")

        d = rec.to_dict()
        self.assertEqual(d["status"], "selected")
        self.assertEqual(d["domain"], "blog-cms")
        self.assertEqual(d["ecosystem"]["ecosystem_id"], "minimal-blog-ecosystem")

        # No match
        rec_miss = registry.recommend("quantum-computing")
        self.assertEqual(rec_miss.status, "no-exact-match")
        self.assertIsNone(rec_miss.ecosystem)

    def test_load_surface_ir(self) -> None:
        registry = DEFAULT_ECOSYSTEM_PACK_REGISTRY
        ir = registry.load_surface_ir("minimal-blog-ecosystem", "author-studio")
        self.assertIsInstance(ir, ApplicationIR)
        self.assertEqual(ir.name, "Author Studio")
        # Validate that ApplicationIR is clean
        val_errors = validate_ir(ir)
        self.assertEqual(len(val_errors), 0, f"Validation errors: {val_errors}")

        # Test loading by surface_kind
        ir_kind = registry.load_surface_ir("minimal-blog-ecosystem", "admin_dashboard")
        self.assertIsInstance(ir_kind, ApplicationIR)
        self.assertEqual(ir_kind.name, "CMS Admin")

        # Unknown surface
        with self.assertRaises(SolutionPackError):
            registry.load_surface_ir("minimal-blog-ecosystem", "nonexistent-surface")

    def test_register_package_dynamic(self) -> None:
        registry = DEFAULT_ECOSYSTEM_PACK_REGISTRY
        initial_count = len(registry.list_packs())

        # Synthesize a package to register
        pkg = synthesize_ecosystem_pack("minimal-blog", registry=None)
        # Modify version to 2.0.0
        pkg_dict = pkg.to_dict()
        pkg_dict["version"] = "2.0.0"
        from omnistackai_agent_engine.solution_packs.ecosystem_pack import (
            compute_ecosystem_checksum,
            parse_ecosystem_pack_package,
        )
        pkg_dict["package_sha256"] = compute_ecosystem_checksum(pkg_dict)
        pkg_v2 = parse_ecosystem_pack_package(pkg_dict)

        new_registry = registry.register_package(pkg_v2)
        self.assertEqual(len(new_registry.list_packs()), initial_count + 1)
        # Verify get picks up newest version
        newest = new_registry.get("minimal-blog-ecosystem")
        self.assertIsNotNone(newest)
        self.assertEqual(newest.version, "2.0.0")

    def test_cli_catalog_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["catalog"])
        out = io.StringIO()
        with patch("sys.stdout", out):
            code = run_catalog(args)
        self.assertEqual(code, 0)
        output = out.getvalue()
        self.assertIn("Registered Ecosystem Packs", output)
        self.assertIn("Minimal Blog Ecosystem", output)
        self.assertIn("Rideshare Favourites Ecosystem", output)

    def test_cli_catalog_json_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["catalog", "--json"])
        out = io.StringIO()
        with patch("sys.stdout", out):
            code = run_catalog(args)
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())
        self.assertIn("ecosystems", data)
        self.assertGreaterEqual(len(data["ecosystems"]), 2)
        eco_ids = [e["ecosystem_id"] for e in data["ecosystems"]]
        self.assertIn("minimal-blog-ecosystem", eco_ids)


if __name__ == "__main__":
    unittest.main()

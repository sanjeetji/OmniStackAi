"""Tests for Ecosystem Multi-Surface Documentation, Architecture Runbooks, and OpenAPI Aggregator Contracts (R-459)."""

from __future__ import annotations

import concurrent.futures
import contextlib
import io
import json
import unittest
import unittest.mock
import urllib.request
from typing import Any

from omnistackai_agent_engine.solution_packs.ecosystem_docs import (
    DocPage,
    RunbookStep,
    ArchitectureRunbook,
    OpenAPIRoute,
    OpenAPIAggregationEntry,
    AggregatedAPISpec,
    EcosystemDocsContract,
    EcosystemDocsEngine,
    synthesize_ecosystem_docs,
)
from omnistackai_agent_engine.solution_packs.ecosystem_pack import (
    EcosystemPackPackage,
    synthesize_ecosystem_pack,
    parse_ecosystem_pack_package,
    verify_ecosystem_pack,
)
from omnistackai_agent_engine.solution_packs.ecosystem_registry import (
    DEFAULT_ECOSYSTEM_PACK_REGISTRY,
    EcosystemPack,
)
from omnistackai_agent_engine.solution_packs.ecosystem_cli import build_parser, main as cli_main
from omnistackai_agent_engine.solution_packs.registry import DEFAULT_SOLUTION_PACK_REGISTRY
from omnistackai_agent_engine.studio.preview import StudioPreviewManager
from omnistackai_agent_engine.studio.server import create_studio_server
from omnistackai_agent_engine.studio.page import STUDIO_HTML


class TestEcosystemDocsModels(unittest.TestCase):
    """Test dataclass serialization, deserialization, and deterministic digest generation."""

    def test_doc_page_roundtrip(self) -> None:
        page = DocPage(
            page_id="page-1",
            surface_slug="web",
            title="Frontend Architecture",
            slug="frontend-architecture",
            category="architecture",
            content_markdown="# Frontend Architecture\nDetails here.",
            order=1,
            tags=("web", "react"),
        )
        d = page.to_dict()
        self.assertEqual(d["page_id"], "page-1")
        self.assertEqual(d["surface_slug"], "web")
        self.assertEqual(d["category"], "architecture")

        rebuilt = DocPage.from_dict(d)
        self.assertEqual(rebuilt, page)

    def test_runbook_step_and_architecture_runbook_roundtrip(self) -> None:
        step = RunbookStep(
            step_id="step-1",
            order=1,
            title="Initialize Database",
            command="docker compose up -d db",
            description="Spin up PostgreSQL container",
            verification="pg_isready returns 0",
            is_automated=True,
        )
        rb = ArchitectureRunbook(
            runbook_id="rb-deploy",
            surface_slug="_ecosystem",
            title="Deployment Runbook",
            summary="Steps to deploy ecosystem.",
            prerequisites=("Docker", "Git"),
            steps=(step,),
            target_role="devops",
            estimated_minutes=20,
            tags=("deploy", "prod"),
        )
        d = rb.to_dict()
        self.assertEqual(d["runbook_id"], "rb-deploy")
        self.assertEqual(len(d["steps"]), 1)
        self.assertEqual(d["steps"][0]["command"], "docker compose up -d db")

        rebuilt = ArchitectureRunbook.from_dict(d)
        self.assertEqual(rebuilt, rb)

    def test_openapi_models_roundtrip(self) -> None:
        route = OpenAPIRoute(
            path="/api/v1/items",
            method="GET",
            summary="List items",
            operation_id="list_items",
            surface_slug="api",
            tags=("items",),
            parameters=({"name": "limit", "in": "query", "schema": {"type": "integer"}},),
            responses={"200": {"description": "OK"}},
        )
        entry = OpenAPIAggregationEntry(
            surface_slug="api",
            surface_kind="backend_api",
            base_path="/api",
            title="API Spec",
            version="1.0.0",
            endpoints_count=1,
            routes=(route,),
            spec_hash="abc123hash",
        )
        d = entry.to_dict()
        self.assertEqual(d["surface_slug"], "api")
        self.assertEqual(len(d["routes"]), 1)

        rebuilt = OpenAPIAggregationEntry.from_dict(d)
        self.assertEqual(rebuilt, entry)

    def test_ecosystem_docs_contract_roundtrip_and_digest(self) -> None:
        page = DocPage(
            page_id="p1",
            surface_slug="_ecosystem",
            title="Overview",
            slug="overview",
            category="overview",
            content_markdown="# Overview",
            order=1,
        )
        rb = ArchitectureRunbook(
            runbook_id="rb1",
            surface_slug="_ecosystem",
            title="Setup",
            summary="Setup guide",
            steps=(),
        )
        contract = EcosystemDocsContract(
            ecosystem_id="test-eco",
            version="1.0.0",
            pages=(page,),
            runbooks=(rb,),
            entries=(),
            generated_at="2026-09-15T00:00:00Z",
        )
        d = contract.to_dict()
        digest1 = contract.digest()
        self.assertIsInstance(digest1, str)
        self.assertEqual(len(digest1), 64)

        json_str = contract.to_json()
        rebuilt = EcosystemDocsContract.from_json(json_str)
        self.assertEqual(rebuilt.digest(), digest1)
        self.assertEqual(rebuilt.ecosystem_id, "test-eco")


class TestEcosystemDocsSynthesis(unittest.TestCase):
    """Test synthesis derivation across multi-surface topologies."""

    def test_synthesize_ecosystem_docs_derivation(self) -> None:
        surfaces = [
            {"slug": "customer-web", "surface_kind": "customer_web"},
            {"slug": "backend-api", "surface_kind": "backend_api"},
            {"slug": "admin-portal", "surface_kind": "admin_portal"},
        ]
        contract = synthesize_ecosystem_docs("shop-eco", surfaces, version="1.0.0")
        self.assertEqual(contract.ecosystem_id, "shop-eco")
        self.assertTrue(len(contract.pages) >= 6)
        self.assertTrue(len(contract.runbooks) >= 3)
        self.assertEqual(len(contract.entries), 3)
        self.assertIsNotNone(contract.aggregated_api)
        assert contract.aggregated_api is not None
        self.assertGreater(contract.aggregated_api.total_endpoints, 0)

        slugs = [p.slug for p in contract.pages]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_ecosystem_docs_multi_surface_kinds(self) -> None:
        surfaces = [
            {"slug": "web", "surface_kind": "customer_web"},
            {"slug": "api", "surface_kind": "backend_api"},
            {"slug": "admin", "surface_kind": "admin_portal"},
            {"slug": "worker", "surface_kind": "async_worker"},
            {"slug": "db", "surface_kind": "database"},
        ]
        contract = synthesize_ecosystem_docs("complex-eco", surfaces)
        self.assertEqual(len(contract.pages), 3 + 5)
        self.assertEqual(len(contract.entries), 5)
        self.assertIsNotNone(contract.aggregated_api)
        assert contract.aggregated_api is not None
        self.assertGreater(contract.aggregated_api.total_endpoints, 5)


class TestEcosystemDocsEngine(unittest.TestCase):
    """Test documentation engine bundle rendering, search, OpenAPI generation, and export simulation."""

    def setUp(self) -> None:
        self.surfaces = [
            {"slug": "web", "surface_kind": "customer_web"},
            {"slug": "api", "surface_kind": "backend_api"},
        ]
        self.contract = synthesize_ecosystem_docs("test-eco", self.surfaces, version="1.0.0")
        self.engine = EcosystemDocsEngine(self.contract)

    def test_render_markdown_bundle(self) -> None:
        bundle = self.engine.render_markdown_bundle(include_runbooks=True, include_api=True)
        self.assertIn("# Test Eco Documentation Bundle", bundle)
        self.assertIn("## Table of Contents", bundle)
        self.assertIn("Overview", bundle)
        self.assertIn("Runbook:", bundle)
        self.assertIn("# Aggregated OpenAPI 3.1 Reference", bundle)

    def test_search_documentation(self) -> None:
        results = self.engine.search_documentation("architecture")
        self.assertGreater(len(results), 0)
        self.assertTrue(any(r["kind"] == "doc_page" for r in results))

        results_rb = self.engine.search_documentation("deployment")
        self.assertGreater(len(results_rb), 0)

        results_api = self.engine.search_documentation("health")
        self.assertGreater(len(results_api), 0)
        self.assertTrue(any(r["kind"] == "api_route" for r in results_api))

    def test_search_edge_cases(self) -> None:
        self.assertEqual(self.engine.search_documentation(""), [])
        self.assertEqual(self.engine.search_documentation("   "), [])
        self.assertEqual(self.engine.search_documentation("nonexistentxyz123"), [])

        arch_matches = self.engine.search_documentation("architecture", category="architecture")
        for m in arch_matches:
            self.assertEqual(m["category"], "architecture")

    def test_openapi_and_export_simulation(self) -> None:
        raw_openapi = self.engine.get_aggregated_openapi(format="json")
        parsed = json.loads(str(raw_openapi))
        self.assertEqual(parsed["openapi"], "3.1.0")
        self.assertIn("/api/api/health/live", parsed["paths"])

        md_sim = self.engine.simulate_documentation_export("markdown")
        self.assertEqual(md_sim["status"], "success")
        self.assertGreater(md_sim["file_count"], 1)
        self.assertGreater(md_sim["total_bytes"], 0)

        json_sim = self.engine.simulate_documentation_export("json")
        self.assertEqual(json_sim["status"], "success")

        api_sim = self.engine.simulate_documentation_export("openapi_bundle")
        self.assertEqual(api_sim["status"], "success")

        rb_sim = self.engine.simulate_documentation_export("runbook_checklist")
        self.assertEqual(rb_sim["status"], "success")

    def test_invalid_export_format(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.simulate_documentation_export("invalid_format_xyz")  # type: ignore[arg-type]

    def test_concurrent_thread_safety(self) -> None:
        def worker(i: int) -> bool:
            bundle = self.engine.render_markdown_bundle()
            search_res = self.engine.search_documentation("architecture")
            exp_res = self.engine.simulate_documentation_export("json")
            return len(bundle) > 0 and len(search_res) > 0 and exp_res["status"] == "success"

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            futures = [ex.submit(worker, i) for i in range(20)]
            results = [f.result() for f in futures]
        self.assertTrue(all(results))


class TestEcosystemDocsPackagingAndRegistry(unittest.TestCase):
    """Test package bundling, integrity verification, and registry discovery."""

    def test_ecosystem_pack_package_bundling(self) -> None:
        pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        self.assertIsNotNone(pack)
        assert pack is not None

        pkg = synthesize_ecosystem_pack(pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)
        self.assertIsNotNone(pkg.docs_contract)
        assert pkg.docs_contract is not None
        self.assertGreater(len(pkg.docs_contract.pages), 0)
        self.assertGreater(len(pkg.docs_contract.runbooks), 0)

        is_valid, diags = verify_ecosystem_pack(pkg)
        self.assertTrue(is_valid)
        self.assertEqual(len(diags), 0)

        data = pkg.to_dict()
        self.assertIn("docs_contract", data)
        rebuilt_pkg = parse_ecosystem_pack_package(data)
        self.assertIsNotNone(rebuilt_pkg.docs_contract)
        self.assertEqual(rebuilt_pkg.package_sha256, pkg.package_sha256)

    def test_registry_docs_contract(self) -> None:
        eco = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get("minimal-blog-ecosystem")
        self.assertIsNotNone(eco)
        assert eco is not None
        self.assertIsNotNone(eco.docs_contract)
        assert eco.docs_contract is not None
        self.assertGreater(len(eco.docs_contract.pages), 0)

        contract_from_reg = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_docs_contract("minimal-blog-ecosystem")
        self.assertIsNotNone(contract_from_reg)
        self.assertEqual(contract_from_reg.ecosystem_id, "minimal-blog-ecosystem")

    def test_tampered_docs_contract_detection(self) -> None:
        pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        self.assertIsNotNone(pack)
        assert pack is not None
        pkg = synthesize_ecosystem_pack(pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)

        data = pkg.to_dict()
        data["docs_contract"]["pages"][0]["content_markdown"] = "Tampered content"

        is_valid, diags = verify_ecosystem_pack(data)
        self.assertFalse(is_valid)
        self.assertTrue(any("checksum" in d.lower() or "mismatch" in d.lower() for d in diags))


class TestStudioDocsIntegration(unittest.TestCase):
    """Test Studio preview manager, HTTP server endpoints, and UI page."""

    def test_preview_manager_docs_integration(self) -> None:
        manager = StudioPreviewManager(start_fn=lambda *a, **kw: unittest.mock.MagicMock())
        surfaces = [
            {"slug": "web", "app_name": "Web App", "surface_kind": "customer_web", "target_dir": "/tmp/mock"},
            {"slug": "api", "app_name": "API Service", "surface_kind": "backend_api", "target_dir": "/tmp/mock2"},
        ]
        status = manager.replace_ecosystem("test-studio-docs", surfaces)
        self.assertTrue(status["has_docs"])
        self.assertGreater(status["page_count"], 0)
        self.assertGreater(status["runbook_count"], 0)
        self.assertGreater(status["api_endpoint_count"], 0)

        docs_info = manager.get_ecosystem_docs()
        self.assertTrue(docs_info["is_ecosystem"])
        self.assertEqual(docs_info["status"], "ok")
        self.assertGreater(docs_info["page_count"], 0)
        self.assertGreater(docs_info["runbook_count"], 0)
        self.assertGreater(docs_info["api_endpoint_count"], 0)

        export_res = manager.export_ecosystem_docs({"format": "markdown"})
        self.assertEqual(export_res["status"], "ok")
        self.assertGreater(export_res["file_count"], 0)

    def test_studio_server_docs_endpoints(self) -> None:
        manager = StudioPreviewManager(start_fn=lambda *a, **kw: unittest.mock.MagicMock())
        surfaces = [
            {"slug": "web", "app_name": "Web", "surface_kind": "customer_web", "target_dir": "/tmp"},
        ]
        manager.replace_ecosystem("server-test-docs", surfaces)

        server = create_studio_server(
            build_fn=lambda **kw: {},
            status_fn=manager.status,
            get_ecosystem_docs_fn=manager.get_ecosystem_docs,
            export_ecosystem_docs_fn=manager.export_ecosystem_docs,
            host="127.0.0.1",
            port=0,
        )
        port = server.server_address[1]

        import threading
        t = threading.Thread(target=server.serve_forever)
        t.daemon = True
        t.start()

        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ecosystem/docs") as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data["status"], "ok")
                self.assertGreater(data["page_count"], 0)

            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/ecosystem/docs/export",
                data=json.dumps({"format": "json"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                res_data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(res_data["status"], "ok")
                self.assertEqual(res_data["export_format"], "json")
        finally:
            server.shutdown()
            server.server_close()

    def test_studio_page_zero_external_requests_and_docs_elements(self) -> None:
        html = STUDIO_HTML
        self.assertIn("preview-docs-info", html)
        self.assertIn("docs-page-count", html)
        self.assertIn("docs-runbook-count", html)
        self.assertIn("docs-endpoint-count", html)
        self.assertIn("docs-export-btn", html)
        self.assertIn("docs-refresh-btn", html)

        self.assertTrue("http://" not in html and "https://" not in html)


class TestEcosystemDocsCLI(unittest.TestCase):
    """Test CLI docs subcommand."""

    def test_cli_docs_text_format(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = cli_main(["docs", "minimal-blog-ecosystem"])
        self.assertEqual(ret, 0)
        out = buf.getvalue()
        self.assertIn("Documentation Contract: Minimal Blog Ecosystem", out)
        self.assertIn("Doc Pages", out)
        self.assertIn("Operational Runbooks", out)
        self.assertIn("Aggregated OpenAPI", out)

    def test_cli_docs_json_format(self) -> None:
        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            ret = cli_main(["docs", "minimal-blog-ecosystem", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf_json.getvalue())
        self.assertEqual(data["ecosystem_id"], "minimal-blog-ecosystem")
        self.assertIn("pages", data)

    def test_cli_docs_search(self) -> None:
        buf_search = io.StringIO()
        with contextlib.redirect_stdout(buf_search):
            ret = cli_main(["docs", "minimal-blog-ecosystem", "--search", "architecture"])
        self.assertEqual(ret, 0)
        search_out = buf_search.getvalue()
        self.assertIn("Documentation Search ('architecture')", search_out)
        self.assertIn("matches", search_out)

    def test_cli_docs_export(self) -> None:
        buf_exp = io.StringIO()
        with contextlib.redirect_stdout(buf_exp):
            ret = cli_main(["docs", "minimal-blog-ecosystem", "--export", "markdown"])
        self.assertEqual(ret, 0)
        exp_out = buf_exp.getvalue()
        self.assertIn("Documentation Export Simulation (markdown): SUCCESS", exp_out)
        self.assertIn("Total Files:", exp_out)

    def test_cli_docs_error_handling(self) -> None:
        buf = io.StringIO()
        buf_err = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf_err):
            ret = cli_main(["docs", "nonexistent-eco-id-xyz"])
        self.assertEqual(ret, 1)
        self.assertIn("Error:", buf_err.getvalue())


if __name__ == "__main__":
    unittest.main()

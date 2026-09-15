"""Tests for Ecosystem Multi-Surface SLA, SLO, and Error Budget Contracts (R-457)."""

from __future__ import annotations

import concurrent.futures
import io
import json
import unittest
import urllib.request
from contextlib import redirect_stdout
from typing import Any

from omnistackai_agent_engine.solution_packs.ecosystem_sla import (
    EcosystemSLAContract,
    EcosystemSLAEngine,
    ErrorBudget,
    ErrorBudgetBurnReport,
    ServiceLevelAgreement,
    ServiceLevelIndicator,
    ServiceLevelObjective,
    SLASimulationReport,
    SLIEvaluationResult,
    synthesize_ecosystem_sla,
)
from omnistackai_agent_engine.solution_packs.ecosystem_cli import build_parser, main, run_sla
from omnistackai_agent_engine.solution_packs.ecosystem_pack import (
    EcosystemPackPackage,
    parse_ecosystem_pack_package,
    synthesize_ecosystem_pack,
)
from omnistackai_agent_engine.solution_packs.ecosystem_registry import (
    DEFAULT_ECOSYSTEM_PACK_REGISTRY,
)
from omnistackai_agent_engine.solution_packs.registry import DEFAULT_SOLUTION_PACK_REGISTRY
from omnistackai_agent_engine.studio.preview import StudioPreviewManager
from omnistackai_agent_engine.studio.server import create_studio_server


class TestEcosystemSLAModels(unittest.TestCase):
    """Test dataclass serialization, deserialization, and deterministic digest generation."""

    def test_service_level_indicator_roundtrip(self) -> None:
        sli = ServiceLevelIndicator(
            sli_id="sli-test-latency",
            surface_slug="api",
            metric_name="p95_latency_ms",
            kind="latency",
            threshold=250.0,
            unit="ms",
            good_events_query="rate(http_requests_good[5m])",
            total_events_query="rate(http_requests_total[5m])",
            description="API 95th percentile response time",
            tags=("api", "latency"),
        )
        d = sli.to_dict()
        restored = ServiceLevelIndicator.from_dict(d)
        self.assertEqual(restored.sli_id, "sli-test-latency")
        self.assertEqual(restored.surface_slug, "api")
        self.assertEqual(restored.metric_name, "p95_latency_ms")
        self.assertEqual(restored.kind, "latency")
        self.assertEqual(restored.threshold, 250.0)
        self.assertEqual(restored.unit, "ms")
        self.assertEqual(restored.tags, ("api", "latency"))

    def test_service_level_objective_roundtrip(self) -> None:
        slo = ServiceLevelObjective(
            slo_id="slo-test-availability",
            name="Web 99.9% Uptime",
            surface_slug="web",
            sli_id="sli-test-avail",
            target_percentage=99.9,
            rolling_window_days=30,
            budgeting_method="timeslice",
            warning_threshold_pct=99.95,
            tier="critical",
            tags=("web", "uptime"),
        )
        d = slo.to_dict()
        restored = ServiceLevelObjective.from_dict(d)
        self.assertEqual(restored.slo_id, "slo-test-availability")
        self.assertEqual(restored.name, "Web 99.9% Uptime")
        self.assertEqual(restored.target_percentage, 99.9)
        self.assertEqual(restored.rolling_window_days, 30)
        self.assertEqual(restored.tier, "critical")

    def test_error_budget_roundtrip(self) -> None:
        budget = ErrorBudget(
            slo_id="slo-test-availability",
            total_budget_percentage=0.1,
            remaining_budget_percentage=0.085,
            burn_rate_1h=1.2,
            burn_rate_6h=1.1,
            burn_rate_24h=1.0,
            budget_status="healthy",
            consumed_budget_percentage=0.015,
        )
        d = budget.to_dict()
        restored = ErrorBudget.from_dict(d)
        self.assertEqual(restored.slo_id, "slo-test-availability")
        self.assertEqual(restored.total_budget_percentage, 0.1)
        self.assertEqual(restored.remaining_budget_percentage, 0.085)
        self.assertEqual(restored.burn_rate_1h, 1.2)
        self.assertEqual(restored.budget_status, "healthy")

    def test_service_level_agreement_roundtrip(self) -> None:
        sla = ServiceLevelAgreement(
            sla_id="sla-test-enterprise",
            customer_tier="enterprise",
            surface_slug="api",
            availability_target_pct=99.95,
            p95_latency_ms_target=250.0,
            financial_credit_pct=25.0,
            penalty_threshold_pct=99.0,
            description="Enterprise Tier SLA for API",
        )
        d = sla.to_dict()
        restored = ServiceLevelAgreement.from_dict(d)
        self.assertEqual(restored.sla_id, "sla-test-enterprise")
        self.assertEqual(restored.customer_tier, "enterprise")
        self.assertEqual(restored.surface_slug, "api")
        self.assertEqual(restored.availability_target_pct, 99.95)
        self.assertEqual(restored.financial_credit_pct, 25.0)

    def test_ecosystem_sla_contract_roundtrip_and_digest(self) -> None:
        sli = ServiceLevelIndicator(
            sli_id="sli-web-avail",
            surface_slug="web",
            metric_name="http_success_rate_pct",
            kind="availability",
            threshold=99.9,
            unit="%",
            good_events_query="sum(rate(http_success[5m]))",
            total_events_query="sum(rate(http_total[5m]))",
            description="Web availability",
            tags=("web",),
        )
        slo = ServiceLevelObjective(
            slo_id="slo-web-avail",
            name="Web 99.9% Availability",
            surface_slug="web",
            sli_id="sli-web-avail",
            target_percentage=99.9,
            rolling_window_days=30,
            budgeting_method="timeslice",
            warning_threshold_pct=99.95,
            tier="critical",
        )
        eb = ErrorBudget(
            slo_id="slo-web-avail",
            total_budget_percentage=0.1,
            remaining_budget_percentage=0.1,
            burn_rate_1h=1.0,
            burn_rate_6h=1.0,
            burn_rate_24h=1.0,
            budget_status="healthy",
        )
        sla = ServiceLevelAgreement(
            sla_id="sla-web-biz",
            customer_tier="business",
            surface_slug="web",
            availability_target_pct=99.9,
            p95_latency_ms_target=400.0,
            financial_credit_pct=15.0,
            penalty_threshold_pct=98.5,
            description="Business tier SLA",
        )
        contract = EcosystemSLAContract(
            ecosystem_id="test-eco",
            version="1.0.0",
            slis=(sli,),
            slos=(slo,),
            error_budgets=(eb,),
            slas=(sla,),
        )
        d = contract.to_dict()
        restored = EcosystemSLAContract.from_dict(d)
        self.assertEqual(restored.ecosystem_id, "test-eco")
        self.assertEqual(len(restored.slis), 1)
        self.assertEqual(len(restored.slos), 1)
        self.assertEqual(len(restored.error_budgets), 1)
        self.assertEqual(len(restored.slas), 1)
        self.assertEqual(restored.digest(), contract.digest())
        self.assertEqual(len(restored.digest()), 64)


class TestSynthesizeEcosystemSLA(unittest.TestCase):
    """Test automatic deterministic synthesis of SLA contracts."""

    def test_synthesize_default_surfaces(self) -> None:
        surfaces = [
            {"slug": "web", "kind": "customer_web", "app_name": "Web App"},
            {"slug": "api", "kind": "backend_api", "app_name": "API Service"},
            {"slug": "admin", "kind": "admin_portal", "app_name": "Admin Portal"},
        ]
        contract = synthesize_ecosystem_sla("synth-eco", surfaces)
        self.assertEqual(contract.ecosystem_id, "synth-eco")
        self.assertTrue(len(contract.slis) >= 6)  # at least availability & latency per surface
        self.assertTrue(len(contract.slos) >= 3)
        self.assertTrue(len(contract.error_budgets) >= 3)
        self.assertTrue(len(contract.slas) >= 2)

        # Verify deterministic digest
        contract_2 = synthesize_ecosystem_sla("synth-eco", surfaces)
        self.assertEqual(contract.digest(), contract_2.digest())


class TestEcosystemSLAEngine(unittest.TestCase):
    """Test thread-safe in-process evaluation and simulation engine."""

    def setUp(self) -> None:
        surfaces = [
            {"slug": "web", "kind": "customer_web"},
            {"slug": "api", "kind": "backend_api"},
        ]
        self.contract = synthesize_ecosystem_sla("test-eco", surfaces)
        self.engine = EcosystemSLAEngine(self.contract)

    def test_evaluate_sli_metrics_healthy(self) -> None:
        metrics = {
            "web:edge_uptime_pct": 99.98,
            "web:lcp_duration_ms": 1800.0,
            "api:http_success_rate_pct": 99.99,
            "api:p95_latency_ms": 110.0,
        }
        evals = self.engine.evaluate_sli_metrics(metrics)
        for ev in evals:
            self.assertTrue(ev.is_good)

    def test_evaluate_sli_metrics_violation(self) -> None:
        metrics = {
            "api:p95_latency_ms": 750.0,  # exceeds target threshold
        }
        evals = self.engine.evaluate_sli_metrics(metrics)
        latency_eval = next(ev for ev in evals if "latency" in ev.sli_id and ev.surface_slug == "api")
        self.assertFalse(latency_eval.is_good)

    def test_calculate_error_budget_burn(self) -> None:
        slo = self.contract.slos[0]
        burn_report = self.engine.calculate_error_budget_burn(slo.slo_id, error_rate_pct=0.05, time_window_hours=1.0)
        self.assertIsInstance(burn_report, ErrorBudgetBurnReport)
        self.assertEqual(burn_report.slo_id, slo.slo_id)
        self.assertIn(burn_report.status, ("healthy", "warning", "exhausted"))
        self.assertGreaterEqual(burn_report.remaining_pct, 0.0)

    def test_simulate_sla_compliance_normal(self) -> None:
        rep = self.engine.simulate_sla_compliance(scenario="normal_operations")
        self.assertIsInstance(rep, SLASimulationReport)
        self.assertEqual(rep.scenario, "normal_operations")
        self.assertEqual(rep.status, "compliant")
        self.assertEqual(rep.total_financial_credit_pct, 0.0)

    def test_simulate_sla_compliance_minor_degradation(self) -> None:
        rep = self.engine.simulate_sla_compliance(scenario="minor_degradation")
        self.assertEqual(rep.scenario, "minor_degradation")
        self.assertIn(rep.status, ("at_risk", "compliant"))
        self.assertTrue(len(rep.burn_reports) >= 1)

    def test_simulate_sla_compliance_severe_outage(self) -> None:
        rep = self.engine.simulate_sla_compliance(scenario="severe_outage")
        self.assertEqual(rep.scenario, "severe_outage")
        self.assertEqual(rep.status, "breached")
        self.assertGreater(rep.total_financial_credit_pct, 0.0)
        self.assertTrue(len(rep.breached_slas) >= 1)

    def test_simulate_sla_compliance_budget_exhaustion(self) -> None:
        rep = self.engine.simulate_sla_compliance(scenario="budget_exhaustion")
        self.assertEqual(rep.scenario, "budget_exhaustion")
        self.assertEqual(rep.status, "breached")
        self.assertTrue(any(b.status == "exhausted" for b in rep.burn_reports))

    def test_thread_safe_concurrent_simulations(self) -> None:
        scenarios = ["normal_operations", "minor_degradation", "severe_outage", "budget_exhaustion"]

        def run_sim(idx: int) -> SLASimulationReport:
            return self.engine.simulate_sla_compliance(scenarios[idx % len(scenarios)])

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(run_sim, i) for i in range(16)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 16)
        for r in results:
            self.assertIsInstance(r, SLASimulationReport)


class TestEcosystemPackBundlingSLA(unittest.TestCase):
    """Test ecosystem pack package bundling and whole-package digest integrity with SLA."""

    def test_ecosystem_pack_with_sla(self) -> None:
        mb_pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        self.assertIsNotNone(mb_pack)
        pack = synthesize_ecosystem_pack(mb_pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)
        self.assertIsNotNone(pack.sla_contract)
        self.assertIsInstance(pack.sla_contract, EcosystemSLAContract)
        self.assertEqual(pack.sla_contract.ecosystem_id, pack.ecosystem_id)

        d = pack.to_dict()
        self.assertIn("sla_contract", d)
        parsed = parse_ecosystem_pack_package(d)
        self.assertIsNotNone(parsed.sla_contract)
        self.assertEqual(parsed.sla_contract.digest(), pack.sla_contract.digest())
        self.assertEqual(parsed.package_sha256, pack.package_sha256)


class TestRegistryGetSLAContract(unittest.TestCase):
    """Test discovery of SLA contracts from ecosystem registry."""

    def test_get_sla_contract_from_registry(self) -> None:
        contract = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_sla_contract("minimal-blog-ecosystem")
        self.assertIsNotNone(contract)
        self.assertIsInstance(contract, EcosystemSLAContract)
        self.assertEqual(contract.ecosystem_id, "minimal-blog-ecosystem")

    def test_get_sla_contract_returns_none_for_unknown(self) -> None:
        contract = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_sla_contract("nonexistent-eco")
        self.assertIsNone(contract)


class TestStudioPreviewManagerSLA(unittest.TestCase):
    """Test StudioPreviewManager SLA integration."""

    def test_preview_manager_ecosystem_sla(self) -> None:
        surfaces = [
            {"slug": "web", "kind": "customer_web", "app_name": "Blog Web"},
            {"slug": "api", "kind": "backend_api", "app_name": "Blog API"},
        ]
        manager = StudioPreviewManager(start_fn=lambda repo, log=None: unittest.mock.MagicMock())
        status = manager.replace_ecosystem("test-eco", surfaces)
        self.assertTrue(status["has_sla"])
        self.assertGreater(status["sli_count"], 0)
        self.assertGreater(status["slo_count"], 0)
        self.assertGreater(status["sla_count"], 0)
        self.assertEqual(status["sla_status"], "configured")

        sla_data = manager.get_ecosystem_sla()
        self.assertTrue(sla_data["is_ecosystem"])
        self.assertEqual(sla_data["status"], "ok")
        self.assertEqual(sla_data["ecosystem_id"], "test-eco")

        sim_res = manager.simulate_ecosystem_sla({"scenario": "normal_operations"})
        self.assertEqual(sim_res["status"], "ok")
        self.assertEqual(sim_res["scenario"], "normal_operations")
        self.assertEqual(sim_res["report"]["status"], "compliant")


class TestStudioServerSLAEndpoints(unittest.TestCase):
    """Test Studio HTTP server endpoints for SLA contract and simulation."""

    def setUp(self) -> None:
        surfaces = [
            {"slug": "web", "kind": "customer_web"},
            {"slug": "api", "kind": "backend_api"},
        ]
        self.contract = synthesize_ecosystem_sla(
            ecosystem_id="studio-sla-eco",
            surfaces=surfaces,
        )
        self.engine = EcosystemSLAEngine(self.contract)

        def get_sla_fn() -> dict[str, Any]:
            return self.contract.to_dict()

        def sim_sla_fn(body: Any = None) -> dict[str, Any]:
            scenario = "normal_operations"
            if isinstance(body, dict):
                scenario = body.get("scenario", "normal_operations")
            return self.engine.simulate_sla_compliance(scenario=scenario).to_dict()

        self.server = create_studio_server(
            lambda prompt, **kw: {"status": "ok"},
            host="127.0.0.1",
            port=0,
            get_ecosystem_sla_fn=get_sla_fn,
            simulate_ecosystem_sla_fn=sim_sla_fn,
        )
        self.server_thread = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.server_thread.submit(self.server.serve_forever)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.shutdown(wait=True)

    def test_get_ecosystem_sla_endpoint(self) -> None:
        req = urllib.request.Request(f"{self.base_url}/api/ecosystem/sla")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["ecosystem_id"], "studio-sla-eco")
            self.assertTrue(len(data["slis"]) >= 1)
            self.assertTrue(len(data["slos"]) >= 1)
            self.assertTrue(len(data["error_budgets"]) >= 1)
            self.assertTrue(len(data["slas"]) >= 1)

    def test_post_ecosystem_sla_simulate_endpoint(self) -> None:
        req = urllib.request.Request(
            f"{self.base_url}/api/ecosystem/sla/simulate",
            data=json.dumps({"scenario": "normal_operations"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("scenario", data)
            self.assertEqual(data["scenario"], "normal_operations")
            self.assertEqual(data["status"], "compliant")
            self.assertTrue(len(data["sli_evaluations"]) >= 1)


class TestEcosystemCLISLA(unittest.TestCase):
    """Test CLI subcommand for SLA."""

    def test_sla_inspect(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["sla", "minimal-blog-ecosystem"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("SLA Contract", output)
        self.assertIn("SLIs", output)
        self.assertIn("SLOs", output)
        self.assertIn("Error Budgets", output)
        self.assertIn("SLAs", output)

    def test_sla_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["sla", "minimal-blog-ecosystem", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["ecosystem_id"], "minimal-blog-ecosystem")
        self.assertTrue(len(data["slis"]) >= 1)

    def test_sla_simulate(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["sla", "minimal-blog-ecosystem", "--simulate", "--scenario", "normal_operations"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("SLA Compliance Simulation (normal_operations)", output)
        self.assertIn("OVERALL STATUS:", output)


if __name__ == "__main__":
    unittest.main()

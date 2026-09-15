"""Tests for Ecosystem Multi-Surface Capacity Planning, Resource Quotas, and Unit Economics Budgeting (R-455)."""

from __future__ import annotations

import concurrent.futures
import io
import json
import unittest
import urllib.request
from contextlib import redirect_stdout
from typing import Any

from omnistackai_agent_engine.solution_packs.ecosystem_capacity import (
    CapacitySimulationReport,
    EcosystemCapacityContract,
    EcosystemCapacityEngine,
    QuotaEvaluationResult,
    ResourceQuota,
    SurfaceCapacityProjection,
    SurfaceCapacitySpec,
    UnitEconomicsCostModel,
    UnitEconomicsReport,
    synthesize_ecosystem_capacity,
)
from omnistackai_agent_engine.solution_packs.ecosystem_cli import build_parser, main, run_capacity
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


class TestEcosystemCapacityModels(unittest.TestCase):
    """Test data class serialization and deserialization."""

    def test_resource_quota_roundtrip(self) -> None:
        quota = ResourceQuota(
            quota_id="quota-api-cpu",
            surface_slug="api",
            resource_kind="cpu_cores",
            limit_value=4.0,
            burst_limit_value=8.0,
            unit="cores",
            enforcement_action="throttle",
        )
        d = quota.to_dict()
        self.assertEqual(d["quota_id"], "quota-api-cpu")
        self.assertEqual(d["limit_value"], 4.0)
        self.assertEqual(d["burst_limit_value"], 8.0)
        self.assertEqual(d["enforcement_action"], "throttle")

        recovered = ResourceQuota.from_dict(d)
        self.assertEqual(recovered, quota)

    def test_surface_capacity_spec_roundtrip(self) -> None:
        spec = SurfaceCapacitySpec(
            surface_slug="customer-web",
            surface_kind="customer_web",
            min_replicas=2,
            max_replicas=10,
            target_cpu_utilization_pct=70,
            target_memory_utilization_pct=75,
            requests_per_replica_limit=500,
            scale_down_stabilization_seconds=300,
        )
        d = spec.to_dict()
        self.assertEqual(d["surface_slug"], "customer-web")
        self.assertEqual(d["min_replicas"], 2)
        self.assertEqual(d["max_replicas"], 10)

        recovered = SurfaceCapacitySpec.from_dict(d)
        self.assertEqual(recovered, spec)

    def test_unit_economics_cost_model_roundtrip(self) -> None:
        cost_model = UnitEconomicsCostModel(
            cost_model_id="cost-api",
            surface_slug="api",
            base_monthly_cost_usd=25.0,
            marginal_cost_per_1k_requests_usd=0.015,
            marginal_cost_per_gb_storage_usd=0.10,
            currency="USD",
            cost_tier="growth",
        )
        d = cost_model.to_dict()
        self.assertEqual(d["cost_model_id"], "cost-api")
        self.assertEqual(d["base_monthly_cost_usd"], 25.0)
        self.assertEqual(d["marginal_cost_per_1k_requests_usd"], 0.015)

        recovered = UnitEconomicsCostModel.from_dict(d)
        self.assertEqual(recovered, cost_model)

    def test_contract_roundtrip_and_digest(self) -> None:
        quota = ResourceQuota(
            quota_id="q-1",
            surface_slug="api",
            resource_kind="requests_per_second",
            limit_value=100.0,
            burst_limit_value=200.0,
            unit="rps",
            enforcement_action="throttle",
        )
        spec = SurfaceCapacitySpec(
            surface_slug="api",
            surface_kind="backend_api",
            min_replicas=1,
            max_replicas=5,
            target_cpu_utilization_pct=80,
            target_memory_utilization_pct=80,
            requests_per_replica_limit=250,
            scale_down_stabilization_seconds=120,
        )
        cost = UnitEconomicsCostModel(
            cost_model_id="c-1",
            surface_slug="api",
            base_monthly_cost_usd=20.0,
            marginal_cost_per_1k_requests_usd=0.01,
            marginal_cost_per_gb_storage_usd=0.05,
            currency="USD",
            cost_tier="starter",
        )
        contract = EcosystemCapacityContract(
            ecosystem_id="eco-demo",
            version="1.0.0",
            surface_capacities=(spec,),
            resource_quotas=(quota,),
            cost_models=(cost,),
            monthly_budget_limit_usd=500.0,
        )

        d = contract.to_dict()
        recovered = EcosystemCapacityContract.from_dict(d)
        self.assertEqual(recovered, contract)

        json_str = contract.to_json()
        from_json_contract = EcosystemCapacityContract.from_json(json_str)
        self.assertEqual(from_json_contract, contract)

        digest1 = contract.digest()
        digest2 = contract.digest()
        self.assertEqual(digest1, digest2)
        self.assertEqual(len(digest1), 64)


class TestEcosystemCapacitySynthesis(unittest.TestCase):
    """Test synthesis of capacity contracts from ecosystem surfaces."""

    def test_synthesize_multi_surface(self) -> None:
        surfaces = [
            {"slug": "web", "kind": "customer_web"},
            {"slug": "api", "kind": "backend_api"},
            {"slug": "database", "kind": "postgres"},
        ]
        contract = synthesize_ecosystem_capacity(
            ecosystem_id="eco-store",
            surfaces=surfaces,
            version="1.0.0",
            monthly_budget_limit_usd=750.0,
        )

        self.assertEqual(contract.ecosystem_id, "eco-store")
        self.assertEqual(contract.version, "1.0.0")
        self.assertEqual(contract.monthly_budget_limit_usd, 750.0)

        # Must have capacity spec for each surface
        spec_slugs = {s.surface_slug for s in contract.surface_capacities}
        self.assertIn("web", spec_slugs)
        self.assertIn("api", spec_slugs)
        self.assertIn("database", spec_slugs)

        # Database should have min_replicas=1 and max_replicas=1
        db_spec = next(s for s in contract.surface_capacities if s.surface_slug == "database")
        self.assertEqual(db_spec.min_replicas, 1)
        self.assertEqual(db_spec.max_replicas, 1)

        # Must have quotas (CPU, memory, requests/rps)
        quota_slugs = {q.surface_slug for q in contract.resource_quotas}
        self.assertIn("api", quota_slugs)
        self.assertIn("database", quota_slugs)

        # Must have cost models
        cost_slugs = {c.surface_slug for c in contract.cost_models}
        self.assertIn("api", cost_slugs)
        self.assertIn("database", cost_slugs)

    def test_synthesize_empty_surfaces_fallback(self) -> None:
        contract = synthesize_ecosystem_capacity(
            ecosystem_id="eco-empty",
            surfaces=[],
        )
        self.assertEqual(contract.ecosystem_id, "eco-empty")
        self.assertGreater(len(contract.surface_capacities), 0)
        self.assertGreater(len(contract.resource_quotas), 0)
        self.assertGreater(len(contract.cost_models), 0)


class TestEcosystemCapacityEngine(unittest.TestCase):
    """Test the in-process deterministic simulation engine."""

    def setUp(self) -> None:
        surfaces = [
            {"slug": "web", "kind": "customer_web"},
            {"slug": "api", "kind": "backend_api"},
            {"slug": "database", "kind": "postgres"},
        ]
        self.contract = synthesize_ecosystem_capacity(
            ecosystem_id="eco-sim",
            surfaces=surfaces,
            monthly_budget_limit_usd=200.0,
        )
        self.engine = EcosystemCapacityEngine(self.contract)

    def test_simulate_workload_tier_base(self) -> None:
        report = self.engine.simulate_workload_tier(tier="base", monthly_requests=50_000)
        self.assertIsInstance(report, CapacitySimulationReport)
        self.assertEqual(report.tier, "base")
        self.assertEqual(report.total_monthly_requests, 50_000)
        self.assertTrue(report.within_budget)
        self.assertEqual(report.status, "pass")
        self.assertGreater(len(report.surface_projections), 0)

        for proj in report.surface_projections:
            self.assertGreater(proj.required_replicas, 0)
            self.assertGreater(proj.estimated_monthly_cost_usd, 0.0)

    def test_simulate_workload_tier_peak_and_stress(self) -> None:
        peak_report = self.engine.simulate_workload_tier(tier="peak", monthly_requests=200_000)
        self.assertEqual(peak_report.tier, "peak")

        # Stress tier with high request load
        stress_report = self.engine.simulate_workload_tier(tier="stress", monthly_requests=5_000_000)
        self.assertEqual(stress_report.tier, "stress")
        self.assertGreater(stress_report.total_monthly_cost_usd, peak_report.total_monthly_cost_usd)
        if not stress_report.within_budget:
            self.assertIn(stress_report.status, ("warning", "breach"))

    def test_evaluate_quota(self) -> None:
        # Evaluate valid value
        res_ok = self.engine.evaluate_quota(
            surface_slug="api",
            resource_kind="cpu_cores",
            proposed_value=2.0,
        )
        self.assertIsInstance(res_ok, QuotaEvaluationResult)
        self.assertTrue(res_ok.allowed)

        # Evaluate excessive value beyond burst limit
        res_exceeded = self.engine.evaluate_quota(
            surface_slug="api",
            resource_kind="cpu_cores",
            proposed_value=999.0,
        )
        self.assertFalse(res_exceeded.allowed)
        self.assertIn("exceeds", res_exceeded.message.lower())

    def test_estimate_monthly_unit_economics(self) -> None:
        report = self.engine.estimate_monthly_unit_economics(
            monthly_active_users=10_000,
            requests_per_user_monthly=50,
        )
        self.assertIsInstance(report, UnitEconomicsReport)
        self.assertEqual(report.total_requests, 500_000)
        self.assertGreater(report.total_cost_usd, 0.0)
        self.assertGreater(report.cost_per_active_user_usd, 0.0)
        self.assertGreater(report.cost_per_1k_requests_usd, 0.0)


class TestPackCapacityContractIntegration(unittest.TestCase):
    """Test package bundling and serialization with capacity contract."""

    def test_synthesized_pack_has_capacity_contract(self) -> None:
        mb_pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        if mb_pack is None:
            self.skipTest("minimal-blog pack not available")
        pack = synthesize_ecosystem_pack(mb_pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)
        self.assertIsNotNone(pack.capacity_contract)
        self.assertIsInstance(pack.capacity_contract, EcosystemCapacityContract)
        self.assertTrue(len(pack.capacity_contract.surface_capacities) >= 1)
        self.assertTrue(len(pack.capacity_contract.resource_quotas) >= 1)

    def test_pack_json_roundtrip_includes_capacity_contract(self) -> None:
        mb_pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        if mb_pack is None:
            self.skipTest("minimal-blog pack not available")
        pack = synthesize_ecosystem_pack(mb_pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)
        d = pack.to_dict()
        self.assertIn("capacity_contract", d)
        parsed = parse_ecosystem_pack_package(d)
        self.assertIsNotNone(parsed.capacity_contract)
        self.assertEqual(parsed.capacity_contract.digest(), pack.capacity_contract.digest())
        self.assertEqual(parsed.package_sha256, pack.package_sha256)


class TestRegistryGetCapacityContract(unittest.TestCase):
    """Test discovery of capacity contracts from ecosystem registry."""

    def test_get_capacity_contract_from_registry(self) -> None:
        contract = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_capacity_contract("minimal-blog-ecosystem")
        self.assertIsNotNone(contract)
        self.assertIsInstance(contract, EcosystemCapacityContract)
        self.assertEqual(contract.ecosystem_id, "minimal-blog-ecosystem")

    def test_get_capacity_contract_returns_none_for_unknown(self) -> None:
        contract = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_capacity_contract("nonexistent-eco")
        self.assertIsNone(contract)


class TestStudioServerCapacityEndpoints(unittest.TestCase):
    """Test Studio HTTP server endpoints for capacity contract and simulation."""

    def setUp(self) -> None:
        surfaces = [
            {"slug": "web", "kind": "customer_web"},
            {"slug": "api", "kind": "backend_api"},
        ]
        self.contract = synthesize_ecosystem_capacity(
            ecosystem_id="studio-cap-eco",
            surfaces=surfaces,
            monthly_budget_limit_usd=500.0,
        )
        self.engine = EcosystemCapacityEngine(self.contract)

        def get_cap_fn() -> dict[str, Any]:
            return self.contract.to_dict()

        def sim_cap_fn(body: Any = None) -> dict[str, Any]:
            tier = "base"
            if isinstance(body, dict):
                tier = body.get("tier", "base")
            return self.engine.simulate_workload_tier(tier=tier).to_dict()

        self.server = create_studio_server(
            lambda prompt, **kw: {"status": "ok"},
            host="127.0.0.1",
            port=0,
            get_ecosystem_capacity_fn=get_cap_fn,
            simulate_ecosystem_capacity_fn=sim_cap_fn,
        )
        self.server_thread = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.server_thread.submit(self.server.serve_forever)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.shutdown(wait=True)

    def test_get_ecosystem_capacity_endpoint(self) -> None:
        req = urllib.request.Request(f"{self.base_url}/api/ecosystem/capacity")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["ecosystem_id"], "studio-cap-eco")
            self.assertTrue(len(data["surface_capacities"]) >= 1)

    def test_post_ecosystem_capacity_simulate_endpoint(self) -> None:
        req = urllib.request.Request(
            f"{self.base_url}/api/ecosystem/capacity/simulate",
            data=json.dumps({"tier": "base"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("status", data)
            self.assertIn("surface_projections", data)
            self.assertTrue(data["within_budget"])


class TestEcosystemCLICapacity(unittest.TestCase):
    """Test CLI subcommand for capacity."""

    def test_capacity_inspect(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["capacity", "minimal-blog-ecosystem"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("Capacity Contract", output)
        self.assertIn("Surface Capacities", output)
        self.assertIn("Resource Quotas", output)

    def test_capacity_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["capacity", "minimal-blog-ecosystem", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["ecosystem_id"], "minimal-blog-ecosystem")
        self.assertTrue(len(data["surface_capacities"]) >= 1)

    def test_capacity_simulate(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["capacity", "minimal-blog-ecosystem", "--simulate", "--tier", "peak"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("Capacity Planning Simulation", output)
        self.assertIn("peak", output)
        self.assertIn("OVERALL STATUS:", output)


if __name__ == "__main__":
    unittest.main()

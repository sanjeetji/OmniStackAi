"""Tests for Ecosystem Multi-Surface Alerting, Incident Runbooks, and Escalation Policies (R-456)."""

from __future__ import annotations

import concurrent.futures
import io
import json
import unittest
import urllib.request
from contextlib import redirect_stdout
from typing import Any

from omnistackai_agent_engine.solution_packs.ecosystem_alerting import (
    AlertRule,
    AlertTriggerResult,
    EcosystemAlertingContract,
    EcosystemAlertingEngine,
    EscalationPolicy,
    EscalationTier,
    IncidentRunbook,
    IncidentSimulationReport,
    RunbookExecutionReport,
    RunbookStep,
    RunbookStepExecution,
    synthesize_ecosystem_alerting,
)
from omnistackai_agent_engine.solution_packs.ecosystem_cli import build_parser, main, run_alerting
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


class TestEcosystemAlertingModels(unittest.TestCase):
    """Test data class serialization and deserialization."""

    def test_alert_rule_roundtrip(self) -> None:
        rule = AlertRule(
            rule_id="rule-test-latency",
            surface_slug="api",
            metric_name="p99_latency_ms",
            condition=">",
            threshold=250.0,
            duration_seconds=60,
            severity="warning",
            description="P99 latency above 250ms",
            runbook_id="rb-test-latency",
            tags=("latency", "api"),
        )
        d = rule.to_dict()
        restored = AlertRule.from_dict(d)
        self.assertEqual(restored.rule_id, "rule-test-latency")
        self.assertEqual(restored.threshold, 250.0)
        self.assertEqual(restored.severity, "warning")
        self.assertEqual(restored.runbook_id, "rb-test-latency")
        self.assertEqual(restored.tags, ("latency", "api"))

    def test_runbook_step_roundtrip(self) -> None:
        step = RunbookStep(
            step_id="step-1",
            order=1,
            action="scale_replicas",
            target="api",
            description="Scale backend pods to handle surge",
            is_automated=True,
            remediation_command="kubectl scale deployment/api --replicas=5",
        )
        d = step.to_dict()
        restored = RunbookStep.from_dict(d)
        self.assertEqual(restored.step_id, "step-1")
        self.assertEqual(restored.order, 1)
        self.assertEqual(restored.action, "scale_replicas")
        self.assertTrue(restored.is_automated)
        self.assertEqual(restored.remediation_command, "kubectl scale deployment/api --replicas=5")

    def test_incident_runbook_roundtrip(self) -> None:
        step1 = RunbookStep(
            step_id="step-1",
            order=1,
            action="inspect_telemetry",
            target="api",
            description="Check for 500 error traces",
            is_automated=True,
        )
        runbook = IncidentRunbook(
            runbook_id="rb-api-errors",
            title="API Error Remediation",
            severity="critical",
            summary="Remediation procedure for HTTP 5xx error spikes",
            steps=(step1,),
            escalation_policy_id="esc-backend",
            tags=("api", "errors"),
        )
        d = runbook.to_dict()
        restored = IncidentRunbook.from_dict(d)
        self.assertEqual(restored.runbook_id, "rb-api-errors")
        self.assertEqual(len(restored.steps), 1)
        self.assertEqual(restored.steps[0].step_id, "step-1")
        self.assertEqual(restored.escalation_policy_id, "esc-backend")

    def test_escalation_policy_roundtrip(self) -> None:
        tier1 = EscalationTier(
            tier=1,
            target_channel="slack-alerts-p0",
            wait_minutes=0,
            auto_action="notify_slack",
        )
        tier2 = EscalationTier(
            tier=2,
            target_channel="pagerduty-primary-oncall",
            wait_minutes=15,
            auto_action="page_oncall",
        )
        policy = EscalationPolicy(
            policy_id="esc-backend",
            name="Backend Escalation Policy",
            description="Multi-tier escalation policy for backend services",
            tiers=(tier1, tier2),
        )
        d = policy.to_dict()
        restored = EscalationPolicy.from_dict(d)
        self.assertEqual(restored.policy_id, "esc-backend")
        self.assertEqual(len(restored.tiers), 2)
        self.assertEqual(restored.tiers[1].wait_minutes, 15)

    def test_alerting_contract_digest_determinism(self) -> None:
        contract1 = synthesize_ecosystem_alerting(
            ecosystem_id="test-digest-eco",
            surfaces=[{"slug": "web", "kind": "customer_web"}],
        )
        contract2 = synthesize_ecosystem_alerting(
            ecosystem_id="test-digest-eco",
            surfaces=[{"slug": "web", "kind": "customer_web"}],
        )
        self.assertEqual(contract1.digest(), contract2.digest())
        self.assertEqual(len(contract1.digest()), 64)

        # Roundtrip to/from dict and JSON
        d = contract1.to_dict()
        restored = EcosystemAlertingContract.from_dict(d)
        self.assertEqual(restored.digest(), contract1.digest())

        raw_json = contract1.to_json()
        restored_json = EcosystemAlertingContract.from_json(raw_json)
        self.assertEqual(restored_json.digest(), contract1.digest())


class TestAlertingSynthesis(unittest.TestCase):
    """Test synthesis of ecosystem alerting contracts."""

    def test_synthesize_minimal_blog(self) -> None:
        surfaces = [
            {"slug": "blog_web", "kind": "customer_web"},
            {"slug": "blog_api", "kind": "backend_api"},
            {"slug": "blog_admin", "kind": "admin_portal"},
        ]
        contract = synthesize_ecosystem_alerting(
            ecosystem_id="minimal-blog-ecosystem",
            surfaces=surfaces,
        )
        self.assertEqual(contract.ecosystem_id, "minimal-blog-ecosystem")
        self.assertTrue(len(contract.alert_rules) >= 3)
        self.assertTrue(len(contract.runbooks) >= 2)
        self.assertTrue(len(contract.escalation_policies) >= 2)

        # Verify rule attributes
        rule_ids = [r.rule_id for r in contract.alert_rules]
        self.assertTrue(any("blog_api" in rid for rid in rule_ids))
        self.assertTrue(any("blog_web" in rid for rid in rule_ids))

    def test_synthesize_rideshare(self) -> None:
        surfaces = [
            {"slug": "passenger_mobile", "kind": "mobile_app"},
            {"slug": "driver_mobile", "kind": "mobile_app"},
            {"slug": "dispatch_api", "kind": "backend_api"},
            {"slug": "ops_console", "kind": "operations_dashboard"},
        ]
        contract = synthesize_ecosystem_alerting(
            ecosystem_id="rideshare-favourites-ecosystem",
            surfaces=surfaces,
        )
        self.assertEqual(contract.ecosystem_id, "rideshare-favourites-ecosystem")
        self.assertTrue(len(contract.alert_rules) >= 4)
        self.assertTrue(len(contract.runbooks) >= 3)
        self.assertTrue(len(contract.escalation_policies) >= 2)


class TestEcosystemAlertingEngine(unittest.TestCase):
    """Test evaluation and simulation engine."""

    def setUp(self) -> None:
        surfaces = [
            {"slug": "web", "kind": "customer_web"},
            {"slug": "api", "kind": "backend_api"},
        ]
        self.contract = synthesize_ecosystem_alerting(
            ecosystem_id="engine-test-eco",
            surfaces=surfaces,
        )
        self.engine = EcosystemAlertingEngine(self.contract)

    def test_evaluate_rules_normal(self) -> None:
        # Healthy metrics: low error rate, low latency, normal CPU
        metrics = {
            "api:http_error_rate_pct": 0.05,
            "api:p99_latency_ms": 120.0,
            "web:page_load_p95_ms": 400.0,
        }
        for rule in self.contract.alert_rules:
            val = metrics.get(f"{rule.surface_slug}:{rule.metric_name}", 0.0)
            res = self.engine.evaluate_metric(rule.rule_id, val)
            self.assertFalse(res.is_firing, f"Rule {rule.rule_id} should not be firing with healthy metric")

    def test_evaluate_rules_firing(self) -> None:
        # Spike API error rate to 8.5% (threshold is typically 5.0%)
        error_rule = next(r for r in self.contract.alert_rules if "error" in r.metric_name)
        res = self.engine.evaluate_metric(error_rule.rule_id, 8.5)
        self.assertTrue(res.is_firing)
        self.assertEqual(res.metric_value, 8.5)
        self.assertEqual(res.severity, error_rule.severity)

    def test_dry_run_runbook(self) -> None:
        runbook = self.contract.runbooks[0]
        result = self.engine.dry_run_runbook(runbook.runbook_id)
        self.assertEqual(result.runbook_id, runbook.runbook_id)
        self.assertIn(result.status, ("auto_mitigated", "pending_manual_action"))
        self.assertEqual(len(result.step_executions), len(runbook.steps))
        self.assertEqual(result.total_steps, len(runbook.steps))

    def test_dry_run_unknown_runbook(self) -> None:
        result = self.engine.dry_run_runbook("unknown-rb-id")
        self.assertEqual(result.total_steps, 0)
        self.assertIn("not found", result.summary)

    def test_simulate_incident_api_spike(self) -> None:
        sim = self.engine.simulate_incident("api_error_spike")
        self.assertEqual(sim.scenario, "api_error_spike")
        self.assertTrue(sim.alert_trigger.is_firing)
        self.assertIsNotNone(sim.runbook_report)
        self.assertTrue(len(sim.active_responder_channels) >= 1)

    def test_simulate_incident_latency_degradation(self) -> None:
        sim = self.engine.simulate_incident("high_latency_degradation")
        self.assertEqual(sim.scenario, "high_latency_degradation")
        self.assertTrue(sim.alert_trigger.is_firing)

    def test_simulate_incident_healthy_baseline(self) -> None:
        sim = self.engine.simulate_incident("healthy_baseline")
        self.assertEqual(sim.scenario, "healthy_baseline")
        self.assertFalse(sim.alert_trigger.is_firing)

    def test_thread_safe_concurrent_simulations(self) -> None:
        def worker(idx: int) -> IncidentSimulationReport:
            scenarios = ["api_error_spike", "high_latency_degradation", "healthy_baseline"]
            return self.engine.simulate_incident(scenarios[idx % 3])

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(worker, i) for i in range(12)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 12)
        for r in results:
            self.assertIsInstance(r, IncidentSimulationReport)


class TestEcosystemPackBundlingAlerting(unittest.TestCase):
    """Test ecosystem pack package bundling with alerting contract."""

    def test_ecosystem_pack_with_alerting(self) -> None:
        mb_pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        self.assertIsNotNone(mb_pack)
        pack = synthesize_ecosystem_pack(mb_pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)
        self.assertIsNotNone(pack.alerting_contract)
        self.assertIsInstance(pack.alerting_contract, EcosystemAlertingContract)
        self.assertEqual(pack.alerting_contract.ecosystem_id, pack.ecosystem_id)

        d = pack.to_dict()
        self.assertIn("alerting_contract", d)
        parsed = parse_ecosystem_pack_package(d)
        self.assertIsNotNone(parsed.alerting_contract)
        self.assertEqual(parsed.alerting_contract.digest(), pack.alerting_contract.digest())
        self.assertEqual(parsed.package_sha256, pack.package_sha256)


class TestRegistryGetAlertingContract(unittest.TestCase):
    """Test discovery of alerting contracts from ecosystem registry."""

    def test_get_alerting_contract_from_registry(self) -> None:
        contract = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_alerting_contract("minimal-blog-ecosystem")
        self.assertIsNotNone(contract)
        self.assertIsInstance(contract, EcosystemAlertingContract)
        self.assertEqual(contract.ecosystem_id, "minimal-blog-ecosystem")

    def test_get_alerting_contract_returns_none_for_unknown(self) -> None:
        contract = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_alerting_contract("nonexistent-eco")
        self.assertIsNone(contract)


class TestStudioServerAlertingEndpoints(unittest.TestCase):
    """Test Studio HTTP server endpoints for alerting contract and simulation."""

    def setUp(self) -> None:
        surfaces = [
            {"slug": "web", "kind": "customer_web"},
            {"slug": "api", "kind": "backend_api"},
        ]
        self.contract = synthesize_ecosystem_alerting(
            ecosystem_id="studio-alert-eco",
            surfaces=surfaces,
        )
        self.engine = EcosystemAlertingEngine(self.contract)

        def get_alert_fn() -> dict[str, Any]:
            return self.contract.to_dict()

        def sim_alert_fn(body: Any = None) -> dict[str, Any]:
            scenario = "api_error_spike"
            if isinstance(body, dict):
                scenario = body.get("scenario", "api_error_spike")
            return self.engine.simulate_incident(scenario=scenario).to_dict()

        self.server = create_studio_server(
            lambda prompt, **kw: {"status": "ok"},
            host="127.0.0.1",
            port=0,
            get_ecosystem_alerting_fn=get_alert_fn,
            simulate_ecosystem_alerting_fn=sim_alert_fn,
        )
        self.server_thread = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.server_thread.submit(self.server.serve_forever)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.shutdown(wait=True)

    def test_get_ecosystem_alerting_endpoint(self) -> None:
        req = urllib.request.Request(f"{self.base_url}/api/ecosystem/alerting")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["ecosystem_id"], "studio-alert-eco")
            self.assertTrue(len(data["alert_rules"]) >= 1)
            self.assertTrue(len(data["runbooks"]) >= 1)
            self.assertTrue(len(data["escalation_policies"]) >= 1)

    def test_post_ecosystem_alerting_simulate_endpoint(self) -> None:
        req = urllib.request.Request(
            f"{self.base_url}/api/ecosystem/alerting/simulate",
            data=json.dumps({"scenario": "api_error_spike"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("scenario", data)
            self.assertEqual(data["scenario"], "api_error_spike")
            self.assertTrue(data["alert_trigger"]["is_firing"])
            self.assertIsNotNone(data["runbook_report"])


class TestEcosystemCLIAlerting(unittest.TestCase):
    """Test CLI subcommand for alerting."""

    def test_alerting_inspect(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["alerting", "minimal-blog-ecosystem"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("Alerting Contract", output)
        self.assertIn("Alert Rules", output)
        self.assertIn("Incident Runbooks", output)
        self.assertIn("Escalation Policies", output)

    def test_alerting_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["alerting", "minimal-blog-ecosystem", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["ecosystem_id"], "minimal-blog-ecosystem")
        self.assertTrue(len(data["alert_rules"]) >= 1)

    def test_alerting_simulate(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["alerting", "minimal-blog-ecosystem", "--simulate", "--scenario", "api_error_spike"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("Incident Simulation (api_error_spike)", output)
        self.assertIn("OVERALL STATUS:", output)


if __name__ == "__main__":
    unittest.main()

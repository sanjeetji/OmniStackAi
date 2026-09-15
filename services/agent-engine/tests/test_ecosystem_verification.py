"""Tests for Solution Pack Ecosystem Multi-Surface Health Check, Smoke Testing, and Canary Verification (R-453)."""

from __future__ import annotations

import io
import json
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from omnistackai_agent_engine.solution_packs.ecosystem_verification import (
    CanaryVerificationRule,
    EcosystemVerificationContract,
    EcosystemVerificationEngine,
    HealthCheckProbe,
    SmokeTestSpec,
    SmokeTestStep,
    synthesize_ecosystem_verification,
)


# ---------------------------------------------------------------------------
# Stub surfaces for synthesis tests
# ---------------------------------------------------------------------------

class FakeSurface:
    def __init__(self, slug: str, surface_kind: str):
        self.slug = slug
        self.surface_kind = surface_kind


# ---------------------------------------------------------------------------
# 1. HealthCheckProbe roundtrip
# ---------------------------------------------------------------------------

class TestHealthCheckProbeRoundtrip(unittest.TestCase):
    def test_roundtrip_all_fields(self):
        probe = HealthCheckProbe(
            probe_id="web-health-0",
            surface_slug="web",
            surface_kind="customer_web",
            method="GET",
            endpoint="/healthz",
            expected_status=200,
            timeout_seconds=5,
            tags=("health", "frontend"),
        )
        data = probe.to_dict()
        restored = HealthCheckProbe.from_dict(data)
        self.assertEqual(restored.probe_id, probe.probe_id)
        self.assertEqual(restored.surface_slug, probe.surface_slug)
        self.assertEqual(restored.surface_kind, probe.surface_kind)
        self.assertEqual(restored.method, probe.method)
        self.assertEqual(restored.endpoint, probe.endpoint)
        self.assertEqual(restored.expected_status, probe.expected_status)
        self.assertEqual(restored.timeout_seconds, probe.timeout_seconds)
        self.assertEqual(restored.tags, probe.tags)

    def test_default_method_and_status(self):
        probe = HealthCheckProbe(probe_id="p1", surface_slug="admin", surface_kind="admin_portal")
        self.assertEqual(probe.method, "GET")
        self.assertEqual(probe.expected_status, 200)
        self.assertEqual(probe.endpoint, "/healthz")
        self.assertEqual(probe.tags, ())


# ---------------------------------------------------------------------------
# 2. SmokeTestStep + SmokeTestSpec roundtrip
# ---------------------------------------------------------------------------

class TestSmokeTestSpecRoundtrip(unittest.TestCase):
    def test_step_roundtrip(self):
        step = SmokeTestStep(
            step_id="step-0",
            description="Navigate to /",
            action="navigate",
            target="/",
            expected="status=200",
        )
        data = step.to_dict()
        restored = SmokeTestStep.from_dict(data)
        self.assertEqual(restored.step_id, "step-0")
        self.assertEqual(restored.action, "navigate")
        self.assertEqual(restored.target, "/")
        self.assertEqual(restored.expected, "status=200")

    def test_spec_roundtrip(self):
        step = SmokeTestStep(step_id="s0", description="GET health", action="GET", target="/healthz", expected="status=200")
        spec = SmokeTestSpec(
            test_id="web-smoke",
            surface_slug="web",
            name="Web Smoke Test",
            category="functional",
            steps=(step,),
            expected_outcome="success",
        )
        data = spec.to_dict()
        restored = SmokeTestSpec.from_dict(data)
        self.assertEqual(restored.test_id, spec.test_id)
        self.assertEqual(restored.name, spec.name)
        self.assertEqual(restored.category, spec.category)
        self.assertEqual(restored.expected_outcome, spec.expected_outcome)
        self.assertEqual(len(restored.steps), 1)
        self.assertEqual(restored.steps[0].step_id, "s0")


# ---------------------------------------------------------------------------
# 3. CanaryVerificationRule roundtrip
# ---------------------------------------------------------------------------

class TestCanaryVerificationRuleRoundtrip(unittest.TestCase):
    def test_roundtrip(self):
        rule = CanaryVerificationRule(
            rule_id="eco-canary-1",
            surfaces_covered=("web", "admin"),
            trigger="all_surfaces_healthy",
            assertion="All surfaces pass health probes",
            severity="error",
        )
        data = rule.to_dict()
        restored = CanaryVerificationRule.from_dict(data)
        self.assertEqual(restored.rule_id, rule.rule_id)
        self.assertEqual(restored.surfaces_covered, rule.surfaces_covered)
        self.assertEqual(restored.trigger, rule.trigger)
        self.assertEqual(restored.assertion, rule.assertion)
        self.assertEqual(restored.severity, rule.severity)


# ---------------------------------------------------------------------------
# 4. EcosystemVerificationContract roundtrip + digest
# ---------------------------------------------------------------------------

class TestEcosystemVerificationContractRoundtrip(unittest.TestCase):
    def _make_contract(self) -> EcosystemVerificationContract:
        probe = HealthCheckProbe(probe_id="p0", surface_slug="web", surface_kind="customer_web")
        step = SmokeTestStep(step_id="s0", description="GET /", action="GET", target="/", expected="status=200")
        spec = SmokeTestSpec(test_id="web-smoke", surface_slug="web", name="Web Smoke", steps=(step,))
        rule = CanaryVerificationRule(
            rule_id="eco-canary-all",
            surfaces_covered=("web",),
            trigger="all_healthy",
            assertion="All healthy",
        )
        return EcosystemVerificationContract(
            ecosystem_id="test-eco",
            version="1.0.0",
            probes=(probe,),
            smoke_tests=(spec,),
            canary_rules=(rule,),
        )

    def test_roundtrip(self):
        contract = self._make_contract()
        data = contract.to_dict()
        restored = EcosystemVerificationContract.from_dict(data)
        self.assertEqual(restored.ecosystem_id, "test-eco")
        self.assertEqual(restored.version, "1.0.0")
        self.assertEqual(len(restored.probes), 1)
        self.assertEqual(len(restored.smoke_tests), 1)
        self.assertEqual(len(restored.canary_rules), 1)

    def test_digest_is_deterministic(self):
        contract1 = self._make_contract()
        contract2 = self._make_contract()
        self.assertEqual(contract1.digest(), contract2.digest())

    def test_digest_is_64_char_hex(self):
        contract = self._make_contract()
        d = contract.digest()
        self.assertEqual(len(d), 64)
        int(d, 16)  # must be valid hex


# ---------------------------------------------------------------------------
# 5. synthesize_ecosystem_verification – derivation from surfaces
# ---------------------------------------------------------------------------

class TestSynthesizeEcosystemVerification(unittest.TestCase):
    def test_single_surface_produces_probes_and_smoke(self):
        surfaces = [FakeSurface("web", "customer_web")]
        vc = synthesize_ecosystem_verification("test-eco", surfaces, version="1.0.0")
        self.assertEqual(vc.ecosystem_id, "test-eco")
        self.assertEqual(vc.version, "1.0.0")
        self.assertGreater(len(vc.probes), 0)
        self.assertEqual(len(vc.smoke_tests), 1)
        self.assertEqual(vc.smoke_tests[0].surface_slug, "web")

    def test_two_surfaces_produce_canary_rules(self):
        surfaces = [FakeSurface("web", "customer_web"), FakeSurface("api", "api_gateway")]
        vc = synthesize_ecosystem_verification("test-eco", surfaces)
        # At least the health-all canary rule
        self.assertGreater(len(vc.canary_rules), 0)
        rule_ids = {r.rule_id for r in vc.canary_rules}
        self.assertIn("test-eco-canary-health-all", rule_ids)
        self.assertIn("test-eco-canary-smoke-suite", rule_ids)

    def test_api_and_web_surface_produces_latency_canary(self):
        surfaces = [FakeSurface("web", "customer_web"), FakeSurface("api-gateway", "api_gateway")]
        vc = synthesize_ecosystem_verification("blog-eco", surfaces)
        latency_rules = [r for r in vc.canary_rules if "latency" in r.rule_id]
        self.assertGreater(len(latency_rules), 0)

    def test_determinism_same_surfaces(self):
        surfaces1 = [FakeSurface("web", "customer_web"), FakeSurface("admin", "admin_portal")]
        surfaces2 = [FakeSurface("web", "customer_web"), FakeSurface("admin", "admin_portal")]
        vc1 = synthesize_ecosystem_verification("eco-1", surfaces1)
        vc2 = synthesize_ecosystem_verification("eco-1", surfaces2)
        self.assertEqual(vc1.digest(), vc2.digest())

    def test_all_probe_tags_are_tuples(self):
        surfaces = [FakeSurface("db", "database"), FakeSurface("worker", "worker")]
        vc = synthesize_ecosystem_verification("eco-infra", surfaces)
        for probe in vc.probes:
            self.assertIsInstance(probe.tags, tuple)

    def test_database_surface_infra_tag(self):
        surfaces = [FakeSurface("db", "database")]
        vc = synthesize_ecosystem_verification("eco-db", surfaces)
        for probe in vc.probes:
            if probe.surface_slug == "db":
                self.assertIn("infrastructure", probe.tags)
                break


# ---------------------------------------------------------------------------
# 6. EcosystemVerificationEngine simulation
# ---------------------------------------------------------------------------

class TestEcosystemVerificationEngine(unittest.TestCase):
    def _make_two_surface_contract(self) -> EcosystemVerificationContract:
        surfaces = [FakeSurface("web", "customer_web"), FakeSurface("api", "api_gateway")]
        return synthesize_ecosystem_verification("blog-eco", surfaces, version="1.0.0")

    def test_simulate_full_returns_pass_status(self):
        contract = self._make_two_surface_contract()
        engine = EcosystemVerificationEngine(contract)
        result = engine.simulate_full_verification()
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["ecosystem_id"], "blog-eco")

    def test_simulate_probes_all_pass(self):
        contract = self._make_two_surface_contract()
        engine = EcosystemVerificationEngine(contract)
        probe_results = engine.simulate_probe_evaluation()
        self.assertEqual(len(probe_results), len(contract.probes))
        for r in probe_results:
            self.assertEqual(r.status, "pass")

    def test_simulate_smoke_tests_all_pass(self):
        contract = self._make_two_surface_contract()
        engine = EcosystemVerificationEngine(contract)
        smoke_results = engine.simulate_smoke_tests()
        self.assertEqual(len(smoke_results), len(contract.smoke_tests))
        for r in smoke_results:
            self.assertEqual(r.status, "pass")
            self.assertIsNone(r.failed_step)

    def test_simulate_canary_rules_all_pass(self):
        contract = self._make_two_surface_contract()
        engine = EcosystemVerificationEngine(contract)
        canary_results = engine.simulate_canary_rules()
        self.assertEqual(len(canary_results), len(contract.canary_rules))
        for r in canary_results:
            self.assertEqual(r.status, "pass")

    def test_summary_counts_match(self):
        contract = self._make_two_surface_contract()
        engine = EcosystemVerificationEngine(contract)
        result = engine.simulate_full_verification()
        summary = result["summary"]
        self.assertEqual(summary["total_probes"], len(contract.probes))
        self.assertEqual(summary["total_smoke_tests"], len(contract.smoke_tests))
        self.assertEqual(summary["total_canary_rules"], len(contract.canary_rules))
        self.assertEqual(summary["probe_fail"], 0)
        self.assertEqual(summary["smoke_fail"], 0)
        self.assertEqual(summary["canary_fail"], 0)

    def test_thread_safe_concurrent_simulate(self):
        """Concurrent simulate_full_verification calls must not corrupt results."""
        contract = self._make_two_surface_contract()
        engine = EcosystemVerificationEngine(contract)
        results = []
        errors = []

        def run():
            try:
                r = engine.simulate_full_verification()
                results.append(r["status"])
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=run) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 10)
        for r in results:
            self.assertEqual(r, "pass")


# ---------------------------------------------------------------------------
# 7. Pack bundling with verification_contract integrity
# ---------------------------------------------------------------------------

class TestPackVerificationContractIntegration(unittest.TestCase):
    def test_synthesized_pack_has_verification_contract(self):
        from omnistackai_agent_engine.solution_packs import (
            DEFAULT_SOLUTION_PACK_REGISTRY,
            synthesize_ecosystem_pack,
        )
        mb_pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        if mb_pack is None:
            self.skipTest("minimal-blog pack not available")
        pkg = synthesize_ecosystem_pack(mb_pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)
        self.assertIsNotNone(pkg.verification_contract)
        vc = pkg.verification_contract
        self.assertGreater(len(vc.probes), 0)
        self.assertGreater(len(vc.smoke_tests), 0)
        self.assertGreater(len(vc.canary_rules), 0)

    def test_pack_json_includes_verification_contract(self):
        from omnistackai_agent_engine.solution_packs import (
            DEFAULT_SOLUTION_PACK_REGISTRY,
            synthesize_ecosystem_pack,
        )
        mb_pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        if mb_pack is None:
            self.skipTest("minimal-blog pack not available")
        pkg = synthesize_ecosystem_pack(mb_pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)
        raw = json.loads(pkg.to_json())
        self.assertIn("verification_contract", raw)
        self.assertIn("probes", raw["verification_contract"])
        self.assertIn("smoke_tests", raw["verification_contract"])
        self.assertIn("canary_rules", raw["verification_contract"])


# ---------------------------------------------------------------------------
# 8. Registry get_verification_contract
# ---------------------------------------------------------------------------

class TestRegistryGetVerificationContract(unittest.TestCase):
    def test_get_verification_contract_from_registry(self):
        from omnistackai_agent_engine.solution_packs import DEFAULT_ECOSYSTEM_PACK_REGISTRY
        packs = DEFAULT_ECOSYSTEM_PACK_REGISTRY.list_packs()
        if not packs:
            self.skipTest("No ecosystem packs in default registry")
        pack = packs[0]
        vc = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_verification_contract(pack.ecosystem_id)
        self.assertIsNotNone(vc)
        self.assertGreater(len(vc.probes), 0)

    def test_get_verification_contract_returns_none_for_unknown(self):
        from omnistackai_agent_engine.solution_packs import DEFAULT_ECOSYSTEM_PACK_REGISTRY
        vc = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_verification_contract("no-such-ecosystem-id")
        self.assertIsNone(vc)


# ---------------------------------------------------------------------------
# 9. Studio preview HTTP endpoints
# ---------------------------------------------------------------------------

class FakePlan:
    has_web = True
    web_url = "http://127.0.0.1:3000"
    api_url = None
    backend_kind = "none"


class FakeSession:
    plan = FakePlan()
    web_ready = True
    api_ready = False

    def is_alive(self):
        return True

    def stop(self):
        pass


def _find_free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestStudioEcosystemVerificationEndpoints(unittest.TestCase):
    def setUp(self):
        from omnistackai_agent_engine.studio.preview import StudioPreviewManager
        from omnistackai_agent_engine.studio.server import create_studio_server
        from omnistackai_agent_engine.solution_packs.ecosystem_verification import (
            EcosystemVerificationEngine,
            synthesize_ecosystem_verification,
        )

        self.preview = StudioPreviewManager()

        # Directly inject verification state without invoking the preview machinery
        self.preview._is_ecosystem = True
        self.preview._ecosystem_id = "test-eco"
        self.preview._surfaces = [
            {"slug": "web", "surface_kind": "customer_web", "app_name": "Web App"},
            {"slug": "api", "surface_kind": "api_gateway", "app_name": "API Gateway"},
        ]

        class _S:
            def __init__(self, slug, kind):
                self.slug = slug
                self.surface_kind = kind

        vc = synthesize_ecosystem_verification("test-eco", [
            _S("web", "customer_web"),
            _S("api", "api_gateway"),
        ])
        self.preview._verification_contract = vc
        self.preview._verification_engine = EcosystemVerificationEngine(vc)

        port = _find_free_port()
        self.server = create_studio_server(
            lambda prompt, **kw: {"status": "ok"},
            host="127.0.0.1",
            port=port,
            get_ecosystem_verification_fn=self.preview.get_ecosystem_verification,
            simulate_ecosystem_verification_fn=self.preview.simulate_ecosystem_verification,
        )
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.base_url = f"http://127.0.0.1:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_get_ecosystem_verification_endpoint(self):
        req = Request(f"{self.base_url}/api/ecosystem/verification")
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        self.assertIn("verification_contract", data)
        self.assertGreater(data["probe_count"], 0)

    def test_post_ecosystem_verification_simulate_endpoint(self):
        body = b"{}"
        req = Request(
            f"{self.base_url}/api/ecosystem/verification/simulate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        self.assertEqual(data["status"], "pass")
        self.assertIn("summary", data)
        self.assertIn("probe_results", data)
        self.assertIn("smoke_test_results", data)
        self.assertIn("canary_rule_results", data)


# ---------------------------------------------------------------------------
# 10. CLI verify-suite subcommand
# ---------------------------------------------------------------------------

class TestEcosystemCLIVerifySuite(unittest.TestCase):
    def _get_pack_file(self) -> str | None:
        """Synthesize a minimal-blog pack to a temp file."""
        import tempfile
        from omnistackai_agent_engine.solution_packs import (
            DEFAULT_SOLUTION_PACK_REGISTRY,
            synthesize_ecosystem_pack,
        )
        mb_pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        if mb_pack is None:
            return None
        pkg = synthesize_ecosystem_pack(mb_pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        f.write(pkg.to_json())
        f.write("\n")
        f.close()
        return f.name

    def test_verify_suite_inspect(self):
        import os
        from omnistackai_agent_engine.solution_packs.ecosystem_cli import main as cli_main
        path = self._get_pack_file()
        if path is None:
            self.skipTest("minimal-blog pack not available")
        try:
            captured = io.StringIO()
            import sys
            old_stdout = sys.stdout
            sys.stdout = captured
            rc = cli_main(["verify-suite", path])
            sys.stdout = old_stdout
            output = captured.getvalue()
            self.assertEqual(rc, 0)
            self.assertIn("Verification Suite", output)
            self.assertIn("Probes", output)
            self.assertIn("Smoke Tests", output)
            self.assertIn("Canary Rules", output)
        finally:
            os.unlink(path)

    def test_verify_suite_simulate(self):
        import os
        from omnistackai_agent_engine.solution_packs.ecosystem_cli import main as cli_main
        path = self._get_pack_file()
        if path is None:
            self.skipTest("minimal-blog pack not available")
        try:
            captured = io.StringIO()
            import sys
            old_stdout = sys.stdout
            sys.stdout = captured
            rc = cli_main(["verify-suite", path, "--simulate"])
            sys.stdout = old_stdout
            output = captured.getvalue()
            self.assertEqual(rc, 0)
            self.assertIn("PASS", output.upper())
        finally:
            os.unlink(path)

    def test_verify_suite_json(self):
        import os
        from omnistackai_agent_engine.solution_packs.ecosystem_cli import main as cli_main
        path = self._get_pack_file()
        if path is None:
            self.skipTest("minimal-blog pack not available")
        try:
            captured = io.StringIO()
            import sys
            old_stdout = sys.stdout
            sys.stdout = captured
            rc = cli_main(["verify-suite", path, "--json"])
            sys.stdout = old_stdout
            output = captured.getvalue()
            self.assertEqual(rc, 0)
            data = json.loads(output)
            self.assertIn("probes", data)
            self.assertIn("smoke_tests", data)
            self.assertIn("canary_rules", data)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()

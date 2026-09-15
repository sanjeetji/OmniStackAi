"""Tests for Ecosystem Multi-Surface Governance, Compliance Policy, and Audit Evidence Contracts (R-458)."""

from __future__ import annotations

import concurrent.futures
import io
import json
import unittest
import unittest.mock
import urllib.request
from contextlib import redirect_stdout
from typing import Any

from omnistackai_agent_engine.solution_packs.ecosystem_governance import (
    AuditEvidenceItem,
    AuditVerificationReport,
    ComplianceStandard,
    CompliancePolicy,
    DataClassification,
    EcosystemGovernanceContract,
    EcosystemGovernanceEngine,
    EvidenceVerificationItemResult,
    GovernanceAuditSimulationReport,
    GovernanceComplianceReport,
    PolicyEvaluationResult,
    synthesize_ecosystem_governance,
)
from omnistackai_agent_engine.solution_packs.ecosystem_cli import build_parser, main
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
from omnistackai_agent_engine.studio.page import STUDIO_HTML


class TestEcosystemGovernanceModels(unittest.TestCase):
    """Test dataclass serialization, deserialization, and deterministic digest generation."""

    def test_compliance_standard_roundtrip(self) -> None:
        std = ComplianceStandard(
            standard_id="soc2-type2",
            name="SOC 2 Type II",
            version="2022",
            description="Service Organization Control 2 Type II Trust Services Criteria",
            mandatory_controls=("CC6.1", "CC6.6", "CC6.8", "CC7.1"),
        )
        d = std.to_dict()
        restored = ComplianceStandard.from_dict(d)
        self.assertEqual(restored.standard_id, "soc2-type2")
        self.assertEqual(restored.name, "SOC 2 Type II")
        self.assertEqual(restored.version, "2022")
        self.assertEqual(restored.mandatory_controls, ("CC6.1", "CC6.6", "CC6.8", "CC7.1"))

    def test_compliance_policy_roundtrip(self) -> None:
        pol = CompliancePolicy(
            policy_id="pol-api-tls",
            surface_slug="api",
            standard_id="soc2-type2",
            control_id="CC6.6",
            severity="critical",
            enforcement_mode="blocking",
            rule_expression="tls_version >= 1.3 and cipher_suite in ('ECDHE-RSA-AES256-GCM-SHA384',)",
            remediation="Enforce TLS 1.3 and modern cipher suites in gateway configuration.",
            description="All API ingress traffic must use TLS 1.3 or higher.",
            tags=("security", "tls", "api"),
        )
        d = pol.to_dict()
        restored = CompliancePolicy.from_dict(d)
        self.assertEqual(restored.policy_id, "pol-api-tls")
        self.assertEqual(restored.surface_slug, "api")
        self.assertEqual(restored.standard_id, "soc2-type2")
        self.assertEqual(restored.control_id, "CC6.6")
        self.assertEqual(restored.severity, "critical")
        self.assertEqual(restored.enforcement_mode, "blocking")
        self.assertEqual(restored.tags, ("security", "tls", "api"))

    def test_data_classification_roundtrip(self) -> None:
        dc = DataClassification(
            classification_id="dc-user-email",
            surface_slug="api",
            entity_name="UserProfile",
            field_name="email",
            classification_level="pii",
            encryption_required=True,
            retention_days=365,
            anonymization_method="pseudonymize_sha256",
            description="User email address classified as PII.",
        )
        d = dc.to_dict()
        restored = DataClassification.from_dict(d)
        self.assertEqual(restored.classification_id, "dc-user-email")
        self.assertEqual(restored.surface_slug, "api")
        self.assertEqual(restored.entity_name, "UserProfile")
        self.assertEqual(restored.field_name, "email")
        self.assertEqual(restored.classification_level, "pii")
        self.assertTrue(restored.encryption_required)
        self.assertEqual(restored.retention_days, 365)
        self.assertEqual(restored.anonymization_method, "pseudonymize_sha256")

    def test_audit_evidence_item_roundtrip(self) -> None:
        item = AuditEvidenceItem(
            evidence_id="evi-db-backup-001",
            control_id="CC7.1",
            surface_slug="db",
            collector_kind="automated_snapshot",
            status="valid",
            collected_at="2026-09-15T00:00:00Z",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            details={"snapshot_id": "snap-999", "size_bytes": 1048576},
        )
        d = item.to_dict()
        restored = AuditEvidenceItem.from_dict(d)
        self.assertEqual(restored.evidence_id, "evi-db-backup-001")
        self.assertEqual(restored.control_id, "CC7.1")
        self.assertEqual(restored.surface_slug, "db")
        self.assertEqual(restored.status, "valid")
        self.assertEqual(restored.sha256_hash, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        self.assertEqual(restored.details, {"snapshot_id": "snap-999", "size_bytes": 1048576})

    def test_ecosystem_governance_contract_roundtrip_and_digest(self) -> None:
        std = ComplianceStandard(
            standard_id="soc2-type2",
            name="SOC 2 Type II",
            version="2022",
            description="Service Organization Control 2 Type II Trust Services Criteria",
            mandatory_controls=("CC6.1",),
        )
        pol = CompliancePolicy(
            policy_id="pol-web-csp",
            surface_slug="web",
            standard_id="soc2-type2",
            control_id="CC6.1",
            severity="high",
            enforcement_mode="blocking",
            rule_expression="has_content_security_policy == true",
            remediation="Configure Content-Security-Policy headers.",
            description="Content Security Policy enforcement",
        )
        dc = DataClassification(
            classification_id="dc-token",
            surface_slug="web",
            entity_name="Session",
            field_name="token",
            classification_level="confidential",
            encryption_required=True,
            retention_days=7,
            anonymization_method="redact",
        )
        item = AuditEvidenceItem(
            evidence_id="evi-web-audit",
            control_id="CC6.1",
            surface_slug="web",
            collector_kind="config_scan",
            status="valid",
            collected_at="2026-09-15T00:00:00Z",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            details={"scan_tool": "in_process"},
        )
        contract = EcosystemGovernanceContract(
            ecosystem_id="test-gov-eco",
            version="1.0.0",
            standards=(std,),
            policies=(pol,),
            classifications=(dc,),
            evidence_items=(item,),
        )
        d = contract.to_dict()
        restored = EcosystemGovernanceContract.from_dict(d)
        self.assertEqual(restored.ecosystem_id, "test-gov-eco")
        self.assertEqual(len(restored.standards), 1)
        self.assertEqual(len(restored.policies), 1)
        self.assertEqual(len(restored.data_classifications), 1)
        self.assertEqual(len(restored.evidence_items), 1)
        self.assertEqual(restored.digest(), contract.digest())
        self.assertEqual(len(restored.digest()), 64)

        # Test JSON roundtrip
        json_str = contract.to_json()
        from_json_contract = EcosystemGovernanceContract.from_json(json_str)
        self.assertEqual(from_json_contract.digest(), contract.digest())


class TestSynthesizeEcosystemGovernance(unittest.TestCase):
    """Test automatic deterministic synthesis of multi-surface governance contracts."""

    def test_synthesize_default_surfaces(self) -> None:
        surfaces = [
            {"slug": "web", "kind": "customer_web", "app_name": "Web App"},
            {"slug": "api", "kind": "backend_api", "app_name": "API Service"},
            {"slug": "admin", "kind": "admin_portal", "app_name": "Admin Portal"},
            {"slug": "worker", "kind": "async_worker", "app_name": "Background Worker"},
            {"slug": "db", "kind": "database", "app_name": "Primary Database"},
        ]
        contract = synthesize_ecosystem_governance("synth-gov-eco", surfaces)
        self.assertEqual(contract.ecosystem_id, "synth-gov-eco")

        # Standards coverage
        standard_ids = {s.standard_id for s in contract.standards}
        self.assertIn("soc2_type_ii", standard_ids)
        self.assertIn("gdpr", standard_ids)
        self.assertIn("iso_27001", standard_ids)

        # Policies across surfaces
        policy_surfaces = {p.surface_slug for p in contract.policies}
        self.assertIn("web", policy_surfaces)
        self.assertIn("api", policy_surfaces)
        self.assertIn("admin", policy_surfaces)
        self.assertIn("worker", policy_surfaces)
        self.assertIn("db", policy_surfaces)
        self.assertTrue(len(contract.policies) >= 10)

        # Data classifications
        self.assertTrue(len(contract.data_classifications) >= 5)
        pii_items = [c for c in contract.data_classifications if c.classification_level == "pii"]
        self.assertTrue(len(pii_items) >= 1)

        # Audit evidence
        self.assertTrue(len(contract.evidence_items) >= 5)
        for ev in contract.evidence_items:
            self.assertEqual(len(ev.sha256_hash), 64)
            self.assertEqual(ev.status, "compliant")

        # Deterministic digest
        contract_2 = synthesize_ecosystem_governance("synth-gov-eco", surfaces)
        self.assertEqual(contract.digest(), contract_2.digest())


class TestEcosystemGovernanceEngine(unittest.TestCase):
    """Test thread-safe in-process governance evaluation, verification, and audit simulation engine."""

    def setUp(self) -> None:
        surfaces = [
            {"slug": "web", "kind": "customer_web"},
            {"slug": "api", "kind": "backend_api"},
            {"slug": "admin", "kind": "admin_portal"},
            {"slug": "worker", "kind": "async_worker"},
            {"slug": "db", "kind": "database"},
        ]
        self.contract = synthesize_ecosystem_governance("test-gov-eco", surfaces)
        self.engine = EcosystemGovernanceEngine(self.contract)

    def test_evaluate_compliance_compliant(self) -> None:
        # Default environment matches synthesized expectations
        report = self.engine.evaluate_compliance()
        self.assertIsInstance(report, GovernanceComplianceReport)
        self.assertTrue(report.overall_compliant)
        self.assertEqual(len(report.violations), 0)
        self.assertEqual(report.compliance_score_pct, 100.0)

    def test_evaluate_compliance_with_violations(self) -> None:
        env_state = {
            "tls_version": "1.1",  # violation
            "encryption_at_rest": False,  # violation
            "audit_logging_enabled": False,  # violation
        }
        report = self.engine.evaluate_compliance(environment_state=env_state)
        self.assertIsInstance(report, GovernanceComplianceReport)
        self.assertFalse(report.overall_compliant)
        self.assertGreater(len(report.violations), 0)
        self.assertLess(report.compliance_score_pct, 100.0)
        violated_policy_ids = {v.policy_id for v in report.violations}
        self.assertTrue(any("tls" in pid or "encrypt" in pid or "audit" in pid for pid in violated_policy_ids))

    def test_verify_audit_evidence_valid(self) -> None:
        report = self.engine.verify_audit_evidence()
        self.assertIsInstance(report, AuditVerificationReport)
        self.assertTrue(report.all_valid)
        self.assertEqual(report.tampered_count, 0)
        self.assertEqual(len(report.results), len(self.contract.evidence_items))

    def test_verify_audit_evidence_tampered(self) -> None:
        tampered_items = list(self.contract.evidence_items)
        first = tampered_items[0]
        # Change hash so it won't match details
        tampered_first = AuditEvidenceItem(
            evidence_id=first.evidence_id,
            control_id=first.control_id,
            surface_slug=first.surface_slug,
            collector_kind=first.collector_kind,
            status=first.status,
            collected_at=first.collected_at,
            sha256_hash="0000000000000000000000000000000000000000000000000000000000000000",
            details=first.details,
        )
        tampered_items[0] = tampered_first
        contract_tampered = EcosystemGovernanceContract(
            ecosystem_id=self.contract.ecosystem_id,
            version=self.contract.version,
            standards=self.contract.standards,
            policies=self.contract.policies,
            classifications=self.contract.classifications,
            evidence_items=tuple(tampered_items),
        )
        engine_tampered = EcosystemGovernanceEngine(contract_tampered)
        report = engine_tampered.verify_audit_evidence()
        self.assertFalse(report.all_valid)
        self.assertGreater(report.tampered_count, 0)

    def test_simulate_compliance_audit_scenarios(self) -> None:
        scenarios = [
            ("standard_audit", True),
            ("gdpr_dsar_request", True),
            ("data_breach_investigation", True),
            ("soc2_certification", True),
            ("high_risk_violations", False),
        ]
        for scenario, expected_pass in scenarios:
            rep = self.engine.simulate_compliance_audit(scenario=scenario)
            self.assertIsInstance(rep, GovernanceAuditSimulationReport)
            self.assertEqual(rep.scenario, scenario)
            self.assertEqual(rep.overall_audit_passed, expected_pass, f"Failed for scenario {scenario}")
            self.assertIsInstance(rep.compliance_report, GovernanceComplianceReport)
            self.assertIsInstance(rep.evidence_report, AuditVerificationReport)

    def test_thread_safe_concurrent_simulations(self) -> None:
        scenarios = [
            "standard_audit",
            "gdpr_dsar_request",
            "data_breach_investigation",
            "soc2_certification",
            "high_risk_violations",
        ]

        def run_sim(idx: int) -> GovernanceAuditSimulationReport:
            return self.engine.simulate_compliance_audit(scenarios[idx % len(scenarios)])

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(run_sim, i) for i in range(16)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 16)
        for r in results:
            self.assertIsInstance(r, GovernanceAuditSimulationReport)


class TestEcosystemPackBundlingGovernance(unittest.TestCase):
    """Test ecosystem pack package bundling and whole-package digest integrity with governance."""

    def test_ecosystem_pack_with_governance(self) -> None:
        mb_pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        self.assertIsNotNone(mb_pack)
        pack = synthesize_ecosystem_pack(mb_pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)
        self.assertIsNotNone(pack.governance_contract)
        self.assertIsInstance(pack.governance_contract, EcosystemGovernanceContract)
        self.assertEqual(pack.governance_contract.ecosystem_id, pack.ecosystem_id)

        d = pack.to_dict()
        self.assertIn("governance_contract", d)
        parsed = parse_ecosystem_pack_package(d)
        self.assertIsNotNone(parsed.governance_contract)
        self.assertEqual(parsed.governance_contract.digest(), pack.governance_contract.digest())
        self.assertEqual(parsed.package_sha256, pack.package_sha256)


class TestRegistryGetGovernanceContract(unittest.TestCase):
    """Test discovery of governance contracts from ecosystem registry."""

    def test_get_governance_contract_from_registry(self) -> None:
        contract = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_governance_contract("minimal-blog-ecosystem")
        self.assertIsNotNone(contract)
        self.assertIsInstance(contract, EcosystemGovernanceContract)
        self.assertEqual(contract.ecosystem_id, "minimal-blog-ecosystem")

    def test_get_governance_contract_returns_none_for_unknown(self) -> None:
        contract = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_governance_contract("nonexistent-eco")
        self.assertIsNone(contract)


class TestStudioPreviewManagerGovernance(unittest.TestCase):
    """Test StudioPreviewManager governance integration."""

    def test_preview_manager_ecosystem_governance(self) -> None:
        surfaces = [
            {"slug": "web", "kind": "customer_web", "app_name": "Blog Web"},
            {"slug": "api", "kind": "backend_api", "app_name": "Blog API"},
        ]
        manager = StudioPreviewManager(start_fn=lambda repo, log=None: unittest.mock.MagicMock())
        status = manager.replace_ecosystem("test-gov-eco", surfaces)
        self.assertTrue(status["has_governance"])
        self.assertGreater(status["standard_count"], 0)
        self.assertGreater(status["policy_count"], 0)
        self.assertGreater(status["evidence_count"], 0)
        self.assertEqual(status["governance_status"], "configured")

        gov_data = manager.get_ecosystem_governance()
        self.assertTrue(gov_data["is_ecosystem"])
        self.assertEqual(gov_data["status"], "ok")
        self.assertEqual(gov_data["ecosystem_id"], "test-gov-eco")
        self.assertGreater(gov_data["policy_count"], 0)

        sim_res = manager.simulate_ecosystem_governance({"scenario": "standard_audit"})
        self.assertEqual(sim_res["status"], "ok")
        self.assertEqual(sim_res["scenario"], "standard_audit")
        self.assertTrue(sim_res["report"]["overall_audit_passed"])


class TestStudioServerGovernanceEndpoints(unittest.TestCase):
    """Test Studio HTTP server endpoints for governance contract and simulation."""

    def setUp(self) -> None:
        surfaces = [
            {"slug": "web", "kind": "customer_web"},
            {"slug": "api", "kind": "backend_api"},
        ]
        self.contract = synthesize_ecosystem_governance(
            ecosystem_id="studio-gov-eco",
            surfaces=surfaces,
        )
        self.engine = EcosystemGovernanceEngine(self.contract)

        def get_gov_fn() -> dict[str, Any]:
            return self.contract.to_dict()

        def sim_gov_fn(body: Any = None) -> dict[str, Any]:
            scenario = "standard_audit"
            if isinstance(body, dict):
                scenario = body.get("scenario", "standard_audit")
            return self.engine.simulate_compliance_audit(scenario=scenario).to_dict()

        self.server = create_studio_server(
            lambda prompt, **kw: {"status": "ok"},
            host="127.0.0.1",
            port=0,
            get_ecosystem_governance_fn=get_gov_fn,
            simulate_ecosystem_governance_fn=sim_gov_fn,
        )
        self.server_thread = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.server_thread.submit(self.server.serve_forever)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.shutdown(wait=True)

    def test_get_ecosystem_governance_endpoint(self) -> None:
        req = urllib.request.Request(f"{self.base_url}/api/ecosystem/governance")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["ecosystem_id"], "studio-gov-eco")
            self.assertTrue(len(data["standards"]) >= 1)
            self.assertTrue(len(data["policies"]) >= 1)
            self.assertTrue(len(data["data_classifications"]) >= 1)
            self.assertTrue(len(data["evidence_items"]) >= 1)

    def test_post_ecosystem_governance_simulate_endpoint(self) -> None:
        req = urllib.request.Request(
            f"{self.base_url}/api/ecosystem/governance/simulate",
            data=json.dumps({"scenario": "standard_audit"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("scenario", data)
            self.assertEqual(data["scenario"], "standard_audit")
            self.assertTrue(data["overall_audit_passed"])
            self.assertIn("compliance_report", data)
            self.assertIn("evidence_report", data)

    def test_studio_page_zero_external_requests(self) -> None:
        """Verify Studio HTML contains strictly zero external network requests."""
        html = STUDIO_HTML
        self.assertNotIn("https://fonts.googleapis.com", html)
        self.assertNotIn("https://cdnjs.cloudflare.com", html)
        self.assertNotIn("https://cdn.jsdelivr.net", html)
        self.assertIn("preview-governance-info", html)
        self.assertIn("gov-simulate-btn", html)
        self.assertIn("gov-refresh-btn", html)


class TestEcosystemCLIGovernance(unittest.TestCase):
    """Test CLI subcommand for governance."""

    def test_governance_inspect(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["governance", "minimal-blog-ecosystem"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("Governance Contract", output)
        self.assertIn("Standards", output)
        self.assertIn("Policies", output)
        self.assertIn("Data Classifications", output)
        self.assertIn("Audit Evidence Items", output)

    def test_governance_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["governance", "minimal-blog-ecosystem", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["ecosystem_id"], "minimal-blog-ecosystem")
        self.assertTrue(len(data["standards"]) >= 1)
        self.assertTrue(len(data["policies"]) >= 1)

    def test_governance_simulate(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["governance", "minimal-blog-ecosystem", "--simulate", "--scenario", "standard_audit"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("Governance Audit Simulation (standard_audit)", output)
        self.assertIn("OVERALL STATUS: COMPLIANT", output)


if __name__ == "__main__":
    unittest.main()

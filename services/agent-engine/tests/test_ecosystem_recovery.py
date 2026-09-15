"""Tests for Solution Pack Ecosystem Multi-Surface Disaster Recovery, Snapshot Backup, and Rollback Orchestration (R-454)."""

from __future__ import annotations

import concurrent.futures
import json
import tempfile
import unittest
from pathlib import Path

from omnistackai_agent_engine.solution_packs.ecosystem_recovery import (
    BackupTarget,
    EcosystemDisasterRecoveryContract,
    EcosystemRecoveryEngine,
    RecoveryStep,
    RecoveryStepResult,
    RollbackTrigger,
    RollbackTriggerResult,
    SnapshotManifest,
    SnapshotResult,
    synthesize_ecosystem_recovery,
)
from omnistackai_agent_engine.solution_packs.ecosystem_pack import (
    EcosystemSurfacePackage,
    parse_ecosystem_pack_package,
    synthesize_ecosystem_pack,
)
from omnistackai_agent_engine.solution_packs.ecosystem_registry import (
    DEFAULT_ECOSYSTEM_PACK_REGISTRY,
)
from omnistackai_agent_engine.solution_packs.registry import DEFAULT_SOLUTION_PACK_REGISTRY
from omnistackai_agent_engine.studio.server import create_studio_server


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def _sample_surfaces() -> list[dict[str, str]]:
    return [
        {"slug": "web", "kind": "web", "app_name": "Web Portal"},
        {"slug": "api", "kind": "api", "app_name": "Backend API"},
        {"slug": "db", "kind": "database", "app_name": "Postgres Database"},
    ]


# ---------------------------------------------------------------------------
# BackupTarget Tests
# ---------------------------------------------------------------------------


class TestBackupTarget(unittest.TestCase):
    def test_backup_target_to_dict_and_from_dict(self) -> None:
        target = BackupTarget(
            target_id="bt-1",
            surface_slug="db",
            target_kind="database",
            storage_uri="snapshots/eco-1/db/db.sql.gz",
            frequency="daily",
            retention_days=30,
            encryption_required=True,
            tags=("database", "critical"),
        )
        d = target.to_dict()
        self.assertEqual(d["target_id"], "bt-1")
        self.assertEqual(d["surface_slug"], "db")
        self.assertEqual(d["target_kind"], "database")
        self.assertEqual(d["retention_days"], 30)
        self.assertTrue(d["encryption_required"])
        self.assertEqual(d["tags"], ["database", "critical"])

        recovered = BackupTarget.from_dict(d)
        self.assertEqual(recovered.target_id, target.target_id)
        self.assertEqual(recovered.surface_slug, target.surface_slug)
        self.assertEqual(recovered.tags, target.tags)
        self.assertEqual(recovered.encryption_required, target.encryption_required)


# ---------------------------------------------------------------------------
# SnapshotManifest Tests
# ---------------------------------------------------------------------------


class TestSnapshotManifest(unittest.TestCase):
    def test_snapshot_manifest_to_dict_and_from_dict(self) -> None:
        manifest = SnapshotManifest(
            snapshot_id="snap-101",
            ecosystem_id="eco-test",
            surface_slug="web",
            created_at_utc="2026-09-15T00:00:00Z",
            checksum_sha256="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
            size_bytes=4096,
            metadata={"environment": "production"},
        )
        d = manifest.to_dict()
        self.assertEqual(d["snapshot_id"], "snap-101")
        self.assertEqual(d["ecosystem_id"], "eco-test")
        self.assertEqual(d["size_bytes"], 4096)
        self.assertEqual(d["metadata"]["environment"], "production")

        recovered = SnapshotManifest.from_dict(d)
        self.assertEqual(recovered.snapshot_id, manifest.snapshot_id)
        self.assertEqual(recovered.checksum_sha256, manifest.checksum_sha256)
        self.assertEqual(recovered.metadata, manifest.metadata)


# ---------------------------------------------------------------------------
# RecoveryStep Tests
# ---------------------------------------------------------------------------


class TestRecoveryStep(unittest.TestCase):
    def test_recovery_step_to_dict_and_from_dict(self) -> None:
        step = RecoveryStep(
            step_id="step-1",
            sequence_order=1,
            surface_slug="api",
            action="drain_traffic",
            target="ingress_gateway",
            timeout_seconds=30,
            critical=True,
            description="Drain traffic",
        )
        d = step.to_dict()
        self.assertEqual(d["step_id"], "step-1")
        self.assertEqual(d["sequence_order"], 1)
        self.assertEqual(d["action"], "drain_traffic")
        self.assertTrue(d["critical"])

        recovered = RecoveryStep.from_dict(d)
        self.assertEqual(recovered.step_id, step.step_id)
        self.assertEqual(recovered.sequence_order, step.sequence_order)
        self.assertEqual(recovered.target, step.target)


# ---------------------------------------------------------------------------
# RollbackTrigger Tests
# ---------------------------------------------------------------------------


class TestRollbackTrigger(unittest.TestCase):
    def test_rollback_trigger_to_dict_and_from_dict(self) -> None:
        trigger = RollbackTrigger(
            trigger_id="trig-1",
            condition="health_probe_failed",
            threshold="consecutive_failures >= 3",
            action="revert_to_last_known_good_snapshot",
            severity="critical",
        )
        d = trigger.to_dict()
        self.assertEqual(d["trigger_id"], "trig-1")
        self.assertEqual(d["condition"], "health_probe_failed")
        self.assertEqual(d["severity"], "critical")

        recovered = RollbackTrigger.from_dict(d)
        self.assertEqual(recovered.trigger_id, trigger.trigger_id)
        self.assertEqual(recovered.action, trigger.action)


# ---------------------------------------------------------------------------
# EcosystemDisasterRecoveryContract Tests
# ---------------------------------------------------------------------------


class TestEcosystemDisasterRecoveryContract(unittest.TestCase):
    def test_contract_roundtrip_and_deterministic_digest(self) -> None:
        surfaces = _sample_surfaces()
        contract = synthesize_ecosystem_recovery("my-test-eco", surfaces)

        digest1 = contract.digest()
        self.assertEqual(len(digest1), 64)

        d = contract.to_dict()
        self.assertIn("ecosystem_id", d)
        self.assertIn("backup_targets", d)
        self.assertIn("recovery_steps", d)
        self.assertIn("rollback_triggers", d)

        recovered = EcosystemDisasterRecoveryContract.from_dict(d)
        self.assertEqual(recovered.digest(), digest1)
        self.assertEqual(recovered.ecosystem_id, contract.ecosystem_id)
        self.assertEqual(len(recovered.backup_targets), len(contract.backup_targets))
        self.assertEqual(len(recovered.recovery_steps), len(contract.recovery_steps))
        self.assertEqual(len(recovered.rollback_triggers), len(contract.rollback_triggers))

    def test_deterministic_digest_stability(self) -> None:
        surfaces = _sample_surfaces()
        c1 = synthesize_ecosystem_recovery("same-eco", surfaces)
        c2 = synthesize_ecosystem_recovery("same-eco", surfaces)
        self.assertEqual(c1.digest(), c2.digest())
        self.assertEqual(c1.to_json(), c2.to_json())

    def test_json_serialization_roundtrip(self) -> None:
        surfaces = _sample_surfaces()
        contract = synthesize_ecosystem_recovery("json-eco", surfaces)
        json_str = contract.to_json()
        recovered = EcosystemDisasterRecoveryContract.from_json(json_str)
        self.assertEqual(recovered.digest(), contract.digest())
        self.assertEqual(recovered.ecosystem_id, "json-eco")


# ---------------------------------------------------------------------------
# Synthesis Tests
# ---------------------------------------------------------------------------


class TestSynthesizeEcosystemRecovery(unittest.TestCase):
    def test_synthesize_derives_correct_targets_and_steps(self) -> None:
        surfaces = _sample_surfaces()
        contract = synthesize_ecosystem_recovery("sample-eco", surfaces)

        target_slugs = [t.surface_slug for t in contract.backup_targets]
        self.assertIn("web", target_slugs)
        self.assertIn("api", target_slugs)
        self.assertIn("db", target_slugs)

        # Database target should have daily frequency and 30 days retention
        db_target = next(t for t in contract.backup_targets if t.surface_slug == "db")
        self.assertEqual(db_target.target_kind, "database")
        self.assertEqual(db_target.retention_days, 30)

        # Steps sequence order strictly ascending
        seq_orders = [s.sequence_order for s in contract.recovery_steps]
        self.assertEqual(seq_orders, sorted(seq_orders))
        self.assertEqual(seq_orders, list(range(1, len(seq_orders) + 1)))

        # Isolation step exists first
        first_step = contract.recovery_steps[0]
        self.assertEqual(first_step.action, "drain_traffic")

        # Re-enable live gateway routing exists last
        last_step = contract.recovery_steps[-1]
        self.assertEqual(last_step.action, "resume_traffic")

        # Rollback triggers present
        self.assertTrue(len(contract.rollback_triggers) >= 2)
        conditions = [t.condition for t in contract.rollback_triggers]
        self.assertIn("health_probe_failed", conditions)
        self.assertIn("migration_error", conditions)


# ---------------------------------------------------------------------------
# Evaluation Engine Tests
# ---------------------------------------------------------------------------


class TestEcosystemRecoveryEngine(unittest.TestCase):
    def setUp(self) -> None:
        surfaces = _sample_surfaces()
        self.contract = synthesize_ecosystem_recovery("sim-eco", surfaces)
        self.engine = EcosystemRecoveryEngine(self.contract)

    def test_simulate_snapshot_creation(self) -> None:
        target = self.contract.backup_targets[0]
        res = self.engine.simulate_snapshot_creation(target.target_id)
        self.assertIsInstance(res, SnapshotResult)
        self.assertEqual(res.status, "pass")
        self.assertEqual(res.target_id, target.target_id)
        self.assertTrue(len(res.checksum_sha256) == 64)
        self.assertGreater(res.size_bytes, 0)

    def test_simulate_recovery_plan(self) -> None:
        results = self.engine.simulate_recovery_plan()
        self.assertEqual(len(results), len(self.contract.recovery_steps))
        for res in results:
            self.assertIsInstance(res, RecoveryStepResult)
            self.assertEqual(res.status, "pass")
            self.assertGreater(res.duration_ms, 0)

    def test_simulate_rollback_triggers(self) -> None:
        results = self.engine.simulate_rollback_triggers()
        self.assertEqual(len(results), len(self.contract.rollback_triggers))
        for res in results:
            self.assertIsInstance(res, RollbackTriggerResult)
            self.assertEqual(res.status, "pass")

    def test_simulate_full_dr_exercise(self) -> None:
        full_res = self.engine.simulate_full_dr_exercise()
        self.assertEqual(full_res["status"], "pass")
        self.assertEqual(full_res["ecosystem_id"], "sim-eco")
        summary = full_res["summary"]
        self.assertEqual(summary["total_backup_targets"], len(self.contract.backup_targets))
        self.assertEqual(summary["total_recovery_steps"], len(self.contract.recovery_steps))
        self.assertEqual(summary["total_rollback_triggers"], len(self.contract.rollback_triggers))
        self.assertEqual(summary["snapshots_pass"], len(self.contract.backup_targets))
        self.assertEqual(summary["steps_pass"], len(self.contract.recovery_steps))
        self.assertEqual(summary["triggers_pass"], len(self.contract.rollback_triggers))


# ---------------------------------------------------------------------------
# Package & Registry Integration Tests
# ---------------------------------------------------------------------------


class TestPackRecoveryContractIntegration(unittest.TestCase):
    def test_synthesized_pack_has_recovery_contract(self) -> None:
        mb_pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        if mb_pack is None:
            self.skipTest("minimal-blog pack not available")
        pack = synthesize_ecosystem_pack(mb_pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)
        self.assertIsNotNone(pack.recovery_contract)
        self.assertIsInstance(pack.recovery_contract, EcosystemDisasterRecoveryContract)
        self.assertTrue(len(pack.recovery_contract.backup_targets) >= 1)
        self.assertTrue(len(pack.recovery_contract.recovery_steps) >= 1)

    def test_pack_json_roundtrip_includes_recovery_contract(self) -> None:
        mb_pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        if mb_pack is None:
            self.skipTest("minimal-blog pack not available")
        pack = synthesize_ecosystem_pack(mb_pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)
        d = pack.to_dict()
        self.assertIn("recovery_contract", d)
        parsed = parse_ecosystem_pack_package(d)
        self.assertIsNotNone(parsed.recovery_contract)
        self.assertEqual(parsed.recovery_contract.digest(), pack.recovery_contract.digest())


class TestRegistryGetRecoveryContract(unittest.TestCase):
    def test_get_recovery_contract_from_registry(self) -> None:
        contract = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_recovery_contract("minimal-blog-ecosystem")
        self.assertIsNotNone(contract)
        self.assertIsInstance(contract, EcosystemDisasterRecoveryContract)
        self.assertEqual(contract.ecosystem_id, "minimal-blog-ecosystem")

    def test_get_recovery_contract_returns_none_for_unknown(self) -> None:
        contract = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_recovery_contract("nonexistent-eco")
        self.assertIsNone(contract)


# ---------------------------------------------------------------------------
# Studio Server Endpoint Tests
# ---------------------------------------------------------------------------


class TestStudioEcosystemRecoveryEndpoints(unittest.TestCase):
    def setUp(self) -> None:
        surfaces = _sample_surfaces()
        self.contract = synthesize_ecosystem_recovery("studio-dr-eco", surfaces)
        self.engine = EcosystemRecoveryEngine(self.contract)

        def get_dr_fn() -> dict[str, str]:
            return self.contract.to_dict()

        def sim_dr_fn() -> dict[str, str]:
            return self.engine.simulate_full_dr_exercise()

        self.server = create_studio_server(
            lambda prompt, **kw: {"status": "ok"},
            host="127.0.0.1",
            port=0,
            get_ecosystem_recovery_fn=get_dr_fn,
            simulate_ecosystem_recovery_fn=sim_dr_fn,
        )
        self.server_thread = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.server_thread.submit(self.server.serve_forever)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.shutdown(wait=True)

    def test_get_ecosystem_recovery_endpoint(self) -> None:
        import urllib.request

        req = urllib.request.Request(f"{self.base_url}/api/ecosystem/recovery")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["ecosystem_id"], "studio-dr-eco")
            self.assertTrue(len(data["backup_targets"]) >= 1)

    def test_post_ecosystem_recovery_simulate_endpoint(self) -> None:
        import urllib.request

        req = urllib.request.Request(
            f"{self.base_url}/api/ecosystem/recovery/simulate",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "pass")
            self.assertIn("summary", data)


# ---------------------------------------------------------------------------
# CLI Subcommand Tests
# ---------------------------------------------------------------------------


class TestEcosystemCLIRecovery(unittest.TestCase):
    def test_recovery_inspect(self) -> None:
        import io
        from contextlib import redirect_stdout
        from omnistackai_agent_engine.solution_packs.ecosystem_cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["recovery", "minimal-blog-ecosystem"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("Disaster Recovery Contract", output)
        self.assertIn("Backup Targets:", output)
        self.assertIn("Recovery Steps:", output)

    def test_recovery_json(self) -> None:
        import io
        from contextlib import redirect_stdout
        from omnistackai_agent_engine.solution_packs.ecosystem_cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["recovery", "minimal-blog-ecosystem", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["ecosystem_id"], "minimal-blog-ecosystem")
        self.assertTrue(len(data["backup_targets"]) >= 1)

    def test_recovery_simulate(self) -> None:
        import io
        from contextlib import redirect_stdout
        from omnistackai_agent_engine.solution_packs.ecosystem_cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["recovery", "minimal-blog-ecosystem", "--simulate"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("Disaster Recovery Simulation", output)
        self.assertIn("OVERALL STATUS: PASS", output)


if __name__ == "__main__":
    unittest.main()

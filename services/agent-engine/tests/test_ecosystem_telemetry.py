"""Unit and integration tests for Ecosystem Cross-Surface Telemetry, Audit Trails,
and Distributed Tracing (R-449)."""

from __future__ import annotations

import json
import time
import unittest

from omnistackai_agent_engine.solution_packs.ecosystem_telemetry import (
    AuditTrailEntry,
    DistributedTrace,
    EcosystemTelemetryCollector,
    EcosystemTelemetryContract,
    TelemetrySamplingPolicy,
    TelemetrySpan,
    TracedSurface,
    synthesize_ecosystem_telemetry,
    _new_span_id,
    _new_trace_id,
    _span_digest,
)
from omnistackai_agent_engine.solution_packs.ecosystem_pack import (
    EcosystemSurfacePackage,
    synthesize_ecosystem_pack,
)
from omnistackai_agent_engine.solution_packs.ecosystem_registry import (
    DEFAULT_ECOSYSTEM_PACK_REGISTRY,
)
from omnistackai_agent_engine.studio.preview import StudioPreviewManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_minimal_surfaces() -> list[dict]:
    """Return two minimal surface-like dicts for testing synthesis."""
    return [
        {
            "slug": "customer-web",
            "surface_kind": "customer_web",
            "app_name": "Customer App",
            "ir_dict": {
                "entities": [
                    {"name": "Order"},
                    {"name": "Product"},
                ]
            },
        },
        {
            "slug": "admin-dashboard",
            "surface_kind": "admin_dashboard",
            "app_name": "Admin Dashboard",
            "ir_dict": {
                "entities": [
                    {"name": "Order"},
                    {"name": "User"},
                ]
            },
        },
    ]


# ---------------------------------------------------------------------------
# 1. ID Generators — deterministic format checks
# ---------------------------------------------------------------------------

class TestIdGenerators(unittest.TestCase):
    def test_trace_id_is_hex_48_chars(self) -> None:
        tid = _new_trace_id()
        self.assertEqual(len(tid), 48)
        int(tid, 16)  # must be valid hex

    def test_span_id_is_hex_16_chars(self) -> None:
        sid = _new_span_id()
        self.assertEqual(len(sid), 16)
        int(sid, 16)

    def test_two_trace_ids_are_unique(self) -> None:
        self.assertNotEqual(_new_trace_id(), _new_trace_id())

    def test_two_span_ids_are_unique(self) -> None:
        self.assertNotEqual(_new_span_id(), _new_span_id())

    def test_span_digest_is_deterministic(self) -> None:
        d1 = _span_digest("trace-abc", "span-def", "page.load")
        d2 = _span_digest("trace-abc", "span-def", "page.load")
        self.assertEqual(d1, d2)

    def test_span_digest_is_32_hex_chars(self) -> None:
        d = _span_digest("t1", "s1", "op")
        self.assertEqual(len(d), 32)
        int(d, 16)

    def test_span_digest_differs_for_different_operations(self) -> None:
        d1 = _span_digest("t1", "s1", "op-a")
        d2 = _span_digest("t1", "s1", "op-b")
        self.assertNotEqual(d1, d2)


# ---------------------------------------------------------------------------
# 2. TelemetrySpan — dataclass invariants and serialization
# ---------------------------------------------------------------------------

class TestTelemetrySpan(unittest.TestCase):
    def _make_span(self, **kwargs) -> TelemetrySpan:
        defaults = dict(
            span_id=_new_span_id(),
            trace_id=_new_trace_id(),
            parent_span_id=None,
            operation="page.load",
            surface="customer-web",
            start_time="2026-09-14T12:00:00+00:00",
            end_time="2026-09-14T12:00:00.120+00:00",
            duration_ms=120.0,
            status="ok",
        )
        defaults.update(kwargs)
        return TelemetrySpan(**defaults)

    def test_span_digest_auto_populated(self) -> None:
        span = self._make_span()
        self.assertTrue(len(span.span_digest) == 32)

    def test_roundtrip_dict(self) -> None:
        span = self._make_span(attributes={"http.method": "GET", "http.status": 200})
        d = span.to_dict()
        restored = TelemetrySpan.from_dict(d)
        self.assertEqual(span.span_id, restored.span_id)
        self.assertEqual(span.trace_id, restored.trace_id)
        self.assertEqual(span.operation, restored.operation)
        self.assertEqual(span.attributes, restored.attributes)

    def test_span_with_parent_preserved(self) -> None:
        parent_id = _new_span_id()
        span = self._make_span(parent_span_id=parent_id)
        self.assertEqual(span.parent_span_id, parent_id)
        restored = TelemetrySpan.from_dict(span.to_dict())
        self.assertEqual(restored.parent_span_id, parent_id)

    def test_error_span_roundtrip(self) -> None:
        span = self._make_span(status="error", error_message="500 Internal Server Error")
        d = span.to_dict()
        restored = TelemetrySpan.from_dict(d)
        self.assertEqual(restored.status, "error")
        self.assertEqual(restored.error_message, "500 Internal Server Error")


# ---------------------------------------------------------------------------
# 3. AuditTrailEntry — immutable, serialization
# ---------------------------------------------------------------------------

class TestAuditTrailEntry(unittest.TestCase):
    def _make_entry(self, **kwargs) -> AuditTrailEntry:
        defaults = dict(
            entry_id="",
            trace_id=_new_trace_id(),
            actor_surface="admin-dashboard",
            action="config.update",
            entity_name="User",
            entity_id="u-123",
            timestamp="2026-09-14T12:00:00+00:00",
            outcome="success",
        )
        defaults.update(kwargs)
        return AuditTrailEntry(**defaults)

    def test_entry_id_auto_populated_when_empty(self) -> None:
        entry = self._make_entry()
        self.assertTrue(entry.entry_id.startswith("aud_"))
        self.assertEqual(len(entry.entry_id), 20)  # "aud_" + 16 hex

    def test_roundtrip_dict(self) -> None:
        entry = self._make_entry(metadata={"reason": "admin-override"})
        restored = AuditTrailEntry.from_dict(entry.to_dict())
        self.assertEqual(entry.entry_id, restored.entry_id)
        self.assertEqual(entry.action, restored.action)
        self.assertEqual(entry.metadata, restored.metadata)

    def test_failure_outcome_preserved(self) -> None:
        entry = self._make_entry(outcome="failure", metadata={"error": "unauthorized"})
        restored = AuditTrailEntry.from_dict(entry.to_dict())
        self.assertEqual(restored.outcome, "failure")


# ---------------------------------------------------------------------------
# 4. EcosystemTelemetryCollector — span lifecycle, audit, bounded log
# ---------------------------------------------------------------------------

class TestEcosystemTelemetryCollector(unittest.TestCase):
    def _make_contract(self, ecosystem_id: str = "test-eco") -> EcosystemTelemetryContract:
        return EcosystemTelemetryContract(ecosystem_id=ecosystem_id)

    def test_start_span_recorded(self) -> None:
        collector = EcosystemTelemetryCollector(self._make_contract())
        span = collector.start_span("page.load", "customer-web")
        self.assertEqual(span.operation, "page.load")
        self.assertEqual(span.surface, "customer-web")
        self.assertEqual(collector.get_span_count(), 1)

    def test_finish_span_updates_duration_and_status(self) -> None:
        collector = EcosystemTelemetryCollector(self._make_contract())
        span = collector.start_span("api.request", "customer-web")
        time.sleep(0.01)
        finished = collector.finish_span(span, status="ok", duration_ms=15.5)
        self.assertEqual(finished.status, "ok")
        self.assertAlmostEqual(finished.duration_ms, 15.5)
        self.assertIsNotNone(finished.end_time)

    def test_finish_error_span(self) -> None:
        collector = EcosystemTelemetryCollector(self._make_contract())
        span = collector.start_span("webhook.deliver", "admin-dashboard")
        finished = collector.finish_span(span, status="error", error_message="Connection refused", duration_ms=200.0)
        self.assertEqual(finished.status, "error")
        self.assertEqual(finished.error_message, "Connection refused")

    def test_record_audit_entry(self) -> None:
        collector = EcosystemTelemetryCollector(self._make_contract())
        entry = collector.record_audit(
            "config.update", "Setting", "s-42", "admin-dashboard",
            outcome="success", metadata={"field": "timeout_seconds"}
        )
        self.assertEqual(collector.get_audit_count(), 1)
        self.assertEqual(entry.action, "config.update")
        self.assertEqual(entry.metadata["field"], "timeout_seconds")

    def test_bounded_span_log(self) -> None:
        collector = EcosystemTelemetryCollector(self._make_contract(), max_spans=5)
        for i in range(10):
            collector.start_span(f"op-{i}", "surface-a")
        self.assertEqual(collector.get_span_count(), 5)

    def test_bounded_audit_log(self) -> None:
        collector = EcosystemTelemetryCollector(self._make_contract(), max_audit_entries=3)
        for i in range(6):
            collector.record_audit(f"action-{i}", "Entity", f"e-{i}", "admin-dashboard")
        self.assertEqual(collector.get_audit_count(), 3)

    def test_get_spans_newest_first(self) -> None:
        collector = EcosystemTelemetryCollector(self._make_contract())
        collector.start_span("op-a", "surface-x")
        collector.start_span("op-b", "surface-x")
        spans = collector.get_spans(limit=2)
        self.assertEqual(spans[0]["operation"], "op-b")
        self.assertEqual(spans[1]["operation"], "op-a")

    def test_build_trace_assembles_spans(self) -> None:
        collector = EcosystemTelemetryCollector(self._make_contract())
        trace_id = _new_trace_id()
        s1 = collector.start_span("page.load", "customer-web", trace_id=trace_id)
        s2 = collector.start_span("api.request", "customer-web", trace_id=trace_id, parent_span_id=s1.span_id)
        collector.finish_span(s1, duration_ms=50.0)
        collector.finish_span(s2, duration_ms=30.0)
        trace = collector.build_trace(trace_id)
        self.assertIsNotNone(trace)
        assert trace is not None  # type guard
        self.assertEqual(trace.span_count, 2)
        self.assertAlmostEqual(trace.total_duration_ms, 80.0)
        self.assertEqual(trace.status, "ok")
        self.assertEqual(trace.root_operation, "page.load")

    def test_build_trace_returns_none_for_unknown_id(self) -> None:
        collector = EcosystemTelemetryCollector(self._make_contract())
        result = collector.build_trace("nonexistent-trace-id")
        self.assertIsNone(result)

    def test_clear_resets_all_logs(self) -> None:
        collector = EcosystemTelemetryCollector(self._make_contract())
        collector.start_span("op", "surface")
        collector.record_audit("action", "Entity", "e-1", "surface")
        collector.clear()
        self.assertEqual(collector.get_span_count(), 0)
        self.assertEqual(collector.get_audit_count(), 0)


# ---------------------------------------------------------------------------
# 5. EcosystemTelemetryContract — synthesis and roundtrip
# ---------------------------------------------------------------------------

class TestEcosystemTelemetryContractSynthesis(unittest.TestCase):
    def test_synthesize_produces_valid_contract(self) -> None:
        surfaces = _make_minimal_surfaces()
        contract = synthesize_ecosystem_telemetry("test-eco", surfaces)
        self.assertEqual(contract.ecosystem_id, "test-eco")
        self.assertEqual(len(contract.traced_surfaces), 2)
        self.assertIn("ecosystem.event.dispatch", contract.cross_surface_operations)

    def test_synthesize_detects_admin_surface_emits_audit(self) -> None:
        surfaces = _make_minimal_surfaces()
        contract = synthesize_ecosystem_telemetry("eco-2", surfaces)
        admin_surface = next(
            (ts for ts in contract.traced_surfaces if ts.surface_slug == "admin-dashboard"), None
        )
        self.assertIsNotNone(admin_surface)
        assert admin_surface is not None
        self.assertTrue(admin_surface.emits_audit_events)

    def test_synthesize_customer_web_does_not_emit_audit(self) -> None:
        surfaces = _make_minimal_surfaces()
        contract = synthesize_ecosystem_telemetry("eco-3", surfaces)
        cw = next(
            (ts for ts in contract.traced_surfaces if ts.surface_slug == "customer-web"), None
        )
        self.assertIsNotNone(cw)
        assert cw is not None
        self.assertFalse(cw.emits_audit_events)

    def test_synthesize_includes_entity_cross_surface_ops(self) -> None:
        surfaces = _make_minimal_surfaces()
        contract = synthesize_ecosystem_telemetry("eco-4", surfaces)
        # order.cross-surface.sync should be derived from shared entity "Order"
        self.assertIn("order.cross-surface.sync", contract.cross_surface_operations)

    def test_contract_roundtrip_json(self) -> None:
        surfaces = _make_minimal_surfaces()
        contract = synthesize_ecosystem_telemetry("eco-5", surfaces)
        d = contract.to_dict()
        raw = json.dumps(d)
        restored = EcosystemTelemetryContract.from_dict(json.loads(raw))
        self.assertEqual(contract.ecosystem_id, restored.ecosystem_id)
        self.assertEqual(len(contract.traced_surfaces), len(restored.traced_surfaces))
        self.assertEqual(contract.cross_surface_operations, restored.cross_surface_operations)
        self.assertEqual(contract.audit_actions, restored.audit_actions)


# ---------------------------------------------------------------------------
# 6. EcosystemPackPackage — telemetry_contract bundled with checksum integrity
# ---------------------------------------------------------------------------

class TestEcosystemPackTelemetry(unittest.TestCase):
    def test_synthesize_ecosystem_pack_includes_telemetry_contract(self) -> None:
        from omnistackai_agent_engine.solution_packs.registry import DEFAULT_SOLUTION_PACK_REGISTRY
        pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        if pack is None:
            self.skipTest("minimal-blog pack not registered")
        pkg = synthesize_ecosystem_pack(pack)
        # telemetry_contract must be attached
        self.assertIsNotNone(pkg.telemetry_contract)
        assert pkg.telemetry_contract is not None
        self.assertEqual(pkg.telemetry_contract.ecosystem_id, pkg.ecosystem_id)
        self.assertGreater(len(pkg.telemetry_contract.traced_surfaces), 0)

    def test_ecosystem_pack_checksum_still_valid_after_telemetry(self) -> None:
        """Confirm checksum verification does not break after adding telemetry_contract."""
        from omnistackai_agent_engine.solution_packs.registry import DEFAULT_SOLUTION_PACK_REGISTRY
        from omnistackai_agent_engine.solution_packs.ecosystem_pack import (
            parse_ecosystem_pack_package,
        )
        pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        if pack is None:
            self.skipTest("minimal-blog pack not registered")
        pkg = synthesize_ecosystem_pack(pack)
        # Serialize → re-parse should pass checksum verification
        raw_json = pkg.to_json()
        restored = parse_ecosystem_pack_package(raw_json)
        self.assertEqual(restored.ecosystem_id, pkg.ecosystem_id)
        self.assertIsNotNone(restored.telemetry_contract)


# ---------------------------------------------------------------------------
# 7. StudioPreviewManager — telemetry contract injected into preview status
# ---------------------------------------------------------------------------

class TestStudioPreviewManagerTelemetry(unittest.TestCase):
    def test_initial_status_lacks_telemetry(self) -> None:
        manager = StudioPreviewManager()
        status = manager.status()
        # Before any ecosystem is started, telemetry fields should be absent or False
        self.assertFalse(status.get("has_telemetry", False))

    def test_get_ecosystem_telemetry_returns_not_active_when_no_ecosystem(self) -> None:
        manager = StudioPreviewManager()
        result = manager.get_ecosystem_telemetry()
        self.assertFalse(result.get("is_ecosystem", True))
        self.assertIsNone(result.get("telemetry_contract"))


if __name__ == "__main__":
    unittest.main()

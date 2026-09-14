"""Ecosystem Cross-Surface Telemetry, Audit Trails, and Distributed Tracing Engine (R-449).

Defines canonical telemetry spans, audit trail entries, distributed traces, and an
in-process telemetry contract enabling deterministic, verified cross-surface observability
for multi-surface applications with stdlib-only trace/span ID generation
(uuid + hashlib, 0 external dependencies, 100% offline).
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Mapping, Sequence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_trace_id() -> str:
    """Generate a deterministic-looking, unique trace ID (128-bit hex)."""
    return uuid.uuid4().hex + uuid.uuid4().hex[:16]


def _new_span_id() -> str:
    """Generate a unique span ID (64-bit hex)."""
    return uuid.uuid4().hex[:16]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _span_digest(trace_id: str, span_id: str, operation: str) -> str:
    """Deterministic content hash for a span (used for idempotency)."""
    raw = f"{trace_id}:{span_id}:{operation}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Dataclasses — public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TelemetrySpan:
    """A single instrumented operation within a distributed trace."""

    span_id: str
    trace_id: str
    parent_span_id: str | None
    operation: str
    surface: str
    start_time: str
    end_time: str | None
    duration_ms: float
    status: str           # "ok", "error", "timeout"
    error_message: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    span_digest: str = ""

    def __post_init__(self) -> None:
        if not self.span_digest:
            object.__setattr__(
                self,
                "span_digest",
                _span_digest(self.trace_id, self.span_id, self.operation),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation": self.operation,
            "surface": self.surface,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_message": self.error_message,
            "attributes": dict(self.attributes),
            "span_digest": self.span_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TelemetrySpan:
        return cls(
            span_id=str(data["span_id"]),
            trace_id=str(data["trace_id"]),
            parent_span_id=str(data["parent_span_id"]) if data.get("parent_span_id") else None,
            operation=str(data["operation"]),
            surface=str(data["surface"]),
            start_time=str(data["start_time"]),
            end_time=str(data["end_time"]) if data.get("end_time") else None,
            duration_ms=float(data.get("duration_ms", 0.0)),
            status=str(data.get("status", "ok")),
            error_message=str(data["error_message"]) if data.get("error_message") else None,
            attributes=dict(data.get("attributes", {})),
            span_digest=str(data.get("span_digest", "")),
        )


@dataclass(frozen=True, slots=True)
class AuditTrailEntry:
    """Immutable audit log entry recording a cross-surface ecosystem action."""

    entry_id: str
    trace_id: str
    actor_surface: str
    action: str          # e.g. "user.login", "order.created", "config.updated"
    entity_name: str
    entity_id: str
    timestamp: str
    outcome: str         # "success", "failure", "skipped"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.entry_id:
            object.__setattr__(self, "entry_id", f"aud_{uuid.uuid4().hex[:16]}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "trace_id": self.trace_id,
            "actor_surface": self.actor_surface,
            "action": self.action,
            "entity_name": self.entity_name,
            "entity_id": self.entity_id,
            "timestamp": self.timestamp,
            "outcome": self.outcome,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AuditTrailEntry:
        return cls(
            entry_id=str(data.get("entry_id", "")),
            trace_id=str(data["trace_id"]),
            actor_surface=str(data["actor_surface"]),
            action=str(data["action"]),
            entity_name=str(data["entity_name"]),
            entity_id=str(data["entity_id"]),
            timestamp=str(data["timestamp"]),
            outcome=str(data.get("outcome", "success")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class DistributedTrace:
    """A collection of spans forming a complete distributed trace across surfaces."""

    trace_id: str
    root_operation: str
    root_surface: str
    start_time: str
    end_time: str | None
    total_duration_ms: float
    span_count: int
    surfaces_involved: tuple[str, ...]
    status: str           # "ok", "error", "partial"
    spans: tuple[TelemetrySpan, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "root_operation": self.root_operation,
            "root_surface": self.root_surface,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_ms": self.total_duration_ms,
            "span_count": self.span_count,
            "surfaces_involved": list(self.surfaces_involved),
            "status": self.status,
            "spans": [s.to_dict() for s in self.spans],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DistributedTrace:
        spans = tuple(
            TelemetrySpan.from_dict(s) for s in data.get("spans", []) if isinstance(s, dict)
        )
        return cls(
            trace_id=str(data["trace_id"]),
            root_operation=str(data["root_operation"]),
            root_surface=str(data["root_surface"]),
            start_time=str(data["start_time"]),
            end_time=str(data["end_time"]) if data.get("end_time") else None,
            total_duration_ms=float(data.get("total_duration_ms", 0.0)),
            span_count=int(data.get("span_count", len(spans))),
            surfaces_involved=tuple(str(s) for s in data.get("surfaces_involved", [])),
            status=str(data.get("status", "ok")),
            spans=spans,
        )


@dataclass(frozen=True, slots=True)
class TelemetrySamplingPolicy:
    """Configurable sampling policy for telemetry spans."""

    sampling_rate: float = 1.0          # 0.0–1.0; 1.0 = always sample
    max_spans_per_trace: int = 128
    export_format: str = "otlp-json"    # "otlp-json", "ndjson", "none"
    propagation_header: str = "X-OmniStack-Trace-Id"
    audit_header: str = "X-OmniStack-Audit-Id"

    def to_dict(self) -> dict[str, Any]:
        return {
            "sampling_rate": self.sampling_rate,
            "max_spans_per_trace": self.max_spans_per_trace,
            "export_format": self.export_format,
            "propagation_header": self.propagation_header,
            "audit_header": self.audit_header,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TelemetrySamplingPolicy:
        return cls(
            sampling_rate=float(data.get("sampling_rate", 1.0)),
            max_spans_per_trace=int(data.get("max_spans_per_trace", 128)),
            export_format=str(data.get("export_format", "otlp-json")),
            propagation_header=str(data.get("propagation_header", "X-OmniStack-Trace-Id")),
            audit_header=str(data.get("audit_header", "X-OmniStack-Audit-Id")),
        )


@dataclass(frozen=True, slots=True)
class TracedSurface:
    """Configuration for a single instrumented surface in the telemetry contract."""

    surface_slug: str
    display_name: str
    instrumented_operations: tuple[str, ...]
    emits_audit_events: bool = True
    sampling_policy: TelemetrySamplingPolicy = field(default_factory=TelemetrySamplingPolicy)

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_slug": self.surface_slug,
            "display_name": self.display_name,
            "instrumented_operations": list(self.instrumented_operations),
            "emits_audit_events": self.emits_audit_events,
            "sampling_policy": self.sampling_policy.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TracedSurface:
        policy_raw = data.get("sampling_policy")
        policy = TelemetrySamplingPolicy.from_dict(policy_raw) if isinstance(policy_raw, dict) else TelemetrySamplingPolicy()
        return cls(
            surface_slug=str(data["surface_slug"]),
            display_name=str(data.get("display_name", data["surface_slug"])),
            instrumented_operations=tuple(str(op) for op in data.get("instrumented_operations", ())),
            emits_audit_events=bool(data.get("emits_audit_events", True)),
            sampling_policy=policy,
        )


@dataclass(frozen=True, slots=True)
class EcosystemTelemetryContract:
    """Contract formalizing cross-surface telemetry, audit trails, and distributed tracing."""

    ecosystem_id: str
    version: str = "1.0"
    trace_id_algorithm: str = "uuid4-hex128"
    span_id_algorithm: str = "uuid4-hex64"
    default_sampling_policy: TelemetrySamplingPolicy = field(default_factory=TelemetrySamplingPolicy)
    traced_surfaces: tuple[TracedSurface, ...] = ()
    cross_surface_operations: tuple[str, ...] = ()
    audit_actions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "trace_id_algorithm": self.trace_id_algorithm,
            "span_id_algorithm": self.span_id_algorithm,
            "default_sampling_policy": self.default_sampling_policy.to_dict(),
            "traced_surfaces": [s.to_dict() for s in self.traced_surfaces],
            "cross_surface_operations": list(self.cross_surface_operations),
            "audit_actions": list(self.audit_actions),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemTelemetryContract:
        policy_raw = data.get("default_sampling_policy")
        policy = TelemetrySamplingPolicy.from_dict(policy_raw) if isinstance(policy_raw, dict) else TelemetrySamplingPolicy()
        traced_surfaces = tuple(
            TracedSurface.from_dict(s)
            for s in data.get("traced_surfaces", [])
            if isinstance(s, dict)
        )
        return cls(
            ecosystem_id=str(data["ecosystem_id"]),
            version=str(data.get("version", "1.0")),
            trace_id_algorithm=str(data.get("trace_id_algorithm", "uuid4-hex128")),
            span_id_algorithm=str(data.get("span_id_algorithm", "uuid4-hex64")),
            default_sampling_policy=policy,
            traced_surfaces=traced_surfaces,
            cross_surface_operations=tuple(str(op) for op in data.get("cross_surface_operations", ())),
            audit_actions=tuple(str(a) for a in data.get("audit_actions", ())),
        )


# ---------------------------------------------------------------------------
# In-Process Telemetry Collector
# ---------------------------------------------------------------------------


class EcosystemTelemetryCollector:
    """In-process telemetry and audit trail collector for multi-surface ecosystems.

    Maintains bounded span log (max_spans) and audit trail (max_audit_entries).
    Thread-safe via RLock. 0 external dependencies, 100% offline.
    """

    def __init__(
        self,
        contract: EcosystemTelemetryContract,
        *,
        max_spans: int = 500,
        max_audit_entries: int = 500,
    ) -> None:
        self._contract = contract
        self._max_spans = max_spans
        self._max_audit_entries = max_audit_entries
        self._spans: list[TelemetrySpan] = []
        self._audit_trail: list[AuditTrailEntry] = []
        self._lock = RLock()

    @property
    def contract(self) -> EcosystemTelemetryContract:
        return self._contract

    def start_span(
        self,
        operation: str,
        surface: str,
        *,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TelemetrySpan:
        """Create and record a new span, returning it.

        The span is recorded immediately with status='ok' and duration_ms=0.0 as a
        placeholder. Call ``finish_span`` to update with actual duration.
        """
        span_id = _new_span_id()
        tid = trace_id or _new_trace_id()
        now = _now_iso()
        span = TelemetrySpan(
            span_id=span_id,
            trace_id=tid,
            parent_span_id=parent_span_id,
            operation=operation,
            surface=surface,
            start_time=now,
            end_time=None,
            duration_ms=0.0,
            status="ok",
            error_message=None,
            attributes=dict(attributes or {}),
        )
        with self._lock:
            self._spans.append(span)
            if len(self._spans) > self._max_spans:
                self._spans.pop(0)
        return span

    def finish_span(
        self,
        span: TelemetrySpan,
        *,
        status: str = "ok",
        error_message: str | None = None,
        duration_ms: float | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TelemetrySpan:
        """Finish a span with timing, status, and optional error info.

        Returns the updated frozen span. The collector removes the placeholder and
        appends the finished span.
        """
        end_time = _now_iso()
        if duration_ms is None:
            # Parse ISO start_time to compute duration if possible
            try:
                from datetime import datetime, timezone
                start_dt = datetime.fromisoformat(span.start_time)
                end_dt = datetime.now(timezone.utc)
                duration_ms = (end_dt - start_dt).total_seconds() * 1000.0
            except Exception:
                duration_ms = 0.0

        merged_attrs = dict(span.attributes)
        if attributes:
            merged_attrs.update(attributes)

        finished = TelemetrySpan(
            span_id=span.span_id,
            trace_id=span.trace_id,
            parent_span_id=span.parent_span_id,
            operation=span.operation,
            surface=span.surface,
            start_time=span.start_time,
            end_time=end_time,
            duration_ms=round(duration_ms, 3),
            status=status,
            error_message=error_message,
            attributes=merged_attrs,
        )
        with self._lock:
            # Replace the placeholder if it exists, otherwise just append
            for i, s in enumerate(self._spans):
                if s.span_id == span.span_id and s.end_time is None:
                    self._spans[i] = finished
                    break
            else:
                self._spans.append(finished)
                if len(self._spans) > self._max_spans:
                    self._spans.pop(0)
        return finished

    def record_audit(
        self,
        action: str,
        entity_name: str,
        entity_id: str,
        actor_surface: str,
        *,
        trace_id: str | None = None,
        outcome: str = "success",
        metadata: dict[str, Any] | None = None,
    ) -> AuditTrailEntry:
        """Record an immutable audit trail entry."""
        entry = AuditTrailEntry(
            entry_id="",
            trace_id=trace_id or _new_trace_id(),
            actor_surface=actor_surface,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            timestamp=_now_iso(),
            outcome=outcome,
            metadata=dict(metadata or {}),
        )
        with self._lock:
            self._audit_trail.append(entry)
            if len(self._audit_trail) > self._max_audit_entries:
                self._audit_trail.pop(0)
        return entry

    def build_trace(self, trace_id: str) -> DistributedTrace | None:
        """Assemble a DistributedTrace from all recorded spans for the given trace_id."""
        with self._lock:
            spans = [s for s in self._spans if s.trace_id == trace_id]
        if not spans:
            return None
        root = min(spans, key=lambda s: s.start_time)
        finished_spans = [s for s in spans if s.end_time is not None]
        total_duration = sum(s.duration_ms for s in finished_spans)
        surfaces_involved = tuple(sorted({s.surface for s in spans}))
        any_error = any(s.status == "error" for s in spans)
        any_open = any(s.end_time is None for s in spans)
        status = "error" if any_error else ("partial" if any_open else "ok")
        return DistributedTrace(
            trace_id=trace_id,
            root_operation=root.operation,
            root_surface=root.surface,
            start_time=root.start_time,
            end_time=max((s.end_time for s in spans if s.end_time), default=None),
            total_duration_ms=round(total_duration, 3),
            span_count=len(spans),
            surfaces_involved=surfaces_involved,
            status=status,
            spans=tuple(spans),
        )

    def get_spans(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return most recent spans, newest first."""
        with self._lock:
            spans = list(reversed(self._spans[-limit:]))
        return [s.to_dict() for s in spans]

    def get_audit_trail(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return most recent audit trail entries, newest first."""
        with self._lock:
            entries = list(reversed(self._audit_trail[-limit:]))
        return [e.to_dict() for e in entries]

    def get_span_count(self) -> int:
        with self._lock:
            return len(self._spans)

    def get_audit_count(self) -> int:
        with self._lock:
            return len(self._audit_trail)

    def clear(self) -> None:
        """Clear all collected spans and audit entries."""
        with self._lock:
            self._spans.clear()
            self._audit_trail.clear()


# ---------------------------------------------------------------------------
# Deterministic Synthesis
# ---------------------------------------------------------------------------

# Standard instrumented operations per surface kind
_SURFACE_KIND_OPERATIONS: dict[str, tuple[str, ...]] = {
    "customer_web": ("page.load", "api.request", "auth.login", "form.submit", "error.boundary"),
    "customer_pwa": ("page.load", "api.request", "auth.login", "form.submit", "offline.sync"),
    "public_web": ("page.load", "api.request", "search.query", "content.load"),
    "operator_portal": ("page.load", "api.request", "auth.login", "bulk.action", "report.export"),
    "admin_dashboard": ("page.load", "api.request", "auth.login", "config.update", "audit.view"),
    "provider_portal": ("page.load", "api.request", "auth.login", "listing.update", "order.manage"),
    "driver_pwa": ("page.load", "api.request", "auth.login", "trip.accept", "offline.sync"),
    "analytics_dashboard": ("page.load", "api.request", "dashboard.load", "chart.render", "export.run"),
    "mobile_web": ("page.load", "api.request", "auth.login", "form.submit"),
}

# Standard cross-surface operations for any ecosystem
_COMMON_CROSS_SURFACE_OPS = (
    "ecosystem.event.dispatch",
    "ecosystem.auth.verify",
    "ecosystem.state.sync",
    "webhook.deliver",
    "trace.propagate",
)

# Standard audit actions per surface kind
_SURFACE_KIND_AUDIT_ACTIONS: dict[str, tuple[str, ...]] = {
    "operator_portal": ("record.create", "record.update", "record.delete", "config.change", "user.assign"),
    "admin_dashboard": ("config.update", "user.create", "user.deactivate", "permission.grant", "audit.export"),
    "provider_portal": ("listing.publish", "listing.update", "order.accept", "order.reject"),
    "customer_web": ("order.placed", "payment.initiated", "review.submitted"),
    "customer_pwa": ("order.placed", "payment.initiated"),
    "driver_pwa": ("trip.accepted", "trip.completed", "trip.cancelled"),
}


def synthesize_ecosystem_telemetry(
    ecosystem_id: str,
    surfaces: Sequence[Any],
) -> EcosystemTelemetryContract:
    """Deterministically derive an EcosystemTelemetryContract from ecosystem surfaces.

    Infers instrumented operations and audit actions from each surface's kind and
    the shared entity model. 0 model calls, 100% offline, stdlib only.
    """
    traced: list[TracedSurface] = []
    audit_actions_set: set[str] = set()
    cross_ops_set: set[str] = set(_COMMON_CROSS_SURFACE_OPS)

    for s in surfaces:
        slug = getattr(s, "slug", s.get("slug", "") if isinstance(s, dict) else "")
        surface_kind = getattr(s, "surface_kind", s.get("surface_kind", "") if isinstance(s, dict) else "")
        app_name = getattr(s, "app_name", s.get("app_name", slug) if isinstance(s, dict) else slug)
        ir_dict = getattr(s, "ir_dict", s.get("ir_dict") if isinstance(s, dict) else None)

        # Collect entity-derived operations
        entity_names: list[str] = []
        if ir_dict and isinstance(ir_dict, dict) and "entities" in ir_dict:
            entity_names = [
                e["name"].lower() for e in ir_dict["entities"]
                if isinstance(e, dict) and "name" in e
            ]

        # Surface-kind base operations
        base_ops = _SURFACE_KIND_OPERATIONS.get(surface_kind, ("page.load", "api.request", "auth.login", "error.boundary"))
        entity_ops = tuple(
            f"{ent}.{action}"
            for ent in entity_names[:6]  # bounded: first 6 entities
            for action in ("fetch", "mutate")
        )
        instrumented_ops = base_ops + entity_ops

        # Surface-kind audit actions
        base_audit = _SURFACE_KIND_AUDIT_ACTIONS.get(surface_kind, ())
        entity_audit = tuple(f"{ent}.modified" for ent in entity_names[:4])
        all_audit = tuple(dict.fromkeys(base_audit + entity_audit))  # deduplicated, ordered
        audit_actions_set.update(all_audit)

        emits_audit = (
            "admin" in surface_kind
            or "operator" in surface_kind
            or "provider" in surface_kind
            or "driver" in surface_kind
        )

        traced.append(
            TracedSurface(
                surface_slug=slug,
                display_name=app_name,
                instrumented_operations=instrumented_ops,
                emits_audit_events=emits_audit,
                sampling_policy=TelemetrySamplingPolicy(),
            )
        )

        # Cross-surface operations from entity names
        for ent in entity_names[:6]:
            cross_ops_set.add(f"{ent}.cross-surface.sync")

    # Add ecosystem-level global audit actions
    audit_actions_set.update(("ecosystem.surface.started", "ecosystem.surface.stopped", "ecosystem.auth.token.minted"))

    sorted_cross_ops = tuple(sorted(cross_ops_set))
    sorted_audit_actions = tuple(sorted(audit_actions_set))

    return EcosystemTelemetryContract(
        ecosystem_id=ecosystem_id,
        version="1.0",
        trace_id_algorithm="uuid4-hex128",
        span_id_algorithm="uuid4-hex64",
        default_sampling_policy=TelemetrySamplingPolicy(),
        traced_surfaces=tuple(traced),
        cross_surface_operations=sorted_cross_ops,
        audit_actions=sorted_audit_actions,
    )

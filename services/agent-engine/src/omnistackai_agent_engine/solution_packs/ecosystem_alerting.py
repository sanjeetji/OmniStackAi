"""Ecosystem Multi-Surface Alerting, Incident Runbooks, and Escalation Policies (R-456).

Provides canonical alert rules, metric thresholds, incident runbooks with automated
and manual remediation steps, and multi-tiered escalation policies across all ecosystem
surfaces. An in-process thread-safe EcosystemAlertingEngine evaluates alert triggers,
executes runbook step dry-runs, and simulates incident escalation sequences offline.

Zero external dependencies — Python 3.13 stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal


AlertSeverity = Literal["info", "warning", "critical", "fatal"]
ConditionOperator = Literal[">", ">=", "<", "<=", "=="]


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AlertRule:
    """A metric-driven alert rule targeting an ecosystem surface."""

    rule_id: str
    surface_slug: str
    metric_name: str
    condition: ConditionOperator
    threshold: float
    duration_seconds: int
    severity: AlertSeverity
    description: str
    runbook_id: str
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "surface_slug": self.surface_slug,
            "metric_name": self.metric_name,
            "condition": self.condition,
            "threshold": self.threshold,
            "duration_seconds": self.duration_seconds,
            "severity": self.severity,
            "description": self.description,
            "runbook_id": self.runbook_id,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AlertRule:
        raw_cond = str(data.get("condition", ">"))
        cond: ConditionOperator = raw_cond if raw_cond in (">", ">=", "<", "<=", "==") else ">"  # type: ignore[assignment]
        raw_sev = str(data.get("severity", "warning")).lower()
        sev: AlertSeverity = raw_sev if raw_sev in ("info", "warning", "critical", "fatal") else "warning"  # type: ignore[assignment]
        return cls(
            rule_id=str(data.get("rule_id", "")),
            surface_slug=str(data.get("surface_slug", "")),
            metric_name=str(data.get("metric_name", "")),
            condition=cond,
            threshold=float(data.get("threshold", 0.0)),
            duration_seconds=int(data.get("duration_seconds", 60)),
            severity=sev,
            description=str(data.get("description", "")),
            runbook_id=str(data.get("runbook_id", "")),
            tags=tuple(str(t) for t in data.get("tags", ())),
        )


@dataclass(frozen=True, slots=True)
class RunbookStep:
    """An ordered mitigation step within an incident runbook."""

    step_id: str
    order: int
    action: str  # e.g. "inspect_telemetry", "scale_replicas", "drain_traffic", "restart_service", "notify_stakeholders"
    target: str
    description: str
    is_automated: bool = False
    remediation_command: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "step_id": self.step_id,
            "order": self.order,
            "action": self.action,
            "target": self.target,
            "description": self.description,
            "is_automated": self.is_automated,
        }
        if self.remediation_command is not None:
            result["remediation_command"] = self.remediation_command
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RunbookStep:
        return cls(
            step_id=str(data.get("step_id", "")),
            order=int(data.get("order", 1)),
            action=str(data.get("action", "inspect_telemetry")),
            target=str(data.get("target", "")),
            description=str(data.get("description", "")),
            is_automated=bool(data.get("is_automated", False)),
            remediation_command=str(data["remediation_command"]) if data.get("remediation_command") else None,
        )


@dataclass(frozen=True, slots=True)
class IncidentRunbook:
    """An incident remediation runbook linking an alert to sequenced steps."""

    runbook_id: str
    title: str
    severity: AlertSeverity
    summary: str
    steps: tuple[RunbookStep, ...]
    escalation_policy_id: str
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "runbook_id": self.runbook_id,
            "title": self.title,
            "severity": self.severity,
            "summary": self.summary,
            "steps": [s.to_dict() for s in self.steps],
            "escalation_policy_id": self.escalation_policy_id,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> IncidentRunbook:
        raw_sev = str(data.get("severity", "warning")).lower()
        sev: AlertSeverity = raw_sev if raw_sev in ("info", "warning", "critical", "fatal") else "warning"  # type: ignore[assignment]
        raw_steps = data.get("steps", ())
        steps = tuple(RunbookStep.from_dict(s) for s in raw_steps) if isinstance(raw_steps, Sequence) else ()
        return cls(
            runbook_id=str(data.get("runbook_id", "")),
            title=str(data.get("title", "")),
            severity=sev,
            summary=str(data.get("summary", "")),
            steps=steps,
            escalation_policy_id=str(data.get("escalation_policy_id", "")),
            tags=tuple(str(t) for t in data.get("tags", ())),
        )


@dataclass(frozen=True, slots=True)
class EscalationTier:
    """A responder tier within an escalation policy."""

    tier: int
    target_channel: str  # e.g. "slack-alerts-p0", "pagerduty-primary-oncall", "executive-escalation"
    wait_minutes: int
    auto_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "tier": self.tier,
            "target_channel": self.target_channel,
            "wait_minutes": self.wait_minutes,
        }
        if self.auto_action is not None:
            result["auto_action"] = self.auto_action
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EscalationTier:
        return cls(
            tier=int(data.get("tier", 1)),
            target_channel=str(data.get("target_channel", "")),
            wait_minutes=int(data.get("wait_minutes", 0)),
            auto_action=str(data["auto_action"]) if data.get("auto_action") else None,
        )


@dataclass(frozen=True, slots=True)
class EscalationPolicy:
    """A multi-tiered escalation policy for incident notification and response."""

    policy_id: str
    name: str
    description: str
    tiers: tuple[EscalationTier, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "tiers": [t.to_dict() for t in self.tiers],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EscalationPolicy:
        raw_tiers = data.get("tiers", ())
        tiers = tuple(EscalationTier.from_dict(t) for t in raw_tiers) if isinstance(raw_tiers, Sequence) else ()
        return cls(
            policy_id=str(data.get("policy_id", "")),
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            tiers=tiers,
        )


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EcosystemAlertingContract:
    """Canonical multi-surface contract defining alert rules, runbooks,
    and escalation policies for an entire ecosystem pack.
    """

    ecosystem_id: str
    version: str
    alert_rules: tuple[AlertRule, ...]
    runbooks: tuple[IncidentRunbook, ...]
    escalation_policies: tuple[EscalationPolicy, ...]

    def digest(self) -> str:
        """Deterministic SHA-256 digest of canonical serialized payload."""
        canonical_json = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "alert_rules": [r.to_dict() for r in self.alert_rules],
            "runbooks": [rb.to_dict() for rb in self.runbooks],
            "escalation_policies": [ep.to_dict() for ep in self.escalation_policies],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemAlertingContract:
        raw_rules = data.get("alert_rules", ())
        rules = tuple(AlertRule.from_dict(r) for r in raw_rules) if isinstance(raw_rules, Sequence) else ()

        raw_rbs = data.get("runbooks", ())
        runbooks = tuple(IncidentRunbook.from_dict(rb) for rb in raw_rbs) if isinstance(raw_rbs, Sequence) else ()

        raw_eps = data.get("escalation_policies", ())
        policies = tuple(EscalationPolicy.from_dict(ep) for ep in raw_eps) if isinstance(raw_eps, Sequence) else ()

        return cls(
            ecosystem_id=str(data.get("ecosystem_id", "")),
            version=str(data.get("version", "1.0.0")),
            alert_rules=rules,
            runbooks=runbooks,
            escalation_policies=policies,
        )

    @classmethod
    def from_json(cls, json_str: str) -> EcosystemAlertingContract:
        return cls.from_dict(json.loads(json_str))


# ---------------------------------------------------------------------------
# Contract Synthesis
# ---------------------------------------------------------------------------


def _surface_kind_from(surface: Any) -> str:
    if isinstance(surface, Mapping):
        return str(surface.get("surface_kind", surface.get("kind", "customer_web")))
    return str(getattr(surface, "surface_kind", getattr(surface, "kind", "customer_web")))


def _surface_slug_from(surface: Any) -> str:
    if isinstance(surface, Mapping):
        return str(surface.get("slug", "surface"))
    return str(getattr(surface, "slug", "surface"))


def synthesize_ecosystem_alerting(
    ecosystem_id: str,
    surfaces: Sequence[Mapping[str, Any]],
    version: str = "1.0.0",
) -> EcosystemAlertingContract:
    """Synthesize canonical multi-surface alert rules, incident runbooks,
    and escalation policies for an ecosystem.

    Fully deterministic, 100% offline, 0 network or filesystem I/O.
    """
    rules: list[AlertRule] = []
    runbooks: list[IncidentRunbook] = []

    # Standard escalation policies
    critical_policy = EscalationPolicy(
        policy_id="esc-critical-platform",
        name="Critical Platform Escalation",
        description="Tiered response for service outages, data corruption, and P0 latency/error spikes.",
        tiers=(
            EscalationTier(tier=1, target_channel="slack-alerts-p0", wait_minutes=0, auto_action="auto_remediate"),
            EscalationTier(tier=2, target_channel="pagerduty-primary-oncall", wait_minutes=10, auto_action="scale_out"),
            EscalationTier(tier=3, target_channel="pagerduty-eng-lead", wait_minutes=25, auto_action=None),
        ),
    )
    standard_policy = EscalationPolicy(
        policy_id="esc-standard-service",
        name="Standard Service Degradation",
        description="Tiered response for warning-level degradation, queue lag, and elevated latencies.",
        tiers=(
            EscalationTier(tier=1, target_channel="slack-alerts-p1", wait_minutes=0, auto_action=None),
            EscalationTier(tier=2, target_channel="pagerduty-service-oncall", wait_minutes=20, auto_action="restart_worker"),
            EscalationTier(tier=3, target_channel="engineering-manager", wait_minutes=60, auto_action=None),
        ),
    )
    budget_policy = EscalationPolicy(
        policy_id="esc-budget-governance",
        name="Budget & FinOps Governance",
        description="Escalation path for cloud resource quota saturation and budget burn rate spikes.",
        tiers=(
            EscalationTier(tier=1, target_channel="slack-finops-alerts", wait_minutes=0, auto_action=None),
            EscalationTier(tier=2, target_channel="finops-lead", wait_minutes=60, auto_action=None),
            EscalationTier(tier=3, target_channel="vp-engineering", wait_minutes=240, auto_action=None),
        ),
    )

    policies = (critical_policy, standard_policy, budget_policy)

    has_database = False

    for s in surfaces:
        slug = _surface_slug_from(s)
        kind = _surface_kind_from(s).lower()

        if kind in ("database", "postgres", "sqlite", "mysql") or "db" in slug:
            has_database = True
            # Database alerts
            rb_db_conn = f"rb-{slug}-conn-pool"
            rules.append(
                AlertRule(
                    rule_id=f"rule-{slug}-conn-pool-exhaustion",
                    surface_slug=slug,
                    metric_name="db_connection_pool_utilization_pct",
                    condition=">=",
                    threshold=85.0,
                    duration_seconds=60,
                    severity="critical",
                    description="Database connection pool utilization has reached or exceeded 85%.",
                    runbook_id=rb_db_conn,
                    tags=("database", "connections", "p0"),
                )
            )
            runbooks.append(
                IncidentRunbook(
                    runbook_id=rb_db_conn,
                    title="Database Connection Pool Exhaustion Mitigation",
                    severity="critical",
                    summary="Diagnose connection leaks, terminate idle transactions, and increase pool capacity.",
                    steps=(
                        RunbookStep(step_id="step-1", order=1, action="inspect_telemetry", target=slug, description="Inspect active connection counts and long-running queries via pg_stat_activity.", is_automated=True, remediation_command="SELECT pid, query, state, age(clock_timestamp(), query_start) FROM pg_stat_activity WHERE state != 'idle' ORDER BY query_start ASC LIMIT 10;"),
                        RunbookStep(step_id="step-2", order=2, action="terminate_idle_transactions", target=slug, description="Terminate transactions idle in transaction over 120 seconds.", is_automated=True, remediation_command="SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND state_change < current_timestamp - INTERVAL '120 seconds';"),
                        RunbookStep(step_id="step-3", order=3, action="notify_stakeholders", target=slug, description="Notify platform engineering lead if connection pool remains saturated.", is_automated=False),
                    ),
                    escalation_policy_id=critical_policy.policy_id,
                    tags=("database", "p0"),
                )
            )

            rb_db_disk = f"rb-{slug}-disk-space"
            rules.append(
                AlertRule(
                    rule_id=f"rule-{slug}-disk-space-critical",
                    surface_slug=slug,
                    metric_name="disk_space_utilization_pct",
                    condition=">=",
                    threshold=85.0,
                    duration_seconds=300,
                    severity="critical",
                    description="Database disk volume capacity is at or above 85% full.",
                    runbook_id=rb_db_disk,
                    tags=("database", "storage", "p1"),
                )
            )
            runbooks.append(
                IncidentRunbook(
                    runbook_id=rb_db_disk,
                    title="Database Storage Expansion & WAL Cleanup",
                    severity="critical",
                    summary="Check table disk footprints, trigger vacuum analyze, and expand disk volume.",
                    steps=(
                        RunbookStep(step_id="step-1", order=1, action="inspect_telemetry", target=slug, description="Identify largest tables and dead tuple accumulation.", is_automated=True, remediation_command="SELECT relname, n_dead_tup, pg_size_pretty(pg_total_relation_size(relid)) FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;"),
                        RunbookStep(step_id="step-2", order=2, action="vacuum_dead_tuples", target=slug, description="Run autovacuum on high-dead-tuple tables.", is_automated=True, remediation_command="VACUUM ANALYZE;"),
                        RunbookStep(step_id="step-3", order=3, action="expand_storage", target=slug, description="Trigger cloud EBS / persistent volume expansion if utilization remains > 85%.", is_automated=False),
                    ),
                    escalation_policy_id=critical_policy.policy_id,
                    tags=("database", "storage"),
                )
            )

        elif kind in ("api", "backend", "fastapi", "go_backend", "service"):
            # API / Backend surface alerts
            rb_api_err = f"rb-{slug}-5xx-errors"
            rules.append(
                AlertRule(
                    rule_id=f"rule-{slug}-http-error-spike",
                    surface_slug=slug,
                    metric_name="http_error_rate_pct",
                    condition=">=",
                    threshold=2.0,
                    duration_seconds=60,
                    severity="critical",
                    description="Backend API 5xx error rate exceeded 2.0% over 60 seconds.",
                    runbook_id=rb_api_err,
                    tags=("api", "http", "5xx", "p0"),
                )
            )
            runbooks.append(
                IncidentRunbook(
                    runbook_id=rb_api_err,
                    title="Backend HTTP 5xx Error Rate Surge Mitigation",
                    severity="critical",
                    summary="Investigate panic stack traces, verify database connectivity, and restart unhealthy pods.",
                    steps=(
                        RunbookStep(step_id="step-1", order=1, action="inspect_telemetry", target=slug, description="Examine recent error traces and exception logs.", is_automated=True, remediation_command=f"omnistackai telemetry query --surface {slug} --level error --tail 50"),
                        RunbookStep(step_id="step-2", order=2, action="verify_upstream_health", target=slug, description="Run health check probes against database and dependent services.", is_automated=True, remediation_command="omnistackai verify-suite --surface database"),
                        RunbookStep(step_id="step-3", order=3, action="restart_service", target=slug, description="Perform rolling restart of unhealthy service replicas.", is_automated=True, remediation_command=f"omnistackai deploy restart --surface {slug}"),
                        RunbookStep(step_id="step-4", order=4, action="notify_stakeholders", target=slug, description="Escalate to on-call backend engineer if errors persist after restart.", is_automated=False),
                    ),
                    escalation_policy_id=critical_policy.policy_id,
                    tags=("api", "p0"),
                )
            )

            rb_api_lat = f"rb-{slug}-p99-latency"
            rules.append(
                AlertRule(
                    rule_id=f"rule-{slug}-p99-latency-spike",
                    surface_slug=slug,
                    metric_name="p99_latency_ms",
                    condition=">=",
                    threshold=800.0,
                    duration_seconds=120,
                    severity="warning",
                    description="API p99 request latency exceeded 800ms for 2 consecutive minutes.",
                    runbook_id=rb_api_lat,
                    tags=("api", "latency", "p1"),
                )
            )
            runbooks.append(
                IncidentRunbook(
                    runbook_id=rb_api_lat,
                    title="API Elevated p99 Response Latency Response",
                    severity="warning",
                    summary="Inspect CPU saturation, scale horizontal replicas, and check database lock wait times.",
                    steps=(
                        RunbookStep(step_id="step-1", order=1, action="inspect_telemetry", target=slug, description="Check slow endpoint breakdown and top CPU-consuming endpoints.", is_automated=True, remediation_command=f"omnistackai telemetry slow-queries --surface {slug}"),
                        RunbookStep(step_id="step-2", order=2, action="scale_replicas", target=slug, description="Scale service replica count up by 2 to alleviate CPU load.", is_automated=True, remediation_command=f"omnistackai capacity scale --surface {slug} --delta +2"),
                        RunbookStep(step_id="step-3", order=3, action="verify_resolution", target=slug, description="Confirm p99 latency returns below 500ms within 5 minutes.", is_automated=False),
                    ),
                    escalation_policy_id=standard_policy.policy_id,
                    tags=("api", "latency"),
                )
            )

            rb_api_cpu = f"rb-{slug}-cpu-saturation"
            rules.append(
                AlertRule(
                    rule_id=f"rule-{slug}-cpu-saturation",
                    surface_slug=slug,
                    metric_name="cpu_utilization_pct",
                    condition=">=",
                    threshold=85.0,
                    duration_seconds=180,
                    severity="warning",
                    description="Backend service CPU utilization exceeded 85% for 3 minutes.",
                    runbook_id=rb_api_cpu,
                    tags=("api", "cpu", "capacity"),
                )
            )
            runbooks.append(
                IncidentRunbook(
                    runbook_id=rb_api_cpu,
                    title="High CPU Saturation Remediation",
                    severity="warning",
                    summary="Trigger horizontal auto-scaling and profile hot execution paths.",
                    steps=(
                        RunbookStep(step_id="step-1", order=1, action="scale_replicas", target=slug, description="Trigger auto-scaler to add capacity.", is_automated=True, remediation_command=f"omnistackai capacity scale --surface {slug} --replicas +1"),
                        RunbookStep(step_id="step-2", order=2, action="inspect_telemetry", target=slug, description="Capture CPU profile flamegraph snapshot.", is_automated=False),
                    ),
                    escalation_policy_id=standard_policy.policy_id,
                    tags=("api", "cpu"),
                )
            )

        elif kind in ("worker", "queue_worker", "consumer"):
            # Worker / Consumer surface alerts
            rb_worker_lag = f"rb-{slug}-queue-lag"
            rules.append(
                AlertRule(
                    rule_id=f"rule-{slug}-queue-lag-spike",
                    surface_slug=slug,
                    metric_name="queue_lag_seconds",
                    condition=">=",
                    threshold=300.0,
                    duration_seconds=180,
                    severity="critical",
                    description="Worker message processing backlog exceeded 300 seconds.",
                    runbook_id=rb_worker_lag,
                    tags=("worker", "queue", "lag", "p0"),
                )
            )
            runbooks.append(
                IncidentRunbook(
                    runbook_id=rb_worker_lag,
                    title="Worker Task Queue Backlog Mitigation",
                    severity="critical",
                    summary="Scale out worker pool instances and drain dead letter queues.",
                    steps=(
                        RunbookStep(step_id="step-1", order=1, action="scale_replicas", target=slug, description="Double worker concurrency to drain backlog rapidly.", is_automated=True, remediation_command=f"omnistackai capacity scale --surface {slug} --replicas 4"),
                        RunbookStep(step_id="step-2", order=2, action="inspect_telemetry", target=slug, description="Check for poison pill messages causing worker loop panics.", is_automated=True, remediation_command=f"omnistackai telemetry errors --surface {slug}"),
                        RunbookStep(step_id="step-3", order=3, action="notify_stakeholders", target=slug, description="Notify backend on-call if queue lag does not decrease within 10 minutes.", is_automated=False),
                    ),
                    escalation_policy_id=critical_policy.policy_id,
                    tags=("worker", "p0"),
                )
            )

        else:
            # Customer Web / Admin Web / Frontend surfaces
            rb_web_err = f"rb-{slug}-http-error"
            rules.append(
                AlertRule(
                    rule_id=f"rule-{slug}-http-error-rate",
                    surface_slug=slug,
                    metric_name="http_error_rate_pct",
                    condition=">=",
                    threshold=5.0,
                    duration_seconds=120,
                    severity="warning",
                    description="Frontend edge delivery 4xx/5xx error rate exceeded 5.0%.",
                    runbook_id=rb_web_err,
                    tags=("web", "edge", "errors", "p1"),
                )
            )
            runbooks.append(
                IncidentRunbook(
                    runbook_id=rb_web_err,
                    title="Frontend Edge Delivery Error Rate Surge",
                    severity="warning",
                    summary="Verify CDN origin status, Next.js hydration health, and API gateway connectivity.",
                    steps=(
                        RunbookStep(step_id="step-1", order=1, action="inspect_telemetry", target=slug, description="Inspect client-side error telemetry and status code breakdown.", is_automated=True, remediation_command=f"omnistackai telemetry query --surface {slug} --metric status_codes"),
                        RunbookStep(step_id="step-2", order=2, action="verify_upstream_health", target=slug, description="Verify backend API gateway and auth endpoint liveness.", is_automated=True, remediation_command="omnistackai verify-suite --surface api"),
                        RunbookStep(step_id="step-3", order=3, action="restart_service", target=slug, description="Flush edge CDN cache and restart web frontend containers.", is_automated=True, remediation_command=f"omnistackai deploy purge-cache --surface {slug}"),
                    ),
                    escalation_policy_id=standard_policy.policy_id,
                    tags=("web", "p1"),
                )
            )

            rb_web_lcp = f"rb-{slug}-lcp-degradation"
            rules.append(
                AlertRule(
                    rule_id=f"rule-{slug}-lcp-degradation",
                    surface_slug=slug,
                    metric_name="p99_latency_ms",
                    condition=">=",
                    threshold=2500.0,
                    duration_seconds=300,
                    severity="info",
                    description="Frontend page delivery p99 response time exceeded 2500ms.",
                    runbook_id=rb_web_lcp,
                    tags=("web", "performance", "lcp"),
                )
            )
            runbooks.append(
                IncidentRunbook(
                    runbook_id=rb_web_lcp,
                    title="Frontend Response & Core Web Vitals LCP Degradation",
                    severity="info",
                    summary="Check asset bundle sizes, static cache hit rates, and SSR render times.",
                    steps=(
                        RunbookStep(step_id="step-1", order=1, action="inspect_telemetry", target=slug, description="Analyze Web Vitals distribution and static asset download latency.", is_automated=True, remediation_command=f"omnistackai telemetry vitals --surface {slug}"),
                        RunbookStep(step_id="step-2", order=2, action="verify_resolution", target=slug, description="Review bundle analysis and image optimization caches.", is_automated=False),
                    ),
                    escalation_policy_id=standard_policy.policy_id,
                    tags=("web", "lcp"),
                )
            )

    # If no database surface was explicitly found, add a canonical database alert rule
    if not has_database:
        rb_db_conn = "rb-db-conn-pool"
        rules.append(
            AlertRule(
                rule_id="rule-db-conn-pool-exhaustion",
                surface_slug="database",
                metric_name="db_connection_pool_utilization_pct",
                condition=">=",
                threshold=85.0,
                duration_seconds=60,
                severity="critical",
                description="Ecosystem PostgreSQL connection pool reached or exceeded 85% saturation.",
                runbook_id=rb_db_conn,
                tags=("database", "connections", "p0"),
            )
        )
        runbooks.append(
            IncidentRunbook(
                runbook_id=rb_db_conn,
                title="Ecosystem Database Connection Saturation Mitigation",
                severity="critical",
                summary="Inspect pool utilization, terminate stalled client connections, and restart connection pooler.",
                steps=(
                    RunbookStep(step_id="step-1", order=1, action="inspect_telemetry", target="database", description="Check active query connections.", is_automated=True, remediation_command="SELECT count(*), state FROM pg_stat_activity GROUP BY state;"),
                    RunbookStep(step_id="step-2", order=2, action="terminate_idle_transactions", target="database", description="Terminate idle in transaction sessions older than 60s.", is_automated=True, remediation_command="SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND state_change < now() - interval '60 seconds';"),
                ),
                escalation_policy_id=critical_policy.policy_id,
                tags=("database", "p0"),
            )
        )

    # Cross-surface FinOps budget overrun alert
    rb_budget = "rb-budget-burn-rate"
    rules.append(
        AlertRule(
            rule_id="rule-budget-burn-rate-spike",
            surface_slug="ecosystem",
            metric_name="budget_burn_rate_pct",
            condition=">=",
            threshold=120.0,
            duration_seconds=3600,
            severity="critical",
            description="Projected monthly cloud spend exceeds 120% of designated monthly budget limit.",
            runbook_id=rb_budget,
            tags=("finops", "budget", "billing", "p1"),
        )
    )
    runbooks.append(
        IncidentRunbook(
            runbook_id=rb_budget,
            title="Cloud Spend & Unit Economics Budget Overrun Response",
            severity="critical",
            summary="Review surface capacity consumption, identify rogue cloud resource allocations, and adjust autoscaling ceilings.",
            steps=(
                RunbookStep(step_id="step-1", order=1, action="inspect_telemetry", target="ecosystem", description="Query unit economics cost model breakdown per surface.", is_automated=True, remediation_command="omnistackai capacity --json"),
                RunbookStep(step_id="step-2", order=2, action="scale_down_nonessential", target="ecosystem", description="Scale down staging/preview replicas and pause idle batch tasks.", is_automated=True, remediation_command="omnistackai capacity scale-down-idle"),
                RunbookStep(step_id="step-3", order=3, action="notify_stakeholders", target="ecosystem", description="Report cost projection to FinOps lead and Engineering VP.", is_automated=False),
            ),
            escalation_policy_id=budget_policy.policy_id,
            tags=("finops", "budget"),
        )
    )

    return EcosystemAlertingContract(
        ecosystem_id=ecosystem_id,
        version=version,
        alert_rules=tuple(rules),
        runbooks=tuple(runbooks),
        escalation_policies=policies,
    )


# ---------------------------------------------------------------------------
# Simulation Engine & Reports
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AlertTriggerResult:
    """Evaluation result for a metric value against an alert rule."""

    rule_id: str
    surface_slug: str
    metric_name: str
    metric_value: float
    threshold: float
    condition: str
    is_firing: bool
    severity: str
    runbook_id: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "surface_slug": self.surface_slug,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "condition": self.condition,
            "is_firing": self.is_firing,
            "severity": self.severity,
            "runbook_id": self.runbook_id,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class RunbookStepExecution:
    """Result of evaluating a single runbook step in dry-run mode."""

    step_id: str
    order: int
    action: str
    target: str
    is_automated: bool
    remediation_command: str | None
    status: str  # "passed" | "manual_required"
    output: str

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "step_id": self.step_id,
            "order": self.order,
            "action": self.action,
            "target": self.target,
            "is_automated": self.is_automated,
            "status": self.status,
            "output": self.output,
        }
        if self.remediation_command is not None:
            result["remediation_command"] = self.remediation_command
        return result


@dataclass(frozen=True, slots=True)
class RunbookExecutionReport:
    """Complete report from dry-run execution of an incident runbook."""

    runbook_id: str
    title: str
    severity: str
    total_steps: int
    automated_steps: int
    manual_steps: int
    status: str  # "auto_mitigated" | "pending_manual_action"
    step_executions: tuple[RunbookStepExecution, ...]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "runbook_id": self.runbook_id,
            "title": self.title,
            "severity": self.severity,
            "total_steps": self.total_steps,
            "automated_steps": self.automated_steps,
            "manual_steps": self.manual_steps,
            "status": self.status,
            "step_executions": [s.to_dict() for s in self.step_executions],
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class IncidentSimulationReport:
    """Full incident simulation report covering trigger, runbook, and escalation."""

    scenario: str
    alert_trigger: AlertTriggerResult
    runbook_report: RunbookExecutionReport | None
    escalation_policy_id: str | None
    escalation_tier_reached: int
    active_responder_channels: tuple[str, ...]
    status: str  # "auto_mitigated" | "escalated" | "manual_intervention_required"
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "alert_trigger": self.alert_trigger.to_dict(),
            "runbook_report": self.runbook_report.to_dict() if self.runbook_report is not None else None,
            "escalation_policy_id": self.escalation_policy_id,
            "escalation_tier_reached": self.escalation_tier_reached,
            "active_responder_channels": list(self.active_responder_channels),
            "status": self.status,
            "summary": self.summary,
        }


class EcosystemAlertingEngine:
    """Thread-safe, in-process, fully deterministic incident alerting and runbook engine.

    Evaluates metric thresholds against alert rules, dry-runs incident runbook steps,
    and simulates multi-tier escalation policies completely offline with 0 external calls.
    """

    def __init__(self, contract: EcosystemAlertingContract) -> None:
        self._contract = contract
        self._lock = threading.Lock()
        self._rules_by_id = {r.rule_id: r for r in contract.alert_rules}
        self._runbooks_by_id = {rb.runbook_id: rb for rb in contract.runbooks}
        self._policies_by_id = {ep.policy_id: ep for ep in contract.escalation_policies}

    @property
    def contract(self) -> EcosystemAlertingContract:
        return self._contract

    def evaluate_metric(self, rule_id: str, metric_value: float) -> AlertTriggerResult:
        """Evaluate a numeric metric against a specific alert rule."""
        with self._lock:
            rule = self._rules_by_id.get(rule_id)
            if rule is None:
                return AlertTriggerResult(
                    rule_id=rule_id,
                    surface_slug="unknown",
                    metric_name="unknown",
                    metric_value=metric_value,
                    threshold=0.0,
                    condition="==",
                    is_firing=False,
                    severity="info",
                    runbook_id="",
                    message=f"Rule '{rule_id}' not found in contract",
                )

            # Evaluate condition
            op = rule.condition
            thresh = rule.threshold
            is_firing = False
            if op == ">":
                is_firing = metric_value > thresh
            elif op == ">=":
                is_firing = metric_value >= thresh
            elif op == "<":
                is_firing = metric_value < thresh
            elif op == "<=":
                is_firing = metric_value <= thresh
            elif op == "==":
                is_firing = abs(metric_value - thresh) < 1e-6

            status_str = "FIRING" if is_firing else "RESOLVED"
            msg = (
                f"Alert [{rule.severity.upper()}] {rule.rule_id} is {status_str}: "
                f"{rule.metric_name} ({metric_value}) {rule.condition} threshold ({thresh})"
            )

            return AlertTriggerResult(
                rule_id=rule.rule_id,
                surface_slug=rule.surface_slug,
                metric_name=rule.metric_name,
                metric_value=metric_value,
                threshold=rule.threshold,
                condition=rule.condition,
                is_firing=is_firing,
                severity=rule.severity,
                runbook_id=rule.runbook_id,
                message=msg,
            )

    def dry_run_runbook(self, runbook_id: str) -> RunbookExecutionReport:
        """Dry-run execute all steps of an incident runbook."""
        with self._lock:
            rb = self._runbooks_by_id.get(runbook_id)
            if rb is None:
                return RunbookExecutionReport(
                    runbook_id=runbook_id,
                    title="Unknown Runbook",
                    severity="info",
                    total_steps=0,
                    automated_steps=0,
                    manual_steps=0,
                    status="pending_manual_action",
                    step_executions=(),
                    summary=f"Runbook '{runbook_id}' not found in contract",
                )

            step_execs: list[RunbookStepExecution] = []
            auto_count = 0
            manual_count = 0

            # Sort steps by order
            sorted_steps = sorted(rb.steps, key=lambda s: s.order)
            for step in sorted_steps:
                if step.is_automated:
                    auto_count += 1
                    status = "passed"
                    cmd_info = f" [cmd: '{step.remediation_command}']" if step.remediation_command else ""
                    out = f"Simulated automated execution of '{step.action}' against target '{step.target}'{cmd_info}: OK"
                else:
                    manual_count += 1
                    status = "manual_required"
                    out = f"Manual intervention required: {step.description}"

                step_execs.append(
                    RunbookStepExecution(
                        step_id=step.step_id,
                        order=step.order,
                        action=step.action,
                        target=step.target,
                        is_automated=step.is_automated,
                        remediation_command=step.remediation_command,
                        status=status,
                        output=out,
                    )
                )

            # If all steps are automated, status is auto_mitigated; otherwise pending_manual_action
            overall_status = "auto_mitigated" if manual_count == 0 else "pending_manual_action"
            summary = (
                f"Runbook '{rb.title}' evaluated {len(step_execs)} steps "
                f"({auto_count} automated, {manual_count} manual) -> {overall_status}"
            )

            return RunbookExecutionReport(
                runbook_id=rb.runbook_id,
                title=rb.title,
                severity=rb.severity,
                total_steps=len(step_execs),
                automated_steps=auto_count,
                manual_steps=manual_count,
                status=overall_status,
                step_executions=tuple(step_execs),
                summary=summary,
            )

    def simulate_incident(
        self,
        scenario: str = "api_error_spike",
        metric_value: float | None = None,
    ) -> IncidentSimulationReport:
        """Simulate an end-to-end incident scenario:
        1. Select appropriate alert rule and evaluate metric.
        2. Dry-run the associated runbook.
        3. Resolve the escalation policy and responders.
        """
        with self._lock:
            # Find matching rule based on scenario
            target_rule: AlertRule | None = None
            default_val = 5.0

            scenario_norm = scenario.lower().replace("-", "_")
            if "healthy" in scenario_norm or "normal" in scenario_norm or "baseline" in scenario_norm:
                target_rule = next((r for r in self._contract.alert_rules if "error" in r.metric_name), None)
                default_val = 0.5
            elif "latency" in scenario_norm:
                target_rule = next((r for r in self._contract.alert_rules if "latency" in r.metric_name), None)
                default_val = 3200.0
            elif "conn" in scenario_norm or "db" in scenario_norm or "database" in scenario_norm:
                target_rule = next((r for r in self._contract.alert_rules if "conn" in r.metric_name or "db" in r.surface_slug), None)
                default_val = 92.0
            elif "budget" in scenario_norm or "finops" in scenario_norm or "cost" in scenario_norm:
                target_rule = next((r for r in self._contract.alert_rules if "budget" in r.metric_name), None)
                default_val = 145.0
            elif "queue" in scenario_norm or "worker" in scenario_norm:
                target_rule = next((r for r in self._contract.alert_rules if "queue" in r.metric_name or "worker" in r.surface_slug), None)
                default_val = 450.0
            else:
                # Default: 5xx / http error rate spike
                target_rule = next((r for r in self._contract.alert_rules if "error" in r.metric_name), None)
                default_val = 8.5

            if target_rule is None and self._contract.alert_rules:
                target_rule = self._contract.alert_rules[0]

            if target_rule is None:
                # Empty contract fallback
                return IncidentSimulationReport(
                    scenario=scenario,
                    alert_trigger=AlertTriggerResult(
                        rule_id="none",
                        surface_slug="none",
                        metric_name="none",
                        metric_value=0.0,
                        threshold=0.0,
                        condition="==",
                        is_firing=False,
                        severity="info",
                        runbook_id="",
                        message="No alert rules found in contract",
                    ),
                    runbook_report=None,
                    escalation_policy_id=None,
                    escalation_tier_reached=0,
                    active_responder_channels=(),
                    status="resolved",
                    summary="No incident simulated (contract has zero alert rules)",
                )

            val = metric_value if metric_value is not None else default_val

        # Step 1: Trigger evaluation
        trigger = self.evaluate_metric(target_rule.rule_id, val)

        # Step 2: Runbook evaluation
        runbook_report: RunbookExecutionReport | None = None
        if trigger.is_firing and trigger.runbook_id:
            runbook_report = self.dry_run_runbook(trigger.runbook_id)

        # Step 3: Escalation resolution
        policy_id: str | None = None
        tier_reached = 1
        channels: list[str] = []

        if trigger.is_firing and trigger.runbook_id:
            rb = self._runbooks_by_id.get(trigger.runbook_id)
            if rb and rb.escalation_policy_id:
                policy_id = rb.escalation_policy_id
                policy = self._policies_by_id.get(policy_id)
                if policy:
                    # If runbook has manual steps or severity is fatal/critical, escalate further
                    if trigger.severity in ("critical", "fatal") or (runbook_report and runbook_report.manual_steps > 0):
                        tier_reached = min(len(policy.tiers), 2)
                    for t in policy.tiers[:tier_reached]:
                        channels.append(t.target_channel)

        if not trigger.is_firing:
            status = "resolved"
            summary = f"Incident scenario '{scenario}' resolved: metric {val} within normal limits"
        elif runbook_report and runbook_report.manual_steps == 0:
            status = "auto_mitigated"
            summary = (
                f"Incident scenario '{scenario}' triggered {trigger.rule_id} ({trigger.severity}) "
                f"and was AUTO-MITIGATED via {trigger.runbook_id}"
            )
        else:
            status = "manual_intervention_required"
            summary = (
                f"Incident scenario '{scenario}' triggered {trigger.rule_id} ({trigger.severity}). "
                f"Escalated to tier {tier_reached} ({', '.join(channels)}) requiring manual action."
            )

        return IncidentSimulationReport(
            scenario=scenario,
            alert_trigger=trigger,
            runbook_report=runbook_report,
            escalation_policy_id=policy_id,
            escalation_tier_reached=tier_reached,
            active_responder_channels=tuple(channels),
            status=status,
            summary=summary,
        )

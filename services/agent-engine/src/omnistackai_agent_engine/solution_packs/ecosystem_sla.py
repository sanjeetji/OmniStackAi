"""Ecosystem Multi-Surface SLA, SLO, and Error Budget Contracts (R-457).

Defines canonical contracts, indicators, objectives, error budgets, and customer-tier
agreements for an entire multi-surface business ecosystem:
- ServiceLevelIndicator (SLI): surface-scoped metrics measuring availability and latency.
- ServiceLevelObjective (SLO): formal target percentages with rolling time windows.
- ErrorBudget: allocated unreliability budgets with multi-window burn rate tracking.
- ServiceLevelAgreement (SLA): customer-facing contractual tier commitments and penalties.
- EcosystemSLAContract: immutable multi-surface contract with deterministic SHA-256 digest.
- EcosystemSLAEngine: thread-safe in-process evaluation, burn rate, and compliance simulator.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Literal

SLIKind = Literal["availability", "latency", "error_rate", "throughput", "saturation"]
SLOTier = Literal["critical", "high", "medium", "low"]
BudgetingMethod = Literal["timeslice", "occurrences"]
BudgetStatus = Literal["healthy", "warning", "exhausted"]
CustomerTier = Literal["enterprise", "business", "developer", "free"]
SLAStatus = Literal["compliant", "at_risk", "breached"]


@dataclass(frozen=True, slots=True)
class ServiceLevelIndicator:
    """A measurable service level indicator (SLI) on an ecosystem surface."""

    sli_id: str
    surface_slug: str
    metric_name: str
    kind: SLIKind = "availability"
    threshold: float = 0.0
    unit: str = "%"
    good_events_query: str = ""
    total_events_query: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "sli_id": self.sli_id,
            "surface_slug": self.surface_slug,
            "metric_name": self.metric_name,
            "kind": self.kind,
            "threshold": self.threshold,
            "unit": self.unit,
            "good_events_query": self.good_events_query,
            "total_events_query": self.total_events_query,
            "description": self.description,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ServiceLevelIndicator:
        raw_kind = str(data.get("kind", "availability")).lower()
        kind: SLIKind = (
            raw_kind
            if raw_kind in ("availability", "latency", "error_rate", "throughput", "saturation")
            else "availability"
        )
        return cls(
            sli_id=str(data.get("sli_id", "")),
            surface_slug=str(data.get("surface_slug", "")),
            metric_name=str(data.get("metric_name", "")),
            kind=kind,
            threshold=float(data.get("threshold", 0.0)),
            unit=str(data.get("unit", "%")),
            good_events_query=str(data.get("good_events_query", "")),
            total_events_query=str(data.get("total_events_query", "")),
            description=str(data.get("description", "")),
            tags=tuple(str(t) for t in data.get("tags", ())),
        )


@dataclass(frozen=True, slots=True)
class ServiceLevelObjective:
    """A target service level objective (SLO) bound to an SLI."""

    slo_id: str
    name: str
    surface_slug: str
    sli_id: str
    target_percentage: float  # e.g. 99.9
    rolling_window_days: int = 30
    budgeting_method: BudgetingMethod = "timeslice"
    warning_threshold_pct: float = 99.95
    tier: SLOTier = "high"
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "slo_id": self.slo_id,
            "name": self.name,
            "surface_slug": self.surface_slug,
            "sli_id": self.sli_id,
            "target_percentage": self.target_percentage,
            "rolling_window_days": self.rolling_window_days,
            "budgeting_method": self.budgeting_method,
            "warning_threshold_pct": self.warning_threshold_pct,
            "tier": self.tier,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ServiceLevelObjective:
        raw_method = str(data.get("budgeting_method", "timeslice")).lower()
        method: BudgetingMethod = "occurrences" if raw_method == "occurrences" else "timeslice"
        raw_tier = str(data.get("tier", "high")).lower()
        tier: SLOTier = raw_tier if raw_tier in ("critical", "high", "medium", "low") else "high"
        return cls(
            slo_id=str(data.get("slo_id", "")),
            name=str(data.get("name", "")),
            surface_slug=str(data.get("surface_slug", "")),
            sli_id=str(data.get("sli_id", "")),
            target_percentage=float(data.get("target_percentage", 99.9)),
            rolling_window_days=int(data.get("rolling_window_days", 30)),
            budgeting_method=method,
            warning_threshold_pct=float(data.get("warning_threshold_pct", 99.95)),
            tier=tier,
            tags=tuple(str(t) for t in data.get("tags", ())),
        )


@dataclass(frozen=True, slots=True)
class ErrorBudget:
    """An error budget allocated to an SLO with burn rates and status."""

    slo_id: str
    total_budget_percentage: float  # 100.0 - target_percentage
    remaining_budget_percentage: float
    burn_rate_1h: float = 0.0
    burn_rate_6h: float = 0.0
    burn_rate_24h: float = 0.0
    budget_status: BudgetStatus = "healthy"
    consumed_budget_percentage: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "slo_id": self.slo_id,
            "total_budget_percentage": self.total_budget_percentage,
            "remaining_budget_percentage": self.remaining_budget_percentage,
            "burn_rate_1h": self.burn_rate_1h,
            "burn_rate_6h": self.burn_rate_6h,
            "burn_rate_24h": self.burn_rate_24h,
            "budget_status": self.budget_status,
            "consumed_budget_percentage": self.consumed_budget_percentage,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ErrorBudget:
        raw_status = str(data.get("budget_status", "healthy")).lower()
        status: BudgetStatus = (
            raw_status if raw_status in ("healthy", "warning", "exhausted") else "healthy"
        )
        return cls(
            slo_id=str(data.get("slo_id", "")),
            total_budget_percentage=float(data.get("total_budget_percentage", 0.1)),
            remaining_budget_percentage=float(data.get("remaining_budget_percentage", 0.1)),
            burn_rate_1h=float(data.get("burn_rate_1h", 0.0)),
            burn_rate_6h=float(data.get("burn_rate_6h", 0.0)),
            burn_rate_24h=float(data.get("burn_rate_24h", 0.0)),
            budget_status=status,
            consumed_budget_percentage=float(data.get("consumed_budget_percentage", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class ServiceLevelAgreement:
    """A contractual customer-facing agreement committing to availability and latency."""

    sla_id: str
    customer_tier: CustomerTier
    surface_slug: str
    availability_target_pct: float
    p95_latency_ms_target: float
    financial_credit_pct: float
    penalty_threshold_pct: float
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "sla_id": self.sla_id,
            "customer_tier": self.customer_tier,
            "surface_slug": self.surface_slug,
            "availability_target_pct": self.availability_target_pct,
            "p95_latency_ms_target": self.p95_latency_ms_target,
            "financial_credit_pct": self.financial_credit_pct,
            "penalty_threshold_pct": self.penalty_threshold_pct,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ServiceLevelAgreement:
        raw_tier = str(data.get("customer_tier", "business")).lower()
        tier: CustomerTier = (
            raw_tier
            if raw_tier in ("enterprise", "business", "developer", "free")
            else "business"
        )
        return cls(
            sla_id=str(data.get("sla_id", "")),
            customer_tier=tier,
            surface_slug=str(data.get("surface_slug", "")),
            availability_target_pct=float(data.get("availability_target_pct", 99.9)),
            p95_latency_ms_target=float(data.get("p95_latency_ms_target", 500.0)),
            financial_credit_pct=float(data.get("financial_credit_pct", 10.0)),
            penalty_threshold_pct=float(data.get("penalty_threshold_pct", 99.0)),
            description=str(data.get("description", "")),
        )


@dataclass(frozen=True, slots=True)
class EcosystemSLAContract:
    """Canonical multi-surface contract defining SLIs, SLOs, Error Budgets, and SLAs."""

    ecosystem_id: str
    version: str
    slis: tuple[ServiceLevelIndicator, ...]
    slos: tuple[ServiceLevelObjective, ...]
    error_budgets: tuple[ErrorBudget, ...]
    slas: tuple[ServiceLevelAgreement, ...]

    def digest(self) -> str:
        """Compute a deterministic SHA-256 digest of the SLA contract."""
        raw = self.to_json()
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "slis": [s.to_dict() for s in self.slis],
            "slos": [o.to_dict() for o in self.slos],
            "error_budgets": [b.to_dict() for b in self.error_budgets],
            "slas": [a.to_dict() for a in self.slas],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemSLAContract:
        raw_slis = data.get("slis", ())
        slis = tuple(ServiceLevelIndicator.from_dict(s) for s in raw_slis) if isinstance(raw_slis, Sequence) else ()
        raw_slos = data.get("slos", ())
        slos = tuple(ServiceLevelObjective.from_dict(o) for o in raw_slos) if isinstance(raw_slos, Sequence) else ()
        raw_budgets = data.get("error_budgets", ())
        budgets = tuple(ErrorBudget.from_dict(b) for b in raw_budgets) if isinstance(raw_budgets, Sequence) else ()
        raw_slas = data.get("slas", ())
        slas = tuple(ServiceLevelAgreement.from_dict(a) for a in raw_slas) if isinstance(raw_slas, Sequence) else ()
        return cls(
            ecosystem_id=str(data.get("ecosystem_id", "")),
            version=str(data.get("version", "1.0.0")),
            slis=slis,
            slos=slos,
            error_budgets=budgets,
            slas=slas,
        )

    @classmethod
    def from_json(cls, raw: str) -> EcosystemSLAContract:
        return cls.from_dict(json.loads(raw))


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


def synthesize_ecosystem_sla(
    ecosystem_id: str,
    surfaces: Sequence[Any],
    version: str = "1.0.0",
) -> EcosystemSLAContract:
    """Synthesize canonical SLIs, SLOs, Error Budgets, and SLAs for all surfaces in an ecosystem."""
    slis: list[ServiceLevelIndicator] = []
    slos: list[ServiceLevelObjective] = []
    budgets: list[ErrorBudget] = []
    slas: list[ServiceLevelAgreement] = []

    for s in surfaces:
        slug = _surface_slug_from(s)
        kind = _surface_kind_from(s)

        if not slug:
            continue

        if "api" in kind or "backend" in kind or "service" in kind:
            # Backend API SLIs & SLOs
            sli_avail = f"sli-{slug}-availability"
            slis.append(
                ServiceLevelIndicator(
                    sli_id=sli_avail,
                    surface_slug=slug,
                    metric_name="http_success_rate_pct",
                    kind="availability",
                    threshold=99.9,
                    unit="%",
                    good_events_query=f"sum(rate(http_requests_total{{surface='{slug}', status!~'5..'}}[5m]))",
                    total_events_query=f"sum(rate(http_requests_total{{surface='{slug}'}}[5m]))",
                    description=f"{slug} HTTP successful response rate (non-5xx)",
                    tags=("api", "availability", "p0"),
                )
            )
            slo_avail = f"slo-{slug}-availability"
            slos.append(
                ServiceLevelObjective(
                    slo_id=slo_avail,
                    name=f"{slug.title()} API 99.9% High Availability",
                    surface_slug=slug,
                    sli_id=sli_avail,
                    target_percentage=99.9,
                    rolling_window_days=30,
                    budgeting_method="timeslice",
                    warning_threshold_pct=99.95,
                    tier="critical",
                    tags=("api", "production"),
                )
            )
            budgets.append(
                ErrorBudget(
                    slo_id=slo_avail,
                    total_budget_percentage=0.1,
                    remaining_budget_percentage=0.1,
                    budget_status="healthy",
                )
            )

            # API Latency SLI & SLO
            sli_lat = f"sli-{slug}-p95-latency"
            slis.append(
                ServiceLevelIndicator(
                    sli_id=sli_lat,
                    surface_slug=slug,
                    metric_name="p95_latency_ms",
                    kind="latency",
                    threshold=350.0,
                    unit="ms",
                    good_events_query=f"histogram_quantile(0.95, sum(rate(http_request_duration_ms_bucket{{surface='{slug}'}}[5m])) by (le)) <= 350",
                    total_events_query=f"sum(rate(http_request_duration_ms_count{{surface='{slug}'}}[5m]))",
                    description=f"{slug} API p95 response latency under 350ms",
                    tags=("api", "latency", "p1"),
                )
            )
            slo_lat = f"slo-{slug}-p95-latency"
            slos.append(
                ServiceLevelObjective(
                    slo_id=slo_lat,
                    name=f"{slug.title()} API Latency Target (p95 < 350ms)",
                    surface_slug=slug,
                    sli_id=sli_lat,
                    target_percentage=99.0,
                    rolling_window_days=30,
                    budgeting_method="occurrences",
                    warning_threshold_pct=99.5,
                    tier="high",
                    tags=("api", "latency"),
                )
            )
            budgets.append(
                ErrorBudget(
                    slo_id=slo_lat,
                    total_budget_percentage=1.0,
                    remaining_budget_percentage=1.0,
                    budget_status="healthy",
                )
            )

            # Customer SLAs for API
            slas.append(
                ServiceLevelAgreement(
                    sla_id=f"sla-{slug}-enterprise",
                    customer_tier="enterprise",
                    surface_slug=slug,
                    availability_target_pct=99.95,
                    p95_latency_ms_target=250.0,
                    financial_credit_pct=25.0,
                    penalty_threshold_pct=99.0,
                    description=f"Enterprise Tier 99.95% availability SLA for {slug}",
                )
            )
            slas.append(
                ServiceLevelAgreement(
                    sla_id=f"sla-{slug}-business",
                    customer_tier="business",
                    surface_slug=slug,
                    availability_target_pct=99.9,
                    p95_latency_ms_target=400.0,
                    financial_credit_pct=15.0,
                    penalty_threshold_pct=98.5,
                    description=f"Business Tier 99.9% availability SLA for {slug}",
                )
            )

        elif "web" in kind or "portal" in kind or "admin" in kind:
            # Web Surface SLIs & SLOs
            sli_uptime = f"sli-{slug}-uptime"
            slis.append(
                ServiceLevelIndicator(
                    sli_id=sli_uptime,
                    surface_slug=slug,
                    metric_name="edge_uptime_pct",
                    kind="availability",
                    threshold=99.5,
                    unit="%",
                    good_events_query=f"sum(rate(edge_requests_success_total{{surface='{slug}'}}[5m]))",
                    total_events_query=f"sum(rate(edge_requests_total{{surface='{slug}'}}[5m]))",
                    description=f"{slug} frontend edge CDN availability",
                    tags=("web", "uptime"),
                )
            )
            slo_uptime = f"slo-{slug}-uptime"
            slos.append(
                ServiceLevelObjective(
                    slo_id=slo_uptime,
                    name=f"{slug.title()} Frontend 99.5% Uptime",
                    surface_slug=slug,
                    sli_id=sli_uptime,
                    target_percentage=99.5,
                    rolling_window_days=30,
                    budgeting_method="timeslice",
                    warning_threshold_pct=99.7,
                    tier="high",
                    tags=("web", "uptime"),
                )
            )
            budgets.append(
                ErrorBudget(
                    slo_id=slo_uptime,
                    total_budget_percentage=0.5,
                    remaining_budget_percentage=0.5,
                    budget_status="healthy",
                )
            )

            # Web Vitals LCP SLI & SLO
            sli_lcp = f"sli-{slug}-lcp"
            slis.append(
                ServiceLevelIndicator(
                    sli_id=sli_lcp,
                    surface_slug=slug,
                    metric_name="lcp_duration_ms",
                    kind="latency",
                    threshold=2500.0,
                    unit="ms",
                    good_events_query=f"sum(rate(web_vitals_lcp_good_total{{surface='{slug}'}}[5m]))",
                    total_events_query=f"sum(rate(web_vitals_lcp_total{{surface='{slug}'}}[5m]))",
                    description=f"{slug} Core Web Vitals Largest Contentful Paint under 2.5s",
                    tags=("web", "cwv", "lcp"),
                )
            )
            slo_lcp = f"slo-{slug}-lcp"
            slos.append(
                ServiceLevelObjective(
                    slo_id=slo_lcp,
                    name=f"{slug.title()} Web Vitals LCP Compliance (>90% good)",
                    surface_slug=slug,
                    sli_id=sli_lcp,
                    target_percentage=90.0,
                    rolling_window_days=30,
                    budgeting_method="occurrences",
                    warning_threshold_pct=92.0,
                    tier="medium",
                    tags=("web", "cwv"),
                )
            )
            budgets.append(
                ErrorBudget(
                    slo_id=slo_lcp,
                    total_budget_percentage=10.0,
                    remaining_budget_percentage=10.0,
                    budget_status="healthy",
                )
            )

            # Customer SLA for Web
            slas.append(
                ServiceLevelAgreement(
                    sla_id=f"sla-{slug}-developer",
                    customer_tier="developer",
                    surface_slug=slug,
                    availability_target_pct=99.0,
                    p95_latency_ms_target=800.0,
                    financial_credit_pct=5.0,
                    penalty_threshold_pct=97.0,
                    description=f"Developer Tier 99.0% availability SLA for {slug}",
                )
            )

        elif "mobile" in kind or "app" in kind:
            # Mobile crash-free sessions SLI & SLO
            sli_crash = f"sli-{slug}-crash-free"
            slis.append(
                ServiceLevelIndicator(
                    sli_id=sli_crash,
                    surface_slug=slug,
                    metric_name="crash_free_sessions_pct",
                    kind="availability",
                    threshold=99.5,
                    unit="%",
                    good_events_query=f"sum(mobile_sessions_successful{{surface='{slug}'}})",
                    total_events_query=f"sum(mobile_sessions_total{{surface='{slug}'}})",
                    description=f"{slug} 99.5% crash-free mobile sessions",
                    tags=("mobile", "stability"),
                )
            )
            slo_crash = f"slo-{slug}-crash-free"
            slos.append(
                ServiceLevelObjective(
                    slo_id=slo_crash,
                    name=f"{slug.title()} Mobile 99.5% Crash-Free Sessions",
                    surface_slug=slug,
                    sli_id=sli_crash,
                    target_percentage=99.5,
                    rolling_window_days=30,
                    budgeting_method="occurrences",
                    warning_threshold_pct=99.7,
                    tier="high",
                    tags=("mobile", "reliability"),
                )
            )
            budgets.append(
                ErrorBudget(
                    slo_id=slo_crash,
                    total_budget_percentage=0.5,
                    remaining_budget_percentage=0.5,
                    budget_status="healthy",
                )
            )

    # Fallback if no specific surfaces matched
    if not slis:
        fallback_sli = ServiceLevelIndicator(
            sli_id=f"sli-{ecosystem_id}-uptime",
            surface_slug="platform",
            metric_name="uptime_pct",
            kind="availability",
            threshold=99.9,
            unit="%",
            description=f"{ecosystem_id} overall platform availability",
        )
        slis.append(fallback_sli)
        fallback_slo = ServiceLevelObjective(
            slo_id=f"slo-{ecosystem_id}-uptime",
            name="Platform 99.9% High Availability",
            surface_slug="platform",
            sli_id=fallback_sli.sli_id,
            target_percentage=99.9,
        )
        slos.append(fallback_slo)
        budgets.append(
            ErrorBudget(
                slo_id=fallback_slo.slo_id,
                total_budget_percentage=0.1,
                remaining_budget_percentage=0.1,
            )
        )
        slas.append(
            ServiceLevelAgreement(
                sla_id=f"sla-{ecosystem_id}-standard",
                customer_tier="business",
                surface_slug="platform",
                availability_target_pct=99.9,
                p95_latency_ms_target=500.0,
                financial_credit_pct=10.0,
                penalty_threshold_pct=98.5,
            )
        )

    return EcosystemSLAContract(
        ecosystem_id=ecosystem_id,
        version=version,
        slis=tuple(slis),
        slos=tuple(slos),
        error_budgets=tuple(budgets),
        slas=tuple(slas),
    )


# ---------------------------------------------------------------------------
# Evaluation & Simulation Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SLIEvaluationResult:
    """Evaluation result for an SLI against observed telemetry metrics."""

    sli_id: str
    surface_slug: str
    metric_name: str
    observed_value: float
    threshold: float
    unit: str
    is_good: bool
    compliance_pct: float
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sli_id": self.sli_id,
            "surface_slug": self.surface_slug,
            "metric_name": self.metric_name,
            "observed_value": self.observed_value,
            "threshold": self.threshold,
            "unit": self.unit,
            "is_good": self.is_good,
            "compliance_pct": self.compliance_pct,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ErrorBudgetBurnReport:
    """Detailed calculation of error budget burn rates and exhaustion forecast."""

    slo_id: str
    target_pct: float
    total_budget_pct: float
    consumed_pct: float
    remaining_pct: float
    burn_rate_1h: float
    burn_rate_6h: float
    burn_rate_24h: float
    hours_until_exhaustion: float | None
    status: BudgetStatus
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "slo_id": self.slo_id,
            "target_pct": self.target_pct,
            "total_budget_pct": self.total_budget_pct,
            "consumed_pct": self.consumed_pct,
            "remaining_pct": self.remaining_pct,
            "burn_rate_1h": self.burn_rate_1h,
            "burn_rate_6h": self.burn_rate_6h,
            "burn_rate_24h": self.burn_rate_24h,
            "hours_until_exhaustion": self.hours_until_exhaustion,
            "status": self.status,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class SLASimulationReport:
    """Full SLA compliance and error budget simulation report."""

    scenario: str
    sli_evaluations: tuple[SLIEvaluationResult, ...]
    burn_reports: tuple[ErrorBudgetBurnReport, ...]
    breached_slos: tuple[str, ...]
    breached_slas: tuple[str, ...]
    total_financial_credit_pct: float
    status: SLAStatus  # "compliant" | "at_risk" | "breached"
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "sli_evaluations": [e.to_dict() for e in self.sli_evaluations],
            "burn_reports": [b.to_dict() for b in self.burn_reports],
            "breached_slos": list(self.breached_slos),
            "breached_slas": list(self.breached_slas),
            "total_financial_credit_pct": self.total_financial_credit_pct,
            "status": self.status,
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class EcosystemSLAEngine:
    """Thread-safe in-process engine for SLI metric evaluation, error budget
    burn calculations, and SLA compliance simulation.
    """

    def __init__(self, contract: EcosystemSLAContract) -> None:
        self._contract = contract
        self._lock = threading.Lock()
        self._slis_by_id = {s.sli_id: s for s in contract.slis}
        self._slos_by_id = {o.slo_id: o for o in contract.slos}
        self._slas_by_id = {a.sla_id: a for a in contract.slas}

    @property
    def contract(self) -> EcosystemSLAContract:
        return self._contract

    def evaluate_sli_metrics(
        self,
        metrics: Mapping[str, float],
    ) -> tuple[SLIEvaluationResult, ...]:
        """Evaluate provided metrics against all contract SLIs."""
        results: list[SLIEvaluationResult] = []
        with self._lock:
            for sli in self._contract.slis:
                # Key format: "<surface_slug>:<metric_name>" or "<metric_name>"
                lookup_key = f"{sli.surface_slug}:{sli.metric_name}"
                val = metrics.get(lookup_key)
                if val is None:
                    val = metrics.get(sli.metric_name)

                if val is None:
                    # Default compliant observation if not provided
                    val = sli.threshold

                if sli.kind == "availability":
                    # Higher is better: observed >= threshold
                    is_good = val >= sli.threshold
                    compliance = round((val / sli.threshold) * 100.0, 2) if sli.threshold > 0 else 100.0
                elif sli.kind == "latency":
                    # Lower is better: observed <= threshold
                    is_good = val <= sli.threshold
                    compliance = round((sli.threshold / max(val, 1.0)) * 100.0, 2)
                else:
                    is_good = val >= sli.threshold
                    compliance = 100.0 if is_good else 80.0

                comp_clamped = min(100.0, max(0.0, compliance))
                verdict = "PASSED" if is_good else "BREACHED"
                msg = f"SLI {sli.sli_id} [{verdict}]: {sli.metric_name} = {val}{sli.unit} (threshold: {sli.threshold}{sli.unit})"

                results.append(
                    SLIEvaluationResult(
                        sli_id=sli.sli_id,
                        surface_slug=sli.surface_slug,
                        metric_name=sli.metric_name,
                        observed_value=float(val),
                        threshold=sli.threshold,
                        unit=sli.unit,
                        is_good=is_good,
                        compliance_pct=comp_clamped,
                        message=msg,
                    )
                )
        return tuple(results)

    def calculate_error_budget_burn(
        self,
        slo_id: str,
        error_rate_pct: float,
        time_window_hours: float = 1.0,
    ) -> ErrorBudgetBurnReport:
        """Calculate error budget burn rate and projected exhaustion."""
        with self._lock:
            slo = self._slos_by_id.get(slo_id)
            if slo is None:
                return ErrorBudgetBurnReport(
                    slo_id=slo_id,
                    target_pct=99.9,
                    total_budget_pct=0.1,
                    consumed_pct=0.0,
                    remaining_pct=0.1,
                    burn_rate_1h=0.0,
                    burn_rate_6h=0.0,
                    burn_rate_24h=0.0,
                    hours_until_exhaustion=None,
                    status="healthy",
                    summary=f"SLO '{slo_id}' not found in contract",
                )

            total_budget = round(100.0 - slo.target_percentage, 4)
            if total_budget <= 0.0:
                total_budget = 0.01

            # Burn rate = (observed error rate) / (acceptable error rate)
            burn_1h = round(error_rate_pct / total_budget, 2)
            burn_6h = round(burn_1h * 0.85, 2)
            burn_24h = round(burn_1h * 0.70, 2)

            # Consumed percentage
            consumed = min(total_budget, round((burn_1h * time_window_hours * (total_budget / 720.0)), 4))
            remaining = max(0.0, round(total_budget - consumed, 4))

            if remaining <= 0.0 or burn_1h >= 14.4 or consumed >= total_budget:
                status: BudgetStatus = "exhausted"
            elif burn_1h >= 3.0 or remaining < (total_budget * 0.25):
                status = "warning"
            else:
                status = "healthy"

            # Exhaustion forecast: (remaining / (burn_rate * (total_budget/720)))
            if burn_1h > 0.0:
                hourly_burn = (burn_1h * total_budget) / 720.0
                hours_left = round(remaining / hourly_burn, 1) if hourly_burn > 0 else None
            else:
                hours_left = None

            summary = (
                f"SLO {slo.name}: remaining budget {remaining:.4f}% of {total_budget:.4f}% "
                f"(burn 1h: {burn_1h}x, status: {status.upper()})"
            )

            return ErrorBudgetBurnReport(
                slo_id=slo.slo_id,
                target_pct=slo.target_percentage,
                total_budget_pct=total_budget,
                consumed_pct=consumed,
                remaining_pct=remaining,
                burn_rate_1h=burn_1h,
                burn_rate_6h=burn_6h,
                burn_rate_24h=burn_24h,
                hours_until_exhaustion=hours_left,
                status=status,
                summary=summary,
            )

    def simulate_sla_compliance(
        self,
        scenario: str = "normal_operations",
        metrics: Mapping[str, float] | None = None,
    ) -> SLASimulationReport:
        """Simulate SLA compliance, error budget burn, and financial penalty liabilities."""
        with self._lock:
            scenario_norm = scenario.lower().replace("-", "_")

            sim_metrics: dict[str, float] = {}

            if "normal" in scenario_norm or "healthy" in scenario_norm:
                # Fully compliant baseline
                for sli in self._contract.slis:
                    sim_metrics[f"{sli.surface_slug}:{sli.metric_name}"] = (
                        sli.threshold if sli.kind == "availability" else sli.threshold * 0.5
                    )
                err_rate = 0.02
                time_hours = 1.0

            elif "minor" in scenario_norm or "degradation" in scenario_norm:
                # Mild latency degradation, slight error increase
                for sli in self._contract.slis:
                    if sli.kind == "latency":
                        sim_metrics[f"{sli.surface_slug}:{sli.metric_name}"] = sli.threshold * 1.15
                    else:
                        sim_metrics[f"{sli.surface_slug}:{sli.metric_name}"] = sli.threshold - 0.05
                err_rate = 0.15
                time_hours = 3.0

            elif "budget" in scenario_norm or "exhaustion" in scenario_norm:
                # Error budget completely consumed
                for sli in self._contract.slis:
                    if sli.kind == "latency":
                        sim_metrics[f"{sli.surface_slug}:{sli.metric_name}"] = sli.threshold * 2.5
                    else:
                        sim_metrics[f"{sli.surface_slug}:{sli.metric_name}"] = sli.threshold - 2.0
                err_rate = 2.5
                time_hours = 720.0

            else:
                # Severe outage: 5xx errors, high latency
                for sli in self._contract.slis:
                    if sli.kind == "latency":
                        sim_metrics[f"{sli.surface_slug}:{sli.metric_name}"] = sli.threshold * 3.5
                    else:
                        sim_metrics[f"{sli.surface_slug}:{sli.metric_name}"] = sli.threshold - 3.5
                err_rate = 8.5
                time_hours = 2.0

            # Override with custom metrics if provided
            if metrics:
                sim_metrics.update(metrics)

        # Step 1: Evaluate SLIs
        sli_evals = self.evaluate_sli_metrics(sim_metrics)
        evals_by_id = {e.sli_id: e for e in sli_evals}

        # Step 2: Calculate SLO error budgets
        burn_reports: list[ErrorBudgetBurnReport] = []
        breached_slos: list[str] = []

        for slo in self._contract.slos:
            ev = evals_by_id.get(slo.sli_id)
            observed_err = max(0.0, 100.0 - ev.observed_value) if ev and ev.unit == "%" else err_rate
            rep = self.calculate_error_budget_burn(slo.slo_id, observed_err, time_hours)
            burn_reports.append(rep)
            if not (ev and ev.is_good) or rep.status == "exhausted":
                breached_slos.append(slo.slo_id)

        # Step 3: Evaluate SLAs and Financial Liabilities
        breached_slas: list[str] = []
        total_credit_pct = 0.0

        for sla in self._contract.slas:
            # Find matching availability SLI for this surface
            matched_evals = [e for e in sli_evals if e.surface_slug == sla.surface_slug and "avail" in e.metric_name]
            if not matched_evals:
                matched_evals = [e for e in sli_evals if e.surface_slug == sla.surface_slug]

            sla_breached = False
            for me in matched_evals:
                if me.unit == "%" and me.observed_value < sla.penalty_threshold_pct:
                    sla_breached = True
                    break

            if sla_breached:
                breached_slas.append(sla.sla_id)
                total_credit_pct += sla.financial_credit_pct

        total_credit_pct = min(100.0, total_credit_pct)

        any_budget_exhausted = any(b.status == "exhausted" for b in burn_reports)
        if breached_slas or any_budget_exhausted:
            status: SLAStatus = "breached"
            summary = (
                f"SLA simulation '{scenario}' BREACHED: {len(breached_slas)} SLA agreements violated "
                f"({len(breached_slos)} SLOs breached, budget exhausted: {any_budget_exhausted}). Financial liability: {total_credit_pct:.1f}% customer credits."
            )
        elif breached_slos:
            status = "at_risk"
            summary = (
                f"SLA simulation '{scenario}' AT RISK: {len(breached_slos)} internal SLOs breached. "
                f"External SLAs currently preserved (0% penalties)."
            )
        else:
            status = "compliant"
            summary = (
                f"SLA simulation '{scenario}' COMPLIANT: All {len(self._contract.slis)} SLIs satisfied. "
                f"Error budgets healthy (0 breaches)."
            )

        return SLASimulationReport(
            scenario=scenario,
            sli_evaluations=sli_evals,
            burn_reports=tuple(burn_reports),
            breached_slos=tuple(breached_slos),
            breached_slas=tuple(breached_slas),
            total_financial_credit_pct=total_credit_pct,
            status=status,
            summary=summary,
        )

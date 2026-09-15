"""Ecosystem Multi-Surface Capacity Planning, Resource Quotas, and Unit Economics Budgeting (R-455).

Provides canonical resource quotas, surface capacity specs, unit economics cost models,
and a deterministic EcosystemCapacityContract derived from ecosystem surfaces. An in-process
thread-safe EcosystemCapacityEngine simulates workload tiers (base, peak, stress), capacity limits,
and monthly unit economics / cloud cost projections offline.

Zero external dependencies — Python 3.13 stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ResourceQuota:
    """A resource quota definition for a single surface."""

    quota_id: str
    surface_slug: str
    resource_kind: str  # "cpu_cores" | "memory_mb" | "storage_gb" | "bandwidth_mbps" | "concurrent_connections" | "requests_per_second"
    limit_value: float
    burst_limit_value: float
    unit: str
    enforcement_action: str = "throttle"  # "throttle" | "queue" | "reject" | "scale_out"

    def to_dict(self) -> dict[str, Any]:
        return {
            "quota_id": self.quota_id,
            "surface_slug": self.surface_slug,
            "resource_kind": self.resource_kind,
            "limit_value": self.limit_value,
            "burst_limit_value": self.burst_limit_value,
            "unit": self.unit,
            "enforcement_action": self.enforcement_action,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ResourceQuota:
        return cls(
            quota_id=str(data.get("quota_id", "")),
            surface_slug=str(data.get("surface_slug", "")),
            resource_kind=str(data.get("resource_kind", "requests_per_second")),
            limit_value=float(data.get("limit_value", 0.0)),
            burst_limit_value=float(data.get("burst_limit_value", data.get("limit_value", 0.0))),
            unit=str(data.get("unit", "")),
            enforcement_action=str(data.get("enforcement_action", "throttle")),
        )


@dataclass(frozen=True, slots=True)
class SurfaceCapacitySpec:
    """Capacity and auto-scaling specification for one surface."""

    surface_slug: str
    surface_kind: str
    min_replicas: int = 1
    max_replicas: int = 5
    target_cpu_utilization_pct: int = 70
    target_memory_utilization_pct: int = 75
    requests_per_replica_limit: int = 250
    scale_down_stabilization_seconds: int = 300

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_slug": self.surface_slug,
            "surface_kind": self.surface_kind,
            "min_replicas": self.min_replicas,
            "max_replicas": self.max_replicas,
            "target_cpu_utilization_pct": self.target_cpu_utilization_pct,
            "target_memory_utilization_pct": self.target_memory_utilization_pct,
            "requests_per_replica_limit": self.requests_per_replica_limit,
            "scale_down_stabilization_seconds": self.scale_down_stabilization_seconds,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SurfaceCapacitySpec:
        return cls(
            surface_slug=str(data.get("surface_slug", "")),
            surface_kind=str(data.get("surface_kind", "")),
            min_replicas=int(data.get("min_replicas", 1)),
            max_replicas=int(data.get("max_replicas", 5)),
            target_cpu_utilization_pct=int(data.get("target_cpu_utilization_pct", 70)),
            target_memory_utilization_pct=int(data.get("target_memory_utilization_pct", 75)),
            requests_per_replica_limit=int(data.get("requests_per_replica_limit", 250)),
            scale_down_stabilization_seconds=int(data.get("scale_down_stabilization_seconds", 300)),
        )


@dataclass(frozen=True, slots=True)
class UnitEconomicsCostModel:
    """Cost model for surface unit economics and monthly cloud budgeting."""

    cost_model_id: str
    surface_slug: str
    base_monthly_cost_usd: float = 20.0
    marginal_cost_per_1k_requests_usd: float = 0.01
    marginal_cost_per_gb_storage_usd: float = 0.10
    currency: str = "USD"
    cost_tier: str = "starter"  # "free" | "starter" | "growth" | "enterprise"

    def to_dict(self) -> dict[str, Any]:
        return {
            "cost_model_id": self.cost_model_id,
            "surface_slug": self.surface_slug,
            "base_monthly_cost_usd": self.base_monthly_cost_usd,
            "marginal_cost_per_1k_requests_usd": self.marginal_cost_per_1k_requests_usd,
            "marginal_cost_per_gb_storage_usd": self.marginal_cost_per_gb_storage_usd,
            "currency": self.currency,
            "cost_tier": self.cost_tier,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> UnitEconomicsCostModel:
        return cls(
            cost_model_id=str(data.get("cost_model_id", "")),
            surface_slug=str(data.get("surface_slug", "")),
            base_monthly_cost_usd=float(data.get("base_monthly_cost_usd", 20.0)),
            marginal_cost_per_1k_requests_usd=float(data.get("marginal_cost_per_1k_requests_usd", 0.01)),
            marginal_cost_per_gb_storage_usd=float(data.get("marginal_cost_per_gb_storage_usd", 0.10)),
            currency=str(data.get("currency", "USD")),
            cost_tier=str(data.get("cost_tier", "starter")),
        )


@dataclass(frozen=True, slots=True)
class EcosystemCapacityContract:
    """A complete multi-surface capacity, quota, and unit economics contract."""

    ecosystem_id: str
    version: str
    surface_capacities: tuple[SurfaceCapacitySpec, ...] = ()
    resource_quotas: tuple[ResourceQuota, ...] = ()
    cost_models: tuple[UnitEconomicsCostModel, ...] = ()
    monthly_budget_limit_usd: float = 1000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "surface_capacities": [c.to_dict() for c in self.surface_capacities],
            "resource_quotas": [q.to_dict() for q in self.resource_quotas],
            "cost_models": [m.to_dict() for m in self.cost_models],
            "monthly_budget_limit_usd": self.monthly_budget_limit_usd,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemCapacityContract:
        raw_caps = data.get("surface_capacities", ())
        caps = tuple(SurfaceCapacitySpec.from_dict(c) for c in raw_caps if isinstance(c, Mapping))

        raw_quotas = data.get("resource_quotas", ())
        quotas = tuple(ResourceQuota.from_dict(q) for q in raw_quotas if isinstance(q, Mapping))

        raw_models = data.get("cost_models", ())
        models = tuple(UnitEconomicsCostModel.from_dict(m) for m in raw_models if isinstance(m, Mapping))

        return cls(
            ecosystem_id=str(data.get("ecosystem_id", "")),
            version=str(data.get("version", "1.0.0")),
            surface_capacities=caps,
            resource_quotas=quotas,
            cost_models=models,
            monthly_budget_limit_usd=float(data.get("monthly_budget_limit_usd", 1000.0)),
        )

    def to_json(self) -> str:
        """Serialize contract to indented JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> EcosystemCapacityContract:
        """Deserialize contract from JSON string."""
        return cls.from_dict(json.loads(text))

    def digest(self) -> str:
        """Deterministic 64-char hex SHA-256 digest of canonical JSON serialization."""
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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


def synthesize_ecosystem_capacity(
    ecosystem_id: str,
    surfaces: Sequence[Mapping[str, Any]],
    version: str = "1.0.0",
    monthly_budget_limit_usd: float = 1000.0,
) -> EcosystemCapacityContract:
    """Synthesize canonical multi-surface capacity specs, resource quotas, and
    unit economics cost models.

    Fully deterministic, 100% offline, 0 network or filesystem I/O.
    """
    specs: list[SurfaceCapacitySpec] = []
    quotas: list[ResourceQuota] = []
    models: list[UnitEconomicsCostModel] = []

    for s in surfaces:
        slug = _surface_slug_from(s)
        kind = _surface_kind_from(s).lower()

        if kind in ("database", "postgres", "sqlite", "mysql") or "db" in slug:
            # Database surface: singleton vertical scaling or primary/replica
            specs.append(
                SurfaceCapacitySpec(
                    surface_slug=slug,
                    surface_kind=kind,
                    min_replicas=1,
                    max_replicas=1,
                    target_cpu_utilization_pct=80,
                    target_memory_utilization_pct=80,
                    requests_per_replica_limit=1000,
                    scale_down_stabilization_seconds=600,
                )
            )
            quotas.append(
                ResourceQuota(
                    quota_id=f"quota-{slug}-cpu",
                    surface_slug=slug,
                    resource_kind="cpu_cores",
                    limit_value=4.0,
                    burst_limit_value=8.0,
                    unit="cores",
                    enforcement_action="throttle",
                )
            )
            quotas.append(
                ResourceQuota(
                    quota_id=f"quota-{slug}-memory",
                    surface_slug=slug,
                    resource_kind="memory_mb",
                    limit_value=4096.0,
                    burst_limit_value=8192.0,
                    unit="MB",
                    enforcement_action="reject",
                )
            )
            quotas.append(
                ResourceQuota(
                    quota_id=f"quota-{slug}-connections",
                    surface_slug=slug,
                    resource_kind="concurrent_connections",
                    limit_value=200.0,
                    burst_limit_value=400.0,
                    unit="connections",
                    enforcement_action="queue",
                )
            )
            models.append(
                UnitEconomicsCostModel(
                    cost_model_id=f"cost-{slug}",
                    surface_slug=slug,
                    base_monthly_cost_usd=35.0,
                    marginal_cost_per_1k_requests_usd=0.005,
                    marginal_cost_per_gb_storage_usd=0.15,
                    currency="USD",
                    cost_tier="starter",
                )
            )

        elif kind in ("api", "api_gateway", "backend", "backend_api", "worker"):
            # API / Backend surface: horizontal auto-scaling
            specs.append(
                SurfaceCapacitySpec(
                    surface_slug=slug,
                    surface_kind=kind,
                    min_replicas=2,
                    max_replicas=10,
                    target_cpu_utilization_pct=70,
                    target_memory_utilization_pct=75,
                    requests_per_replica_limit=300,
                    scale_down_stabilization_seconds=300,
                )
            )
            quotas.append(
                ResourceQuota(
                    quota_id=f"quota-{slug}-cpu",
                    surface_slug=slug,
                    resource_kind="cpu_cores",
                    limit_value=4.0,
                    burst_limit_value=8.0,
                    unit="cores",
                    enforcement_action="scale_out",
                )
            )
            quotas.append(
                ResourceQuota(
                    quota_id=f"quota-{slug}-memory",
                    surface_slug=slug,
                    resource_kind="memory_mb",
                    limit_value=2048.0,
                    burst_limit_value=4096.0,
                    unit="MB",
                    enforcement_action="scale_out",
                )
            )
            quotas.append(
                ResourceQuota(
                    quota_id=f"quota-{slug}-rps",
                    surface_slug=slug,
                    resource_kind="requests_per_second",
                    limit_value=250.0,
                    burst_limit_value=500.0,
                    unit="rps",
                    enforcement_action="throttle",
                )
            )
            models.append(
                UnitEconomicsCostModel(
                    cost_model_id=f"cost-{slug}",
                    surface_slug=slug,
                    base_monthly_cost_usd=25.0,
                    marginal_cost_per_1k_requests_usd=0.015,
                    marginal_cost_per_gb_storage_usd=0.08,
                    currency="USD",
                    cost_tier="starter",
                )
            )

        else:
            # Customer Web / Admin / Frontend surface
            specs.append(
                SurfaceCapacitySpec(
                    surface_slug=slug,
                    surface_kind=kind,
                    min_replicas=1,
                    max_replicas=6,
                    target_cpu_utilization_pct=65,
                    target_memory_utilization_pct=70,
                    requests_per_replica_limit=500,
                    scale_down_stabilization_seconds=180,
                )
            )
            quotas.append(
                ResourceQuota(
                    quota_id=f"quota-{slug}-bandwidth",
                    surface_slug=slug,
                    resource_kind="bandwidth_mbps",
                    limit_value=100.0,
                    burst_limit_value=250.0,
                    unit="mbps",
                    enforcement_action="throttle",
                )
            )
            quotas.append(
                ResourceQuota(
                    quota_id=f"quota-{slug}-rps",
                    surface_slug=slug,
                    resource_kind="requests_per_second",
                    limit_value=300.0,
                    burst_limit_value=600.0,
                    unit="rps",
                    enforcement_action="throttle",
                )
            )
            models.append(
                UnitEconomicsCostModel(
                    cost_model_id=f"cost-{slug}",
                    surface_slug=slug,
                    base_monthly_cost_usd=15.0,
                    marginal_cost_per_1k_requests_usd=0.008,
                    marginal_cost_per_gb_storage_usd=0.05,
                    currency="USD",
                    cost_tier="starter",
                )
            )

    if not specs:
        # Fallback default capacity spec
        specs.append(
            SurfaceCapacitySpec(
                surface_slug="root",
                surface_kind="customer_web",
                min_replicas=1,
                max_replicas=4,
                target_cpu_utilization_pct=70,
                target_memory_utilization_pct=70,
                requests_per_replica_limit=250,
                scale_down_stabilization_seconds=300,
            )
        )
        quotas.append(
            ResourceQuota(
                quota_id=f"quota-{ecosystem_id}-root-rps",
                surface_slug="root",
                resource_kind="requests_per_second",
                limit_value=100.0,
                burst_limit_value=200.0,
                unit="rps",
                enforcement_action="throttle",
            )
        )
        models.append(
            UnitEconomicsCostModel(
                cost_model_id=f"cost-{ecosystem_id}-root",
                surface_slug="root",
                base_monthly_cost_usd=20.0,
                marginal_cost_per_1k_requests_usd=0.01,
                marginal_cost_per_gb_storage_usd=0.10,
                currency="USD",
                cost_tier="starter",
            )
        )

    return EcosystemCapacityContract(
        ecosystem_id=ecosystem_id,
        version=version,
        surface_capacities=tuple(specs),
        resource_quotas=tuple(quotas),
        cost_models=tuple(models),
        monthly_budget_limit_usd=monthly_budget_limit_usd,
    )


# ---------------------------------------------------------------------------
# Simulation Engine
# ---------------------------------------------------------------------------


@dataclass
class SurfaceCapacityProjection:
    """Capacity and cost projection for one surface in a simulated workload."""

    surface_slug: str
    required_replicas: int
    estimated_cpu_cores: float
    estimated_memory_mb: int
    estimated_monthly_cost_usd: float
    quota_violations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_slug": self.surface_slug,
            "required_replicas": self.required_replicas,
            "estimated_cpu_cores": round(self.estimated_cpu_cores, 2),
            "estimated_memory_mb": self.estimated_memory_mb,
            "estimated_monthly_cost_usd": round(self.estimated_monthly_cost_usd, 2),
            "quota_violations": list(self.quota_violations),
        }


@dataclass
class CapacitySimulationReport:
    """Overall simulation report across all surfaces for a specified tier."""

    tier: str
    total_monthly_requests: int
    surface_projections: list[SurfaceCapacityProjection]
    total_monthly_cost_usd: float
    monthly_budget_limit_usd: float
    within_budget: bool
    status: str  # "pass" | "warning" | "breach"
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "total_monthly_requests": self.total_monthly_requests,
            "surface_projections": [p.to_dict() for p in self.surface_projections],
            "total_monthly_cost_usd": round(self.total_monthly_cost_usd, 2),
            "monthly_budget_limit_usd": round(self.monthly_budget_limit_usd, 2),
            "within_budget": self.within_budget,
            "status": self.status,
            "summary": self.summary,
        }


@dataclass
class QuotaEvaluationResult:
    """Result of evaluating a resource allocation against defined quotas."""

    surface_slug: str
    resource_kind: str
    allowed: bool
    limit_value: float
    burst_limit_value: float
    proposed_value: float
    enforcement_action: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_slug": self.surface_slug,
            "resource_kind": self.resource_kind,
            "allowed": self.allowed,
            "limit_value": self.limit_value,
            "burst_limit_value": self.burst_limit_value,
            "proposed_value": self.proposed_value,
            "enforcement_action": self.enforcement_action,
            "message": self.message,
        }


@dataclass
class UnitEconomicsReport:
    """Unit economics projection based on MAU and user activity."""

    monthly_active_users: int
    requests_per_user_monthly: int
    total_requests: int
    total_cost_usd: float
    cost_per_active_user_usd: float
    cost_per_1k_requests_usd: float
    monthly_budget_limit_usd: float
    within_budget: bool
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "monthly_active_users": self.monthly_active_users,
            "requests_per_user_monthly": self.requests_per_user_monthly,
            "total_requests": self.total_requests,
            "total_cost_usd": round(self.total_cost_usd, 2),
            "cost_per_active_user_usd": round(self.cost_per_active_user_usd, 4),
            "cost_per_1k_requests_usd": round(self.cost_per_1k_requests_usd, 4),
            "monthly_budget_limit_usd": round(self.monthly_budget_limit_usd, 2),
            "within_budget": self.within_budget,
            "summary": self.summary,
        }


class EcosystemCapacityEngine:
    """Thread-safe, in-process, fully deterministic capacity planning engine.

    Simulates workload tiers, evaluates resource quotas, and computes unit
    economics without external network or filesystem dependencies.
    """

    def __init__(self, contract: EcosystemCapacityContract) -> None:
        self._contract = contract
        self._lock = threading.Lock()

    @property
    def contract(self) -> EcosystemCapacityContract:
        return self._contract

    def simulate_workload_tier(
        self,
        tier: str = "base",
        monthly_requests: int = 100_000,
    ) -> CapacitySimulationReport:
        """Simulate capacity and cost projections for a given workload tier.

        Tiers:
          - 'base': standard steady-state load (1.0x)
          - 'peak': traffic burst / high hours (2.5x)
          - 'stress': 6.0x stress / peak flash sale load
        """
        tier_normalized = tier.lower() if tier.lower() in ("base", "peak", "stress") else "base"
        multiplier = 1.0 if tier_normalized == "base" else (2.5 if tier_normalized == "peak" else 6.0)

        effective_requests = int(monthly_requests * multiplier)
        projections: list[SurfaceCapacityProjection] = []
        total_cost = 0.0
        has_quota_breach = False

        with self._lock:
            # Requests per second average (assuming 30 days, 86400s per day)
            avg_rps = effective_requests / (30.0 * 86400.0)

            for spec in self._contract.surface_capacities:
                slug = spec.surface_slug
                # Replicas required based on limit
                req_limit = max(1, spec.requests_per_replica_limit)
                # Assume peak rps can be 4x avg_rps during working hours
                peak_rps_surface = max(1.0, avg_rps * 4.0)

                needed_reps = max(spec.min_replicas, math.ceil(peak_rps_surface / req_limit))
                reps = min(needed_reps, spec.max_replicas)

                # Check if required replicas exceed max_replicas
                violations: list[str] = []
                if needed_reps > spec.max_replicas:
                    violations.append(
                        f"Required {needed_reps} replicas exceeds max_replicas ({spec.max_replicas})"
                    )
                    has_quota_breach = True

                # CPU and memory estimates per replica
                cpu_per_rep = 1.0 if "db" not in slug else 2.0
                mem_per_rep = 1024 if "db" not in slug else 4096
                total_cpu = reps * cpu_per_rep
                total_mem = reps * mem_per_rep

                # Check resource quotas
                surface_quotas = [q for q in self._contract.resource_quotas if q.surface_slug == slug]
                for q in surface_quotas:
                    if q.resource_kind == "cpu_cores" and total_cpu > q.burst_limit_value:
                        violations.append(
                            f"Projected CPU {total_cpu:.1f} cores exceeds quota burst limit {q.burst_limit_value:.1f}"
                        )
                        has_quota_breach = True
                    elif q.resource_kind == "memory_mb" and total_mem > q.burst_limit_value:
                        violations.append(
                            f"Projected Memory {total_mem} MB exceeds quota burst limit {q.burst_limit_value:.0f} MB"
                        )
                        has_quota_breach = True
                    elif q.resource_kind == "requests_per_second" and peak_rps_surface > q.burst_limit_value:
                        violations.append(
                            f"Projected {peak_rps_surface:.1f} rps exceeds quota burst limit {q.burst_limit_value:.1f}"
                        )
                        has_quota_breach = True

                # Cost estimation for surface
                cost_model = next((m for m in self._contract.cost_models if m.surface_slug == slug), None)
                if cost_model:
                    base_cost = cost_model.base_monthly_cost_usd * reps
                    req_cost = (effective_requests / 1000.0) * cost_model.marginal_cost_per_1k_requests_usd
                    surf_cost = base_cost + req_cost
                else:
                    surf_cost = 20.0 * reps

                total_cost += surf_cost
                projections.append(
                    SurfaceCapacityProjection(
                        surface_slug=slug,
                        required_replicas=reps,
                        estimated_cpu_cores=total_cpu,
                        estimated_memory_mb=total_mem,
                        estimated_monthly_cost_usd=surf_cost,
                        quota_violations=violations,
                    )
                )

            budget = self._contract.monthly_budget_limit_usd
            within_budget = total_cost <= budget

            if within_budget and not has_quota_breach:
                status = "pass"
                summary = f"Capacity simulation for '{tier_normalized}' tier passed within ${budget:.2f}/mo budget."
            elif not within_budget and total_cost <= (budget * 1.25) and not has_quota_breach:
                status = "warning"
                summary = f"Cost (${total_cost:.2f}) moderately exceeds budget (${budget:.2f}) under '{tier_normalized}' tier."
            else:
                status = "breach"
                summary = f"Capacity limits or budget breached: total ${total_cost:.2f}/mo vs ${budget:.2f} budget."

            return CapacitySimulationReport(
                tier=tier_normalized,
                total_monthly_requests=effective_requests,
                surface_projections=projections,
                total_monthly_cost_usd=total_cost,
                monthly_budget_limit_usd=budget,
                within_budget=within_budget,
                status=status,
                summary=summary,
            )

    def evaluate_quota(
        self,
        surface_slug: str,
        resource_kind: str,
        proposed_value: float,
    ) -> QuotaEvaluationResult:
        """Evaluate a proposed resource consumption against the defined quotas."""
        with self._lock:
            match = next(
                (
                    q
                    for q in self._contract.resource_quotas
                    if q.surface_slug == surface_slug and q.resource_kind == resource_kind
                ),
                None,
            )
            if not match:
                return QuotaEvaluationResult(
                    surface_slug=surface_slug,
                    resource_kind=resource_kind,
                    allowed=True,
                    limit_value=0.0,
                    burst_limit_value=0.0,
                    proposed_value=proposed_value,
                    enforcement_action="none",
                    message=f"No quota defined for {surface_slug}/{resource_kind}; permitted by default.",
                )

            if proposed_value <= match.limit_value:
                return QuotaEvaluationResult(
                    surface_slug=surface_slug,
                    resource_kind=resource_kind,
                    allowed=True,
                    limit_value=match.limit_value,
                    burst_limit_value=match.burst_limit_value,
                    proposed_value=proposed_value,
                    enforcement_action=match.enforcement_action,
                    message=f"Within quota limit ({proposed_value} <= {match.limit_value} {match.unit})",
                )
            elif proposed_value <= match.burst_limit_value:
                return QuotaEvaluationResult(
                    surface_slug=surface_slug,
                    resource_kind=resource_kind,
                    allowed=True,
                    limit_value=match.limit_value,
                    burst_limit_value=match.burst_limit_value,
                    proposed_value=proposed_value,
                    enforcement_action=match.enforcement_action,
                    message=f"Operating in burst window ({proposed_value} <= {match.burst_limit_value} {match.unit})",
                )
            else:
                return QuotaEvaluationResult(
                    surface_slug=surface_slug,
                    resource_kind=resource_kind,
                    allowed=False,
                    limit_value=match.limit_value,
                    burst_limit_value=match.burst_limit_value,
                    proposed_value=proposed_value,
                    enforcement_action=match.enforcement_action,
                    message=f"Exceeds burst limit ({proposed_value} > {match.burst_limit_value} {match.unit}); action: {match.enforcement_action}",
                )

    def estimate_monthly_unit_economics(
        self,
        monthly_active_users: int = 10_000,
        requests_per_user_monthly: int = 50,
    ) -> UnitEconomicsReport:
        """Estimate per-user and per-thousand request unit economics."""
        with self._lock:
            mau = max(1, monthly_active_users)
            rpu = max(1, requests_per_user_monthly)
            total_requests = mau * rpu

            total_cost = 0.0
            for model in self._contract.cost_models:
                base = model.base_monthly_cost_usd
                req = (total_requests / 1000.0) * model.marginal_cost_per_1k_requests_usd
                total_cost += base + req

            cost_per_user = total_cost / float(mau)
            cost_per_1k = (total_cost / float(total_requests)) * 1000.0
            budget = self._contract.monthly_budget_limit_usd
            within_budget = total_cost <= budget

            summary = (
                f"Projected ${total_cost:.2f}/mo for {mau:,} MAU "
                f"(${cost_per_user:.4f}/user, ${cost_per_1k:.4f}/1k requests)."
            )

            return UnitEconomicsReport(
                monthly_active_users=mau,
                requests_per_user_monthly=rpu,
                total_requests=total_requests,
                total_cost_usd=total_cost,
                cost_per_active_user_usd=cost_per_user,
                cost_per_1k_requests_usd=cost_per_1k,
                monthly_budget_limit_usd=budget,
                within_budget=within_budget,
                summary=summary,
            )

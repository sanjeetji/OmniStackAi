"""Ecosystem Multi-Surface Health Check, Smoke Testing, and Canary Verification (R-453).

Provides canonical health check probes, smoke test specs, canary verification rules, and a
deterministic EcosystemVerificationContract derived from ecosystem surfaces. An in-process
thread-safe EcosystemVerificationEngine simulates probe and test evaluation offline.

Zero external dependencies — Python 3.13 stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HealthCheckProbe:
    """A single health check probe targeting one surface endpoint."""

    probe_id: str
    surface_slug: str
    surface_kind: str
    method: str = "GET"
    endpoint: str = "/healthz"
    expected_status: int = 200
    timeout_seconds: int = 5
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "surface_slug": self.surface_slug,
            "surface_kind": self.surface_kind,
            "method": self.method,
            "endpoint": self.endpoint,
            "expected_status": self.expected_status,
            "timeout_seconds": self.timeout_seconds,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> HealthCheckProbe:
        return cls(
            probe_id=str(data.get("probe_id", "")),
            surface_slug=str(data.get("surface_slug", "")),
            surface_kind=str(data.get("surface_kind", "")),
            method=str(data.get("method", "GET")),
            endpoint=str(data.get("endpoint", "/healthz")),
            expected_status=int(data.get("expected_status", 200)),
            timeout_seconds=int(data.get("timeout_seconds", 5)),
            tags=tuple(str(t) for t in data.get("tags", ())),
        )


@dataclass(frozen=True, slots=True)
class SmokeTestStep:
    """One step in a smoke test sequence."""

    step_id: str
    description: str
    action: str
    target: str = ""
    expected: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "action": self.action,
            "target": self.target,
            "expected": self.expected,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SmokeTestStep:
        return cls(
            step_id=str(data.get("step_id", "")),
            description=str(data.get("description", "")),
            action=str(data.get("action", "")),
            target=str(data.get("target", "")),
            expected=str(data.get("expected", "")),
        )


@dataclass(frozen=True, slots=True)
class SmokeTestSpec:
    """A functional smoke test targeting one surface's critical user flow."""

    test_id: str
    surface_slug: str
    name: str
    category: str = "functional"
    steps: tuple[SmokeTestStep, ...] = ()
    expected_outcome: str = "success"

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "surface_slug": self.surface_slug,
            "name": self.name,
            "category": self.category,
            "steps": [s.to_dict() for s in self.steps],
            "expected_outcome": self.expected_outcome,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SmokeTestSpec:
        return cls(
            test_id=str(data.get("test_id", "")),
            surface_slug=str(data.get("surface_slug", "")),
            name=str(data.get("name", "")),
            category=str(data.get("category", "functional")),
            steps=tuple(
                SmokeTestStep.from_dict(s) for s in data.get("steps", ())
            ),
            expected_outcome=str(data.get("expected_outcome", "success")),
        )


@dataclass(frozen=True, slots=True)
class CanaryVerificationRule:
    """Cross-surface canary assertion that fires on a trigger condition."""

    rule_id: str
    surfaces_covered: tuple[str, ...]
    trigger: str
    assertion: str
    severity: str = "warning"  # "info" | "warning" | "error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "surfaces_covered": list(self.surfaces_covered),
            "trigger": self.trigger,
            "assertion": self.assertion,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CanaryVerificationRule:
        return cls(
            rule_id=str(data.get("rule_id", "")),
            surfaces_covered=tuple(str(s) for s in data.get("surfaces_covered", ())),
            trigger=str(data.get("trigger", "")),
            assertion=str(data.get("assertion", "")),
            severity=str(data.get("severity", "warning")),
        )


@dataclass(frozen=True, slots=True)
class EcosystemVerificationContract:
    """Portable, offline-evaluable verification contract for an ecosystem."""

    ecosystem_id: str
    version: str
    probes: tuple[HealthCheckProbe, ...] = ()
    smoke_tests: tuple[SmokeTestSpec, ...] = ()
    canary_rules: tuple[CanaryVerificationRule, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "probes": [p.to_dict() for p in self.probes],
            "smoke_tests": [t.to_dict() for t in self.smoke_tests],
            "canary_rules": [r.to_dict() for r in self.canary_rules],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemVerificationContract:
        return cls(
            ecosystem_id=str(data.get("ecosystem_id", "")),
            version=str(data.get("version", "1.0.0")),
            probes=tuple(
                HealthCheckProbe.from_dict(p) for p in data.get("probes", ())
            ),
            smoke_tests=tuple(
                SmokeTestSpec.from_dict(t) for t in data.get("smoke_tests", ())
            ),
            canary_rules=tuple(
                CanaryVerificationRule.from_dict(r) for r in data.get("canary_rules", ())
            ),
        )

    def digest(self) -> str:
        """Deterministic SHA-256 over the canonical JSON representation."""
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------

_SURFACE_KIND_HEALTH_ENDPOINTS: dict[str, list[str]] = {
    "customer_web": ["/healthz", "/api/health", "/"],
    "customer_pwa": ["/healthz", "/api/health"],
    "public_web": ["/healthz", "/"],
    "admin_portal": ["/healthz", "/api/health", "/admin"],
    "operator_portal": ["/healthz", "/api/health"],
    "api_gateway": ["/healthz", "/api/health", "/api/status"],
    "worker": ["/healthz"],
    "database": ["/healthz"],
}

_SURFACE_KIND_SMOKE_FLOWS: dict[str, list[dict[str, str]]] = {
    "customer_web": [
        {"action": "navigate", "target": "/", "expected": "status=200"},
        {"action": "navigate", "target": "/healthz", "expected": "status=200"},
    ],
    "customer_pwa": [
        {"action": "navigate", "target": "/", "expected": "status=200"},
        {"action": "navigate", "target": "/healthz", "expected": "status=200"},
    ],
    "public_web": [
        {"action": "navigate", "target": "/", "expected": "status=200"},
    ],
    "admin_portal": [
        {"action": "navigate", "target": "/healthz", "expected": "status=200"},
        {"action": "navigate", "target": "/admin", "expected": "status=200 or 302"},
    ],
    "operator_portal": [
        {"action": "navigate", "target": "/healthz", "expected": "status=200"},
        {"action": "navigate", "target": "/", "expected": "status=200"},
    ],
    "api_gateway": [
        {"action": "GET", "target": "/healthz", "expected": "status=200"},
        {"action": "GET", "target": "/api/health", "expected": "status=200"},
    ],
    "worker": [
        {"action": "GET", "target": "/healthz", "expected": "status=200"},
    ],
    "database": [
        {"action": "GET", "target": "/healthz", "expected": "status=200"},
    ],
}


def _surface_kind_from(surface: Any) -> str:
    if isinstance(surface, Mapping):
        return str(surface.get("surface_kind", "customer_web"))
    return str(getattr(surface, "surface_kind", "customer_web"))


def _surface_slug_from(surface: Any) -> str:
    if isinstance(surface, Mapping):
        return str(surface.get("slug", "surface"))
    return str(getattr(surface, "slug", "surface"))


def synthesize_ecosystem_verification(
    ecosystem_id: str,
    surfaces: Sequence[Any],
    version: str = "1.0.0",
) -> EcosystemVerificationContract:
    """Derive a deterministic EcosystemVerificationContract from ecosystem surfaces.

    Each surface produces:
    - One or more HealthCheckProbe entries covering the surface's endpoints.
    - One SmokeTestSpec with surface-kind-derived critical user steps.
    Cross-surface canary rules cover all surfaces that share entity read/write access.
    Fully offline — no I/O, no randomness. Output is deterministic for the same inputs.
    """
    probes: list[HealthCheckProbe] = []
    smoke_tests: list[SmokeTestSpec] = []
    surface_slugs: list[str] = []

    for surface in surfaces:
        slug = _surface_slug_from(surface)
        kind = _surface_kind_from(surface)
        surface_slugs.append(slug)

        # Health check probes — one per relevant endpoint
        endpoints = _SURFACE_KIND_HEALTH_ENDPOINTS.get(kind, ["/healthz"])
        for i, ep in enumerate(endpoints):
            probe_id = f"{slug}-health-{i}"
            method = "GET"
            expected = 200
            timeout = 5
            tags: tuple[str, ...] = ("health",)
            if kind in ("database",):
                tags = ("health", "infrastructure")
                timeout = 10
            elif kind in ("api_gateway", "worker"):
                tags = ("health", "backend")
            else:
                tags = ("health", "frontend")
            probes.append(
                HealthCheckProbe(
                    probe_id=probe_id,
                    surface_slug=slug,
                    surface_kind=kind,
                    method=method,
                    endpoint=ep,
                    expected_status=expected,
                    timeout_seconds=timeout,
                    tags=tags,
                )
            )

        # Smoke test for this surface
        flow_templates = _SURFACE_KIND_SMOKE_FLOWS.get(kind, [
            {"action": "GET", "target": "/healthz", "expected": "status=200"}
        ])
        steps = tuple(
            SmokeTestStep(
                step_id=f"step-{j}",
                description=f"{tmpl['action']} {tmpl['target']}",
                action=tmpl["action"],
                target=tmpl["target"],
                expected=tmpl["expected"],
            )
            for j, tmpl in enumerate(flow_templates)
        )
        category = (
            "api" if kind in ("api_gateway", "worker") else
            "infrastructure" if kind in ("database",) else
            "functional"
        )
        smoke_tests.append(
            SmokeTestSpec(
                test_id=f"{slug}-smoke",
                surface_slug=slug,
                name=f"{kind.replace('_', ' ').title()} Smoke Test",
                category=category,
                steps=steps,
                expected_outcome="success",
            )
        )

    # Canary rules — cross-surface consistency assertions
    canary_rules: list[CanaryVerificationRule] = []
    all_slugs = tuple(surface_slugs)

    if len(all_slugs) >= 2:
        canary_rules.append(
            CanaryVerificationRule(
                rule_id=f"{ecosystem_id}-canary-health-all",
                surfaces_covered=all_slugs,
                trigger="all_surfaces_healthy",
                assertion="All ecosystem surfaces respond to health check probes within timeout",
                severity="error",
            )
        )

    if len(all_slugs) >= 2:
        canary_rules.append(
            CanaryVerificationRule(
                rule_id=f"{ecosystem_id}-canary-cross-auth",
                surfaces_covered=all_slugs,
                trigger="cross_surface_auth_verified",
                assertion="Cross-surface JWT tokens are valid and accepted by all surfaces",
                severity="error",
            )
        )

    api_surfaces = [s for s in surface_slugs if "api" in s or "gateway" in s]
    web_surfaces = [s for s in surface_slugs if "web" in s or "portal" in s or "pwa" in s]
    if api_surfaces and web_surfaces:
        canary_rules.append(
            CanaryVerificationRule(
                rule_id=f"{ecosystem_id}-canary-api-web-latency",
                surfaces_covered=tuple(api_surfaces + web_surfaces),
                trigger="api_response_time_check",
                assertion="API surface p95 latency < 500ms for web surface primary flows",
                severity="warning",
            )
        )

    if len(all_slugs) >= 2:
        canary_rules.append(
            CanaryVerificationRule(
                rule_id=f"{ecosystem_id}-canary-data-consistency",
                surfaces_covered=all_slugs,
                trigger="shared_entity_consistency",
                assertion="Shared entity state is consistent across all surfaces within 1 sync cycle",
                severity="warning",
            )
        )

    canary_rules.append(
        CanaryVerificationRule(
            rule_id=f"{ecosystem_id}-canary-smoke-suite",
            surfaces_covered=all_slugs,
            trigger="smoke_suite_pass",
            assertion="All surface smoke tests pass with no critical failures",
            severity="error",
        )
    )

    return EcosystemVerificationContract(
        ecosystem_id=ecosystem_id,
        version=version,
        probes=tuple(probes),
        smoke_tests=tuple(smoke_tests),
        canary_rules=tuple(canary_rules),
    )


# ---------------------------------------------------------------------------
# Verification engine
# ---------------------------------------------------------------------------


@dataclass
class ProbeResult:
    """Result of simulating one health check probe."""

    probe_id: str
    surface_slug: str
    status: str  # "pass" | "fail" | "skipped"
    simulated_status_code: int
    latency_ms: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "surface_slug": self.surface_slug,
            "status": self.status,
            "simulated_status_code": self.simulated_status_code,
            "latency_ms": self.latency_ms,
            "message": self.message,
        }


@dataclass
class SmokeTestResult:
    """Result of simulating one smoke test spec."""

    test_id: str
    surface_slug: str
    name: str
    status: str  # "pass" | "fail"
    executed_steps: int
    failed_step: str | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "surface_slug": self.surface_slug,
            "name": self.name,
            "status": self.status,
            "executed_steps": self.executed_steps,
            "failed_step": self.failed_step,
            "message": self.message,
        }


@dataclass
class CanaryRuleResult:
    """Result of evaluating one canary verification rule."""

    rule_id: str
    status: str  # "pass" | "fail" | "warning"
    severity: str
    assertion: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "status": self.status,
            "severity": self.severity,
            "assertion": self.assertion,
            "message": self.message,
        }


class EcosystemVerificationEngine:
    """Thread-safe, in-process, fully deterministic verification engine.

    Simulates probe health evaluation and smoke test execution without any
    actual network calls or process spawning. All state is immutable after
    construction; results are re-computed on each simulate call.
    """

    def __init__(self, contract: EcosystemVerificationContract) -> None:
        self._contract = contract
        self._lock = threading.Lock()

    @property
    def contract(self) -> EcosystemVerificationContract:
        return self._contract

    def simulate_probe_evaluation(self) -> list[ProbeResult]:
        """Deterministically simulate all health check probes.

        In dry-run mode every probe is assumed to succeed within a bounded
        simulated latency based on the probe's timeout budget.
        """
        with self._lock:
            results: list[ProbeResult] = []
            for probe in self._contract.probes:
                # Simulate latency as 10% of timeout (deterministic, no randomness)
                latency = max(1, probe.timeout_seconds * 100)
                results.append(
                    ProbeResult(
                        probe_id=probe.probe_id,
                        surface_slug=probe.surface_slug,
                        status="pass",
                        simulated_status_code=probe.expected_status,
                        latency_ms=latency,
                        message=f"[DRY-RUN] {probe.method} {probe.endpoint} -> {probe.expected_status} OK",
                    )
                )
            return results

    def simulate_smoke_tests(self) -> list[SmokeTestResult]:
        """Deterministically simulate all smoke test specs."""
        with self._lock:
            results: list[SmokeTestResult] = []
            for spec in self._contract.smoke_tests:
                results.append(
                    SmokeTestResult(
                        test_id=spec.test_id,
                        surface_slug=spec.surface_slug,
                        name=spec.name,
                        status="pass",
                        executed_steps=len(spec.steps),
                        failed_step=None,
                        message=f"[DRY-RUN] All {len(spec.steps)} smoke test steps passed",
                    )
                )
            return results

    def simulate_canary_rules(self) -> list[CanaryRuleResult]:
        """Deterministically evaluate all canary verification rules."""
        with self._lock:
            results: list[CanaryRuleResult] = []
            for rule in self._contract.canary_rules:
                results.append(
                    CanaryRuleResult(
                        rule_id=rule.rule_id,
                        status="pass",
                        severity=rule.severity,
                        assertion=rule.assertion,
                        message=f"[DRY-RUN] Canary rule '{rule.rule_id}' assertion satisfied",
                    )
                )
            return results

    def simulate_full_verification(self) -> dict[str, Any]:
        """Run a complete dry-run simulation of all probes, smoke tests, and canary rules."""
        probe_results = self.simulate_probe_evaluation()
        smoke_results = self.simulate_smoke_tests()
        canary_results = self.simulate_canary_rules()

        probe_pass = sum(1 for r in probe_results if r.status == "pass")
        probe_fail = sum(1 for r in probe_results if r.status == "fail")
        smoke_pass = sum(1 for r in smoke_results if r.status == "pass")
        smoke_fail = sum(1 for r in smoke_results if r.status == "fail")
        canary_pass = sum(1 for r in canary_results if r.status == "pass")
        canary_fail = sum(1 for r in canary_results if r.status == "fail")

        overall_status = "pass" if (probe_fail == 0 and smoke_fail == 0 and canary_fail == 0) else "fail"

        return {
            "status": overall_status,
            "ecosystem_id": self._contract.ecosystem_id,
            "version": self._contract.version,
            "probe_results": [r.to_dict() for r in probe_results],
            "smoke_test_results": [r.to_dict() for r in smoke_results],
            "canary_rule_results": [r.to_dict() for r in canary_results],
            "summary": {
                "probe_pass": probe_pass,
                "probe_fail": probe_fail,
                "smoke_pass": smoke_pass,
                "smoke_fail": smoke_fail,
                "canary_pass": canary_pass,
                "canary_fail": canary_fail,
                "total_probes": len(probe_results),
                "total_smoke_tests": len(smoke_results),
                "total_canary_rules": len(canary_results),
            },
        }

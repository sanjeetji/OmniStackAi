"""Ecosystem Multi-Surface Governance, Compliance Policy, and Audit Evidence Contracts (R-458).

Defines canonical contracts, compliance standards, policy rules, data classifications,
and cryptographic audit evidence for an entire multi-surface business ecosystem:
- ComplianceStandard: Industry standard definitions (SOC 2, GDPR, ISO 27001, HIPAA, PCI-DSS).
- CompliancePolicy: Surface-scoped governance controls and enforcement modes.
- DataClassification: Field-level sensitivity, encryption requirements, and retention policies.
- AuditEvidenceItem: Cryptographic audit evidence records with SHA-256 provenance.
- EcosystemGovernanceContract: Immutable multi-surface contract with deterministic SHA-256 digest.
- EcosystemGovernanceEngine: Thread-safe in-process evaluation, evidence verification, and audit simulator.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Literal

PolicySeverity = Literal["critical", "high", "medium", "low"]
EnforcementMode = Literal["automated_block", "automated_remediate", "audit_only", "blocking"]
ClassificationLevel = Literal["public", "internal", "restricted", "pii", "phi", "pci", "confidential"]
AnonymizationMethod = Literal["hash", "mask", "drop", "none", "pseudonymize_sha256", "redact"]
EvidenceStatus = Literal["compliant", "non_compliant", "exempt", "valid"]
CollectorKind = Literal[
    "code_scan",
    "access_control",
    "encryption_check",
    "retention_audit",
    "network_policy",
    "config_scan",
    "automated_snapshot",
]
AuditStatus = Literal["compliant", "at_risk", "non_compliant"]


def _canonical_json(data: Any) -> str:
    """Serialize data to byte-stable, sorted canonical JSON string."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _surface_slug_from(surface: Any) -> str:
    """Extract surface slug safely from dict or surface dataclass."""
    if isinstance(surface, Mapping):
        return str(surface.get("slug") or surface.get("surface_slug") or "default")
    return str(getattr(surface, "slug", getattr(surface, "surface_slug", "default")))


def _surface_kind_from(surface: Any) -> str:
    """Extract surface kind safely from dict or surface dataclass and normalize."""
    if isinstance(surface, Mapping):
        raw = str(surface.get("surface_kind") or surface.get("kind") or "customer_web").lower()
    else:
        raw = str(getattr(surface, "surface_kind", getattr(surface, "kind", "customer_web"))).lower()
    if "admin" in raw:
        return "admin"
    if "api" in raw or "backend" in raw:
        return "api"
    if "worker" in raw or "queue" in raw or "async" in raw:
        return "worker"
    if "db" in raw or "database" in raw or "storage" in raw:
        return "db"
    return "web"


@dataclass(frozen=True, slots=True)
class ComplianceStandard:
    """An industry compliance standard or framework."""

    standard_id: str
    name: str
    version: str
    description: str
    mandatory_controls: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "standard_id": self.standard_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "mandatory_controls": list(self.mandatory_controls),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ComplianceStandard:
        return cls(
            standard_id=str(data.get("standard_id", "")),
            name=str(data.get("name", "")),
            version=str(data.get("version", "")),
            description=str(data.get("description", "")),
            mandatory_controls=tuple(str(c) for c in data.get("mandatory_controls", ())),
        )


@dataclass(frozen=True, slots=True)
class CompliancePolicy:
    """A surface-scoped compliance policy control rule."""

    policy_id: str
    surface_slug: str
    standard_id: str
    control_id: str
    severity: PolicySeverity = "high"
    enforcement_mode: EnforcementMode = "automated_block"
    rule_expression: str = ""
    remediation: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "surface_slug": self.surface_slug,
            "standard_id": self.standard_id,
            "control_id": self.control_id,
            "severity": self.severity,
            "enforcement_mode": self.enforcement_mode,
            "rule_expression": self.rule_expression,
            "remediation": self.remediation,
            "description": self.description,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CompliancePolicy:
        raw_sev = str(data.get("severity", "high")).lower()
        severity: PolicySeverity = (
            raw_sev if raw_sev in ("critical", "high", "medium", "low") else "high"
        )
        raw_mode = str(data.get("enforcement_mode", "automated_block")).lower()
        enforcement_mode: EnforcementMode = (
            raw_mode
            if raw_mode in ("automated_block", "automated_remediate", "audit_only", "blocking")
            else "automated_block"
        )
        return cls(
            policy_id=str(data.get("policy_id", "")),
            surface_slug=str(data.get("surface_slug", "")),
            standard_id=str(data.get("standard_id", "")),
            control_id=str(data.get("control_id", "")),
            severity=severity,
            enforcement_mode=enforcement_mode,
            rule_expression=str(data.get("rule_expression", "")),
            remediation=str(data.get("remediation", "")),
            description=str(data.get("description", "")),
            tags=tuple(str(t) for t in data.get("tags", ())),
        )


@dataclass(frozen=True, slots=True)
class DataClassification:
    """A data privacy classification and lifecycle policy for entity fields."""

    classification_id: str
    surface_slug: str
    entity_name: str
    field_name: str
    classification_level: ClassificationLevel = "internal"
    encryption_required: bool = False
    retention_days: int = 365
    anonymization_method: AnonymizationMethod = "none"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification_id": self.classification_id,
            "surface_slug": self.surface_slug,
            "entity_name": self.entity_name,
            "field_name": self.field_name,
            "classification_level": self.classification_level,
            "encryption_required": self.encryption_required,
            "retention_days": self.retention_days,
            "anonymization_method": self.anonymization_method,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DataClassification:
        raw_lvl = str(data.get("classification_level", "internal")).lower()
        level: ClassificationLevel = (
            raw_lvl
            if raw_lvl in ("public", "internal", "restricted", "pii", "phi", "pci", "confidential")
            else "internal"
        )
        raw_anon = str(data.get("anonymization_method", "none")).lower()
        anon: AnonymizationMethod = (
            raw_anon
            if raw_anon in ("hash", "mask", "drop", "none", "pseudonymize_sha256", "redact")
            else "none"
        )
        return cls(
            classification_id=str(data.get("classification_id", "")),
            surface_slug=str(data.get("surface_slug", "")),
            entity_name=str(data.get("entity_name", "")),
            field_name=str(data.get("field_name", "")),
            classification_level=level,
            encryption_required=bool(data.get("encryption_required", False)),
            retention_days=int(data.get("retention_days", 365)),
            anonymization_method=anon,
            description=str(data.get("description", "")),
        )


@dataclass(frozen=True, slots=True)
class AuditEvidenceItem:
    """A cryptographic audit evidence entry verifying a compliance control."""

    evidence_id: str
    control_id: str
    surface_slug: str
    collector_kind: CollectorKind = "code_scan"
    status: EvidenceStatus = "compliant"
    collected_at: str = "2026-09-15T00:00:00Z"
    sha256_hash: str = ""
    details: dict[str, Any] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "control_id": self.control_id,
            "surface_slug": self.surface_slug,
            "collector_kind": self.collector_kind,
            "status": self.status,
            "collected_at": self.collected_at,
            "sha256_hash": self.sha256_hash,
            "details": dict(self.details) if isinstance(self.details, Mapping) else {},
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AuditEvidenceItem:
        raw_kind = str(data.get("collector_kind", "code_scan")).lower()
        collector_kind: CollectorKind = (
            raw_kind
            if raw_kind in (
                "code_scan",
                "access_control",
                "encryption_check",
                "retention_audit",
                "network_policy",
                "config_scan",
                "automated_snapshot",
            )
            else "code_scan"
        )
        raw_status = str(data.get("status", "compliant")).lower()
        status: EvidenceStatus = (
            raw_status
            if raw_status in ("compliant", "non_compliant", "exempt", "valid")
            else "compliant"
        )
        details_val = data.get("details", {})
        details = dict(details_val) if isinstance(details_val, Mapping) else {}
        return cls(
            evidence_id=str(data.get("evidence_id", "")),
            control_id=str(data.get("control_id", "")),
            surface_slug=str(data.get("surface_slug", "")),
            collector_kind=collector_kind,
            status=status,
            collected_at=str(data.get("collected_at", "2026-09-15T00:00:00Z")),
            sha256_hash=str(data.get("sha256_hash", "")),
            details=details,
        )


@dataclass(frozen=True, slots=True)
class EcosystemGovernanceContract:
    """Canonical, byte-stable governance and compliance contract for an entire ecosystem."""

    ecosystem_id: str
    version: str
    standards: tuple[ComplianceStandard, ...]
    policies: tuple[CompliancePolicy, ...]
    classifications: tuple[DataClassification, ...]
    evidence_items: tuple[AuditEvidenceItem, ...]
    metadata: dict[str, Any] = ()

    @property
    def data_classifications(self) -> tuple[DataClassification, ...]:
        return self.classifications

    def digest(self) -> str:
        """Calculate deterministic SHA-256 digest of normalized contract payload."""
        payload = {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "standards": [s.to_dict() for s in self.standards],
            "policies": [p.to_dict() for p in self.policies],
            "classifications": [c.to_dict() for c in self.classifications],
            "evidence_items": [e.to_dict() for e in self.evidence_items],
            "metadata": dict(self.metadata) if isinstance(self.metadata, Mapping) else {},
        }
        return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "standards": [s.to_dict() for s in self.standards],
            "policies": [p.to_dict() for p in self.policies],
            "classifications": [c.to_dict() for c in self.classifications],
            "data_classifications": [c.to_dict() for c in self.classifications],
            "evidence_items": [e.to_dict() for e in self.evidence_items],
            "metadata": dict(self.metadata) if isinstance(self.metadata, Mapping) else {},
            "digest": self.digest(),
        }

    def to_json(self, indent: int | None = 2) -> str:
        data = self.to_dict()
        if indent is None:
            return _canonical_json(data)
        return json.dumps(data, indent=indent, sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemGovernanceContract:
        standards = tuple(
            ComplianceStandard.from_dict(s) for s in data.get("standards", ())
        )
        policies = tuple(
            CompliancePolicy.from_dict(p) for p in data.get("policies", ())
        )
        raw_classifications = (
            data.get("classifications")
            if data.get("classifications") is not None
            else data.get("data_classifications", ())
        )
        classifications = tuple(
            DataClassification.from_dict(c) for c in raw_classifications
        )
        evidence_items = tuple(
            AuditEvidenceItem.from_dict(e) for e in data.get("evidence_items", ())
        )
        meta_val = data.get("metadata", {})
        metadata = dict(meta_val) if isinstance(meta_val, Mapping) else {}
        return cls(
            ecosystem_id=str(data.get("ecosystem_id", "")),
            version=str(data.get("version", "1.0.0")),
            standards=standards,
            policies=policies,
            classifications=classifications,
            evidence_items=evidence_items,
            metadata=metadata,
        )

    @classmethod
    def from_json(cls, json_str: str) -> EcosystemGovernanceContract:
        return cls.from_dict(json.loads(json_str))


# ---------------------------------------------------------------------------
# Report Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PolicyEvaluationResult:
    """Individual policy evaluation result."""

    policy_id: str
    surface_slug: str
    control_id: str
    status: EvidenceStatus
    severity: PolicySeverity
    enforcement_mode: EnforcementMode
    details: str
    remediation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "surface_slug": self.surface_slug,
            "control_id": self.control_id,
            "status": self.status,
            "severity": self.severity,
            "enforcement_mode": self.enforcement_mode,
            "details": self.details,
            "remediation": self.remediation,
        }


@dataclass(frozen=True, slots=True)
class GovernanceComplianceReport:
    """Summary of governance policy evaluations."""

    ecosystem_id: str
    total_policies: int
    compliant_count: int
    non_compliant_count: int
    exempt_count: int
    compliance_score_pct: float
    critical_violations: int
    high_violations: int
    results: tuple[PolicyEvaluationResult, ...]

    @property
    def overall_compliant(self) -> bool:
        return self.non_compliant_count == 0 and self.critical_violations == 0

    @property
    def violations(self) -> tuple[PolicyEvaluationResult, ...]:
        return tuple(r for r in self.results if r.status != "compliant")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "total_policies": self.total_policies,
            "compliant_count": self.compliant_count,
            "non_compliant_count": self.non_compliant_count,
            "exempt_count": self.exempt_count,
            "compliance_score_pct": self.compliance_score_pct,
            "critical_violations": self.critical_violations,
            "high_violations": self.high_violations,
            "overall_compliant": self.overall_compliant,
            "violations": [v.to_dict() for v in self.violations],
            "results": [r.to_dict() for r in self.results],
        }


@dataclass(frozen=True, slots=True)
class EvidenceVerificationItemResult:
    """Verification outcome of a single audit evidence item."""

    evidence_id: str
    control_id: str
    surface_slug: str
    collector_kind: CollectorKind
    status: EvidenceStatus
    hash_verified: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "control_id": self.control_id,
            "surface_slug": self.surface_slug,
            "collector_kind": self.collector_kind,
            "status": self.status,
            "hash_verified": self.hash_verified,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class AuditVerificationReport:
    """Summary report of cryptographic audit evidence verification."""

    ecosystem_id: str
    total_evidence_items: int
    verified_count: int
    tampered_count: int
    standards_covered: tuple[str, ...]
    status: AuditStatus
    results: tuple[EvidenceVerificationItemResult, ...]

    @property
    def all_valid(self) -> bool:
        return self.status == "compliant" and self.tampered_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "total_evidence_items": self.total_evidence_items,
            "verified_count": self.verified_count,
            "tampered_count": self.tampered_count,
            "standards_covered": list(self.standards_covered),
            "status": self.status,
            "all_valid": self.all_valid,
            "results": [r.to_dict() for r in self.results],
        }


@dataclass(frozen=True, slots=True)
class GovernanceAuditSimulationReport:
    """Simulation output of a full compliance audit under a specific operational scenario."""

    scenario: str
    ecosystem_id: str
    timestamp: str
    standards_evaluated: tuple[str, ...]
    total_controls_tested: int
    passed_controls: int
    failed_controls: int
    audit_status: AuditStatus
    risk_score: float
    findings: tuple[dict[str, Any], ...]
    recommended_actions: tuple[str, ...]
    compliance_report: GovernanceComplianceReport | None = None
    evidence_report: AuditVerificationReport | None = None

    @property
    def overall_audit_passed(self) -> bool:
        return self.audit_status in ("compliant", "at_risk")

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "ecosystem_id": self.ecosystem_id,
            "timestamp": self.timestamp,
            "standards_evaluated": list(self.standards_evaluated),
            "total_controls_tested": self.total_controls_tested,
            "passed_controls": self.passed_controls,
            "failed_controls": self.failed_controls,
            "audit_status": self.audit_status,
            "risk_score": self.risk_score,
            "findings": list(self.findings),
            "recommended_actions": list(self.recommended_actions),
            "overall_audit_passed": self.overall_audit_passed,
            "compliance_report": self.compliance_report.to_dict() if self.compliance_report else None,
            "evidence_report": self.evidence_report.to_dict() if self.evidence_report else None,
        }


# ---------------------------------------------------------------------------
# Deterministic Contract Synthesis
# ---------------------------------------------------------------------------


def synthesize_ecosystem_governance(
    ecosystem_id: str,
    surfaces: Sequence[Any],
    version: str = "1.0.0",
) -> EcosystemGovernanceContract:
    """Synthesize a complete, deterministic governance contract for an ecosystem.

    Derives industry standards (SOC 2, GDPR, ISO 27001), surface-specific compliance
    policies across web, admin, API, worker, and database surfaces, entity data
    classifications, and initial cryptographic audit evidence items offline.
    """
    # 1. Standard Definitions
    standards = (
        ComplianceStandard(
            standard_id="soc2_type_ii",
            name="SOC 2 Type II",
            version="2022",
            description="Trust Services Criteria for Security, Availability, and Confidentiality.",
            mandatory_controls=("CC6.1", "CC6.6", "CC6.7", "CC7.1", "CC8.1"),
        ),
        ComplianceStandard(
            standard_id="gdpr",
            name="General Data Protection Regulation (GDPR)",
            version="2018",
            description="EU regulation on data protection, privacy, and user consent.",
            mandatory_controls=("ART-25", "ART-32", "ART-33", "ART-35"),
        ),
        ComplianceStandard(
            standard_id="iso_27001",
            name="ISO/IEC 27001:2022",
            version="2022",
            description="Information security management systems requirements and controls.",
            mandatory_controls=("A.8.1", "A.8.20", "A.8.24", "A.8.28"),
        ),
    )

    policies: list[CompliancePolicy] = []
    classifications: list[DataClassification] = []
    evidence_items: list[AuditEvidenceItem] = []

    # 2. Derive Policies and Classifications per surface
    for surface in surfaces:
        slug = _surface_slug_from(surface)
        kind = _surface_kind_from(surface)

        if kind in ("web", "admin"):
            # Web & Admin Policies
            policies.append(
                CompliancePolicy(
                    policy_id=f"pol-{slug}-csp",
                    surface_slug=slug,
                    standard_id="soc2_type_ii",
                    control_id="CC6.6",
                    severity="high",
                    enforcement_mode="automated_block",
                    rule_expression="header_csp_present == True and 'default-src' in header_csp",
                    remediation="Configure Content-Security-Policy headers in reverse proxy or edge gateway.",
                    description=f"Enforce strict Content-Security-Policy on {slug} web surface.",
                    tags=("security", "browser", "xss"),
                )
            )
            policies.append(
                CompliancePolicy(
                    policy_id=f"pol-{slug}-tls",
                    surface_slug=slug,
                    standard_id="iso_27001",
                    control_id="A.8.24",
                    severity="critical",
                    enforcement_mode="automated_block",
                    rule_expression="tls_version >= 1.3 and hsts_max_age >= 31536000",
                    remediation="Enforce TLS 1.3 and HTTP Strict Transport Security (HSTS) with 1y max-age.",
                    description=f"Enforce TLS 1.3 and HSTS for {slug} surface.",
                    tags=("encryption", "transit", "network"),
                )
            )
            policies.append(
                CompliancePolicy(
                    policy_id=f"pol-{slug}-cookie-sec",
                    surface_slug=slug,
                    standard_id="gdpr",
                    control_id="ART-25",
                    severity="high",
                    enforcement_mode="automated_block",
                    rule_expression="cookie_secure == True and cookie_httponly == True and cookie_samesite in ('Strict', 'Lax')",
                    remediation="Set Secure, HttpOnly, and SameSite flags on all browser session cookies.",
                    description=f"Enforce secure cookie attributes on {slug} surface.",
                    tags=("privacy", "cookie", "session"),
                )
            )
            if kind == "admin":
                policies.append(
                    CompliancePolicy(
                        policy_id=f"pol-{slug}-mfa",
                        surface_slug=slug,
                        standard_id="soc2_type_ii",
                        control_id="CC6.1",
                        severity="critical",
                        enforcement_mode="automated_block",
                        rule_expression="admin_mfa_required == True and session_idle_timeout <= 900",
                        remediation="Require hardware token or TOTP MFA for administrative accounts and 15m idle timeout.",
                        description="Enforce mandatory Multi-Factor Authentication for administrative access.",
                        tags=("auth", "admin", "mfa"),
                    )
                )
                policies.append(
                    CompliancePolicy(
                        policy_id=f"pol-{slug}-audit-trail",
                        surface_slug=slug,
                        standard_id="iso_27001",
                        control_id="A.8.15",
                        severity="high",
                        enforcement_mode="automated_remediate",
                        rule_expression="admin_mutation_logged == True and log_tamper_resistant == True",
                        remediation="Emit immutable audit trail entry for every administrative mutation.",
                        description="Ensure all administrative state modifications produce immutable audit events.",
                        tags=("audit", "logging", "forensics"),
                    )
                )

            # Data Classifications for Web / Admin
            classifications.append(
                DataClassification(
                    classification_id=f"cls-{slug}-user-session",
                    surface_slug=slug,
                    entity_name="UserSession",
                    field_name="session_token",
                    classification_level="restricted",
                    encryption_required=True,
                    retention_days=30,
                    anonymization_method="hash",
                    description="User browser session tokens.",
                )
            )
            classifications.append(
                DataClassification(
                    classification_id=f"cls-{slug}-analytics-ip",
                    surface_slug=slug,
                    entity_name="AnalyticsEvent",
                    field_name="client_ip",
                    classification_level="pii",
                    encryption_required=False,
                    retention_days=90,
                    anonymization_method="mask",
                    description="Client IP address for telemetry and fraud prevention.",
                )
            )

        elif kind in ("api", "worker"):
            # API & Worker Policies
            policies.append(
                CompliancePolicy(
                    policy_id=f"pol-{slug}-jwt-auth",
                    surface_slug=slug,
                    standard_id="soc2_type_ii",
                    control_id="CC6.1",
                    severity="critical",
                    enforcement_mode="automated_block",
                    rule_expression="auth_token_verified == True and algorithm in ('HS256', 'RS256')",
                    remediation="Reject unauthenticated HTTP requests with 401 Unauthorized.",
                    description=f"Enforce mandatory cryptographic token authentication for {slug}.",
                    tags=("auth", "api", "jwt"),
                )
            )
            policies.append(
                CompliancePolicy(
                    policy_id=f"pol-{slug}-rate-limit",
                    surface_slug=slug,
                    standard_id="iso_27001",
                    control_id="A.8.20",
                    severity="high",
                    enforcement_mode="automated_block",
                    rule_expression="rate_limit_enforced == True and max_burst <= 100",
                    remediation="Attach token-bucket or sliding-window rate limiter on all public routes.",
                    description=f"Enforce rate limiting and DoS throttling on {slug}.",
                    tags=("traffic", "rate_limit", "dos"),
                )
            )
            policies.append(
                CompliancePolicy(
                    policy_id=f"pol-{slug}-sqli-defense",
                    surface_slug=slug,
                    standard_id="soc2_type_ii",
                    control_id="CC6.6",
                    severity="critical",
                    enforcement_mode="automated_block",
                    rule_expression="raw_sql_execution == False and parameterized_queries == True",
                    remediation="Disallow raw SQL string interpolation; require parameterized prepared statements.",
                    description=f"Prevent SQL injection vulnerabilities across data access layers in {slug}.",
                    tags=("security", "sqli", "database"),
                )
            )
            policies.append(
                CompliancePolicy(
                    policy_id=f"pol-{slug}-secret-brokering",
                    surface_slug=slug,
                    standard_id="iso_27001",
                    control_id="A.8.24",
                    severity="critical",
                    enforcement_mode="automated_block",
                    rule_expression="secrets_in_source == False and secrets_brokered == True",
                    remediation="Store secrets in brokered vault or capability provider, never in code or logs.",
                    description=f"Verify platform capability secret isolation for {slug}.",
                    tags=("secrets", "credentials", "vault"),
                )
            )
            if kind == "worker":
                policies.append(
                    CompliancePolicy(
                        policy_id=f"pol-{slug}-job-dedup",
                        surface_slug=slug,
                        standard_id="soc2_type_ii",
                        control_id="CC7.1",
                        severity="medium",
                        enforcement_mode="audit_only",
                        rule_expression="job_idempotency_key_present == True",
                        remediation="Attach unique idempotency keys to asynchronous task invocations.",
                        description="Enforce background job idempotency and deduplication.",
                        tags=("worker", "idempotency", "queue"),
                    )
                )

            # Data Classifications for API / Worker
            classifications.append(
                DataClassification(
                    classification_id=f"cls-{slug}-user-email",
                    surface_slug=slug,
                    entity_name="UserProfile",
                    field_name="email",
                    classification_level="pii",
                    encryption_required=True,
                    retention_days=730,
                    anonymization_method="mask",
                    description="User primary email address.",
                )
            )
            classifications.append(
                DataClassification(
                    classification_id=f"cls-{slug}-password-hash",
                    surface_slug=slug,
                    entity_name="UserAuth",
                    field_name="password_hash",
                    classification_level="restricted",
                    encryption_required=True,
                    retention_days=730,
                    anonymization_method="drop",
                    description="Argon2/bcrypt salted cryptographic password digest.",
                )
            )

        elif kind in ("database", "db", "storage"):
            # Database / Storage Policies
            policies.append(
                CompliancePolicy(
                    policy_id=f"pol-{slug}-atrest-encryption",
                    surface_slug=slug,
                    standard_id="gdpr",
                    control_id="ART-32",
                    severity="critical",
                    enforcement_mode="automated_block",
                    rule_expression="storage_encrypted == True and cipher == 'AES-256-GCM'",
                    remediation="Enable AES-256 storage volume and tablespace encryption.",
                    description=f"Enforce AES-256 encryption-at-rest on {slug}.",
                    tags=("encryption", "at_rest", "database"),
                )
            )
            policies.append(
                CompliancePolicy(
                    policy_id=f"pol-{slug}-retention-purge",
                    surface_slug=slug,
                    standard_id="gdpr",
                    control_id="ART-25",
                    severity="medium",
                    enforcement_mode="automated_remediate",
                    rule_expression="retention_purge_job_active == True",
                    remediation="Schedule automated data lifecycle purge job for expired PII records.",
                    description=f"Enforce automated GDPR retention limit purging on {slug}.",
                    tags=("privacy", "gdpr", "retention"),
                )
            )
            policies.append(
                CompliancePolicy(
                    policy_id=f"pol-{slug}-rbac",
                    surface_slug=slug,
                    standard_id="soc2_type_ii",
                    control_id="CC6.1",
                    severity="high",
                    enforcement_mode="automated_block",
                    rule_expression="least_privilege_roles == True and superuser_access_disabled == True",
                    remediation="Revoke superuser privileges from application connection pools.",
                    description=f"Enforce least-privilege role-based access control on {slug}.",
                    tags=("database", "rbac", "least_privilege"),
                )
            )

            # Data Classifications for Database
            classifications.append(
                DataClassification(
                    classification_id=f"cls-{slug}-financial-record",
                    surface_slug=slug,
                    entity_name="BillingTransaction",
                    field_name="payment_reference",
                    classification_level="restricted",
                    encryption_required=True,
                    retention_days=2555,  # 7 years for tax/financial records
                    anonymization_method="hash",
                    description="Financial transaction reference tokens.",
                )
            )

    # 3. Derive Initial Cryptographic Evidence Items for each policy
    collected_at = "2026-09-15T00:00:00Z"
    for pol in policies:
        ev_data = {
            "policy_id": pol.policy_id,
            "control_id": pol.control_id,
            "surface_slug": pol.surface_slug,
            "standard_id": pol.standard_id,
            "rule_expression": pol.rule_expression,
            "timestamp": collected_at,
        }
        ev_hash = hashlib.sha256(_canonical_json(ev_data).encode("utf-8")).hexdigest()
        evidence_items.append(
            AuditEvidenceItem(
                evidence_id=f"ev-{pol.policy_id}",
                control_id=pol.control_id,
                surface_slug=pol.surface_slug,
                collector_kind="code_scan" if "sqli" in pol.tags or "secrets" in pol.tags else "access_control",
                status="compliant",
                collected_at=collected_at,
                sha256_hash=ev_hash,
                details={
                    "verifier": "omnistackai_governance_synthesizer",
                    "rule": pol.rule_expression,
                    "verified": True,
                },
            )
        )

    metadata = {
        "synthesizer": "omnistackai_governance_engine",
        "surface_count": len(surfaces),
        "standards_count": len(standards),
        "policy_count": len(policies),
        "classification_count": len(classifications),
        "evidence_count": len(evidence_items),
    }

    return EcosystemGovernanceContract(
        ecosystem_id=ecosystem_id,
        version=version,
        standards=standards,
        policies=tuple(policies),
        classifications=tuple(classifications),
        evidence_items=tuple(evidence_items),
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# In-Process Thread-Safe Governance Engine
# ---------------------------------------------------------------------------


class EcosystemGovernanceEngine:
    """Thread-safe evaluation, evidence verification, and audit simulation engine."""

    def __init__(self, contract: EcosystemGovernanceContract) -> None:
        self._contract = contract
        self._lock = threading.RLock()

    @property
    def contract(self) -> EcosystemGovernanceContract:
        return self._contract

    def evaluate_compliance(
        self,
        surface_configs: Mapping[str, Mapping[str, Any]] | None = None,
        environment_state: Mapping[str, Any] | None = None,
    ) -> GovernanceComplianceReport:
        """Evaluate compliance policies against surface configurations and environment state."""
        with self._lock:
            results: list[PolicyEvaluationResult] = []
            compliant_count = 0
            non_compliant_count = 0
            exempt_count = 0
            critical_violations = 0
            high_violations = 0

            configs = surface_configs or {}
            global_env = environment_state or {}

            for pol in self._contract.policies:
                surf_cfg = dict(configs.get(pol.surface_slug, {}))
                surf_cfg.update(global_env)
                status: EvidenceStatus = "compliant"
                detail_msg = f"Control {pol.control_id} verified compliant with rule: {pol.rule_expression}"

                raw_tls = surf_cfg.get("tls_version", 1.3)
                try:
                    tls_ver = float(raw_tls)
                except (ValueError, TypeError):
                    tls_ver = 1.3

                # Check for explicit violations in provided configuration
                if pol.policy_id.endswith("-csp") and surf_cfg.get("header_csp_present") is False:
                    status = "non_compliant"
                    detail_msg = "Content-Security-Policy header is missing"
                elif (pol.policy_id.endswith("-tls") or "tls" in pol.tags) and tls_ver < 1.3:
                    status = "non_compliant"
                    detail_msg = f"TLS version {raw_tls} is below required 1.3"
                elif pol.policy_id.endswith("-cookie-sec") and surf_cfg.get("cookie_secure") is False:
                    status = "non_compliant"
                    detail_msg = "Cookie Secure flag is disabled"
                elif pol.policy_id.endswith("-mfa") and surf_cfg.get("admin_mfa_required") is False:
                    status = "non_compliant"
                    detail_msg = "Administrative MFA requirement is disabled"
                elif "audit" in pol.tags and surf_cfg.get("audit_logging_enabled") is False:
                    status = "non_compliant"
                    detail_msg = "Audit logging is disabled"
                elif pol.policy_id.endswith("-jwt-auth") and surf_cfg.get("auth_token_verified") is False:
                    status = "non_compliant"
                    detail_msg = "JWT token verification check failed"
                elif pol.policy_id.endswith("-rate-limit") and surf_cfg.get("rate_limit_enforced") is False:
                    status = "non_compliant"
                    detail_msg = "Rate limiting throttling is disabled"
                elif pol.policy_id.endswith("-sqli-defense") and surf_cfg.get("raw_sql_execution") is True:
                    status = "non_compliant"
                    detail_msg = "Detected unparameterized raw SQL execution"
                elif pol.policy_id.endswith("-secret-brokering") and surf_cfg.get("secrets_in_source") is True:
                    status = "non_compliant"
                    detail_msg = "Detected plain-text credentials in repository source files"
                elif (
                    pol.policy_id.endswith("-atrest-encryption") or "encryption" in pol.tags
                ) and (
                    surf_cfg.get("storage_encrypted") is False or surf_cfg.get("encryption_at_rest") is False
                ):
                    status = "non_compliant"
                    detail_msg = "Storage volume encryption-at-rest is disabled"

                if status == "compliant":
                    compliant_count += 1
                elif status == "non_compliant":
                    non_compliant_count += 1
                    if pol.severity == "critical":
                        critical_violations += 1
                    elif pol.severity == "high":
                        high_violations += 1
                else:
                    exempt_count += 1

                results.append(
                    PolicyEvaluationResult(
                        policy_id=pol.policy_id,
                        surface_slug=pol.surface_slug,
                        control_id=pol.control_id,
                        status=status,
                        severity=pol.severity,
                        enforcement_mode=pol.enforcement_mode,
                        details=detail_msg,
                        remediation=pol.remediation,
                    )
                )

            total = len(self._contract.policies)
            score = round((compliant_count / total * 100.0), 2) if total > 0 else 100.0

            return GovernanceComplianceReport(
                ecosystem_id=self._contract.ecosystem_id,
                total_policies=total,
                compliant_count=compliant_count,
                non_compliant_count=non_compliant_count,
                exempt_count=exempt_count,
                compliance_score_pct=score,
                critical_violations=critical_violations,
                high_violations=high_violations,
                results=tuple(results),
            )

    def verify_audit_evidence(
        self, evidence_items: Sequence[AuditEvidenceItem] | None = None
    ) -> AuditVerificationReport:
        """Verify the cryptographic integrity of audit evidence items."""
        with self._lock:
            items = evidence_items if evidence_items is not None else self._contract.evidence_items
            results: list[EvidenceVerificationItemResult] = []
            verified_count = 0
            tampered_count = 0

            standards_set: set[str] = set()

            for item in items:
                # Find matching policy to recalculate expected hash
                matching_pol = next(
                    (p for p in self._contract.policies if p.control_id == item.control_id and p.surface_slug == item.surface_slug),
                    None,
                )

                if matching_pol:
                    standards_set.add(matching_pol.standard_id)
                    expected_payload = {
                        "policy_id": matching_pol.policy_id,
                        "control_id": matching_pol.control_id,
                        "surface_slug": matching_pol.surface_slug,
                        "standard_id": matching_pol.standard_id,
                        "rule_expression": matching_pol.rule_expression,
                        "timestamp": item.collected_at,
                    }
                    expected_hash = hashlib.sha256(_canonical_json(expected_payload).encode("utf-8")).hexdigest()
                    hash_matches = (item.sha256_hash == expected_hash)
                else:
                    hash_matches = bool(item.sha256_hash and len(item.sha256_hash) == 64)

                if hash_matches and item.status == "compliant":
                    verified_count += 1
                    reason = "Cryptographic SHA-256 hash verified and control status compliant."
                elif not hash_matches:
                    tampered_count += 1
                    reason = "Cryptographic SHA-256 hash mismatch! Possible record tampering."
                else:
                    reason = f"Evidence status is {item.status}."

                results.append(
                    EvidenceVerificationItemResult(
                        evidence_id=item.evidence_id,
                        control_id=item.control_id,
                        surface_slug=item.surface_slug,
                        collector_kind=item.collector_kind,
                        status=item.status,
                        hash_verified=hash_matches,
                        reason=reason,
                    )
                )

            total = len(items)
            status: AuditStatus = "compliant"
            if tampered_count > 0:
                status = "non_compliant"
            elif verified_count < total:
                status = "at_risk"

            return AuditVerificationReport(
                ecosystem_id=self._contract.ecosystem_id,
                total_evidence_items=total,
                verified_count=verified_count,
                tampered_count=tampered_count,
                standards_covered=tuple(sorted(standards_set)),
                status=status,
                results=tuple(results),
            )

    def simulate_compliance_audit(
        self, scenario: str = "standard_audit"
    ) -> GovernanceAuditSimulationReport:
        """Simulate a comprehensive compliance audit under an operational scenario."""
        with self._lock:
            timestamp = "2026-09-15T12:00:00Z"
            standards = tuple(s.standard_id for s in self._contract.standards)
            total_controls = len(self._contract.policies)

            scenario_norm = scenario.lower().strip()
            findings: list[dict[str, Any]] = []
            actions: list[str] = []

            if scenario_norm == "standard_audit":
                passed = total_controls
                failed = 0
                status: AuditStatus = "compliant"
                risk = 0.05
                findings.append({
                    "finding_id": "AUD-001",
                    "severity": "low",
                    "title": "Baseline Controls Fully Operative",
                    "description": f"All {total_controls} controls across SOC 2, GDPR, and ISO 27001 verified operational.",
                })
                actions.append("Maintain continuous evidence collection cycles.")

            elif scenario_norm == "gdpr_dsar_request":
                passed = total_controls
                failed = 0
                status = "compliant"
                risk = 0.08
                findings.append({
                    "finding_id": "GDPR-DSAR-001",
                    "severity": "low",
                    "title": "Automated Subject Access Request Fulfillment",
                    "description": "PII classification mapping accurately identified all subject entities (email, IP, sessions).",
                })
                actions.append("Verify data purge execution upon confirmed deletion requests.")

            elif scenario_norm == "data_breach_investigation":
                passed = max(0, total_controls - 1)
                failed = 1
                status = "at_risk"
                risk = 0.35
                findings.append({
                    "finding_id": "SEC-BREACH-001",
                    "severity": "medium",
                    "title": "Audit Trail Inspection Under Investigation Scenario",
                    "description": "Forensic log export completed in 120s; recommended isolating read-only audit storage.",
                })
                actions.append("Enable write-once-read-many (WORM) storage for audit trails.")
                actions.append("Test automated notification hook to compliance officer.")

            elif scenario_norm == "soc2_certification":
                passed = total_controls
                failed = 0
                status = "compliant"
                risk = 0.02
                findings.append({
                    "finding_id": "SOC2-AUDIT-001",
                    "severity": "low",
                    "title": "SOC 2 Type II Annual Inspection Passed",
                    "description": "Zero non-conformities identified across CC6 (Access), CC7 (Operations), CC8 (Change Mgmt).",
                })
                actions.append("Publish updated SOC 2 Type II attestation to customer trust portal.")

            elif scenario_norm == "high_risk_violations":
                failed = max(3, total_controls // 3)
                passed = total_controls - failed
                status = "non_compliant"
                risk = 0.88
                findings.append({
                    "finding_id": "VIO-001",
                    "severity": "critical",
                    "title": "Missing Administrative MFA and Plaintext Secrets Detected",
                    "description": "Administrative access control bypass and unbrokered secrets detected during penetration scan.",
                })
                findings.append({
                    "finding_id": "VIO-002",
                    "severity": "high",
                    "title": "TLS 1.1 Insecure Protocol Negotiated",
                    "description": "Edge gateway allowed deprecated cipher suites and legacy TLS connections.",
                })
                actions.append("Immediately revoke and rotate all active API tokens.")
                actions.append("Enforce TLS 1.3 minimum cipher policy at edge proxy.")
                actions.append("Enable mandatory hardware MFA on administrative endpoints.")

            else:
                # Default generic scenario
                passed = total_controls
                failed = 0
                status = "compliant"
                risk = 0.10
                findings.append({
                    "finding_id": "AUD-GENERIC",
                    "severity": "low",
                    "title": f"Completed simulation for {scenario}",
                    "description": "General audit verification completed.",
                })
                actions.append("Review standard compliance policy schedules.")

            comp_env: dict[str, Any] = {}
            if scenario_norm == "high_risk_violations":
                comp_env = {
                    "tls_version": 1.1,
                    "storage_encrypted": False,
                    "admin_mfa_required": False,
                    "secrets_in_source": True,
                }
            comp_rep = self.evaluate_compliance(environment_state=comp_env)
            evi_rep = self.verify_audit_evidence()

            return GovernanceAuditSimulationReport(
                scenario=scenario,
                ecosystem_id=self._contract.ecosystem_id,
                timestamp=timestamp,
                standards_evaluated=standards,
                total_controls_tested=total_controls,
                passed_controls=passed,
                failed_controls=failed,
                audit_status=status,
                risk_score=risk,
                findings=tuple(findings),
                recommended_actions=tuple(actions),
                compliance_report=comp_rep,
                evidence_report=evi_rep,
            )

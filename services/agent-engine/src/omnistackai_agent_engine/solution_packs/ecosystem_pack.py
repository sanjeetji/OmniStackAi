"""Solution Pack Multi-Surface Ecosystem Pack Schema, Synthesis, and Verification (R-444).

Enables bundling and synthesizing an entire multi-surface business ecosystem
(customer web, operator portals, admin dashboards) derived from a Solution Pack's
unified data model into a portable, byte-stable, and verifiable EcosystemPackPackage.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from omnistackai_agent_engine.application_ir import (
    ApplicationIR,
    has_errors,
    normalize_ir,
    validate_ir,
)
from omnistackai_agent_engine.verify import verify_plans_for_ir
from .application import SolutionPackApplicationResult
from .ecosystem_auth import EcosystemAuthContract, synthesize_ecosystem_auth
from .ecosystem_events import EcosystemEventBridgeContract, synthesize_ecosystem_events
from .ecosystem_state import EcosystemStateBinding, synthesize_ecosystem_state
from .ecosystem_telemetry import EcosystemTelemetryContract, synthesize_ecosystem_telemetry
from .ecosystem_deployment import EcosystemDeploymentManifest, synthesize_ecosystem_deployment
from .ecosystem_sync import EcosystemSyncContract, synthesize_ecosystem_sync
from .ecosystem_cicd import EcosystemCICDContract, synthesize_ecosystem_cicd
from .ecosystem_verification import EcosystemVerificationContract, synthesize_ecosystem_verification
from .ecosystem_recovery import EcosystemDisasterRecoveryContract, synthesize_ecosystem_recovery
from .registry import (
    DEFAULT_SOLUTION_PACK_REGISTRY,
    SolutionPack,
    SolutionPackError,
    SolutionPackRegistry,
    canonical_ir_digest,
)

ECOSYSTEM_PACK_SCHEMA_VERSION = "1.0"
_SEMVER_REGEX = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_SLUG_REGEX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return cleaned or "app"


def compute_ecosystem_checksum(payload: Mapping[str, Any]) -> str:
    """Compute deterministic SHA-256 over canonical JSON of all fields except package_sha256."""
    canonical_data = {k: v for k, v in payload.items() if k != "package_sha256"}
    canonical_json = json.dumps(
        canonical_data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EcosystemSurfacePackage:
    """One packaged surface in an ecosystem package bundle."""

    surface_kind: str
    app_name: str
    slug: str
    ir_sha256: str
    ir_dict: dict[str, Any]
    verify_targets: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_kind": self.surface_kind,
            "app_name": self.app_name,
            "slug": self.slug,
            "ir_sha256": self.ir_sha256,
            "ir_dict": self.ir_dict,
            "verify_targets": list(self.verify_targets),
        }

    def to_application_ir(self) -> ApplicationIR:
        ir = ApplicationIR.from_dict(self.ir_dict)
        return normalize_ir(ir)


@dataclass(frozen=True)
class EcosystemPackPackage:
    """Self-contained, portable, and verifiable multi-surface ecosystem package bundle."""

    schema_version: str
    ecosystem_id: str
    version: str
    display_name: str
    description: str
    domain: str
    base_pack_id: str
    surfaces: tuple[EcosystemSurfacePackage, ...]
    package_sha256: str
    auth_contract: EcosystemAuthContract | None = None
    state_binding: EcosystemStateBinding | None = None
    event_bridge: EcosystemEventBridgeContract | None = None
    telemetry_contract: EcosystemTelemetryContract | None = None
    deployment_manifest: EcosystemDeploymentManifest | None = None
    sync_contract: EcosystemSyncContract | None = None
    cicd_contract: EcosystemCICDContract | None = None
    verification_contract: EcosystemVerificationContract | None = None
    recovery_contract: EcosystemDisasterRecoveryContract | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "schema_version": self.schema_version,
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "display_name": self.display_name,
            "description": self.description,
            "domain": self.domain,
            "base_pack_id": self.base_pack_id,
            "surfaces": [s.to_dict() for s in self.surfaces],
            "package_sha256": self.package_sha256,
        }
        if self.auth_contract is not None:
            data["auth_contract"] = self.auth_contract.to_dict()
        if self.state_binding is not None:
            data["state_binding"] = self.state_binding.to_dict()
        if self.event_bridge is not None:
            data["event_bridge"] = self.event_bridge.to_dict()
        if self.telemetry_contract is not None:
            data["telemetry_contract"] = self.telemetry_contract.to_dict()
        if self.deployment_manifest is not None:
            data["deployment_manifest"] = self.deployment_manifest.to_dict()
        if self.sync_contract is not None:
            data["sync_contract"] = self.sync_contract.to_dict()
        if self.cicd_contract is not None:
            data["cicd_contract"] = self.cicd_contract.to_dict()
        if self.verification_contract is not None:
            data["verification_contract"] = self.verification_contract.to_dict()
        if self.recovery_contract is not None:
            data["recovery_contract"] = self.recovery_contract.to_dict()
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def parse_ecosystem_pack_package(data: str | bytes | Mapping[str, Any]) -> EcosystemPackPackage:
    """Strictly parse, validate, and verify an EcosystemPackPackage bundle.

    Fails closed with SolutionPackError on corrupt checksums, invalid schema,
    tampered IRs, semantic errors, or drift.
    """
    if isinstance(data, (str, bytes)):
        try:
            raw = json.loads(data)
        except Exception as exc:
            raise SolutionPackError(f"Invalid JSON payload in ecosystem package: {exc}") from exc
    elif isinstance(data, Mapping):
        raw = dict(data)
    else:
        raise SolutionPackError(f"Expected str, bytes, or mapping, got {type(data).__name__}")

    required_keys = {
        "schema_version",
        "ecosystem_id",
        "version",
        "display_name",
        "description",
        "domain",
        "base_pack_id",
        "surfaces",
        "package_sha256",
    }
    missing = required_keys - set(raw.keys())
    if missing:
        raise SolutionPackError(f"Ecosystem package missing required keys: {', '.join(sorted(missing))}")

    schema_version = str(raw["schema_version"]).strip()
    if schema_version != ECOSYSTEM_PACK_SCHEMA_VERSION:
        raise SolutionPackError(
            f"Unsupported ecosystem package schema version '{schema_version}', expected '{ECOSYSTEM_PACK_SCHEMA_VERSION}'"
        )

    ecosystem_id = str(raw["ecosystem_id"]).strip()
    if not _SLUG_REGEX.match(ecosystem_id):
        raise SolutionPackError(f"Invalid ecosystem_id slug format '{ecosystem_id}'")

    version = str(raw["version"]).strip()
    if not _SEMVER_REGEX.match(version):
        raise SolutionPackError(f"Invalid semver version format '{version}'")

    domain = str(raw["domain"]).strip()
    if not domain or not _SLUG_REGEX.match(domain):
        raise SolutionPackError(f"Invalid domain slug format '{domain}'")

    base_pack_id = str(raw["base_pack_id"]).strip()
    if not base_pack_id or not _SLUG_REGEX.match(base_pack_id):
        raise SolutionPackError(f"Invalid base_pack_id slug format '{base_pack_id}'")

    display_name = str(raw["display_name"]).strip()
    if not display_name:
        raise SolutionPackError("display_name cannot be empty")

    description = str(raw["description"]).strip()

    raw_surfaces = raw["surfaces"]
    if not isinstance(raw_surfaces, (list, tuple)) or len(raw_surfaces) == 0:
        raise SolutionPackError("surfaces must be a non-empty list of surface packages")

    # Check package checksum first
    expected_package_checksum = compute_ecosystem_checksum(raw)
    declared_package_checksum = str(raw["package_sha256"]).strip()
    if declared_package_checksum != expected_package_checksum:
        raise SolutionPackError(
            f"Ecosystem package checksum mismatch: declared {declared_package_checksum}, computed {expected_package_checksum}"
        )

    surfaces_list: list[EcosystemSurfacePackage] = []
    for idx, surface_dict in enumerate(raw_surfaces):
        if not isinstance(surface_dict, Mapping):
            raise SolutionPackError(f"Surface at index {idx} is not an object")

        surface_required = {"surface_kind", "app_name", "slug", "ir_sha256", "ir_dict", "verify_targets"}
        surf_missing = surface_required - set(surface_dict.keys())
        if surf_missing:
            raise SolutionPackError(f"Surface at index {idx} missing keys: {', '.join(sorted(surf_missing))}")

        ir_dict = surface_dict["ir_dict"]
        if not isinstance(ir_dict, dict):
            raise SolutionPackError(f"Surface '{surface_dict.get('surface_kind')}' ir_dict must be a dictionary")

        try:
            ir = ApplicationIR.from_dict(ir_dict)
            ir = normalize_ir(ir)
        except Exception as exc:
            raise SolutionPackError(
                f"Failed to deserialize Application IR for surface '{surface_dict.get('surface_kind')}': {exc}"
            ) from exc

        issues = validate_ir(ir)
        if has_errors(issues):
            detail = "; ".join(f"{i.location}: {i.message}" for i in issues if i.severity.name == "ERROR")
            raise SolutionPackError(f"Application IR validation failed for surface '{surface_dict.get('surface_kind')}': {detail}")

        declared_ir_sha = str(surface_dict["ir_sha256"]).strip()
        computed_ir_sha = canonical_ir_digest(ir)
        if declared_ir_sha != computed_ir_sha:
            raise SolutionPackError(
                f"IR SHA-256 mismatch for surface '{surface_dict.get('surface_kind')}': declared {declared_ir_sha}, computed {computed_ir_sha}"
            )

        surfaces_list.append(
            EcosystemSurfacePackage(
                surface_kind=str(surface_dict["surface_kind"]).strip(),
                app_name=str(surface_dict["app_name"]).strip(),
                slug=str(surface_dict["slug"]).strip(),
                ir_sha256=declared_ir_sha,
                ir_dict=ir_dict,
                verify_targets=tuple(str(t).strip() for t in surface_dict.get("verify_targets", ())),
            )
        )

    auth_contract = None
    if "auth_contract" in raw and raw["auth_contract"] is not None:
        auth_contract = EcosystemAuthContract.from_dict(raw["auth_contract"])

    state_binding = None
    if "state_binding" in raw and raw["state_binding"] is not None:
        state_binding = EcosystemStateBinding.from_dict(raw["state_binding"])

    event_bridge = None
    if "event_bridge" in raw and raw["event_bridge"] is not None:
        event_bridge = EcosystemEventBridgeContract.from_dict(raw["event_bridge"])

    telemetry_contract = None
    if "telemetry_contract" in raw and raw["telemetry_contract"] is not None:
        telemetry_contract = EcosystemTelemetryContract.from_dict(raw["telemetry_contract"])

    deployment_manifest = None
    if "deployment_manifest" in raw and raw["deployment_manifest"] is not None:
        deployment_manifest = EcosystemDeploymentManifest.from_dict(raw["deployment_manifest"])

    sync_contract = None
    if "sync_contract" in raw and raw["sync_contract"] is not None:
        sync_contract = EcosystemSyncContract.from_dict(raw["sync_contract"])

    cicd_contract = None
    if "cicd_contract" in raw and raw["cicd_contract"] is not None:
        cicd_contract = EcosystemCICDContract.from_dict(raw["cicd_contract"])

    verification_contract = None
    if "verification_contract" in raw and raw["verification_contract"] is not None:
        verification_contract = EcosystemVerificationContract.from_dict(raw["verification_contract"])

    recovery_contract = None
    if "recovery_contract" in raw and raw["recovery_contract"] is not None:
        recovery_contract = EcosystemDisasterRecoveryContract.from_dict(raw["recovery_contract"])

    return EcosystemPackPackage(
        schema_version=schema_version,
        ecosystem_id=ecosystem_id,
        version=version,
        display_name=display_name,
        description=description,
        domain=domain,
        base_pack_id=base_pack_id,
        surfaces=tuple(surfaces_list),
        package_sha256=declared_package_checksum,
        auth_contract=auth_contract,
        state_binding=state_binding,
        event_bridge=event_bridge,
        telemetry_contract=telemetry_contract,
        deployment_manifest=deployment_manifest,
        sync_contract=sync_contract,
        cicd_contract=cicd_contract,
        verification_contract=verification_contract,
        recovery_contract=recovery_contract,
    )


def verify_ecosystem_pack(package_or_data: EcosystemPackPackage | Mapping[str, Any] | str | bytes) -> tuple[bool, tuple[str, ...]]:
    """Diagnose an ecosystem pack package, returning (is_valid, diagnostics)."""
    if isinstance(package_or_data, EcosystemPackPackage):
        data = package_or_data.to_dict()
    else:
        data = package_or_data

    try:
        parse_ecosystem_pack_package(data)
        return True, ()
    except Exception as exc:
        return False, (str(exc),)


def synthesize_ecosystem_pack(
    pack_or_result: SolutionPack | SolutionPackApplicationResult,
    proposal: Any = None,
    option_id: str = "complete",
    *,
    registry: SolutionPackRegistry | None = None,
) -> EcosystemPackPackage:
    """Synthesize a complete multi-surface EcosystemPackPackage from a Solution Pack or Application Result."""
    from omnistackai_agent_engine.intake.scope_compiler import DOMAIN_LIBRARY, propose_ecosystem
    from omnistackai_agent_engine.intake.ecosystem import _surfaces_for_option, synthesize_surface_ir

    if registry is None:
        registry = DEFAULT_SOLUTION_PACK_REGISTRY

    if isinstance(pack_or_result, str):
        pack = registry.get(pack_or_result)
        if pack is None:
            raise SolutionPackError(f"Solution pack '{pack_or_result}' not found in registry")
        pack_or_result = pack

    if isinstance(pack_or_result, SolutionPackApplicationResult):
        base_pack_id = pack_or_result.pack_id
        version = pack_or_result.pack_version
        primary_ir = pack_or_result.ir
        descriptor = registry.get(base_pack_id)
        domain = descriptor.domains[0] if descriptor else "custom-application"
        display_name = f"{primary_ir.name} Ecosystem"
        description = f"Synthesized multi-surface ecosystem for {primary_ir.name}"
    elif isinstance(pack_or_result, SolutionPack):
        base_pack_id = pack_or_result.pack_id
        version = pack_or_result.version
        primary_ir = registry.load_ir(base_pack_id, version)
        domain = pack_or_result.domains[0]
        display_name = f"{pack_or_result.display_name} Ecosystem"
        description = f"Synthesized multi-surface ecosystem for {pack_or_result.display_name}"
    else:
        raise SolutionPackError(f"Unsupported pack object type: {type(pack_or_result).__name__}")

    if proposal is None:
        matched_spec = next((spec for spec in DOMAIN_LIBRARY if spec.domain == domain), None)
        prompt = matched_spec.example_prompt if matched_spec else domain
        proposal = propose_ecosystem(prompt)

    surfaces = _surfaces_for_option(proposal, option_id)
    if not surfaces:
        surfaces = proposal.surfaces

    target_surface_index: int | None = None
    for idx, s in enumerate(surfaces):
        if s.kind in ("customer_web", "customer_pwa", "public_web"):
            target_surface_index = idx
            break
    if target_surface_index is None:
        target_surface_index = 0

    surface_packages: list[EcosystemSurfacePackage] = []
    for idx, surface in enumerate(surfaces):
        if idx == target_surface_index:
            ir = primary_ir
        else:
            ir = synthesize_surface_ir(proposal, surface, primary_ir)

        ir = normalize_ir(ir)
        plans = verify_plans_for_ir(ir)
        verify_targets = tuple(sorted({p.target for p in plans}))
        ir_sha = canonical_ir_digest(ir)

        surface_packages.append(
            EcosystemSurfacePackage(
                surface_kind=surface.kind,
                app_name=ir.name,
                slug=_slug(ir.name),
                ir_sha256=ir_sha,
                ir_dict=ir.to_dict(),
                verify_targets=verify_targets,
            )
        )

    ecosystem_id = f"{base_pack_id}-ecosystem"
    auth_contract = synthesize_ecosystem_auth(ecosystem_id, surface_packages)
    state_binding = synthesize_ecosystem_state(ecosystem_id, surface_packages)
    event_bridge = synthesize_ecosystem_events(ecosystem_id, surface_packages, state_binding=state_binding)
    telemetry_contract = synthesize_ecosystem_telemetry(ecosystem_id, surface_packages)
    deployment_manifest = synthesize_ecosystem_deployment(
        ecosystem_id,
        surface_packages,
        auth_contract=auth_contract,
        state_binding=state_binding,
    )
    sync_contract = synthesize_ecosystem_sync(
        ecosystem_id,
        surface_packages,
        version=version,
    )
    cicd_contract = synthesize_ecosystem_cicd(
        ecosystem_id,
        surface_packages,
    )
    verification_contract = synthesize_ecosystem_verification(
        ecosystem_id,
        surface_packages,
        version=version,
    )
    recovery_contract = synthesize_ecosystem_recovery(
        ecosystem_id,
        surface_packages,
        version=version,
    )

    payload = {
        "schema_version": ECOSYSTEM_PACK_SCHEMA_VERSION,
        "ecosystem_id": ecosystem_id,
        "version": version,
        "display_name": display_name,
        "description": description,
        "domain": domain,
        "base_pack_id": base_pack_id,
        "surfaces": [s.to_dict() for s in surface_packages],
        "auth_contract": auth_contract.to_dict(),
        "state_binding": state_binding.to_dict(),
        "event_bridge": event_bridge.to_dict(),
        "telemetry_contract": telemetry_contract.to_dict(),
        "deployment_manifest": deployment_manifest.to_dict(),
        "sync_contract": sync_contract.to_dict(),
        "cicd_contract": cicd_contract.to_dict(),
        "verification_contract": verification_contract.to_dict(),
        "recovery_contract": recovery_contract.to_dict(),
    }
    package_sha256 = compute_ecosystem_checksum(payload)

    return EcosystemPackPackage(
        schema_version=ECOSYSTEM_PACK_SCHEMA_VERSION,
        ecosystem_id=ecosystem_id,
        version=version,
        display_name=display_name,
        description=description,
        domain=domain,
        base_pack_id=base_pack_id,
        surfaces=tuple(surface_packages),
        package_sha256=package_sha256,
        auth_contract=auth_contract,
        state_binding=state_binding,
        event_bridge=event_bridge,
        telemetry_contract=telemetry_contract,
        deployment_manifest=deployment_manifest,
        sync_contract=sync_contract,
        cicd_contract=cicd_contract,
        verification_contract=verification_contract,
        recovery_contract=recovery_contract,
    )

"""Ecosystem Pack Registry, Catalog Discovery, and Management (R-445).

Provides an immutable, deterministic registry for multi-surface ecosystem packs,
catalog discovery and recommendation, dynamic package registration, and surface IR
loading for the OmniStackAI platform and Studio.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from omnistackai_agent_engine.application_ir import ApplicationIR
from .ecosystem_pack import (
    EcosystemPackPackage,
    EcosystemSurfacePackage,
    parse_ecosystem_pack_package,
    synthesize_ecosystem_pack,
)
from .registry import (
    DEFAULT_SOLUTION_PACK_REGISTRY,
    SolutionPackError,
    _bounded_text,
    _slug,
    _version_key,
)


@dataclass(frozen=True, slots=True)
class EcosystemPack:
    """Descriptor representing a registered verified multi-surface ecosystem pack."""

    ecosystem_id: str
    version: str
    display_name: str
    description: str
    domain: str
    base_pack_id: str
    surfaces: tuple[EcosystemSurfacePackage, ...]
    package_sha256: str
    package: EcosystemPackPackage | None = None

    def __post_init__(self) -> None:
        _slug(self.ecosystem_id, "ecosystem_id")
        _version_key(self.version)
        _bounded_text(self.display_name, "display_name", maximum=140)
        _bounded_text(self.description, "description", maximum=600)
        _slug(self.domain, "domain")
        _slug(self.base_pack_id, "base_pack_id")
        if not self.surfaces:
            raise SolutionPackError("EcosystemPack must have at least one surface")
        if not isinstance(self.package_sha256, str) or len(self.package_sha256) != 64:
            raise SolutionPackError("package_sha256 must be a 64-character hex string")

    @property
    def surface_count(self) -> int:
        return len(self.surfaces)

    @property
    def surface_kinds(self) -> tuple[str, ...]:
        return tuple(s.surface_kind for s in self.surfaces)

    @property
    def surface_slugs(self) -> tuple[str, ...]:
        return tuple(s.slug for s in self.surfaces)

    @property
    def auth_contract(self) -> Any:
        return self.package.auth_contract if self.package else None

    @property
    def state_binding(self) -> Any:
        return self.package.state_binding if self.package else None

    @property
    def event_bridge(self) -> Any:
        return self.package.event_bridge if self.package else None

    @property
    def telemetry_contract(self) -> Any:
        return self.package.telemetry_contract if self.package else None

    @property
    def deployment_manifest(self) -> Any:
        return self.package.deployment_manifest if self.package else None

    @property
    def sync_contract(self) -> Any:
        return self.package.sync_contract if self.package else None

    @property
    def cicd_contract(self) -> Any:
        return self.package.cicd_contract if self.package else None

    @property
    def verification_contract(self) -> Any:
        return self.package.verification_contract if self.package else None

    @property
    def recovery_contract(self) -> Any:
        return self.package.recovery_contract if self.package else None

    @property
    def capacity_contract(self) -> Any:
        return self.package.capacity_contract if self.package else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "display_name": self.display_name,
            "description": self.description,
            "domain": self.domain,
            "base_pack_id": self.base_pack_id,
            "package_sha256": self.package_sha256,
            "surface_count": len(self.surfaces),
            "surfaces": [
                {
                    "surface_kind": s.surface_kind,
                    "app_name": s.app_name,
                    "slug": s.slug,
                    "ir_sha256": s.ir_sha256,
                    "verify_targets": list(s.verify_targets),
                }
                for s in self.surfaces
            ],
            "has_auth_contract": self.auth_contract is not None,
            "has_state_binding": self.state_binding is not None,
            "has_event_bridge": self.event_bridge is not None,
            "has_telemetry_contract": self.telemetry_contract is not None,
            "has_deployment_manifest": self.deployment_manifest is not None,
            "has_sync_contract": self.sync_contract is not None,
            "has_cicd_contract": self.cicd_contract is not None,
            "has_verification_contract": self.verification_contract is not None,
            "has_recovery_contract": self.recovery_contract is not None,
            "has_capacity_contract": self.capacity_contract is not None,
        }

    @classmethod
    def from_package(cls, pkg: EcosystemPackPackage) -> "EcosystemPack":
        """Instantiate an EcosystemPack descriptor from a verified EcosystemPackPackage."""
        return cls(
            ecosystem_id=pkg.ecosystem_id,
            version=pkg.version,
            display_name=pkg.display_name,
            description=pkg.description,
            domain=pkg.domain,
            base_pack_id=pkg.base_pack_id,
            surfaces=pkg.surfaces,
            package_sha256=pkg.package_sha256,
            package=pkg,
        )

    def to_package(self) -> EcosystemPackPackage:
        """Return the underlying EcosystemPackPackage."""
        if self.package is not None:
            return self.package
        return EcosystemPackPackage(
            schema_version="1.0",
            ecosystem_id=self.ecosystem_id,
            version=self.version,
            display_name=self.display_name,
            description=self.description,
            domain=self.domain,
            base_pack_id=self.base_pack_id,
            surfaces=self.surfaces,
            package_sha256=self.package_sha256,
        )


@dataclass(frozen=True, slots=True)
class EcosystemPackRecommendation:
    """A deterministic recommendation query and result for ecosystem packs."""

    domain: str
    ecosystem: EcosystemPack | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "status": self.status,
            "ecosystem": self.ecosystem.to_dict() if self.ecosystem else None,
        }


class EcosystemPackRegistry:
    """An immutable, validated collection of ecosystem packs with deterministic lookup."""

    ecosystems: tuple[EcosystemPack, ...]

    def __init__(self, ecosystems: tuple[EcosystemPack, ...]) -> None:
        if not isinstance(ecosystems, tuple):
            raise SolutionPackError("ecosystems must be a tuple of EcosystemPack descriptors")
        seen: set[tuple[str, str]] = set()
        for eco in ecosystems:
            if not isinstance(eco, EcosystemPack):
                raise SolutionPackError("registry entries must be EcosystemPack descriptors")
            identity = (eco.ecosystem_id, eco.version)
            if identity in seen:
                raise SolutionPackError(f"Duplicate ecosystem pack {eco.ecosystem_id}@{eco.version}")
            seen.add(identity)
        ordered = tuple(
            sorted(
                ecosystems,
                key=lambda e: (
                    e.ecosystem_id,
                    tuple(-part for part in _version_key(e.version)),
                ),
            )
        )
        object.__setattr__(self, "ecosystems", ordered)

    def list_packs(self) -> tuple[EcosystemPack, ...]:
        """Return all registered ecosystem packs."""
        return self.ecosystems

    def get(self, ecosystem_id: str, version: str | None = None) -> EcosystemPack | None:
        """Return an exact version, or newest registered stable version, for ``ecosystem_id``."""
        _slug(ecosystem_id, "ecosystem_id query")
        if version is not None:
            _version_key(version)
        matches = tuple(
            e
            for e in self.ecosystems
            if e.ecosystem_id == ecosystem_id and (version is None or e.version == version)
        )
        if not matches:
            return None
        return max(matches, key=lambda e: _version_key(e.version))

    def select(
        self,
        domain: str,
        *,
        required_surfaces: tuple[str, ...] = (),
    ) -> EcosystemPack | None:
        """Select newest ecosystem pack for an exact domain satisfying required surface kinds."""
        domain = _slug(domain, "domain query")
        required = set(required_surfaces)
        matches = [
            e
            for e in self.ecosystems
            if e.domain == domain and (not required or required <= set(e.surface_kinds))
        ]
        if not matches:
            return None
        return max(matches, key=lambda e: _version_key(e.version))

    def recommend(self, domain: str, prompt: str = "") -> EcosystemPackRecommendation:
        """Recommend an ecosystem pack for a domain query."""
        selected = self.select(domain)
        status = "selected" if selected is not None else "no-exact-match"
        return EcosystemPackRecommendation(
            domain=domain,
            ecosystem=selected,
            status=status,
        )

    def register_package(self, pkg: EcosystemPackPackage | Mapping[str, Any]) -> "EcosystemPackRegistry":
        """Validate package and return a fresh registry containing the newly registered pack."""
        if not isinstance(pkg, EcosystemPackPackage):
            pkg = parse_ecosystem_pack_package(pkg)
        pack = EcosystemPack.from_package(pkg)
        existing = [
            e
            for e in self.ecosystems
            if not (e.ecosystem_id == pack.ecosystem_id and e.version == pack.version)
        ]
        return EcosystemPackRegistry(tuple(existing + [pack]))

    def load_package(self, ecosystem_id: str, version: str | None = None) -> EcosystemPackPackage:
        """Load the verified EcosystemPackPackage for ``ecosystem_id``."""
        pack = self.get(ecosystem_id, version)
        if pack is None:
            raise SolutionPackError(f"Ecosystem pack '{ecosystem_id}' not found in registry")
        return pack.to_package()

    def load_surface_ir(
        self,
        ecosystem_id: str,
        surface_slug: str,
        version: str | None = None,
    ) -> ApplicationIR:
        """Load and normalize the ApplicationIR for a specific surface in an ecosystem pack."""
        pkg = self.load_package(ecosystem_id, version)
        surface = next(
            (s for s in pkg.surfaces if s.slug == surface_slug or s.surface_kind == surface_slug),
            None,
        )
        if surface is None:
            available = [f"{s.slug} ({s.surface_kind})" for s in pkg.surfaces]
            raise SolutionPackError(
                f"Surface '{surface_slug}' not found in ecosystem '{ecosystem_id}'. Available: {', '.join(available)}"
            )
        return surface.to_application_ir()

    def get_auth_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        """Get the EcosystemAuthContract for an ecosystem if present."""
        pack = self.get(ecosystem_id, version)
        return pack.auth_contract if pack else None

    def get_state_binding(self, ecosystem_id: str, version: str | None = None) -> Any:
        """Get the EcosystemStateBinding for an ecosystem if present."""
        pack = self.get(ecosystem_id, version)
        return pack.state_binding if pack else None

    def get_event_bridge(self, ecosystem_id: str, version: str | None = None) -> Any:
        """Get the EcosystemEventBridgeContract for an ecosystem if present."""
        pack = self.get(ecosystem_id, version)
        return pack.event_bridge if pack else None

    def get_telemetry_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        """Get the EcosystemTelemetryContract for an ecosystem if present."""
        pack = self.get(ecosystem_id, version)
        return pack.telemetry_contract if pack else None

    def get_deployment_manifest(self, ecosystem_id: str, version: str | None = None) -> Any:
        """Get the EcosystemDeploymentManifest for an ecosystem if present."""
        pack = self.get(ecosystem_id, version)
        return pack.deployment_manifest if pack else None

    def get_sync_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        """Get the EcosystemSyncContract for an ecosystem if present."""
        pack = self.get(ecosystem_id, version)
        return pack.sync_contract if pack else None

    def get_cicd_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        """Get the EcosystemCICDContract for an ecosystem if present."""
        pack = self.get(ecosystem_id, version)
        return pack.cicd_contract if pack else None

    def get_verification_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        """Get the EcosystemVerificationContract for an ecosystem if present."""
        pack = self.get(ecosystem_id, version)
        return pack.verification_contract if pack else None

    def get_recovery_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        """Get the EcosystemDisasterRecoveryContract for an ecosystem if present."""
        pack = self.get(ecosystem_id, version)
        return pack.recovery_contract if pack else None

    def get_capacity_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        """Get the EcosystemCapacityContract for an ecosystem if present."""
        pack = self.get(ecosystem_id, version)
        return pack.capacity_contract if pack else None


def build_default_ecosystem_packs() -> tuple[EcosystemPack, ...]:
    """Synthesize default verified ecosystem packs from registered baseline solution packs."""
    packs: list[EcosystemPack] = []
    # 1. Minimal Blog Ecosystem
    mb_pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
    if mb_pack is not None:
        mb_pkg = synthesize_ecosystem_pack(mb_pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)
        packs.append(EcosystemPack.from_package(mb_pkg))

    # 2. Rideshare Favourites Ecosystem
    rs_pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("rideshare-favourites")
    if rs_pack is not None:
        rs_pkg = synthesize_ecosystem_pack(rs_pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)
        packs.append(EcosystemPack.from_package(rs_pkg))

    return tuple(packs)


class _LazyEcosystemPackRegistry(EcosystemPackRegistry):
    """Lazy proxy for the default registry to prevent eager import-time circular dependencies."""

    _instance: EcosystemPackRegistry | None = None

    def __init__(self) -> None:
        pass

    @classmethod
    def _get_delegate(cls) -> EcosystemPackRegistry:
        if cls._instance is None:
            cls._instance = EcosystemPackRegistry(build_default_ecosystem_packs())
        return cls._instance

    @property
    def ecosystems(self) -> tuple[EcosystemPack, ...]:
        return self._get_delegate().ecosystems

    def list_packs(self) -> tuple[EcosystemPack, ...]:
        return self._get_delegate().list_packs()

    def get(self, ecosystem_id: str, version: str | None = None) -> EcosystemPack | None:
        return self._get_delegate().get(ecosystem_id, version)

    def select(
        self,
        domain: str,
        *,
        required_surfaces: tuple[str, ...] = (),
    ) -> EcosystemPack | None:
        return self._get_delegate().select(domain, required_surfaces=required_surfaces)

    def recommend(self, domain: str, prompt: str = "") -> EcosystemPackRecommendation:
        return self._get_delegate().recommend(domain, prompt)

    def register_package(self, pkg: Any) -> EcosystemPackRegistry:
        return self._get_delegate().register_package(pkg)

    def load_package(self, ecosystem_id: str, version: str | None = None) -> EcosystemPackPackage:
        return self._get_delegate().load_package(ecosystem_id, version)

    def load_surface_ir(
        self,
        ecosystem_id: str,
        surface_slug: str,
        version: str | None = None,
    ) -> ApplicationIR:
        return self._get_delegate().load_surface_ir(ecosystem_id, surface_slug, version)

    def get_auth_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        return self._get_delegate().get_auth_contract(ecosystem_id, version)

    def get_state_binding(self, ecosystem_id: str, version: str | None = None) -> Any:
        return self._get_delegate().get_state_binding(ecosystem_id, version)

    def get_event_bridge(self, ecosystem_id: str, version: str | None = None) -> Any:
        return self._get_delegate().get_event_bridge(ecosystem_id, version)

    def get_telemetry_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        return self._get_delegate().get_telemetry_contract(ecosystem_id, version)

    def get_deployment_manifest(self, ecosystem_id: str, version: str | None = None) -> Any:
        return self._get_delegate().get_deployment_manifest(ecosystem_id, version)

    def get_sync_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        return self._get_delegate().get_sync_contract(ecosystem_id, version)

    def get_cicd_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        return self._get_delegate().get_cicd_contract(ecosystem_id, version)

    def get_verification_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        return self._get_delegate().get_verification_contract(ecosystem_id, version)

    def get_recovery_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        return self._get_delegate().get_recovery_contract(ecosystem_id, version)

    def get_capacity_contract(self, ecosystem_id: str, version: str | None = None) -> Any:
        return self._get_delegate().get_capacity_contract(ecosystem_id, version)


DEFAULT_ECOSYSTEM_PACK_REGISTRY: EcosystemPackRegistry = _LazyEcosystemPackRegistry()

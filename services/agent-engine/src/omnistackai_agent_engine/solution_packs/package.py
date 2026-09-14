"""Standalone, portable Solution Pack packaging and verification (R-443).

Enables Solution Packs to be bundled into self-contained, redistributable, and
tamper-evident .pack.json packages with canonical Application IR, verification plans,
and cryptographic digests. 100% offline, stdlib-only, and deterministic.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from ..application_ir import ApplicationIR, validate_ir
from ..application_ir.validate import has_errors
from ..projectplan import build_project_plan
from .registry import (
    _SHA256,
    SolutionPack,
    SolutionPackError,
    _bounded_text,
    _slug,
    _slug_tuple,
    _version_key,
    canonical_ir_digest,
)

PACKAGE_SCHEMA_VERSION = "1.0"


def compute_package_checksum(payload: dict[str, Any]) -> str:
    """Compute the stable SHA-256 digest of a package payload excluding package_sha256."""
    clean = {k: v for k, v in payload.items() if k != "package_sha256"}
    encoded = json.dumps(
        clean,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class SolutionPackPackage:
    """A self-contained, portable, and verifiable Solution Pack bundle."""

    schema_version: str
    pack_id: str
    version: str
    display_name: str
    description: str
    domains: tuple[str, ...]
    capabilities: tuple[str, ...]
    targets: tuple[str, ...]
    verify_targets: tuple[str, ...]
    ir_sha256: str
    ir_dict: dict[str, Any]
    verify_plans: dict[str, Any]
    package_sha256: str

    @classmethod
    def from_solution_pack(
        cls,
        pack: SolutionPack,
        *,
        registry: Any | None = None,
    ) -> "SolutionPackPackage":
        """Build a self-contained package from a registered SolutionPack."""
        from .registry import DEFAULT_SOLUTION_PACK_REGISTRY

        reg = registry or DEFAULT_SOLUTION_PACK_REGISTRY
        ir = reg.load_ir(pack.pack_id, pack.version)
        plan = build_project_plan(ir)
        verify_plans = {
            app.app_dir: (
                [step.command.display() for step in app.verify.steps]
                if app.verify is not None
                else []
            )
            for app in plan.apps
        }
        ir_dict = ir.to_dict()
        ir_digest = canonical_ir_digest(ir)

        payload: dict[str, Any] = {
            "schema_version": PACKAGE_SCHEMA_VERSION,
            "pack_id": pack.pack_id,
            "version": pack.version,
            "display_name": pack.display_name,
            "description": pack.description,
            "domains": list(pack.domains),
            "capabilities": list(pack.capabilities),
            "targets": list(pack.targets),
            "verify_targets": list(pack.targets),
            "ir_sha256": ir_digest,
            "ir_dict": ir_dict,
            "verify_plans": verify_plans,
        }
        checksum = compute_package_checksum(payload)
        return cls(
            schema_version=PACKAGE_SCHEMA_VERSION,
            pack_id=pack.pack_id,
            version=pack.version,
            display_name=pack.display_name,
            description=pack.description,
            domains=pack.domains,
            capabilities=pack.capabilities,
            targets=pack.targets,
            verify_targets=pack.targets,
            ir_sha256=ir_digest,
            ir_dict=ir_dict,
            verify_plans=verify_plans,
            package_sha256=checksum,
        )

    def to_application_ir(self) -> ApplicationIR:
        """Safely deserialize and validate the embedded Application IR."""
        try:
            ir = ApplicationIR.from_dict(self.ir_dict)
        except Exception as error:
            raise SolutionPackError(
                f"corrupted Application IR in package {self.pack_id}@{self.version}: {error}"
            ) from error
        issues = validate_ir(ir)
        if has_errors(issues):
            raise SolutionPackError(
                f"embedded Application IR in package {self.pack_id}@{self.version} has validation errors: {issues}"
            )
        return ir

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-safe dictionary representation."""
        return {
            "schema_version": self.schema_version,
            "pack_id": self.pack_id,
            "version": self.version,
            "display_name": self.display_name,
            "description": self.description,
            "domains": list(self.domains),
            "capabilities": list(self.capabilities),
            "targets": list(self.targets),
            "verify_targets": list(self.verify_targets),
            "ir_sha256": self.ir_sha256,
            "ir_dict": self.ir_dict,
            "verify_plans": self.verify_plans,
            "package_sha256": self.package_sha256,
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        """Return byte-stable canonical JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, sort_keys=True)


def parse_solution_pack_package(
    data: str | bytes | dict[str, Any],
    *,
    verify_integrity: bool = True,
) -> SolutionPackPackage:
    """Parse and strictly validate a SolutionPackPackage from JSON or dict."""
    if isinstance(data, (str, bytes)):
        try:
            raw = json.loads(data)
        except Exception as error:
            raise SolutionPackError(f"invalid package JSON: {error}") from error
    elif isinstance(data, dict):
        raw = data
    else:
        raise SolutionPackError("package data must be a JSON string, bytes, or dictionary")

    if not isinstance(raw, dict):
        raise SolutionPackError("package payload must be a mapping")

    required_keys = {
        "schema_version",
        "pack_id",
        "version",
        "display_name",
        "description",
        "domains",
        "capabilities",
        "targets",
        "verify_targets",
        "ir_sha256",
        "ir_dict",
        "verify_plans",
        "package_sha256",
    }
    missing = required_keys - set(raw.keys())
    if missing:
        raise SolutionPackError(f"package missing required keys: {sorted(missing)}")

    schema_version = str(raw["schema_version"])
    if schema_version != PACKAGE_SCHEMA_VERSION:
        raise SolutionPackError(
            f"unsupported package schema version {schema_version!r}; expected {PACKAGE_SCHEMA_VERSION!r}"
        )

    pack_id = _slug(raw["pack_id"], "pack_id")
    version = str(raw["version"])
    _version_key(version)
    display_name = _bounded_text(raw["display_name"], "display_name", maximum=120)
    description = _bounded_text(raw["description"], "description", maximum=500)
    domains = _slug_tuple(
        tuple(raw["domains"]) if isinstance(raw["domains"], (list, tuple)) else None,
        "domains",
    )
    capabilities = _slug_tuple(
        tuple(raw["capabilities"]) if isinstance(raw["capabilities"], (list, tuple)) else None,
        "capabilities",
    )
    targets = _slug_tuple(
        tuple(raw["targets"]) if isinstance(raw["targets"], (list, tuple)) else None,
        "targets",
    )
    verify_targets = _slug_tuple(
        tuple(raw["verify_targets"]) if isinstance(raw["verify_targets"], (list, tuple)) else None,
        "verify_targets",
    )

    ir_sha256 = str(raw["ir_sha256"])
    if not isinstance(ir_sha256, str) or _SHA256.fullmatch(ir_sha256) is None:
        raise SolutionPackError("ir_sha256 must be a lowercase 64-character SHA-256 digest")

    ir_dict = raw["ir_dict"]
    if not isinstance(ir_dict, dict):
        raise SolutionPackError("ir_dict must be a dictionary")

    verify_plans = raw["verify_plans"]
    if not isinstance(verify_plans, dict):
        raise SolutionPackError("verify_plans must be a dictionary")

    package_sha256 = str(raw["package_sha256"])
    if not isinstance(package_sha256, str) or _SHA256.fullmatch(package_sha256) is None:
        raise SolutionPackError("package_sha256 must be a lowercase 64-character SHA-256 digest")

    if verify_integrity:
        expected_checksum = compute_package_checksum(raw)
        if package_sha256 != expected_checksum:
            raise SolutionPackError(
                f"package checksum mismatch for {pack_id}@{version}: recorded {package_sha256} vs computed {expected_checksum}"
            )

        try:
            ir = ApplicationIR.from_dict(ir_dict)
        except Exception as error:
            raise SolutionPackError(f"corrupted embedded Application IR: {error}") from error

        issues = validate_ir(ir)
        if has_errors(issues):
            raise SolutionPackError(f"embedded Application IR has validation errors: {issues}")

        actual_ir_digest = canonical_ir_digest(ir)
        if actual_ir_digest != ir_sha256:
            raise SolutionPackError(
                f"embedded Application IR digest drifted for {pack_id}@{version}: recorded {ir_sha256} vs computed {actual_ir_digest}"
            )

    return SolutionPackPackage(
        schema_version=schema_version,
        pack_id=pack_id,
        version=version,
        display_name=display_name,
        description=description,
        domains=domains,
        capabilities=capabilities,
        targets=targets,
        verify_targets=verify_targets,
        ir_sha256=ir_sha256,
        ir_dict=ir_dict,
        verify_plans=verify_plans,
        package_sha256=package_sha256,
    )


def verify_package(data: str | bytes | dict[str, Any]) -> tuple[bool, str]:
    """Verify package integrity, returning (is_valid, human_readable_reason)."""
    try:
        pkg = parse_solution_pack_package(data, verify_integrity=True)
        return True, f"Package {pkg.pack_id}@{pkg.version} is valid and verified (SHA-256: {pkg.package_sha256[:12]})."
    except Exception as error:
        return False, f"Package verification failed: {error}"

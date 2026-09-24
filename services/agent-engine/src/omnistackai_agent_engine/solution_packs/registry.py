"""Immutable Solution Pack descriptors, registry, and planning recommendations (R-434, R-435).

A baseline pack references an existing, verified Application IR builder. It never copies generated source.
The descriptor pins the canonical IR digest and assembled targets so an IR change cannot silently masquerade
as the same pack version. Registry construction and selection are pure/offline and make no model calls.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from ..application_ir import ApplicationIR, example_ir, validate_ir
from ..application_ir.validate import has_errors
from ..projectplan import build_project_plan

_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class SolutionPackError(ValueError):
    """A pack descriptor or registry violates the deterministic pack contract."""


def _bounded_text(value: object, label: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise SolutionPackError(f"{label} must be non-empty text of at most {maximum} characters")
    return value


def _slug(value: object, label: str) -> str:
    if not isinstance(value, str) or _SLUG.fullmatch(value) is None:
        raise SolutionPackError(f"{label} must be a lowercase hyphenated identifier")
    return value


def _slug_tuple(value: object, label: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, tuple) or (not value and not allow_empty):
        requirement = "a tuple" if allow_empty else "a non-empty tuple"
        raise SolutionPackError(f"{label} must be {requirement} of identifiers")
    checked = tuple(_slug(item, f"{label} item") for item in value)
    if len(set(checked)) != len(checked):
        raise SolutionPackError(f"{label} must not contain duplicates")
    return checked


def _version_key(version: str) -> tuple[int, int, int]:
    match = _SEMVER.fullmatch(version) if isinstance(version, str) else None
    if match is None:
        raise SolutionPackError("version must use stable major.minor.patch semantic versioning")
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def canonical_ir_digest(ir: ApplicationIR) -> str:
    """Return the stable SHA-256 for an Application IR's canonical JSON representation."""
    if not isinstance(ir, ApplicationIR):
        raise TypeError("canonical_ir_digest expects an ApplicationIR")
    encoded = json.dumps(
        ir.to_dict(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class SolutionPack:
    """An immutable version pin to an existing verified Application IR baseline."""

    pack_id: str
    version: str
    display_name: str
    description: str
    domains: tuple[str, ...]
    capabilities: tuple[str, ...]
    example_ir_ref: str
    ir_sha256: str
    targets: tuple[str, ...]
    package: object | None = None

    def __post_init__(self) -> None:
        _slug(self.pack_id, "pack_id")
        _version_key(self.version)
        _bounded_text(self.display_name, "display_name", maximum=120)
        _bounded_text(self.description, "description", maximum=500)
        _slug_tuple(self.domains, "domains")
        _slug_tuple(self.capabilities, "capabilities")
        _slug(self.example_ir_ref, "example_ir_ref")
        if not isinstance(self.ir_sha256, str) or _SHA256.fullmatch(self.ir_sha256) is None:
            raise SolutionPackError("ir_sha256 must be a lowercase 64-character SHA-256 digest")
        _slug_tuple(self.targets, "targets")

    @classmethod
    def from_package(cls, pkg: object) -> "SolutionPack":
        """Construct a SolutionPack descriptor wrapping an in-memory package."""
        from .package import SolutionPackPackage

        if not isinstance(pkg, SolutionPackPackage):
            raise SolutionPackError("from_package expects a SolutionPackPackage")
        return cls(
            pack_id=pkg.pack_id,
            version=pkg.version,
            display_name=pkg.display_name,
            description=pkg.description,
            domains=pkg.domains,
            capabilities=pkg.capabilities,
            example_ir_ref=f"pkg-{pkg.pack_id}",
            ir_sha256=pkg.ir_sha256,
            targets=pkg.targets,
            package=pkg,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "pack_id": self.pack_id,
            "version": self.version,
            "display_name": self.display_name,
            "description": self.description,
            "domains": list(self.domains),
            "capabilities": list(self.capabilities),
            "example_ir_ref": self.example_ir_ref,
            "ir_sha256": self.ir_sha256,
            "targets": list(self.targets),
        }


@dataclass(frozen=True, slots=True)
class SolutionPackRecommendation:
    """A canonical compatibility query plus its exact registry selection, if one exists."""

    domain: str
    required_capabilities: tuple[str, ...]
    required_targets: tuple[str, ...]
    selection: SolutionPack | None

    def __post_init__(self) -> None:
        _slug(self.domain, "recommendation domain")
        capabilities = _slug_tuple(
            self.required_capabilities,
            "recommendation required_capabilities",
            allow_empty=True,
        )
        targets = _slug_tuple(
            self.required_targets,
            "recommendation required_targets",
            allow_empty=True,
        )
        if capabilities != tuple(sorted(capabilities)) or targets != tuple(sorted(targets)):
            raise SolutionPackError("recommendation requirements must be canonically sorted")
        if self.selection is None:
            return
        if not isinstance(self.selection, SolutionPack):
            raise SolutionPackError("recommendation selection must be a SolutionPack or None")
        if (
            self.domain not in self.selection.domains
            or not set(capabilities) <= set(self.selection.capabilities)
            or not set(targets) <= set(self.selection.targets)
        ):
            raise SolutionPackError("recommendation selection is incompatible with its exact query")

    def to_dict(self) -> dict[str, object]:
        selection: dict[str, object] | None = None
        if self.selection is not None:
            selection = {
                "pack_id": self.selection.pack_id,
                "version": self.selection.version,
                "ir_sha256": self.selection.ir_sha256,
                "targets": list(self.selection.targets),
            }
        return {
            "status": "selected" if self.selection is not None else "no-exact-match",
            "query": {
                "domain": self.domain,
                "required_capabilities": list(self.required_capabilities),
                "required_targets": list(self.required_targets),
            },
            "selection": selection,
        }


def _load_and_validate(pack: SolutionPack) -> ApplicationIR:
    if getattr(pack, "package", None) is not None:
        ir = pack.package.to_application_ir()  # type: ignore[union-attr]
    else:
        try:
            ir = example_ir(pack.example_ir_ref)
        except Exception as error:  # existing builder owns its bounded error type
            raise SolutionPackError(
                f"pack {pack.pack_id}@{pack.version} references unknown example {pack.example_ir_ref!r}"
            ) from error

    issues = validate_ir(ir)
    if has_errors(issues):
        raise SolutionPackError(f"pack {pack.pack_id}@{pack.version} references an invalid IR")

    actual_digest = canonical_ir_digest(ir)
    if actual_digest != pack.ir_sha256:
        raise SolutionPackError(
            f"pack {pack.pack_id}@{pack.version} IR digest drifted; create a new pack version"
        )

    plan = build_project_plan(ir)
    actual_targets = tuple(app.target for app in plan.apps)
    if actual_targets != pack.targets:
        raise SolutionPackError(
            f"pack {pack.pack_id}@{pack.version} assembled targets drifted: {actual_targets!r}"
        )
    if any(app.verify is None for app in plan.apps):
        raise SolutionPackError(
            f"pack {pack.pack_id}@{pack.version} has a target without a verify plan"
        )
    return ir


@dataclass(frozen=True, slots=True, init=False)
class SolutionPackRegistry:
    """An immutable validated collection with deterministic lookup and selection."""

    packs: tuple[SolutionPack, ...]

    def __init__(self, packs: tuple[SolutionPack, ...]) -> None:
        if not isinstance(packs, tuple):
            raise SolutionPackError("registry packs must be a tuple")
        seen: set[tuple[str, str]] = set()
        for pack in packs:
            if not isinstance(pack, SolutionPack):
                raise SolutionPackError("registry entries must be SolutionPack descriptors")
            identity = (pack.pack_id, pack.version)
            if identity in seen:
                raise SolutionPackError(f"duplicate Solution Pack {pack.pack_id}@{pack.version}")
            seen.add(identity)
            _load_and_validate(pack)
        ordered = tuple(
            sorted(
                packs,
                key=lambda pack: (
                    pack.pack_id,
                    tuple(-part for part in _version_key(pack.version)),
                ),
            )
        )
        object.__setattr__(self, "packs", ordered)

    def register_package(self, pkg: object) -> "SolutionPackRegistry":
        """Return a fresh immutable registry with the given package registered."""
        pack = SolutionPack.from_package(pkg)
        existing = [
            p
            for p in self.packs
            if not (p.pack_id == pack.pack_id and p.version == pack.version)
        ]
        return SolutionPackRegistry(tuple(existing + [pack]))

    def get(self, pack_id: str, version: str | None = None) -> SolutionPack | None:
        """Return an exact version, or the newest registered stable version, for ``pack_id``."""
        _slug(pack_id, "pack_id query")
        if version is not None:
            _version_key(version)
        matches = tuple(
            pack
            for pack in self.packs
            if pack.pack_id == pack_id and (version is None or pack.version == version)
        )
        if not matches:
            return None
        return max(matches, key=lambda pack: _version_key(pack.version))

    def select(
        self,
        domain: str,
        *,
        required_capabilities: tuple[str, ...] = (),
        required_targets: tuple[str, ...] = (),
    ) -> SolutionPack | None:
        """Select the newest exact-domain pack satisfying all capabilities and targets; never guess."""
        domain = _slug(domain, "domain query")
        required = frozenset(
            _slug_tuple(required_capabilities, "required_capabilities", allow_empty=True)
        )
        targets = frozenset(
            _slug_tuple(required_targets, "required_targets", allow_empty=True)
        )
        matches = [
            pack
            for pack in self.packs
            if (
                domain in pack.domains
                and required <= set(pack.capabilities)
                and targets <= set(pack.targets)
            )
        ]
        if not matches:
            return None
        return sorted(
            matches,
            key=lambda pack: (
                tuple(-part for part in _version_key(pack.version)),
                len(set(pack.capabilities) - required),
                pack.pack_id,
            ),
        )[0]

    def recommend(
        self,
        domain: str,
        *,
        required_capabilities: tuple[str, ...] = (),
        required_targets: tuple[str, ...] = (),
    ) -> SolutionPackRecommendation:
        """Return an immutable, transparent exact-match recommendation result."""
        domain = _slug(domain, "domain query")
        capabilities = tuple(
            sorted(
                _slug_tuple(
                    required_capabilities,
                    "required_capabilities",
                    allow_empty=True,
                )
            )
        )
        targets = tuple(
            sorted(_slug_tuple(required_targets, "required_targets", allow_empty=True))
        )
        selection = self.select(
            domain,
            required_capabilities=capabilities,
            required_targets=targets,
        )
        return SolutionPackRecommendation(
            domain=domain,
            required_capabilities=capabilities,
            required_targets=targets,
            selection=selection,
        )

    def load_ir(self, pack_id: str, version: str | None = None) -> ApplicationIR:
        """Load and revalidate a fresh IR instance for a registered pack."""
        pack = self.get(pack_id, version)
        if pack is None:
            suffix = "" if version is None else f"@{version}"
            raise SolutionPackError(f"unknown Solution Pack {pack_id}{suffix}")
        return _load_and_validate(pack)

    def to_dict(self) -> dict[str, object]:
        return {"packs": [pack.to_dict() for pack in self.packs]}


MINIMAL_BLOG_PACK = SolutionPack(
    pack_id="minimal-blog",
    version="1.0.0",
    display_name="Minimal Blog",
    description="Verified content-publishing baseline with authors, readers, posts, comments, and fixtures.",
    domains=("blog-cms", "content-publishing"),
    capabilities=(
        "admin-web",
        "comments",
        "content-publishing",
        "fixtures",
        "python-backend",
        "web",
    ),
    example_ir_ref="minimal-blog",
    ir_sha256="85d1275232bef36601ed13ffd614f7a98c5ec13399824800f4bcad348c2bba67",
    # R-541: the IR has always declared admin_strategy "nextjs"; until the admin adapter existed
    # the assembler dropped it, so the pin recorded two targets. The pack now assembles the
    # console its own IR asks for. The IR itself is unchanged (ir_sha256 still matches).
    targets=("nextjs-web", "nextjs-admin", "backend-python"),
)

RIDESHARE_FAVOURITES_PACK = SolutionPack(
    pack_id="rideshare-favourites",
    version="1.0.0",
    display_name="Rideshare Favourites",
    description="Verified marketplace baseline with a public driver catalog and authenticated favourites.",
    domains=("rideshare",),
    capabilities=(
        "authenticated-actions",
        "favourites",
        "go-backend",
        "marketplace",
        "web",
    ),
    example_ir_ref="rideshare-favourites",
    ir_sha256="1693cb999955fa2ea8210e054b001982abc493e782ee7ac2f49aec8356f932ff",
    targets=("nextjs-web", "backend-go"),
)

BASELINE_SOLUTION_PACKS = (MINIMAL_BLOG_PACK, RIDESHARE_FAVOURITES_PACK)
DEFAULT_SOLUTION_PACK_REGISTRY = SolutionPackRegistry(BASELINE_SOLUTION_PACKS)

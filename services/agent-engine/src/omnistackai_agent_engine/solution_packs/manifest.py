"""Pinned declarative Solution Pack customization manifests (R-436).

The manifest is intent metadata, not an executable patch. It deliberately has no file path, source-code,
command, secret-value, or raw-model-output field and this module never loads/applies a pack or calls a model.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum

from .registry import (
    DEFAULT_SOLUTION_PACK_REGISTRY,
    SolutionPackError,
    SolutionPackRecommendation,
    SolutionPackRegistry,
)

MANIFEST_SCHEMA_VERSION = "1.0"
MAX_MANIFEST_CHANGES = 32
MAX_ACCEPTANCE_CRITERIA = 8
MAX_SUMMARY_LENGTH = 240
MAX_CRITERION_LENGTH = 240

_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_SEMVER = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SEMANTIC_TARGET = re.compile(
    r"(?P<kind>project|entity|field|api|screen|design|capability):"
    r"(?P<name>[A-Za-z][A-Za-z0-9_.-]{0,119})\Z"
)
_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")


class ChangeSource(StrEnum):
    """Origin class for a declarative customization intent."""

    CONFIGURATION = "configuration"
    AI_DELTA = "ai-delta"


class ChangeOperation(StrEnum):
    """Bounded semantic operation; it is not an executable mutation instruction."""

    ADD = "add"
    UPDATE = "update"
    REMOVE = "remove"


class ChangeArea(StrEnum):
    """Architectural area addressed by a semantic change target."""

    PROJECT = "project"
    DATA_MODEL = "data-model"
    API = "api"
    SCREEN = "screen"
    DESIGN = "design"
    CAPABILITY = "capability"


_TARGET_KINDS: dict[ChangeArea, frozenset[str]] = {
    ChangeArea.PROJECT: frozenset({"project"}),
    ChangeArea.DATA_MODEL: frozenset({"entity", "field"}),
    ChangeArea.API: frozenset({"api"}),
    ChangeArea.SCREEN: frozenset({"screen"}),
    ChangeArea.DESIGN: frozenset({"design"}),
    ChangeArea.CAPABILITY: frozenset({"capability"}),
}

_ROOT_KEYS = frozenset({"schema_version", "base_pack", "query", "changes"})
_BASE_PACK_KEYS = frozenset({"pack_id", "version", "ir_sha256"})
_QUERY_KEYS = frozenset({"domain", "required_capabilities", "required_targets"})
_CHANGE_KEYS = frozenset(
    {
        "change_id",
        "source",
        "operation",
        "area",
        "target",
        "summary",
        "acceptance_criteria",
    }
)
_CONSTRUCTION_TOKEN = object()


def _slug(value: object, label: str) -> str:
    if not isinstance(value, str) or _SLUG.fullmatch(value) is None:
        raise SolutionPackError(f"{label} must be a lowercase hyphenated identifier")
    return value


def _slug_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise SolutionPackError(f"{label} must be a tuple of identifiers")
    checked = tuple(_slug(item, f"{label} item") for item in value)
    if len(set(checked)) != len(checked):
        raise SolutionPackError(f"{label} must not contain duplicates")
    if checked != tuple(sorted(checked)):
        raise SolutionPackError(f"{label} must be canonically sorted")
    return checked


def _bounded_line(value: object, label: str, *, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
        or _CONTROL_CHARACTER.search(value) is not None
    ):
        raise SolutionPackError(
            f"{label} must be trimmed, non-empty, control-free text of at most {maximum} characters"
        )
    return value


@dataclass(frozen=True, slots=True)
class SolutionPackChange:
    """One bounded semantic intent; it cannot carry executable content."""

    change_id: str
    source: ChangeSource
    operation: ChangeOperation
    area: ChangeArea
    target: str
    summary: str
    acceptance_criteria: tuple[str, ...]

    def __post_init__(self) -> None:
        _slug(self.change_id, "change_id")
        if not isinstance(self.source, ChangeSource):
            raise SolutionPackError("source must be a ChangeSource")
        if not isinstance(self.operation, ChangeOperation):
            raise SolutionPackError("operation must be a ChangeOperation")
        if not isinstance(self.area, ChangeArea):
            raise SolutionPackError("area must be a ChangeArea")
        if not isinstance(self.target, str):
            raise SolutionPackError("target must be a semantic target reference")
        target_match = _SEMANTIC_TARGET.fullmatch(self.target)
        if target_match is None:
            raise SolutionPackError("target must be a bounded semantic target reference")
        if target_match.group("kind") not in _TARGET_KINDS[self.area]:
            raise SolutionPackError(f"target kind is incompatible with {self.area.value} area")
        _bounded_line(self.summary, "summary", maximum=MAX_SUMMARY_LENGTH)
        if (
            not isinstance(self.acceptance_criteria, tuple)
            or not self.acceptance_criteria
            or len(self.acceptance_criteria) > MAX_ACCEPTANCE_CRITERIA
        ):
            raise SolutionPackError(
                f"acceptance_criteria must contain 1 to {MAX_ACCEPTANCE_CRITERIA} entries"
            )
        for criterion in self.acceptance_criteria:
            _bounded_line(
                criterion,
                "acceptance criterion",
                maximum=MAX_CRITERION_LENGTH,
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "change_id": self.change_id,
            "source": self.source.value,
            "operation": self.operation.value,
            "area": self.area.value,
            "target": self.target,
            "summary": self.summary,
            "acceptance_criteria": list(self.acceptance_criteria),
        }


@dataclass(frozen=True, slots=True, init=False)
class SolutionPackManifest:
    """Immutable exact pack pin plus canonical declarative change intents."""

    schema_version: str
    pack_id: str
    pack_version: str
    pack_ir_sha256: str
    domain: str
    required_capabilities: tuple[str, ...]
    required_targets: tuple[str, ...]
    changes: tuple[SolutionPackChange, ...]

    def __init__(
        self,
        *,
        schema_version: str,
        pack_id: str,
        pack_version: str,
        pack_ir_sha256: str,
        domain: str,
        required_capabilities: tuple[str, ...],
        required_targets: tuple[str, ...],
        changes: tuple[SolutionPackChange, ...],
        _token: object | None = None,
    ) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise SolutionPackError(
                "SolutionPackManifest must be created from a selected recommendation or strict JSON"
            )
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "pack_id", pack_id)
        object.__setattr__(self, "pack_version", pack_version)
        object.__setattr__(self, "pack_ir_sha256", pack_ir_sha256)
        object.__setattr__(self, "domain", domain)
        object.__setattr__(self, "required_capabilities", required_capabilities)
        object.__setattr__(self, "required_targets", required_targets)
        object.__setattr__(self, "changes", changes)
        self._validate_structure()

    def _validate_structure(self) -> None:
        if self.schema_version != MANIFEST_SCHEMA_VERSION:
            raise SolutionPackError(
                f"schema_version must be {MANIFEST_SCHEMA_VERSION!r}"
            )
        _slug(self.pack_id, "base pack_id")
        if not isinstance(self.pack_version, str) or _SEMVER.fullmatch(self.pack_version) is None:
            raise SolutionPackError("base pack version must use major.minor.patch semantic versioning")
        if (
            not isinstance(self.pack_ir_sha256, str)
            or _SHA256.fullmatch(self.pack_ir_sha256) is None
        ):
            raise SolutionPackError("base pack ir_sha256 must be a lowercase SHA-256 digest")
        _slug(self.domain, "query domain")
        _slug_tuple(self.required_capabilities, "query required_capabilities")
        _slug_tuple(self.required_targets, "query required_targets")
        if not isinstance(self.changes, tuple) or len(self.changes) > MAX_MANIFEST_CHANGES:
            raise SolutionPackError(
                f"manifest changes must be a tuple with at most {MAX_MANIFEST_CHANGES} entries"
            )
        if any(not isinstance(change, SolutionPackChange) for change in self.changes):
            raise SolutionPackError("manifest changes must contain SolutionPackChange values")
        change_ids = tuple(change.change_id for change in self.changes)
        if len(set(change_ids)) != len(change_ids):
            raise SolutionPackError("manifest changes must not contain duplicate change_id values")
        if change_ids != tuple(sorted(change_ids)):
            raise SolutionPackError("manifest changes must be canonically sorted by change_id")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "base_pack": {
                "pack_id": self.pack_id,
                "version": self.pack_version,
                "ir_sha256": self.pack_ir_sha256,
            },
            "query": {
                "domain": self.domain,
                "required_capabilities": list(self.required_capabilities),
                "required_targets": list(self.required_targets),
            },
            "changes": [change.to_dict() for change in self.changes],
        }

    def to_json(self) -> str:
        """Return a byte-stable canonical JSON representation."""
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )


def _new_manifest(
    *,
    pack_id: str,
    pack_version: str,
    pack_ir_sha256: str,
    domain: str,
    required_capabilities: tuple[str, ...],
    required_targets: tuple[str, ...],
    changes: tuple[SolutionPackChange, ...],
) -> SolutionPackManifest:
    return SolutionPackManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        pack_id=pack_id,
        pack_version=pack_version,
        pack_ir_sha256=pack_ir_sha256,
        domain=domain,
        required_capabilities=required_capabilities,
        required_targets=required_targets,
        changes=tuple(sorted(changes, key=lambda change: change.change_id)),
        _token=_CONSTRUCTION_TOKEN,
    )


def _validate_registered_pin(
    manifest: SolutionPackManifest,
    registry: SolutionPackRegistry,
) -> None:
    recommendation = registry.recommend(
        manifest.domain,
        required_capabilities=manifest.required_capabilities,
        required_targets=manifest.required_targets,
    )
    selection = recommendation.selection
    if selection is None or (
        selection.pack_id,
        selection.version,
        selection.ir_sha256,
    ) != (
        manifest.pack_id,
        manifest.pack_version,
        manifest.pack_ir_sha256,
    ):
        raise SolutionPackError(
            "manifest pin does not match the registry's exact recommendation for its query"
        )


def create_solution_pack_manifest(
    recommendation: SolutionPackRecommendation,
    *,
    changes: tuple[SolutionPackChange, ...] = (),
    registry: SolutionPackRegistry = DEFAULT_SOLUTION_PACK_REGISTRY,
) -> SolutionPackManifest:
    """Create a validated manifest above one exact selected recommendation."""
    if not isinstance(recommendation, SolutionPackRecommendation):
        raise SolutionPackError("recommendation must be a SolutionPackRecommendation")
    if recommendation.selection is None:
        raise SolutionPackError("a selected exact-compatible recommendation is required")
    if not isinstance(changes, tuple):
        raise SolutionPackError("changes must be a tuple")
    if any(not isinstance(change, SolutionPackChange) for change in changes):
        raise SolutionPackError("changes must contain SolutionPackChange values")
    selection = recommendation.selection
    manifest = _new_manifest(
        pack_id=selection.pack_id,
        pack_version=selection.version,
        pack_ir_sha256=selection.ir_sha256,
        domain=recommendation.domain,
        required_capabilities=recommendation.required_capabilities,
        required_targets=recommendation.required_targets,
        changes=changes,
    )
    _validate_registered_pin(manifest, registry)
    return manifest


def _exact_dict(value: object, label: str, keys: frozenset[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise SolutionPackError(f"{label} must contain exactly these keys: {sorted(keys)!r}")
    return value


def _string_list(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SolutionPackError(f"{label} must be a JSON array of strings")
    return tuple(value)


def _parse_change(value: object) -> SolutionPackChange:
    document = _exact_dict(value, "change", _CHANGE_KEYS)
    try:
        source = ChangeSource(document["source"])
        operation = ChangeOperation(document["operation"])
        area = ChangeArea(document["area"])
    except (TypeError, ValueError) as error:
        raise SolutionPackError("change source, operation, and area must use supported values") from error
    return SolutionPackChange(
        change_id=document["change_id"],  # type: ignore[arg-type]
        source=source,
        operation=operation,
        area=area,
        target=document["target"],  # type: ignore[arg-type]
        summary=document["summary"],  # type: ignore[arg-type]
        acceptance_criteria=_string_list(
            document["acceptance_criteria"],
            "change acceptance_criteria",
        ),
    )


def parse_solution_pack_manifest(
    document: str | dict[str, object],
    *,
    registry: SolutionPackRegistry = DEFAULT_SOLUTION_PACK_REGISTRY,
) -> SolutionPackManifest:
    """Strictly parse canonical manifest JSON and revalidate its registry recommendation pin."""
    if isinstance(document, str):
        try:
            decoded: object = json.loads(document)
        except (json.JSONDecodeError, UnicodeError) as error:
            raise SolutionPackError("manifest must be valid JSON") from error
    elif isinstance(document, dict):
        decoded = document
    else:
        raise SolutionPackError("manifest must be a JSON object or JSON object string")

    root = _exact_dict(decoded, "manifest", _ROOT_KEYS)
    base_pack = _exact_dict(root["base_pack"], "base_pack", _BASE_PACK_KEYS)
    query = _exact_dict(root["query"], "query", _QUERY_KEYS)
    raw_changes = root["changes"]
    if not isinstance(raw_changes, list):
        raise SolutionPackError("changes must be a JSON array")
    changes = tuple(_parse_change(change) for change in raw_changes)
    manifest = SolutionPackManifest(
        schema_version=root["schema_version"],  # type: ignore[arg-type]
        pack_id=base_pack["pack_id"],  # type: ignore[arg-type]
        pack_version=base_pack["version"],  # type: ignore[arg-type]
        pack_ir_sha256=base_pack["ir_sha256"],  # type: ignore[arg-type]
        domain=query["domain"],  # type: ignore[arg-type]
        required_capabilities=_string_list(
            query["required_capabilities"],
            "query required_capabilities",
        ),
        required_targets=_string_list(
            query["required_targets"],
            "query required_targets",
        ),
        changes=changes,
        _token=_CONSTRUCTION_TOKEN,
    )
    _validate_registered_pin(manifest, registry)
    return manifest

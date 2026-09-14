"""Deterministic allowlisted application of Solution Pack configuration (R-437)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace

from ..application_ir import ApplicationIR, ApplicationIRError, validate_ir
from ..application_ir.validate import has_errors
from .manifest import (
    ChangeArea,
    ChangeOperation,
    ChangeSource,
    SolutionPackManifest,
    validate_solution_pack_manifest,
)
from .registry import (
    DEFAULT_SOLUTION_PACK_REGISTRY,
    SolutionPackError,
    SolutionPackRegistry,
    canonical_ir_digest,
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SUPPORTED_PROJECT_TARGETS = frozenset({"project:name", "project:description"})


@dataclass(frozen=True, slots=True)
class SolutionPackApplicationResult:
    """A validated derived IR and transparent deterministic application provenance."""

    pack_id: str
    pack_version: str
    base_ir_sha256: str
    derived_ir_sha256: str
    applied_configuration_change_ids: tuple[str, ...]
    unapplied_ai_delta_change_ids: tuple[str, ...]
    ir: ApplicationIR

    def __post_init__(self) -> None:
        if not isinstance(self.pack_id, str) or not self.pack_id:
            raise SolutionPackError("application result pack_id must be non-empty text")
        if not isinstance(self.pack_version, str) or not self.pack_version:
            raise SolutionPackError("application result pack_version must be non-empty text")
        if (
            not isinstance(self.base_ir_sha256, str)
            or _SHA256.fullmatch(self.base_ir_sha256) is None
            or not isinstance(self.derived_ir_sha256, str)
            or _SHA256.fullmatch(self.derived_ir_sha256) is None
        ):
            raise SolutionPackError("application result digests must be lowercase SHA-256 values")
        if not isinstance(self.ir, ApplicationIR):
            raise SolutionPackError("application result ir must be an ApplicationIR")
        if canonical_ir_digest(self.ir) != self.derived_ir_sha256:
            raise SolutionPackError("application result derived IR digest does not match its IR")
        for label, change_ids in (
            ("applied configuration", self.applied_configuration_change_ids),
            ("unapplied AI delta", self.unapplied_ai_delta_change_ids),
        ):
            if (
                not isinstance(change_ids, tuple)
                or any(not isinstance(change_id, str) or not change_id for change_id in change_ids)
                or change_ids != tuple(sorted(change_ids))
                or len(set(change_ids)) != len(change_ids)
            ):
                raise SolutionPackError(f"{label} change ids must be a unique sorted tuple")
        if set(self.applied_configuration_change_ids) & set(
            self.unapplied_ai_delta_change_ids
        ):
            raise SolutionPackError("a change cannot be both applied and unapplied")

    def to_dict(self) -> dict[str, object]:
        return {
            "base_pack": {
                "pack_id": self.pack_id,
                "version": self.pack_version,
                "ir_sha256": self.base_ir_sha256,
            },
            "derived_ir_sha256": self.derived_ir_sha256,
            "applied_configuration_change_ids": list(
                self.applied_configuration_change_ids
            ),
            "unapplied_ai_delta_change_ids": list(
                self.unapplied_ai_delta_change_ids
            ),
            "derived_ir": self.ir.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )


def apply_solution_pack_manifest(
    manifest: SolutionPackManifest,
    *,
    registry: SolutionPackRegistry = DEFAULT_SOLUTION_PACK_REGISTRY,
) -> SolutionPackApplicationResult:
    """Apply the allowlisted configuration subset to a fresh exact-pinned pack IR."""
    validate_solution_pack_manifest(manifest, registry=registry)

    configuration_changes = tuple(
        change
        for change in manifest.changes
        if change.source is ChangeSource.CONFIGURATION
    )
    ai_delta_change_ids = tuple(
        change.change_id
        for change in manifest.changes
        if change.source is ChangeSource.AI_DELTA
    )

    seen_targets: set[str] = set()
    updates: dict[str, str] = {}
    for change in configuration_changes:
        if (
            change.operation is not ChangeOperation.UPDATE
            or change.area is not ChangeArea.PROJECT
            or change.target not in _SUPPORTED_PROJECT_TARGETS
        ):
            raise SolutionPackError(
                f"unsupported deterministic configuration change {change.change_id}: "
                f"{change.operation.value} {change.target}"
            )
        if change.target in seen_targets:
            raise SolutionPackError(
                f"duplicate deterministic configuration target {change.target}"
            )
        seen_targets.add(change.target)
        if change.desired_text is None:
            raise SolutionPackError(
                f"configuration change {change.change_id} requires explicit desired_text"
            )
        ir_field = "name" if change.target == "project:name" else "description"
        updates[ir_field] = change.desired_text

    base_ir = registry.load_ir(manifest.pack_id, manifest.pack_version)
    if canonical_ir_digest(base_ir) != manifest.pack_ir_sha256:
        raise SolutionPackError("loaded Solution Pack IR does not match the manifest pin")
    try:
        derived_ir = replace(base_ir, **updates) if updates else base_ir
    except ApplicationIRError as error:
        raise SolutionPackError("configuration produced an invalid Application IR") from error
    if has_errors(validate_ir(derived_ir)):
        raise SolutionPackError("configuration produced an invalid Application IR")

    return SolutionPackApplicationResult(
        pack_id=manifest.pack_id,
        pack_version=manifest.pack_version,
        base_ir_sha256=manifest.pack_ir_sha256,
        derived_ir_sha256=canonical_ir_digest(derived_ir),
        applied_configuration_change_ids=tuple(
            change.change_id for change in configuration_changes
        ),
        unapplied_ai_delta_change_ids=ai_delta_change_ids,
        ir=derived_ir,
    )

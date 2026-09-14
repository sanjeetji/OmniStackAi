"""Deterministic allowlisted application of Solution Pack configuration and AI deltas (R-437, R-439)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace

from ..application_ir import ApplicationIR, ApplicationIRError, validate_ir
from ..application_ir.validate import has_errors
from .ai_delta import AIDeltaProposal
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
    applied_ai_delta_change_ids: tuple[str, ...] = ()

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
            ("applied AI delta", self.applied_ai_delta_change_ids),
            ("unapplied AI delta", self.unapplied_ai_delta_change_ids),
        ):
            if (
                not isinstance(change_ids, tuple)
                or any(not isinstance(change_id, str) or not change_id for change_id in change_ids)
                or change_ids != tuple(sorted(change_ids))
                or len(set(change_ids)) != len(change_ids)
            ):
                raise SolutionPackError(f"{label} change ids must be a unique sorted tuple")

        applied_set = set(self.applied_configuration_change_ids) | set(
            self.applied_ai_delta_change_ids
        )
        if set(self.applied_configuration_change_ids) & set(
            self.applied_ai_delta_change_ids
        ):
            raise SolutionPackError(
                "a change cannot be both configuration and AI delta applied"
            )
        if applied_set & set(self.unapplied_ai_delta_change_ids):
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
            "applied_ai_delta_change_ids": list(
                self.applied_ai_delta_change_ids
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
    proposal: AIDeltaProposal | None = None,
    registry: SolutionPackRegistry = DEFAULT_SOLUTION_PACK_REGISTRY,
) -> SolutionPackApplicationResult:
    """Apply allowlisted configuration and validated AI deltas to a fresh exact-pinned pack IR."""
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

    applied_ai_delta_change_ids: tuple[str, ...] = ()
    unapplied_ai_delta_change_ids = ai_delta_change_ids
    proposed_entities: tuple = ()
    proposed_apis: tuple = ()
    proposed_screens: tuple = ()

    if proposal is not None:
        if not isinstance(proposal, AIDeltaProposal):
            raise SolutionPackError("proposal must be an AIDeltaProposal instance")
        if proposal.pack_id != manifest.pack_id:
            raise SolutionPackError(
                f"proposal pack_id '{proposal.pack_id}' does not match manifest pin '{manifest.pack_id}'"
            )
        if proposal.pack_version != manifest.pack_version:
            raise SolutionPackError(
                f"proposal pack_version '{proposal.pack_version}' does not match manifest pin '{manifest.pack_version}'"
            )
        if proposal.base_ir_sha256 != manifest.pack_ir_sha256:
            raise SolutionPackError(
                f"proposal base_ir_sha256 '{proposal.base_ir_sha256}' does not match manifest pin '{manifest.pack_ir_sha256}'"
            )

        manifest_ai_ids = set(ai_delta_change_ids)
        addressed_ids = set(proposal.addressed_change_ids)
        unmapped = sorted(addressed_ids - manifest_ai_ids)
        if unmapped:
            raise SolutionPackError(
                f"proposal addresses unknown AI-delta change ids: {unmapped}"
            )

        applied_ai_delta_change_ids = proposal.addressed_change_ids
        unapplied_ai_delta_change_ids = tuple(
            cid for cid in ai_delta_change_ids if cid not in addressed_ids
        )

        base_entity_names = {e.name for e in base_ir.entities}
        for entity in proposal.entities:
            if entity.name in base_entity_names:
                raise SolutionPackError(
                    f"proposed entity '{entity.name}' collides with base IR entity"
                )

        base_api_endpoints = {(api.method, api.path) for api in base_ir.apis}
        for api in proposal.apis:
            if (api.method, api.path) in base_api_endpoints:
                raise SolutionPackError(
                    f"proposed API endpoint '{api.method.value} {api.path}' collides with base IR API"
                )

        base_screen_ids = {s.id for s in base_ir.screens}
        for screen in proposal.screens:
            if screen.id in base_screen_ids:
                raise SolutionPackError(
                    f"proposed screen '{screen.id}' collides with base IR screen"
                )

        all_entities = base_entity_names | {e.name for e in proposal.entities}
        for entity in proposal.entities:
            for relation in entity.relations:
                if relation.target_entity not in all_entities:
                    raise SolutionPackError(
                        f"proposed entity '{entity.name}' relation targets undeclared entity '{relation.target_entity}'"
                    )

        proposed_entities = proposal.entities
        proposed_apis = proposal.apis
        proposed_screens = proposal.screens

    new_entities = base_ir.entities + proposed_entities
    new_apis = base_ir.apis + proposed_apis
    new_screens = base_ir.screens + proposed_screens

    try:
        derived_ir = (
            replace(
                base_ir,
                entities=new_entities,
                apis=new_apis,
                screens=new_screens,
                **updates,
            )
            if (updates or proposal is not None)
            else base_ir
        )
    except ApplicationIRError as error:
        raise SolutionPackError("merged IR produced an invalid Application IR") from error

    if has_errors(validate_ir(derived_ir)):
        raise SolutionPackError("merged IR failed semantic validation")

    return SolutionPackApplicationResult(
        pack_id=manifest.pack_id,
        pack_version=manifest.pack_version,
        base_ir_sha256=manifest.pack_ir_sha256,
        derived_ir_sha256=canonical_ir_digest(derived_ir),
        applied_configuration_change_ids=tuple(
            change.change_id for change in configuration_changes
        ),
        unapplied_ai_delta_change_ids=unapplied_ai_delta_change_ids,
        ir=derived_ir,
        applied_ai_delta_change_ids=applied_ai_delta_change_ids,
    )

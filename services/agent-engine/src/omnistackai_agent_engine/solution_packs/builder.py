"""Verified project builder pipeline for Solution Packs (R-440).

Materializes a derived Solution Pack Application IR (from configuration and/or AI deltas)
into an owned, fully assembled monorepo Git repository, validated against its verify plans
and stamped with immutable provenance.

Pure disk/codegen/git work; 0 model calls, 0 network, 100% offline.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Sequence

from ..codegen import assemble_project
from ..git_service import create_repository
from ..verify import verify_plans_for_ir
from .ai_delta import AIDeltaProposal
from .application import SolutionPackApplicationResult, apply_solution_pack_manifest
from .manifest import SolutionPackManifest
from .registry import DEFAULT_SOLUTION_PACK_REGISTRY, SolutionPackError, SolutionPackRegistry


@dataclass(frozen=True)
class SolutionPackBuildResult:
    """Outcome of building a derived Solution Pack into an owned Git repository."""

    pack_id: str
    pack_version: str
    base_ir_sha256: str
    derived_ir_sha256: str
    applied_configuration_change_ids: tuple[str, ...]
    applied_ai_delta_change_ids: tuple[str, ...]
    unapplied_ai_delta_change_ids: tuple[str, ...]
    app_name: str
    target_dir: str
    file_count: int
    commit_sha: str
    verify_targets: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.pack_id or not self.pack_id.strip():
            raise SolutionPackError("pack_id must not be empty")
        if not self.pack_version or not self.pack_version.strip():
            raise SolutionPackError("pack_version must not be empty")
        if len(self.base_ir_sha256) != 64:
            raise SolutionPackError("base_ir_sha256 must be a 64-char hex SHA-256")
        if len(self.derived_ir_sha256) != 64:
            raise SolutionPackError("derived_ir_sha256 must be a 64-char hex SHA-256")
        if not self.target_dir or not self.target_dir.strip():
            raise SolutionPackError("target_dir must not be empty")
        if self.file_count < 0:
            raise SolutionPackError("file_count must be non-negative")
        if len(self.commit_sha) != 40:
            raise SolutionPackError("commit_sha must be a 40-char hex commit hash")

    def to_dict(self) -> dict[str, object]:
        return {
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "base_ir_sha256": self.base_ir_sha256,
            "derived_ir_sha256": self.derived_ir_sha256,
            "applied_configuration_change_ids": list(self.applied_configuration_change_ids),
            "applied_ai_delta_change_ids": list(self.applied_ai_delta_change_ids),
            "unapplied_ai_delta_change_ids": list(self.unapplied_ai_delta_change_ids),
            "app_name": self.app_name,
            "target_dir": self.target_dir,
            "file_count": self.file_count,
            "commit_sha": self.commit_sha,
            "verify_targets": list(self.verify_targets),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, sort_keys=True)


def build_solution_pack_project(
    source: SolutionPackApplicationResult | SolutionPackManifest,
    target_dir: str | os.PathLike[str],
    *,
    proposal: AIDeltaProposal | None = None,
    author_name: str,
    author_email: str,
    overwrite: bool = False,
    registry: SolutionPackRegistry = DEFAULT_SOLUTION_PACK_REGISTRY,
    provider: ModelProvider | None = None,
    prompt: str = "",
    model_id: str | None = None,
) -> SolutionPackBuildResult:
    """Assemble a derived Solution Pack Application IR into an owned Git repository.

    Accepts either an already-applied ``SolutionPackApplicationResult`` or a
    ``SolutionPackManifest`` (with optional ``proposal``). Applies manifest if needed,
    runs codegen, writes Git repository, checks verify targets, and returns
    provenance-stamped build result.
    """
    if isinstance(source, SolutionPackApplicationResult):
        app_result = source
    elif isinstance(source, SolutionPackManifest):
        app_result = apply_solution_pack_manifest(
            source,
            proposal=proposal,
            registry=registry,
        )
    else:
        raise SolutionPackError(
            f"Expected SolutionPackApplicationResult or SolutionPackManifest, got {type(source).__name__}"
        )

    project = assemble_project(
        app_result.ir,
        provider=provider,
        prompt=prompt,
        model_id=model_id,
    )
    repo = create_repository(
        project,
        target_dir,
        author_name=author_name,
        author_email=author_email,
        commit_message=f"Initial commit: {app_result.ir.name}",
        overwrite=overwrite,
    )

    plans = verify_plans_for_ir(app_result.ir)
    verify_targets = tuple(sorted({plan.target for plan in plans}))

    return SolutionPackBuildResult(
        pack_id=app_result.pack_id,
        pack_version=app_result.pack_version,
        base_ir_sha256=app_result.base_ir_sha256,
        derived_ir_sha256=app_result.derived_ir_sha256,
        applied_configuration_change_ids=app_result.applied_configuration_change_ids,
        applied_ai_delta_change_ids=app_result.applied_ai_delta_change_ids,
        unapplied_ai_delta_change_ids=app_result.unapplied_ai_delta_change_ids,
        app_name=app_result.ir.name,
        target_dir=repo.target_dir,
        file_count=repo.file_count,
        commit_sha=repo.commit_sha,
        verify_targets=verify_targets,
    )

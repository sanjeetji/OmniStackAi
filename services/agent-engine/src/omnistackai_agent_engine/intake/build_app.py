"""Prompt -> generated app repo (R-417).

Brick 2 of the "chat -> create an app" front door: chain the R-416 intake agent into
the existing assembler + git service so a single plain-English description becomes a
real, customer-owned Git repository.

    prompt --generate_ir--> ApplicationIR --assemble_project--> GeneratedProject
           --create_repository--> owned Git repo on disk

``build_app_from_ir`` is pure disk work (no model); ``build_app_from_prompt`` adds the
single model step and depends only on the vendor-neutral ``ModelProvider`` protocol, so
`task verify` exercises it against an in-memory stub (0 model calls, 0 network).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ..application_ir import ApplicationIR
from ..codegen import assemble_project
from ..git_service import create_repository
from ..model_gateway import ModelProvider
from .nl_to_ir import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_TEMPLATE_EXAMPLE,
    DEFAULT_TIMEOUT_SECONDS,
    generate_ir,
)


@dataclass(frozen=True)
class AppBuildResult:
    """Outcome of compiling a description into a materialized, owned Git repository."""

    prompt: str
    ir: ApplicationIR
    target_dir: str
    file_count: int
    commit_sha: str


def build_app_from_ir(
    ir: ApplicationIR,
    target_dir: str | os.PathLike[str],
    *,
    author_name: str,
    author_email: str,
    prompt: str = "",
    overwrite: bool = False,
) -> AppBuildResult:
    """Assemble ``ir`` into a monorepo and materialize it as an owned Git repo at ``target_dir``."""
    project = assemble_project(ir)
    repo = create_repository(
        project,
        target_dir,
        author_name=author_name,
        author_email=author_email,
        commit_message=f"Initial commit: {ir.name}",
        overwrite=overwrite,
    )
    return AppBuildResult(
        prompt=prompt,
        ir=ir,
        target_dir=repo.target_dir,
        file_count=repo.file_count,
        commit_sha=repo.commit_sha,
    )


def app_build_result_to_dict(result: AppBuildResult, *, max_files: int = 500) -> dict:
    """A JSON-safe view of an AppBuildResult for the studio/API (no secrets)."""
    root = Path(result.target_dir)
    files: list[str] = []
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if ".git" in rel.parts:
                continue
            files.append(str(rel))
            if len(files) >= max_files:
                break
    return {
        "prompt": result.prompt,
        "name": result.ir.name,
        "description": result.ir.description,
        "entities": [entity.name for entity in result.ir.entities],
        "file_count": result.file_count,
        "target_dir": result.target_dir,
        "commit_sha": result.commit_sha,
        "files": files,
    }


async def build_app_from_prompt(
    prompt: str,
    provider: ModelProvider,
    target_dir: str | os.PathLike[str],
    *,
    model_id: str,
    author_name: str,
    author_email: str,
    example_name: str = DEFAULT_TEMPLATE_EXAMPLE,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    overwrite: bool = False,
) -> AppBuildResult:
    """Compile ``prompt`` into an IR via ``provider`` and materialize an owned Git repo.

    Raises IntakeResponseError (from the intake step) if the model output cannot be turned
    into a valid Application IR.
    """
    result = await generate_ir(
        prompt,
        provider,
        model_id=model_id,
        example_name=example_name,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
    )
    return build_app_from_ir(
        result.ir,
        target_dir,
        author_name=author_name,
        author_email=author_email,
        prompt=prompt,
        overwrite=overwrite,
    )

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
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from ..application_ir import ApplicationIR
from ..codegen import assemble_project
from ..git_service import create_repository
from ..model_gateway import ModelProvider
from .ecosystem_intent import detect_ecosystem_intent
from .nl_to_ir import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_TEMPLATE_EXAMPLE,
    DEFAULT_TIMEOUT_SECONDS,
    IntakeResult,
    generate_ir,
    generate_ir_stream,
)


@dataclass(frozen=True)
class AppBuildResult:
    """Outcome of compiling a description into a materialized, owned Git repository."""

    prompt: str
    ir: ApplicationIR
    target_dir: str
    file_count: int
    commit_sha: str
    context_truncated: bool = False
    active_skills: tuple[str, ...] = ()
    truncated_skills: tuple[str, ...] = ()
    #: R-555: set when the prompt named a second kind of user and the whole ecosystem was built.
    #: `ecosystem_reason` is shown to the user, because "you got four apps" needs a because.
    ecosystem_apps: tuple[str, ...] = ()
    ecosystem_reason: str = ""


def build_app_from_ir(
    ir: ApplicationIR,
    target_dir: str | os.PathLike[str],
    *,
    author_name: str,
    author_email: str,
    prompt: str = "",
    overwrite: bool = False,
    provider: ModelProvider | None = None,
    model_id: str | None = None,
    synthesize_screens: bool = False,
    ui_outcomes: list | None = None,
    context_truncated: bool = False,
    active_skills: tuple[str, ...] = (),
    truncated_skills: tuple[str, ...] = (),
) -> AppBuildResult:
    """Assemble ``ir`` into a monorepo and materialize it as an owned Git repo at ``target_dir``.

    ``synthesize_screens`` / ``ui_outcomes`` (R-465) opt the web target into model-written screens and
    collect the per-file outcome records; both are no-ops without a ``provider``.
    """
    project = assemble_project(
        ir,
        provider=provider,
        prompt=prompt,
        model_id=model_id,
        synthesize_screens=synthesize_screens,
        ui_outcomes=ui_outcomes,
    )
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
        context_truncated=context_truncated,
        active_skills=active_skills,
        truncated_skills=truncated_skills,
    )


def app_build_result_to_dict(
    result: AppBuildResult,
    *,
    max_files: int = 500,
    ui_outcomes: list | None = None,
    usage: dict | None = None,
) -> dict:
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
    payload = {
        "prompt": result.prompt,
        "name": result.ir.name,
        "description": result.ir.description,
        "entities": [entity.name for entity in result.ir.entities],
        "file_count": result.file_count,
        "target_dir": result.target_dir,
        "commit_sha": result.commit_sha,
        "files": files,
        "context_truncated": result.context_truncated,
        "active_skills": list(result.active_skills),
        "truncated_skills": list(result.truncated_skills),
    }
    if ui_outcomes:
        payload["ui_outcomes"] = [outcome.to_dict() for outcome in ui_outcomes]
    if usage is not None:
        payload["usage"] = usage
    return payload


def build_ecosystem_from_plan(
    plan,
    target_dir: str | os.PathLike[str],
    *,
    author_name: str,
    author_email: str,
    prompt: str = "",
    overwrite: bool = False,
    provider: ModelProvider | None = None,
    reason: str = "",
    context_truncated: bool = False,
    active_skills: tuple[str, ...] = (),
    truncated_skills: tuple[str, ...] = (),
) -> AppBuildResult:
    """Materialize a planned ecosystem as one owned Git repo (R-555).

    One repo rather than one per surface: the apps share a database, so splitting them would mean
    the courier could not see the customer's order. `ir` on the result is the union the shared
    backend was generated from — the thing that describes the whole product rather than one app.
    """
    from ..codegen.ecosystem_assembler import assemble_ecosystem, surface_directory, union_ir

    project = assemble_ecosystem(plan, provider=provider, prompt=prompt)
    shared = union_ir(plan)
    repo = create_repository(
        project,
        target_dir,
        author_name=author_name,
        author_email=author_email,
        commit_message=f"Initial commit: {shared.name}",
        overwrite=overwrite,
    )
    taken: set[str] = set()
    directories = []
    for app in plan.apps:
        directory = surface_directory(app.surface.kind, taken)
        taken.add(directory)
        directories.append(directory)
    return AppBuildResult(
        prompt=prompt,
        ir=shared,
        target_dir=repo.target_dir,
        file_count=repo.file_count,
        commit_sha=repo.commit_sha,
        context_truncated=context_truncated,
        active_skills=active_skills,
        truncated_skills=truncated_skills,
        ecosystem_apps=tuple(directories),
        ecosystem_reason=reason,
    )


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
    synthesize_screens: bool = False,
    ui_outcomes: list | None = None,
    context: dict | str | None = None,
) -> AppBuildResult:
    """Compile ``prompt`` into an IR via ``provider`` and materialize an owned Git repo.

    Raises IntakeResponseError (from the intake step) if the model output cannot be turned
    into a valid Application IR. ``synthesize_screens`` (R-465) additionally lets the same provider write
    every screen page (the overview page is always model-written when a provider is given).
    """
    # R-555: does this prompt want one app or a whole ecosystem? Decided from the prompt alone,
    # deterministically and offline — whether a build produces one app or four must not vary
    # between runs of the same sentence, and it is not a judgement for a small local model.
    intent = detect_ecosystem_intent(prompt)
    if intent.build_ecosystem:
        # Local import: `ecosystem` imports AppBuildResult from this module, so a top-level import
        # here would be a cycle.
        from .ecosystem import plan_ecosystem_from_prompt

        plan = plan_ecosystem_from_prompt(prompt, intent.option_id)
        if len(plan.apps) > 1:
            return build_ecosystem_from_plan(
                plan,
                target_dir,
                author_name=author_name,
                author_email=author_email,
                prompt=prompt,
                overwrite=overwrite,
                provider=provider,
                reason=intent.reason,
            )

    result = await generate_ir(
        prompt,
        provider,
        model_id=model_id,
        example_name=example_name,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        context=context,
    )
    return build_app_from_ir(
        result.ir,
        target_dir,
        author_name=author_name,
        author_email=author_email,
        prompt=prompt,
        overwrite=overwrite,
        provider=provider,
        model_id=model_id,
        synthesize_screens=synthesize_screens,
        ui_outcomes=ui_outcomes,
        context_truncated=result.context_truncated,
        active_skills=result.active_skills,
        truncated_skills=result.truncated_skills,
    )


async def build_app_from_prompt_stream(
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
    context: dict | str | None = None,
) -> AsyncIterator[str | AppBuildResult]:
    """Streaming twin of `build_app_from_prompt` (R-484): yields text deltas from the IR-generation
    call as they arrive, then does the existing `build_app_from_ir`'s pure-disk work (assemble +
    git commit — fast, not usefully streamable token-by-token) once the IR is complete, and yields
    the final `AppBuildResult`.
    """
    result: IntakeResult | None = None
    async for item in generate_ir_stream(
        prompt,
        provider,
        model_id=model_id,
        example_name=example_name,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        context=context,
    ):
        if isinstance(item, str):
            yield item
        else:
            result = item
    assert result is not None  # generate_ir_stream always yields exactly one IntakeResult last
    yield build_app_from_ir(
        result.ir,
        target_dir,
        author_name=author_name,
        author_email=author_email,
        prompt=prompt,
        overwrite=overwrite,
        context_truncated=result.context_truncated,
        active_skills=result.active_skills,
        truncated_skills=result.truncated_skills,
    )

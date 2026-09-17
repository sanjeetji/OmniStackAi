"""Compile-level repair for LLM-written UI files (R-466).

R-465's validator is string-level: a model-written page can pass import/brace/export checks and still fail
`tsc`. This module closes the loop with the real compiler:

    compile (capturing tsc) -> per-file errors -> feed each LLM-written file's errors back through R-465's
    `_repair_message` channel -> validate -> apply as a ProjectDiff -> recompile (bounded rounds) ->
    revert still-failing LLM files to their deterministic templates.

Only files the model wrote (`app/page.tsx`, `app/<screen>/page.tsx`) are ever rewritten; a deterministic
file with an error is reported, never touched. Opt-in (model + toolchain); `task verify` exercises it with
stub providers, fake runners and temp dirs only. Outcomes are JSON-safe and secret-free.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ..application_ir import ApplicationIR
from .llm_ui import (
    _MAX_ECHO_CHARS,
    MARKER_PREFIX,
    UiSynthesisOutcome,
    _Transcript,
    _finalize,
    _is_request_too_large,
    _reason_for,
    _repair_message,
    _resolve_target,
    _run_sync,
    _safe_message_text,
    build_screen_synthesis_prompt,
    build_ui_synthesis_prompt,
    clean_and_validate_jsx,
)
from .nextjs import (
    _overview_page,
    _screen_page,
    compact_grounding,
    summarize_components,
    summarize_data_layer,
    summarize_design_tokens,
)

if TYPE_CHECKING:
    from ..edit.diff import ProjectDiff
    from ..model_gateway.contracts import ModelProvider
    from ..verify.compile import CompileError, CompileReport, Runner

logger = logging.getLogger(__name__)

WEB_PREFIX = "apps/web/"
DEFAULT_MAX_ROUNDS = 2
DEFAULT_REPAIR_ATTEMPTS = 2
_MAX_ERRORS_IN_MESSAGE = 20


@dataclass(frozen=True, slots=True)
class LlmFileSpec:
    """One model-written file: its web-relative path, the exact grounded prompt, the template fallback, and
    the compact prompt used when a provider rejects the full request as too large."""

    path: str
    prompt: str
    fallback: str
    compact_prompt: str | None = None


def llm_file_specs(ir: ApplicationIR, user_prompt: str, *, synthesize_screens: bool = True) -> dict[str, LlmFileSpec]:
    """The files the hybrid engine lets the model write, with the same prompts and fallbacks R-465 used."""

    grounding = {
        "data_layer": summarize_data_layer(ir),
        "components": summarize_components(ir),
        "design_tokens": summarize_design_tokens(),
    }
    compact = compact_grounding(ir)
    specs = {
        "app/page.tsx": LlmFileSpec(
            "app/page.tsx",
            build_ui_synthesis_prompt(ir, user_prompt, **grounding),
            _overview_page(ir),
            build_ui_synthesis_prompt(ir, user_prompt, **compact),
        )
    }
    if synthesize_screens:
        for screen in ir.screens:
            path = f"app/{screen.id}/page.tsx"
            specs[path] = LlmFileSpec(
                path,
                build_screen_synthesis_prompt(screen, ir, user_prompt, **grounding),
                _screen_page(screen, ir),
                build_screen_synthesis_prompt(screen, ir, user_prompt, **compact),
            )
    return specs


def compile_errors_message(errors: tuple[CompileError, ...], *, max_errors: int = _MAX_ERRORS_IN_MESSAGE) -> str:
    """The compiler's diagnostics for one file, bounded, phrased for the corrective turn."""

    lines = [f"TypeScript reported {len(errors)} error(s) in this file:"]
    lines.extend(f"  {error.render()}" for error in errors[:max_errors])
    if len(errors) > max_errors:
        lines.append(f"  ... and {len(errors) - max_errors} more")
    lines.append(
        "Fix every error. Use only the listed hooks with exactly their signatures and only the listed "
        "components and exports; do not invent properties."
    )
    return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class CompileRepairReport:
    """What compile-and-repair did: every compile pass plus how each failing file was handled."""

    rounds: tuple[CompileReport, ...]
    repaired: tuple[str, ...]  # LLM-written files the model fixed (web-relative paths)
    reverted: tuple[str, ...]  # LLM-written files reverted to the deterministic template
    untouched_failures: tuple[str, ...]  # deterministic files with errors — reported, never rewritten
    final_ok: bool

    def to_dict(self) -> dict:
        return {
            "rounds": [report.to_dict() for report in self.rounds],
            "repaired": list(self.repaired),
            "reverted": list(self.reverted),
            "untouched_failures": list(self.untouched_failures),
            "final_ok": self.final_ok,
        }


async def _repair_one(
    *,
    path: str,
    content: str,
    errors: tuple[CompileError, ...],
    spec: LlmFileSpec,
    provider: ModelProvider,
    model_id: str | None,
    timeout_seconds: float,
    max_attempts: int,
    outcomes: list[UiSynthesisOutcome] | None,
) -> str:
    """Ask the model to fix one file given the compiler's errors; validate; template fallback. Never raises."""

    from ..model_gateway.contracts import GenerateRequest

    try:
        target, max_output = _resolve_target(provider, model_id)
    except Exception as err:  # noqa: BLE001 - never raise out of repair
        if outcomes is not None:
            outcomes.append(UiSynthesisOutcome(path, "deterministic", 0, "default", type(err).__name__))
        return spec.fallback

    attempts_allowed = max(1, int(max_attempts))
    # The transcript starts as a rejected attempt: the current file is the echo, the compiler's errors the
    # corrective turn. It shrinks like a synthesis transcript when a provider says the request is too large.
    transcript = _Transcript(spec.prompt, spec.compact_prompt)
    transcript.reject(
        _safe_message_text(content, _MAX_ECHO_CHARS), _repair_message(path, compile_errors_message(errors))
    )

    attempts = 0
    last_reason = ""
    for attempt in range(1, attempts_allowed + 1):
        attempts = attempt
        try:
            request = GenerateRequest(
                request_id=f"ui-repair-{uuid.uuid4().hex[:12]}",
                model=target,
                messages=transcript.messages(),
                max_output_tokens=max_output,
                timeout_seconds=timeout_seconds,
            )
            response = await asyncio.wait_for(provider.generate(request), timeout=timeout_seconds)
        except Exception as err:  # noqa: BLE001 - transport/provider errors never retry; fall back
            last_reason = _reason_for(err)
            shrunk = transcript.shrink() if _is_request_too_large(err) and attempt < attempts_allowed else None
            if shrunk is not None:
                logger.warning("Compile repair for %s: request too large (%s); %s and retrying", path, last_reason, shrunk)
                continue
            logger.warning("Compile repair for %s failed (%s); reverting to the template", path, last_reason)
            break
        raw = getattr(response, "text", None)
        if raw is None:
            raw = getattr(getattr(response, "message", None), "content", "") or ""
        valid, cleaned, reason = clean_and_validate_jsx(raw)
        if valid:
            tag = f"{MARKER_PREFIX} ({target.model_id}; compile-repair {attempt}/{attempts_allowed})\n"
            if outcomes is not None:
                outcomes.append(UiSynthesisOutcome(path, "llm", attempts, target.model_id, ""))
            logger.info("Compile-repaired %s on attempt %d", path, attempt)
            return _finalize(cleaned, tag)
        last_reason = reason
        if attempt < attempts_allowed:
            transcript.reject(_safe_message_text(raw, _MAX_ECHO_CHARS), _repair_message(path, reason))

    if outcomes is not None:
        outcomes.append(UiSynthesisOutcome(path, "deterministic", attempts, target.model_id, last_reason))
    return spec.fallback


async def repair_compiled_files(
    *,
    current: dict[str, str],
    errors_by_file: dict[str, tuple[CompileError, ...]],
    specs: dict[str, LlmFileSpec],
    provider: ModelProvider,
    model_id: str | None = None,
    timeout_seconds: float = 120.0,
    max_attempts: int = DEFAULT_REPAIR_ATTEMPTS,
    outcomes: list[UiSynthesisOutcome] | None = None,
) -> dict[str, str]:
    """New content for every LLM-written file that has compiler errors (model fix or template fallback).

    A path without a spec is a deterministic file and is skipped: never rewritten, no model call.
    """

    changes: dict[str, str] = {}
    for path, errors in errors_by_file.items():
        spec = specs.get(path)
        if spec is None or not errors:
            continue
        changes[path] = await _repair_one(
            path=path,
            content=current.get(path, ""),
            errors=errors,
            spec=spec,
            provider=provider,
            model_id=model_id,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            outcomes=outcomes,
        )
    return changes


def build_repair_diff(changes: dict[str, str], *, web_prefix: str = WEB_PREFIX) -> ProjectDiff:
    """A ProjectDiff of MODIFIED monorepo paths (`apps/web/<path>`) for `edit/apply_diff`."""

    from ..edit.diff import ChangeKind, FileChange, ProjectDiff
    from .files import GeneratedFile

    file_changes = tuple(
        FileChange(ChangeKind.MODIFIED, f"{web_prefix}{path}", GeneratedFile(f"{web_prefix}{path}", content))
        for path, content in sorted(changes.items())
    )
    return ProjectDiff(file_changes, ())


def _read_current(web_dir: Path, paths: dict[str, tuple[CompileError, ...]]) -> dict[str, str]:
    current: dict[str, str] = {}
    for path in paths:
        file = web_dir / path
        try:
            current[path] = file.read_text(encoding="utf-8") if file.is_file() else ""
        except OSError:
            current[path] = ""
    return current


async def compile_and_repair(
    *,
    repo_dir: str | os.PathLike[str],
    ir: ApplicationIR,
    user_prompt: str,
    provider: ModelProvider,
    model_id: str | None = None,
    synthesize_screens: bool = True,
    outcomes: list[UiSynthesisOutcome] | None = None,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    max_attempts: int = DEFAULT_REPAIR_ATTEMPTS,
    runner: Runner | None = None,
    timeout_seconds: float = 120.0,
    compile_timeout_seconds: float = 600.0,
    web_prefix: str = WEB_PREFIX,
) -> CompileRepairReport:
    """Compile the web app; repair LLM-written files with the model; recompile; revert what still fails.

    ``max_rounds`` repair rounds follow the first compile: every round but the last asks the model, the
    last reverts still-failing LLM files to their templates; each applied round is followed by a compile,
    so the final report reflects the files on disk. Deterministic files are never rewritten.
    """

    from ..edit.apply import apply_diff
    from ..verify.compile import compile_web_project

    web_dir = Path(repo_dir) / web_prefix.rstrip("/")
    specs = llm_file_specs(ir, user_prompt, synthesize_screens=synthesize_screens)
    rounds_allowed = max(1, int(max_rounds))
    repaired: set[str] = set()
    reverted: set[str] = set()
    untouched: set[str] = set()

    report = compile_web_project(web_dir, runner=runner, timeout_seconds=compile_timeout_seconds)
    rounds = [report]
    for round_index in range(1, rounds_allowed + 1):
        if report.ok:
            break
        by_file = report.errors_by_file()
        untouched.update(path for path in by_file if path not in specs)
        failing = {path: errors for path, errors in by_file.items() if path in specs}
        if not failing:
            break
        if round_index < rounds_allowed:
            changes = await repair_compiled_files(
                current=_read_current(web_dir, failing),
                errors_by_file=failing,
                specs=specs,
                provider=provider,
                model_id=model_id,
                timeout_seconds=timeout_seconds,
                max_attempts=max_attempts,
                outcomes=outcomes,
            )
        else:
            changes = {path: specs[path].fallback for path in failing}
            if outcomes is not None:
                for path, errors in failing.items():
                    outcomes.append(
                        UiSynthesisOutcome(path, "deterministic", 0, model_id or "default", f"tsc: {len(errors)} error(s)")
                    )
        for path, content in changes.items():
            if content == specs[path].fallback:
                repaired.discard(path)
                reverted.add(path)
            else:
                repaired.add(path)
        apply_diff(build_repair_diff(changes, web_prefix=web_prefix), repo_dir)
        report = compile_web_project(web_dir, runner=runner, timeout_seconds=compile_timeout_seconds)
        rounds.append(report)

    return CompileRepairReport(
        tuple(rounds), tuple(sorted(repaired)), tuple(sorted(reverted)), tuple(sorted(untouched)), report.ok
    )


def compile_and_repair_sync(**kwargs) -> CompileRepairReport:
    """Sync bridge for CLIs and the studio (see `llm_ui._run_sync`)."""

    return _run_sync(lambda: compile_and_repair(**kwargs))  # type: ignore[return-value]

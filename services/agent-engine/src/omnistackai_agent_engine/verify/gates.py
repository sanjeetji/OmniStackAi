"""Per-target verify-plan recipes, IR mapping, and the opt-in executor.

`verify_plan` builds the deterministic gate ladder for one target; `verify_plans_for_ir` returns the
plans for an IR's assembled monorepo apps (consistent with the assembler); `run_verify` is the opt-in
executor that actually runs a plan (fail-fast) and returns a structured report. The recipe table is the
single source of truth for "what it means for a generated target to be engineered-verifiable."
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from ..application_ir import ApplicationIR
from ..codegen.adapter import AdapterRegistry
from ..codegen.assembler import assembled_targets
from ..runtime.contracts import Command
from .errors import UnsupportedVerifyTargetError
from .plans import VerifyPlan, VerifyStep, VerifyStepKind

_K = VerifyStepKind

# target -> ordered ladder of (kind, label, program, args)
_RECIPES: dict[str, tuple[tuple[VerifyStepKind, str, str, tuple[str, ...]], ...]] = {
    "nextjs-web": (
        (_K.INSTALL, "install dependencies", "pnpm", ("install",)),
        (_K.TYPECHECK, "type-check", "pnpm", ("exec", "tsc", "--noEmit")),
        (_K.LINT, "lint", "pnpm", ("run", "lint")),
        (_K.BUILD, "production build", "pnpm", ("run", "build")),
    ),
    "nextjs-admin": (
        (_K.INSTALL, "install dependencies", "pnpm", ("install",)),
        (_K.TYPECHECK, "type-check", "pnpm", ("exec", "tsc", "--noEmit")),
        (_K.LINT, "lint", "pnpm", ("run", "lint")),
        (_K.BUILD, "production build", "pnpm", ("run", "build")),
    ),
    "backend-python": (
        (_K.INSTALL, "install dependencies", "pip", ("install", "-r", "requirements.txt")),
        (_K.TYPECHECK, "byte-compile", "python", ("-m", "compileall", "app")),
        (_K.TEST, "tests", "python", ("-m", "pytest", "-q")),
    ),
    "backend-go": (
        (_K.LINT, "vet", "go", ("vet", "./...")),
        (_K.TEST, "tests", "go", ("test", "./...")),
        (_K.BUILD, "build", "go", ("build", "./...")),
    ),
}


def supported_targets() -> tuple[str, ...]:
    """The targets that have a verify plan, sorted."""

    return tuple(sorted(_RECIPES))


def verify_plan(target: str, app_dir: str) -> VerifyPlan:
    """The deterministic gate ladder a generated `target` is engineered to pass."""

    try:
        recipe = _RECIPES[target]
    except KeyError as error:
        raise UnsupportedVerifyTargetError(
            f"no verify plan for target {target!r}; known: {', '.join(supported_targets())}"
        ) from error
    steps = tuple(VerifyStep(kind, label, Command(program, args)) for kind, label, program, args in recipe)
    return VerifyPlan(target=target, app_dir=app_dir, steps=steps)


def verify_plans_for_ir(ir: ApplicationIR, registry: AdapterRegistry | None = None) -> tuple[VerifyPlan, ...]:
    """Verify plans for every app the IR assembles, each bound to its monorepo directory."""

    plans: list[VerifyPlan] = []
    for app in assembled_targets(ir, registry):
        if app.target in _RECIPES:
            plans.append(verify_plan(app.target, app.directory))
    return tuple(plans)


@dataclass(frozen=True, slots=True)
class StepResult:
    step: VerifyStep
    returncode: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass(frozen=True, slots=True)
class VerifyReport:
    target: str
    app_dir: str
    results: tuple[StepResult, ...]

    @property
    def ok(self) -> bool:
        return all(result.ok for result in self.results)


def run_verify(plan: VerifyPlan) -> VerifyReport:
    """Execute a verify plan fail-fast on this machine (opt-in; needs the toolchain).

    Runs each step in the plan's app_dir and stops at the first non-zero exit. Never called by tests or
    `task verify`.
    """

    results: list[StepResult] = []
    for step in plan.steps:
        completed = subprocess.run(
            [step.command.program, *step.command.args], cwd=plan.app_dir, check=False
        )
        results.append(StepResult(step, completed.returncode))
        if completed.returncode != 0:
            break
    return VerifyReport(plan.target, plan.app_dir, tuple(results))

"""Verify-plan data model (Brief 26/27/77).

A *verify plan* is the ordered ladder of gate commands that the generated code for one target is
engineered to pass — install, typecheck, lint, test, build. It is pure, validated data (like the
runtime preview/deploy plans): the planning code never runs anything. The vetted `Command` primitive
is reused from `runtime.contracts` so every command is control-free by construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..runtime.contracts import Command
from .errors import VerifyError


class VerifyStepKind(StrEnum):
    """The engineering gate a step belongs to, in ladder order."""

    INSTALL = "install"
    TYPECHECK = "typecheck"
    LINT = "lint"
    TEST = "test"
    BUILD = "build"


_LADDER = {kind: index for index, kind in enumerate(VerifyStepKind)}


def _text(value: str, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise VerifyError(f"{name} must be a non-empty string within {maximum} characters")
    return value


@dataclass(frozen=True, slots=True)
class VerifyStep:
    """One gate: a labelled command classified by the ladder kind it satisfies."""

    kind: VerifyStepKind
    label: str
    command: Command

    def __post_init__(self) -> None:
        if not isinstance(self.kind, VerifyStepKind):
            raise VerifyError("step kind must be a VerifyStepKind")
        _text(self.label, "step label", 128)
        if not isinstance(self.command, Command):
            raise VerifyError("step command must be a Command")


@dataclass(frozen=True, slots=True)
class VerifyPlan:
    """The ordered gate ladder for one generated target, rooted at a project directory."""

    target: str
    app_dir: str
    steps: tuple[VerifyStep, ...]

    def __post_init__(self) -> None:
        _text(self.target, "target", 64)
        _text(self.app_dir, "app_dir", 400)
        if not isinstance(self.steps, tuple) or not self.steps or any(
            not isinstance(step, VerifyStep) for step in self.steps
        ):
            raise VerifyError("steps must be a non-empty tuple of VerifyStep")
        order = [_LADDER[step.kind] for step in self.steps]
        if order != sorted(order):
            raise VerifyError("steps must be ordered by gate ladder (install<typecheck<lint<test<build)")

    def gates(self) -> tuple[VerifyStepKind, ...]:
        """The distinct gate kinds present, in ladder order."""

        seen: list[VerifyStepKind] = []
        for step in self.steps:
            if step.kind not in seen:
                seen.append(step.kind)
        return tuple(seen)

    def display(self) -> str:
        lines = [f"Verify plan for '{self.target}' (run in {self.app_dir}):"]
        lines += [f"  [{step.kind.value}] {step.label}: {step.command.display()}" for step in self.steps]
        return "\n".join(lines)

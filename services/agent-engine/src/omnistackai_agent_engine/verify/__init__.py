"""Verifiable-engineering layer: per-target verify plans, IR mapping, and an opt-in executor."""

from .compile import (
    CompileError,
    CompileReport,
    compile_web_project,
    ensure_web_dependencies,
    parse_tsc_output,
)
from .errors import UnsupportedVerifyTargetError, VerifyError
from .gates import (
    StepResult,
    VerifyReport,
    run_verify,
    supported_targets,
    verify_plan,
    verify_plans_for_ir,
)
from .plans import VerifyPlan, VerifyStep, VerifyStepKind

__all__ = [
    "CompileError",
    "CompileReport",
    "StepResult",
    "UnsupportedVerifyTargetError",
    "VerifyError",
    "VerifyPlan",
    "VerifyReport",
    "VerifyStep",
    "VerifyStepKind",
    "compile_web_project",
    "ensure_web_dependencies",
    "parse_tsc_output",
    "run_verify",
    "supported_targets",
    "verify_plan",
    "verify_plans_for_ir",
]

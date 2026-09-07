"""Verifiable-engineering layer: per-target verify plans, IR mapping, and an opt-in executor."""

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
    "StepResult",
    "UnsupportedVerifyTargetError",
    "VerifyError",
    "VerifyPlan",
    "VerifyReport",
    "VerifyStep",
    "VerifyStepKind",
    "run_verify",
    "supported_targets",
    "verify_plan",
    "verify_plans_for_ir",
]

"""Intake: turn a plain-English app description into an Application IR.

The first brick of the OmniStackAI "chat -> create an app" front door.
"""

from .build_app import AppBuildResult, build_app_from_ir, build_app_from_prompt
from .errors import IntakeError, IntakeResponseError
from .nl_to_ir import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_TEMPLATE_EXAMPLE,
    DEFAULT_TIMEOUT_SECONDS,
    IntakeResult,
    build_intake_messages,
    generate_ir,
    parse_ir_response,
)

__all__ = [
    "IntakeError",
    "IntakeResponseError",
    "IntakeResult",
    "build_intake_messages",
    "parse_ir_response",
    "generate_ir",
    "AppBuildResult",
    "build_app_from_ir",
    "build_app_from_prompt",
    "DEFAULT_TEMPLATE_EXAMPLE",
    "DEFAULT_MAX_OUTPUT_TOKENS",
    "DEFAULT_TIMEOUT_SECONDS",
]

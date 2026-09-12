"""Intake: turn a plain-English app description into an Application IR.

The first brick of the OmniStackAI "chat -> create an app" front door.
"""

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
    "DEFAULT_TEMPLATE_EXAMPLE",
    "DEFAULT_MAX_OUTPUT_TOKENS",
    "DEFAULT_TIMEOUT_SECONDS",
]

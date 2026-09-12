"""Prompt -> Application IR intake agent (R-416).

The first brick of the OmniStackAI "chat -> create an app" front door: turn a
plain-English application description into a validated, normalized Application IR
(the framework-neutral spec the code generators already consume).

Design (so `task verify` stays offline and deterministic):
  * build_intake_messages(prompt) -> the (system, user) Message tuple. The system
    message teaches the schema BY EXAMPLE, embedding a real ``example_ir(...).to_dict()``
    so it can never drift from the actual IR schema.
  * parse_ir_response(text) -> ApplicationIR. Pure text -> IR: tolerates ```json fences
    and surrounding prose, injects the schema version when omitted, builds the IR via
    ``ApplicationIR.from_dict`` and normalizes it.
  * generate_ir(prompt, provider, ...) -> IntakeResult. The only I/O step; it depends
    solely on the vendor-neutral ``ModelProvider`` protocol, so tests inject an in-memory
    stub (0 model calls, 0 network). The live local-Ollama path is the opt-in
    ``omnistackai_agent_engine.intake.live_run`` module, excluded from static verify.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..application_ir import (
    ApplicationIR,
    Issue,
    Severity,
    has_errors,
    normalize_ir,
    validate_ir,
)
from ..application_ir.errors import ApplicationIRError
from ..application_ir.examples import example_ir
from ..application_ir.ir import IR_SCHEMA_VERSION, FieldType
from ..model_gateway import (
    ChatRole,
    GenerateRequest,
    Message,
    ModelProvider,
    ModelRef,
)
from .errors import IntakeError, IntakeResponseError

DEFAULT_TEMPLATE_EXAMPLE = "minimal-blog"
DEFAULT_MAX_OUTPUT_TOKENS = 2048
DEFAULT_TIMEOUT_SECONDS = 300.0
_REQUEST_ID = "r416-intake-nl-to-ir"


@dataclass(frozen=True)
class IntakeResult:
    """Outcome of compiling a natural-language prompt into an Application IR."""

    ir: ApplicationIR
    issues: tuple[Issue, ...]
    raw_text: str


def _system_instruction(example_name: str) -> str:
    template = json.dumps(example_ir(example_name).to_dict(), indent=2, sort_keys=True)
    field_types = ", ".join(t.value for t in FieldType)
    return (
        "You are the intake compiler for OmniStackAI, an AI app-generation platform.\n"
        "Convert the user's application description into a single Application IR JSON object.\n"
        "\n"
        "Rules:\n"
        "- Output ONLY one JSON object. No prose, no explanation, no markdown code fences.\n"
        f'- It MUST match the structure of the template below exactly, including "schema_version": '
        f"{IR_SCHEMA_VERSION}.\n"
        "- Use lower_snake_case identifiers for entity names, field names, roles, and screen ids.\n"
        "- Model the user's real domain: choose sensible entities, fields (each with a name and type),\n"
        "  relations, API endpoints, screens, and at least one acceptance criterion. Minimal but complete.\n"
        f"- Every field 'type' MUST be EXACTLY one of: {field_types}. Do NOT invent other types.\n"
        "  For a status/category/enum-like field use \"string\". For money use \"float\". For an id use \"uuid\".\n"
        "\n"
        "Template (copy this shape; replace the content with the user's domain):\n"
        f"{template}\n"
    )


def build_intake_messages(
    prompt: str, *, example_name: str = DEFAULT_TEMPLATE_EXAMPLE
) -> tuple[Message, ...]:
    """Build the (system, user) messages instructing a model to emit an Application IR."""
    cleaned = prompt.strip()
    if not cleaned:
        raise IntakeError("prompt must be a non-empty application description")
    user = (
        "Application description:\n"
        f"{cleaned}\n\n"
        "Return only the Application IR JSON object."
    )
    return (
        Message(ChatRole.SYSTEM, _system_instruction(example_name).strip()),
        Message(ChatRole.USER, user.strip()),
    )


def _extract_json_object(text: str) -> str:
    """Pull the outermost JSON object out of raw model text (fences/prose tolerated)."""
    stripped = text.strip()
    if not stripped:
        raise IntakeResponseError("model returned an empty response")
    if "```" in stripped:
        fence = stripped.find("```")
        newline = stripped.find("\n", fence)
        if newline != -1:
            close = stripped.find("```", newline)
            if close != -1:
                stripped = stripped[newline + 1 : close].strip()
    open_idx = stripped.find("{")
    close_idx = stripped.rfind("}")
    if open_idx == -1 or close_idx == -1 or close_idx < open_idx:
        raise IntakeResponseError("model response did not contain a JSON object")
    return stripped[open_idx : close_idx + 1]


def parse_ir_response(text: str) -> ApplicationIR:
    """Parse raw model text into a validated, normalized ApplicationIR.

    Raises IntakeResponseError when the text is not JSON or does not describe a
    structurally valid IR.
    """
    payload = _extract_json_object(text)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as error:
        raise IntakeResponseError(f"model response was not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise IntakeResponseError("model response JSON was not an object")
    data.setdefault("schema_version", IR_SCHEMA_VERSION)
    try:
        ir = ApplicationIR.from_dict(data)
    except (ApplicationIRError, ValueError, TypeError, KeyError) as error:
        raise IntakeResponseError(
            f"model response was not a valid Application IR: {error}"
        ) from error
    return normalize_ir(ir)


async def generate_ir(
    prompt: str,
    provider: ModelProvider,
    *,
    model_id: str,
    example_name: str = DEFAULT_TEMPLATE_EXAMPLE,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> IntakeResult:
    """Compile a natural-language prompt into a validated Application IR via ``provider``.

    Raises IntakeResponseError if the model output cannot be parsed into a structurally
    valid IR, or if the resulting IR fails semantic validation.
    """
    messages = build_intake_messages(prompt, example_name=example_name)
    request = GenerateRequest(
        _REQUEST_ID,
        ModelRef(provider.provider_id, model_id),
        messages,
        max_output_tokens,
        timeout_seconds,
    )
    response = await provider.generate(request)
    ir = parse_ir_response(response.text)
    issues = validate_ir(ir)
    if has_errors(issues):
        detail = "; ".join(
            f"{issue.location}: {issue.message}"
            for issue in issues
            if issue.severity is Severity.ERROR
        )
        raise IntakeResponseError(f"generated IR failed validation: {detail}")
    return IntakeResult(ir=ir, issues=issues, raw_text=response.text)

"""Tests for the Prompt -> Application IR intake agent (intake/nl_to_ir.py, R-416).

Fully deterministic and offline: generate_ir is exercised against an in-memory stub
ModelProvider, so 0 real model calls and 0 network I/O occur under `task verify`.
"""

from __future__ import annotations

import asyncio
import json
import unittest

from omnistackai_agent_engine.application_ir import (
    ApplicationIR,
    example_ir,
    has_errors,
    validate_ir,
)
from omnistackai_agent_engine.codegen import NextjsWebAdapter
from omnistackai_agent_engine.intake import (
    IntakeError,
    IntakeResponseError,
    IntakeResult,
    build_intake_messages,
    generate_ir,
    parse_ir_response,
)
from omnistackai_agent_engine.model_gateway import (
    ChatRole,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    TokenUsage,
)

# A canonical, structurally valid IR JSON payload, derived from a real example so it
# always matches the current schema without hand-maintenance.
VALID_IR_DICT = example_ir("minimal-blog").to_dict()
VALID_IR_JSON = json.dumps(VALID_IR_DICT)


class StubProvider:
    """In-memory ModelProvider returning a fixed text; records the requests it sees."""

    def __init__(self, text: str, *, provider_id: str = "ollama") -> None:
        self._text = text
        self._provider_id = provider_id
        self.requests: list[GenerateRequest] = []

    @property
    def provider_id(self) -> str:
        return self._provider_id

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        self.requests.append(request)
        return GenerateResponse(
            request.request_id,
            request.model,
            self._text,
            FinishReason.STOP,
            TokenUsage(12, 34),
            5,
        )


def _run(coro):
    return asyncio.run(coro)


class TestBuildIntakeMessages(unittest.TestCase):
    def test_system_and_user_roles(self) -> None:
        messages = build_intake_messages("Build a blog")
        self.assertEqual(len(messages), 2)
        self.assertIs(messages[0].role, ChatRole.SYSTEM)
        self.assertIs(messages[1].role, ChatRole.USER)

    def test_system_message_is_schema_by_example(self) -> None:
        messages = build_intake_messages("Build a blog")
        system = messages[0].content
        # The template embeds a real example IR shape, incl. the pinned schema version.
        self.assertIn('"schema_version": 1', system)
        self.assertIn('"entities"', system)
        self.assertIn("JSON", system)

    def test_user_message_carries_the_prompt(self) -> None:
        messages = build_intake_messages("Build a recipe box app")
        self.assertIn("Build a recipe box app", messages[1].content)

    def test_system_message_enumerates_valid_field_types(self) -> None:
        # Guides local models away from inventing field types (e.g. "enum").
        system = build_intake_messages("Build a blog")[0].content
        for field_type in ("string", "uuid", "datetime", "bool"):
            self.assertIn(field_type, system)
        self.assertIn("Do NOT invent", system)

    def test_empty_prompt_rejected(self) -> None:
        with self.assertRaises(IntakeError):
            build_intake_messages("   ")


class TestParseIrResponse(unittest.TestCase):
    def test_bare_json(self) -> None:
        ir = parse_ir_response(VALID_IR_JSON)
        self.assertIsInstance(ir, ApplicationIR)
        self.assertEqual(ir.name, VALID_IR_DICT["name"])
        self.assertEqual(len(ir.entities), len(VALID_IR_DICT["entities"]))

    def test_fenced_json_with_prose(self) -> None:
        wrapped = "Sure! Here is the IR:\n```json\n" + VALID_IR_JSON + "\n```\nHope that helps."
        ir = parse_ir_response(wrapped)
        self.assertEqual(ir.name, VALID_IR_DICT["name"])

    def test_json_with_surrounding_prose_no_fence(self) -> None:
        noisy = "Here you go: " + VALID_IR_JSON + " -- done"
        ir = parse_ir_response(noisy)
        self.assertEqual(ir.name, VALID_IR_DICT["name"])

    def test_schema_version_injected_when_missing(self) -> None:
        without_version = {k: v for k, v in VALID_IR_DICT.items() if k != "schema_version"}
        ir = parse_ir_response(json.dumps(without_version))
        self.assertEqual(ir.schema_version, 1)

    def test_non_json_rejected(self) -> None:
        with self.assertRaises(IntakeResponseError):
            parse_ir_response("I cannot help with that request.")

    def test_empty_rejected(self) -> None:
        with self.assertRaises(IntakeResponseError):
            parse_ir_response("   ")

    def test_valid_json_but_invalid_ir_rejected(self) -> None:
        with self.assertRaises(IntakeResponseError):
            parse_ir_response('{"name": "x"}')

    def test_result_is_normalized_and_valid(self) -> None:
        ir = parse_ir_response(VALID_IR_JSON)
        self.assertFalse(has_errors(validate_ir(ir)))


class TestGenerateIr(unittest.TestCase):
    def test_happy_path_returns_result(self) -> None:
        provider = StubProvider(VALID_IR_JSON)
        result = _run(generate_ir("Build a blog", provider, model_id="qwen2.5-coder:14b"))
        self.assertIsInstance(result, IntakeResult)
        self.assertEqual(result.ir.name, VALID_IR_DICT["name"])
        self.assertFalse(has_errors(result.issues))
        self.assertEqual(result.raw_text, VALID_IR_JSON)

    def test_request_shape(self) -> None:
        provider = StubProvider(VALID_IR_JSON)
        _run(generate_ir("Build a blog", provider, model_id="qwen2.5-coder:14b", max_output_tokens=1500))
        self.assertEqual(len(provider.requests), 1)
        request = provider.requests[0]
        self.assertEqual(request.model.provider_id, "ollama")
        self.assertEqual(request.model.model_id, "qwen2.5-coder:14b")
        self.assertEqual(request.max_output_tokens, 1500)
        self.assertEqual(request.messages[0].role, ChatRole.SYSTEM)
        self.assertGreaterEqual(len(request.messages), 2)

    def test_invalid_model_output_raises(self) -> None:
        provider = StubProvider("sorry, no JSON here")
        with self.assertRaises(IntakeResponseError):
            _run(generate_ir("Build a blog", provider, model_id="qwen2.5-coder:14b"))

    def test_result_ir_is_buildable_end_to_end(self) -> None:
        # The whole point: a prompt-derived IR flows straight into the code generators.
        provider = StubProvider(VALID_IR_JSON)
        result = _run(generate_ir("Build a blog", provider, model_id="qwen2.5-coder:14b"))
        project = NextjsWebAdapter().generate(result.ir)
        self.assertIsNotNone(project.get("app/page.tsx"))


class TestPackageExports(unittest.TestCase):
    def test_public_api(self) -> None:
        import omnistackai_agent_engine.intake as intake

        for name in (
            "build_intake_messages",
            "parse_ir_response",
            "generate_ir",
            "IntakeResult",
            "IntakeError",
            "IntakeResponseError",
        ):
            self.assertTrue(hasattr(intake, name), name)
        self.assertIn("generate_ir", intake.__all__)


if __name__ == "__main__":
    unittest.main()

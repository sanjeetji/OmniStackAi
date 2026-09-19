"""Tests for the Prompt -> Application IR intake agent (intake/nl_to_ir.py, R-416).

Fully deterministic and offline: generate_ir is exercised against an in-memory stub
ModelProvider, so 0 real model calls and 0 network I/O occur under `task verify`.
"""

from __future__ import annotations

import asyncio
import json
import unittest
from collections.abc import AsyncIterator

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
    generate_ir_stream,
    parse_ir_response,
)
from omnistackai_agent_engine.model_gateway import (
    ChatRole,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    StreamEvent,
    TokenUsage,
)

# A canonical, structurally valid IR JSON payload, derived from a real example so it
# always matches the current schema without hand-maintenance.
VALID_IR_DICT = example_ir("minimal-blog").to_dict()
VALID_IR_JSON = json.dumps(VALID_IR_DICT)


class StubProvider:
    """In-memory ModelProvider returning a fixed text; records the requests it sees."""

    def __init__(self, text: str, *, provider_id: str = "ollama", stream_chunk_size: int = 8) -> None:
        self._text = text
        self._provider_id = provider_id
        self._stream_chunk_size = stream_chunk_size
        self.requests: list[GenerateRequest] = []
        self.stream_requests: list[GenerateRequest] = []

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

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamEvent]:
        """R-484: yields `self._text` in several small deltas (not all at once) - a real,
        in-memory stand-in for a provider's real token-by-token streaming, so
        `generate_ir_stream`'s own accumulation logic is genuinely exercised, not just handed one
        big chunk that happens to equal the non-streaming case."""
        self.stream_requests.append(request)
        size = max(1, self._stream_chunk_size)
        chunks = [self._text[i : i + size] for i in range(0, len(self._text), size)] or [""]
        for sequence, chunk in enumerate(chunks):
            is_last = sequence == len(chunks) - 1
            yield StreamEvent(
                request.request_id,
                sequence,
                chunk,
                is_last,
                TokenUsage(12, 34) if is_last else None,
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

    def test_reactive_native_normalized(self) -> None:
        payload = dict(VALID_IR_DICT)
        payload["project_strategy"] = dict(payload["project_strategy"])
        payload["project_strategy"]["mobile_profile"] = "reactive native"
        payload["project_strategy"]["admin_strategy"] = "reactive native"
        ir = parse_ir_response(json.dumps(payload))
        from omnistackai_agent_engine.application_ir.ir import AdminStrategy, MobileProfile

        self.assertEqual(ir.project_strategy.mobile_profile, MobileProfile.REACT_NATIVE)
        self.assertEqual(ir.project_strategy.admin_strategy, AdminStrategy.NEXTJS)

    def test_missing_strategy_keys_defaulted(self) -> None:
        payload = dict(VALID_IR_DICT)
        payload["project_strategy"] = {"mobile_profile": "react-native"}
        ir = parse_ir_response(json.dumps(payload))
        from omnistackai_agent_engine.application_ir.ir import MobileProfile

        self.assertEqual(ir.project_strategy.mobile_profile, MobileProfile.REACT_NATIVE)
        self.assertEqual(ir.project_strategy.web_strategy.value, "nextjs")

    def test_syntax_faults_and_missing_commas_repaired(self) -> None:
        raw = VALID_IR_JSON.replace('"name": "Minimal Blog",', '"name": "Minimal Blog"\n')
        raw = raw.replace('"version": 1,', '"version": 1,\n// inline comment\n')
        ir = parse_ir_response(raw)
        self.assertEqual(ir.name, "Minimal Blog")

    def test_unescaped_quotes_and_newlines_repaired(self) -> None:
        payload = dict(VALID_IR_DICT)
        payload["description"] = 'A "cool" store with\nmultiple lines'
        # Emulate raw JSON with unescaped quote and unescaped newline
        raw = json.dumps(payload).replace('\\"cool\\"', '"cool"').replace('\\n', '\n')
        ir = parse_ir_response(raw)
        self.assertIn("cool", ir.description)


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


class TestGenerateIrStream(unittest.TestCase):
    async def _collect(self, prompt: str, provider: StubProvider, **kwargs):
        deltas: list[str] = []
        result: IntakeResult | None = None
        async for item in generate_ir_stream(prompt, provider, **kwargs):
            if isinstance(item, str):
                deltas.append(item)
            else:
                result = item
        return deltas, result

    def test_happy_path_matches_non_streaming_result(self) -> None:
        stream_provider = StubProvider(VALID_IR_JSON)
        deltas, streamed = _run(
            self._collect("Build a blog", stream_provider, model_id="qwen2.5-coder:14b")
        )
        generate_provider = StubProvider(VALID_IR_JSON)
        direct = _run(generate_ir("Build a blog", generate_provider, model_id="qwen2.5-coder:14b"))

        self.assertIsInstance(streamed, IntakeResult)
        self.assertGreater(len(deltas), 1)
        self.assertEqual("".join(deltas), VALID_IR_JSON)
        self.assertEqual(streamed.raw_text, direct.raw_text)
        self.assertEqual(streamed.ir.name, direct.ir.name)
        self.assertFalse(has_errors(streamed.issues))

    def test_request_shape(self) -> None:
        provider = StubProvider(VALID_IR_JSON)
        _run(
            self._collect(
                "Build a blog", provider, model_id="qwen2.5-coder:14b", max_output_tokens=1500
            )
        )
        self.assertEqual(len(provider.stream_requests), 1)
        self.assertEqual(len(provider.requests), 0)
        request = provider.stream_requests[0]
        self.assertEqual(request.model.provider_id, "ollama")
        self.assertEqual(request.model.model_id, "qwen2.5-coder:14b")
        self.assertEqual(request.max_output_tokens, 1500)
        self.assertEqual(request.messages[0].role, ChatRole.SYSTEM)
        self.assertGreaterEqual(len(request.messages), 2)

    def test_invalid_model_output_raises(self) -> None:
        provider = StubProvider("sorry, no JSON here")
        with self.assertRaises(IntakeResponseError):
            _run(self._collect("Build a blog", provider, model_id="qwen2.5-coder:14b"))

    def test_result_ir_is_buildable_end_to_end(self) -> None:
        provider = StubProvider(VALID_IR_JSON)
        _deltas, result = _run(
            self._collect("Build a blog", provider, model_id="qwen2.5-coder:14b")
        )
        assert result is not None
        project = NextjsWebAdapter().generate(result.ir)
        self.assertIsNotNone(project.get("app/page.tsx"))


class TestPackageExports(unittest.TestCase):
    def test_public_api(self) -> None:
        import omnistackai_agent_engine.intake as intake

        for name in (
            "build_intake_messages",
            "parse_ir_response",
            "generate_ir",
            "generate_ir_stream",
            "IntakeResult",
            "IntakeError",
            "IntakeResponseError",
        ):
            self.assertTrue(hasattr(intake, name), name)
        self.assertIn("generate_ir", intake.__all__)
        self.assertIn("generate_ir_stream", intake.__all__)


if __name__ == "__main__":
    unittest.main()

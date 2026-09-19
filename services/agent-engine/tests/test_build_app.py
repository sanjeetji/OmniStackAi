"""Tests for prompt -> generated app repo (intake/build_app.py, R-417).

Deterministic and offline: build_app_from_prompt is exercised against an in-memory stub
ModelProvider (0 real model calls, 0 network); repo materialization uses the local git CLI
into a temporary directory, like the existing git_service tests.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import AsyncIterator
from pathlib import Path

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.intake import (
    AppBuildResult,
    app_build_result_to_dict,
    build_app_from_ir,
    build_app_from_prompt,
    build_app_from_prompt_stream,
)
from omnistackai_agent_engine.intake.errors import IntakeResponseError
from omnistackai_agent_engine.model_gateway import (
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    StreamEvent,
    TokenUsage,
)

VALID_IR_DICT = example_ir("minimal-blog").to_dict()
VALID_IR_JSON = json.dumps(VALID_IR_DICT)

AUTHOR = {"author_name": "sanjeetji", "author_email": "sk698166@gmail.com"}


class StubProvider:
    """In-memory ModelProvider returning a fixed text."""

    def __init__(self, text: str, *, provider_id: str = "ollama", stream_chunk_size: int = 8) -> None:
        self._text = text
        self._provider_id = provider_id
        self._stream_chunk_size = stream_chunk_size

    @property
    def provider_id(self) -> str:
        return self._provider_id

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        return GenerateResponse(
            request.request_id,
            request.model,
            self._text,
            FinishReason.STOP,
            TokenUsage(12, 34),
            5,
        )

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamEvent]:
        """R-484: yields `self._text` in several small deltas, mirroring the real
        ModelProvider.stream() shape, so build_app_from_prompt_stream's own accumulation is
        genuinely exercised (not handed one chunk equal to the non-streaming case)."""
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
    import asyncio

    return asyncio.run(coro)


class TestBuildAppFromIr(unittest.TestCase):
    def test_creates_owned_repo_on_disk(self) -> None:
        ir = example_ir("minimal-blog")
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "app")
            result = build_app_from_ir(ir, target, **AUTHOR)
            self.assertIsInstance(result, AppBuildResult)
            self.assertGreater(result.file_count, 0)
            self.assertTrue(Path(result.target_dir).is_dir())
            self.assertTrue((Path(result.target_dir) / ".git").is_dir())
            self.assertTrue(result.commit_sha)

    def test_writes_expected_web_and_backend_files(self) -> None:
        ir = example_ir("minimal-blog")
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "app")
            result = build_app_from_ir(ir, target, **AUTHOR)
            root = Path(result.target_dir)
            self.assertTrue((root / "apps/web/app/page.tsx").is_file())
            self.assertTrue((root / "services/api").is_dir())

    def test_commit_message_names_the_app(self) -> None:
        import subprocess

        ir = example_ir("minimal-blog")
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "app")
            result = build_app_from_ir(ir, target, **AUTHOR)
            subject = subprocess.run(
                ["git", "-C", result.target_dir, "log", "-1", "--pretty=%s"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            self.assertIn(ir.name, subject)


class TestBuildAppFromPrompt(unittest.TestCase):
    def test_prompt_to_repo_end_to_end(self) -> None:
        provider = StubProvider(VALID_IR_JSON)
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "app")
            result = _run(
                build_app_from_prompt(
                    "Build a simple blog",
                    provider,
                    target,
                    model_id="qwen2.5-coder:14b",
                    **AUTHOR,
                )
            )
            self.assertEqual(result.prompt, "Build a simple blog")
            self.assertEqual(result.ir.name, VALID_IR_DICT["name"])
            self.assertGreater(result.file_count, 0)
            self.assertTrue((Path(result.target_dir) / "apps/web/app/page.tsx").is_file())

    def test_result_carries_ir_and_prompt(self) -> None:
        provider = StubProvider(VALID_IR_JSON)
        with tempfile.TemporaryDirectory() as tmp:
            result = _run(
                build_app_from_prompt(
                    "Make a blog",
                    provider,
                    str(Path(tmp) / "app"),
                    model_id="qwen2.5-coder:14b",
                    **AUTHOR,
                )
            )
            self.assertEqual(result.prompt, "Make a blog")
            self.assertEqual(len(result.ir.entities), len(VALID_IR_DICT["entities"]))

    def test_invalid_model_output_raises_and_writes_nothing(self) -> None:
        provider = StubProvider("sorry, I cannot produce JSON")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "app"
            with self.assertRaises(IntakeResponseError):
                _run(
                    build_app_from_prompt(
                        "Build a blog",
                        provider,
                        str(target),
                        model_id="qwen2.5-coder:14b",
                        **AUTHOR,
                    )
                )
            self.assertFalse(target.exists())


class TestBuildAppFromPromptStream(unittest.TestCase):
    async def _collect(self, prompt: str, provider: StubProvider, target: str, **kwargs):
        deltas: list[str] = []
        result = None
        async for item in build_app_from_prompt_stream(prompt, provider, target, **kwargs):
            if isinstance(item, str):
                deltas.append(item)
            else:
                result = item
        return deltas, result

    def test_prompt_to_repo_end_to_end(self) -> None:
        provider = StubProvider(VALID_IR_JSON)
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "app")
            deltas, result = _run(
                self._collect(
                    "Build a simple blog",
                    provider,
                    target,
                    model_id="qwen2.5-coder:14b",
                    **AUTHOR,
                )
            )
            self.assertGreater(len(deltas), 1)
            self.assertEqual("".join(deltas), VALID_IR_JSON)
            self.assertIsInstance(result, AppBuildResult)
            self.assertEqual(result.prompt, "Build a simple blog")
            self.assertEqual(result.ir.name, VALID_IR_DICT["name"])
            self.assertGreater(result.file_count, 0)
            self.assertTrue((Path(result.target_dir) / "apps/web/app/page.tsx").is_file())

    def test_matches_non_streaming_result_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            streamed_target = str(Path(tmp) / "streamed")
            _deltas, streamed = _run(
                self._collect(
                    "Make a blog",
                    StubProvider(VALID_IR_JSON),
                    streamed_target,
                    model_id="qwen2.5-coder:14b",
                    **AUTHOR,
                )
            )
            direct = _run(
                build_app_from_prompt(
                    "Make a blog",
                    StubProvider(VALID_IR_JSON),
                    str(Path(tmp) / "direct"),
                    model_id="qwen2.5-coder:14b",
                    **AUTHOR,
                )
            )
            assert streamed is not None
            self.assertEqual(streamed.prompt, direct.prompt)
            self.assertEqual(streamed.ir.name, direct.ir.name)
            self.assertEqual(streamed.file_count, direct.file_count)

    def test_invalid_model_output_raises_and_writes_nothing(self) -> None:
        provider = StubProvider("sorry, I cannot produce JSON")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "app"
            with self.assertRaises(IntakeResponseError):
                _run(
                    self._collect(
                        "Build a blog",
                        provider,
                        str(target),
                        model_id="qwen2.5-coder:14b",
                        **AUTHOR,
                    )
                )
            self.assertFalse(target.exists())


class _FakeOutcome:
    """Stand-in for R-465's UiSynthesisOutcome -- only .to_dict() is required by the contract."""

    def __init__(self, path: str, mode: str) -> None:
        self._path, self._mode = path, mode

    def to_dict(self) -> dict:
        return {"path": self._path, "mode": self._mode, "attempts": 1, "model_id": "m", "last_reason": ""}


class TestAppBuildResultToDict(unittest.TestCase):
    def _result(self, tmp: str) -> AppBuildResult:
        ir = example_ir("minimal-blog")
        return build_app_from_ir(ir, str(Path(tmp) / "app"), **AUTHOR)

    def test_omitting_ui_outcomes_is_byte_for_byte_the_old_shape(self) -> None:
        # R-467: a regression guard -- every existing caller of app_build_result_to_dict must see the
        # exact same dict as before this parameter was added.
        with tempfile.TemporaryDirectory() as tmp:
            result = self._result(tmp)
            without_kwarg = app_build_result_to_dict(result)
            explicit_none = app_build_result_to_dict(result, ui_outcomes=None)
            explicit_empty = app_build_result_to_dict(result, ui_outcomes=[])
            self.assertEqual(without_kwarg, explicit_none)
            self.assertEqual(without_kwarg, explicit_empty)
            self.assertNotIn("ui_outcomes", without_kwarg)

    def test_ui_outcomes_are_included_when_given(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self._result(tmp)
            outcomes = [_FakeOutcome("app/page.tsx", "llm"), _FakeOutcome("app/posts/page.tsx", "deterministic")]
            payload = app_build_result_to_dict(result, ui_outcomes=outcomes)
            self.assertEqual(payload["ui_outcomes"], [o.to_dict() for o in outcomes])
            json.dumps(payload)

    def test_omitting_usage_is_byte_for_byte_the_old_shape(self) -> None:
        # R-472: the same additive-key regression guard R-467 established for ui_outcomes, applied
        # to the new usage key -- every existing caller must see an unchanged dict.
        with tempfile.TemporaryDirectory() as tmp:
            result = self._result(tmp)
            without_kwarg = app_build_result_to_dict(result)
            explicit_none = app_build_result_to_dict(result, usage=None)
            self.assertEqual(without_kwarg, explicit_none)
            self.assertNotIn("usage", without_kwarg)

    def test_usage_is_included_unchanged_when_given(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self._result(tmp)
            usage = {"total_calls": 2, "successful_calls": 1, "failed_calls": 1, "cost_micros_usd": 0}
            payload = app_build_result_to_dict(result, usage=usage)
            self.assertEqual(payload["usage"], usage)
            json.dumps(payload)


class TestPackageExports(unittest.TestCase):
    def test_public_api(self) -> None:
        import omnistackai_agent_engine.intake as intake

        for name in (
            "AppBuildResult",
            "build_app_from_ir",
            "build_app_from_prompt",
            "build_app_from_prompt_stream",
        ):
            self.assertTrue(hasattr(intake, name), name)
            self.assertIn(name, intake.__all__)


if __name__ == "__main__":
    unittest.main()

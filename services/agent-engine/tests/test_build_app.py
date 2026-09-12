"""Tests for prompt -> generated app repo (intake/build_app.py, R-417).

Deterministic and offline: build_app_from_prompt is exercised against an in-memory stub
ModelProvider (0 real model calls, 0 network); repo materialization uses the local git CLI
into a temporary directory, like the existing git_service tests.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.intake import (
    AppBuildResult,
    build_app_from_ir,
    build_app_from_prompt,
)
from omnistackai_agent_engine.intake.errors import IntakeResponseError
from omnistackai_agent_engine.model_gateway import (
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    TokenUsage,
)

VALID_IR_DICT = example_ir("minimal-blog").to_dict()
VALID_IR_JSON = json.dumps(VALID_IR_DICT)

AUTHOR = {"author_name": "sanjeetji", "author_email": "sk698166@gmail.com"}


class StubProvider:
    """In-memory ModelProvider returning a fixed text."""

    def __init__(self, text: str, *, provider_id: str = "ollama") -> None:
        self._text = text
        self._provider_id = provider_id

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


class TestPackageExports(unittest.TestCase):
    def test_public_api(self) -> None:
        import omnistackai_agent_engine.intake as intake

        for name in ("AppBuildResult", "build_app_from_ir", "build_app_from_prompt"):
            self.assertTrue(hasattr(intake, name), name)
            self.assertIn(name, intake.__all__)


if __name__ == "__main__":
    unittest.main()

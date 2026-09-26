"""PC-084: speed is measured on every build, and the console path stays fast and checked.

Measured live on 2026-09-26 through the real console:
* before: a 61 s build whose web app was never type-checked — the streaming path (the one the
  console uses) did not pass the provider, so every console build said "not type-checked";
* passing it naively made assembly model-written: 82 s of a 165 s build, and an admin page that
  did not compile;
* now: deterministic pages (about 1 s), the provider used only for checking and repair, and the
  mobile app type-checked from a shared Expo cache — about 45-55 s prompt to running app on Gemini,
  under the 90 s target. Every build records where its time went.
"""

import asyncio
import json
import os
import stat
import tempfile
import time
from pathlib import Path
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.application_ir.examples import EXAMPLES as _EXAMPLES

EXAMPLE_NAMES = tuple(_EXAMPLES)
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.intake.build_app import app_build_result_to_dict, build_app_from_prompt_stream
from omnistackai_agent_engine.intake.build_verify import MOBILE_NODE_MODULES_ENV, verify_other_surfaces
from omnistackai_agent_engine.model_gateway import FinishReason, GenerateResponse, StreamEvent, TokenUsage

PLAN = json.dumps(example_ir("minimal-blog").to_dict())


class _CountingProvider:
    """A provider that returns the plan and counts every call made to it."""

    provider_id = "fake"

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, request):
        self.calls += 1
        return GenerateResponse(request.request_id, request.model, PLAN, FinishReason.STOP, TokenUsage(1, 1), 1)

    async def stream(self, request):
        self.calls += 1
        yield StreamEvent(request.request_id, 0, PLAN, True)


def _stream_build(provider, target):
    async def run():
        result = None
        async for item in build_app_from_prompt_stream(
            "A tiny blog with posts and comments", provider, target,
            model_id="m", author_name="t", author_email="t@example.com", overwrite=True,
        ):
            if not isinstance(item, str):
                result = item
        return result

    return asyncio.run(run())


class TheConsolePathIsFastAndChecked(TestCase):
    def test_the_model_writes_the_plan_and_no_pages(self) -> None:
        provider = _CountingProvider()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"OMNISTACKAI_BUILD_VERIFY": "off"}):
            _stream_build(provider, f"{tmp}/repo")
        # One call: the plan. A model-written overview page would be a second call and ~80 s.
        self.assertEqual(provider.calls, 1)

    def test_the_provider_reaches_verification(self) -> None:
        seen = {}

        def fake_verify(**kwargs):
            seen.update(kwargs)
            return {"status": "clean"}

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("omnistackai_agent_engine.intake.build_app.verify_and_repair_build", side_effect=fake_verify):
            _stream_build(_CountingProvider(), f"{tmp}/repo")
        self.assertIsNotNone(seen.get("provider"), "the streaming path must pass the provider to verification")

    def test_every_build_records_where_its_time_went(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"OMNISTACKAI_BUILD_VERIFY": "off"}):
            result = _stream_build(_CountingProvider(), f"{tmp}/repo")
        self.assertEqual(set(result.timings), {"plan", "assemble", "repository", "verify"})
        self.assertIn("timings", app_build_result_to_dict(result))


class TheDeterministicStagesStayFast(TestCase):
    BUDGET_SECONDS = 10.0  # about 1 s today; the regression this guards against was 82 s

    def test_assembly_of_every_example(self) -> None:
        for name in EXAMPLE_NAMES:
            with self.subTest(example=name):
                started = time.perf_counter()
                assemble_project(example_ir(name))
                self.assertLess(time.perf_counter() - started, self.BUDGET_SECONDS)


class MobileAppsAreTypeChecked(TestCase):
    def _fake_cache(self, root: Path, deps: dict) -> Path:
        cache = root / "cache" / "node_modules"
        (cache / ".bin").mkdir(parents=True)
        tsc = cache / ".bin" / "tsc"
        tsc.write_text("#!/bin/sh\nexit 0\n")
        tsc.chmod(tsc.stat().st_mode | stat.S_IEXEC)
        (root / "cache" / "package.json").write_text(json.dumps({"dependencies": deps}))
        return cache

    def test_an_expo_app_is_checked_from_the_shared_cache_and_the_link_removed(self) -> None:
        deps = {"expo": "~51.0.0", "react": "18.2.0"}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = self._fake_cache(root, deps)
            app = root / "project" / "apps" / "courier"
            app.mkdir(parents=True)
            (app / "package.json").write_text(json.dumps({"dependencies": deps}))
            with mock.patch.dict(os.environ, {MOBILE_NODE_MODULES_ENV: str(cache)}):
                surfaces = verify_other_surfaces(root / "project")
            self.assertEqual(surfaces["apps/courier"]["status"], "clean")
            self.assertFalse((app / "node_modules").exists(), "the shared cache must not stay linked")

    def test_a_different_dependency_set_is_not_linked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = self._fake_cache(root, {"expo": "~51.0.0"})
            app = root / "project" / "apps" / "mobile"
            app.mkdir(parents=True)
            (app / "package.json").write_text(json.dumps({"dependencies": {"expo": "~52.0.0"}}))
            with mock.patch.dict(os.environ, {MOBILE_NODE_MODULES_ENV: str(cache)}):
                surfaces = verify_other_surfaces(root / "project")
            self.assertEqual(surfaces["apps/mobile"]["status"], "skipped")

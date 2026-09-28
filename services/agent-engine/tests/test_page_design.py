"""PC-098: model-designed pages after the build - bounded, checked, honest, and safe under edits.

Offline: the model is a stub and the compiler a fake runner. The live proof (a console build whose
pages are designed while the preview runs, billed, and kept through an edit) is in the CHANGELOG.
"""

import asyncio
import os
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.application_ir.ir import AdminStrategy
from omnistackai_agent_engine.codegen.llm_ui import MARKER_PREFIX
from omnistackai_agent_engine.intake.build_app import build_app_from_ir
from omnistackai_agent_engine.studio import page_design

_PAGE = '''"use client";
import { useListPosts } from "@/lib/hooks";

export default function Page() {
  const { items, loading } = useListPosts();
  return <main className="p-8">{loading ? "..." : items.length}</main>;
}
'''


class _Model:
    provider_id = "stub"

    def __init__(self, answers=None, fail=None):
        self.answers = list(answers or [])
        self.fail = fail
        self.calls = 0

    async def generate(self, request):  # noqa: ANN001
        self.calls += 1
        if self.fail is not None:
            raise self.fail
        return SimpleNamespace(text=self.answers.pop(0) if self.answers else _PAGE)


class _Tsc:
    """A fake compiler: clean unless told which page (app-relative) fails."""

    def __init__(self, failing: str | None = None):
        self.failing = failing
        self.calls = 0

    def __call__(self, argv, cwd, timeout_seconds):  # noqa: ANN001
        self.calls += 1
        if self.failing:
            return SimpleNamespace(returncode=2, stdout=f"{self.failing}(1,1): error TS2322: bad.\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")


def _ir():
    ir = example_ir("minimal-blog")
    return replace(ir, project_strategy=replace(ir.project_strategy, admin_strategy=AdminStrategy.NEXTJS))


def _project(tmp: str, *, with_tsc: bool = True):
    ir = _ir()
    build_app_from_ir(ir, tmp, author_name="t", author_email="t@t.t", prompt="a blog", overwrite=True)
    if with_tsc:  # what an installed app has; the fake runner stands in for running it
        for app in ("web", "admin"):
            tsc = Path(tmp, "apps", app, "node_modules", ".bin", "tsc")
            tsc.parent.mkdir(parents=True, exist_ok=True)
            tsc.write_text("")
    return ir


def _run(tmp, ir, model, **kwargs):
    async def go():
        return [event async for event in page_design.design_pages(tmp, ir, "a blog", model, **kwargs)]
    return asyncio.run(go())


class WhatGetsDesigned(TestCase):
    def test_home_pages_first_then_screens_and_never_more_than_the_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ir = _project(tmp)
            pages = [t.path for t in page_design.plan_pages(tmp, ir, limit=3)]
        self.assertEqual(pages[:2], ["apps/web/app/page.tsx", "apps/admin/app/page.tsx"])
        self.assertEqual(len(pages), 3)

    def test_a_designed_page_is_not_designed_again_unless_named(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ir = _project(tmp)
            home = Path(tmp, "apps/web/app/page.tsx")
            home.write_text(MARKER_PREFIX + " (m)\n" + _PAGE)
            self.assertNotIn("apps/web/app/page.tsx", [t.path for t in page_design.plan_pages(tmp, ir)])
            self.assertEqual([t.path for t in page_design.plan_pages(tmp, ir, only=["apps/web/app/page.tsx"])],
                             ["apps/web/app/page.tsx"])

    def test_it_can_be_turned_off(self) -> None:
        with mock.patch.dict(os.environ, {page_design.DESIGN_ENV: "off"}):
            self.assertFalse(page_design.design_enabled())
        self.assertTrue(page_design.design_enabled())


class EveryPageIsCheckedAndReported(TestCase):
    def test_pages_that_compile_are_designed_and_committed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ir = _project(tmp)
            tsc = _Tsc()
            events = _run(tmp, ir, _Model(), limit=2, runner=tsc)
            summary = events[-1]
            self.assertEqual((summary["designed"], summary["kept_template"]), (2, 0))
            self.assertIn(MARKER_PREFIX, Path(tmp, "apps/admin/app/page.tsx").read_text())
            self.assertEqual(tsc.calls, 2, "each app is compiled once")
            log = subprocess.run(["git", "log", "--oneline", "-1"], cwd=tmp, capture_output=True, text=True).stdout
            self.assertIn("model-designed pages", log)
            tracked = subprocess.run(["git", "ls-files"], cwd=tmp, capture_output=True, text=True).stdout
            self.assertNotIn("node_modules", tracked)

    def test_a_page_that_does_not_compile_goes_back_to_its_own_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ir = _project(tmp)
            before = Path(tmp, "apps/web/app/page.tsx").read_text()
            events = _run(tmp, ir, _Model(), limit=1, runner=_Tsc(failing="app/page.tsx"))
            self.assertEqual(Path(tmp, "apps/web/app/page.tsx").read_text(), before)
            final = [e for e in events if e.get("path") == "apps/web/app/page.tsx"][-1]
            self.assertEqual(final["status"], "kept_template")
            self.assertIn("did not compile", final["reason"])

    def test_a_page_nobody_could_type_check_is_not_left_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ir = _project(tmp, with_tsc=False)
            before = Path(tmp, "apps/web/app/page.tsx").read_text()
            with mock.patch.dict(os.environ, {"OMNISTACKAI_WEB_NODE_MODULES": ""}):
                events = _run(tmp, ir, _Model(), limit=1)
            self.assertEqual(Path(tmp, "apps/web/app/page.tsx").read_text(), before)
            self.assertIn("could not be type-checked", events[-1]["pages"]["apps/web/app/page.tsx"]["reason"])

    def test_a_failing_model_keeps_every_template_and_says_why(self) -> None:
        from omnistackai_agent_engine.model_gateway.errors import ProviderHTTPError

        with tempfile.TemporaryDirectory() as tmp:
            ir = _project(tmp)
            events = _run(tmp, ir, _Model(fail=ProviderHTTPError("too large", status_code=413)), limit=2, runner=_Tsc())
            summary = events[-1]
            self.assertEqual((summary["designed"], summary["kept_template"]), (0, 2))
            self.assertTrue(all("too large" in p["reason"] for p in summary["pages"].values()))

    def test_stopping_between_pages_is_honoured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ir = _project(tmp)
            model = _Model()
            _run(tmp, ir, model, limit=4, runner=_Tsc(), cancelled=lambda: True)
            self.assertEqual(model.calls, 0)


class EditsNeverThrowADesignedPageAway(TestCase):
    def test_an_edit_keeps_a_designed_page_and_names_it_for_redesign(self) -> None:
        from omnistackai_agent_engine.edit.diff import plan_edit
        from omnistackai_agent_engine.studio.live_serve import _keep_designed_pages

        with tempfile.TemporaryDirectory() as tmp:
            ir = _project(tmp)
            home = Path(tmp, "apps/web/app/page.tsx")
            home.write_text(MARKER_PREFIX + " (m)\n" + _PAGE)
            renamed = replace(ir, name="Minimal Blog Two")
            diff = plan_edit(ir, renamed)
            self.assertIn("apps/web/app/page.tsx", diff.modified())
            kept, redesign = _keep_designed_pages(diff, tmp)
            self.assertNotIn("apps/web/app/page.tsx", kept.modified())
            self.assertEqual(redesign, ["apps/web/app/page.tsx"])
            self.assertTrue(set(diff.modified()) - {"apps/web/app/page.tsx"} <= set(kept.modified()))


class ThePageModelCanTakeThePage(TestCase):
    def test_page_writing_gets_a_page_sized_answer_through_the_billing_wrapper(self) -> None:
        from omnistackai_agent_engine.codegen.llm_ui import _resolve_target
        from omnistackai_agent_engine.intake.provider_resolution import resolve_page_provider_from_env
        from omnistackai_agent_engine.model_gateway.accounting import UsageLedger, price_book_from_env

        env = {"GOOGLE_API_KEY": "test-key", "OMNISTACKAI_PAGE_PROVIDER": "", "OMNISTACKAI_PAGE_MAX_OUTPUT_TOKENS": "12000"}
        with mock.patch.dict(os.environ, env):
            provider, model, budget, _ = resolve_page_provider_from_env(usage_ledger=UsageLedger(price_book_from_env()))
        self.assertEqual((provider.provider_id, budget), ("google-gemini", 12000))
        self.assertEqual(_resolve_target(provider, model)[1], 12000)

    def test_a_projects_own_provider_is_kept(self) -> None:
        from omnistackai_agent_engine.intake.provider_resolution import page_provider_choice

        self.assertEqual(page_provider_choice("openai"), "openai")

    def test_the_page_model_is_priced(self) -> None:
        from omnistackai_agent_engine.model_gateway.accounting import price_book_from_env
        from omnistackai_agent_engine.model_gateway.contracts import TokenUsage

        self.assertIsNotNone(price_book_from_env().cost_for("google-gemini", "gemini-3-flash-preview", TokenUsage(1, 1)))

    def test_the_build_estimate_includes_page_design(self) -> None:
        from omnistackai_agent_engine.studio import estimates

        self.assertIn("design", estimates.KINDS)
        design = estimates.estimate("design", "google-gemini", "gemini-3-flash-preview")
        self.assertGreater(design["cost_micros_high"], 0)


class RateLimitsAreWaitedOut(TestCase):
    """Found live: Gemini's free tier limits requests per minute; the provider's own ~30 s backoff
    gave 7 of 8 pages up. Page design runs after the build, so it waits the minute out."""

    def test_a_rate_limited_call_is_retried_after_a_wait(self) -> None:
        from omnistackai_agent_engine.model_gateway.errors import ProviderRateLimitedError

        slept = []

        class Flaky:
            provider_id = "stub"
            calls = 0

            async def generate(self, request):  # noqa: ANN001
                Flaky.calls += 1
                if Flaky.calls < 3:
                    raise ProviderRateLimitedError("slow down", status_code=429)
                return "ok"

        async def sleep(seconds):
            slept.append(seconds)

        patient = page_design.PatientProvider(Flaky(), waits=(20.0, 40.0, 60.0), sleep=sleep)
        self.assertEqual(asyncio.run(patient.generate(None)), "ok")
        self.assertEqual(slept, [20.0, 40.0])

    def test_it_gives_up_after_its_waits(self) -> None:
        from omnistackai_agent_engine.model_gateway.errors import ProviderRateLimitedError

        class Always:
            provider_id = "stub"

            async def generate(self, request):  # noqa: ANN001
                raise ProviderRateLimitedError("slow down", status_code=429)

        async def sleep(_seconds):
            return None

        with self.assertRaises(ProviderRateLimitedError):
            asyncio.run(page_design.PatientProvider(Always(), waits=(1.0,), sleep=sleep).generate(None))

    def test_home_pages_are_designed_before_any_screen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ir = _project(tmp)
            events = _run(tmp, ir, _Model(), limit=4, runner=_Tsc())
            written = [e["path"] for e in events if e.get("status") == "written"]
        self.assertEqual(written[:2], ["apps/web/app/page.tsx", "apps/admin/app/page.tsx"])


class TheStreamStaysOpenWhileItWaits(TestCase):
    """Found live: a design stream silent for 300 s was dropped by the console's HTTP client."""

    def test_heartbeats_are_sent_while_nothing_else_is(self) -> None:
        import threading
        import urllib.request

        from omnistackai_agent_engine.studio.server import create_studio_server

        async def slow_design(ws_id, **options):  # noqa: ANN001
            import time

            time.sleep(0.5)  # blocks, as real model calls and compiles do
            yield {"phase": "done", "designed": 0}

        with mock.patch.dict(os.environ, {"OMNISTACKAI_SSE_HEARTBEAT_SECONDS": "0.1"}):
            server = create_studio_server(lambda _p: {}, host="127.0.0.1", port=0, workspace_design_stream_fn=slow_design)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                request = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/api/workspaces/w1/design/stream",
                                                 data=b"{}", method="POST", headers={"Content-Type": "application/json"})
                body = urllib.request.urlopen(request, timeout=10).read().decode()
            finally:
                server.shutdown()
        self.assertIn('"heartbeat"', body)
        self.assertIn('"done"', body)


class ASpentLimitStopsTheRun(TestCase):
    def test_after_one_page_exhausts_the_limit_the_rest_are_not_tried(self) -> None:
        from omnistackai_agent_engine.model_gateway.errors import ProviderRateLimitedError

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {page_design.RATE_LIMIT_WAITS_ENV: "0"}):
            ir = _project(tmp)
            model = _Model(fail=ProviderRateLimitedError("slow down", status_code=429))
            events = _run(tmp, ir, model, limit=4, runner=_Tsc())
            summary = events[-1]
        self.assertEqual(summary["kept_template"], 4)
        self.assertTrue(all("used up for now" in p["reason"] for p in summary["pages"].values()))
        self.assertLessEqual(model.calls, 3, "only the first page asked the model")

    def test_a_daily_quota_is_not_waited_for(self) -> None:
        from omnistackai_agent_engine.model_gateway.errors import ProviderRateLimitedError

        slept = []

        class Daily:
            provider_id = "stub"

            async def generate(self, request):  # noqa: ANN001
                raise ProviderRateLimitedError('quotaId: "GenerateRequestsPerDayPerProjectPerModel-FreeTier"', status_code=429)

        async def sleep(seconds):
            slept.append(seconds)

        with self.assertRaises(ProviderRateLimitedError):
            asyncio.run(page_design.PatientProvider(Daily(), waits=(20.0,), sleep=sleep).generate(None))
        self.assertEqual(slept, [])


class AnotherProviderTakesOver(TestCase):
    """Found live: Gemini 3 Flash's free tier allows 20 requests a day."""

    def test_when_one_limit_is_spent_the_next_provider_answers_and_the_first_is_not_retried(self) -> None:
        from omnistackai_agent_engine.model_gateway.errors import ProviderRateLimitedError

        class Spent:
            provider_id = "first"
            calls = 0

            async def generate(self, request):  # noqa: ANN001
                Spent.calls += 1
                raise ProviderRateLimitedError("daily", status_code=429)

        class Fresh:
            provider_id = "second"
            models: list = []

            async def generate(self, request):  # noqa: ANN001
                Fresh.models.append(request.model.model_id)
                return "page"

        async def sleep(_s):
            return None

        from omnistackai_agent_engine.model_gateway.contracts import ChatRole, GenerateRequest, Message, ModelRef

        chain = page_design.ChainProvider([(Spent(), "m1"), (Fresh(), "m2")], waits=(1.0,), sleep=sleep)
        request = GenerateRequest("r", ModelRef("first", "m1"), (Message(ChatRole.USER, "hi"),), 64, 30)
        self.assertEqual(asyncio.run(chain.generate(request)), "page")
        self.assertEqual(asyncio.run(chain.generate(request)), "page")
        self.assertEqual(Fresh.models, ["m2", "m2"], "each request goes to the serving provider's own model")
        self.assertEqual(Spent.calls, 1, "a daily limit is not waited for, and the spent provider is not asked again")
        self.assertEqual(chain.served_by, ["second"])


class TheEditorTemplateCompiles(TestCase):
    """Found compiling a real project (PC-098): an editor screen with a detail screen closed its
    "View ..." link with a literal `)}}`, so `tsc` and `next build` failed on every such project."""

    def test_the_view_link_is_balanced_and_shows_a_link_not_an_id(self) -> None:
        from omnistackai_agent_engine.application_ir.ir import Screen
        from omnistackai_agent_engine.codegen.assembler import assemble_project

        ir = example_ir("minimal-blog")
        detail = Screen(id="post_detail", role="reader", components=("detail",), actions=("open",), navigation=())
        ir = replace(ir, screens=(*ir.screens, detail))
        page = next(f.content for f in assemble_project(ir).files() if f.path == "apps/web/app/post_editor/page.tsx")
        link = page[page.index("/post_detail?id="):]
        link = link[: link.index("</Link>") + 40]
        self.assertIn("</Link>\n          )}\n", link)
        self.assertNotIn(")}}", link)
        self.assertIn("{(lastSavedId", page)  # parenthesised in both the create-only and edit variants


class ARunEndsInsideItsTimeBudget(TestCase):
    """Found live: a slow model's run outlived the control plane's bound, so its bill never came."""

    def test_no_page_starts_after_the_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {page_design.TIME_BUDGET_ENV: "0"}):
            ir = _project(tmp)
            model = _Model()
            events = _run(tmp, ir, model, limit=3, runner=_Tsc())
        self.assertEqual(model.calls, 0)
        self.assertEqual(events[-1]["kept_template"], 3)
        self.assertTrue(all("used its time" in p["reason"] for p in events[-1]["pages"].values()))


class EachProviderOnItsOwnTerms(TestCase):
    def _request(self, max_out=16384):
        from omnistackai_agent_engine.model_gateway.contracts import ChatRole, GenerateRequest, Message, ModelRef

        return GenerateRequest("r", ModelRef("first", "m1"), (Message(ChatRole.USER, "hi"),), max_out, 30)

    def test_a_local_model_gets_its_own_answer_size_and_timeout(self) -> None:
        seen = []

        class Local:
            provider_id = "ollama-local"

            async def generate(self, request):  # noqa: ANN001
                seen.append((request.max_output_tokens, request.timeout_seconds))
                return "page"

        chain = page_design.ChainProvider([(Local(), "qwen", 900.0, 6144)], waits=())
        asyncio.run(chain.generate(self._request()))
        self.assertEqual(seen, [(6144, 900.0)])

    def test_any_provider_failure_moves_on_but_a_spent_budget_stops(self) -> None:
        from omnistackai_agent_engine.model_gateway.errors import BudgetExceededError, UnknownModelError

        class Gone:
            provider_id = "gone"

            async def generate(self, request):  # noqa: ANN001
                raise UnknownModelError("model retired")

        class Ok:
            provider_id = "ok"

            async def generate(self, request):  # noqa: ANN001
                return "page"

        class Broke:
            provider_id = "broke"

            async def generate(self, request):  # noqa: ANN001
                raise BudgetExceededError("budget spent")

        self.assertEqual(asyncio.run(page_design.ChainProvider([(Gone(), "a"), (Ok(), "b")], waits=()).generate(self._request())), "page")
        with self.assertRaises(BudgetExceededError):
            asyncio.run(page_design.ChainProvider([(Broke(), "a"), (Ok(), "b")], waits=()).generate(self._request()))

    def test_openrouter_is_used_with_free_models_only(self) -> None:
        from omnistackai_agent_engine.intake import provider_resolution as pr

        env = {pr.PAGE_CHAIN_ENV: "openrouter:some/paid-model,openrouter:qwen/qwen3.8-27b:free", "OPENROUTER_API_KEY": "k"}
        with mock.patch.dict(os.environ, env), mock.patch.object(pr, "is_ollama_ready", return_value=False):
            chain = pr.resolve_page_providers_from_env()
        self.assertEqual([m for _p, m, _o, _t in chain], ["qwen/qwen3.8-27b:free"])

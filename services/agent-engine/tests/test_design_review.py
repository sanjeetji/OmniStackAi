"""PC-130: every page is looked at, scored from its screenshots, and designed again when below the bar."""

import asyncio
import json
import struct
import tempfile
import zlib
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from omnistackai_agent_engine.model_gateway.contracts import ChatRole, GenerateRequest, Message, ModelRef
from omnistackai_agent_engine.studio import design_review


def _png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff")) + chunk(b"IEND", b"")


def _ui_check(root: Path, routes=("/", "/post_list", "/login")) -> Path:
    folder = root / "logs" / "ui-check"
    (folder / "shots").mkdir(parents=True)
    results = []
    for route in routes:
        for device in ("desktop", "phone"):
            name = f"web-{route.strip('/') or 'home'}-{device}.png"
            (folder / "shots" / name).write_bytes(_png())
            results.append({"app": "web", "route": route, "device": device, "shot": f"shots/{name}", "problems": []})
    (folder / "report.json").write_text(json.dumps({"results": results}))
    return folder


class _Seer:
    """A model that can see: scores by route."""

    provider_id = "google-gemini"

    def __init__(self, scores):
        self.scores, self.requests = scores, []

    async def generate(self, request):
        self.requests.append(request)
        route = "/" if "The page: / " in request.messages[0].content else "/post_list"
        score = self.scores[route]
        problems = [] if score >= 9 else [{"issue": "the badge overlaps the delete icon", "fix": "move the badge left"}]
        return SimpleNamespace(text=json.dumps({"score": score, "summary": f"route {route}", "problems": problems}))


class Images(TestCase):
    def test_a_message_can_carry_screenshots(self) -> None:
        message = Message(ChatRole.USER, "look", (_png(),))
        self.assertEqual(len(message.images), 1)
        for bad in ((b"GIF89a",), tuple(_png() for _ in range(9))):
            with self.subTest(bad=len(bad)), self.assertRaises(ValueError):
                Message(ChatRole.USER, "look", bad)

    def test_each_provider_gets_them_in_its_own_form(self) -> None:
        from omnistackai_agent_engine.model_gateway import cloud

        message = Message(ChatRole.USER, "look", (_png(),))
        self.assertEqual(cloud._openai_content(message)[1]["type"], "image_url")
        self.assertTrue(cloud._openai_content(message)[1]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertEqual(cloud._anthropic_content(message)[0]["source"]["media_type"], "image/png")
        self.assertEqual(cloud._gemini_parts(message)[1]["inline_data"]["mime_type"], "image/png")
        self.assertEqual(cloud._openai_content(Message(ChatRole.USER, "text only")), "text only", "unchanged without images")


class TheReview(TestCase):
    def test_reading_a_review(self) -> None:
        score, summary, problems = design_review.parse_review('Here: {"score": 6, "summary": "ok", "problems": [{"issue": "a", "fix": "b"}]}')
        self.assertEqual((score, summary, problems), (6.0, "ok", [{"issue": "a", "fix": "b"}]))
        for bad in ("no json", '{"score": 11}', '{"score": "x"}'):
            with self.subTest(bad=bad), self.assertRaises((ValueError, TypeError)):
                design_review.parse_review(bad)

    def test_every_screenshotted_page_but_the_sign_in_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pages = design_review.pages_to_review(_ui_check(Path(tmp)))
        self.assertEqual([(a, r, [p.name for p in s]) for a, r, s in pages], [
            ("web", "/", ["web-home-desktop.png", "web-home-phone.png"]),
            ("web", "/post_list", ["web-post_list-desktop.png", "web-post_list-phone.png"])])

    def test_both_screenshots_go_to_the_model(self) -> None:
        seer = _Seer({"/": 9, "/post_list": 5})

        async def go(folder):
            return [r async for r in design_review.review_pages(folder, "A blog", chain=[(seer, "gemini", 2048, 60.0)])]

        with tempfile.TemporaryDirectory() as tmp:
            reviews = asyncio.run(go(_ui_check(Path(tmp))))
        self.assertEqual([(r.route, r.score) for r in reviews], [("/", 9.0), ("/post_list", 5.0)])
        self.assertEqual(len(seer.requests[0].messages[0].images), 2)
        self.assertEqual(reviews[1].page_path, "apps/web/app/post_list/page.tsx")

    def test_no_model_that_can_see(self) -> None:
        async def go(folder):
            return [r async for r in design_review.review_pages(folder, "A blog", chain=[])]

        with tempfile.TemporaryDirectory() as tmp:
            reviews = asyncio.run(go(_ui_check(Path(tmp))))
        self.assertTrue(all(r.error == "no model that can see is configured" for r in reviews))


class ImprovingWhatIsBelowTheBar(TestCase):
    def test_a_low_page_is_designed_again_with_its_review(self) -> None:
        seen = {}

        async def fake_design(root, ir, prompt, provider, **kw):
            seen.update(kw)
            for path in kw["only"]:
                yield {"phase": "page", "path": path, "status": "designed"}
            yield {"phase": "summary", "designed": len(kw["only"])}

        async def go(repo):
            return [e async for e in design_review.review_and_improve(
                repo, None, "A blog", object(), page_model="m", chain=[(_Seer({"/": 9, "/post_list": 5}), "g", 2048, 60.0)])]

        with tempfile.TemporaryDirectory() as tmp, mock.patch("omnistackai_agent_engine.studio.page_design.design_pages", fake_design):
            root = Path(tmp)
            _ui_check(root)
            repo = root / "repo"
            for page in ("apps/web/app/page.tsx", "apps/web/app/post_list/page.tsx"):
                (repo / page).parent.mkdir(parents=True, exist_ok=True)
                (repo / page).write_text("export default function P() { return null }\n")
            events = asyncio.run(go(repo))
            saved = json.loads((root / "logs" / "design-review" / "review.json").read_text())
        self.assertEqual(seen["only"], ["apps/web/app/post_list/page.tsx"], "only the page below the bar")
        self.assertIn("the badge overlaps the delete icon -> move the badge left", seen["critiques"]["apps/web/app/post_list/page.tsx"])
        self.assertEqual(events[-1]["phase"], "summary")
        self.assertEqual((saved["mean"], saved["below_bar"], saved["improved"]),
                         (7.0, ["apps/web/app/post_list/page.tsx"], {"apps/web/app/post_list/page.tsx": "designed"}))

    def test_a_critique_reaches_the_page_writer(self) -> None:
        from omnistackai_agent_engine.application_ir import example_ir
        from omnistackai_agent_engine.studio import page_design

        prompts = []

        async def fake_write(target, ir, prompt, *a, **k):
            prompts.append(prompt)
            return None, "stopped here by the test"

        ir = example_ir("minimal-blog")
        target = page_design.PageTarget("apps/web", "web", f"app/{ir.screens[0].id}/page.tsx", ir.screens[0].id, ir)

        async def go(tmp):
            return [e async for e in page_design.design_pages(
                tmp, ir, "A blog", SimpleNamespace(provider_id="p", generate=None), only=[target.path],
                apps=[("apps/web", ir, "web")], critiques={target.path: "A design review scored it 5/10. Fix every point: - overlap"})]

        with mock.patch.object(page_design, "plan_pages", return_value=[target]), \
                mock.patch.object(page_design, "_write_page", fake_write), tempfile.TemporaryDirectory() as tmp:
            asyncio.run(go(tmp))
        self.assertTrue(prompts and prompts[0].startswith("A blog") and "Fix every point: - overlap" in prompts[0], prompts)


class TheBenchmarkScoresTheLooks(TestCase):
    def test_looks(self) -> None:
        from omnistackai_agent_engine.benchmark import run as bench
        from omnistackai_agent_engine.benchmark.cases import Case

        result = bench.CaseResult("blog", "A blog", ())
        result.apps, result.entities, result.verification = ["Blog"], [], {"status": "clean"}
        result.review = {"mean": 6.5}
        bench.finish(Case("blog", "A blog"), result)
        self.assertEqual(result.parts["looks"], 0.65)


class TheVisionChain(TestCase):
    def test_free_vision_models_follow_gemini(self) -> None:
        import os

        env = {"ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": "", "GOOGLE_API_KEY": "g", "OPENROUTER_API_KEY": "o",
               "OMNISTACKAI_VISION_CHAIN": ""}
        with mock.patch.dict(os.environ, env):
            chain = design_review.vision_chain()
        self.assertEqual([m for _p, m, _o, _t in chain], ["gemini-3.8-flash", "qwen/qwen3.8-27b:free", "google/gemma-4-31b-it:free"])
        with mock.patch.dict(os.environ, {**env, "OMNISTACKAI_VISION_CHAIN": "openrouter:some/vision:free"}):
            self.assertEqual([m for _p, m, _o, _t in design_review.vision_chain()], ["some/vision:free"])


class OnlyBetterIsKept(TestCase):
    """Found live: a redesign from its review did not always score higher. It is kept only if it does."""

    def _run(self, after_scores):
        rounds = {"n": 0}

        class Seer:
            provider_id = "openrouter"

            async def generate(self, request):
                content = request.messages[0].content
                route = "/" if "The page: / " in content else "/post_list"
                score = (after_scores if rounds["n"] else {"/": 5, "/post_list": 4})[route]
                return SimpleNamespace(text=json.dumps({"score": score, "summary": "s", "problems": [{"issue": "i", "fix": "f"}]}))

        async def fake_design(root, ir, prompt, provider, **kw):
            for path in kw["only"]:
                (Path(root) / path).write_text("// redesigned\n")
                yield {"phase": "page", "path": path, "status": "designed"}

        def rescreenshot():
            rounds["n"] += 1
            return {"status": "passed"}

        async def go(repo):
            return [e async for e in design_review.review_and_improve(
                repo, None, "A blog", object(), page_model="m", chain=[(Seer(), "q", 2048, 60.0)],
                rescreenshot=rescreenshot, sleep=lambda s: asyncio.sleep(0))]

        with tempfile.TemporaryDirectory() as tmp, mock.patch("omnistackai_agent_engine.studio.page_design.design_pages", fake_design):
            root = Path(tmp)
            _ui_check(root)
            repo = root / "repo"
            for page in ("apps/web/app/page.tsx", "apps/web/app/post_list/page.tsx"):
                (repo / page).parent.mkdir(parents=True, exist_ok=True)
                (repo / page).write_text("// original\n")
            events = asyncio.run(go(repo))
            files = {p: (repo / p).read_text() for p in ("apps/web/app/page.tsx", "apps/web/app/post_list/page.tsx")}
        return events, files

    def test_a_better_page_stays_a_worse_one_goes_back(self) -> None:
        events, files = self._run({"/": 8, "/post_list": 3})
        rescored = {e["path"]: e for e in events if e.get("phase") == "rescored"}
        self.assertEqual((rescored["apps/web/app/page.tsx"]["before"], rescored["apps/web/app/page.tsx"]["after"],
                          rescored["apps/web/app/page.tsx"]["kept"]), (5.0, 8.0, True))
        self.assertFalse(rescored["apps/web/app/post_list/page.tsx"]["kept"])
        self.assertEqual(files, {"apps/web/app/page.tsx": "// redesigned\n", "apps/web/app/post_list/page.tsx": "// original\n"})

    def test_a_rate_limited_review_is_tried_once_more(self) -> None:
        from omnistackai_agent_engine.model_gateway.errors import ProviderRateLimitedError

        calls = {"n": 0}
        pauses = []

        class Limited:
            provider_id = "openrouter"

            async def generate(self, request):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise ProviderRateLimitedError("slow down", status_code=429)
                return SimpleNamespace(text='{"score": 7, "summary": "ok", "problems": []}')

        async def pause(seconds):
            pauses.append(seconds)

        async def go(folder):
            return [r async for r in design_review.review_pages(folder, "A blog", chain=[(Limited(), "q", 2048, 60.0)], sleep=pause)]

        with tempfile.TemporaryDirectory() as tmp:
            reviews = asyncio.run(go(_ui_check(Path(tmp), routes=("/",))))
        self.assertEqual((reviews[0].score, reviews[0].error, pauses), (7.0, "", [30.0]))

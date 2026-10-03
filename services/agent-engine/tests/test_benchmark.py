"""PC-122: the benchmark scores what a build delivered, and says when a change made it worse."""

import asyncio
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import ApplicationIR
from omnistackai_agent_engine.benchmark import run as bench
from omnistackai_agent_engine.benchmark import score
from omnistackai_agent_engine.benchmark.cases import CASES, QUICK_IDS, Case, select

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"


def _ir() -> ApplicationIR:
    return ApplicationIR.from_dict(json.loads(FIXTURE.read_text()))


class TheCases(TestCase):
    def test_varied_and_unique(self) -> None:
        ids = [c.id for c in CASES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(CASES), 40)
        self.assertGreaterEqual(sum(1 for c in CASES if c.apps > 1), 5, "ecosystems as well as single apps")
        self.assertEqual({c.id for c in select("quick")}, set(QUICK_IDS))
        self.assertEqual([c.id for c in select(only=["blog", "crm"])], ["crm", "blog"])
        with self.assertRaises(ValueError):
            select(only=["nope"])


class TheScore(TestCase):
    def test_build(self) -> None:
        self.assertEqual(score.build_part(False, {}), 0.0)
        self.assertEqual(score.build_part(True, {"status": "clean"}), 1.0)
        self.assertEqual(score.build_part(True, {"status": "repaired", "surfaces": {"apps/web": {"status": "clean"}}}), 1.0)
        self.assertEqual(score.build_part(True, {"status": "failing", "surfaces": {"apps/web": {"status": "failing"}}}), 0.25)
        skipped = {"status": "skipped", "surfaces": {"services/api": {"status": "parsed"}, "apps/web": {"status": "skipped"}}}
        self.assertEqual(score.build_part(True, skipped), 0.5, "parsing is not type-checking (found in the first run)")
        mixed = {"status": "clean", "surfaces": {"services/api": {"status": "parsed"}, "apps/web": {"status": "clean"}}}
        self.assertEqual(score.build_part(True, mixed), 0.75)
        self.assertEqual(score.build_part(True, {"status": "skipped"}), 0.5, "not checked is not good")

    def test_complete(self) -> None:
        case = Case("x", "p", ("Customer", "Invoice"), ("money",), apps=1)
        part, missing = score.complete_part(case, ["Customer", "Order"], ["workflow"], 1)
        self.assertAlmostEqual(part, 2 / 4)
        self.assertEqual(missing, ["no Invoice", "no money building block"])
        eco = Case("y", "p", (), (), apps=3)
        self.assertEqual(score.complete_part(eco, [], [], 1)[1], ["1 app, expected 3 to 6"])
        self.assertEqual(score.complete_part(Case("b", "A blog"), [], [], 4)[1], ["4 apps, expected 1"])
        two_sided = Case("c", "patients and doctors", max_apps=3)
        self.assertEqual(score.complete_part(two_sided, [], [], 3)[1], [], "the platform decides the scope")

    def test_unmeasured_parts_are_left_out(self) -> None:
        self.assertEqual(score.total({"build": 1.0, "complete": 0.5, "pages": None}), 75.0)
        self.assertEqual(score.total({}), 0.0)

    def test_regressions(self) -> None:
        before = [{"id": "a", "score": 80.0}, {"id": "b", "score": 70.0}]
        now = [{"id": "a", "score": 65.0}, {"id": "b", "score": 72.0}, {"id": "c", "score": 50.0}]
        result = score.compare(now, before)
        self.assertEqual(result["regressions"], ["a: 80.0 -> 65.0"])
        self.assertEqual(result["changes"], {"a": -15.0, "b": 2.0})
        self.assertEqual((result["mean_before"], result["mean_now"]), (75.0, 68.5))
        self.assertFalse(score.compare(now, None)["baseline"])


class OneCase(TestCase):
    def test_list_endpoints_only(self) -> None:
        seen = []
        statuses = bench.call_list_endpoints("http://127.0.0.1:9/", _ir(), fetch=lambda u: seen.append(u) or 200)
        self.assertTrue(statuses and all(s == 200 for s in statuses.values()))
        self.assertFalse(any("{" in u for u in seen), "a path with an id needs a record; list endpoints only")

    def test_finish(self) -> None:
        case = Case("crm", "A CRM", ("Customer",), (), apps=1)
        result = bench.CaseResult("crm", "A CRM", ())
        result.apps, result.entities, result.verification = ["CRM"], ["Customer"], {"status": "clean"}
        result.endpoints = {"/customers": 200, "/orders": 500}
        result.ui = {"status": "failed", "page_views": 10, "failing": 2}
        result.design = {"designed": 3, "kept_template": 1}
        result.parts["runs"] = 1.0
        parts = bench.finish(case, result).parts
        self.assertEqual(parts, {"runs": 1.0, "build": 1.0, "complete": 1.0, "api": 0.5, "pages": 0.8, "designed": 0.75})
        self.assertEqual(result.score, 87.4, "PC-130 rebalanced the weights for 'looks'")

    def test_a_failed_build_scores_zero_where_it_counts(self) -> None:
        result = bench.CaseResult("blog", "A blog", ())
        result.errors.append("build: IntakeResponseError: no JSON")
        bench.finish(select(only=["blog"])[0], result)
        self.assertEqual(result.score, 0.0)

    def test_preview_measures_and_stops(self) -> None:
        stopped = []
        plan = SimpleNamespace(backend_kind="python", api_url="http://127.0.0.1:9", has_admin=True)
        session = SimpleNamespace(plan=plan, api_ready=True, web_ready=True, admin_ready=False, stop=lambda: stopped.append(1))
        result = bench.CaseResult("crm", "A CRM", ())
        result.repo = tempfile.mkdtemp() + "/repo"
        with mock.patch("omnistackai_agent_engine.localrun.ui_check.read_status",
                        return_value={"status": "passed", "page_views": 4, "failing": 0}):
            bench.preview_case(result, SimpleNamespace(ir=_ir()), log=lambda m: None,
                               start=lambda *a, **k: session, fetch=lambda u: 200)
        self.assertEqual(result.parts["runs"], 2 / 3, "the admin app did not come up")
        self.assertEqual(result.ui["status"], "passed")
        self.assertEqual(stopped, [1])

    def test_a_preview_that_fails_to_start(self) -> None:
        result = bench.CaseResult("crm", "A CRM", ())

        def boom(*a, log_callback, **k):
            log_callback("api: ModuleNotFoundError: No module named 'app.jobs'\n")
            raise RuntimeError("port in use")

        with tempfile.TemporaryDirectory() as tmp:
            result.repo = str(Path(tmp) / "crm" / "repo")
            bench.preview_case(result, SimpleNamespace(ir=_ir()), log=lambda m: None, start=boom)
            saved = (Path(tmp) / "crm" / "logs" / "app.log").read_text()
        self.assertEqual(result.parts["runs"], 0.0)
        self.assertTrue(result.errors[0].startswith("preview: RuntimeError: port in use (its output: "))
        self.assertIn("No module named 'app.jobs'", saved, "what the apps printed is kept beside the case")


class TheRun(TestCase):
    def test_report_and_comparison_with_the_previous_run(self) -> None:
        async def fake_build(case, folder, *, design, log):
            result = bench.CaseResult(case.id, case.prompt, case.tags)
            result.apps, result.entities, result.verification = ["App"], list(case.entities), {"status": "clean"}
            result.capabilities = list(case.capabilities)
            result.apps = ["App"] * case.apps
            result.repo = str(folder / "repo")
            return result, None

        cases = select(only=["blog", "crm"])
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(bench, "build_case", fake_build):
            out = Path(tmp)
            (out / "20000101-000000").mkdir()
            (out / "20000101-000000" / "report.json").write_text(json.dumps(
                {"run": "20000101-000000", "cases": [{"id": "blog", "score": 100.0}, {"id": "crm", "score": 40.0}]}))
            report = asyncio.run(bench.run_benchmark(cases, out, preview=False, log=lambda m: None))
            md = (out / report["run"] / "report.md").read_text()
        self.assertEqual([c["score"] for c in report["cases"]], [100.0, 100.0])
        self.assertEqual(report["comparison"]["changes"], {"crm": 60.0, "blog": 0.0})
        self.assertEqual(report["comparison"]["regressions"], [])
        self.assertIn("| blog | 100.0 | +0.0 |", md)
        self.assertIn("Against 20000101-000000", md)

    def test_one_crash_does_not_end_the_run(self) -> None:
        async def crash(case, folder, *, design, log):
            raise KeyError("boom")

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(bench, "build_case", crash):
            report = asyncio.run(bench.run_benchmark(select(only=["blog", "crm"]), Path(tmp), preview=False, log=lambda m: None))
        self.assertEqual(len(report["cases"]), 2)
        self.assertTrue(all(c["score"] == 0.0 and c["errors"] for c in report["cases"]))


class Rescoring(TestCase):
    def test_a_saved_run_is_scored_with_the_current_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "20260101-000000"
            run_dir.mkdir()
            skipped = {"status": "skipped", "surfaces": {"services/api": {"status": "parsed"}}}
            (run_dir / "report.json").write_text(json.dumps({"run": run_dir.name, "design": False, "preview": True, "cases": [
                {"id": "blog", "prompt": "A simple blog", "tags": [], "score": 100.0, "parts": {"build": 1.0, "runs": 1.0},
                 "apps": ["Blog"], "entities": ["Post", "Category", "Comment"], "capabilities": [], "verification": skipped,
                 "endpoints": {}, "ui": {}, "design": {}, "errors": [], "missing": [], "timings": {}, "repo": ""}]}))
            report = bench.rescore(run_dir)
        self.assertEqual(report["cases"][0]["parts"]["build"], 0.5)
        self.assertEqual(report["cases"][0]["parts"]["runs"], 1.0, "measured parts are kept")

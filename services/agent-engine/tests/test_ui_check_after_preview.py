"""PC-106: the UI check runs by itself once a preview is ready, and the Studio shows the result.

PC-101 ran `scripts/ui-check.mjs` by hand. Now the runner starts it after the preview's pages are
warmed, on the apps' own ports with their API calls routed to the API, and keeps a status beside
the workspace's logs; the preview status carries it to the console. No model is asked anything, and
without Node, Chrome or playwright-core the check is skipped with the reason.
"""

import json
import tempfile
import time
from pathlib import Path
from unittest import TestCase, mock

from omnistackai_agent_engine.localrun import ui_check
from omnistackai_agent_engine.localrun.plan import RunPlan

_REPO = Path(__file__).resolve().parents[3]


def _plan(repo_dir: str, **changes) -> RunPlan:
    values = dict(repo_dir=repo_dir, app_slug="s", db_name="d", backend_kind="python", has_web=True,
                  api_url="http://127.0.0.1:8000", web_url="http://127.0.0.1:3000", db_password="x",
                  multi_app=True, public_base="/preview/p1",
                  web_surfaces=(("web", "http://127.0.0.1:3000"), ("admin", "http://127.0.0.1:3100")))
    values.update(changes)
    return RunPlan(**values)


class ItChecksEveryAppOnItsOwnPort(TestCase):
    def test_every_app_under_its_base_path_and_the_api_routed(self) -> None:
        args = ui_check.check_arguments(_plan("/w/repo"), Path("/w/logs/ui-check"))
        self.assertIn("web=http://127.0.0.1:3000/preview/p1/web", args)
        self.assertIn("admin=http://127.0.0.1:3100/preview/p1/admin", args)
        self.assertEqual(args[args.index("--route-api") + 1], "/preview/p1/api=http://127.0.0.1:8000")
        self.assertNotIn("--login", args, "no console session is needed")

    def test_the_script_routes_api_calls_and_answers_the_favicon(self) -> None:
        script = (_REPO / "scripts/ui-check.mjs").read_text()
        self.assertIn('else if (key === "--route-api")', script)
        self.assertIn("route.continue({ url: `${target}", script)


class ItKeepsAStatusTheStudioShows(TestCase):
    def test_a_summary_names_the_first_problems(self) -> None:
        report = {"results": [
            {"app": "web", "route": "/", "device": "phone", "problems": [], "notes": []},
            {"app": "web", "route": "/", "device": "desktop", "problems": ["low contrast: x"], "notes": []},
            {"app": "admin", "route": "/users", "device": "phone", "problems": [], "notes": ["transient"]},
        ]}
        summary = ui_check.summarize(report)
        self.assertEqual((summary["status"], summary["pages"], summary["page_views"], summary["failing"]),
                         ("failed", 2, 3, 1))
        self.assertEqual(summary["transient"], 1)
        self.assertEqual(summary["problems"][0]["problem"], "low contrast: x")

    def test_it_is_skipped_with_the_reason_when_it_cannot_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "logs").mkdir()
            (Path(tmp) / "repo").mkdir()
            started = time.time() - 1
            with mock.patch.object(ui_check, "unavailable_reason", return_value="no Chrome or Chromium found"):
                self.assertIsNone(ui_check.run_ui_check(_plan(str(Path(tmp) / "repo"))))
            status = ui_check.read_status(str(Path(tmp) / "repo"), started)
            self.assertEqual(status, {**status, "status": "skipped", "reason": "no Chrome or Chromium found"})

    def test_an_earlier_runs_status_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "logs" / "ui-check"
            folder.mkdir(parents=True)
            (folder / "status.json").write_text(json.dumps({"status": "passed", "started_at": 100.0}))
            self.assertIsNone(ui_check.read_status(str(Path(tmp) / "repo"), since=200.0))
            self.assertEqual(ui_check.read_status(str(Path(tmp) / "repo"), since=50.0)["status"], "passed")

    def test_outside_a_workspace_or_a_preview_nothing_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(ui_check.run_ui_check(_plan(tmp)), "no logs folder: a CLI run")
            (Path(tmp) / "logs").mkdir()
            self.assertIsNone(ui_check.run_ui_check(_plan(str(Path(tmp) / "repo"), multi_app=False, public_base="")))

    def test_the_runner_starts_it_after_warming_and_the_status_carries_it(self) -> None:
        run = (_REPO / "services/agent-engine/src/omnistackai_agent_engine/localrun/run.py").read_text()
        self.assertIn("run_ui_check(active_plan, after=warmed)", run)
        preview = (_REPO / "services/agent-engine/src/omnistackai_agent_engine/studio/preview.py").read_text()
        self.assertIn('res["ui_check"] = ui_check', preview)
        studio = (_REPO / "apps/console-web/app/studio/studio-preview-apps.tsx").read_text()
        self.assertIn("<UiCheckStrip check={status.ui_check} />", studio)

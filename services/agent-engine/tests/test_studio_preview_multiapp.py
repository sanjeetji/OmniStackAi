"""R-520 (Phase T, T-2): the Studio preview manager for multi-app (template) projects.

Template projects start asynchronously: ``start_workspace`` returns ``starting`` at once and
``workspace_status`` reports progress, per-app readiness and the demo logins. Prompt-built
projects (no omnistack.json) keep the synchronous single-app path. The last test runs real
local processes end to end.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

from omnistackai_agent_engine.localrun.multiapp import (
    MultiAppRunError,
    allocate_ports,
    build_multiapp_plan,
    start_multiapp,
)
from omnistackai_agent_engine.studio.preview import StudioPreviewManager

from test_localrun_multiapp import MANIFEST, _SERVER, _make_repo

WS = "9a8b7c6d-1111-4222-8333-444455556666"

MANIFEST_WITH_USERS = {
    **MANIFEST,
    "demo_users": [
        {"role": "customer", "name": "Asha Rao", "email": "asha@corner-shop.test", "password": "demo-1"},
    ],
}


class FakeSession:
    def __init__(self) -> None:
        self.alive = True
        self.stopped = False

    def is_alive(self) -> bool:
        return self.alive and not self.stopped

    def stop(self) -> None:
        self.stopped = True


def _plan_fn(repo_dir, manifest, *, project_id, extra_env=None):  # noqa: ANN001
    return build_multiapp_plan(
        repo_dir, manifest, project_id=project_id, ports=[5101, 5102, 5103], jwt_secret="jwt-xyz", extra_env=extra_env
    )


def _wait_for(manager: StudioPreviewManager, predicate, timeout: float = 10.0) -> dict:  # noqa: ANN001
    deadline = time.time() + timeout
    status = manager.workspace_status(WS)
    while time.time() < deadline:
        status = manager.workspace_status(WS)
        if predicate(status):
            return status
        time.sleep(0.05)
    raise AssertionError(f"condition not met, last status: {status}")


class MultiAppPreviewManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = _make_repo(Path(self._tmp.name), MANIFEST_WITH_USERS)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_starts_asynchronously_and_reports_apps_and_demo_users(self) -> None:
        gate = threading.Event()
        session = FakeSession()
        received: dict = {}

        def fake_start(plan, *, on_phase, on_app_ready, log_callback, cancelled, **_):  # noqa: ANN001
            received["env"] = dict(plan.apps[0].env)
            gate.wait(5)
            on_phase("install")
            for app in plan.apps:
                on_app_ready(app.id)
            on_phase("ready")
            return session

        manager = StudioPreviewManager(multiapp_plan_fn=_plan_fn, multiapp_start_fn=fake_start)
        first = manager.start_workspace(WS, str(self.repo), env={"STRIPE_KEY": "sk_test"})
        self.assertEqual(first["status"], "starting")
        self.assertEqual(first["kind"], "multi")
        self.assertEqual([a["id"] for a in first["apps"]], ["web", "courier", "api"])
        self.assertFalse(any(a["ready"] for a in first["apps"]))
        self.assertEqual(first["apps"][0]["path"], f"/preview/{WS}/web")
        self.assertEqual(first["demo_users"][0]["email"], "asha@corner-shop.test")

        gate.set()
        ready = _wait_for(manager, lambda s: s["status"] == "ready")
        self.assertTrue(all(a["ready"] for a in ready["apps"]))
        self.assertEqual(ready["web_url"], "http://127.0.0.1:5101")
        self.assertEqual(ready["api_url"], "http://127.0.0.1:5103")
        self.assertEqual(received["env"]["STRIPE_KEY"], "sk_test")  # project secrets reach the apps

        manager.stop_workspace(WS)
        self.assertTrue(session.stopped)
        self.assertEqual(manager.workspace_status(WS)["status"], "stopped")

    def test_failure_is_reported_with_secrets_masked(self) -> None:
        def fake_start(plan, **_):  # noqa: ANN001
            raise MultiAppRunError("api exited: bad secret jwt-xyz")

        manager = StudioPreviewManager(multiapp_plan_fn=_plan_fn, multiapp_start_fn=fake_start)
        manager.start_workspace(WS, str(self.repo))
        status = _wait_for(manager, lambda s: s["status"] == "error")
        self.assertIn("api exited", status["message"])
        self.assertNotIn("jwt-xyz", status["message"])

    def test_stop_while_starting_cancels_without_reporting_an_error(self) -> None:
        started = threading.Event()

        def fake_start(plan, *, cancelled, **_):  # noqa: ANN001
            started.set()
            while not cancelled():
                time.sleep(0.01)
            raise MultiAppRunError("the preview was stopped while it was starting")

        manager = StudioPreviewManager(multiapp_plan_fn=_plan_fn, multiapp_start_fn=fake_start)
        manager.start_workspace(WS, str(self.repo))
        self.assertTrue(started.wait(5))
        self.assertEqual(manager.stop_workspace(WS)["status"], "stopped")
        time.sleep(0.2)
        self.assertEqual(manager.workspace_status(WS)["status"], "stopped")

    def test_a_late_start_after_restart_is_discarded(self) -> None:
        sessions: list[FakeSession] = []
        gates = [threading.Event(), threading.Event()]

        def fake_start(plan, **_):  # noqa: ANN001
            index = len(sessions)
            session = FakeSession()
            sessions.append(session)
            gates[index].wait(5)
            return session

        manager = StudioPreviewManager(multiapp_plan_fn=_plan_fn, multiapp_start_fn=fake_start)
        manager.start_workspace(WS, str(self.repo))
        _wait_until = time.time() + 5
        while len(sessions) < 1 and time.time() < _wait_until:
            time.sleep(0.01)
        manager.start_workspace(WS, str(self.repo))  # restart before the first finished
        while len(sessions) < 2 and time.time() < _wait_until:
            time.sleep(0.01)
        gates[1].set()
        _wait_for(manager, lambda s: s["status"] == "ready")
        gates[0].set()
        time.sleep(0.2)
        self.assertTrue(sessions[0].stopped, "the superseded start must be stopped, not adopted")
        self.assertFalse(sessions[1].stopped)
        manager.stop_workspace(WS)

    def test_crashed_app_is_noticed_by_status(self) -> None:
        session = FakeSession()
        manager = StudioPreviewManager(multiapp_plan_fn=_plan_fn, multiapp_start_fn=lambda plan, **_: session)
        manager.start_workspace(WS, str(self.repo))
        _wait_for(manager, lambda s: s["status"] == "ready")
        session.alive = False
        status = manager.workspace_status(WS)
        self.assertEqual(status["status"], "stopped")
        self.assertFalse(any(a["ready"] for a in status["apps"]))

    def test_invalid_manifest_is_an_immediate_error(self) -> None:
        (self.repo / "omnistack.json").write_text("{", encoding="utf-8")
        manager = StudioPreviewManager(multiapp_plan_fn=_plan_fn, multiapp_start_fn=lambda *a, **k: FakeSession())
        status = manager.start_workspace(WS, str(self.repo))
        self.assertEqual(status["status"], "error")
        self.assertIn("omnistack.json", status["message"])

    def test_prompt_built_projects_keep_the_single_app_path(self) -> None:
        (self.repo / "omnistack.json").unlink()
        calls: list[str] = []

        def legacy_start(repo_dir, **_):  # noqa: ANN001
            calls.append(repo_dir)
            raise RuntimeError("legacy path used")

        def must_not_run(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            raise AssertionError("the multi-app runner must not handle prompt-built projects")

        manager = StudioPreviewManager(start_fn=legacy_start, multiapp_start_fn=must_not_run)
        status = manager.start_workspace(WS, str(self.repo))
        self.assertEqual(calls, [str(self.repo)])
        self.assertEqual(status["status"], "error")
        self.assertEqual(status["kind"], "single")
        self.assertNotIn("apps", status)


class RealProcessesTests(unittest.TestCase):
    def test_end_to_end_with_real_local_servers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(Path(tmp), MANIFEST_WITH_USERS)
            (repo / "server.py").write_text(_SERVER, encoding="utf-8")

            def plan_fn(repo_dir, manifest, *, project_id, extra_env=None):  # noqa: ANN001
                plan = build_multiapp_plan(repo_dir, manifest, project_id=project_id, ports=allocate_ports(3))
                health = {"web": f"/preview/{project_id}/web", "courier": "/preview/", "api": "/health"}
                apps = tuple(
                    dataclasses.replace(a, command=(sys.executable, str(repo / "server.py"), health[a.id]))
                    for a in plan.apps
                )
                return dataclasses.replace(plan, apps=apps, setup=())

            manager = StudioPreviewManager(
                multiapp_plan_fn=plan_fn,
                multiapp_start_fn=lambda plan, **kw: start_multiapp(plan, health_timeout_seconds=20, **kw),
            )
            manager.start_workspace(WS, str(repo))
            ready = _wait_for(manager, lambda s: s["status"] in ("ready", "error"), timeout=30)
            self.assertEqual(ready["status"], "ready", ready.get("message"))
            web = ready["apps"][0]
            body = urllib.request.urlopen(f"{web['url']}{web['path']}", timeout=5).read().decode()
            self.assertTrue(body.startswith(web["path"]))
            manager.stop_workspace(WS)
            with self.assertRaises(OSError):
                urllib.request.urlopen(f"{web['url']}{web['path']}", timeout=2)


if __name__ == "__main__":
    unittest.main()

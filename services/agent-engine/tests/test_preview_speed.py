"""PC-006: the running app appears fast, and a model's odd plan cannot break its pages.

Measured on 2026-09-26 with a blog app (API + web + admin), preview start went from 17.7 s to 9.6 s,
and a live console build from prompt to running app went from 18-26 s to 12-15 s on Groq:
* the API used to create a virtualenv and pip-install on every preview (3.3 s), then pay for a first
  start of freshly installed packages; it now links to one shared environment per requirements set;
* the API, web app and admin console were waited for one after another at 1 s intervals; they are
  now probed at the same time, every 0.25 s.

Tried and not taken: Turbopack boots ~0.6 s faster but failed to compile generated pages that
webpack compiles. Starting the preview during verification would save ~5 s more, but both touch an
app's node_modules at the same moment; left for a follow-up.

Found live along the way: Groq wrote screen navigation as objects, which became links to
``/{'target': ...}`` and pages that did not compile.
"""

import tempfile
import threading
import time
from pathlib import Path
from unittest import TestCase, mock

from omnistackai_agent_engine.intake.nl_to_ir import _sanitize_ir_dict
from omnistackai_agent_engine.localrun import RunPlan, RunStep, api_env, start_app
from omnistackai_agent_engine.localrun import run as run_module


def _fake_build(env_dir, python, requirements):
    (env_dir / "bin").mkdir(parents=True)
    (env_dir / "bin" / "uvicorn").write_text("#!/bin/sh\n")
    (env_dir / api_env.READY_MARKER).write_text("ok\n")
    return True


class ApisShareOneWarmEnvironment(TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cache = self.tmp / "cache"
        patches = [
            mock.patch.dict("os.environ", {api_env.CACHE_ENV: str(self.cache)}),
            mock.patch.object(api_env, "_build", side_effect=_fake_build),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _project(self, name: str, requirements: str = "fastapi==0.115.0\n") -> Path:
        api = self.tmp / name / "services" / "api"
        api.mkdir(parents=True)
        (api / "requirements.txt").write_text(requirements)
        return api

    def test_projects_with_the_same_requirements_share_one_build(self) -> None:
        first, second = self._project("a"), self._project("b")
        self.assertTrue(api_env.link_shared_environment(first))
        self.assertTrue(api_env.link_shared_environment(second))
        self.assertEqual(api_env._build.call_count, 1)
        self.assertTrue((first / ".venv").is_symlink())
        self.assertEqual((first / ".venv").resolve(), (second / ".venv").resolve())

    def test_changed_requirements_get_their_own_environment(self) -> None:
        api = self._project("a")
        api_env.link_shared_environment(api)
        before = (api / ".venv").resolve()
        (api / "requirements.txt").write_text("fastapi==0.115.0\nhttpx==0.27.0\n")
        self.assertTrue(api_env.link_shared_environment(api))
        self.assertNotEqual((api / ".venv").resolve(), before)

    def test_a_projects_own_environment_is_left_alone(self) -> None:
        api = self._project("a")
        (api / ".venv").mkdir()
        self.assertFalse(api_env.link_shared_environment(api))
        self.assertFalse((api / ".venv").is_symlink())

    def test_it_can_be_turned_off(self) -> None:
        with mock.patch.dict("os.environ", {api_env.CACHE_ENV: "off"}):
            self.assertFalse(api_env.link_shared_environment(self._project("a")))

    def test_a_failed_build_falls_back_to_the_per_project_install(self) -> None:
        with mock.patch.object(api_env, "_build", return_value=False):
            self.assertFalse(api_env.link_shared_environment(self._project("a")))

    def test_the_link_is_kept_out_of_the_repository(self) -> None:
        from omnistackai_agent_engine.application_ir import example_ir
        from omnistackai_agent_engine.codegen.assembler import assemble_project

        ignore = assemble_project(example_ir("minimal-blog")).get(".gitignore").content.splitlines()
        # `.venv/` matches only a directory; a symlink named .venv would be committed.
        self.assertIn(".venv", ignore)


def _plan(root: str, **extra) -> RunPlan:
    steps = (
        RunStep(label="create backend virtualenv", program="python3", cwd=root),
        RunStep(label="install backend dependencies", program=".venv/bin/pip", cwd=root),
        RunStep(label="start api", program="api", background=True),
    )
    return RunPlan(repo_dir=root, app_slug="app", db_name="app", backend_kind="python", has_web=True,
                   api_url="http://127.0.0.1:8000", web_url="http://127.0.0.1:3000", db_password="x",
                   steps=steps, **extra)


class _Process:
    def poll(self):
        return None

    def terminate(self):
        pass

    def wait(self, timeout=None):
        return 0


class StartingIsQuick(TestCase):
    def _start(self, plan, wait):
        with mock.patch.object(run_module, "_run_sync") as run_sync, \
                mock.patch.object(run_module, "_launch", return_value=_Process()), \
                mock.patch.object(run_module, "_port_available", return_value=True), \
                mock.patch.object(run_module, "_wait_healthy", side_effect=wait), \
                mock.patch.object(run_module, "_link_shared_environment", return_value=True):
            session = start_app(plan.repo_dir, plan=plan, log=None)
        return session, run_sync

    def test_a_linked_environment_skips_create_and_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, run_sync = self._start(_plan(tmp), lambda url, timeout_seconds=45.0: True)
        run_sync.assert_not_called()

    def test_surfaces_are_probed_at_the_same_time(self) -> None:
        active, peak, lock = [0], [0], threading.Lock()

        def slow(url, timeout_seconds=45.0):
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            time.sleep(0.2)
            with lock:
                active[0] -= 1
            return True

        with tempfile.TemporaryDirectory() as tmp:
            session, _ = self._start(_plan(tmp, has_admin=True, admin_url="http://127.0.0.1:3100"), slow)
        self.assertEqual(peak[0], 3, "API, web and admin must be waited for together")
        self.assertTrue(session.api_ready and session.web_ready and session.admin_ready)

    def test_a_slow_mobile_app_does_not_fail_the_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = _plan(tmp, has_mobile=True, mobile_url="http://127.0.0.1:8081")
            session, _ = self._start(plan, lambda url, timeout_seconds=45.0: "8081" not in url)
        self.assertTrue(session.web_ready)
        self.assertFalse(session.mobile_ready)

    def test_checks_come_four_times_a_second(self) -> None:
        self.assertLessEqual(run_module._POLL_SECONDS, 0.25)


class NavigationFromTheModelIsPlainScreenIds(TestCase):
    def _screens(self, navigation):
        data = {
            "name": "Habits", "entities": [], "roles": [{"id": "user", "description": "User"}],
            "screens": [
                {"id": "habit_list", "role": "user", "components": ["list"], "actions": ["open"],
                 "navigation": navigation},
                {"id": "habit_editor", "role": "user", "components": [{"name": "form"}],
                 "actions": [{"name": "save"}], "navigation": ["habit_list"]},
            ],
        }
        return {s["id"]: s for s in _sanitize_ir_dict(data)["screens"]}

    def test_objects_are_unwrapped_to_their_target(self) -> None:
        screens = self._screens([{"target": "habit_editor", "action": "create"},
                                 {"target": "habit_editor", "action": "open"}])
        self.assertEqual(screens["habit_list"]["navigation"], ["habit_editor"])
        self.assertEqual(screens["habit_editor"]["components"], ["form"])
        self.assertEqual(screens["habit_editor"]["actions"], ["save"])

    def test_links_to_missing_screens_are_dropped(self) -> None:
        self.assertEqual(self._screens(["Habit Editor", "nowhere"])["habit_list"]["navigation"], ["habit_editor"])

"""Managed generated-app session tests for R-421.

All process execution and readiness checks are patched in memory. These tests never invoke Docker,
package installers, generated code, a database, a model, or the network.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omnistackai_agent_engine.localrun import (
    LocalAppRunError,
    LocalAppSession,
    RunPlan,
    RunStep,
    allocate_preview_ports,
    find_free_port,
    start_app,
    start_preview_app,
)


class FakeProcess:
    def __init__(self, *, returncode: int | None = None) -> None:
        self.terminate_calls = 0
        self.wait_calls = 0
        self.kill_calls = 0
        self.returncode = returncode

    def terminate(self) -> None:
        self.terminate_calls += 1

    def wait(self, timeout=None) -> int:
        self.wait_calls += 1
        return 0

    def kill(self) -> None:
        self.kill_calls += 1

    def poll(self) -> int | None:
        return self.returncode


def _plan(root: str, *, backend_kind: str = "python", has_web: bool = True) -> RunPlan:
    steps = (
        RunStep(label="setup", program="setup"),
        RunStep(label="start api", program="api", background=True),
        RunStep(label="web install", program="install"),
        RunStep(label="start web", program="web", background=True),
    )
    return RunPlan(
        repo_dir=root,
        app_slug="app",
        db_name="app",
        backend_kind=backend_kind,
        has_web=has_web,
        api_url="http://127.0.0.1:8000",
        web_url="http://127.0.0.1:3000",
        db_password="never-return-this",
        steps=steps,
    )


class TestLocalAppSession(unittest.TestCase):
    def test_start_reports_api_and_web_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            processes = [FakeProcess(), FakeProcess()]
            health_urls: list[str] = []

            def healthy(url: str, timeout_seconds: float = 45.0) -> bool:
                health_urls.append(url)
                return True

            with (
                patch("omnistackai_agent_engine.localrun.run._run_sync") as run_sync,
                patch("omnistackai_agent_engine.localrun.run._launch", side_effect=processes),
                patch("omnistackai_agent_engine.localrun.run._wait_healthy", side_effect=healthy),
                patch("omnistackai_agent_engine.localrun.run._port_available", return_value=True),
            ):
                session = start_app(tmp, plan=_plan(tmp), log=None)

            self.assertIsInstance(session, LocalAppSession)
            self.assertTrue(session.api_ready)
            self.assertTrue(session.web_ready)
            self.assertEqual(health_urls, ["http://127.0.0.1:8000/healthz", "http://127.0.0.1:3000"])
            self.assertEqual(run_sync.call_count, 2)
            self.assertEqual(session.processes, processes)
            session.stop()

    def test_stop_is_idempotent(self) -> None:
        process = FakeProcess()
        session = LocalAppSession(_plan("/tmp/app"), processes=[process])
        session.stop()
        session.stop()
        self.assertEqual(process.terminate_calls, 1)
        self.assertEqual(process.wait_calls, 1)
        self.assertEqual(process.kill_calls, 0)

    def test_later_setup_failure_cleans_up_started_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            process = FakeProcess()

            def fail_web_install(step: RunStep) -> None:
                if step.label == "web install":
                    raise LocalAppRunError("setup failed")

            with (
                patch("omnistackai_agent_engine.localrun.run._run_sync", side_effect=fail_web_install),
                patch("omnistackai_agent_engine.localrun.run._launch", return_value=process),
                patch("omnistackai_agent_engine.localrun.run._port_available", return_value=True),
            ):
                with self.assertRaisesRegex(LocalAppRunError, "setup failed"):
                    start_app(tmp, plan=_plan(tmp), log=None)

            self.assertEqual(process.terminate_calls, 1)
            self.assertEqual(process.wait_calls, 1)

    def test_failed_readiness_cleans_up_every_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            processes = [FakeProcess(), FakeProcess()]
            with (
                patch("omnistackai_agent_engine.localrun.run._run_sync"),
                patch("omnistackai_agent_engine.localrun.run._launch", side_effect=processes),
                patch("omnistackai_agent_engine.localrun.run._wait_healthy", side_effect=[True, False]),
                patch("omnistackai_agent_engine.localrun.run._port_available", return_value=True),
            ):
                with self.assertRaisesRegex(LocalAppRunError, "web app did not become ready"):
                    start_app(tmp, plan=_plan(tmp), log=None)

            self.assertTrue(all(process.terminate_calls == 1 for process in processes))

    def test_occupied_preview_port_is_rejected_before_setup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch("omnistackai_agent_engine.localrun.run._port_available", return_value=False),
                patch("omnistackai_agent_engine.localrun.run._run_sync") as run_sync,
            ):
                with self.assertRaisesRegex(LocalAppRunError, "local preview port is already in use"):
                    start_app(tmp, plan=_plan(tmp), log=None)
            run_sync.assert_not_called()

    def test_stale_health_response_cannot_hide_exited_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            processes = [FakeProcess(returncode=1), FakeProcess()]
            with (
                patch("omnistackai_agent_engine.localrun.run._port_available", return_value=True),
                patch("omnistackai_agent_engine.localrun.run._run_sync"),
                patch("omnistackai_agent_engine.localrun.run._launch", side_effect=processes),
                patch("omnistackai_agent_engine.localrun.run._wait_healthy", return_value=True),
            ):
                with self.assertRaisesRegex(LocalAppRunError, "background process exited"):
                    start_app(tmp, plan=_plan(tmp), log=None)
            self.assertTrue(all(process.terminate_calls == 1 for process in processes))

    def test_missing_repo_is_rejected_before_planning(self) -> None:
        missing = str(Path(tempfile.gettempdir()) / "omnistackai-r421-does-not-exist")
        with self.assertRaisesRegex(LocalAppRunError, "not a directory"):
            start_app(missing, log=None)


class TestPreviewPortAllocation(unittest.TestCase):
    def test_find_free_port_returns_a_bindable_loopback_port(self) -> None:
        import socket

        port = find_free_port("127.0.0.1")
        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)
        # The reported port is actually free right now.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", port))

    def test_allocate_preview_ports_returns_two_distinct_free_ports(self) -> None:
        api_port, web_port = allocate_preview_ports("127.0.0.1")
        self.assertIsInstance(api_port, int)
        self.assertIsInstance(web_port, int)
        self.assertNotEqual(api_port, web_port)
        self.assertGreater(api_port, 0)
        self.assertGreater(web_port, 0)

    def test_start_preview_app_allocates_and_threads_ports_into_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            captured: dict = {}

            def fake_start_app(repo_dir, *, plan=None, **kwargs):
                captured["plan"] = plan
                captured["kwargs"] = kwargs
                return LocalAppSession(plan)

            with (
                patch(
                    "omnistackai_agent_engine.localrun.run.allocate_preview_ports",
                    return_value=(9101, 9102),
                ),
                patch("omnistackai_agent_engine.localrun.run.start_app", side_effect=fake_start_app),
            ):
                start_preview_app(tmp, log=None)

            plan = captured["plan"]
            self.assertIsNotNone(plan)
            # Allocated ports were threaded into the run plan (and thus NEXT_PUBLIC_API_URL).
            self.assertEqual(plan.api_url, "http://127.0.0.1:9101")
            self.assertEqual(plan.web_url, "http://127.0.0.1:9102")

    def test_start_preview_app_rejects_missing_repo(self) -> None:
        missing = str(Path(tempfile.gettempdir()) / "omnistackai-r422-does-not-exist")
        with self.assertRaisesRegex(LocalAppRunError, "not a directory"):
            start_preview_app(missing, log=None)


if __name__ == "__main__":
    unittest.main()

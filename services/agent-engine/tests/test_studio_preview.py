"""Studio live-preview coordinator and opt-in task tests for R-421.

Uses fake managed sessions only; no generated code, Docker, database, package manager, or model runs.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from omnistackai_agent_engine.localrun import RunPlan
from omnistackai_agent_engine.studio import StudioPreviewManager


class FakeSession:
    def __init__(self, *, has_web: bool = True, web_ready: bool = True) -> None:
        self.plan = RunPlan(
            repo_dir="/tmp/generated",
            app_slug="generated",
            db_name="generated",
            backend_kind="python",
            has_web=has_web,
            api_url="http://127.0.0.1:8000",
            web_url="http://127.0.0.1:3000",
            db_password="top-secret-password",
        )
        self.api_ready = True
        self.web_ready = web_ready
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1


class TestStudioPreviewManager(unittest.TestCase):
    def test_ready_payload_is_json_safe_and_secret_free(self) -> None:
        session = FakeSession()
        manager = StudioPreviewManager(start_fn=lambda repo, log=None: session)
        payload = manager.replace("/tmp/generated")
        text = json.dumps(payload)
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["web_url"], "http://127.0.0.1:3000")
        self.assertEqual(payload["api_url"], "http://127.0.0.1:8000")
        self.assertNotIn("top-secret-password", text)
        manager.stop()

    def test_replacement_stops_previous_session(self) -> None:
        first = FakeSession()
        second = FakeSession()
        sessions = iter((first, second))
        manager = StudioPreviewManager(start_fn=lambda repo, log=None: next(sessions))
        self.assertEqual(manager.replace("/tmp/one")["status"], "ready")
        self.assertEqual(manager.replace("/tmp/two")["status"], "ready")
        self.assertEqual(first.stop_calls, 1)
        self.assertEqual(second.stop_calls, 0)
        manager.stop()
        self.assertEqual(second.stop_calls, 1)

    def test_launch_failure_returns_bounded_generic_error(self) -> None:
        def fail(repo: str, log=None):
            raise RuntimeError("DATABASE_URL=postgresql://user:secret@host/db\nraw traceback detail")

        payload = StudioPreviewManager(start_fn=fail).replace("/tmp/generated")
        self.assertEqual(payload["status"], "error")
        self.assertIn("then retry", payload["message"])
        self.assertNotIn("secret", json.dumps(payload))
        self.assertLessEqual(len(payload["message"]), 240)

    def test_repo_without_web_returns_unavailable_and_stops(self) -> None:
        session = FakeSession(has_web=False, web_ready=False)
        payload = StudioPreviewManager(start_fn=lambda repo, log=None: session).replace("/tmp/api")
        self.assertEqual(payload["status"], "unavailable")
        self.assertNotIn("web_url", payload)
        self.assertEqual(session.stop_calls, 1)

    def test_stop_is_idempotent(self) -> None:
        session = FakeSession()
        manager = StudioPreviewManager(start_fn=lambda repo, log=None: session)
        manager.replace("/tmp/generated")
        manager.stop()
        manager.stop()
        self.assertEqual(session.stop_calls, 1)


class TestStudioPreviewTask(unittest.TestCase):
    def test_preview_task_is_explicit_and_starts_database(self) -> None:
        root = Path(__file__).resolve().parents[3]
        taskfile = (root / "Taskfile.yml").read_text()
        script = (root / "scripts" / "agent-engine.sh").read_text()
        self.assertIn("agent-engine:studio:preview:", taskfile)
        preview_block = taskfile.split("agent-engine:studio:preview:", 1)[1].split("\n  ", 1)[0]
        self.assertIn("trusted-local", taskfile)
        self.assertIn("deps: [db:up]", taskfile)
        self.assertIn("studio-preview", script)
        self.assertIn("OMNISTACKAI_STUDIO_LIVE_PREVIEW", script)


if __name__ == "__main__":
    unittest.main()

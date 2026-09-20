"""Tests for Studio workspace preview management (F-02 / R-500).

Deterministic and offline tests for StudioPreviewManager workspace preview lifecycle,
phase callbacks, ports recording, idle reaper, and server HTTP endpoints.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock

from omnistackai_agent_engine.localrun import LocalAppSession, RunPlan
from omnistackai_agent_engine.studio.preview import StudioPreviewManager, WorkspacePreviewSession
from omnistackai_agent_engine.studio.server import create_studio_server


def _make_dummy_session(web_port: int = 34567, api_port: int = 34568) -> LocalAppSession:
    plan = RunPlan(
        repo_dir="/dummy/repo",
        app_slug="app",
        db_name="app",
        backend_kind="python",
        has_web=True,
        api_url=f"http://127.0.0.1:{api_port}",
        web_url=f"http://127.0.0.1:{web_port}",
        db_password="",
        steps=(),
    )
    sess = LocalAppSession(plan)
    sess.web_ready = True
    sess.api_ready = True
    sess.is_alive = MagicMock(return_value=True)  # type: ignore[method-assign]
    sess.stop = MagicMock()  # type: ignore[method-assign]
    return sess


class TestStudioWorkspacePreview(unittest.TestCase):
    def test_workspace_lifecycle_and_phases(self) -> None:
        phases_recorded: list[str] = []

        def mock_start(repo_dir: str, log=None, on_phase=None) -> LocalAppSession:
            if on_phase:
                on_phase("install")
                phases_recorded.append("install")
                on_phase("migrate")
                phases_recorded.append("migrate")
                on_phase("start")
                phases_recorded.append("start")
                on_phase("ready")
                phases_recorded.append("ready")
            return _make_dummy_session(web_port=41234, api_port=41235)

        mgr = StudioPreviewManager(start_fn=mock_start)

        # Initial status is idle
        init_status = mgr.workspace_status("ws-1")
        self.assertEqual(init_status["status"], "idle")
        self.assertEqual(init_status["phase"], "idle")

        # Start workspace
        res = mgr.start_workspace("ws-1", "/dummy/repo")
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["phase"], "ready")
        self.assertEqual(res["web_port"], 41234)
        self.assertEqual(res["api_port"], 41235)
        self.assertEqual(res["web_url"], "http://127.0.0.1:41234")
        self.assertEqual(res["api_url"], "http://127.0.0.1:41235")
        self.assertEqual(phases_recorded, ["install", "migrate", "start", "ready"])

        # Status check reflects ready
        status = mgr.workspace_status("ws-1")
        self.assertEqual(status["status"], "ready")
        self.assertEqual(status["web_port"], 41234)

        # Stop workspace
        stop_res = mgr.stop_workspace("ws-1")
        self.assertEqual(stop_res["status"], "stopped")
        self.assertEqual(stop_res["phase"], "stopped")

        # Subsequent status check reflects stopped
        status_after = mgr.workspace_status("ws-1")
        self.assertEqual(status_after["status"], "stopped")

    def test_idle_reaper(self) -> None:
        dummy_sess = _make_dummy_session()

        def mock_start(repo_dir: str, log=None, on_phase=None) -> LocalAppSession:
            return dummy_sess

        mgr = StudioPreviewManager(start_fn=mock_start)
        mgr.start_workspace("ws-idle", "/dummy/repo")

        # Force idle by adjusting last_active_at into the past
        ws_sess = mgr._workspaces["ws-idle"]
        ws_sess.last_active_at = ws_sess.last_active_at - 3600  # 1 hour ago

        # Setting idle timeout to 30 mins (default)
        status = mgr.workspace_status("ws-idle")
        self.assertEqual(status["status"], "stopped")
        self.assertIn("stopped — start again", status["message"])
        dummy_sess.stop.assert_called()

    def test_process_exit_detection(self) -> None:
        dummy_sess = _make_dummy_session()

        def mock_start(repo_dir: str, log=None, on_phase=None) -> LocalAppSession:
            return dummy_sess

        mgr = StudioPreviewManager(start_fn=mock_start)
        mgr.start_workspace("ws-dead", "/dummy/repo")

        # Subprocess unexpectedly dies
        dummy_sess.is_alive = MagicMock(return_value=False)  # type: ignore[method-assign]

        status = mgr.workspace_status("ws-dead")
        self.assertEqual(status["status"], "stopped")
        self.assertIn("stopped running", status["message"])


import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class TestStudioWorkspacePreviewServer(unittest.TestCase):
    def setUp(self) -> None:
        def dummy_build(prompt: str, **kwargs) -> dict:
            return {"status": "ok"}

        self.preview_data = {
            "status": "ready",
            "phase": "ready",
            "web_url": "http://127.0.0.1:45678",
            "api_url": "http://127.0.0.1:45679",
            "web_port": 45678,
            "api_port": 45679,
            "elapsed_ms": 1200,
            "message": "The generated application is running locally.",
        }
        self.stopped_data = {"status": "stopped", "phase": "stopped", "message": "Preview stopped."}

        def dummy_preview(ws_id: str, on_phase=None) -> dict:
            if on_phase:
                on_phase("install")
                on_phase("ready")
            return self.preview_data

        def dummy_preview_status(ws_id: str) -> dict:
            return self.preview_data

        def dummy_preview_stop(ws_id: str) -> dict:
            return self.stopped_data

        self.server = create_studio_server(
            dummy_build,
            host="127.0.0.1",
            port=0,
            workspace_preview_fn=dummy_preview,
            workspace_preview_status_fn=dummy_preview_status,
            workspace_preview_stop_fn=dummy_preview_stop,
        )
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def _get(self, path: str) -> tuple[int, dict]:
        req = Request(self._url(path), method="GET")
        try:
            with urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body) if body else {}
        except HTTPError as err:
            body = err.read().decode("utf-8")
            return err.code, json.loads(body) if body else {}

    def _post(self, path: str, payload: dict | None = None, headers: dict | None = None) -> tuple[int, dict]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else b""
        hdrs = {"Content-Type": "application/json"}
        if headers:
            hdrs.update(headers)
        req = Request(self._url(path), data=data, headers=hdrs, method="POST")
        try:
            with urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body) if body else {}
        except HTTPError as err:
            body = err.read().decode("utf-8")
            return err.code, json.loads(body) if body else {}

    def test_preview_endpoints(self) -> None:
        # GET /api/workspaces/ws-test/preview
        code, body = self._get("/api/workspaces/ws-test/preview")
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "ready")
        self.assertEqual(body["web_port"], 45678)

        # POST /api/workspaces/ws-test/preview
        code, body = self._post("/api/workspaces/ws-test/preview")
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "ready")
        self.assertEqual(body["web_port"], 45678)

        # POST /api/workspaces/ws-test/preview/stop
        code, body = self._post("/api/workspaces/ws-test/preview/stop")
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "stopped")


if __name__ == "__main__":
    unittest.main()

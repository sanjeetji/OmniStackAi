"""Tests for Studio multi-surface ecosystem live preview and process orchestration (R-446).

Uses fake managed sessions only; 0 real process execution, 0 model calls, 100% offline.
"""

from __future__ import annotations

import json
import unittest
from urllib.request import Request, urlopen

from omnistackai_agent_engine.localrun import RunPlan
from omnistackai_agent_engine.studio import (
    STUDIO_HTML,
    StudioBuildHistory,
    StudioPreviewManager,
    create_studio_server,
)


class FakeSurfaceSession:
    def __init__(
        self,
        repo_dir: str,
        *,
        web_port: int = 3000,
        api_port: int = 8000,
        has_web: bool = True,
        web_ready: bool = True,
        alive: bool = True,
    ) -> None:
        self.repo_dir = repo_dir
        self.plan = RunPlan(
            repo_dir=repo_dir,
            app_slug=repo_dir.split("/")[-1],
            db_name="test_db",
            backend_kind="python",
            has_web=has_web,
            api_url=f"http://127.0.0.1:{api_port}",
            web_url=f"http://127.0.0.1:{web_port}",
            db_password="secret-password",
        )
        self.api_ready = True
        self.web_ready = web_ready
        self.alive = alive
        self.stop_calls = 0

    def is_alive(self) -> bool:
        return self.alive

    def stop(self) -> None:
        self.stop_calls += 1
        self.alive = False


def make_surface_start_fn():
    sessions: dict[str, FakeSurfaceSession] = {}
    port_counter = [31000]

    def start_fn(repo_dir: str, log=None):
        w_port = port_counter[0]
        a_port = port_counter[0] + 1000
        port_counter[0] += 1
        sess = FakeSurfaceSession(repo_dir, web_port=w_port, api_port=a_port)
        sessions[repo_dir] = sess
        return sess

    return start_fn, sessions


class TestStudioEcosystemPreviewManager(unittest.TestCase):
    def setUp(self) -> None:
        self.start_fn, self.sessions = make_surface_start_fn()
        self.manager = StudioPreviewManager(start_fn=self.start_fn)
        self.sample_surfaces = [
            {
                "slug": "customer-web",
                "app_name": "Customer Web App",
                "surface_kind": "customer_web",
                "target_dir": "/tmp/eco/customer-web",
            },
            {
                "slug": "author-studio",
                "app_name": "Author Studio",
                "surface_kind": "provider_portal",
                "target_dir": "/tmp/eco/author-studio",
            },
            {
                "slug": "cms-admin",
                "app_name": "CMS Admin Dashboard",
                "surface_kind": "admin_dashboard",
                "target_dir": "/tmp/eco/cms-admin",
            },
        ]

    def tearDown(self) -> None:
        self.manager.stop()

    def test_replace_ecosystem_launches_primary_surface_and_registers_all(self) -> None:
        payload = self.manager.replace_ecosystem(
            ecosystem_id="minimal-blog-ecosystem",
            surfaces=self.sample_surfaces,
        )
        self.assertEqual(payload["status"], "ready")
        self.assertTrue(payload["is_ecosystem"])
        self.assertEqual(payload["ecosystem_id"], "minimal-blog-ecosystem")
        self.assertEqual(payload["active_surface"], "customer-web")
        self.assertEqual(payload["web_url"], "http://127.0.0.1:31000")
        self.assertEqual(payload["api_url"], "http://127.0.0.1:32000")
        self.assertNotIn("secret-password", json.dumps(payload))

        # Check surfaces list
        surfaces = payload["surfaces"]
        self.assertEqual(len(surfaces), 3)
        self.assertEqual(surfaces[0]["slug"], "customer-web")
        self.assertEqual(surfaces[0]["status"], "ready")
        self.assertTrue(surfaces[0]["is_active"])
        self.assertEqual(surfaces[1]["slug"], "author-studio")
        self.assertEqual(surfaces[1]["status"], "stopped")
        self.assertFalse(surfaces[1]["is_active"])

    def test_switch_surface_launches_on_demand_with_distinct_ports(self) -> None:
        self.manager.replace_ecosystem(
            ecosystem_id="minimal-blog-ecosystem",
            surfaces=self.sample_surfaces,
        )
        # Switch to author-studio
        payload = self.manager.switch_surface("author-studio")
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["active_surface"], "author-studio")
        self.assertEqual(payload["web_url"], "http://127.0.0.1:31001")
        self.assertEqual(payload["api_url"], "http://127.0.0.1:32001")

        # Both sessions should be alive concurrently
        self.assertEqual(len(self.sessions), 2)
        self.assertTrue(self.sessions["/tmp/eco/customer-web"].is_alive())
        self.assertTrue(self.sessions["/tmp/eco/author-studio"].is_alive())

        # Check surface statuses in payload
        surfaces_by_slug = {s["slug"]: s for s in payload["surfaces"]}
        self.assertEqual(surfaces_by_slug["customer-web"]["status"], "ready")
        self.assertFalse(surfaces_by_slug["customer-web"]["is_active"])
        self.assertEqual(surfaces_by_slug["author-studio"]["status"], "ready")
        self.assertTrue(surfaces_by_slug["author-studio"]["is_active"])

    def test_switch_to_already_running_surface_does_not_relaunch(self) -> None:
        self.manager.replace_ecosystem(
            ecosystem_id="minimal-blog-ecosystem",
            surfaces=self.sample_surfaces,
        )
        # Switch to author-studio then back to customer-web
        self.manager.switch_surface("author-studio")
        self.assertEqual(len(self.sessions), 2)

        # Switch back to customer-web
        payload = self.manager.switch_surface("customer-web")
        self.assertEqual(payload["active_surface"], "customer-web")
        self.assertEqual(payload["web_url"], "http://127.0.0.1:31000")
        # No extra session was created
        self.assertEqual(len(self.sessions), 2)

    def test_stop_specific_surface_keeps_other_surfaces_alive(self) -> None:
        self.manager.replace_ecosystem(
            ecosystem_id="minimal-blog-ecosystem",
            surfaces=self.sample_surfaces,
        )
        self.manager.switch_surface("author-studio")
        self.assertEqual(len(self.sessions), 2)

        # Stop customer-web
        payload = self.manager.stop(surface_slug="customer-web")
        self.assertEqual(self.sessions["/tmp/eco/customer-web"].stop_calls, 1)
        self.assertEqual(self.sessions["/tmp/eco/author-studio"].stop_calls, 0)
        self.assertTrue(self.sessions["/tmp/eco/author-studio"].is_alive())

        surfaces_by_slug = {s["slug"]: s for s in payload["surfaces"]}
        self.assertEqual(surfaces_by_slug["customer-web"]["status"], "stopped")
        self.assertEqual(surfaces_by_slug["author-studio"]["status"], "ready")

    def test_stop_all_stops_every_running_surface(self) -> None:
        self.manager.replace_ecosystem(
            ecosystem_id="minimal-blog-ecosystem",
            surfaces=self.sample_surfaces,
        )
        self.manager.switch_surface("author-studio")
        payload = self.manager.stop()  # stop all
        self.assertEqual(payload["status"], "stopped")
        for sess in self.sessions.values():
            self.assertEqual(sess.stop_calls, 1)

    def test_restart_specific_surface(self) -> None:
        self.manager.replace_ecosystem(
            ecosystem_id="minimal-blog-ecosystem",
            surfaces=self.sample_surfaces,
        )
        first_session = self.sessions["/tmp/eco/customer-web"]
        # Restart customer-web
        payload = self.manager.restart(surface_slug="customer-web")
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["active_surface"], "customer-web")
        # Previous customer session was stopped
        self.assertEqual(first_session.stop_calls, 1)

    def test_liveness_detection_across_multiple_surfaces(self) -> None:
        self.manager.replace_ecosystem(
            ecosystem_id="minimal-blog-ecosystem",
            surfaces=self.sample_surfaces,
        )
        self.manager.switch_surface("author-studio")

        # Simulate author-studio crashing/exiting
        self.sessions["/tmp/eco/author-studio"].alive = False

        status = self.manager.status()
        surfaces_by_slug = {s["slug"]: s for s in status["surfaces"]}
        self.assertEqual(surfaces_by_slug["customer-web"]["status"], "ready")
        self.assertEqual(surfaces_by_slug["author-studio"]["status"], "stopped")


class TestStudioServerEcosystemPreview(unittest.TestCase):
    def setUp(self) -> None:
        self.start_fn, self.sessions = make_surface_start_fn()
        self.manager = StudioPreviewManager(start_fn=self.start_fn)
        self.history = StudioBuildHistory()
        self.sample_surfaces = [
            {
                "slug": "customer-web",
                "app_name": "Customer Web App",
                "surface_kind": "customer_web",
                "target_dir": "/tmp/eco/customer-web",
            },
            {
                "slug": "author-studio",
                "app_name": "Author Studio",
                "surface_kind": "provider_portal",
                "target_dir": "/tmp/eco/author-studio",
            },
        ]

        def build_fn(prompt: str, **kwargs):
            return {"status": "ok", "prompt": prompt}

        self.server = create_studio_server(
            build_fn,
            host="127.0.0.1",
            port=0,
            status_fn=self.manager.status,
            stop_fn=self.manager.stop,
            restart_fn=self.manager.restart,
            history_fn=self.history.list,
            preview_build_fn=lambda bid, surface_slug=None: self.manager.replace_ecosystem(
                "test-eco", self.sample_surfaces, active_surface_slug=surface_slug
            ),
            switch_surface_fn=self.manager.switch_surface,
        )
        self.port = self.server.server_address[1]
        import threading
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.manager.stop()
        self.server.shutdown()
        self.server.server_close()

    def _post(self, path: str, payload: dict | None = None) -> tuple[int, dict]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else b""
        req = Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            headers={"Content-Type": "application/json"} if payload is not None else {},
            method="POST",
        )
        try:
            with urlopen(req) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return resp.status, body
        except Exception as err:
            if hasattr(err, "code"):
                return err.code, json.loads(err.read().decode("utf-8"))
            raise

    def test_switch_surface_endpoint(self) -> None:
        self.manager.replace_ecosystem("test-eco", self.sample_surfaces)
        code, body = self._post("/api/preview/switch", {"surface_slug": "author-studio"})
        self.assertEqual(code, 200)
        self.assertEqual(body["active_surface"], "author-studio")

    def test_switch_surface_missing_slug_returns_400(self) -> None:
        code, body = self._post("/api/preview/switch", {})
        self.assertEqual(code, 400)
        self.assertIn("surface_slug is required", body["error"])

    def test_stop_surface_endpoint(self) -> None:
        self.manager.replace_ecosystem("test-eco", self.sample_surfaces)
        self.manager.switch_surface("author-studio")

        code, body = self._post("/api/preview/stop", {"surface_slug": "customer-web"})
        self.assertEqual(code, 200)
        surfaces_by_slug = {s["slug"]: s for s in body["surfaces"]}
        self.assertEqual(surfaces_by_slug["customer-web"]["status"], "stopped")
        self.assertEqual(surfaces_by_slug["author-studio"]["status"], "ready")

    def test_history_preview_with_surface_slug(self) -> None:
        code, body = self._post("/api/history/preview", {"id": "test-id", "surface_slug": "author-studio"})
        self.assertEqual(code, 200)
        self.assertEqual(body["active_surface"], "author-studio")


class TestStudioPageEcosystemPreview(unittest.TestCase):
    def test_studio_page_contains_surface_tabs_and_zero_external_resources(self) -> None:
        # Check UI elements for ecosystem multi-surface preview
        self.assertIn("preview-surface-tabs", STUDIO_HTML)
        self.assertIn("switchSurface", STUDIO_HTML)

        # Zero external dependencies
        self.assertNotIn("http://", STUDIO_HTML)
        self.assertNotIn("https://", STUDIO_HTML)
        self.assertNotIn("<link", STUDIO_HTML)
        self.assertNotIn("<script src", STUDIO_HTML)


if __name__ == "__main__":
    unittest.main()

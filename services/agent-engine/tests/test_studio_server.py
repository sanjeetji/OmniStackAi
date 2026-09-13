"""Tests for the OmniStackAI Studio web server (studio/, R-418).

Deterministic and offline: the server is started on an ephemeral localhost port with an
in-memory stub build function (0 model calls, 0 external network); real HTTP requests are
made against it with stdlib urllib.
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.intake import app_build_result_to_dict, build_app_from_ir
from omnistackai_agent_engine.studio import STUDIO_HTML, create_studio_server

STUB_RESULT = {
    "prompt": "Build a recipe box",
    "name": "Recipe Box",
    "description": "A recipe box.",
    "entities": ["Recipe", "Ingredient"],
    "file_count": 154,
    "target_dir": "/tmp/recipe-box",
    "commit_sha": "abc123def4567890",
    "files": ["apps/web/app/page.tsx", "services/api/app/main.py"],
}

AUTHOR = {"author_name": "sanjeetji", "author_email": "sk698166@gmail.com"}


class RecordingBuild:
    def __init__(self, result: dict) -> None:
        self.result = result
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        return self.result


@contextmanager
def running_server(build_fn, **control_kwargs):
    server = create_studio_server(build_fn, host="127.0.0.1", port=0, **control_kwargs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _get(url: str):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def _post(url: str, *, obj=None, raw: bytes | None = None):
    body = raw if raw is not None else json.dumps(obj or {}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


class TestStudioPage(unittest.TestCase):
    def test_page_is_self_contained_html(self) -> None:
        self.assertTrue(STUDIO_HTML.lstrip().startswith("<!doctype html>"))
        for token in ('id="prompt"', "/api/build", "Build app", "OmniStackAI Studio"):
            self.assertIn(token, STUDIO_HTML)

    def test_page_has_no_external_resources(self) -> None:
        # No CDN/script/style/img pulling from the network — fully local.
        for bad in ("http://", "https://", "src=", "<link"):
            self.assertNotIn(bad, STUDIO_HTML)

    def test_page_has_sandboxed_live_preview_surface(self) -> None:
        for token in (
            'id="preview-frame"',
            'id="preview-status"',
            'id="preview-open"',
            'sandbox="allow-forms allow-modals allow-popups allow-same-origin allow-scripts"',
            'referrerpolicy="no-referrer"',
            "preview.web_url",
        ):
            self.assertIn(token, STUDIO_HTML)
        self.assertNotIn("preview.innerHTML", STUDIO_HTML)

    def test_page_has_preview_lifecycle_controls(self) -> None:
        for token in (
            'id="preview-stop"',
            'id="preview-restart"',
            "/api/preview/stop",
            "/api/preview/restart",
        ):
            self.assertIn(token, STUDIO_HTML)

    def test_page_polls_live_preview_status(self) -> None:
        # The page polls GET /api/preview on an interval to keep the preview surface accurate.
        self.assertIn("setInterval", STUDIO_HTML)
        self.assertIn("'/api/preview'", STUDIO_HTML)


class TestStudioServer(unittest.TestCase):
    def test_get_serves_page(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            status, body = _get(base + "/")
            self.assertEqual(status, 200)
            self.assertIn(b"OmniStackAI Studio", body)

    def test_healthz(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            status, body = _get(base + "/healthz")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["status"], "ok")

    def test_unknown_get_is_404(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            status, _ = _get(base + "/nope")
            self.assertEqual(status, 404)

    def test_post_build_success(self) -> None:
        build = RecordingBuild(STUB_RESULT)
        with running_server(build) as base:
            status, data = _post(base + "/api/build", obj={"prompt": "Build a recipe box"})
            self.assertEqual(status, 200)
            self.assertEqual(data["name"], "Recipe Box")
            self.assertEqual(data["file_count"], 154)
            self.assertEqual(build.prompts, ["Build a recipe box"])

    def test_successful_build_keeps_200_when_preview_launch_failed(self) -> None:
        result = {
            **STUB_RESULT,
            "preview": {
                "status": "error",
                "message": "Preview could not start. Stop other local app sessions and retry.",
            },
        }
        with running_server(RecordingBuild(result)) as base:
            status, data = _post(base + "/api/build", obj={"prompt": "Build a recipe box"})
            self.assertEqual(status, 200)
            self.assertEqual(data["name"], "Recipe Box")
            self.assertEqual(data["preview"]["status"], "error")

    def test_post_empty_prompt_is_400(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            status, data = _post(base + "/api/build", obj={"prompt": "   "})
            self.assertEqual(status, 400)
            self.assertIn("error", data)

    def test_post_invalid_json_is_400(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            status, data = _post(base + "/api/build", raw=b"not json{")
            self.assertEqual(status, 400)
            self.assertIn("error", data)

    def test_post_build_failure_is_502(self) -> None:
        def failing(prompt: str) -> dict:
            raise RuntimeError("model produced no valid IR")

        with running_server(failing) as base:
            status, data = _post(base + "/api/build", obj={"prompt": "Build a blog"})
            self.assertEqual(status, 502)
            self.assertIn("model produced no valid IR", data["error"])

    def test_unknown_post_is_404(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            status, _ = _post(base + "/api/other", obj={"prompt": "x"})
            self.assertEqual(status, 404)


class TestStudioPreviewControlRoutes(unittest.TestCase):
    READY = {"status": "ready", "web_url": "http://127.0.0.1:51234"}
    STOPPED = {"status": "stopped", "message": "Preview stopped."}

    def test_get_preview_status(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT), status_fn=lambda: self.READY) as base:
            status, data = _get(base + "/api/preview")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(data)["status"], "ready")

    def test_post_preview_stop(self) -> None:
        calls = []

        def stop_fn():
            calls.append("stop")
            return self.STOPPED

        with running_server(RecordingBuild(STUB_RESULT), stop_fn=stop_fn) as base:
            status, data = _post(base + "/api/preview/stop")
            self.assertEqual(status, 200)
            self.assertEqual(data["status"], "stopped")
            self.assertEqual(calls, ["stop"])

    def test_post_preview_restart(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT), restart_fn=lambda: self.READY) as base:
            status, data = _post(base + "/api/preview/restart")
            self.assertEqual(status, 200)
            self.assertEqual(data["status"], "ready")

    def test_control_routes_404_when_disabled(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            self.assertEqual(_get(base + "/api/preview")[0], 404)
            self.assertEqual(_post(base + "/api/preview/stop")[0], 404)
            self.assertEqual(_post(base + "/api/preview/restart")[0], 404)


class TestStudioHistoryRoutes(unittest.TestCase):
    HISTORY = {"builds": [{"id": "2", "name": "Blog"}, {"id": "1", "name": "Shop"}]}

    def test_get_history(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT), history_fn=lambda: self.HISTORY) as base:
            status, data = _get(base + "/api/history")
            self.assertEqual(status, 200)
            self.assertEqual(len(json.loads(data)["builds"]), 2)

    def test_post_history_preview_passes_id(self) -> None:
        seen = []

        def preview_build(build_id):
            seen.append(build_id)
            return {"status": "ready", "web_url": "http://127.0.0.1:51999"}

        with running_server(RecordingBuild(STUB_RESULT), preview_build_fn=preview_build) as base:
            status, data = _post(base + "/api/history/preview", obj={"id": "2"})
            self.assertEqual(status, 200)
            self.assertEqual(data["status"], "ready")
            self.assertEqual(seen, ["2"])

    def test_post_history_preview_missing_id_is_400(self) -> None:
        with running_server(
            RecordingBuild(STUB_RESULT), preview_build_fn=lambda build_id: {"status": "ready"}
        ) as base:
            status, data = _post(base + "/api/history/preview", obj={})
            self.assertEqual(status, 400)
            self.assertIn("error", data)

    def test_history_routes_404_when_disabled(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            self.assertEqual(_get(base + "/api/history")[0], 404)
            self.assertEqual(_post(base + "/api/history/preview", obj={"id": "1"})[0], 404)

    def test_page_has_recent_builds_surface(self) -> None:
        for token in ('id="history-list"', "/api/history", "/api/history/preview"):
            self.assertIn(token, STUDIO_HTML)


class TestResultDict(unittest.TestCase):
    def test_app_build_result_to_dict_shape(self) -> None:
        ir = example_ir("minimal-blog")
        with tempfile.TemporaryDirectory() as tmp:
            result = build_app_from_ir(ir, str(Path(tmp) / "app"), prompt="Build a blog", **AUTHOR)
            payload = app_build_result_to_dict(result)
            self.assertEqual(payload["prompt"], "Build a blog")
            self.assertEqual(payload["name"], ir.name)
            self.assertEqual(payload["file_count"], result.file_count)
            self.assertGreater(len(payload["files"]), 0)
            self.assertIn("apps/web/app/page.tsx", payload["files"])
            # No file lives inside the .git directory (".gitignore" is fine — it's a real file).
            self.assertTrue(
                all(part != ".git" for f in payload["files"] for part in f.split("/"))
            )
            json.dumps(payload)  # must be JSON-serializable


if __name__ == "__main__":
    unittest.main()

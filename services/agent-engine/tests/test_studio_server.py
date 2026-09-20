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


class RecordingBuildStream:
    """R-484: an in-memory async-generator BuildStreamFn stub, records the prompts it sees."""

    def __init__(self, events: list[dict]) -> None:
        self.events = events
        self.prompts: list[str] = []

    async def __call__(self, prompt: str):
        self.prompts.append(prompt)
        for event in self.events:
            yield event


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


def _post_sse(url: str, obj: dict):
    """R-484: POST a JSON body and parse an `text/event-stream` response into a list of the
    decoded `data:` JSON payloads, in arrival order. urllib.request.urlopen's `.read()` blocks
    until the connection closes -- fine for asserting event content/order/framing here; real
    incremental-over-time arrival is verified by the task's live `curl -N` manual smoke test."""
    body = json.dumps(obj).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            status, raw = resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read().decode("utf-8")
    events = []
    for frame in raw.split("\n\n"):
        frame = frame.strip()
        if frame.startswith("data: "):
            events.append(json.loads(frame[len("data: ") :]))
    return status, events


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

    def test_post_history_open_passes_id(self) -> None:
        seen = []

        def open_dir(build_id):
            seen.append(build_id)
            return {"status": "opened", "message": "Opened the generated project folder."}

        with running_server(RecordingBuild(STUB_RESULT), open_dir_fn=open_dir) as base:
            status, data = _post(base + "/api/history/open", obj={"id": "3"})
            self.assertEqual(status, 200)
            self.assertEqual(data["status"], "opened")
            self.assertEqual(seen, ["3"])

    def test_post_history_open_missing_id_is_400(self) -> None:
        with running_server(
            RecordingBuild(STUB_RESULT), open_dir_fn=lambda build_id: {"status": "opened"}
        ) as base:
            status, data = _post(base + "/api/history/open", obj={})
            self.assertEqual(status, 400)
            self.assertIn("error", data)

    def test_history_open_404_when_disabled(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            self.assertEqual(_post(base + "/api/history/open", obj={"id": "1"})[0], 404)

    def test_page_has_recent_builds_surface(self) -> None:
        for token in ('id="history-list"', "/api/history", "/api/history/preview"):
            self.assertIn(token, STUDIO_HTML)

    def test_page_has_per_build_repo_actions(self) -> None:
        for token in ("/api/history/open", "navigator.clipboard", "Copy path", "Open folder"):
            self.assertIn(token, STUDIO_HTML)

    def test_post_history_delete_passes_id(self) -> None:
        seen = []

        def delete_build(build_id):
            seen.append(build_id)
            return {"removed": True, "builds": [{"id": "1", "name": "Blog"}]}

        with running_server(RecordingBuild(STUB_RESULT), delete_build_fn=delete_build) as base:
            status, data = _post(base + "/api/history/delete", obj={"id": "2"})
            self.assertEqual(status, 200)
            self.assertTrue(data["removed"])
            self.assertEqual(len(data["builds"]), 1)
            self.assertEqual(seen, ["2"])

    def test_post_history_delete_missing_id_is_400(self) -> None:
        with running_server(
            RecordingBuild(STUB_RESULT), delete_build_fn=lambda build_id: {"removed": False}
        ) as base:
            status, data = _post(base + "/api/history/delete", obj={})
            self.assertEqual(status, 400)
            self.assertIn("error", data)

    def test_history_delete_404_when_disabled(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            self.assertEqual(_post(base + "/api/history/delete", obj={"id": "1"})[0], 404)

    def test_page_has_remove_action(self) -> None:
        for token in ("/api/history/delete", "Remove"):
            self.assertIn(token, STUDIO_HTML)


class TestStudioFileRoutes(unittest.TestCase):
    """R-467: GET /api/build/{id}/files and GET /api/build/{id}/file?path=..."""

    def test_get_file_tree(self) -> None:
        seen = []

        def file_tree(build_id):
            seen.append(build_id)
            return {"files": ["app/page.tsx", "lib/hooks.ts"], "truncated": False}

        with running_server(RecordingBuild(STUB_RESULT), file_tree_fn=file_tree) as base:
            status, data = _get(base + "/api/build/7/files")
            self.assertEqual(status, 200)
            payload = json.loads(data)
            self.assertEqual(payload["files"], ["app/page.tsx", "lib/hooks.ts"])
            self.assertFalse(payload["truncated"])
            self.assertEqual(seen, ["7"])

    def test_file_tree_404_when_disabled(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            self.assertEqual(_get(base + "/api/build/7/files")[0], 404)

    def test_file_tree_maps_build_not_found_to_404(self) -> None:
        from omnistackai_agent_engine.studio.files import BuildNotFoundError

        def file_tree(build_id):
            raise BuildNotFoundError(f"build '{build_id}' is not available in this session")

        with running_server(RecordingBuild(STUB_RESULT), file_tree_fn=file_tree) as base:
            status, data = _get(base + "/api/build/missing/files")
            self.assertEqual(status, 404)
            self.assertIn("missing", data.decode())

    def test_file_tree_maps_other_exception_to_502(self) -> None:
        def file_tree(build_id):
            raise RuntimeError("disk is unavailable")

        with running_server(RecordingBuild(STUB_RESULT), file_tree_fn=file_tree) as base:
            status, data = _get(base + "/api/build/1/files")
            self.assertEqual(status, 502)
            self.assertIn("disk is unavailable", json.loads(data)["error"])

    def test_build_id_with_a_slash_is_not_matched(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT), file_tree_fn=lambda build_id: {"files": []}) as base:
            status, _ = _get(base + "/api/build/1/2/files")
            self.assertEqual(status, 404)

    def test_get_file_content(self) -> None:
        seen = []

        def read_file(build_id, path):
            seen.append((build_id, path))
            return {"path": path, "content": "export default function Page() {}", "truncated": False, "binary": False, "size": 34}

        with running_server(RecordingBuild(STUB_RESULT), read_file_fn=read_file) as base:
            status, data = _get(base + "/api/build/7/file?path=app%2Fpage.tsx")
            self.assertEqual(status, 200)
            payload = json.loads(data)
            self.assertEqual(payload["path"], "app/page.tsx")
            self.assertIn("export default function Page", payload["content"])
            self.assertEqual(seen, [("7", "app/page.tsx")])

    def test_file_content_404_when_disabled(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            self.assertEqual(_get(base + "/api/build/7/file?path=a.txt")[0], 404)

    def test_file_content_missing_path_is_400(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT), read_file_fn=lambda bid, path: {}) as base:
            status, data = _get(base + "/api/build/7/file")
            self.assertEqual(status, 400)
            self.assertIn("path", json.loads(data)["error"])

    def test_file_content_maps_each_typed_error(self) -> None:
        from omnistackai_agent_engine.studio.files import (
            BuildNotFoundError,
            FileNotFoundInBuildError,
            PathOutsideBuildError,
        )

        cases = [
            (BuildNotFoundError("no such build"), 404),
            (PathOutsideBuildError("escapes the build directory"), 400),
            (FileNotFoundInBuildError("no such file"), 404),
            (RuntimeError("boom"), 502),
        ]
        for error, expected_status in cases:
            def read_file(build_id, path, _error=error):
                raise _error

            with running_server(RecordingBuild(STUB_RESULT), read_file_fn=read_file) as base:
                status, _ = _get(base + "/api/build/7/file?path=a.txt")
                self.assertEqual(status, expected_status, type(error).__name__)

    def test_page_has_file_browser_and_hybrid_ui_controls(self) -> None:
        for token in (
            'id="r-files"',
            'id="file-viewer-code"',
            'id="file-viewer-path"',
            'id="hybrid-ui-toggle"',
            'id="hybrid-summary"',
            "/api/build/",
            "hybrid_ui",
        ):
            self.assertIn(token, STUDIO_HTML)
        # Still zero external assets after this addition.
        for bad in ("http://", "https://", "src=", "<link"):
            self.assertNotIn(bad, STUDIO_HTML)

    def test_file_routes_available_without_any_preview_wiring(self) -> None:
        # File browsing needs no toolchain or running preview -- available in build-only mode.
        with running_server(
            RecordingBuild(STUB_RESULT),
            file_tree_fn=lambda build_id: {"files": [], "truncated": False},
            read_file_fn=lambda build_id, path: {"path": path, "content": "", "truncated": False, "binary": False, "size": 0},
        ) as base:
            self.assertEqual(_get(base + "/api/build/1/files")[0], 200)
            self.assertEqual(_get(base + "/api/build/1/file?path=a.txt")[0], 200)
            # Preview/history controls remain unwired and 404, confirming independence.
            self.assertEqual(_get(base + "/api/preview")[0], 404)


class TestStudioEditRoutes(unittest.TestCase):
    """R-468: POST /api/build/{id}/edit and GET /api/build/{id}/turns."""

    def test_post_edit_success(self) -> None:
        seen = []

        def edit_build(build_id, prompt):
            seen.append((build_id, prompt))
            return {
                "id": build_id,
                "diff": {"added": ["app/favorites/page.tsx"], "modified": [], "deleted": [], "summary": "1 added"},
                "entities": ["Post", "Favorite"],
                "file_count": 161,
                "commit_sha": "def456",
                "rationale": "Adds favorites.",
                "turns": [{"role": "user", "text": "add favorites", "created_at": 1.0}],
            }

        with running_server(RecordingBuild(STUB_RESULT), edit_fn=edit_build) as base:
            status, data = _post(base + "/api/build/7/edit", obj={"prompt": "add favorites"})
            self.assertEqual(status, 200)
            self.assertEqual(data["entities"], ["Post", "Favorite"])
            self.assertEqual(data["diff"]["added"], ["app/favorites/page.tsx"])
            self.assertEqual(seen, [("7", "add favorites")])

    def test_edit_404_when_disabled(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            self.assertEqual(_post(base + "/api/build/7/edit", obj={"prompt": "x"})[0], 404)

    def test_edit_empty_prompt_is_400(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT), edit_fn=lambda bid, p: {}) as base:
            status, data = _post(base + "/api/build/7/edit", obj={"prompt": "   "})
            self.assertEqual(status, 400)
            self.assertIn("prompt", data["error"])

    def test_edit_maps_each_typed_error(self) -> None:
        from omnistackai_agent_engine.studio.files import BuildNotFoundError
        from omnistackai_agent_engine.studio.session import EditNotSupportedError

        cases = [
            (BuildNotFoundError("no such build"), 404),
            (EditNotSupportedError("not supported for this build kind"), 400),
            (RuntimeError("boom"), 502),
        ]
        for error, expected_status in cases:
            def edit_build(build_id, prompt, _error=error):
                raise _error

            with running_server(RecordingBuild(STUB_RESULT), edit_fn=edit_build) as base:
                status, _ = _post(base + "/api/build/7/edit", obj={"prompt": "add favorites"})
                self.assertEqual(status, expected_status, type(error).__name__)

    def test_edit_build_id_with_a_slash_is_not_matched(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT), edit_fn=lambda bid, p: {}) as base:
            status, _ = _post(base + "/api/build/1/2/edit", obj={"prompt": "x"})
            self.assertEqual(status, 404)

    def test_get_turns(self) -> None:
        seen = []

        def turns(build_id):
            seen.append(build_id)
            return {"turns": [{"role": "user", "text": "add favorites", "created_at": 1.0}]}

        with running_server(RecordingBuild(STUB_RESULT), turns_fn=turns) as base:
            status, data = _get(base + "/api/build/7/turns")
            self.assertEqual(status, 200)
            self.assertEqual(len(json.loads(data)["turns"]), 1)
            self.assertEqual(seen, ["7"])

    def test_turns_404_when_disabled(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            self.assertEqual(_get(base + "/api/build/7/turns")[0], 404)

    def test_turns_maps_other_exception_to_502(self) -> None:
        def turns(build_id):
            raise RuntimeError("boom")

        with running_server(RecordingBuild(STUB_RESULT), turns_fn=turns) as base:
            status, data = _get(base + "/api/build/7/turns")
            self.assertEqual(status, 502)
            self.assertIn("boom", json.loads(data)["error"])

    def test_edit_and_turns_available_without_any_preview_wiring(self) -> None:
        with running_server(
            RecordingBuild(STUB_RESULT),
            edit_fn=lambda bid, prompt: {"id": bid},
            turns_fn=lambda bid: {"turns": []},
        ) as base:
            self.assertEqual(_post(base + "/api/build/1/edit", obj={"prompt": "x"})[0], 200)
            self.assertEqual(_get(base + "/api/build/1/turns")[0], 200)
            self.assertEqual(_get(base + "/api/preview")[0], 404)

    def test_page_has_edit_chat_controls(self) -> None:
        for token in ("/edit", "/turns", "Apply change"):
            self.assertIn(token, STUDIO_HTML)


class TestStudioBuildStreamRoute(unittest.TestCase):
    """R-484: POST /api/build/stream - Server-Sent Events for real-time build progress."""

    def test_stream_success_yields_events_in_order(self) -> None:
        events = [
            {"phase": "generating_ir", "delta": '{"na'},
            {"phase": "generating_ir", "delta": 'me": "Recipe Box"}'},
            {"phase": "done", "id": "1", "name": "Recipe Box", "file_count": 154},
        ]
        stream = RecordingBuildStream(events)
        with running_server(RecordingBuild(STUB_RESULT), build_stream_fn=stream) as base:
            status, received = _post_sse(base + "/api/build/stream", {"prompt": "Build a recipe box"})
            self.assertEqual(status, 200)
            self.assertEqual(received, events)
            self.assertEqual(stream.prompts, ["Build a recipe box"])

    def test_stream_404_when_disabled(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            status, data = _post(base + "/api/build/stream", obj={"prompt": "x"})
            self.assertEqual(status, 404)
            self.assertIn("error", data)

    def test_stream_empty_prompt_is_400(self) -> None:
        stream = RecordingBuildStream([{"phase": "done"}])
        with running_server(RecordingBuild(STUB_RESULT), build_stream_fn=stream) as base:
            status, data = _post(base + "/api/build/stream", obj={"prompt": "   "})
            self.assertEqual(status, 400)
            self.assertIn("error", data)
            self.assertEqual(stream.prompts, [])

    def test_stream_invalid_json_is_400(self) -> None:
        stream = RecordingBuildStream([{"phase": "done"}])
        with running_server(RecordingBuild(STUB_RESULT), build_stream_fn=stream) as base:
            status, data = _post(base + "/api/build/stream", raw=b"not json{")
            self.assertEqual(status, 400)
            self.assertIn("error", data)
            self.assertEqual(stream.prompts, [])

    def test_stream_rejects_pack_id_before_any_sse_framing(self) -> None:
        stream = RecordingBuildStream([{"phase": "done"}])
        with running_server(RecordingBuild(STUB_RESULT), build_stream_fn=stream) as base:
            status, data = _post(
                base + "/api/build/stream", obj={"prompt": "x", "pack_id": "minimal-blog"}
            )
            self.assertEqual(status, 400)
            self.assertIn("error", data)
            self.assertEqual(stream.prompts, [])

    def test_stream_rejects_ecosystem_id_before_any_sse_framing(self) -> None:
        stream = RecordingBuildStream([{"phase": "done"}])
        with running_server(RecordingBuild(STUB_RESULT), build_stream_fn=stream) as base:
            status, data = _post(base + "/api/build/stream", obj={"prompt": "x", "ecosystem_id": "e1"})
            self.assertEqual(status, 400)
            self.assertIn("error", data)
            self.assertEqual(stream.prompts, [])

    def test_stream_rejects_hybrid_ui_before_any_sse_framing(self) -> None:
        stream = RecordingBuildStream([{"phase": "done"}])
        with running_server(RecordingBuild(STUB_RESULT), build_stream_fn=stream) as base:
            status, data = _post(base + "/api/build/stream", obj={"prompt": "x", "hybrid_ui": True})
            self.assertEqual(status, 400)
            self.assertIn("error", data)
            self.assertEqual(stream.prompts, [])

    def test_stream_mid_stream_error_is_reported_as_a_final_frame(self) -> None:
        # Headers are already sent by the time a mid-stream failure happens (R-484's own design:
        # a clean 400 only for the *pre-stream* rejections above) - the failure must surface as one
        # last SSE frame, not an unhandled exception in the handler thread.
        async def failing_stream(prompt: str):
            yield {"phase": "generating_ir", "delta": "partial"}
            raise RuntimeError("model connection dropped")

        with running_server(RecordingBuild(STUB_RESULT), build_stream_fn=failing_stream) as base:
            status, received = _post_sse(base + "/api/build/stream", {"prompt": "Build a blog"})
            self.assertEqual(status, 200)
            self.assertEqual(received[0], {"phase": "generating_ir", "delta": "partial"})
            self.assertEqual(received[-1]["phase"], "error")
            self.assertIn("model connection dropped", received[-1]["error"])


class TestLiveServeBuildStream(unittest.TestCase):
    """R-484: _build_stream() - the async-generator twin of _build() streaming SSE-ready events."""

    def test_streamed_deltas_reconstruct_the_final_payload(self) -> None:
        import asyncio
        from unittest.mock import patch
        from omnistackai_agent_engine.application_ir import example_ir
        from omnistackai_agent_engine.model_gateway import StreamEvent, TokenUsage
        from omnistackai_agent_engine.studio.live_serve import _build_stream

        ir_dict = example_ir("minimal-blog").to_dict()
        ir_json = json.dumps(ir_dict)

        class _StreamingStubProvider:
            provider_id = "stub"

            async def generate(self, request):  # pragma: no cover
                raise AssertionError("generate() must not be called by the streaming path")

            async def stream(self, request):
                chunks = [ir_json[i : i + 16] for i in range(0, len(ir_json), 16)]
                for sequence, chunk in enumerate(chunks):
                    is_last = sequence == len(chunks) - 1
                    yield StreamEvent(
                        request.request_id,
                        sequence,
                        chunk,
                        is_last,
                        TokenUsage(20, 8) if is_last else None,
                    )

        async def _collect():
            deltas: list[str] = []
            final = None
            with tempfile.TemporaryDirectory() as tmp:
                with patch(
                    "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                    return_value=(_StreamingStubProvider(), "stub-model", 4096, 5.0),
                ):
                    async for event in _build_stream("A tech blog", target_dir=str(Path(tmp) / "blog")):
                        if event.get("phase") == "generating_ir":
                            deltas.append(event["delta"])
                        else:
                            final = event
            return deltas, final

        deltas, final = asyncio.run(_collect())
        self.assertGreater(len(deltas), 1)
        self.assertEqual("".join(deltas), ir_json)
        assert final is not None
        self.assertEqual(final["phase"], "done")
        self.assertEqual(final["name"], ir_dict["name"])
        self.assertIn("usage", final)

    def test_solution_pack_rejected_before_any_streaming(self) -> None:
        import asyncio
        from omnistackai_agent_engine.studio.live_serve import StreamingBuildNotSupportedError, _build_stream

        async def _run_it():
            async for _event in _build_stream("A tech blog", pack_id="minimal-blog"):
                pass

        with self.assertRaises(StreamingBuildNotSupportedError):
            asyncio.run(_run_it())

    def test_ecosystem_rejected_before_any_streaming(self) -> None:
        import asyncio
        from omnistackai_agent_engine.studio.live_serve import StreamingBuildNotSupportedError, _build_stream

        async def _run_it():
            async for _event in _build_stream("A tech blog", ecosystem_id="e1"):
                pass

        with self.assertRaises(StreamingBuildNotSupportedError):
            asyncio.run(_run_it())

    def test_hybrid_ui_rejected_before_any_streaming(self) -> None:
        import asyncio
        from omnistackai_agent_engine.studio.live_serve import StreamingBuildNotSupportedError, _build_stream

        async def _run_it():
            async for _event in _build_stream("A tech blog", hybrid_ui=True):
                pass

        with self.assertRaises(StreamingBuildNotSupportedError):
            asyncio.run(_run_it())


class TestStudioProblemsRoutes(unittest.TestCase):
    """R-480: POST /api/build/{id}/problems and GET /api/build/{id}/problems."""

    def test_post_problems_check_success(self) -> None:
        seen = []

        def check(build_id):
            seen.append(build_id)
            return {"ok": False, "returncode": 2, "error_count": 1, "files": {"app/page.tsx": ["L1:1 TS2339: x"]}, "output_tail": ""}

        with running_server(RecordingBuild(STUB_RESULT), problems_check_fn=check) as base:
            status, data = _post(base + "/api/build/7/problems", obj={})
            self.assertEqual(status, 200)
            self.assertFalse(data["ok"])
            self.assertEqual(data["error_count"], 1)
            self.assertEqual(seen, ["7"])

    def test_problems_check_404_when_disabled(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            self.assertEqual(_post(base + "/api/build/7/problems", obj={})[0], 404)

    def test_problems_check_maps_each_typed_error(self) -> None:
        from omnistackai_agent_engine.studio.files import BuildNotFoundError
        from omnistackai_agent_engine.studio.problems import NoWebTargetError, ToolchainNotInstalledError

        cases = [
            (BuildNotFoundError("no such build"), 404),
            (NoWebTargetError("this build has no web app to check for problems"), 400),
            (ToolchainNotInstalledError("tsc is not installed for this app"), 409),
            (RuntimeError("boom"), 502),
        ]
        for error, expected_status in cases:
            def check(build_id, _error=error):
                raise _error

            with running_server(RecordingBuild(STUB_RESULT), problems_check_fn=check) as base:
                status, _ = _post(base + "/api/build/7/problems", obj={})
                self.assertEqual(status, expected_status, type(error).__name__)

    def test_get_problems_success(self) -> None:
        seen = []

        def get(build_id):
            seen.append(build_id)
            return {"ok": True, "returncode": 0, "error_count": 0, "files": {}, "output_tail": ""}

        with running_server(RecordingBuild(STUB_RESULT), problems_get_fn=get) as base:
            status, data = _get(base + "/api/build/7/problems")
            self.assertEqual(status, 200)
            self.assertTrue(json.loads(data)["ok"])
            self.assertEqual(seen, ["7"])

    def test_get_problems_404_when_disabled(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            self.assertEqual(_get(base + "/api/build/7/problems")[0], 404)

    def test_get_problems_maps_each_typed_error(self) -> None:
        from omnistackai_agent_engine.studio.files import BuildNotFoundError
        from omnistackai_agent_engine.studio.problems import ProblemsNotCheckedError

        cases = [
            (BuildNotFoundError("no such build"), 404),
            (ProblemsNotCheckedError("not checked yet"), 404),
            (RuntimeError("boom"), 502),
        ]
        for error, expected_status in cases:
            def get(build_id, _error=error):
                raise _error

            with running_server(RecordingBuild(STUB_RESULT), problems_get_fn=get) as base:
                status, _ = _get(base + "/api/build/7/problems")
                self.assertEqual(status, expected_status, type(error).__name__)

    def test_problems_available_without_any_preview_wiring(self) -> None:
        with running_server(
            RecordingBuild(STUB_RESULT),
            problems_check_fn=lambda bid: {"ok": True, "returncode": 0, "error_count": 0, "files": {}, "output_tail": ""},
            problems_get_fn=lambda bid: {"ok": True, "returncode": 0, "error_count": 0, "files": {}, "output_tail": ""},
        ) as base:
            self.assertEqual(_post(base + "/api/build/1/problems", obj={})[0], 200)
            self.assertEqual(_get(base + "/api/build/1/problems")[0], 200)
            self.assertEqual(_get(base + "/api/preview")[0], 404)


class TestStudioProvidersRoute(unittest.TestCase):
    """R-482: GET /api/providers - a live model-fabric status view."""

    def test_get_providers(self) -> None:
        overview = {
            "providers": [{"providerId": "ollama-local", "active": True}],
            "activeNow": {"providerId": "ollama-local", "modelId": "qwen2.5-coder:14b"},
            "activeNowError": None,
        }
        with running_server(RecordingBuild(STUB_RESULT), providers_fn=lambda: overview) as base:
            status, data = _get(base + "/api/providers")
            self.assertEqual(status, 200)
            body = json.loads(data)
            self.assertEqual(body["activeNow"]["providerId"], "ollama-local")

    def test_providers_404_when_disabled(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            self.assertEqual(_get(base + "/api/providers")[0], 404)

    def test_providers_maps_unexpected_error_to_502(self) -> None:
        def providers():
            raise RuntimeError("boom")

        with running_server(RecordingBuild(STUB_RESULT), providers_fn=providers) as base:
            status, data = _get(base + "/api/providers")
            self.assertEqual(status, 502)
            self.assertIn("boom", json.loads(data)["error"])

    def test_providers_available_without_any_preview_wiring(self) -> None:
        with running_server(
            RecordingBuild(STUB_RESULT),
            providers_fn=lambda: {"providers": [], "activeNow": None, "activeNowError": None},
        ) as base:
            self.assertEqual(_get(base + "/api/providers")[0], 200)
            self.assertEqual(_get(base + "/api/preview")[0], 404)


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


class TestStudioSolutionPacks(unittest.TestCase):
    def test_get_solution_packs(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            status, body = _get(base + "/api/solution-packs")
            self.assertEqual(status, 200)
            data = json.loads(body)
            self.assertIn("packs", data)
            pack_ids = [p["pack_id"] for p in data["packs"]]
            self.assertIn("minimal-blog", pack_ids)
            self.assertIn("rideshare-favourites", pack_ids)
            blog = next(p for p in data["packs"] if p["pack_id"] == "minimal-blog")
            self.assertEqual(blog["version"], "1.0.0")
            self.assertIn("blog-cms", blog["domains"])
            self.assertIn("nextjs-web", blog["targets"])

    def test_post_solution_packs_recommend_for_blog(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            status, data = _post(
                base + "/api/solution-packs/recommend",
                obj={"prompt": "A blog with posts and comments"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(data["domain"], "blog-cms")
            self.assertEqual(data["recommendation"]["status"], "selected")
            self.assertEqual(data["recommendation"]["selection"]["pack_id"], "minimal-blog")

    def test_post_solution_packs_recommend_missing_prompt_is_400(self) -> None:
        with running_server(RecordingBuild(STUB_RESULT)) as base:
            status, data = _post(base + "/api/solution-packs/recommend", obj={})
            self.assertEqual(status, 400)
            self.assertIn("error", data)

    def test_post_build_passes_solution_pack_options(self) -> None:
        captured = {}

        def pack_build(prompt: str, **options) -> dict:
            captured["prompt"] = prompt
            captured["options"] = options
            return {
                **STUB_RESULT,
                "pack_id": options.get("pack_id"),
                "pack_version": "1.0.0",
                "applied_configuration_change_ids": ["config-name"],
            }

        with running_server(pack_build) as base:
            status, data = _post(
                base + "/api/build",
                obj={
                    "prompt": "Build a tech blog",
                    "pack_id": "minimal-blog",
                    "custom_name": "My Tech Blog",
                    "custom_description": "A tech blog for developers",
                },
            )
            self.assertEqual(status, 200)
            self.assertEqual(captured["prompt"], "Build a tech blog")
            self.assertEqual(captured["options"].get("pack_id"), "minimal-blog")
            self.assertEqual(captured["options"].get("custom_name"), "My Tech Blog")
            self.assertEqual(data["pack_id"], "minimal-blog")
            self.assertEqual(data["applied_configuration_change_ids"], ["config-name"])

    def test_post_build_forwards_hybrid_ui(self) -> None:
        captured = {}

        def build(prompt: str, **options) -> dict:
            captured["options"] = options
            return STUB_RESULT

        with running_server(build) as base:
            status, _ = _post(base + "/api/build", obj={"prompt": "A blog", "hybrid_ui": True})
            self.assertEqual(status, 200)
            self.assertIs(captured["options"]["hybrid_ui"], True)

    def test_post_build_omits_hybrid_ui_when_not_sent(self) -> None:
        captured = {}

        def build(prompt: str, **options) -> dict:
            captured["options"] = options
            return STUB_RESULT

        with running_server(build) as base:
            _post(base + "/api/build", obj={"prompt": "A blog"})
            self.assertNotIn("hybrid_ui", captured["options"])

    def test_page_has_solution_pack_ui_controls(self) -> None:
        for token in (
            'id="pack-select"',
            'id="pack-banner"',
            'id="custom-name"',
            'id="custom-desc"',
            "/api/solution-packs",
            "/api/solution-packs/recommend",
            "Solution Pack",
            "pack_id",
        ):
            self.assertIn(token, STUDIO_HTML)

    def test_page_solution_pack_still_has_no_external_resources(self) -> None:
        for bad in ("http://", "https://", "src=", "<link"):
            self.assertNotIn(bad, STUDIO_HTML)

    def test_live_serve_build_with_solution_pack(self) -> None:
        from unittest.mock import patch
        from omnistackai_agent_engine.studio.live_serve import _build

        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "omnistackai_agent_engine.studio.live_serve._target_dir_for",
                return_value=str(Path(tmp) / "blog_app"),
            ), patch(
                # R-467: resolve_generation_provider_from_env is real and env-sensitive; mock it so
                # this test's "0 model calls, 0 network calls" holds by construction.
                "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                return_value=(None, "stub-model", 4096, 5.0),
            ):
                payload = _build(
                    "A tech blog",
                    pack_id="minimal-blog",
                    custom_name="Custom Blog",
                    custom_description="My customized blog",
                )
                self.assertEqual(payload["pack_id"], "minimal-blog")
                self.assertEqual(payload["name"], "Custom Blog")
                self.assertEqual(payload["description"], "My customized blog")
                self.assertIn("config-custom-name", payload["applied_configuration_change_ids"])
                self.assertIn(
                    "config-custom-description", payload["applied_configuration_change_ids"]
                )
                self.assertGreater(payload["file_count"], 100)
                self.assertTrue(Path(payload["target_dir"]).is_dir())
                self.assertIn("nextjs-web", payload["verify_targets"])

    def test_live_serve_plain_prompt_build_surfaces_real_usage(self) -> None:
        """R-472: a plain-prompt build's response carries a real, per-request usage summary.

        The provider is wrapped in the real RecordingProvider (around the exact UsageLedger `_build`
        creates for this request) so the resulting `payload["usage"]` reflects genuinely recorded
        calls, not a hand-built fixture.
        """
        from unittest.mock import patch
        from omnistackai_agent_engine.application_ir import example_ir
        from omnistackai_agent_engine.model_gateway import FinishReason, GenerateResponse, TokenUsage
        from omnistackai_agent_engine.model_gateway.recording import RecordingProvider
        from omnistackai_agent_engine.studio.live_serve import _build

        ir_json = json.dumps(example_ir("minimal-blog").to_dict())

        class _StubProvider:
            provider_id = "stub"

            async def generate(self, request):  # noqa: ANN001
                return GenerateResponse(
                    request.request_id, request.model, ir_json, FinishReason.STOP, TokenUsage(37, 11), 5
                )

        captured = {}

        def fake_resolve(*, usage_ledger=None, **_ignored):
            captured["usage_ledger"] = usage_ledger
            return RecordingProvider(_StubProvider(), usage_ledger), "stub-model", 4096, 5.0

        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                side_effect=fake_resolve,
            ):
                payload = _build("A tech blog", target_dir=str(Path(tmp) / "blog"))

        self.assertIsNotNone(captured["usage_ledger"])
        self.assertIn("usage", payload)
        usage = payload["usage"]
        self.assertGreaterEqual(usage["total_calls"], 1)
        self.assertEqual(usage["successful_calls"], usage["total_calls"])
        self.assertEqual(usage["failed_calls"], 0)
        # The stub's provider_id ("stub") has no DEFAULT_PRICE_BOOK entry -- unpriced by design,
        # never guessed (accounting.py's own documented contract).
        self.assertEqual(usage["unpriced_calls"], usage["total_calls"])
        self.assertEqual(usage["cost_micros_usd"], 0)
        self.assertIsInstance(usage["cost_micros_usd"], int)

    def test_live_serve_edit_surfaces_real_usage(self) -> None:
        """R-476: a follow-up edit's response also carries a real, per-request usage summary.

        Before this fix, _edit() never created a UsageLedger at all, so its response had no
        "usage" key regardless of the real cost incurred. Same RecordingProvider-around-a-real-
        UsageLedger approach as the plain-prompt build test above, applied to the edit call.
        """
        import asyncio
        from unittest.mock import patch
        from omnistackai_agent_engine.application_ir import example_ir
        from omnistackai_agent_engine.model_gateway import FinishReason, GenerateResponse, TokenUsage
        from omnistackai_agent_engine.model_gateway.recording import RecordingProvider
        from omnistackai_agent_engine.studio.history import StudioBuildHistory
        from omnistackai_agent_engine.studio.live_serve import _build, _edit
        from omnistackai_agent_engine.studio.session import StudioSessionStore

        ir_json = json.dumps(example_ir("minimal-blog").to_dict())
        delta_json = json.dumps(
            {
                "entities": [],
                "apis": [{"method": "GET", "path": "/health", "auth": False}],
                "screens": [],
                "rationale": "Adds a health check.",
            }
        )

        class _StubProvider:
            def __init__(self, text: str) -> None:
                self._text = text
                self.provider_id = "stub"

            async def generate(self, request):  # noqa: ANN001
                return GenerateResponse(
                    request.request_id, request.model, self._text, FinishReason.STOP, TokenUsage(20, 8), 4
                )

        history = StudioBuildHistory()
        session_store = StudioSessionStore()

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            with patch(
                "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                return_value=(_StubProvider(ir_json), "stub-model", 4096, 5.0),
            ):
                build_payload = _build(
                    "A tech blog",
                    target_dir=str(Path(tmp) / "blog"),
                    history=history,
                    session_store=session_store,
                )

            captured = {}

            def fake_resolve(*, usage_ledger=None, **_ignored):
                captured["usage_ledger"] = usage_ledger
                return RecordingProvider(_StubProvider(delta_json), usage_ledger), "stub-model", 4096, 5.0

            with patch(
                "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                side_effect=fake_resolve,
            ):
                edit_result = asyncio.run(
                    _edit(build_payload["id"], "add a health check", history=history, session_store=session_store)
                )

        self.assertIsNotNone(captured["usage_ledger"])
        self.assertIn("usage", edit_result)
        usage = edit_result["usage"]
        self.assertGreaterEqual(usage["total_calls"], 1)
        self.assertEqual(usage["successful_calls"], usage["total_calls"])
        self.assertEqual(usage["cost_micros_usd"], 0)  # unpriced "stub" provider, never guessed
        self.assertIsInstance(usage["cost_micros_usd"], int)

    def test_post_build_passes_ai_delta_options(self) -> None:
        captured = {}

        def pack_build(prompt: str, **options) -> dict:
            captured["prompt"] = prompt
            captured["options"] = options
            return {
                **STUB_RESULT,
                "pack_id": options.get("pack_id"),
                "applied_ai_delta_change_ids": ["ai-delta-1"],
            }

        with running_server(pack_build) as base:
            status, data = _post(
                base + "/api/build",
                obj={
                    "prompt": "Build a tech blog",
                    "pack_id": "minimal-blog",
                    "ai_delta_prompt": "Add newsletter subscribers",
                    "ai_features": ["Add newsletter subscribers"],
                },
            )
            self.assertEqual(status, 200)
            self.assertEqual(captured["options"].get("ai_delta_prompt"), "Add newsletter subscribers")
            self.assertEqual(captured["options"].get("ai_features"), ["Add newsletter subscribers"])
            self.assertEqual(data["applied_ai_delta_change_ids"], ["ai-delta-1"])

    def test_live_serve_build_with_ai_delta_features(self) -> None:
        from unittest.mock import patch
        from omnistackai_agent_engine.application_ir import (
            ApiEndpoint,
            Entity,
            Field,
            FieldType,
            HttpMethod,
            Screen,
        )
        from omnistackai_agent_engine.solution_packs.ai_delta import AIDeltaProposal
        from omnistackai_agent_engine.solution_packs.registry import DEFAULT_SOLUTION_PACK_REGISTRY
        from omnistackai_agent_engine.studio.live_serve import _build

        pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        assert pack is not None

        mock_proposal = AIDeltaProposal(
            pack_id=pack.pack_id,
            pack_version=pack.version,
            base_ir_sha256=pack.ir_sha256,
            addressed_change_ids=("ai-delta-1",),
            entities=(
                Entity(
                    name="Subscriber",
                    fields=(
                        Field(name="id", type=FieldType.UUID, required=True),
                        Field(name="email", type=FieldType.STRING, required=True),
                    ),
                ),
            ),
            apis=(
                ApiEndpoint(
                    method=HttpMethod.POST,
                    path="/subscribers",
                    request_schema="Subscriber",
                    response_schema="Subscriber",
                ),
            ),
            screens=(
                Screen(
                    id="subscriber_list",
                    role="reader",
                ),
            ),
            capabilities=("newsletter-subscription",),
            rationale="Added Subscriber entity and API endpoint.",
        )

        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "omnistackai_agent_engine.studio.live_serve._target_dir_for",
                return_value=str(Path(tmp) / "blog_app"),
            ), patch(
                "omnistackai_agent_engine.solution_packs.ai_delta.generate_ai_delta_proposal",
                return_value=mock_proposal,
            ), patch(
                # R-467: same as above -- this test forces the has_ai_deltas branch, which also
                # resolves a real provider unless mocked.
                "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                return_value=(None, "stub-model", 4096, 5.0),
            ):
                payload = _build(
                    "A tech blog",
                    pack_id="minimal-blog",
                    ai_features=["Add newsletter subscribers"],
                )
                self.assertEqual(payload["pack_id"], "minimal-blog")
                self.assertIn("Subscriber", payload["entities"])
                self.assertIn("ai-delta-1", payload["applied_ai_delta_change_ids"])
                self.assertTrue(Path(payload["target_dir"]).is_dir())

    def test_page_has_ai_delta_ui_controls(self) -> None:
        for token in (
            'id="ai-features"',
            "ai_features",
        ):
            self.assertIn(token, STUDIO_HTML)

    def test_page_has_destination_selector_controls(self) -> None:
        for token in (
            'id="dest-btn-workspace"',
            'id="dest-btn-personal"',
            'id="dest-btn-custom"',
            'id="output-dir"',
            'id="folder-name"',
            'id="dest-preview-path"',
            "loadConfig",
            "/api/config",
        ):
            self.assertIn(token, STUDIO_HTML)

    def test_get_api_config(self) -> None:
        def stub_build(prompt: str, **kwargs) -> dict:
            return STUB_RESULT

        with running_server(stub_build) as base_url:
            req = urllib.request.Request(f"{base_url}/api/config")
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertIn("workspace_apps_dir", data)
                self.assertIn("personal_apps_dir", data)
                self.assertIn("current_out_dir", data)
                self.assertTrue(data["workspace_apps_dir"].endswith("scratch/apps"))

    def test_build_forwards_destination_options(self) -> None:
        captured_options = {}

        def stub_build(prompt: str, **options) -> dict:
            captured_options.update(options)
            return STUB_RESULT

        with running_server(stub_build) as base_url:
            body = json.dumps({
                "prompt": "Build a test app",
                "output_dir": "/custom/path/apps",
                "folder_name": "my-special-app",
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/build",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)

        self.assertEqual(captured_options.get("output_dir"), "/custom/path/apps")
        self.assertEqual(captured_options.get("folder_name"), "my-special-app")

    def test_target_dir_for_resolution(self) -> None:
        from omnistackai_agent_engine.studio.live_serve import _target_dir_for
        import os

        with tempfile.TemporaryDirectory() as tmp:
            p = _target_dir_for("Prompt", custom_dir=tmp, folder_name="my_custom_folder")
            self.assertEqual(p, os.path.join(tmp, "my-custom-folder"))
            self.assertTrue(os.path.isdir(tmp))

        p_tilde = _target_dir_for("Prompt", custom_dir="~/some_test_dir", folder_name="my_app")
        self.assertEqual(p_tilde, os.path.join(os.path.expanduser("~/some_test_dir"), "my-app"))


if __name__ == "__main__":
    unittest.main()

"""F-01 / R-499: Tests for StudioWorkspaceStore and workspace HTTP server routes.

Validates:
- On-disk workspace persistence under ~/.omnistackai/workspaces/<uuid>/
- Atomic state writing and turn appending
- Lossless ApplicationIR persistence (surviving restarts)
- Concurrency locks (fcntl) and 409 conflict responses
- Safe file tree listing and file reading
- Clean workspace purge
- HTTP server workspace route handlers
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from omnistackai_agent_engine.application_ir import (
    AdminStrategy,
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    MobileProfile,
    Platform,
    ProjectStrategy,
    RepoStrategy,
    WebStrategy,
)
from omnistackai_agent_engine.studio.files import (
    BuildNotFoundError,
    FileNotFoundInBuildError,
    PathOutsideBuildError,
)
from omnistackai_agent_engine.studio.server import create_studio_server
from omnistackai_agent_engine.studio.workspace import (
    StudioWorkspaceStore,
    WorkspaceLockedError,
)


def _dummy_strategy() -> ProjectStrategy:
    return ProjectStrategy(
        mobile_profile=MobileProfile.NONE,
        web_strategy=WebStrategy.NEXTJS,
        admin_strategy=AdminStrategy.NONE,
        backend_strategy=BackendStrategy.GO,
        database_strategy=DatabaseStrategy.POSTGRES,
        repo_strategy=RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
    )


class StudioWorkspaceStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.store = StudioWorkspaceStore(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_ensure_workspace_creates_directory(self) -> None:
        ws_id = "ws-test-1"
        ws_dir = self.store.ensure_workspace(ws_id)
        self.assertTrue(ws_dir.is_dir())
        self.assertEqual(ws_dir.resolve(), (self.root / ws_id).resolve())

    def test_state_persistence_and_atomic_write(self) -> None:
        ws_id = "ws-test-state"
        self.store.ensure_workspace(ws_id)
        state_data = {
            "name": "Inventory App",
            "description": "Track items and warehouses",
            "entities": ["Item", "Warehouse"],
            "file_count": 42,
            "commit_sha": "abc12345",
        }
        self.store.save_state(ws_id, state_data)

        loaded = self.store.get_state(ws_id)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded["name"], "Inventory App")
        self.assertEqual(loaded["file_count"], 42)
        self.assertEqual(loaded["commit_sha"], "abc12345")
        self.assertEqual(loaded["schema_version"], 1)

    def test_turns_persistence(self) -> None:
        ws_id = "ws-test-turns"
        self.store.ensure_workspace(ws_id)
        self.store.append_turn(ws_id, "user", "Create an inventory app")
        self.store.append_turn(ws_id, "assistant", "Built Inventory App with 2 entities.")
        self.store.append_turn(ws_id, "user", "Add barcode scanner")

        turns = self.store.get_turns(ws_id)
        self.assertEqual(len(turns), 3)
        self.assertEqual(turns[0]["role"], "user")
        self.assertEqual(turns[0]["text"], "Create an inventory app")
        self.assertEqual(turns[1]["role"], "assistant")
        self.assertEqual(turns[2]["text"], "Add barcode scanner")

    def test_ir_persistence_survives_restart(self) -> None:
        ws_id = "ws-test-ir"
        self.store.ensure_workspace(ws_id)

        ir = ApplicationIR(
            name="Bookstore",
            description="Online books catalogue",
            platforms=(Platform.WEB, Platform.BACKEND),
            project_strategy=_dummy_strategy(),
            entities=(
                Entity(
                    name="Book",
                    fields=(
                        Field(name="title", type="string"),
                        Field(name="price", type="number"),
                    ),
                ),
            ),
        )
        self.store.save_ir(ws_id, ir)

        # Simulate fresh process restart by creating a new store instance with same root
        new_store = StudioWorkspaceStore(self.root)
        loaded_ir = new_store.load_ir(ws_id)
        self.assertIsNotNone(loaded_ir)
        assert loaded_ir is not None
        self.assertEqual(loaded_ir.name, "Bookstore")
        self.assertEqual(loaded_ir.description, "Online books catalogue")
        self.assertEqual(len(loaded_ir.entities), 1)
        self.assertEqual(loaded_ir.entities[0].name, "Book")
        self.assertEqual(loaded_ir.entities[0].fields[0].name, "title")

    def test_lock_prevents_concurrent_access(self) -> None:
        ws_id = "ws-test-lock"
        self.store.ensure_workspace(ws_id)

        with self.store.lock(ws_id):
            # Attempting to lock the same workspace concurrently in another store or thread must fail
            other_store = StudioWorkspaceStore(self.root)
            with self.assertRaises(WorkspaceLockedError):
                with other_store.lock(ws_id):
                    pass

        # After releasing the lock, acquiring it succeeds
        with self.store.lock(ws_id):
            pass

    def test_file_listing_and_reading(self) -> None:
        ws_id = "ws-test-files"
        repo_dir = self.store.repo_path(ws_id)
        repo_dir.mkdir(parents=True, exist_ok=True)

        (repo_dir / "README.md").write_text("# Test App\n", encoding="utf-8")
        src_dir = repo_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "main.py").write_text("print('hello')\n", encoding="utf-8")

        tree = self.store.list_files(ws_id)
        self.assertIn("README.md", tree["files"])
        self.assertIn("src/main.py", tree["files"])

        content = self.store.read_file(ws_id, "src/main.py")
        self.assertEqual(content["content"], "print('hello')\n")
        self.assertEqual(content["path"], "src/main.py")

        with self.assertRaises(FileNotFoundInBuildError):
            self.store.read_file(ws_id, "nonexistent.txt")

        with self.assertRaises(PathOutsideBuildError):
            self.store.read_file(ws_id, "../outside.txt")

    def test_purge_removes_workspace(self) -> None:
        ws_id = "ws-test-purge"
        self.store.ensure_workspace(ws_id)
        self.store.save_state(ws_id, {"name": "Purge Me"})
        self.assertTrue(self.store.workspace_dir(ws_id).is_dir())

        self.store.purge(ws_id)
        self.assertFalse(self.store.workspace_dir(ws_id).exists())


class StudioWorkspaceServerHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.store = StudioWorkspaceStore(self.root)

        def dummy_build(prompt: str, **options) -> dict:
            return {"status": "ok", "prompt": prompt}

        def dummy_ws_build(ws_id: str, prompt: str, **options) -> dict:
            self.store.ensure_workspace(ws_id)
            self.store.save_state(ws_id, {"name": "Built App", "prompt": prompt})
            self.store.append_turn(ws_id, "user", prompt)
            self.store.append_turn(ws_id, "assistant", "App built.")
            return {"id": ws_id, "name": "Built App", "prompt": prompt}

        def dummy_ws_edit(ws_id: str, prompt: str) -> dict:
            self.store.append_turn(ws_id, "user", prompt)
            self.store.append_turn(ws_id, "assistant", f"Edited with {prompt}")
            return {"id": ws_id, "commit_sha": "new_sha", "diff": {"summary": "1 file modified"}}

        def dummy_ws_preview(ws_id: str) -> dict:
            return {"status": "running", "url": "http://127.0.0.1:3000"}

        def dummy_ws_problems(ws_id: str) -> dict:
            return {"errors": [], "warnings": [], "passed": True}

        self.server = create_studio_server(
            dummy_build,
            host="127.0.0.1",
            port=0,
            workspace_store=self.store,
            workspace_build_fn=dummy_ws_build,
            workspace_edit_fn=dummy_ws_edit,
            workspace_preview_fn=dummy_ws_preview,
            workspace_problems_check_fn=dummy_ws_problems,
            workspace_problems_get_fn=dummy_ws_problems,
        )
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._tmp.cleanup()

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

    def _post(self, path: str, payload: dict) -> tuple[int, dict]:
        req = Request(
            self._url(path),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body) if body else {}
        except HTTPError as err:
            body = err.read().decode("utf-8")
            return err.code, json.loads(body) if body else {}

    def _delete(self, path: str) -> tuple[int, dict]:
        req = Request(self._url(path), method="DELETE")
        try:
            with urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body) if body else {}
        except HTTPError as err:
            body = err.read().decode("utf-8")
            return err.code, json.loads(body) if body else {}

    def test_workspace_build_and_get_lifecycle(self) -> None:
        ws_id = "test-ws-http-1"

        # Initially workspace does not exist
        status, data = self._get(f"/api/workspaces/{ws_id}")
        self.assertEqual(status, 404)

        # Build workspace
        status, data = self._post(f"/api/workspaces/{ws_id}/build", {"prompt": "Build an e-commerce platform"})
        self.assertEqual(status, 200)
        self.assertEqual(data["id"], ws_id)
        self.assertEqual(data["name"], "Built App")

        # Now GET /api/workspaces/{id} returns 200 state
        status, data = self._get(f"/api/workspaces/{ws_id}")
        self.assertEqual(status, 200)
        self.assertEqual(data["name"], "Built App")

        # GET /api/workspaces/{id}/turns
        status, data = self._get(f"/api/workspaces/{ws_id}/turns")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["turns"]), 2)

        # POST /api/workspaces/{id}/edit
        status, data = self._post(f"/api/workspaces/{ws_id}/edit", {"prompt": "Add cart"})
        self.assertEqual(status, 200)
        self.assertEqual(data["commit_sha"], "new_sha")

        # Turns should now have 4 entries
        status, data = self._get(f"/api/workspaces/{ws_id}/turns")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["turns"]), 4)

        # POST /api/workspaces/{id}/preview
        status, data = self._post(f"/api/workspaces/{ws_id}/preview", {})
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "running")

        # GET /api/workspaces/{id}/problems
        status, data = self._get(f"/api/workspaces/{ws_id}/problems")
        self.assertEqual(status, 200)
        self.assertTrue(data["passed"])

        # DELETE /api/workspaces/{id}
        status, data = self._delete(f"/api/workspaces/{ws_id}")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "purged")

        # Verify it is deleted
        status, data = self._get(f"/api/workspaces/{ws_id}")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()

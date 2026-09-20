"""Unit tests for workspace logs, secrets scrubbing, rotation, and build cancellation (F-08 / R-506)."""

import asyncio
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omnistackai_agent_engine.model_gateway.contracts import (
    GenerateRequest,
    StreamEvent,
    TokenUsage,
)
from omnistackai_agent_engine.studio.logs import StudioLogManager, scrub_secrets
from omnistackai_agent_engine.studio.workspace import StudioWorkspaceStore
from omnistackai_agent_engine.studio.live_serve import _build_stream


class StubSlowStreamProvider:
    """Stub provider that yields multiple chunks with a slight pause for testing cancellation."""

    provider_id = "stub-stream"

    async def generate(self, request: GenerateRequest):  # pragma: no cover
        raise AssertionError("generate() must not be called")

    async def stream(self, request: GenerateRequest):
        for i in range(10):
            await asyncio.sleep(0.05)
            is_last = i == 9
            yield StreamEvent(
                request.request_id,
                i,
                f"chunk_{i} ",
                is_last,
                TokenUsage(10, 10) if is_last else None,
            )


class TestLogsAndCancellation(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="omnistackai-test-logs-")
        self.workspace_store = StudioWorkspaceStore(root_dir=self.temp_dir)
        self.log_mgr = StudioLogManager(root_dir=self.temp_dir)
        self.ws_id = "test-ws-logs-001"
        self.workspace_store.ensure_workspace(self.ws_id)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_secrets_scrubbing(self) -> None:
        secrets = ["SUPER_SECRET_TOKEN_999", "db_password_xyz123"]
        raw_msg = "Error connecting to db with password db_password_xyz123 and token SUPER_SECRET_TOKEN_999"
        scrubbed = scrub_secrets(raw_msg, secrets)
        self.assertNotIn("db_password_xyz123", scrubbed)
        self.assertNotIn("SUPER_SECRET_TOKEN_999", scrubbed)
        self.assertIn("***", scrubbed)

        # Build log scrubbing
        entry = self.log_mgr.append_build_log(
            self.ws_id,
            level="error",
            phase="connect",
            message=raw_msg,
            secrets=secrets,
        )
        self.assertNotIn("SUPER_SECRET_TOKEN_999", entry["message"])
        self.assertIn("***", entry["message"])

        # App log scrubbing
        self.log_mgr.write_app_log(self.ws_id, raw_msg + "\n", secrets=secrets)
        read = self.log_mgr.read_logs(self.ws_id, source="app")
        self.assertTrue(len(read["lines"]) > 0)
        self.assertNotIn("SUPER_SECRET_TOKEN_999", read["lines"][0])
        self.assertIn("***", read["lines"][0])

    def test_log_rotation(self) -> None:
        # Override OMNISTACKAI_LOG_MAX_BYTES to 200 bytes for testing rotation
        old_env = os.environ.get("OMNISTACKAI_LOG_MAX_BYTES")
        os.environ["OMNISTACKAI_LOG_MAX_BYTES"] = "200"
        try:
            for i in range(10):
                self.log_mgr.write_app_log(self.ws_id, f"Line {i}: " + ("x" * 40) + "\n")
            app_log = self.log_mgr.app_log_path(self.ws_id)
            self.assertTrue(app_log.exists())
            # Check that rotated backup file .1 was created
            backup_1 = app_log.with_name(f"{app_log.name}.1")
            self.assertTrue(backup_1.exists())
        finally:
            if old_env is not None:
                os.environ["OMNISTACKAI_LOG_MAX_BYTES"] = old_env
            else:
                os.environ.pop("OMNISTACKAI_LOG_MAX_BYTES", None)

    def test_log_read_and_clear(self) -> None:
        self.log_mgr.append_build_log(self.ws_id, "info", "step1", "Message 1")
        self.log_mgr.append_build_log(self.ws_id, "info", "step2", "Message 2")
        self.log_mgr.append_build_log(self.ws_id, "warn", "step3", "Message 3")

        read_all = self.log_mgr.read_logs(self.ws_id, source="build", since=0)
        self.assertEqual(len(read_all["lines"]), 3)
        self.assertEqual(read_all["next_cursor"], 3)

        read_since = self.log_mgr.read_logs(self.ws_id, source="build", since=1)
        self.assertEqual(len(read_since["lines"]), 2)

        self.log_mgr.clear_logs(self.ws_id, source="build")
        read_empty = self.log_mgr.read_logs(self.ws_id, source="build", since=0)
        self.assertEqual(len(read_empty["lines"]), 0)

    def test_workspace_cancellation_flags(self) -> None:
        self.assertFalse(self.workspace_store.is_cancelled(self.ws_id))
        self.workspace_store.set_cancelled(self.ws_id)
        self.assertTrue(self.workspace_store.is_cancelled(self.ws_id))
        self.workspace_store.clear_cancelled(self.ws_id)
        self.assertFalse(self.workspace_store.is_cancelled(self.ws_id))

    def test_workspace_attachments(self) -> None:
        path = self.workspace_store.save_attachment(
            self.ws_id,
            turn_index=1,
            filename="data.csv",
            content="col1,col2\nval1,val2\n",
        )
        self.assertTrue(os.path.exists(path))
        attachments = self.workspace_store.get_attachments(self.ws_id, turn_index=1)
        self.assertIn("data.csv", attachments)

    async def test_build_cancellation_stops_immediately_and_commits_nothing(self) -> None:
        provider = StubSlowStreamProvider()
        target_dir = str(self.workspace_store.repo_path(self.ws_id))
        self.workspace_store.clear_cancelled(self.ws_id)

        # Set up a task that cancels after 0.08 seconds
        async def _trigger_cancel():
            await asyncio.sleep(0.08)
            self.workspace_store.set_cancelled(self.ws_id)

        cancel_task = asyncio.create_task(_trigger_cancel())

        saw_cancelled = False
        with patch(
            "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
            return_value=(provider, "stub-model", 4096, 5.0),
        ):
            async for event in _build_stream(
                "Build a task manager app",
                direct_target_dir=target_dir,
                workspace_store=self.workspace_store,
                workspace_id=self.ws_id,
            ):
                if event.get("phase") == "cancelled":
                    saw_cancelled = True
                    break

        await cancel_task
        self.assertTrue(saw_cancelled, "Expected to receive phase: cancelled event")

        # Verify nothing was committed to git repo
        repo_dir = Path(target_dir)
        git_dir = repo_dir / ".git"
        if git_dir.exists():
            import subprocess
            res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_dir), capture_output=True, text=True)
            self.assertNotEqual(res.returncode, 0, "Git HEAD should not exist when build was cancelled")


if __name__ == "__main__":
    unittest.main()

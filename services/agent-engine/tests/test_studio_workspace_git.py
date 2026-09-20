"""Tests for studio workspace export (.zip) and git push integration (R-501 / F-03)."""

from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from omnistackai_agent_engine.studio.workspace import (
    GitOperationError,
    StudioWorkspaceStore,
)


class TestStudioWorkspaceGit(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="omnistackai-test-workspace-git-")
        self.store = StudioWorkspaceStore(self.temp_dir)
        self.workspace_id = "test-ws-git-1"
        self.repo_dir = self.store.ensure_workspace(self.workspace_id) / "repo"

        # Initialize git repo in workspace repo dir
        subprocess.run(["git", "init", "-q"], cwd=str(self.repo_dir), check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=str(self.repo_dir),
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=str(self.repo_dir),
            check=True,
        )

        # Create files
        (self.repo_dir / "package.json").write_text('{"name": "test-app"}', encoding="utf-8")
        (self.repo_dir / ".env.example").write_text("API_URL=http://localhost", encoding="utf-8")
        (self.repo_dir / ".env").write_text("API_SECRET=supersecret", encoding="utf-8")
        (self.repo_dir / ".env.local").write_text("LOCAL_KEY=secret123", encoding="utf-8")

        nm_dir = self.repo_dir / "node_modules" / "dummy"
        nm_dir.mkdir(parents=True, exist_ok=True)
        (nm_dir / "index.js").write_text("// module code", encoding="utf-8")

        # Commit initial files
        subprocess.run(["git", "add", "."], cwd=str(self.repo_dir), check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Initial commit"],
            cwd=str(self.repo_dir),
            check=True,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_zip_excludes_git_and_secrets(self) -> None:
        buf = io.BytesIO()
        count = self.store.export_zip(self.workspace_id, buf)
        self.assertGreater(count, 0)

        buf.seek(0)
        with zipfile.ZipFile(buf, "r") as zf:
            names = set(zf.namelist())

            # Required project files must be present
            self.assertIn("package.json", names)
            self.assertIn(".env.example", names)

            # Secret and cache files must NEVER be in the zip archive
            self.assertNotIn(".env", names)
            self.assertNotIn(".env.local", names)
            for name in names:
                self.assertFalse(name.startswith(".git/"))
                self.assertFalse(name.startswith("node_modules/"))

    def test_git_status_reports_commit_and_clean_state(self) -> None:
        status = self.store.git_status(self.workspace_id)
        self.assertTrue(status["commit_sha"])
        self.assertEqual(len(status["commit_sha"]), 40)
        self.assertFalse(status["dirty"])

        # Make a change
        (self.repo_dir / "README.md").write_text("# New", encoding="utf-8")
        status_dirty = self.store.git_status(self.workspace_id)
        self.assertTrue(status_dirty["dirty"])

    def test_git_push_scrubs_token_on_failure(self) -> None:
        secret_token = "ghs_TEST_TOKEN_XYZ_9999"
        failing_url = f"https://x-access-token:{secret_token}@127.0.0.1:9/nonexistent/repo.git"

        with self.assertRaises(GitOperationError) as ctx:
            self.store.git_push(self.workspace_id, failing_url, branch="main")

        error_message = str(ctx.exception)
        # Verify secret token is NEVER leaked in exception message
        self.assertNotIn(secret_token, error_message)
        self.assertNotIn("x-access-token", error_message)

    def test_git_push_redacts_credentials_in_simulated_stderr(self) -> None:
        from unittest.mock import patch, MagicMock
        secret_token = "ghs_TEST_TOKEN_MOCK_12345"
        failing_url = f"https://x-access-token:{secret_token}@github.com/org/repo.git"

        mock_res = MagicMock()
        mock_res.returncode = 128
        mock_res.stderr = f"fatal: unable to access '{failing_url}': Could not resolve host"
        mock_res.stdout = ""

        with patch("subprocess.run") as mock_run:
            # First call is git rev-parse HEAD (success)
            rev_mock = MagicMock(returncode=0, stdout="a"*40)
            mock_run.side_effect = [rev_mock, mock_res]

            with self.assertRaises(GitOperationError) as ctx:
                self.store.git_push(self.workspace_id, failing_url, branch="main")

            err = str(ctx.exception)
            self.assertNotIn(secret_token, err)
            self.assertIn("[REDACTED]", err)


if __name__ == "__main__":
    unittest.main()

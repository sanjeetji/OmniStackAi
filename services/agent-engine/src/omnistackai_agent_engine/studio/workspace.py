"""On-disk workspace store for the OmniStackAI Studio (F-01 / R-499).

Replaces ephemeral in-memory build history with persistent workspaces on disk:
<root>/<workspace_id>/
  repo/        - git repository with generated project files
  state.json   - atomic metadata {schema, project_id, name, description, entities, ...}
  turns.jsonl  - append-only chat turn history
  ir.json      - serialized ApplicationIR for surviving restarts and follow-up edits
  .lock        - concurrency lock for workspace edits
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from ..application_ir import ApplicationIR
from .files import (
    BuildNotFoundError,
    FileNotFoundInBuildError,
    PathOutsideBuildError,
    _is_excluded_dir,
    _is_secret_env_file,
    list_build_files,
    read_build_file,
)

_WORKSPACE_SCHEMA_VERSION = 1
_DEFAULT_ROOT = "~/.omnistackai/workspaces"
_MAX_TURN_CHARS = 2_000
_VALID_ROLES = frozenset({"user", "assistant"})


class WorkspaceLockedError(Exception):
    """Raised when another process or request holds the lock on this workspace."""


class WorkspaceNotFoundError(Exception):
    """Raised when the requested workspace does not exist on disk."""


class GitOperationError(Exception):
    """Raised when a workspace git operation (status, push, commit) fails."""


class StudioWorkspaceStore:
    def __init__(self, root_dir: str | os.PathLike[str] | None = None) -> None:
        raw_root = root_dir or os.environ.get("OMNISTACKAI_STUDIO_WORKSPACE_ROOT") or _DEFAULT_ROOT
        self._root = Path(os.path.expanduser(str(raw_root))).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def workspace_path(self, workspace_id: str) -> Path:
        clean_id = Path(workspace_id).name
        if not clean_id or clean_id in {".", ".."}:
            raise ValueError(f"invalid workspace_id: {workspace_id!r}")
        return self._root / clean_id

    def exists(self, workspace_id: str) -> bool:
        return self.workspace_path(workspace_id).is_dir()

    def ensure_workspace(self, workspace_id: str) -> Path:
        p = self.workspace_path(workspace_id)
        p.mkdir(parents=True, exist_ok=True)
        (p / "repo").mkdir(parents=True, exist_ok=True)
        return p

    def workspace_dir(self, workspace_id: str) -> Path:
        return self.workspace_path(workspace_id)

    def repo_path(self, workspace_id: str) -> Path:
        return self.workspace_path(workspace_id) / "repo"

    def get_repo_dir(self, workspace_id: str) -> str:
        self.ensure_workspace(workspace_id)
        return str(self.repo_path(workspace_id))

    @contextmanager
    def lock(self, workspace_id: str, timeout: float = 0.0) -> Generator[None, None, None]:
        wpath = self.ensure_workspace(workspace_id)
        lock_file = wpath / ".lock"
        fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
        try:
            flags = fcntl.LOCK_EX
            if timeout <= 0:
                flags |= fcntl.LOCK_NB
            try:
                fcntl.flock(fd, flags)
            except (BlockingIOError, OSError) as e:
                raise WorkspaceLockedError(f"workspace {workspace_id} is currently locked by another operation") from e
            yield
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
            os.close(fd)

    def save_state(self, workspace_id: str, state: dict) -> None:
        wpath = self.ensure_workspace(workspace_id)
        data = dict(state)
        data["schema"] = _WORKSPACE_SCHEMA_VERSION
        data["schema_version"] = _WORKSPACE_SCHEMA_VERSION
        data["workspace_id"] = workspace_id
        data["updated_at"] = time.time()
        if "created_at" not in data:
            data["created_at"] = time.time()

        content = json.dumps(data, indent=2)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(wpath), prefix="state-", suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, str(wpath / "state.json"))
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def get_state(self, workspace_id: str) -> dict | None:
        state_file = self.workspace_path(workspace_id) / "state.json"
        if not state_file.is_file():
            return None
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save_ir(self, workspace_id: str, ir: ApplicationIR) -> None:
        wpath = self.ensure_workspace(workspace_id)
        content = json.dumps(ir.to_dict(), indent=2)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(wpath), prefix="ir-", suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, str(wpath / "ir.json"))
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def load_ir(self, workspace_id: str) -> ApplicationIR | None:
        ir_file = self.workspace_path(workspace_id) / "ir.json"
        if not ir_file.is_file():
            return None
        try:
            with open(ir_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return ApplicationIR.from_dict(raw)
        except Exception:
            return None

    def append_turn(self, workspace_id: str, role: str, text: str) -> None:
        if role not in _VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(_VALID_ROLES)}: {role!r}")
        wpath = self.ensure_workspace(workspace_id)
        entry = {
            "role": role,
            "text": str(text)[:_MAX_TURN_CHARS],
            "created_at": time.time(),
        }
        line = json.dumps(entry) + "\n"
        with open(wpath / "turns.jsonl", "a", encoding="utf-8") as f:
            f.write(line)

    def get_turns(self, workspace_id: str) -> list[dict]:
        turns_file = self.workspace_path(workspace_id) / "turns.jsonl"
        if not turns_file.is_file():
            return []
        turns = []
        try:
            with open(turns_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        turns.append(json.loads(line))
        except Exception:
            pass
        return turns

    def list_files(self, workspace_id: str) -> dict:
        repo_path = self.workspace_path(workspace_id) / "repo"
        if not repo_path.is_dir():
            raise BuildNotFoundError(f"workspace repo directory does not exist: {repo_path}")
        return list_build_files(repo_path)

    def read_file(self, workspace_id: str, rel_path: str) -> dict:
        repo_path = self.workspace_path(workspace_id) / "repo"
        if not repo_path.is_dir():
            raise BuildNotFoundError(f"workspace repo directory does not exist: {repo_path}")
        return read_build_file(repo_path, rel_path)

    def purge(self, workspace_id: str) -> bool:
        wpath = self.workspace_path(workspace_id)
        if not wpath.exists():
            return False
        shutil.rmtree(wpath)
        return True

    def export_zip(self, workspace_id: str, out_file: any) -> int:
        repo_dir = self.workspace_path(workspace_id) / "repo"
        if not repo_dir.is_dir():
            raise BuildNotFoundError(f"workspace repo directory does not exist: {repo_dir}")

        count = 0
        with zipfile.ZipFile(out_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for dirpath, dirnames, filenames in os.walk(repo_dir):
                dirnames[:] = [d for d in dirnames if not _is_excluded_dir(d)]
                for fname in sorted(filenames):
                    if _is_secret_env_file(fname):
                        continue
                    full_path = Path(dirpath) / fname
                    rel_path = full_path.relative_to(repo_dir)
                    zf.write(full_path, arcname=str(rel_path))
                    count += 1
        return count

    def git_status(self, workspace_id: str) -> dict:
        repo_dir = self.workspace_path(workspace_id) / "repo"
        if not repo_dir.is_dir():
            raise BuildNotFoundError(f"workspace repo directory does not exist: {repo_dir}")

        commit_sha = ""
        branch = "main"
        dirty = False
        ahead_by = 0

        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                commit_sha = res.stdout.strip()
        except Exception:
            pass

        try:
            res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                branch = res.stdout.strip()
        except Exception:
            pass

        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                dirty = True
        except Exception:
            pass

        return {
            "commit_sha": commit_sha,
            "branch": branch,
            "dirty": dirty,
            "ahead_by": ahead_by,
        }

    def git_push(self, workspace_id: str, remote_url: str, branch: str = "main") -> dict:
        repo_dir = self.workspace_path(workspace_id) / "repo"
        if not repo_dir.is_dir():
            raise BuildNotFoundError(f"workspace repo directory does not exist: {repo_dir}")

        if not remote_url:
            raise GitOperationError("remote_url is required")

        rev = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if rev.returncode != 0:
            raise GitOperationError("no commits to push in workspace")
        commit_sha = rev.stdout.strip()

        # Push to remote without saving credentials in .git/config
        # We push to the explicit URL refspec: git push <remote_url> HEAD:<branch>
        push_cmd = ["git", "push", remote_url, f"HEAD:{branch}"]
        env = dict(os.environ)
        env["GIT_TERMINAL_PROMPT"] = "0"

        res = subprocess.run(
            push_cmd,
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

        if res.returncode != 0:
            # CRITICAL: scrub remote_url and any embedded tokens from stderr/stdout
            err_msg = res.stderr or res.stdout or f"git push exited with code {res.returncode}"
            if "@" in remote_url and "://" in remote_url:
                proto, rest = remote_url.split("://", 1)
                userpass, hostpath = rest.split("@", 1)
                err_msg = err_msg.replace(userpass, "[REDACTED]")
                err_msg = err_msg.replace(remote_url, f"{proto}://[REDACTED]@{hostpath}")
            raise GitOperationError(f"git push failed: {err_msg.strip()}")

        return {
            "commit_sha": commit_sha,
            "branch": branch,
        }


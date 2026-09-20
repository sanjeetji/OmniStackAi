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
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from ..application_ir import ApplicationIR
from .files import BuildNotFoundError, FileNotFoundInBuildError, PathOutsideBuildError, list_build_files, read_build_file

_WORKSPACE_SCHEMA_VERSION = 1
_DEFAULT_ROOT = "~/.omnistackai/workspaces"
_MAX_TURN_CHARS = 2_000
_VALID_ROLES = frozenset({"user", "assistant"})


class WorkspaceLockedError(Exception):
    """Raised when another process or request holds the lock on this workspace."""


class WorkspaceNotFoundError(Exception):
    """Raised when the requested workspace does not exist on disk."""


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

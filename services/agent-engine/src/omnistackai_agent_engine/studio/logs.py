"""Workspace and application logging with secrets scrubbing and rotation (F-08 / R-506).

Handles:
- <workspace>/logs/build.jsonl: structured event stream for builds/edits ({ts, level, phase, message}).
- <workspace>/logs/app.log: captured stdout/stderr from local preview runner processes with size cap
  and file rotation (OMNISTACKAI_LOG_MAX_BYTES, default 5 MB, 3 rotated files).
- Secrets scrubbing: any value matching a known project secret is replaced with '***' before write.
- Cursor-based log reading and SSE streaming for real-time console display.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import AsyncIterator, Iterable, List

_DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_DEFAULT_BACKUP_COUNT = 3


def get_log_max_bytes() -> int:
    try:
        val = os.environ.get("OMNISTACKAI_LOG_MAX_BYTES")
        if val:
            return int(val)
    except Exception:
        pass
    return _DEFAULT_MAX_BYTES


def scrub_secrets(text: str, secrets: Iterable[str] | None) -> str:
    """Replace occurrences of secret values with '***'. Never leaks secrets in logs."""
    if not text or not secrets:
        return text
    scrubbed = text
    for secret in secrets:
        # Ignore empty or very short strings to avoid false-positive masking
        if secret and len(secret) >= 3 and secret in scrubbed:
            scrubbed = scrubbed.replace(secret, "***")
    return scrubbed


class StudioLogManager:
    """Manages build and app logs for workspaces."""

    def __init__(self, root_dir: str | os.PathLike[str] | None = None) -> None:
        raw_root = root_dir or os.environ.get("OMNISTACKAI_STUDIO_WORKSPACE_ROOT") or "~/.omnistackai/workspaces"
        self._root = Path(os.path.expanduser(str(raw_root))).resolve()

    def logs_dir(self, workspace_id: str) -> Path:
        p = self._root / Path(workspace_id).name / "logs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def build_log_path(self, workspace_id: str) -> Path:
        return self.logs_dir(workspace_id) / "build.jsonl"

    def app_log_path(self, workspace_id: str) -> Path:
        return self.logs_dir(workspace_id) / "app.log"

    def append_build_log(
        self,
        workspace_id: str,
        level: str,
        phase: str,
        message: str,
        secrets: Iterable[str] | None = None,
    ) -> dict:
        """Append one structured entry to <workspace>/logs/build.jsonl."""
        scrubbed_msg = scrub_secrets(message, secrets)
        entry = {
            "ts": time.time(),
            "level": level,
            "phase": phase,
            "message": scrubbed_msg,
        }
        line = json.dumps(entry) + "\n"
        log_file = self.build_log_path(workspace_id)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)
        return entry

    def write_app_log(
        self,
        workspace_id: str,
        text: str,
        secrets: Iterable[str] | None = None,
    ) -> None:
        """Write raw process stdout/stderr to <workspace>/logs/app.log with rotation."""
        scrubbed = scrub_secrets(text, secrets)
        if not scrubbed:
            return
        log_file = self.app_log_path(workspace_id)
        max_bytes = get_log_max_bytes()

        # Check rotation
        if log_file.exists():
            try:
                current_size = log_file.stat().st_size
                if current_size + len(scrubbed.encode("utf-8")) > max_bytes:
                    self._rotate_file(log_file, _DEFAULT_BACKUP_COUNT)
            except OSError:
                pass

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(scrubbed)

    def _rotate_file(self, target: Path, backup_count: int) -> None:
        """Rotate target -> target.1 -> target.2 ... up to backup_count."""
        for i in range(backup_count - 1, 0, -1):
            src = target.with_name(f"{target.name}.{i}")
            dst = target.with_name(f"{target.name}.{i + 1}")
            if src.exists():
                try:
                    if dst.exists():
                        dst.unlink()
                    src.rename(dst)
                except OSError:
                    pass
        first_backup = target.with_name(f"{target.name}.1")
        try:
            if first_backup.exists():
                first_backup.unlink()
            target.rename(first_backup)
        except OSError:
            pass

    def read_logs(
        self,
        workspace_id: str,
        source: str = "build",
        since: int | None = None,
        limit: int = 500,
    ) -> dict:
        """Read lines from logs after cursor ``since`` (0-based line index)."""
        if source == "app":
            log_file = self.app_log_path(workspace_id)
        else:
            log_file = self.build_log_path(workspace_id)

        if not log_file.exists():
            return {"source": source, "lines": [], "next_cursor": 0, "total": 0}

        lines: List[dict | str] = []
        start_idx = since if since is not None and since >= 0 else 0
        current_idx = 0

        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if current_idx >= start_idx:
                        if source == "build":
                            try:
                                lines.append(json.loads(line))
                            except Exception:
                                lines.append({"ts": 0, "level": "info", "phase": "raw", "message": line.rstrip("\n")})
                        else:
                            lines.append(line.rstrip("\n"))
                        if len(lines) >= limit:
                            current_idx += 1
                            break
                    current_idx += 1
        except OSError:
            pass

        next_cursor = current_idx
        return {
            "source": source,
            "lines": lines,
            "next_cursor": next_cursor,
            "total": current_idx,
        }

    async def stream_logs(
        self,
        workspace_id: str,
        source: str = "build",
        since: int | None = None,
    ) -> AsyncIterator[dict]:
        """Async generator yielding log events as they appear."""
        cursor = since if since is not None and since >= 0 else 0
        initial = self.read_logs(workspace_id, source=source, since=cursor, limit=1000)
        for item in initial["lines"]:
            yield {"source": source, "entry": item, "cursor": cursor}
            cursor += 1

        if source == "app":
            log_file = self.app_log_path(workspace_id)
        else:
            log_file = self.build_log_path(workspace_id)

        # Poll loop for new lines
        while True:
            await asyncio.sleep(0.5)
            if not log_file.exists():
                continue
            update = self.read_logs(workspace_id, source=source, since=cursor, limit=200)
            if update["lines"]:
                for item in update["lines"]:
                    yield {"source": source, "entry": item, "cursor": cursor}
                    cursor += 1

    def clear_logs(self, workspace_id: str, source: str | None = None) -> dict:
        """Clear build and/or app logs for a workspace."""
        cleared = []
        if source in ("build", None):
            bf = self.build_log_path(workspace_id)
            if bf.exists():
                try:
                    bf.unlink()
                    cleared.append("build")
                except OSError:
                    pass
        if source in ("app", None):
            af = self.app_log_path(workspace_id)
            if af.exists():
                try:
                    af.unlink()
                    cleared.append("app")
                except OSError:
                    pass
            # Clear rotated files as well
            for i in range(1, _DEFAULT_BACKUP_COUNT + 1):
                rotated = af.with_name(f"{af.name}.{i}")
                if rotated.exists():
                    try:
                        rotated.unlink()
                    except OSError:
                        pass
        return {"status": "cleared", "sources": cleared}

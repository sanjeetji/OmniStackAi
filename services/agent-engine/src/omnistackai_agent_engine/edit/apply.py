"""Apply a project diff to an existing project on disk, and optionally commit it.

`apply_diff` writes added/modified files and removes deleted ones, strictly inside the caller-provided
target directory (escapes are refused, mirroring the git service). `commit_edit` applies a diff and
records one commit as the customer identity. No network call, no code execution.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ..git_service import RepositoryResult, commit_all
from .diff import ChangeKind, ProjectDiff
from .errors import ApplyError


@dataclass(frozen=True, slots=True)
class ApplyReport:
    target_dir: str
    added: tuple[str, ...]
    modified: tuple[str, ...]
    deleted: tuple[str, ...]

    @property
    def changed_count(self) -> int:
        return len(self.added) + len(self.modified) + len(self.deleted)


def _safe_destination(target: Path, path: str) -> Path:
    destination = (target / path).resolve()
    try:
        destination.relative_to(target)
    except ValueError as error:
        raise ApplyError(f"refusing to touch a path outside the target: {path}") from error
    return destination


def apply_diff(diff: ProjectDiff, target_dir: str | os.PathLike[str]) -> ApplyReport:
    """Write added/modified files and remove deleted ones under ``target_dir`` (path-safe)."""

    if not isinstance(diff, ProjectDiff):
        raise ApplyError("apply_diff expects a ProjectDiff")
    target = Path(target_dir).resolve()
    if not target.is_dir():
        raise ApplyError("target directory does not exist")

    added: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    for change in diff.changes:
        destination = _safe_destination(target, change.path)
        if change.kind is ChangeKind.DELETED:
            if destination.exists():
                destination.unlink()
            _prune_empty_parents(target, destination.parent)
            deleted.append(change.path)
            continue
        # added or modified: new_file is guaranteed present by FileChange validation
        generated = change.new_file
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(generated.content, encoding="utf-8")  # type: ignore[union-attr]
        if generated.executable:  # type: ignore[union-attr]
            destination.chmod(0o755)
        (added if change.kind is ChangeKind.ADDED else modified).append(change.path)

    return ApplyReport(str(target), tuple(added), tuple(modified), tuple(deleted))


def _prune_empty_parents(root: Path, directory: Path) -> None:
    """Remove now-empty directories left by a delete, never ascending past the target root."""

    current = directory
    while current != root and current.is_dir() and not any(current.iterdir()):
        current.rmdir()
        current = current.parent


def commit_edit(
    diff: ProjectDiff,
    target_dir: str | os.PathLike[str],
    *,
    author_name: str,
    author_email: str,
    message: str,
) -> RepositoryResult:
    """Apply ``diff`` to an existing repo and record one commit as the given customer identity."""

    apply_diff(diff, target_dir)
    return commit_all(target_dir, author_name=author_name, author_email=author_email, message=message)

"""Line-level (hunk) diffs and rename detection on top of the R-237 file-level ProjectDiff.

`diff_report` classifies every path as added / modified / deleted / renamed and attaches a git-style
unified (hunk) diff for content changes; `unified_patch` concatenates them into one patch string. Pure
and deterministic (standard-library ``difflib`` only) — additive to the edit package; nothing is run or
written to disk.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from enum import StrEnum

from ..codegen import GeneratedProject
from .errors import EditError


class DiffKind(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass(frozen=True, slots=True)
class FileDiff:
    kind: DiffKind
    path: str            # the new path (for RENAMED, the destination)
    old_path: str | None  # the source path for RENAMED, else None
    patch: str           # git-style unified diff (empty for a pure, content-identical rename)


_ORDER = {DiffKind.ADDED: 0, DiffKind.MODIFIED: 1, DiffKind.RENAMED: 2, DiffKind.DELETED: 3}


def _lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def _unified(from_file: str, to_file: str, old_text: str, new_text: str) -> str:
    return "".join(
        difflib.unified_diff(_lines(old_text), _lines(new_text), fromfile=from_file, tofile=to_file)
    )


def diff_report(old: GeneratedProject, new: GeneratedProject) -> tuple[FileDiff, ...]:
    """Classify changes between two projects with hunk-level patches and rename detection."""

    if not isinstance(old, GeneratedProject) or not isinstance(new, GeneratedProject):
        raise EditError("diff_report expects two GeneratedProject values")

    old_by = {generated.path: generated for generated in old.files()}
    new_by = {generated.path: generated for generated in new.files()}
    added = sorted(set(new_by) - set(old_by))
    deleted = sorted(set(old_by) - set(new_by))
    common = sorted(set(old_by) & set(new_by))

    # Rename detection: a deleted file whose content exactly matches an added file (greedy, sorted).
    renames: list[tuple[str, str]] = []
    claimed: set[str] = set()
    for source in deleted:
        content = old_by[source].content
        match = next((a for a in added if a not in claimed and new_by[a].content == content), None)
        if match is not None:
            renames.append((source, match))
            claimed.add(match)
    renamed_sources = {source for source, _ in renames}
    added = [a for a in added if a not in claimed]
    deleted = [d for d in deleted if d not in renamed_sources]

    reports: list[FileDiff] = []
    for path in added:
        reports.append(FileDiff(DiffKind.ADDED, path, None, _unified("/dev/null", f"b/{path}", "", new_by[path].content)))
    for path in deleted:
        reports.append(FileDiff(DiffKind.DELETED, path, None, _unified(f"a/{path}", "/dev/null", old_by[path].content, "")))
    for path in common:
        before, after = old_by[path], new_by[path]
        if before.content != after.content or before.executable != after.executable:
            reports.append(
                FileDiff(DiffKind.MODIFIED, path, None, _unified(f"a/{path}", f"b/{path}", before.content, after.content))
            )
    for source, destination in renames:
        reports.append(FileDiff(DiffKind.RENAMED, destination, source, ""))

    reports.sort(key=lambda report: (_ORDER[report.kind], report.path))
    return tuple(reports)


def unified_patch(old: GeneratedProject, new: GeneratedProject) -> str:
    """One git-style patch string for the whole diff (rename headers included), byte-stable."""

    parts: list[str] = []
    for report in diff_report(old, new):
        if report.kind is DiffKind.RENAMED:
            parts.append(f"rename from {report.old_path}\nrename to {report.path}\n")
        parts.append(report.patch)
    return "".join(parts)

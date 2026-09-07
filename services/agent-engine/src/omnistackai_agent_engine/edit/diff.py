"""Project diff: the minimal file-level change set between two generated projects.

`diff_projects` is pure — it compares two `GeneratedProject`s by path and classifies each as added,
modified, deleted, or unchanged. `plan_edit` is the "edit an app" entry point: it assembles two
Application IRs and diffs them, so a change to the IR becomes exactly the set of files to rewrite. No
disk, no network, no code execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..application_ir import ApplicationIR
from ..codegen import AdapterRegistry, GeneratedFile, GeneratedProject, assemble_project
from .errors import EditError


class ChangeKind(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class FileChange:
    """One path's change. `new_file` carries the desired content for added/modified, None for deleted."""

    kind: ChangeKind
    path: str
    new_file: GeneratedFile | None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ChangeKind):
            raise EditError("change kind must be a ChangeKind")
        if not isinstance(self.path, str) or not self.path:
            raise EditError("change path must be a non-empty string")
        if self.kind is ChangeKind.DELETED:
            if self.new_file is not None:
                raise EditError("a deleted change must not carry a new_file")
        else:
            if not isinstance(self.new_file, GeneratedFile) or self.new_file.path != self.path:
                raise EditError("an added/modified change must carry a matching GeneratedFile")


@dataclass(frozen=True, slots=True)
class ProjectDiff:
    """The ordered change set plus the paths that are identical in both projects."""

    changes: tuple[FileChange, ...]
    unchanged: tuple[str, ...]

    def _paths(self, kind: ChangeKind) -> tuple[str, ...]:
        return tuple(change.path for change in self.changes if change.kind is kind)

    def added(self) -> tuple[str, ...]:
        return self._paths(ChangeKind.ADDED)

    def modified(self) -> tuple[str, ...]:
        return self._paths(ChangeKind.MODIFIED)

    def deleted(self) -> tuple[str, ...]:
        return self._paths(ChangeKind.DELETED)

    def is_empty(self) -> bool:
        return not self.changes

    def summary(self) -> str:
        return (
            f"{len(self.added())} added, {len(self.modified())} modified, "
            f"{len(self.deleted())} deleted, {len(self.unchanged)} unchanged"
        )


def diff_projects(old: GeneratedProject, new: GeneratedProject) -> ProjectDiff:
    """Classify every path across two projects as added, modified, deleted, or unchanged."""

    if not isinstance(old, GeneratedProject) or not isinstance(new, GeneratedProject):
        raise EditError("diff_projects expects two GeneratedProject values")

    old_by_path = {generated.path: generated for generated in old.files()}
    new_by_path = {generated.path: generated for generated in new.files()}

    changes: list[FileChange] = []
    unchanged: list[str] = []
    for path in sorted(set(old_by_path) | set(new_by_path)):
        before = old_by_path.get(path)
        after = new_by_path.get(path)
        if before is None:
            changes.append(FileChange(ChangeKind.ADDED, path, after))
        elif after is None:
            changes.append(FileChange(ChangeKind.DELETED, path, None))
        elif before.content != after.content or before.executable != after.executable:
            changes.append(FileChange(ChangeKind.MODIFIED, path, after))
        else:
            unchanged.append(path)
    return ProjectDiff(tuple(changes), tuple(unchanged))


def plan_edit(
    old_ir: ApplicationIR, new_ir: ApplicationIR, registry: AdapterRegistry | None = None
) -> ProjectDiff:
    """Assemble both IRs into customer monorepos and return the diff — the delta to apply for an edit."""

    old_project = assemble_project(old_ir, registry)
    new_project = assemble_project(new_ir, registry)
    return diff_projects(old_project, new_project)

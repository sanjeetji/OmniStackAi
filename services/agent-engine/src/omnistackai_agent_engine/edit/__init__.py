"""Edit loop: diff two generated projects and apply only the delta to an existing app."""

from .apply import ApplyReport, apply_diff, commit_edit
from .diff import ChangeKind, FileChange, ProjectDiff, diff_projects, plan_edit
from .errors import ApplyError, EditError
from .patch import DiffKind, FileDiff, diff_report, unified_patch

__all__ = [
    "ApplyError",
    "ApplyReport",
    "ChangeKind",
    "DiffKind",
    "EditError",
    "FileChange",
    "FileDiff",
    "ProjectDiff",
    "apply_diff",
    "commit_edit",
    "diff_projects",
    "diff_report",
    "plan_edit",
    "unified_patch",
]

"""Edit loop: diff two generated projects and apply only the delta to an existing app."""

from .apply import ApplyReport, apply_diff, commit_edit
from .diff import ChangeKind, FileChange, ProjectDiff, diff_projects, plan_edit
from .errors import ApplyError, EditError

__all__ = [
    "ApplyError",
    "ApplyReport",
    "ChangeKind",
    "EditError",
    "FileChange",
    "ProjectDiff",
    "apply_diff",
    "commit_edit",
    "diff_projects",
    "plan_edit",
]

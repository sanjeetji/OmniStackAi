"""Studio: the user-facing "chat -> create an app" web UI.

Brick 3 of the front door. Dependency-free (stdlib ``http.server``); the build function is
injected so the HTTP layer is testable offline.
"""

from .files import (
    BuildNotFoundError,
    FileNotFoundInBuildError,
    PathOutsideBuildError,
    StudioFilesError,
    list_build_files,
    read_build_file,
)
from .history import StudioBuildHistory
from .page import STUDIO_HTML
from .preview import StudioPreviewManager
from .server import BuildFn, create_studio_server
from .session import EditNotSupportedError, SessionEntry, StudioSessionStore

__all__ = [
    "STUDIO_HTML",
    "BuildFn",
    "BuildNotFoundError",
    "EditNotSupportedError",
    "FileNotFoundInBuildError",
    "PathOutsideBuildError",
    "SessionEntry",
    "StudioBuildHistory",
    "StudioFilesError",
    "StudioPreviewManager",
    "StudioSessionStore",
    "create_studio_server",
    "list_build_files",
    "read_build_file",
]

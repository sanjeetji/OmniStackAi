"""Studio: the user-facing "chat -> create an app" web UI.

Brick 3 of the front door. Dependency-free (stdlib ``http.server``); the build function is
injected so the HTTP layer is testable offline.
"""

from .page import STUDIO_HTML
from .preview import StudioPreviewManager
from .server import BuildFn, create_studio_server

__all__ = ["STUDIO_HTML", "BuildFn", "StudioPreviewManager", "create_studio_server"]

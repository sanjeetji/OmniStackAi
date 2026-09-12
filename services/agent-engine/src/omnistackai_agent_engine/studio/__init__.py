"""Studio: the user-facing "chat -> create an app" web UI.

Brick 3 of the front door. Dependency-free (stdlib ``http.server``); the build function is
injected so the HTTP layer is testable offline.
"""

from .page import STUDIO_HTML
from .server import BuildFn, create_studio_server

__all__ = ["STUDIO_HTML", "BuildFn", "create_studio_server"]

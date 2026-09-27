"""PC-007: which engine runs a generated app's preview.

* ``local`` — the machine's own Node, pnpm and Python (R-419..R-573). Fastest where they exist.
* ``container`` — the whole app (API, web app, admin console) runs in one container. The machine
  needs Docker and nothing else: no Node, no pnpm, no Python, no Go. Under gVisor (``runsc``) where
  that runtime is registered, which is how a hosted service isolates one user's app from another's.
* ``webcontainer`` — Node in the visitor's browser. Needs StackBlitz's commercial licence (D-6), so
  it is a key supplied at the end (PC-070); until then it is reported as not available.

``OMNISTACKAI_PREVIEW_ENGINE`` chooses (``auto`` by default): ``auto`` uses ``local`` when the
toolchain is installed and ``container`` when it is not but Docker is.
"""

from __future__ import annotations

import os
import shutil
import subprocess

ENGINE_ENV = "OMNISTACKAI_PREVIEW_ENGINE"
LOCAL = "local"
CONTAINER = "container"
WEBCONTAINER = "webcontainer"
ENGINES = (LOCAL, CONTAINER, WEBCONTAINER)

#: What a local preview needs on the machine. Go is only needed for Go backends, so not listed.
LOCAL_TOOLCHAIN = ("node", "pnpm", "python3")


def missing_toolchain() -> tuple[str, ...]:
    return tuple(tool for tool in LOCAL_TOOLCHAIN if shutil.which(tool) is None)


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True,
                              timeout=10, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def resolve_engine(requested: str | None = None) -> str:
    """The engine to use now. ``webcontainer`` runs in the browser, so the server previews locally."""
    from .sandbox import multi_tenant

    if multi_tenant():
        # PC-009: on a shared host a generated app never runs on the host itself.
        return CONTAINER
    choice = (requested or os.environ.get(ENGINE_ENV, "") or "auto").strip().lower()
    if choice in (LOCAL, CONTAINER):
        return choice
    if choice == WEBCONTAINER:
        return LOCAL
    return LOCAL if not missing_toolchain() or not docker_available() else CONTAINER


def engine_status() -> dict:
    """For the Studio: what each engine needs, and whether it can run here. Metadata only."""
    missing = missing_toolchain()
    docker = docker_available()
    licence = bool(os.environ.get("OMNISTACKAI_WEBCONTAINER_CLIENT_ID", "").strip())
    return {
        "selected": resolve_engine(),
        "engines": [
            {"id": LOCAL, "available": not missing,
             "needs": "Node, pnpm and Python on this machine" + (f" (missing: {', '.join(missing)})" if missing else "")},
            {"id": CONTAINER, "available": docker, "needs": "Docker only"},
            {"id": WEBCONTAINER, "available": False,
             "needs": "a StackBlitz WebContainer licence key (supplied at go-live)" if not licence
             else "the in-browser engine (not built yet)"},
        ],
    }

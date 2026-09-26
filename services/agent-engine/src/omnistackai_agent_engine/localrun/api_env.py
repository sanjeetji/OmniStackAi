"""PC-006: a generated Python API starts from a shared, warm environment.

Measured on 2026-09-26, a preview of a blog app took 17.7 s to come up, and 9 s of it was the API:
a brand-new virtualenv (1.2 s), a pip install (2.1 s), then a first start that compiles and scans
every freshly installed package while two `next dev` servers boot beside it. Every generated
FastAPI app asks for the same pinned requirements, so one environment per distinct
`requirements.txt` serves them all: the first preview builds it, every later one links to it.

The link is `.venv` itself, so the project's own commands (`.venv/bin/uvicorn`) work unchanged and
the generated `.gitignore` (`.venv`) keeps it out of the repository. A project whose requirements
change gets a different environment, never a modified shared one. A project that already has a
real `.venv` of its own is left alone. Anything unexpected falls back to the per-project
virtualenv and install the plan already carries.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

CACHE_ENV = "OMNISTACKAI_API_VENV_CACHE"
READY_MARKER = ".omnistack-ready"


def cache_root() -> Path | None:
    """Where shared environments live; ``None`` when turned off (``OMNISTACKAI_API_VENV_CACHE=off``)."""
    configured = os.environ.get(CACHE_ENV, "").strip()
    if configured.lower() in ("off", "0", "false", "no"):
        return None
    return Path(configured).expanduser() if configured else Path.home() / ".omnistackai" / "api-venvs"


def _python() -> str | None:
    found = shutil.which("python3")
    return os.path.realpath(found) if found else None


def environment_key(requirements: bytes, python: str) -> str:
    """One environment per interpreter and exact requirements text."""
    return hashlib.sha256(python.encode() + b"\0" + requirements).hexdigest()[:16]


def _is_ready(env_dir: Path) -> bool:
    return (env_dir / READY_MARKER).is_file() and (env_dir / "bin" / "uvicorn").exists()


def _build(env_dir: Path, python: str, requirements: Path) -> bool:
    # Built in place: a virtualenv's scripts carry its absolute path, so it cannot be moved after.
    if env_dir.exists():
        shutil.rmtree(env_dir, ignore_errors=True)
    steps = (
        [python, "-m", "venv", str(env_dir)],
        [str(env_dir / "bin" / "pip"), "install", "-q", "-r", str(requirements)],
        # Compile once here, so no preview pays for it on its first start.
        [str(env_dir / "bin" / "python"), "-m", "compileall", "-q", str(env_dir / "lib")],
    )
    for command in steps:
        if subprocess.run(command, check=False, stdout=subprocess.DEVNULL).returncode != 0:
            shutil.rmtree(env_dir, ignore_errors=True)
            return False
    (env_dir / READY_MARKER).write_text("ok\n", encoding="utf-8")
    return True


def link_shared_environment(api_dir: str | Path) -> bool:
    """Point ``api_dir/.venv`` at the shared environment for its requirements.

    Returns True when the project is ready to start with no install of its own, False when the
    caller should create and install a per-project environment as before.
    """
    root = cache_root()
    python = _python()
    api = Path(api_dir)
    requirements = api / "requirements.txt"
    if root is None or python is None or not requirements.is_file():
        return False
    venv = api / ".venv"
    if venv.exists() and not venv.is_symlink():
        return False  # the project's own environment

    env_dir = root / environment_key(requirements.read_bytes(), python)
    if venv.is_symlink():
        if Path(os.path.realpath(venv)) == Path(os.path.realpath(env_dir)) and _is_ready(env_dir):
            return True
        venv.unlink()  # requirements changed since it was linked

    try:
        root.mkdir(parents=True, exist_ok=True)
        with open(root / f"{env_dir.name}.lock", "w") as lock:
            # Two previews of the same stack wait for one build rather than racing two.
            fcntl.flock(lock, fcntl.LOCK_EX)
            if not _is_ready(env_dir) and not _build(env_dir, python, requirements):
                return False
        os.symlink(env_dir, venv, target_is_directory=True)
    except OSError:
        return False
    return True

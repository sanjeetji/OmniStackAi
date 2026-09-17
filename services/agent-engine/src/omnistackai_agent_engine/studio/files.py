"""Read-only, path-safe access to a built app's files (R-467).

The Studio lets a user inspect what was generated -- a clickable file list and a read-only viewer --
backed directly by the files already committed to disk under a recorded build's ``target_dir``. No re-run
of codegen, no new state: this module only ever reads the filesystem, bounded and deterministically.

Path safety mirrors ``edit/apply.py``'s ``_safe_destination``: every requested path is joined onto the
build's root, resolved, and checked to still be inside that root via ``relative_to`` -- so ``../../etc/passwd``
style traversal (and a symlink that points outside the root) is refused rather than silently followed.
"""

from __future__ import annotations

import os
from pathlib import Path

_EXCLUDED_DIR_NAMES = frozenset({".git", "node_modules", "__pycache__", ".next", ".venv", "venv"})
_DEFAULT_MAX_ENTRIES = 4_000
_DEFAULT_MAX_FILE_BYTES = 512_000


class StudioFilesError(Exception):
    """Base for read-only file-access errors raised by this module."""


class BuildNotFoundError(StudioFilesError):
    """The build's recorded directory does not exist (or is not a directory) on disk."""


class PathOutsideBuildError(StudioFilesError):
    """The requested path is empty, absolute, or would resolve outside the build's directory."""


class FileNotFoundInBuildError(StudioFilesError):
    """The path is safe but does not name a readable file in the build (missing, a directory, or excluded)."""


def _is_secret_env_file(name: str) -> bool:
    """True for a real ``.env*`` file. ``.env.example`` is kept -- generators commit it on purpose; it
    never carries a secret (see codegen/nextjs.py's NEXT_PUBLIC_-only .env.example)."""
    return name == ".env" or (name.startswith(".env.") and name != ".env.example")


def _is_excluded_dir(name: str) -> bool:
    return name in _EXCLUDED_DIR_NAMES


def list_build_files(root_dir: str | os.PathLike[str], *, max_entries: int = _DEFAULT_MAX_ENTRIES) -> dict:
    """A sorted, flat, secret-free list of every readable file under a built app's directory.

    Skips VCS internals, installed dependencies, and build caches (``.git``, ``node_modules``,
    ``__pycache__``, ``.next``, ``.venv``, ``venv``) and any real ``.env`` file. Bounded by
    ``max_entries``; ``truncated`` is True when the walk was cut short.
    """
    root = Path(root_dir)
    if not root.is_dir():
        raise BuildNotFoundError(f"build directory does not exist: {root_dir}")
    paths: list[str] = []
    truncated = False
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _is_excluded_dir(d)]
        for filename in filenames:
            if _is_secret_env_file(filename):
                continue
            rel = Path(dirpath, filename).relative_to(root).as_posix()
            paths.append(rel)
            if len(paths) >= max_entries:
                truncated = True
                break
        if truncated:
            break
    paths.sort()
    return {"files": paths, "truncated": truncated}


def read_build_file(
    root_dir: str | os.PathLike[str], rel_path: str, *, max_bytes: int = _DEFAULT_MAX_FILE_BYTES
) -> dict:
    """Read one file's content from a built app's directory, path-safety-checked against ``root_dir``.

    Returns ``{"path", "content", "truncated", "binary", "size"}``. A binary file is reported
    (``binary: true``, empty content) rather than raised -- the viewer can say so plainly.
    """
    root = Path(root_dir)
    if not root.is_dir():
        raise BuildNotFoundError(f"build directory does not exist: {root_dir}")
    if not rel_path or rel_path.startswith("/") or rel_path.startswith("\\"):
        raise PathOutsideBuildError("path must be a non-empty, relative path")
    resolved_root = root.resolve()
    candidate = (resolved_root / rel_path).resolve()
    try:
        relative = candidate.relative_to(resolved_root)
    except ValueError as error:
        raise PathOutsideBuildError(f"path escapes the build directory: {rel_path}") from error
    if any(_is_excluded_dir(part) for part in relative.parts[:-1]) or _is_secret_env_file(relative.name):
        raise FileNotFoundInBuildError(f"no such file in this build: {rel_path}")
    if not candidate.is_file():
        raise FileNotFoundInBuildError(f"no such file in this build: {rel_path}")
    size = candidate.stat().st_size
    raw = candidate.read_bytes()[:max_bytes]
    truncated = size > max_bytes
    try:
        content = raw.decode("utf-8")
        binary = False
    except UnicodeDecodeError:
        content = ""
        binary = True
    return {
        "path": relative.as_posix(),
        "content": content,
        "truncated": truncated,
        "binary": binary,
        "size": size,
    }

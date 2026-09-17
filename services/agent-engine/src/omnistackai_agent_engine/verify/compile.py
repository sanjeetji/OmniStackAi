"""Capturing TypeScript compile executor (R-466).

`run_verify` records only exit codes. The hybrid UI engine needs *what* failed so it can feed the compiler's
own words back to the model: this module runs `tsc --noEmit --pretty false` for a generated web app, parses
the output into per-file errors, and returns a JSON-safe report. Opt-in — it needs the toolchain — and never
called by `task verify`, which exercises `parse_tsc_output` and an injected fake runner only.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import VerifyError

# `tsc --pretty false` prints one diagnostic per line: `app/page.tsx(12,5): error TS2339: Property ...`
_TSC_LINE = re.compile(
    r"^(?P<path>[^\r\n(]+?)\((?P<line>\d+),(?P<column>\d+)\): error (?P<code>TS\d+): (?P<message>.*)$"
)
_TSC_ARGS = ("--noEmit", "--pretty", "false")
_INSTALL_ARGS = ("pnpm", "install", "--ignore-scripts")

# A runner takes (argv, cwd, timeout_seconds) and returns something with returncode/stdout/stderr.
Runner = Callable[[list[str], str, float], Any]


@dataclass(frozen=True, slots=True)
class CompileError:
    """One compiler diagnostic, with a web-app-relative POSIX path."""

    path: str
    line: int
    column: int
    code: str
    message: str

    def render(self) -> str:
        return f"L{self.line}:{self.column} {self.code}: {self.message}"


@dataclass(frozen=True, slots=True)
class CompileReport:
    """The outcome of one compile pass: JSON-safe, bounded, never carries a secret."""

    ok: bool
    returncode: int
    errors: tuple[CompileError, ...]
    output_tail: str

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def errors_by_file(self) -> dict[str, tuple[CompileError, ...]]:
        grouped: dict[str, list[CompileError]] = {}
        for error in self.errors:
            grouped.setdefault(error.path, []).append(error)
        return {path: tuple(errors) for path, errors in grouped.items()}

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "returncode": self.returncode,
            "error_count": self.error_count,
            "files": {path: [error.render() for error in errors] for path, errors in self.errors_by_file().items()},
            "output_tail": self.output_tail,
        }


def parse_tsc_output(text: str) -> tuple[CompileError, ...]:
    """Parse `tsc --pretty false` output into de-duplicated diagnostics (pure)."""

    seen: set[tuple[str, int, int, str, str]] = set()
    errors: list[CompileError] = []
    for raw_line in (text or "").splitlines():
        match = _TSC_LINE.match(raw_line.strip())
        if match is None:
            continue
        path = match["path"].strip().replace("\\", "/")
        key = (path, int(match["line"]), int(match["column"]), match["code"], match["message"].strip())
        if key in seen:
            continue
        seen.add(key)
        errors.append(CompileError(*key))
    return tuple(errors)


def _default_runner(argv: list[str], cwd: str, timeout_seconds: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout_seconds, check=False)


def tsc_binary(web_dir: str | os.PathLike[str]) -> Path:
    return Path(web_dir) / "node_modules" / ".bin" / "tsc"


def _output_of(completed: Any) -> str:
    stdout = str(getattr(completed, "stdout", "") or "")
    stderr = str(getattr(completed, "stderr", "") or "")
    return stdout + ("\n" + stderr if stderr else "")


def compile_web_project(
    web_dir: str | os.PathLike[str],
    *,
    runner: Runner | None = None,
    timeout_seconds: float = 600.0,
    tail_chars: int = 4_000,
) -> CompileReport:
    """Type-check a generated web app with its own installed `tsc` and capture every diagnostic.

    Opt-in (toolchain). Raises VerifyError when the app directory or `node_modules/.bin/tsc` is missing or
    the compiler times out; a compile *failure* is a report, not an exception.
    """

    web = Path(web_dir)
    if not web.is_dir():
        raise VerifyError(f"web app directory does not exist: {web}")
    tsc = tsc_binary(web)
    if not tsc.exists():
        raise VerifyError(
            "tsc is not installed for this app; run `pnpm install --ignore-scripts` in the web app directory "
            "(or ensure_web_dependencies) first"
        )
    run = runner or _default_runner
    try:
        completed = run([str(tsc), *_TSC_ARGS], str(web), float(timeout_seconds))
    except subprocess.TimeoutExpired as error:
        raise VerifyError(f"tsc timed out after {float(timeout_seconds):.0f}s") from error
    output = _output_of(completed)
    returncode = getattr(completed, "returncode", 1)
    returncode = returncode if isinstance(returncode, int) else 1
    errors = parse_tsc_output(output)
    return CompileReport(returncode == 0 and not errors, returncode, errors, output[-tail_chars:])


def ensure_web_dependencies(
    web_dir: str | os.PathLike[str],
    *,
    node_modules_source: str | os.PathLike[str] | None = None,
    runner: Runner | None = None,
    timeout_seconds: float = 900.0,
) -> str:
    """Make `node_modules` available: reuse it, symlink an existing install, or `pnpm install`.

    Returns "present", "linked" or "installed". Opt-in (toolchain); raises VerifyError when pnpm is
    missing or the install fails.
    """

    web = Path(web_dir)
    if not web.is_dir():
        raise VerifyError(f"web app directory does not exist: {web}")
    target = web / "node_modules"
    if target.exists():
        return "present"
    if node_modules_source:
        source = Path(node_modules_source)
        if not source.is_dir():
            raise VerifyError(f"node_modules source is not a directory: {source}")
        target.symlink_to(source.resolve(), target_is_directory=True)
        return "linked"
    run = runner or _default_runner
    try:
        completed = run(list(_INSTALL_ARGS), str(web), float(timeout_seconds))
    except FileNotFoundError as error:
        raise VerifyError("pnpm is not installed; install pnpm or set OMNISTACKAI_WEB_NODE_MODULES") from error
    except subprocess.TimeoutExpired as error:
        raise VerifyError(f"pnpm install timed out after {float(timeout_seconds):.0f}s") from error
    returncode = getattr(completed, "returncode", 1)
    if returncode != 0:
        raise VerifyError(f"pnpm install failed (exit {returncode}): {_output_of(completed)[-500:]}")
    return "installed"

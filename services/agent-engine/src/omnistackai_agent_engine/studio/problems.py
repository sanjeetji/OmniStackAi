"""On-demand compile/type-check reporting for a built app (R-480).

Real TypeScript compile-error reporting for the Studio's Problems tab -- the first time this
codebase has surfaced `verify/compile.py`'s real `compile_web_project()` machinery through the
Studio path at all (previously only a standalone CLI script called it, never `_build()`/`_edit()`).

Deliberately **on-demand, not automatic**: `node_modules`/`tsc` only exist in a generated repo after
a live-preview install (`ensure_web_dependencies`), which can itself be a real, minutes-long,
network-dependent operation. Running a compile check automatically on every build/edit would make
the fast, network-light core loop slower and more toolchain-dependent than today -- a real
regression risk this module deliberately avoids. A caller triggers a check explicitly
(`check_build_problems`); a bounded, in-memory `StudioProblemsStore` (the same OrderedDict-as-LRU
idiom `StudioSessionStore`/`StudioBuildHistory` already use) remembers the last report per build id
so a repeated read does not have to recompile.
"""

from __future__ import annotations

import os
from collections import OrderedDict
from pathlib import Path
from threading import Lock

from ..verify.compile import Runner, compile_web_project
from ..verify.errors import VerifyError

_DEFAULT_LIMIT = 50


class StudioProblemsError(Exception):
    """Base for problems-check errors raised by this module."""


class NoWebTargetError(StudioProblemsError):
    """The generated project has no web target (`apps/web`) to type-check."""


class ToolchainNotInstalledError(StudioProblemsError):
    """`tsc` is not installed for this build yet -- install dependencies via live preview first.

    Deliberately never triggers an install as a side effect of a "check problems" click; the caller
    should not be surprised by a silent, possibly-minutes-long `pnpm install` they didn't ask for.
    """


class ProblemsNotCheckedError(StudioProblemsError):
    """No problems check has been run yet for this build (`StudioProblemsStore` has no entry)."""


def check_build_problems(root_dir: str | os.PathLike[str], *, runner: Runner | None = None) -> dict:
    """Type-check `root_dir`'s web app (`apps/web`) and return a JSON-safe `CompileReport` dict.

    Raises `NoWebTargetError` when the generated project has no web app at all, and
    `ToolchainNotInstalledError` when the web app exists but its dependencies (and therefore `tsc`)
    have not been installed yet -- both real, actionable states, not generic failures. `runner` is
    passed straight through to `compile_web_project` -- tests inject a fake one, exactly like
    `verify/compile.py`'s own tests do, so this module's own tests need no real toolchain either.
    """
    web_dir = Path(root_dir) / "apps" / "web"
    if not (web_dir / "package.json").is_file():
        raise NoWebTargetError("this build has no web app to check for problems")
    try:
        report = compile_web_project(web_dir, runner=runner)
    except VerifyError as error:
        raise ToolchainNotInstalledError(str(error)) from error
    return report.to_dict()


class StudioProblemsStore:
    """A bounded, thread-safe, in-memory map of build id -> last `CompileReport` dict.

    Bounded by `limit`, evicting the least-recently-set entry -- mirrors
    `StudioSessionStore`'s own bounded-LRU idiom. Server-only, lost on restart, same as every other
    Studio in-memory store.
    """

    def __init__(self, *, limit: int = _DEFAULT_LIMIT) -> None:
        self._limit = max(1, limit)
        self._reports: OrderedDict[str, dict] = OrderedDict()
        self._lock = Lock()

    def set(self, build_id: str, report: dict) -> None:
        with self._lock:
            self._reports[build_id] = report
            self._reports.move_to_end(build_id)
            while len(self._reports) > self._limit:
                self._reports.popitem(last=False)

    def get(self, build_id: str) -> dict | None:
        with self._lock:
            return self._reports.get(build_id)

"""R-480: on-demand compile/type-check reporting for the Studio (studio/problems.py).

Pure filesystem checks plus an injected fake runner, mirroring verify/compile.py's own tests:
no toolchain, no real subprocess, no network under `task verify`.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from omnistackai_agent_engine.studio.files import BuildNotFoundError
from omnistackai_agent_engine.studio.history import StudioBuildHistory
from omnistackai_agent_engine.studio.live_serve import _check_build_problems, _get_build_problems
from omnistackai_agent_engine.studio.problems import (
    NoWebTargetError,
    ProblemsNotCheckedError,
    StudioProblemsStore,
    ToolchainNotInstalledError,
    check_build_problems,
)

_SAMPLE = "app/page.tsx(12,5): error TS2339: Property 'x' does not exist.\n"


class _FakeRunner:
    def __init__(self, steps: list) -> None:
        self._steps = list(steps)
        self.calls: list[tuple[list[str], str, float]] = []

    def __call__(self, argv: list[str], cwd: str, timeout_seconds: float) -> SimpleNamespace:
        self.calls.append((argv, cwd, timeout_seconds))
        returncode, stdout = self._steps.pop(0)
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")


def _fake_web_app(root: Path, *, with_tsc: bool = True) -> None:
    web = root / "apps" / "web"
    web.mkdir(parents=True)
    (web / "package.json").write_text("{}\n", encoding="utf-8")
    if with_tsc:
        (web / "node_modules" / ".bin").mkdir(parents=True)
        (web / "node_modules" / ".bin" / "tsc").write_text("#!/bin/sh\n", encoding="utf-8")


class CheckBuildProblemsTests(unittest.TestCase):
    def test_no_web_app_raises_no_web_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(NoWebTargetError):
                check_build_problems(tmp)

    def test_missing_tsc_raises_toolchain_not_installed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fake_web_app(root, with_tsc=False)
            with self.assertRaises(ToolchainNotInstalledError):
                check_build_problems(root)

    def test_clean_compile_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fake_web_app(root)
            report = check_build_problems(root, runner=_FakeRunner([(0, "")]))
            self.assertTrue(report["ok"])
            self.assertEqual(report["error_count"], 0)

    def test_errors_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fake_web_app(root)
            report = check_build_problems(root, runner=_FakeRunner([(2, _SAMPLE)]))
            self.assertFalse(report["ok"])
            self.assertEqual(report["error_count"], 1)
            self.assertIn("app/page.tsx", report["files"])

    def test_report_is_json_serializable(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fake_web_app(root)
            json.dumps(check_build_problems(root, runner=_FakeRunner([(0, "")])))

    def test_runner_invoked_against_the_web_subdirectory_not_the_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fake_web_app(root)
            runner = _FakeRunner([(0, "")])
            check_build_problems(root, runner=runner)
            _argv, cwd, _timeout = runner.calls[0]
            self.assertEqual(Path(cwd), root / "apps" / "web")


class StudioProblemsStoreTests(unittest.TestCase):
    def test_get_returns_none_when_never_set(self) -> None:
        store = StudioProblemsStore()
        self.assertIsNone(store.get("unknown"))

    def test_set_then_get_roundtrips(self) -> None:
        store = StudioProblemsStore()
        report = {"ok": True, "returncode": 0, "error_count": 0, "files": {}, "output_tail": ""}
        store.set("build-1", report)
        self.assertEqual(store.get("build-1"), report)

    def test_bounded_eviction_of_oldest(self) -> None:
        store = StudioProblemsStore(limit=2)
        store.set("a", {"n": 1})
        store.set("b", {"n": 2})
        store.set("c", {"n": 3})
        self.assertIsNone(store.get("a"))
        self.assertEqual(store.get("b"), {"n": 2})
        self.assertEqual(store.get("c"), {"n": 3})

    def test_re_setting_an_existing_id_counts_as_a_touch(self) -> None:
        store = StudioProblemsStore(limit=2)
        store.set("a", {"n": 1})
        store.set("b", {"n": 2})
        store.set("a", {"n": 11})  # touches "a" again - "b" is now the oldest
        store.set("c", {"n": 3})
        self.assertIsNone(store.get("b"))
        self.assertEqual(store.get("a"), {"n": 11})
        self.assertEqual(store.get("c"), {"n": 3})


class LiveServeProblemsWiringTests(unittest.TestCase):
    """studio/live_serve.py's _check_build_problems/_get_build_problems glue (R-480)."""

    def test_check_unknown_build_raises_build_not_found(self) -> None:
        history = StudioBuildHistory()
        store = StudioProblemsStore()
        with self.assertRaises(BuildNotFoundError):
            _check_build_problems("no-such-id", history, store)

    def test_get_unknown_build_raises_build_not_found(self) -> None:
        history = StudioBuildHistory()
        store = StudioProblemsStore()
        with self.assertRaises(BuildNotFoundError):
            _get_build_problems("no-such-id", history, store)

    def test_get_before_any_check_raises_not_checked_yet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fake_web_app(root)
            history = StudioBuildHistory()
            build_id = history.record({"target_dir": str(root)})
            store = StudioProblemsStore()
            with self.assertRaises(ProblemsNotCheckedError):
                _get_build_problems(build_id, history, store)

    def test_a_failed_check_is_not_stored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fake_web_app(root, with_tsc=False)  # package.json exists, so NoWebTargetError is not
            history = StudioBuildHistory()  # raised; the missing tsc raises ToolchainNotInstalledError.
            build_id = history.record({"target_dir": str(root)})
            store = StudioProblemsStore()
            with self.assertRaises(ToolchainNotInstalledError):
                _check_build_problems(build_id, history, store)
            # A failed check (an exception, not a report) never reaches problems_store.set().
            with self.assertRaises(ProblemsNotCheckedError):
                _get_build_problems(build_id, history, store)


if __name__ == "__main__":
    unittest.main()

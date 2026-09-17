"""R-466: the capturing TypeScript compile executor (verify/compile.py).

Pure parsing plus an injected fake runner: no toolchain, no subprocess, no network under `task verify`.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from omnistackai_agent_engine.verify import (
    CompileError,
    CompileReport,
    VerifyError,
    compile_web_project,
    ensure_web_dependencies,
    parse_tsc_output,
)

_SAMPLE = """\
app/page.tsx(12,5): error TS2339: Property 'refresh' does not exist on type 'UseListPosts'.
app/page.tsx(40,11): error TS2322: Type 'string' is not assignable to type 'number'.
app/posts/page.tsx(7,3): error TS2304: Cannot find name 'Foo'.
app/page.tsx(12,5): error TS2339: Property 'refresh' does not exist on type 'UseListPosts'.
Found 3 errors in 2 files.
"""


class _FakeRunner:
    """Scripted (returncode, stdout) results; records every call."""

    def __init__(self, steps: list) -> None:
        self._steps = list(steps)
        self.calls: list[tuple[list[str], str, float]] = []

    def __call__(self, argv: list[str], cwd: str, timeout_seconds: float) -> SimpleNamespace:
        self.calls.append((argv, cwd, timeout_seconds))
        step = self._steps.pop(0)
        if isinstance(step, Exception):
            raise step
        returncode, stdout = step
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")


def _fake_web_app(root: str) -> Path:
    web = Path(root) / "apps" / "web"
    (web / "node_modules" / ".bin").mkdir(parents=True)
    (web / "node_modules" / ".bin" / "tsc").write_text("#!/bin/sh\n", encoding="utf-8")
    return web


class ParseTests(unittest.TestCase):
    def test_parses_and_deduplicates_diagnostics(self) -> None:
        errors = parse_tsc_output(_SAMPLE)
        self.assertEqual(len(errors), 3)
        first = errors[0]
        self.assertEqual((first.path, first.line, first.column, first.code), ("app/page.tsx", 12, 5, "TS2339"))
        self.assertIn("does not exist", first.message)
        self.assertEqual(first.render(), "L12:5 TS2339: Property 'refresh' does not exist on type 'UseListPosts'.")

    def test_windows_paths_are_normalized_and_noise_is_ignored(self) -> None:
        errors = parse_tsc_output("app\\posts\\page.tsx(1,1): error TS1005: ';' expected.\nrandom noise\n")
        self.assertEqual([e.path for e in errors], ["app/posts/page.tsx"])
        self.assertEqual(parse_tsc_output(""), ())

    def test_report_groups_by_file_and_is_json_safe(self) -> None:
        report = CompileReport(False, 2, parse_tsc_output(_SAMPLE), "tail")
        grouped = report.errors_by_file()
        self.assertEqual(list(grouped), ["app/page.tsx", "app/posts/page.tsx"])
        self.assertEqual(len(grouped["app/page.tsx"]), 2)
        self.assertEqual(report.error_count, 3)
        payload = json.loads(json.dumps(report.to_dict()))
        self.assertEqual(payload["files"]["app/posts/page.tsx"], ["L7:3 TS2304: Cannot find name 'Foo'."])
        self.assertIsInstance(CompileError("a.ts", 1, 1, "TS1", "m"), CompileError)


class CompileWebProjectTests(unittest.TestCase):
    def test_runs_tsc_with_captured_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            web = _fake_web_app(tmp)
            runner = _FakeRunner([(2, _SAMPLE)])
            report = compile_web_project(web, runner=runner, timeout_seconds=30)
            self.assertFalse(report.ok)
            self.assertEqual(report.returncode, 2)
            self.assertEqual(report.error_count, 3)
            argv, cwd, timeout = runner.calls[0]
            self.assertEqual(argv[1:], ["--noEmit", "--pretty", "false"])
            self.assertTrue(argv[0].endswith(os.path.join("node_modules", ".bin", "tsc")))
            self.assertEqual(Path(cwd), web)
            self.assertEqual(timeout, 30.0)
            self.assertIn("Found 3 errors", report.output_tail)

    def test_clean_compile_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = compile_web_project(_fake_web_app(tmp), runner=_FakeRunner([(0, "")]))
            self.assertTrue(report.ok)
            self.assertEqual(report.errors, ())

    def test_missing_tsc_or_directory_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(VerifyError):
                compile_web_project(Path(tmp) / "nope", runner=_FakeRunner([]))
            web = Path(tmp) / "apps" / "web"
            web.mkdir(parents=True)
            with self.assertRaises(VerifyError):
                compile_web_project(web, runner=_FakeRunner([]))

    def test_timeout_is_a_verify_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _FakeRunner([subprocess.TimeoutExpired(cmd="tsc", timeout=1)])
            with self.assertRaises(VerifyError):
                compile_web_project(_fake_web_app(tmp), runner=runner, timeout_seconds=1)


class EnsureDependenciesTests(unittest.TestCase):
    def test_present_install_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _FakeRunner([])
            self.assertEqual(ensure_web_dependencies(_fake_web_app(tmp), runner=runner), "present")
            self.assertEqual(runner.calls, [])

    def test_existing_install_is_symlinked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "shared_node_modules"
            source.mkdir()
            web = Path(tmp) / "apps" / "web"
            web.mkdir(parents=True)
            self.assertEqual(ensure_web_dependencies(web, node_modules_source=source, runner=_FakeRunner([])), "linked")
            self.assertTrue((web / "node_modules").is_symlink())
            self.assertEqual((web / "node_modules").resolve(), source.resolve())

    def test_install_runs_pnpm_in_the_web_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp) / "apps" / "web"
            web.mkdir(parents=True)
            runner = _FakeRunner([(0, "done")])
            self.assertEqual(ensure_web_dependencies(web, runner=runner), "installed")
            argv, cwd, _ = runner.calls[0]
            self.assertEqual(argv, ["pnpm", "install", "--ignore-scripts"])
            self.assertEqual(Path(cwd), web)

    def test_install_failures_are_verify_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp) / "apps" / "web"
            web.mkdir(parents=True)
            with self.assertRaises(VerifyError):
                ensure_web_dependencies(web, runner=_FakeRunner([(1, "ERR_PNPM")]))
            with self.assertRaises(VerifyError) as raised:
                ensure_web_dependencies(web, runner=_FakeRunner([FileNotFoundError("pnpm")]))
            self.assertIn("pnpm", str(raised.exception))
            with self.assertRaises(VerifyError):
                ensure_web_dependencies(web, node_modules_source=Path(tmp) / "missing", runner=_FakeRunner([]))


if __name__ == "__main__":
    unittest.main()

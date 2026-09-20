"""Automated test runner and result reporter for generated projects (F-10 / R-508).

Discovers and executes tests across:
- Web: pnpm test / npm test
- Python: python3 -m unittest / pytest
- Go: go test -v ./...

Parses test results into structured format and reports an honest empty state when no tests exist.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _detect_test_suites(repo_dir: Path) -> list[dict[str, Any]]:
    """Detect which test frameworks are configured in the project."""
    suites = []

    # 1. Web (Next.js / TypeScript)
    web_dir = repo_dir / "apps" / "web"
    if not (web_dir / "package.json").is_file():
        web_dir = repo_dir

    pkg_json_file = web_dir / "package.json"
    if pkg_json_file.is_file():
        try:
            pkg_data = json.loads(pkg_json_file.read_text(encoding="utf-8"))
            scripts = pkg_data.get("scripts", {})
            if "test" in scripts:
                suites.append({
                    "id": "web",
                    "name": "Web App Tests",
                    "cwd": web_dir,
                    "kind": "web",
                })
        except (OSError, json.JSONDecodeError):
            pass

    # 2. Python Backend
    py_dir = repo_dir / "services" / "api"
    if not py_dir.is_dir():
        py_dir = repo_dir

    has_py_tests = False
    tests_folder = py_dir / "tests"
    if tests_folder.is_dir() and any(tests_folder.glob("test_*.py")):
        has_py_tests = True
    elif any(py_dir.glob("test_*.py")):
        has_py_tests = True

    if has_py_tests:
        suites.append({
            "id": "python",
            "name": "Python Backend Tests",
            "cwd": py_dir,
            "kind": "python",
        })

    # 3. Go Backend
    go_dir = repo_dir / "services" / "api"
    if not (go_dir / "go.mod").is_file():
        go_dir = repo_dir

    if (go_dir / "go.mod").is_file() and any(go_dir.glob("**/*_test.go")):
        suites.append({
            "id": "go",
            "name": "Go Backend Tests",
            "cwd": go_dir,
            "kind": "go",
        })

    return suites


def _run_single_suite(suite_info: dict[str, Any]) -> dict[str, Any]:
    """Execute tests for a single suite and parse output."""
    kind = suite_info["kind"]
    cwd = suite_info["cwd"]
    name = suite_info["name"]

    cmd: list[str] = []
    if kind == "web":
        if shutil.which("pnpm"):
            cmd = ["pnpm", "test"]
        elif shutil.which("npm"):
            cmd = ["npm", "test"]
    elif kind == "python":
        if shutil.which("pytest"):
            cmd = ["pytest", "-v"]
        else:
            cmd = ["python3", "-m", "unittest", "discover", "-v"]
    elif kind == "go":
        if shutil.which("go"):
            cmd = ["go", "test", "-v", "./..."]

    if not cmd:
        return {
            "name": name,
            "passed": 0,
            "failed": 0,
            "skipped": 1,
            "duration_ms": 0,
            "status": "skipped",
            "message": f"Runner executable for {kind} not found",
            "tests": [],
            "raw_output": f"Skipped: toolchain for {kind} not installed",
        }

    t0 = time.monotonic()
    try:
        res = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=60,
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        raw_output = (res.stdout + "\n" + res.stderr).strip()
    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - t0) * 1000)
        return {
            "name": name,
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "duration_ms": duration_ms,
            "status": "failed",
            "message": "Test execution timed out after 60s",
            "tests": [],
            "raw_output": "Timed out after 60 seconds",
        }
    except Exception as ex:
        duration_ms = int((time.monotonic() - t0) * 1000)
        return {
            "name": name,
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "duration_ms": duration_ms,
            "status": "failed",
            "message": str(ex),
            "tests": [],
            "raw_output": str(ex),
        }

    # Parse output
    tests: list[dict[str, Any]] = []
    passed = 0
    failed = 0
    skipped = 0

    lines = raw_output.splitlines()
    for line in lines:
        line_clean = line.strip()
        # Look for test case lines: e.g. "=== RUN", "--- PASS: TestX", "--- FAIL: TestY" in Go
        go_pass = re.match(r"---\s+PASS:\s+(\S+)\s+\(([\d\.]+)s\)", line_clean)
        go_fail = re.match(r"---\s+FAIL:\s+(\S+)\s+\(([\d\.]+)s\)", line_clean)
        if go_pass:
            passed += 1
            tests.append({
                "name": go_pass.group(1),
                "status": "passed",
                "duration_ms": int(float(go_pass.group(2)) * 1000),
            })
            continue
        if go_fail:
            failed += 1
            tests.append({
                "name": go_fail.group(1),
                "status": "failed",
                "duration_ms": int(float(go_fail.group(2)) * 1000),
            })
            continue

        # Python unittest: e.g. "test_something (module.TestClass) ... ok"
        py_ok = re.match(r"(\S+)\s+\(([\w\.]+)\)\s+\.\.\.\s+ok", line_clean)
        py_fail = re.match(r"(\S+)\s+\(([\w\.]+)\)\s+\.\.\.\s+(FAIL|ERROR)", line_clean)
        if py_ok:
            passed += 1
            tests.append({
                "name": f"{py_ok.group(2)}.{py_ok.group(1)}",
                "status": "passed",
                "duration_ms": 0,
            })
            continue
        if py_fail:
            failed += 1
            tests.append({
                "name": f"{py_fail.group(2)}.{py_fail.group(1)}",
                "status": "failed",
                "duration_ms": 0,
            })
            continue

        # Jest / Vitest / pnpm test: e.g. "✓ test name" or "✕ test name"
        jest_pass = re.match(r"(?:✓|PASS)\s+(.+?)(?:\s+\((\d+)\s*ms\))?$", line_clean)
        jest_fail = re.match(r"(?:✕|FAIL)\s+(.+?)(?:\s+\((\d+)\s*ms\))?$", line_clean)
        if jest_pass and not line_clean.startswith("PASS "):
            passed += 1
            ms = int(jest_pass.group(2)) if jest_pass.group(2) else 0
            tests.append({
                "name": jest_pass.group(1),
                "status": "passed",
                "duration_ms": ms,
            })
            continue
        if jest_fail and not line_clean.startswith("FAIL "):
            failed += 1
            ms = int(jest_fail.group(2)) if jest_fail.group(2) else 0
            tests.append({
                "name": jest_fail.group(1),
                "status": "failed",
                "duration_ms": ms,
            })
            continue

    # Fallback counts if individual lines weren't matched
    if passed == 0 and failed == 0:
        if res.returncode == 0:
            passed = 1
        else:
            failed = 1

    overall_status = "passed" if (res.returncode == 0 and failed == 0) else "failed"

    return {
        "name": name,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration_ms": duration_ms,
        "status": overall_status,
        "tests": tests,
        "raw_output": raw_output,
    }


def run_project_tests(repo_dir: str | Path) -> dict[str, Any]:
    """Discover and execute all test suites in *repo_dir*."""
    repo_path = Path(repo_dir)
    suites_info = _detect_test_suites(repo_path)

    if not suites_info:
        empty_report = {
            "suites": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration_ms": 0,
            },
            "raw_output": "",
            "message": "This project has no test suite yet — ask the chat to add one.",
            "ran_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_test_report(repo_path, empty_report)
        return empty_report

    suite_results = []
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_duration = 0
    all_raw: list[str] = []

    for s in suites_info:
        res = _run_single_suite(s)
        suite_results.append(res)
        total_passed += res.get("passed", 0)
        total_failed += res.get("failed", 0)
        total_skipped += res.get("skipped", 0)
        total_duration += res.get("duration_ms", 0)
        all_raw.append(f"=== Suite: {res.get('name')} ===\n" + res.get("raw_output", ""))

    report = {
        "suites": suite_results,
        "summary": {
            "total": total_passed + total_failed + total_skipped,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "duration_ms": total_duration,
        },
        "raw_output": "\n\n".join(all_raw),
        "message": None,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }

    _save_test_report(repo_path, report)
    return report


def _save_test_report(repo_path: Path, report: dict[str, Any]) -> None:
    try:
        cache_file = repo_path / ".omnistackai_test_report.json"
        cache_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError:
        pass


def get_last_test_report(repo_dir: str | Path) -> dict[str, Any] | None:
    """Retrieve last cached test report for *repo_dir*, or None."""
    cache_file = Path(repo_dir) / ".omnistackai_test_report.json"
    if not cache_file.is_file():
        return None
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

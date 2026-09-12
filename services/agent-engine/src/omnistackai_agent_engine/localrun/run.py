"""Opt-in executor: run a generated app repo locally with one command (R-419).

Excluded from static verification. Usage (via the Task wrapper, which starts Postgres first):

    task agent-engine:app:run -- /path/to/generated/repo

It recreates a clean per-app database, applies the migrations, installs and starts the
backend (:8000) and the web app (:3000), waits for the API to be healthy, prints the URLs,
and shuts both servers down cleanly on Ctrl+C. Local only; no cloud, no secrets in output.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from .plan import RunPlan, RunStep, build_run_plan


def _plan_from_env(repo_dir: str) -> RunPlan:
    return build_run_plan(
        repo_dir,
        db_container=os.environ.get("OMNISTACKAI_POSTGRES_CONTAINER", "omnistackai-local-postgres-1"),
        db_user=os.environ.get("OMNISTACKAI_POSTGRES_USER", "omnistackai"),
        db_password=os.environ.get("OMNISTACKAI_POSTGRES_PASSWORD", ""),
        db_host=os.environ.get("OMNISTACKAI_POSTGRES_HOST", "127.0.0.1"),
        db_port=int(os.environ.get("OMNISTACKAI_POSTGRES_PORT", "5432")),
        maintenance_db=os.environ.get("OMNISTACKAI_POSTGRES_DB", "omnistackai"),
        api_port=int(os.environ.get("OMNISTACKAI_APP_API_PORT", "8000")),
        web_port=int(os.environ.get("OMNISTACKAI_APP_WEB_PORT", "3000")),
        jwt_secret=os.environ.get("OMNISTACKAI_APP_JWT_SECRET", "local-dev-secret"),
    )


def _should_skip(step: RunStep) -> bool:
    cwd = Path(step.cwd) if step.cwd else Path.cwd()
    if step.label.startswith("create backend virtualenv") and (cwd / ".venv").is_dir():
        return True
    if step.label.startswith("install web dependencies") and (cwd / "node_modules" / ".bin" / "next").exists():
        return True
    return False


def _run_sync(step: RunStep) -> None:
    env = {**os.environ, **dict(step.env)}
    stdin = open(step.stdin_file, "rb") if step.stdin_file else None
    try:
        result = subprocess.run(
            [step.program, *step.args], cwd=step.cwd, env=env, stdin=stdin, check=False
        )
    finally:
        if stdin is not None:
            stdin.close()
    if result.returncode != 0 and not step.tolerate_failure:
        raise SystemExit(f"step failed: {step.label} (exit {result.returncode})")


def _launch(step: RunStep) -> subprocess.Popen:
    env = {**os.environ, **dict(step.env)}
    return subprocess.Popen([step.program, *step.args], cwd=step.cwd, env=env)


def _wait_healthy(url: str, timeout_seconds: float = 45.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(1.0)
    return False


def run_app(repo_dir: str) -> None:
    root = Path(repo_dir).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")
    plan = _plan_from_env(str(root))
    print(f"Running generated app at: {root}")
    print(f"  backend: {plan.backend_kind}   web: {'yes' if plan.has_web else 'no'}   db: {plan.db_name}")

    servers: list[subprocess.Popen] = []
    try:
        for step in plan.steps:
            if step.background:
                print(f"-> {step.label}")
                servers.append(_launch(step))
                continue
            if _should_skip(step):
                print(f"-  {step.label} (already done, skipping)")
                continue
            print(f"-> {step.label}")
            _run_sync(step)

        if plan.backend_kind != "none":
            print("Waiting for the API to be healthy ...")
            if _wait_healthy(plan.api_url + "/healthz"):
                print(f"API ready: {plan.api_url}")
            else:
                print(f"API not healthy yet at {plan.api_url} (it may still be starting)")

        print("\n================ App is running ================")
        if plan.has_web:
            print(f"  Web:  {plan.web_url}")
        if plan.backend_kind != "none":
            print(f"  API:  {plan.api_url}   (docs at {plan.api_url}/docs)")
        print("  Press Ctrl+C to stop.")
        print("===============================================\n")

        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping app ...")
    finally:
        for proc in servers:
            proc.terminate()
        for proc in servers:
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> None:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        raise SystemExit("usage: app:run -- <path-to-generated-repo>")
    run_app(sys.argv[1])


if __name__ == "__main__":
    main()

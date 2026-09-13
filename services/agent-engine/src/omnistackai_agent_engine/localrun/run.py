"""Opt-in executor and managed local app session (R-419/R-421).

Excluded from static verification. Usage (via the Task wrapper, which starts Postgres first):

    task agent-engine:app:run -- /path/to/generated/repo

It recreates a clean per-app database, applies the migrations, installs and starts the
backend (:8000) and the web app (:3000), checks readiness, prints the URLs,
and shuts both servers down cleanly on Ctrl+C. Local only; no cloud, no secrets in output.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .plan import RunPlan, RunStep, build_run_plan


class LocalAppRunError(RuntimeError):
    """A generated app could not be started or made ready in trusted-local mode."""


class LocalAppSession:
    """Own the child processes and readiness state for one locally running generated app."""

    def __init__(self, plan: RunPlan, *, processes: list[subprocess.Popen] | None = None) -> None:
        self.plan = plan
        self.processes = [] if processes is None else processes
        self.api_ready = False
        self.web_ready = False
        self._stopped = False

    def is_alive(self) -> bool:
        """True only when this session is not stopped and every owned process is still running."""
        if self._stopped or not self.processes:
            return False
        return all(process.poll() is None for process in self.processes)

    def stop(self) -> None:
        """Terminate every owned process; safe to call more than once."""
        if self._stopped:
            return
        self._stopped = True
        for process in self.processes:
            try:
                process.terminate()
            except OSError:
                pass
        for process in self.processes:
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                    process.wait(timeout=3)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            except OSError:
                pass


def _plan_from_env(
    repo_dir: str, *, api_port: int | None = None, web_port: int | None = None
) -> RunPlan:
    return build_run_plan(
        repo_dir,
        db_container=os.environ.get("OMNISTACKAI_POSTGRES_CONTAINER", "omnistackai-local-postgres-1"),
        db_user=os.environ.get("OMNISTACKAI_POSTGRES_USER", "omnistackai"),
        db_password=os.environ.get("OMNISTACKAI_POSTGRES_PASSWORD", ""),
        db_host=os.environ.get("OMNISTACKAI_POSTGRES_HOST", "127.0.0.1"),
        db_port=int(os.environ.get("OMNISTACKAI_POSTGRES_PORT", "5432")),
        maintenance_db=os.environ.get("OMNISTACKAI_POSTGRES_DB", "omnistackai"),
        api_port=api_port if api_port is not None else int(os.environ.get("OMNISTACKAI_APP_API_PORT", "8000")),
        web_port=web_port if web_port is not None else int(os.environ.get("OMNISTACKAI_APP_WEB_PORT", "3000")),
        jwt_secret=os.environ.get("OMNISTACKAI_APP_JWT_SECRET", "local-dev-secret"),
    )


def find_free_port(host: str = "127.0.0.1") -> int:
    """Return a currently-free loopback TCP port (bound to port 0, then released)."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return probe.getsockname()[1]


def allocate_preview_ports(host: str = "127.0.0.1") -> tuple[int, int]:
    """Return two distinct, currently-free loopback ports for a preview's API and web servers.

    Both sockets are held open simultaneously while their OS-assigned ports are read, so the two
    ports are guaranteed distinct and free — a preview never collides with an existing local app
    (e.g. a `task app:run` on 3000/8000) or a prior preview.
    """
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    api_sock = socket.socket(family, socket.SOCK_STREAM)
    web_sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        api_sock.bind((host, 0))
        web_sock.bind((host, 0))
        return api_sock.getsockname()[1], web_sock.getsockname()[1]
    finally:
        api_sock.close()
        web_sock.close()


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
        raise LocalAppRunError(f"step failed: {step.label} (exit {result.returncode})")


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


def _port_available(url: str) -> bool:
    """Return whether a loopback URL's TCP port can be claimed before strict preview startup."""
    parsed = urllib.parse.urlparse(url)
    host, port = parsed.hostname, parsed.port
    if host is None or port is None:
        return False
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            probe.bind((host, port))
        return True
    except OSError:
        return False


def _ensure_background_processes_running(session: LocalAppSession) -> None:
    if any(process.poll() is not None for process in session.processes):
        raise LocalAppRunError("a generated-app background process exited during startup")


def start_app(
    repo_dir: str,
    *,
    plan: RunPlan | None = None,
    log=print,
    health_timeout_seconds: float = 45.0,
    require_ready: bool = True,
) -> LocalAppSession:
    """Start one managed generated-app session and return it only when its targets are ready.

    This is the reusable execution boundary used by both the CLI and Studio preview. Callers own the
    returned session and must call ``stop``. On any setup or readiness failure, already-launched child
    processes are stopped before the error is re-raised.
    """
    root = Path(repo_dir).expanduser().resolve()
    if not root.is_dir():
        raise LocalAppRunError(f"not a directory: {root}")
    active_plan = plan or _plan_from_env(str(root))
    session = LocalAppSession(active_plan)

    def emit(message: str) -> None:
        if log is not None:
            log(message)

    try:
        if require_ready:
            target_urls = []
            if active_plan.backend_kind != "none":
                target_urls.append(active_plan.api_url)
            if active_plan.has_web:
                target_urls.append(active_plan.web_url)
            for url in target_urls:
                if not _port_available(url):
                    raise LocalAppRunError(f"local preview port is already in use: {url}")

        for step in active_plan.steps:
            if step.background:
                emit(f"-> {step.label}")
                session.processes.append(_launch(step))
                continue
            if _should_skip(step):
                emit(f"-  {step.label} (already done, skipping)")
                continue
            emit(f"-> {step.label}")
            _run_sync(step)

        if active_plan.backend_kind != "none":
            emit("Waiting for the API to be healthy ...")
            session.api_ready = _wait_healthy(
                active_plan.api_url + "/healthz", timeout_seconds=health_timeout_seconds
            )
            _ensure_background_processes_running(session)
            if not session.api_ready and require_ready:
                raise LocalAppRunError(f"backend API did not become ready at {active_plan.api_url}")
            emit(
                f"API ready: {active_plan.api_url}"
                if session.api_ready
                else f"API not healthy yet at {active_plan.api_url} (it may still be starting)"
            )

        if active_plan.has_web:
            emit("Waiting for the web app to be ready ...")
            session.web_ready = _wait_healthy(
                active_plan.web_url, timeout_seconds=health_timeout_seconds
            )
            _ensure_background_processes_running(session)
            if not session.web_ready and require_ready:
                raise LocalAppRunError(f"web app did not become ready at {active_plan.web_url}")
            emit(
                f"Web ready: {active_plan.web_url}"
                if session.web_ready
                else f"Web not ready yet at {active_plan.web_url} (it may still be starting)"
            )
    except BaseException:
        session.stop()
        raise
    return session


def start_preview_app(
    repo_dir: str, *, log=None, health_timeout_seconds: float = 45.0, host: str = "127.0.0.1"
) -> LocalAppSession:
    """Start a managed preview on automatically allocated, collision-free API/web ports.

    Distinct free loopback ports are chosen and threaded through the R-419 run plan (and thus the
    generated web app's ``NEXT_PUBLIC_API_URL``), so a Studio preview never fails on, or clobbers, an
    existing local app or a prior preview. Delegates to the strict ``start_app`` boundary (readiness,
    occupied-port rejection, and cleanup on failure).
    """
    root = Path(repo_dir).expanduser().resolve()
    if not root.is_dir():
        raise LocalAppRunError(f"not a directory: {root}")
    api_port, web_port = allocate_preview_ports(host)
    plan = _plan_from_env(str(root), api_port=api_port, web_port=web_port)
    return start_app(
        str(root), plan=plan, log=log, health_timeout_seconds=health_timeout_seconds
    )


def run_app(repo_dir: str) -> None:
    root = Path(repo_dir).expanduser().resolve()
    if not root.is_dir():
        raise LocalAppRunError(f"not a directory: {root}")
    plan = _plan_from_env(str(root))
    print(f"Running generated app at: {root}")
    print(f"  backend: {plan.backend_kind}   web: {'yes' if plan.has_web else 'no'}   db: {plan.db_name}")

    session: LocalAppSession | None = None
    try:
        # Preserve the original CLI's best-effort behavior: it keeps the servers running even when
        # the readiness timeout expires. Studio preview uses the strict default above.
        session = start_app(str(root), plan=plan, require_ready=False)

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
        if session is not None:
            session.stop()


def main() -> None:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        raise SystemExit("usage: app:run -- <path-to-generated-repo>")
    try:
        run_app(sys.argv[1])
    except LocalAppRunError as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()

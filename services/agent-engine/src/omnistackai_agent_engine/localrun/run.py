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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .api_env import link_shared_environment
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
        self.admin_ready = False
        self.mobile_ready = False
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
    repo_dir: str,
    *,
    api_port: int | None = None,
    web_port: int | None = None,
    admin_port: int | None = None,
    mobile_port: int | None = None,
    extra_app_ports: tuple[int, ...] = (),
    public_base: str = "",
    extra_env: Mapping[str, str] | None = None,
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
        admin_port=admin_port if admin_port is not None else int(os.environ.get("OMNISTACKAI_APP_ADMIN_PORT", "3100")),
        mobile_port=mobile_port if mobile_port is not None else int(os.environ.get("OMNISTACKAI_APP_MOBILE_PORT", "8081")),
        extra_app_ports=extra_app_ports,
        public_base=public_base,
        jwt_secret=os.environ.get("OMNISTACKAI_APP_JWT_SECRET", "local-dev-secret"),
        extra_env=extra_env,
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
    api_port, web_port, _admin_port = allocate_preview_ports3(host)
    return api_port, web_port


def allocate_preview_ports3(host: str = "127.0.0.1") -> tuple[int, int, int]:
    """Three distinct free loopback ports: API, web and the admin console (R-542)."""
    api, web, admin, _mobile = allocate_preview_ports4(host)
    return api, web, admin


def allocate_free_ports(count: int, host: str = "127.0.0.1") -> tuple[int, ...]:
    """`count` distinct free loopback ports (R-553).

    All sockets are held open together while their assigned ports are read, so the set is distinct
    and free at that moment. Generalised from the fixed four because an ecosystem has as many web
    surfaces as its plan produced, not a number anyone can hard-code.
    """
    if count <= 0:
        return ()
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    socks = [socket.socket(family, socket.SOCK_STREAM) for _ in range(count)]
    try:
        for sock in socks:
            sock.bind((host, 0))
        return tuple(sock.getsockname()[1] for sock in socks)
    finally:
        for sock in socks:
            sock.close()


def allocate_preview_ports4(host: str = "127.0.0.1") -> tuple[int, int, int, int]:
    """Four distinct free ports: API, web, admin console and the Expo dev server (R-545).

    All sockets are held open together while their OS-assigned ports are read, so every port is
    distinct and free. They are allocated whether or not the project has each app — binding and
    releasing a socket is cheap, and it keeps allocation in one place.
    """
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    socks = [socket.socket(family, socket.SOCK_STREAM) for _ in range(4)]
    try:
        for sock in socks:
            sock.bind((host, 0))
        return tuple(sock.getsockname()[1] for sock in socks)  # type: ignore[return-value]
    finally:
        for sock in socks:
            sock.close()


def _should_skip(step: RunStep) -> bool:
    cwd = Path(step.cwd) if step.cwd else Path.cwd()
    if step.label.startswith("create backend virtualenv") and (cwd / ".venv").is_dir():
        return True
    # R-542: the admin console installs into its own directory, so it needs the same check —
    # without it every preview start reinstalls its dependencies from scratch.
    if step.label.startswith(("install web dependencies", "install admin dependencies")) and (
        cwd / "node_modules" / ".bin" / "next"
    ).exists():
        return True
    # R-545: the Expo app installs into its own directory and has no `next` binary.
    if step.label.startswith("install mobile dependencies") and (
        cwd / "node_modules" / ".bin" / "expo"
    ).exists():
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


def _launch(step: RunStep, log_callback: Callable[[str], None] | None = None) -> subprocess.Popen:
    env = {**os.environ, **dict(step.env)}
    if log_callback is not None:
        import threading
        proc = subprocess.Popen(
            [step.program, *step.args],
            cwd=step.cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def _tee() -> None:
            try:
                if proc.stdout:
                    for line in iter(proc.stdout.readline, ""):
                        if not line:
                            break
                        log_callback(line)
            except Exception:
                pass

        threading.Thread(target=_tee, daemon=True).start()
        return proc
    return subprocess.Popen([step.program, *step.args], cwd=step.cwd, env=env)


#: PC-006: a server that comes up between two checks waits for the next one; at 1 s that was up
#: to a second per surface, paid in turn by the API, the web app and the admin console.
_POLL_SECONDS = 0.25


def _wait_healthy(url: str, timeout_seconds: float = 45.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(_POLL_SECONDS)
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


@dataclass(frozen=True)
class _Probe:
    name: str
    url: str
    #: The session flag it sets, if any.
    attr: str | None
    failure: str
    #: R-545: the mobile app is an extra surface; a slow Expo start must not tear down a working
    #: web and admin preview, so it is reported as not ready instead.
    required: bool = True
    cap: float = float("inf")


def _readiness_probes(plan: RunPlan) -> list[_Probe]:
    probes: list[_Probe] = []
    if plan.backend_kind != "none":
        probes.append(_Probe("API", plan.api_url + "/healthz", "api_ready",
                             f"backend API did not become ready at {plan.api_url}"))
    if plan.has_web:
        # R-542: probe where the app actually serves. Under a base path "/" is a 404, so probing
        # the origin would declare a perfectly healthy app dead.
        web_probe = plan.web_health_url or plan.web_url
        probes.append(_Probe("Web", web_probe, "web_ready", f"web app did not become ready at {web_probe}"))
    if getattr(plan, "has_admin", False):
        admin_probe = plan.admin_health_url or plan.admin_url
        probes.append(_Probe("Admin", admin_probe, "admin_ready",
                             f"admin console did not become ready at {admin_probe}"))
    # R-553: a surface nobody waits for is reported ready before it can answer, and the first
    # thing a user does is click it.
    for app_id, url in getattr(plan, "web_surfaces", ()) or ():
        if app_id in ("web", "admin"):
            continue  # already probed above, with their base paths
        probe = f"{url}{plan.public_base.rstrip('/')}/{app_id}" if plan.multi_app else url
        probes.append(_Probe(app_id, probe, None, f"{app_id} did not become ready at {probe}"))
    if getattr(plan, "has_mobile", False):
        probes.append(_Probe("Mobile (Expo)", plan.mobile_url, "mobile_ready", "", required=False, cap=60.0))
    return probes


def _link_shared_environment(cwd: str | None) -> bool:
    return bool(cwd) and link_shared_environment(cwd)


def start_app(
    repo_dir: str,
    *,
    plan: RunPlan | None = None,
    log=print,
    health_timeout_seconds: float = 45.0,
    require_ready: bool = True,
    on_phase: Callable[[str], None] | None = None,
    log_callback: Callable[[str], None] | None = None,
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

        current_phase = None
        shared_env_dirs: set[str | None] = set()
        for step in active_plan.steps:
            if step.background:
                step_phase = "start"
            elif any(k in step.label.lower() for k in ("database", "migration")):
                step_phase = "migrate"
            else:
                step_phase = "install"

            if step_phase != current_phase:
                current_phase = step_phase
                if on_phase is not None:
                    on_phase(current_phase)

            if step.background:
                emit(f"-> {step.label}")
                session.processes.append(_launch(step, log_callback=log_callback))
                continue
            # PC-006: a generated Python API reuses the shared, already-installed environment for
            # its exact requirements instead of creating and installing its own.
            if step.label.startswith("create backend virtualenv") and _link_shared_environment(step.cwd):
                shared_env_dirs.add(step.cwd)
                emit("-  backend environment (shared, already installed)")
                continue
            if step.label.startswith("install backend dependencies") and step.cwd in shared_env_dirs:
                continue
            if _should_skip(step):
                emit(f"-  {step.label} (already done, skipping)")
                continue
            emit(f"-> {step.label}")
            _run_sync(step)

        if current_phase != "start" and (active_plan.backend_kind != "none" or active_plan.has_web):
            current_phase = "start"
            if on_phase is not None:
                on_phase("start")

        # PC-006: every surface is probed at once. One after another, each `next dev` compiled its
        # first page only when its turn came, and the preview paid for the API, the web app and the
        # admin console in sequence.
        probes = _readiness_probes(active_plan)
        if probes:
            for probe in probes:
                emit(f"Waiting for {probe.name} ...")
            with ThreadPoolExecutor(max_workers=len(probes)) as pool:
                futures = [
                    pool.submit(_wait_healthy, p.url, timeout_seconds=min(health_timeout_seconds, p.cap))
                    for p in probes
                ]
                results = [future.result() for future in futures]
            _ensure_background_processes_running(session)
            for probe, ready in zip(probes, results):
                if probe.attr:
                    setattr(session, probe.attr, ready)
                emit(f"{probe.name} ready: {probe.url}" if ready else f"{probe.name} not ready yet at {probe.url}")
            for probe, ready in zip(probes, results):
                if not ready and probe.required and require_ready:
                    raise LocalAppRunError(probe.failure)

        if on_phase is not None:
            on_phase("ready")
    except BaseException:
        session.stop()
        raise
    return session


def start_preview_app(
    repo_dir: str,
    *,
    log=None,
    health_timeout_seconds: float = 45.0,
    host: str = "127.0.0.1",
    on_phase: Callable[[str], None] | None = None,
    extra_env: Mapping[str, str] | None = None,
    log_callback: Callable[[str], None] | None = None,
    public_base: str = "",
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
    # R-553: an ecosystem has as many web surfaces as its plan produced, so count them before
    # allocating rather than assuming two.
    from .plan import discover_web_apps

    extra_count = max(0, len(discover_web_apps(root)) - 2)  # web and admin already have ports
    ports = allocate_free_ports(4 + extra_count, host)
    api_port, web_port, admin_port, mobile_port = ports[:4]
    plan = _plan_from_env(
        str(root),
        api_port=api_port,
        web_port=web_port,
        admin_port=admin_port,
        mobile_port=mobile_port,
        extra_app_ports=ports[4:],
        public_base=public_base,
        extra_env=extra_env,
    )
    return start_app(
        str(root),
        plan=plan,
        log=log,
        health_timeout_seconds=health_timeout_seconds,
        on_phase=on_phase,
        log_callback=log_callback,
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

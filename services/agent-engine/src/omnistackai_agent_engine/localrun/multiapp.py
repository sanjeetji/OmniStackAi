"""Run a multi-app project (a template copy) locally for the Studio preview (Phase T, T-2 / R-520).

A template project is several apps (web, admin, PWA, API) sharing one API and one database. Its
root ``omnistack.json`` lists the apps. This module turns that into a plan and runs it:

* ``build_multiapp_plan`` is pure. It picks each app's port and public base path
  (``<prefix>/<project>/<app>``), each app's environment, the database steps (fresh per-project
  database, then the API app's ``migrations/*.sql`` and ``seed/*.sql`` in name order) and the
  dependency install.
* ``start_multiapp`` runs it. Every app runs ``pnpm run dev`` in its own process group, so stopping
  the session also stops the servers those scripts spawn. App processes get a minimal environment,
  never the Studio's model keys.

The single-app preview for prompt-built apps (``plan.py`` / ``run.py``) is separate and unchanged.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import signal
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping, Sequence

from .plan import RunStep

MANIFEST_NAME = "omnistack.json"
APP_KINDS = ("web", "admin", "pwa", "api")
WEB_KINDS = ("web", "admin", "pwa")
DEFAULT_PUBLIC_PREFIX = "/preview"

_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")
_DB_SAFE_RE = re.compile(r"[^a-z0-9]+")

# Variables an app process may inherit from the Studio. Everything else (model API keys, cloud
# tokens, the Studio's own configuration) stays out of generated code's reach.
_BASE_ENV_KEYS = (
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "SHELL",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TMPDIR",
    "TERM",
    "PNPM_HOME",
    "COREPACK_HOME",
    "NVM_DIR",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "NODE_EXTRA_CA_CERTS",
    "SSL_CERT_FILE",
)
# Setup steps additionally need to reach Docker (the local Postgres) and the package registry.
_SETUP_ENV_KEYS = ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CONFIG", "DOCKER_CERT_PATH", "DOCKER_TLS_VERIFY")
_SETUP_ENV_PREFIXES = ("npm_config_", "NPM_CONFIG_")


class ProjectManifestError(ValueError):
    """``omnistack.json`` exists but cannot be used to run the project."""


class MultiAppRunError(RuntimeError):
    """The project could not be set up, started or made ready."""


# --- manifest ------------------------------------------------------------------------------------


def _safe_relative(value: object) -> PurePosixPath | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = PurePosixPath(value.strip())
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        return None
    return path


def load_project_manifest(repo_dir: str | os.PathLike[str]) -> dict | None:
    """The project's ``omnistack.json``, or None when the project has none (a prompt-built app)."""

    root = Path(repo_dir)
    path = root / MANIFEST_NAME
    if not path.is_file():
        return None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ProjectManifestError(f"{MANIFEST_NAME} is not valid JSON: {error}") from error
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ProjectManifestError(f"{MANIFEST_NAME} must be an object with schema_version 1")
    apps = manifest.get("apps")
    if not isinstance(apps, list) or not apps:
        raise ProjectManifestError(f"{MANIFEST_NAME} must list at least one app")
    seen: set[str] = set()
    api_count = 0
    for index, app in enumerate(apps):
        if not isinstance(app, dict):
            raise ProjectManifestError(f"apps[{index}] must be an object")
        app_id = app.get("id")
        if not isinstance(app_id, str) or not _ID_RE.match(app_id) or app_id in seen:
            raise ProjectManifestError(f"apps[{index}].id must be a unique short lowercase identifier")
        seen.add(app_id)
        if app.get("kind") not in APP_KINDS:
            raise ProjectManifestError(f"apps[{index}].kind must be one of {', '.join(APP_KINDS)}")
        api_count += app["kind"] == "api"
        rel = _safe_relative(app.get("path"))
        if rel is None or not (root / rel).is_dir():
            raise ProjectManifestError(f"apps[{index}].path must be an existing directory inside the project")
        if not (root / rel / "package.json").is_file():
            raise ProjectManifestError(f"apps[{index}] ({app_id}) needs a package.json with a dev script")
    if api_count > 1:
        raise ProjectManifestError("a project can have at most one api app")
    return manifest


# --- plan ----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AppRun:
    """One app of a multi-app project, ready to launch."""

    id: str
    name: str
    kind: str
    cwd: str
    port: int
    public_path: str  # the path the console serves this app under
    command: tuple[str, ...] = ("pnpm", "run", "dev")
    env: tuple[tuple[str, str], ...] = ()

    @property
    def internal_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def health_url(self) -> str:
        if self.kind == "api":
            return f"{self.internal_url}/health"
        return f"{self.internal_url}{self.public_path}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "port": self.port,
            "path": self.public_path,
            "url": self.internal_url,
        }


@dataclass(frozen=True)
class MultiAppPlan:
    repo_dir: str
    project_id: str
    db_name: str
    apps: tuple[AppRun, ...]
    setup: tuple[RunStep, ...] = ()
    secrets: tuple[str, ...] = field(default=(), repr=False)

    def to_dict(self) -> dict:
        def mask(value: str) -> str:
            for secret in self.secrets:
                if secret:
                    value = value.replace(secret, "***")
            return value

        return {
            "repo_dir": self.repo_dir,
            "project_id": self.project_id,
            "db_name": self.db_name,
            "apps": [app.to_dict() for app in self.apps],
            "setup": [step.to_dict(mask=self.secrets) for step in self.setup],
            "app_env": {app.id: {k: mask(v) for k, v in app.env} for app in self.apps},
        }


def project_db_name(project_id: str) -> str:
    cleaned = _DB_SAFE_RE.sub("", project_id.lower())[:16] or "project"
    return f"tpl_{cleaned}"


def build_multiapp_plan(
    repo_dir: str | os.PathLike[str],
    manifest: Mapping,
    *,
    project_id: str,
    ports: Sequence[int],
    public_prefix: str = DEFAULT_PUBLIC_PREFIX,
    db_container: str = "omnistackai-local-postgres-1",
    db_user: str = "omnistackai",
    db_password: str = "",
    db_host: str = "127.0.0.1",
    db_port: int = 5432,
    maintenance_db: str = "omnistackai",
    jwt_secret: str = "local-preview-secret",
    extra_env: Mapping[str, str] | None = None,
) -> MultiAppPlan:
    """Compose how to set up and run every app of a multi-app project. Pure: nothing is executed."""

    root = Path(repo_dir).resolve()
    apps_spec = list(manifest["apps"])
    if len(ports) < len(apps_spec):
        raise ValueError(f"need {len(apps_spec)} ports, got {len(ports)}")
    prefix = "/" + public_prefix.strip("/") if public_prefix.strip("/") else ""
    project_base = f"{prefix}/{project_id}"
    database = project_db_name(project_id)
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{database}"
    extra = tuple((k, str(v)) for k, v in sorted((extra_env or {}).items()))

    api_spec = next((a for a in apps_spec if a["kind"] == "api"), None)
    api_port = ports[apps_spec.index(api_spec)] if api_spec else None
    api_public = f"{project_base}/{api_spec['id']}" if api_spec else ""

    apps: list[AppRun] = []
    for spec, port in zip(apps_spec, ports):
        cwd = str(root / spec["path"])
        public_path = f"{project_base}/{spec['id']}"
        env: list[tuple[str, str]] = [("PORT", str(port)), ("OMNISTACK_PREVIEW", "1")]
        if spec["kind"] == "api":
            env += [
                ("DATABASE_URL", database_url),
                ("JWT_SECRET", jwt_secret),
                ("PUBLIC_BASE_PATH", public_path),
            ]
        else:
            env += [("BASE_PATH", public_path), ("NEXT_PUBLIC_BASE_PATH", public_path)]
            if api_port is not None:
                env += [
                    ("API_URL", f"http://127.0.0.1:{api_port}"),
                    ("NEXT_PUBLIC_API_URL", api_public),
                ]
        apps.append(
            AppRun(
                id=spec["id"],
                name=str(spec.get("name") or spec["id"]),
                kind=spec["kind"],
                cwd=cwd,
                port=port,
                public_path=public_path,
                env=tuple(env) + extra,
            )
        )

    setup: list[RunStep] = []
    pg_env = (("PGPASSWORD", db_password),)
    psql = ("exec", "-i", db_container, "psql", "-U", db_user)
    if api_spec is not None:
        setup.append(
            RunStep(
                label=f"drop database {database} (if it exists)",
                program="docker",
                args=psql + ("-d", maintenance_db, "-c", f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE);'),
                env=pg_env,
                tolerate_failure=True,
            )
        )
        setup.append(
            RunStep(
                label=f"create database {database}",
                program="docker",
                args=psql + ("-d", maintenance_db, "-c", f'CREATE DATABASE "{database}";'),
                env=pg_env,
            )
        )
        api_dir = root / api_spec["path"]
        for folder, verb in (("migrations", "apply migration"), ("seed", "load seed data")):
            for sql in sorted((api_dir / folder).glob("*.sql")) if (api_dir / folder).is_dir() else []:
                setup.append(
                    RunStep(
                        label=f"{verb} {folder}/{sql.name}",
                        program="docker",
                        args=psql + ("-d", database, "-v", "ON_ERROR_STOP=1"),
                        stdin_file=str(sql),
                        env=pg_env,
                    )
                )

    install = ("install", "--ignore-scripts", "--prefer-offline")
    if (root / "pnpm-workspace.yaml").is_file():
        setup.append(RunStep(label="install dependencies (pnpm workspace)", program="pnpm", args=install, cwd=str(root)))
    else:
        for app in apps:
            setup.append(
                RunStep(
                    label=f"install dependencies for {app.id}",
                    program="pnpm",
                    args=install + ("--ignore-workspace",),
                    cwd=app.cwd,
                )
            )

    return MultiAppPlan(
        repo_dir=str(root),
        project_id=project_id,
        db_name=database,
        apps=tuple(apps),
        setup=tuple(setup),
        secrets=tuple(s for s in (db_password, jwt_secret) if s),
    )


def allocate_ports(count: int, host: str = "127.0.0.1") -> list[int]:
    """``count`` distinct, currently free loopback ports (all held open while they are read)."""

    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    sockets = [socket.socket(family, socket.SOCK_STREAM) for _ in range(count)]
    try:
        for sock in sockets:
            sock.bind((host, 0))
        return [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()


def plan_from_env(
    repo_dir: str | os.PathLike[str],
    manifest: Mapping,
    *,
    project_id: str,
    extra_env: Mapping[str, str] | None = None,
) -> MultiAppPlan:
    """A plan on free ports, using the platform's local Postgres settings and a fresh JWT secret."""

    return build_multiapp_plan(
        repo_dir,
        manifest,
        project_id=project_id,
        ports=allocate_ports(len(manifest["apps"])),
        public_prefix=os.environ.get("OMNISTACKAI_PREVIEW_PUBLIC_PREFIX", DEFAULT_PUBLIC_PREFIX),
        db_container=os.environ.get("OMNISTACKAI_POSTGRES_CONTAINER", "omnistackai-local-postgres-1"),
        db_user=os.environ.get("OMNISTACKAI_POSTGRES_USER", "omnistackai"),
        db_password=os.environ.get("OMNISTACKAI_POSTGRES_PASSWORD", ""),
        db_host=os.environ.get("OMNISTACKAI_POSTGRES_HOST", "127.0.0.1"),
        db_port=int(os.environ.get("OMNISTACKAI_POSTGRES_PORT", "5432")),
        maintenance_db=os.environ.get("OMNISTACKAI_POSTGRES_DB", "omnistackai"),
        jwt_secret=secrets.token_urlsafe(32),
        extra_env=extra_env,
    )


# --- execution -----------------------------------------------------------------------------------


def base_environment(*, for_setup: bool = False, source: Mapping[str, str] | None = None) -> dict[str, str]:
    """The minimal environment app processes (and, with ``for_setup``, setup steps) inherit."""

    source = os.environ if source is None else source
    env = {key: source[key] for key in _BASE_ENV_KEYS if key in source}
    if for_setup:
        env.update({key: source[key] for key in _SETUP_ENV_KEYS if key in source})
        env.update({k: v for k, v in source.items() if k.startswith(_SETUP_ENV_PREFIXES)})
    return env


class MultiAppSession:
    """The running processes of one multi-app project; each app is its own process group."""

    def __init__(self, plan: MultiAppPlan) -> None:
        self.plan = plan
        self.processes: dict[str, subprocess.Popen] = {}
        self.ready: dict[str, bool] = {app.id: False for app in plan.apps}
        self._stopped = False
        self._lock = threading.Lock()

    def is_alive(self) -> bool:
        if self._stopped or not self.processes:
            return False
        return all(process.poll() is None for process in self.processes.values())

    def exited_apps(self) -> list[str]:
        return [app_id for app_id, process in self.processes.items() if process.poll() is not None]

    def stop(self) -> None:
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
        for process in self.processes.values():
            _signal_group(process, signal.SIGTERM)
        deadline = time.time() + 8
        for process in self.processes.values():
            try:
                process.wait(timeout=max(0.1, deadline - time.time()))
            except subprocess.TimeoutExpired:
                pass
        for process in self.processes.values():
            # Kill the whole group even when the leader already exited: `pnpm run dev` can exit
            # while the server it spawned keeps running.
            _signal_group(process, signal.SIGKILL)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
            if process.stdout is not None:
                try:
                    process.stdout.close()
                except OSError:
                    pass


def _signal_group(process: subprocess.Popen, sig: signal.Signals) -> None:
    try:
        os.killpg(process.pid, sig)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _run_setup_step(step: RunStep) -> None:
    env = {**base_environment(for_setup=True), **dict(step.env)}
    stdin = open(step.stdin_file, "rb") if step.stdin_file else None
    try:
        result = subprocess.run(
            [step.program, *step.args],
            cwd=step.cwd,
            env=env,
            stdin=stdin,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        if stdin is not None:
            stdin.close()
    if result.returncode != 0 and not step.tolerate_failure:
        detail = (result.stderr or result.stdout or "").strip().splitlines()[-3:]
        raise MultiAppRunError(f"{step.label} failed (exit {result.returncode}): {' '.join(detail)[:300]}")


def _launch(app: AppRun, log_callback: Callable[[str], None] | None) -> subprocess.Popen:
    env = {**base_environment(), **dict(app.env)}
    process = subprocess.Popen(
        list(app.command),
        cwd=app.cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        start_new_session=True,
    )

    def _tee() -> None:
        try:
            assert process.stdout is not None
            for line in iter(process.stdout.readline, ""):
                if log_callback is not None:
                    log_callback(f"[{app.id}] {line}")
        except Exception:
            pass

    threading.Thread(target=_tee, daemon=True).start()
    return process


def _responds(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            return response.status < 500
    except urllib.error.HTTPError as error:
        return error.code < 500
    except (urllib.error.URLError, ConnectionError, OSError):
        return False


def _api_healthy(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            return response.status == 200
    except (urllib.error.URLError, ConnectionError, OSError):
        return False


def start_multiapp(
    plan: MultiAppPlan,
    *,
    on_phase: Callable[[str], None] | None = None,
    on_app_ready: Callable[[str], None] | None = None,
    log_callback: Callable[[str], None] | None = None,
    health_timeout_seconds: float = 240.0,
    cancelled: Callable[[], bool] | None = None,
    run_step: Callable[[RunStep], None] = _run_setup_step,
) -> MultiAppSession:
    """Set up and start every app; return only when all are ready. Cleans up on any failure."""

    session = MultiAppSession(plan)

    def check_cancelled() -> None:
        if cancelled is not None and cancelled():
            raise MultiAppRunError("the preview was stopped while it was starting")

    def phase(name: str) -> None:
        if on_phase is not None:
            on_phase(name)

    try:
        current = None
        for step in plan.setup:
            check_cancelled()
            step_phase = "install" if step.program == "pnpm" else "migrate"
            if step_phase != current:
                current = step_phase
                phase(step_phase)
            if log_callback is not None:
                log_callback(f"-> {step.label}\n")
            run_step(step)

        check_cancelled()
        phase("start")
        for app in plan.apps:
            session.processes[app.id] = _launch(app, log_callback)

        deadline = time.time() + health_timeout_seconds
        pending = list(plan.apps)
        while pending:
            check_cancelled()
            exited = session.exited_apps()
            if exited:
                raise MultiAppRunError(f"app {exited[0]} exited during startup (see the preview logs)")
            for app in list(pending):
                healthy = _api_healthy(app.health_url) if app.kind == "api" else _responds(app.health_url)
                if healthy:
                    session.ready[app.id] = True
                    pending.remove(app)
                    if on_app_ready is not None:
                        on_app_ready(app.id)
            if pending:
                if time.time() > deadline:
                    names = ", ".join(app.id for app in pending)
                    raise MultiAppRunError(f"app(s) did not become ready in time: {names}")
                time.sleep(0.5)
        phase("ready")
    except BaseException:
        session.stop()
        raise
    return session

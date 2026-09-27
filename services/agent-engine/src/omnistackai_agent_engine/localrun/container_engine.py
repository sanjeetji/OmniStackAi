"""PC-007: preview a generated app with nothing but Docker on the machine.

The local engine needs Node, pnpm and Python installed — fine on a developer's laptop, and the
reason a hosted service cannot hand every user a machine. This engine runs the same run plan
(R-419) inside one container built from ``omnistackai/preview-runtime`` (Node 22 + pnpm, Python,
Go), so the plan, ports, base paths and environment are exactly the ones the local engine uses:

* the project is mounted at its own path, so every step's working directory is unchanged;
* each port is published on 127.0.0.1 under the same number, so the URLs the plan computed — and
  the console's preview proxy — work as they are;
* the database steps run from the host (they only need ``docker exec`` into Postgres); inside, the
  app reaches Postgres over its container network by name;
* dependencies live in Docker volumes keyed by their manifest — one pnpm store for every app, a
  ``node_modules`` per dependency set, a virtualenv per requirements file — so the second preview of
  a stack installs nothing, and nothing Linux-built lands in the project on the host;
* under gVisor (``runsc``) when Docker has that runtime, which is what isolates one user's code
  from another's on a shared host (R-489).

The Expo dev server is not started here: a phone must reach it on the LAN, which a container on a
hosted service cannot offer. The mobile app still builds and is type-checked; it previews locally
or through the store builds (R-574).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import shlex
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Callable, Mapping

from . import sandbox
from .plan import RunPlan, RunStep
from .run import (
    LocalAppRunError,
    LocalAppSession,
    _plan_from_env,
    _port_available,
    _run_sync,
    allocate_free_ports,
    await_ready,
)

IMAGE = "omnistackai/preview-runtime:2"
#: The API's virtualenv, at a fixed path: a virtualenv's scripts carry the path it was made at, so
#: one made under another project's folder does not run under this one (seen live).
VENV = "/omni-venv"
DOCKERFILE = """\
FROM golang:1.23-bookworm AS go
FROM node:22-bookworm-slim
RUN apt-get update \\
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip ca-certificates git \\
 && rm -rf /var/lib/apt/lists/*
COPY --from=go /usr/local/go /usr/local/go
ENV PATH=/usr/local/go/bin:$PATH GOPATH=/go GOFLAGS=-modcacherw
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate
# pnpm reads npm_config_store_dir, not PNPM_STORE_DIR: without it the store lands inside the
# project on the host, and every project path looks like a new store (seen live).
ENV npm_config_store_dir=/pnpm-store npm_config_package_import_method=copy npm_config_update_notifier=false \
    NEXT_TELEMETRY_DISABLED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /
"""
_LABEL = "omnistackai.preview"


def _docker(*args: str, input_text: str | None = None, timeout: float = 120.0) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], input=input_text, capture_output=True, text=True,
                          timeout=timeout, check=False)


def ensure_image(log: Callable[[str], None] | None = None) -> None:
    """Build the runtime image once; later previews reuse it."""
    if _docker("image", "inspect", IMAGE).returncode == 0:
        return
    if log is not None:
        log(f"-> building the preview runtime image {IMAGE} (first time only)")
    built = _docker("build", "-t", IMAGE, "-", input_text=DOCKERFILE, timeout=1200.0)
    if built.returncode != 0:
        raise LocalAppRunError(f"could not build the preview runtime image: {built.stderr.strip()[-400:]}")


def _gvisor_runtime() -> str | None:
    configured = os.environ.get("OMNISTACKAI_PREVIEW_RUNTIME", "").strip()
    if configured:
        return configured
    info = _docker("info", "--format", "{{json .Runtimes}}")
    try:
        return "runsc" if info.returncode == 0 and "runsc" in json.loads(info.stdout or "{}") else None
    except ValueError:
        return None


def _db_network_and_host(plan: RunPlan) -> tuple[str | None, str]:
    """The Postgres container's network, and the name the app reaches it by on that network."""
    del plan
    container = os.environ.get("OMNISTACKAI_POSTGRES_CONTAINER", "omnistackai-local-postgres-1")
    shown = _docker("inspect", "-f", "{{json .NetworkSettings.Networks}}", container)
    try:
        networks = json.loads(shown.stdout) if shown.returncode == 0 else {}
    except ValueError:
        networks = {}
    return (next(iter(networks), None), container)


def _is_db_step(step: RunStep) -> bool:
    return any(word in step.label.lower() for word in ("database", "migration"))


def _is_mobile_step(step: RunStep) -> bool:
    return "expo" in step.label.lower() or (
        step.cwd is not None and (Path(step.cwd) / "app.json").is_file() and not (Path(step.cwd) / "next.config.mjs").exists()
    )


def _inside(value: str, db_from: str, db_to: str) -> str:
    return value.replace(db_from, db_to)


def container_script(plan: RunPlan, *, db_from: str, db_to: str) -> str:
    """The plan's install and start steps as one shell script run inside the container."""
    lines = ["#!/usr/bin/env bash", "set -e", "pids=()"]
    for step in plan.steps:
        if _is_db_step(step) or _is_mobile_step(step):
            continue
        cwd = shlex.quote(step.cwd or "/")
        args = list(step.args)
        program = step.program
        if program.startswith(".venv/bin/"):
            program = f"{VENV}/bin/{program.removeprefix('.venv/bin/')}"
        if step.program.endswith("uvicorn"):
            # A server bound to the container's loopback cannot be reached through a published port.
            args = ["0.0.0.0" if a == "127.0.0.1" else a for a in args]
        env = " ".join(f"{k}={shlex.quote(_inside(v, db_from, db_to))}" for k, v in step.env)
        command = " ".join(shlex.quote(x) for x in (program, *args))
        label = step.label.lower()
        if label.startswith("create backend virtualenv"):
            lines.append(f"[ -x {VENV}/bin/python ] || python3 -m venv {VENV}")
        elif label.startswith("install backend dependencies"):
            lines.append(f"cd {cwd} && [ -x {VENV}/bin/uvicorn ] || {command}")
        elif step.background:
            lines.append(f"echo '-> {step.label}'")
            lines.append(f"(cd {cwd} && exec env {env} {command}) & pids+=($!)")
        else:
            lines.append(f"echo '-> {step.label}'")
            lines.append(f"cd {cwd} && env {env} {command}" + (" || true" if step.tolerate_failure else ""))
    # One server exiting ends the container, and the session notices (like a local child exiting).
    lines += ['wait -n "${pids[@]}"', "exit 1"]
    return "\n".join(lines) + "\n"


def _volume(kind: str, key_source: Path) -> str:
    """A volume per dependency set. For a package.json only the dependencies count: the file also
    carries the app's own name, and keying on that made every new project a cold install (45 s
    instead of ~10 s, seen live through the console)."""
    try:
        raw = key_source.read_bytes()
        if key_source.name == "package.json":
            manifest = json.loads(raw)
            raw = json.dumps({k: manifest.get(k) for k in ("dependencies", "devDependencies")},
                             sort_keys=True).encode()
        digest = hashlib.sha256(raw).hexdigest()[:12]
    except (OSError, ValueError):
        digest = "none"
    return f"omnistackai-preview-{kind}-{digest}"


def _mounts(plan: RunPlan, script_dir: str) -> list[str]:
    root = Path(plan.repo_dir)
    args = ["-v", f"{root}:{root}", "-v", f"{script_dir}:/omni-run:ro",
            "-v", "omnistackai-preview-pnpm-store:/pnpm-store",
            "-v", "omnistackai-preview-go-cache:/go"]
    for app in sorted((root / "apps").glob("*/package.json")):
        app_dir = app.parent
        if (app_dir / "app.json").is_file() and not (app_dir / "next.config.mjs").exists():
            continue  # the Expo app does not run here
        _drop_host_link(app_dir / "node_modules")
        args += ["-v", f"{_volume('node-modules', app)}:{app_dir / 'node_modules'}",
                 # Next's build cache is per container: Linux artifacts must not land on the host.
                 "-v", str(app_dir / ".next")]
    requirements = root / "services" / "api" / "requirements.txt"
    if requirements.is_file():
        args += ["-v", f"{_volume('venv', requirements)}:{VENV}"]
    return args


def _drop_host_link(path: Path) -> None:
    # The local engine links shared caches in (PC-006, R-560); a link to a host path means nothing
    # inside the container, and a volume cannot be mounted over it. The caches themselves stay.
    if path.is_symlink():
        path.unlink()


class ContainerAppSession(LocalAppSession):
    """A preview running in one container. Stopping it removes the container and its build cache."""

    def __init__(self, plan: RunPlan, container: str, script_dir: str) -> None:
        super().__init__(plan)
        self.engine = "container"
        self.container = container
        self._script_dir = script_dir
        #: The inbound gateway of an isolated (multi-tenant) preview, if any.
        self.gateway: str | None = None

    def stop(self) -> None:
        if self._stopped:
            return
        super().stop()
        _docker("rm", "-f", "-v", self.container, timeout=60.0)
        if self.gateway:
            _docker("rm", "-f", self.gateway, timeout=60.0)
        try:
            for child in Path(self._script_dir).iterdir():
                child.unlink()
            Path(self._script_dir).rmdir()
        except OSError:
            pass


def start_container_preview(
    repo_dir: str,
    *,
    log=None,
    health_timeout_seconds: float = 180.0,
    host: str = "127.0.0.1",
    on_phase: Callable[[str], None] | None = None,
    extra_env: Mapping[str, str] | None = None,
    log_callback: Callable[[str], None] | None = None,
    public_base: str = "",
) -> LocalAppSession:
    """Start the generated app at ``repo_dir`` in a container and return it once it answers."""
    from .plan import discover_web_apps

    def emit(message: str) -> None:
        if log is not None:
            log(message)

    root = Path(repo_dir).expanduser().resolve()
    extra_count = max(0, len(discover_web_apps(root)) - 2)
    ports = allocate_free_ports(4 + extra_count, host)
    api_port, web_port, admin_port, mobile_port = ports[:4]
    # PC-009: multi-tenant previews use their own database server and a network with no way out.
    isolated = sandbox.multi_tenant()
    preview_db = sandbox.prepare() if isolated else None
    plan = _plan_from_env(str(root), api_port=api_port, web_port=web_port, admin_port=admin_port,
                          mobile_port=mobile_port, extra_app_ports=ports[4:], public_base=public_base,
                          extra_env=extra_env, db=preview_db)

    ensure_image(emit)
    if isolated:
        network = sandbox.NETWORK
        db_from = db_to = ""  # the plan already names the preview database server
    else:
        network, db_name_host = _db_network_and_host(plan)
        db_from = (f"@{os.environ.get('OMNISTACKAI_POSTGRES_HOST', '127.0.0.1')}:"
                   f"{os.environ.get('OMNISTACKAI_POSTGRES_PORT', '5432')}/")
        db_to = f"@{db_name_host}:5432/"

    # Under the home folder: Docker Desktop, Colima and Linux hosts all share it with the daemon;
    # the system temp folder is not shared on a Mac.
    run_root = Path.home() / ".omnistackai" / "preview-run"
    run_root.mkdir(parents=True, exist_ok=True)
    script_dir = tempfile.mkdtemp(prefix="run-", dir=run_root)
    Path(script_dir, "run.sh").write_text(container_script(plan, db_from=db_from, db_to=db_to), encoding="utf-8")
    container = f"omnistackai-preview-{plan.app_slug}-{uuid.uuid4().hex[:8]}"
    session = ContainerAppSession(plan, container, script_dir)
    try:
        if on_phase is not None:
            on_phase("migrate")
        for step in plan.steps:
            if _is_db_step(step):
                emit(f"-> {step.label}")
                _run_sync(step)

        if on_phase is not None:
            on_phase("install")
        published = [api_port, web_port, admin_port, *ports[4:]]
        for port in published:
            if not _port_available(f"http://{host}:{port}"):
                raise LocalAppRunError(f"local preview port is already in use: {port}")
        run = ["run", "-d", "--name", container, "--label", f"{_LABEL}={plan.app_slug}", "--init"]
        if network:
            run += ["--network", network]
        runtime = _gvisor_runtime()
        if runtime:
            run += ["--runtime", runtime]
        if isolated:
            run += sandbox.limits()
            for key, value in sandbox.proxy_env().items():
                run += ["-e", f"{key}={value}"]
        else:
            for port in published:
                run += ["-p", f"{host}:{port}:{port}"]
        run += _mounts(plan, script_dir)
        run += [IMAGE, "bash", "/omni-run/run.sh"]
        started = _docker(*run, timeout=120.0)
        if started.returncode != 0:
            raise LocalAppRunError(f"the preview container did not start: {started.stderr.strip()[-400:]}")
        emit(f"-> container {container}" + (f" (runtime {runtime})" if runtime else "")
             + (" on the isolated preview network" if isolated else ""))
        if isolated:
            session.gateway = sandbox.start_gateway(container, published, host)

        # Following the container's output is the session's child process: it ends when the
        # container does, which is how a crashed app is noticed, exactly as with a local server.
        follow = subprocess.Popen(["docker", "logs", "-f", container], stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, bufsize=1)
        session.processes.append(follow)
        if log_callback is not None:
            import threading

            def _tee() -> None:
                for line in iter(follow.stdout.readline, ""):
                    log_callback(line)

            threading.Thread(target=_tee, daemon=True).start()

        if on_phase is not None:
            on_phase("start")
        # The Expo app is not started here (see the module docstring), so it is not waited for.
        await_ready(session, dataclasses.replace(plan, has_mobile=False), health_timeout_seconds, True, emit)
        if on_phase is not None:
            on_phase("ready")
    except BaseException:
        # The app's own last words, before the container (and they) are removed.
        tail = _docker("logs", "--tail", "40", container, timeout=30.0)
        for line in (tail.stdout + tail.stderr).splitlines()[-40:]:
            emit(f"   | {line}")
            if log_callback is not None:
                log_callback(line + "\n")
        session.stop()
        raise
    return session

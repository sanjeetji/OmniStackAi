"""PC-009: where multi-tenant previews run, and what they can reach.

``OMNISTACKAI_TENANCY=multi`` turns a single operator's Studio into one that can serve many users on
one host. Every preview then runs in the container engine (PC-007) — never on the host — and:

* on ``omnistackai-previews``, an *internal* Docker network: no route to the internet, the host,
  the control plane or the platform's database. Its only neighbours are other previews' published
  nothing (each preview talks to its own ports) plus two shared services below;
* with its own database on ``omnistackai-preview-postgres``, a PostgreSQL server that holds preview
  data only; each project still gets its own database and unprivileged role (plan.py);
* with outbound traffic only through ``omnistackai-egress`` (``egress_proxy.py``): allowlisted
  hosts, ports 80/443, public addresses only;
* under limits: memory, CPU, process count, no Linux capabilities, no privilege escalation, and
  gVisor (``runsc``) when Docker has it.

Everything is created on demand and reused; nothing here needs a cloud account.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import subprocess
import tempfile
from pathlib import Path

TENANCY_ENV = "OMNISTACKAI_TENANCY"
NETWORK = "omnistackai-previews"
DB_CONTAINER = "omnistackai-preview-postgres"
EGRESS_CONTAINER = "omnistackai-egress"
_EGRESS_SOURCE = Path(__file__).with_name("egress_proxy.py")
#: Tagged by the proxy's own source, so a change to it can never keep running an old image.
EGRESS_IMAGE = "omnistackai/egress-proxy:" + hashlib.sha256(_EGRESS_SOURCE.read_bytes()).hexdigest()[:12]
EGRESS_PORT = 3128


def multi_tenant() -> bool:
    return os.environ.get(TENANCY_ENV, "").strip().lower() in ("multi", "hosted", "multi-tenant")


def limits() -> list[str]:
    """docker run flags that bound one preview (overridable per host)."""
    env = os.environ
    return [
        "--memory", env.get("OMNISTACKAI_PREVIEW_MEMORY", "2g"),
        "--cpus", env.get("OMNISTACKAI_PREVIEW_CPUS", "2"),
        "--pids-limit", env.get("OMNISTACKAI_PREVIEW_PIDS", "1024"),
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
    ]


def proxy_env() -> dict[str, str]:
    proxy = f"http://{EGRESS_CONTAINER}:{EGRESS_PORT}"
    return {"HTTP_PROXY": proxy, "HTTPS_PROXY": proxy, "http_proxy": proxy, "https_proxy": proxy,
            "NO_PROXY": f"localhost,127.0.0.1,{DB_CONTAINER}", "no_proxy": f"localhost,127.0.0.1,{DB_CONTAINER}",
            "npm_config_proxy": proxy, "npm_config_https_proxy": proxy}


def _docker(*args: str, input_text: str | None = None, timeout: float = 300.0) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], input=input_text, capture_output=True, text=True, timeout=timeout,
                          check=False)


def _running(name: str) -> bool:
    shown = _docker("inspect", "-f", "{{.State.Running}}", name, timeout=30.0)
    return shown.returncode == 0 and shown.stdout.strip() == "true"


def _secret_file() -> Path:
    return Path.home() / ".omnistackai" / "preview-db-password"


def _db_password() -> str:
    path = _secret_file()
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(secrets.token_urlsafe(32))
    return path.read_text().strip()


def ensure_network() -> None:
    if _docker("network", "inspect", NETWORK, timeout=30.0).returncode != 0:
        made = _docker("network", "create", "--internal", "--label", "omnistackai.role=previews", NETWORK)
        if made.returncode != 0:
            raise RuntimeError(f"could not create the preview network: {made.stderr.strip()}")


def ensure_database() -> dict[str, str]:
    """The preview-only PostgreSQL server; returns what the run plan needs to use it."""
    password = _db_password()
    if not _running(DB_CONTAINER):
        _docker("rm", "-f", DB_CONTAINER, timeout=60.0)
        started = _docker("run", "-d", "--name", DB_CONTAINER, "--restart", "unless-stopped",
                          "--network", NETWORK, "-e", "POSTGRES_USER=previews", "-e", f"POSTGRES_PASSWORD={password}",
                          "-e", "POSTGRES_DB=previews", "-v", "omnistackai-preview-pgdata:/var/lib/postgresql/data",
                          "--label", "omnistackai.role=previews", "postgres:16-alpine")
        if started.returncode != 0:
            raise RuntimeError(f"could not start the preview database: {started.stderr.strip()}")
        for _ in range(60):
            if _docker("exec", DB_CONTAINER, "pg_isready", "-U", "previews", timeout=30.0).returncode == 0:
                break
            subprocess.run(["sleep", "1"], check=False)
    return {"container": DB_CONTAINER, "user": "previews", "password": password, "host": DB_CONTAINER,
            "port": "5432", "maintenance_db": "previews"}


def ensure_egress() -> None:
    """The allowlist proxy: on the preview network, and on the default bridge for the way out."""
    ensure_egress_image()
    image = _docker("inspect", "-f", "{{.Config.Image}}", EGRESS_CONTAINER, timeout=30.0).stdout.strip()
    if _running(EGRESS_CONTAINER) and image == EGRESS_IMAGE:
        return
    _docker("rm", "-f", EGRESS_CONTAINER, timeout=60.0)
    started = _docker("run", "-d", "--name", EGRESS_CONTAINER, "--restart", "unless-stopped",
                      "--network", NETWORK, "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                      "-e", f"OMNISTACKAI_EGRESS_ALLOW={os.environ.get('OMNISTACKAI_EGRESS_ALLOW', '')}",
                      "--label", "omnistackai.role=previews", EGRESS_IMAGE)
    if started.returncode != 0:
        raise RuntimeError(f"could not start the egress proxy: {started.stderr.strip()}")
    # The second network is the proxy's way out; previews never join it.
    _docker("network", "connect", "bridge", EGRESS_CONTAINER, timeout=60.0)


def ensure_egress_image() -> None:
    """One small image serves both the egress proxy and each preview's inbound gateway."""
    if _docker("image", "inspect", EGRESS_IMAGE, timeout=30.0).returncode != 0:
        source = _EGRESS_SOURCE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "egress_proxy.py").write_text(source, encoding="utf-8")
            Path(tmp, "Dockerfile").write_text(
                "FROM python:3.12-alpine\nCOPY egress_proxy.py /egress_proxy.py\n"
                f"USER nobody\nEXPOSE {EGRESS_PORT}\nCMD [\"python\", \"/egress_proxy.py\", \"{EGRESS_PORT}\"]\n",
                encoding="utf-8")
            built = _docker("build", "-t", EGRESS_IMAGE, tmp, timeout=600.0)
            if built.returncode != 0:
                raise RuntimeError(f"could not build the egress proxy: {built.stderr.strip()[-300:]}")


def start_gateway(container: str, ports: list[int], host: str = "127.0.0.1") -> str:
    """Publish a preview's ports on the host. Inbound only: the gateway relays to the preview over
    the private network, and the preview gains no way out (Docker cannot publish ports of a
    container that is only on an internal network)."""
    name = f"{container}-gw"
    _docker("rm", "-f", name, timeout=60.0)
    args = ["run", "-d", "--name", name, "--network", "bridge", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--label", "omnistackai.role=previews"]
    for port in ports:
        args += ["-p", f"{host}:{port}:{port}"]
    args += [EGRESS_IMAGE, "python", "/egress_proxy.py", "forward", *[f"{p}:{container}:{p}" for p in ports]]
    started = _docker(*args, timeout=120.0)
    if started.returncode != 0:
        raise RuntimeError(f"could not start the preview gateway: {started.stderr.strip()}")
    _docker("network", "connect", NETWORK, name, timeout=60.0)
    return name


def prepare() -> dict[str, str]:
    """Network, preview database and egress proxy, ready for a preview. Returns the database."""
    ensure_network()
    database = ensure_database()
    ensure_egress()
    return database

"""PC-008: publish the whole generated app — database, API, web app, admin console — to a live URL.

One call does it all, in order, and records each step so the Studio can show it:

  bundle    write the production files into the project (`bundle.py`) and commit them
  build     build every image in production mode, tagged with this release's number
  database  start the app's own PostgreSQL (a volume keeps its data across releases)
  migrate   apply each migration file the database has not seen, each in one transaction
  start     start the release
  check     sign up, sign in and read the account back through the live URL, then remove the
            check account; open every surface
  live      record the release; keep the last three for rollback

If the check fails, the previous release is started again and the failure is reported with the
step and the reason. Nothing is lost between releases: the database volume and the secrets stay.

Where it runs (`Target`, from the environment — keys last, PC-070):

* nothing set — this machine's Docker, the app on its own local port (the stand-in);
* ``OMNISTACKAI_PUBLISH_DOCKER_HOST=ssh://user@server`` — the same stack on that server;
* ``OMNISTACKAI_PUBLISH_DOMAIN=example.com`` — each app at ``<app>.example.com`` with HTTPS, behind
  one shared edge proxy per host that routes by name and obtains the certificates.

Secrets (database password, signing secret, the project's own keys) are generated or copied into
files readable only by this user, outside the project, and never logged or returned.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets as token_source
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from .bundle import Layout, base_path, migrations, read_layout, write_bundle

STATE_DIR_ENV = "OMNISTACKAI_PUBLISH_DIR"
#: The development seed's hash for "changeme" (schema_sql._ADMIN_SEED_HASH), recognised to replace it.
from ..codegen.schema_sql import _ADMIN_SEED_HASH as _SEED_HASH  # noqa: E402
KEEP_RELEASES = 3
EDGE = "omnistackai-edge"
_CHECK_EMAIL = "publish-check@omnistackai.invalid"
_SEED_ADMIN = "admin@example.local"


@dataclass(frozen=True)
class Target:
    docker_host: str | None = None
    domain: str | None = None
    edge_bind: str = "0.0.0.0"
    edge_http: int = 80
    edge_https: int = 443

    @property
    def label(self) -> str:
        where = self.docker_host or "this machine"
        return f"{where}, {'https://<app>.' + self.domain if self.domain else 'a local port'}"


def target_from_env() -> Target:
    env = os.environ
    return Target(
        docker_host=env.get("OMNISTACKAI_PUBLISH_DOCKER_HOST", "").strip() or None,
        domain=env.get("OMNISTACKAI_PUBLISH_DOMAIN", "").strip().strip(".") or None,
        edge_bind=env.get("OMNISTACKAI_PUBLISH_EDGE_BIND", "0.0.0.0").strip() or "0.0.0.0",
        edge_http=int(env.get("OMNISTACKAI_PUBLISH_EDGE_HTTP_PORT", "80")),
        edge_https=int(env.get("OMNISTACKAI_PUBLISH_EDGE_HTTPS_PORT", "443")),
    )


class PublishError(RuntimeError):
    def __init__(self, step: str, reason: str) -> None:
        super().__init__(f"{step}: {reason}")
        self.step = step
        self.reason = reason


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.chmod(path, 0o600)


def _env_lines(values: dict[str, str]) -> str:
    return "".join(f"{k}={v}\n" for k, v in values.items() if "\n" not in str(v))


def _read_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            out[key.strip()] = value
    return out


class StackPublisher:
    """Publishes, reports, rolls back and removes published apps. One publish per app at a time."""

    def __init__(self, root: Path | None = None, *, target: Target | None = None,
                 runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
                 http_get: Callable[[str], int] | None = None) -> None:
        self._root = root or Path(os.environ.get(STATE_DIR_ENV, "") or Path.home() / ".omnistackai" / "published")
        self._target = target
        self._run = runner
        self._http_get = http_get or _http_status
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    # ── state ──────────────────────────────────────────────────────────────────────────────────
    def _dir(self, app_id: str) -> Path:
        safe = "".join(c for c in app_id if c.isalnum() or c in "-_")[:64] or "app"
        return self._root / safe

    def _state(self, app_id: str) -> dict:
        try:
            return json.loads((self._dir(app_id) / "state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"status": "unpublished", "releases": [], "log": []}

    def _save(self, app_id: str, state: dict) -> None:
        state["log"] = state.get("log", [])[-200:]
        _write_private(self._dir(app_id) / "state.json", json.dumps(state, indent=2))

    def status(self, app_id: str) -> dict:
        state = self._state(app_id)
        secrets_env = _read_env(self._dir(app_id) / "secrets.env")
        # The owner's admin sign-in for the published app. The routes that serve this check that the
        # caller owns the project; it is never written to the log.
        admin = ({"email": _SEED_ADMIN, "password": secrets_env["ADMIN_PASSWORD"]}
                 if secrets_env.get("ADMIN_PASSWORD") and state.get("status") == "live" else None)
        return {k: state.get(k) for k in ("status", "step", "message", "url", "release", "surfaces",
                                          "target", "published_at", "error", "log")} | {"admin": admin} | {
            "releases": [{k: r.get(k) for k in ("release", "commit", "at", "status")}
                         for r in state.get("releases", [])]}

    def _lock(self, app_id: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(app_id, threading.Lock())

    # ── docker ─────────────────────────────────────────────────────────────────────────────────
    def _target_now(self) -> Target:
        return self._target or target_from_env()

    def _docker(self, args: list[str], *, stdin: str | None = None, timeout: float = 900.0,
                log: Callable[[str], None] | None = None) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        target = self._target_now()
        if target.docker_host:
            env["DOCKER_HOST"] = target.docker_host
        done = self._run(["docker", *args], input=stdin, capture_output=True, text=True, env=env,
                         timeout=timeout, check=False)
        if log is not None:
            for line in ((done.stdout or "") + (done.stderr or "")).splitlines()[-60:]:
                if line.strip():
                    log(line)
        return done

    def _compose(self, repo: Path, project: str, env_file: Path) -> list[str]:
        return ["compose", "-p", project, "-f", str(repo / "deploy" / "compose.yaml"),
                "--env-file", str(env_file)]

    # ── publish ────────────────────────────────────────────────────────────────────────────────
    def live_apps(self, owner: str, *, excluding: str | None = None) -> int:
        """How many of this owner's apps are live (PC-011: a plan limit)."""
        count = 0
        for state_file in self._root.glob("*/state.json"):
            if state_file.parent.name == excluding:
                continue
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if state.get("owner") == owner and state.get("status") == "live":
                count += 1
        return count

    def publish(self, app_id: str, repo_dir: str, *, name: str, app_env: dict[str, str] | None = None,
                commit: Callable[[Path, str], str | None] | None = None, owner: str | None = None) -> dict:
        lock = self._lock(app_id)
        if not lock.acquire(blocking=False):
            return self.status(app_id) | {"status": "publishing", "message": "A publish is already running."}
        try:
            return self._publish(app_id, Path(repo_dir), name=name, app_env=app_env or {}, commit=commit, owner=owner)
        finally:
            lock.release()

    def _publish(self, app_id: str, repo: Path, *, name: str, app_env: dict[str, str],
                 commit: Callable[[Path, str], str | None] | None, owner: str | None = None) -> dict:
        state = self._state(app_id)
        if owner:
            state["owner"] = owner
        target = self._target_now()
        state.update(status="publishing", error=None, target=target.label, log=state.get("log", [])[-50:])
        project = f"omni-{''.join(c for c in app_id.lower() if c.isalnum())[:12]}"

        def step(name_: str, message: str) -> None:
            state.update(step=name_, message=message)
            state["log"].append(f"[{_now()}] {name_}: {message}")
            self._save(app_id, state)

        def log(line: str) -> None:
            # Docker colours its output; the Studio shows the log as plain text.
            state["log"].append(_ANSI.sub("", line)[-400:])

        previous = next((r for r in reversed(state.get("releases", [])) if r.get("status") == "live"), None)
        release = (max((r["release"] for r in state.get("releases", [])), default=0) + 1)
        try:
            step("bundle", "Writing the production files into the project")
            layout = read_layout(repo, f"{name}-{project[5:]}")
            if not layout.web_apps:
                raise PublishError("bundle", "this project has no web app to publish")
            written = write_bundle(repo, layout)
            sha = commit(repo, "chore(publish): production bundle") if (commit and written) else None
            sha = sha or _head(repo)

            secrets_file = self._dir(app_id) / "secrets.env"
            stored = _read_env(secrets_file)
            stored.setdefault("DB_PASSWORD", token_source.token_urlsafe(24))
            stored.setdefault("JWT_SECRET", token_source.token_urlsafe(48))
            port = int(state.get("port") or _free_port())
            state["port"] = port
            if target.domain:
                host = f"{layout.slug}.{target.domain}"
                url = f"https://{host}"
                # Reached only through the edge proxy, over the app's own network.
                routing = {"SITE_ADDRESS": ":80", "PUBLISH_BIND": "127.0.0.1", "HTTP_PORT": str(port),
                           "HTTPS_PORT": str(_free_port()), "PUBLIC_URL": url}
            else:
                host = None
                url = f"http://127.0.0.1:{port}"
                routing = {"SITE_ADDRESS": ":80", "PUBLISH_BIND": "127.0.0.1", "HTTP_PORT": str(port),
                           "HTTPS_PORT": str(_free_port()), "PUBLIC_URL": url}
            # PC-102: production storage (R2 prod, else AWS S3, else the uploads volume) and the
            # cloud-drive keys, from the platform's .env; the project's own keys win. Private file.
            from ..localrun.upload_env import production_settings

            from ..localrun.upload_env import project_key_for

            storage_env, upload_compose = production_settings(project_key=project_key_for(repo))
            app_env = {**storage_env, **app_env}
            app_env_file = self._dir(app_id) / "app.env"
            _write_private(app_env_file, _env_lines(app_env))
            compose_env = self._dir(app_id) / "compose.env"
            _write_private(secrets_file, _env_lines(stored))
            _write_private(compose_env, _env_lines(stored | routing | {
                "RELEASE": str(release), "APP_ENV_FILE": str(app_env_file),
                "UPLOAD_SOURCES": upload_compose["UPLOAD_SOURCES"]}))
            compose = self._compose(repo, project, compose_env)

            step("build", f"Building release {release} in production mode")
            built = self._docker([*compose, "build"], timeout=1800.0, log=log)
            if built.returncode != 0:
                raise PublishError("build", _last_error(built) or "the production build failed")

            step("database", "Starting the app's database")
            if self._docker([*compose, "up", "-d", "--wait", "db"], timeout=300.0, log=log).returncode != 0:
                raise PublishError("database", "the database did not become healthy")

            step("migrate", "Applying the database schema")
            applied = self._migrate(repo, compose, log)
            log(f"migrations applied this release: {', '.join(applied) or 'none (up to date)'}")
            if self._secure_seeded_admin(compose, stored):
                _write_private(secrets_file, _env_lines(stored))
                log("the development admin's known password was replaced (shown to the owner only)")

            step("start", f"Starting release {release}")
            if self._docker([*compose, "up", "-d", "--remove-orphans"], timeout=600.0, log=log).returncode != 0:
                raise PublishError("start", "the release did not start")
            if host is not None:
                self._route_edge(app_id, project, host, log)

            step("check", "Checking the live app: pages, API, sign-up and sign-in")
            local = f"http://127.0.0.1:{port}"
            surfaces = self._check(layout, local, compose, log, accounts=_has_accounts(repo),
                                   collection=_collection_path(repo))

            state["releases"] = state.get("releases", []) + [
                {"release": release, "commit": sha, "at": _now(), "status": "live"}]
            for r in state["releases"][:-1]:
                if r.get("status") == "live":
                    r["status"] = "previous"
            self._prune_images(layout, state)
            state.update(status="live", release=release, url=url, published_at=_now(),
                         surfaces=[{"name": s, "url": url + (base_path(s) or "/")} for s in surfaces])
            step("live", f"Release {release} is live at {url}")
            return self.status(app_id)
        except PublishError as error:
            return self._failed(app_id, state, error, previous, repo, project, release, log)
        except (OSError, subprocess.TimeoutExpired) as error:
            return self._failed(app_id, state, PublishError(state.get("step") or "publish", str(error)),
                                previous, repo, project, release, log)

    def _failed(self, app_id, state, error: PublishError, previous, repo, project, release, log) -> dict:
        state["releases"] = state.get("releases", []) + [
            {"release": release, "commit": _head(repo), "at": _now(), "status": "failed"}]
        rolled = ""
        if previous is not None and error.step in ("start", "check"):
            if self._start_release(app_id, repo, project, previous["release"], log):
                rolled = f" Release {previous['release']} is still live."
        state.update(status="live" if rolled else "failed", error={"step": error.step, "reason": error.reason},
                     message=f"Publish failed at '{error.step}': {error.reason}.{rolled}")
        state["log"].append(f"[{_now()}] failed at {error.step}: {error.reason}")
        self._save(app_id, state)
        return self.status(app_id)

    # ── steps ──────────────────────────────────────────────────────────────────────────────────
    def _psql(self, compose: list[str], sql: str, *, single: bool = True) -> subprocess.CompletedProcess:
        args = [*compose, "exec", "-T", "db", "psql", "-U", "app", "-d", "app", "-v", "ON_ERROR_STOP=1", "-q"]
        return self._docker(args + (["-1"] if single else []) + ["-f", "-"], stdin=sql, timeout=300.0)

    def _migrate(self, repo: Path, compose: list[str], log) -> list[str]:
        ledger = ("CREATE TABLE IF NOT EXISTS _omnistack_migrations "
                  "(name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now());")
        if self._psql(compose, ledger).returncode != 0:
            raise PublishError("migrate", "could not prepare the migration ledger")
        seen = self._docker([*compose, "exec", "-T", "db", "psql", "-U", "app", "-d", "app", "-tA", "-c",
                             "SELECT name FROM _omnistack_migrations"], timeout=60.0)
        done = {line.strip() for line in (seen.stdout or "").splitlines() if line.strip()}
        applied = []
        for path in migrations(repo):
            if path.name in done:
                continue
            safe_name = path.name.replace("'", "")
            sql = path.read_text(encoding="utf-8") + (
                f"\nINSERT INTO _omnistack_migrations (name) VALUES ('{safe_name}');\n")
            result = self._psql(compose, sql)
            if result.returncode != 0:
                raise PublishError("migrate", f"{path.name} did not apply: {_last_error(result)}")
            applied.append(path.name)
        return applied

    def _secure_seeded_admin(self, compose: list[str], stored: dict[str, str]) -> bool:
        """The schema seeds admin@example.local / changeme for local development. A published app
        must never accept that password (found live: every published app did). It is replaced with a
        generated one, kept in the private secrets file and shown only to the project's owner."""
        found = self._docker([*compose, "exec", "-T", "db", "psql", "-U", "app", "-d", "app", "-tA", "-c",
                              "SELECT to_regclass('public.users') IS NOT NULL AND EXISTS "
                              f"(SELECT 1 FROM users WHERE email = '{_SEED_ADMIN}' AND password_hash = '{_SEED_HASH}')"],
                             timeout=60.0)
        if (found.stdout or "").strip() != "t":
            return False
        stored.setdefault("ADMIN_PASSWORD", token_source.token_urlsafe(15))
        new_hash = _pbkdf2(stored["ADMIN_PASSWORD"])
        result = self._psql(compose, f"UPDATE users SET password_hash = '{new_hash}' WHERE email = '{_SEED_ADMIN}' "
                                     f"AND password_hash = '{_SEED_HASH}';")
        if result.returncode != 0:
            raise PublishError("migrate", "could not replace the development admin's password")
        return True

    def _check(self, layout: Layout, local: str, compose: list[str], log, *, accounts: bool = True,
               collection: str | None = None) -> list[str]:
        deadline = time.time() + 180
        wanted = {app: local + (base_path(app) or "/") for app in layout.web_apps}
        if layout.api_kind:
            wanted["api"] = local + "/api/healthz"
        ok: set[str] = set()
        while time.time() < deadline and len(ok) < len(wanted):
            for name_, url in wanted.items():
                if name_ not in ok and self._http_get(url) == 200:
                    ok.add(name_)
            if len(ok) < len(wanted):
                time.sleep(1.0)
        missing = sorted(set(wanted) - ok)
        if missing:
            raise PublishError("check", f"not answering: {', '.join(missing)}")
        if layout.api_kind and accounts:
            self._check_accounts(local, compose, log)
        elif layout.api_kind and collection:
            # No accounts to sign up with: read real data through the live URL instead.
            code = self._http_get(local + "/api" + collection)
            if code != 200:
                raise PublishError("check", f"reading {collection} through the live URL answered {code}")
            log(f"data check: {collection} read from the database through the live URL")
        return list(layout.web_apps)

    def _check_accounts(self, local: str, compose: list[str], log) -> None:
        """A real sign-up, sign-in and read-back through the live URL; the account is then removed."""
        password = token_source.token_urlsafe(18)
        self._psql(compose, f"DELETE FROM users WHERE email = '{_CHECK_EMAIL}';", single=False)
        try:
            status, _ = _post_json(local + "/api/auth/register",
                                   {"email": _CHECK_EMAIL, "password": password, "full_name": "Publish check"})
            if status not in (200, 201):
                raise PublishError("check", f"sign-up answered {status}")
            status, body = _post_json(local + "/api/auth/login", {"email": _CHECK_EMAIL, "password": password})
            token = (body or {}).get("access_token") if isinstance(body, dict) else None
            if status != 200 or not token:
                raise PublishError("check", f"sign-in answered {status}")
            if _http_status(local + "/api/auth/me", token=token) != 200:
                raise PublishError("check", "the signed-in account could not be read back")
            log("account check: sign-up, sign-in and read-back all passed")
        finally:
            self._psql(compose, f"DELETE FROM users WHERE email = '{_CHECK_EMAIL}';", single=False)

    def _route_edge(self, app_id: str, project: str, host: str, log) -> None:
        """One shared proxy per host for every app with a domain; it holds the certificates."""
        target = self._target_now()
        if self._docker(["inspect", EDGE], timeout=60.0).returncode != 0:
            started = self._docker(["run", "-d", "--name", EDGE, "--restart", "unless-stopped",
                                    "-p", f"{target.edge_bind}:{target.edge_http}:80",
                                    "-p", f"{target.edge_bind}:{target.edge_https}:443",
                                    "-v", f"{EDGE}-data:/data", "caddy:2-alpine"], timeout=300.0, log=log)
            if started.returncode != 0:
                raise PublishError("start", "the shared HTTPS proxy did not start")
        self._docker(["network", "connect", f"{project}_default", EDGE], timeout=60.0)
        registry = self._root / f"edge-{_host_key(target)}.json"
        try:
            sites = json.loads(registry.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            sites = {}
        sites[host] = f"{project}-proxy-1:80"
        _write_private(registry, json.dumps(sites, indent=2))
        config = "".join(f"{h} {{\n\treverse_proxy {upstream}\n}}\n" for h, upstream in sorted(sites.items()))
        self._docker(["exec", "-i", EDGE, "sh", "-c", "cat > /etc/caddy/Caddyfile"], stdin=config, timeout=60.0)
        if self._docker(["exec", EDGE, "caddy", "reload", "--config", "/etc/caddy/Caddyfile"],
                        timeout=120.0, log=log).returncode != 0:
            raise PublishError("start", "the shared HTTPS proxy rejected its configuration")

    def _start_release(self, app_id: str, repo: Path, project: str, release: int, log) -> bool:
        compose_env = self._dir(app_id) / "compose.env"
        values = _read_env(compose_env)
        values["RELEASE"] = str(release)
        _write_private(compose_env, _env_lines(values))
        compose = self._compose(repo, project, compose_env)
        return self._docker([*compose, "up", "-d", "--no-build", "--remove-orphans"], timeout=600.0,
                            log=log).returncode == 0

    def _prune_images(self, layout: Layout, state: dict) -> None:
        keep = {r["release"] for r in state["releases"][-KEEP_RELEASES:]}
        services = (["api"] if layout.api_kind else []) + list(layout.web_apps) + ["proxy"]
        for r in state["releases"]:
            if r["release"] not in keep and not r.get("pruned"):
                for service in services:
                    self._docker(["image", "rm", f"omnistackai/{layout.slug}-{service}:{r['release']}"], timeout=120.0)
                r["pruned"] = True

    # ── rollback and remove ────────────────────────────────────────────────────────────────────
    def rollback(self, app_id: str, repo_dir: str) -> dict:
        state = self._state(app_id)
        kept = [r for r in state.get("releases", []) if r.get("status") in ("live", "previous") and not r.get("pruned")]
        if len(kept) < 2:
            return self.status(app_id) | {"message": "There is no earlier release to go back to."}
        current, earlier = kept[-1], kept[-2]
        project = f"omni-{''.join(c for c in app_id.lower() if c.isalnum())[:12]}"
        logs: list[str] = []
        if not self._start_release(app_id, Path(repo_dir), project, earlier["release"], logs.append):
            state["message"] = f"Could not start release {earlier['release']}."
        else:
            current["status"] = "rolled-back"
            earlier["status"] = "live"
            state.update(status="live", release=earlier["release"],
                         message=f"Rolled back to release {earlier['release']}.")
        state["log"] = state.get("log", []) + [f"[{_now()}] rollback: {state['message']}"] + logs[-20:]
        self._save(app_id, state)
        return self.status(app_id)

    def unpublish(self, app_id: str, repo_dir: str, *, delete_data: bool = False) -> dict:
        state = self._state(app_id)
        project = f"omni-{''.join(c for c in app_id.lower() if c.isalnum())[:12]}"
        compose_env = self._dir(app_id) / "compose.env"
        if compose_env.is_file() and (Path(repo_dir) / "deploy" / "compose.yaml").is_file():
            args = [*self._compose(Path(repo_dir), project, compose_env), "down", "--remove-orphans"]
            self._docker(args + (["-v"] if delete_data else []), timeout=300.0)
        if delete_data:
            # PC-012: nothing of a deleted app stays behind - not its release history, and not the
            # secrets its compose.env and secrets.env hold.
            shutil.rmtree(self._dir(app_id), ignore_errors=True)
            # PC-102: nor its uploads in production storage (the stack's volume went with `down -v`).
            from ..localrun.upload_env import project_key_for, purge_project_files

            purge_project_files(project_key_for(repo_dir), only=("r2-prod", "s3"))
            return self.status(app_id) | {"message": "Unpublished. Its data is deleted."}
        state.update(status="unpublished", url=None, surfaces=None,
                     message="Unpublished." + ("" if delete_data else " The database is kept."))
        self._save(app_id, state)
        return self.status(app_id)


_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _has_accounts(repo: Path) -> bool:
    """Whether the app has sign-up (R-591): its schema then carries the accounts table.

    Read from the schema rather than the API contract, which does not list the /auth routes yet.
    """
    for path in migrations(repo):
        try:
            if 'CREATE TABLE IF NOT EXISTS "users"' in path.read_text(encoding="utf-8"):
                return True
        except OSError:
            continue
    return False


def _collection_path(repo: Path) -> str | None:
    """A list endpoint from the API's own contract, to read real data through the live URL."""
    for contract in (repo / "services" / "api" / "openapi.json", repo / "services" / "api" / "contracts" / "openapi.json"):
        try:
            paths = json.loads(contract.read_text(encoding="utf-8")).get("paths", {})
        except (OSError, ValueError, AttributeError):
            continue
        for path, ops in paths.items():
            if "{" not in path and "get" in ops and not path.startswith(("/auth", "/health")):
                return path
    return None


def _pbkdf2(plain: str) -> str:
    """The generated apps' password format (R-591): "<hex salt>:<hex PBKDF2-SHA256 x100k>"."""
    salt = token_source.token_bytes(32)
    return salt.hex() + ":" + hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, 100_000).hex()


def _host_key(target: Target) -> str:
    return "".join(c for c in (target.docker_host or "local") if c.isalnum())[:40] or "local"


def _head(repo: Path) -> str | None:
    done = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, capture_output=True, text=True, check=False)
    return done.stdout.strip() or None


def _last_error(result: subprocess.CompletedProcess) -> str:
    text = _ANSI.sub("", (result.stderr or "") + "\n" + (result.stdout or ""))
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # The compiler's own words beat pnpm's closing "command failed": "Module not found: Can't
    # resolve '@/components/x' in ./app/page.tsx" is something a person can act on.
    for marker in ("Type error:", "Module not found", "Failed to compile", "No matching distribution"):
        hits = [i for i, l in enumerate(lines) if marker in l]
        if hits:
            i = hits[0]
            return " ".join(lines[max(0, i - 1): i + 2])[:300]
    errors = [l for l in lines if "error" in l.lower() or "failed" in l.lower()]
    return (errors or lines or [""])[-1][:300]


def _http_status(url: str, *, token: str | None = None) -> int:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except (urllib.error.URLError, OSError):
        return 0


def _post_json(url: str, body: dict) -> tuple[int, object]:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        return error.code, None
    except (urllib.error.URLError, OSError, ValueError):
        return 0, None

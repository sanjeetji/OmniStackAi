"""Deterministic run plan for a generated app repo (R-419).

``build_run_plan(repo_dir, ...)`` inspects a generated customer repo and composes an
ordered, JSON-safe plan to run it locally: recreate a per-app PostgreSQL database in the
local container, apply migrations, start the backend, and start the web app. Pure and
offline (it only reads the repo layout and composes commands as data); the opt-in
``localrun.run`` module executes it.
"""

from __future__ import annotations

import re
import socket
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    slug = _SLUG_RE.sub("_", text.lower()).strip("_")
    return slug or "app"


@dataclass(frozen=True)
class RunStep:
    """One command in a run plan. ``env``/``stdin_file`` are optional; ``background`` marks a server."""

    label: str
    program: str
    args: tuple[str, ...] = ()
    cwd: str | None = None
    stdin_file: str | None = None
    background: bool = False
    env: tuple[tuple[str, str], ...] = ()
    tolerate_failure: bool = False

    def to_dict(self, *, mask: tuple[str, ...] = ()) -> dict:
        def _mask(value: str) -> str:
            out = value
            for secret in mask:
                if secret:
                    out = out.replace(secret, "***")
            return out

        return {
            "label": self.label,
            "program": self.program,
            "args": [_mask(a) for a in self.args],
            "cwd": self.cwd,
            "stdin_file": self.stdin_file,
            "background": self.background,
            "env": {k: _mask(v) for k, v in self.env},
            "tolerate_failure": self.tolerate_failure,
        }


@dataclass(frozen=True)
class RunPlan:
    repo_dir: str
    app_slug: str
    db_name: str
    backend_kind: str  # "python" | "go" | "none"
    has_web: bool
    api_url: str
    web_url: str
    db_password: str
    # R-541: a prompt-built project can now carry a staff console at apps/admin beside the public
    # app. Defaulted so every existing caller and recorded plan stays valid.
    has_admin: bool = False
    admin_url: str = ""
    # R-542: set when the project runs more than one UI and the console serves each under its own
    # base path. False keeps the single-app preview exactly as it was.
    multi_app: bool = False
    public_base: str = ""
    # R-542: with a base path the app no longer answers at "/" — a readiness probe against the
    # origin gets a 404 and the preview is declared dead. These are where each app actually
    # serves its home page, which is what readiness must check.
    web_health_url: str = ""
    admin_health_url: str = ""
    # R-545: the generated Expo app. `expo_url` is what the QR encodes — Expo Go opens exp:// URLs.
    has_mobile: bool = False
    #: R-562: every Expo app in the project — id, port, url and the exp:// the phone scans. The
    #: singular fields below describe the first of them, unchanged, for every existing reader.
    mobile_surfaces: tuple[dict, ...] = ()
    mobile_url: str = ""
    expo_url: str = ""
    #: R-553: (id, url) per discovered web surface, in the order they are started. Empty for a
    #: plan built before this existed, so `preview_apps()` falls back to web/admin.
    web_surfaces: tuple[tuple[str, str], ...] = ()
    steps: tuple[RunStep, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        mask = (self.db_password,) if self.db_password else ()
        return {
            "repo_dir": self.repo_dir,
            "app_slug": self.app_slug,
            "db_name": self.db_name,
            "backend_kind": self.backend_kind,
            "has_web": self.has_web,
            "has_admin": self.has_admin,
            "has_mobile": self.has_mobile,
            "mobile_surfaces": [dict(s) for s in self.mobile_surfaces],
            "multi_app": self.multi_app,
            "api_url": self.api_url,
            "web_url": self.web_url,
            "admin_url": self.admin_url,
            "mobile_url": self.mobile_url,
            "expo_url": self.expo_url,
            "steps": [step.to_dict(mask=mask) for step in self.steps],
        }

    def preview_apps(self) -> tuple[dict, ...]:
        """The app list a multi-app preview payload reports, in switcher order.

        Empty unless this plan is multi-app, so a single-app project keeps reporting the plain
        `web_url` preview it always has. Shape matches the console's `PreviewApp`, which template
        previews already populate — which is why the console needs no change to show these.
        """
        if not self.multi_app and not self.has_mobile:
            return ()
        base = self.public_base.rstrip("/")
        # R-553: whatever apps/ actually held. `web` and `admin` keep their names and kinds so the
        # console renders them as it always has; a role-scoped surface is titled from its directory
        # and rendered as a plain web app.
        surfaces = self.web_surfaces or (("web", self.web_url), ("admin", self.admin_url))
        titles = {"web": "Web app", "admin": "Admin console"}
        apps: list[dict] = [
            {
                "id": app_id,
                "name": titles.get(app_id, app_id.replace("-", " ").replace("_", " ").title()),
                "kind": app_id if app_id in ("web", "admin") else "web",
                "url": url,
                "path": f"{base}/{app_id}",
            }
            for app_id, url in surfaces
            if url
        ]
        if self.backend_kind != "none":
            apps.append(
                {
                    "id": "api",
                    "name": "API",
                    "kind": "api",
                    "url": self.api_url,
                    "path": f"{base}/api",
                }
            )
        # R-545: not proxied. Expo Go talks to the dev server directly over the LAN, so the console
        # shows the exp:// URL as a QR rather than an iframe — a native app cannot be rendered in
        # one. `scan` is what the phone reads. R-562: one entry per app, because an ecosystem can
        # have a courier app and a customer app and a single QR cannot stand for both.
        for surface in self.mobile_surfaces:
            label = "Mobile app" if surface["id"] == "mobile" else surface["id"].replace("-", " ").title()
            apps.append(
                {
                    "id": surface["id"],
                    "name": f"{label} (Expo)",
                    "kind": "mobile",
                    "url": surface["url"],
                    "path": "",
                    "scan": surface["scan"],
                }
            )
        for app in apps:
            parsed = urllib.parse.urlparse(app["url"])
            app["port"] = parsed.port or 0
        return tuple(apps)


def lan_address(fallback: str = "127.0.0.1") -> str:
    """This machine's LAN IPv4, for URLs a phone has to reach (R-545).

    A phone scanning the Expo QR is a different device: `127.0.0.1` is the phone itself, so an app
    pointed there silently fails every API call. Opening a UDP socket toward a routable address
    makes the OS pick the outbound interface and reveals its address; no packet is actually sent,
    and nothing here requires the network to be up — it falls back to loopback when it is not.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 9))  # TEST-NET-1: reserved, never routed, never answered.
        address = sock.getsockname()[0]
    except OSError:
        return fallback
    finally:
        sock.close()
    return address if isinstance(address, str) and address else fallback


#: R-553: `web` and `admin` keep fixed ids so existing previews, proxy paths and tests are
#: unchanged; `mobile` is Expo and is handled separately, never as a proxied web app. Anything else
#: under apps/ is a role-scoped surface an ecosystem plan produced, and is discovered rather than
#: named — the alternative is another hand-written block per surface, which is the ceiling this
#: removes.
RESERVED_APP_IDS = ("web", "admin", "mobile")


#: What makes a directory an Expo app. R-562: an ecosystem can contain several — a courier app and
#: a customer app over one API — so they are found by what they are rather than by being the one
#: directory called `mobile`.
_EXPO_MARKERS = ("app.config.js", "app.json")


def is_mobile_app(app_dir: Path) -> bool:
    """Whether this app directory is an Expo app rather than a web one.

    `apps/mobile` counts by name because it has been the reserved directory for the Expo app since
    R-545, and a project generated before this change has no other marker to go by. Everything else
    is judged by what it contains, which is what lets an ecosystem name its apps after their roles.
    """
    return app_dir.name == "mobile" or any((app_dir / marker).is_file() for marker in _EXPO_MARKERS)


def discover_mobile_apps(root: Path) -> tuple[str, ...]:
    """Every Expo app under apps/, in a stable order.

    `mobile` first when present, so a single-app project keeps the id it has always had, then the
    rest sorted — a plan that reorders between runs is one nobody can reason about.
    """
    apps_dir = root / "apps"
    if not apps_dir.is_dir():
        return ()
    found = {
        entry.name
        for entry in apps_dir.iterdir()
        if entry.is_dir() and (entry / "package.json").is_file() and is_mobile_app(entry)
    }
    ordered = [name for name in ("mobile",) if name in found]
    return tuple(ordered + sorted(found - set(ordered)))


def discover_web_apps(root: Path) -> tuple[str, ...]:
    """Every runnable web app under apps/, in a stable order: web, admin, then the rest sorted.

    Sorted rather than filesystem order, because a run plan that changes between two runs of the
    same project is a plan nobody can reason about.
    """
    apps_dir = root / "apps"
    if not apps_dir.is_dir():
        return ()
    found = {
        entry.name
        for entry in apps_dir.iterdir()
        if entry.is_dir() and (entry / "package.json").is_file() and not is_mobile_app(entry)
    }
    ordered = [name for name in ("web", "admin") if name in found]
    ordered += sorted(found - set(ordered))
    return tuple(ordered)


def _backend_kind(api_dir: Path) -> str:
    if (api_dir / "requirements.txt").is_file():
        return "python"
    if (api_dir / "go.mod").is_file() or (api_dir / "main.go").is_file():
        return "go"
    return "none"


def build_run_plan(
    repo_dir: str,
    *,
    db_container: str = "omnistackai-local-postgres-1",
    db_user: str = "omnistackai",
    db_password: str = "",
    db_host: str = "127.0.0.1",
    db_port: int = 5432,
    maintenance_db: str = "omnistackai",
    db_name: str | None = None,
    api_port: int = 8000,
    web_port: int = 3000,
    admin_port: int = 3100,
    mobile_port: int = 8081,
    extra_app_ports: tuple[int, ...] = (),
    public_base: str = "",
    jwt_secret: str = "local-dev-secret",
    extra_env: Mapping[str, str] | None = None,
) -> RunPlan:
    """Compose the ordered plan to run the generated repo at ``repo_dir`` locally."""
    root = Path(repo_dir)
    api_dir = root / "services" / "api"
    web_dir = root / "apps" / "web"
    admin_dir = root / "apps" / "admin"
    app_slug = _slug(root.name)
    database = db_name or app_slug
    backend_kind = _backend_kind(api_dir)
    # R-553: discovered rather than named. `web` and `admin` keep their meaning; anything else
    # under apps/ is a role-scoped surface (a courier dispatch app, a merchant portal) that an
    # ecosystem plan produced.
    web_apps = discover_web_apps(root)
    has_web = "web" in web_apps
    has_admin = "admin" in web_apps
    mobile_ids = discover_mobile_apps(root)
    has_mobile = bool(mobile_ids)

    api_url = f"http://{db_host}:{api_port}"
    web_url = f"http://127.0.0.1:{web_port}"
    admin_url = f"http://127.0.0.1:{admin_port}" if has_admin else ""
    # R-545: Expo binds on the LAN so a phone can reach it; the QR encodes the exp:// form.
    lan = lan_address() if has_mobile else "127.0.0.1"
    web_lan = lan if has_mobile else lan_address()
    # One port per app, from `mobile_port` upward. The first keeps the original port and the
    # original `mobile_url`/`expo_url`, so a single-app project and everything reading those two
    # fields behaves exactly as before.
    mobile_surfaces = tuple(
        {
            "id": app_id,
            "port": mobile_port + offset,
            "url": f"http://{lan}:{mobile_port + offset}",
            "scan": f"exp://{lan}:{mobile_port + offset}",
        }
        for offset, app_id in enumerate(mobile_ids)
    )
    mobile_url = mobile_surfaces[0]["url"] if mobile_surfaces else ""
    expo_url = mobile_surfaces[0]["scan"] if mobile_surfaces else ""

    # R-542: with two Next apps in one project the console serves each under its own base path,
    # exactly as template previews do. Only then — a single-app project keeps serving at the root,
    # so nothing about today's behaviour changes for it.
    # More than one UI means the console serves each under its own base path, as template previews
    # already do. One UI keeps serving at the root, so a single-app project is untouched.
    multi_app = len(web_apps) > 1 and bool(public_base)
    base = public_base.rstrip("/")

    # `web` and `admin` keep the ports they were allocated; further surfaces take the extras, and
    # fall back to a deterministic offset so a caller that has not allocated any still gets a
    # usable plan rather than a crash.
    app_ports: dict[str, int] = {}
    spare = list(extra_app_ports)
    for app_id in web_apps:
        if app_id == "web":
            app_ports[app_id] = web_port
        elif app_id == "admin":
            app_ports[app_id] = admin_port
        elif spare:
            app_ports[app_id] = spare.pop(0)
        else:
            app_ports[app_id] = admin_port + 1 + len(app_ports)

    web_base_path = f"{base}/web" if multi_app and has_web else ""
    admin_base_path = f"{base}/admin" if multi_app and has_admin else ""
    # Relative on purpose: the browser loads the app from the console's origin, so a loopback
    # address here would break every API call from another device on the LAN.
    public_api_url = f"{base}/api" if multi_app else api_url
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{database}"

    extra_tuples = tuple((k, str(v)) for k, v in sorted(extra_env.items())) if extra_env else ()

    steps: list[RunStep] = []

    # --- database: recreate a clean per-app database, then apply migrations ---
    pg_env = (("PGPASSWORD", db_password),)
    steps.append(
        RunStep(
            label=f"drop database {database} (if it exists)",
            program="docker",
            args=(
                "exec", "-i", db_container,
                "psql", "-U", db_user, "-d", maintenance_db,
                "-c", f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE);',
            ),
            env=pg_env,
            tolerate_failure=True,
        )
    )
    steps.append(
        RunStep(
            label=f"create database {database}",
            program="docker",
            args=(
                "exec", "-i", db_container,
                "psql", "-U", db_user, "-d", maintenance_db,
                "-c", f'CREATE DATABASE "{database}";',
            ),
            env=pg_env,
        )
    )
    migrations_dir = api_dir / "migrations"
    if migrations_dir.is_dir():
        for migration in sorted(migrations_dir.glob("*.sql")):
            steps.append(
                RunStep(
                    label=f"apply migration {migration.name}",
                    program="docker",
                    args=(
                        "exec", "-i", db_container,
                        "psql", "-U", db_user, "-d", database, "-v", "ON_ERROR_STOP=1",
                    ),
                    stdin_file=str(migration),
                    env=pg_env,
                )
            )

    # --- backend ---
    if backend_kind == "python":
        steps.append(
            RunStep(
                label="create backend virtualenv",
                program="python3",
                args=("-m", "venv", ".venv"),
                cwd=str(api_dir),
            )
        )
        steps.append(
            RunStep(
                label="install backend dependencies",
                program=".venv/bin/pip",
                args=("install", "-q", "-r", "requirements.txt"),
                cwd=str(api_dir),
            )
        )
        steps.append(
            RunStep(
                label=f"start backend API (uvicorn) on {api_url}",
                program=".venv/bin/uvicorn",
                args=("app.main:app", "--host", "127.0.0.1", "--port", str(api_port)),
                cwd=str(api_dir),
                env=(("DATABASE_URL", database_url), ("JWT_SECRET", jwt_secret)) + extra_tuples,
                background=True,
            )
        )
    elif backend_kind == "go":
        # R-561: the Python branch above creates a virtualenv and installs before starting; the Go
        # branch went straight to `go run`, which fails on a generated project because it ships
        # go.mod with no go.sum. Every Go backend was therefore broken end to end, in the preview
        # and for anyone following the generated README.
        steps.append(
            RunStep(
                label="resolve backend dependencies (go mod tidy)",
                program="go",
                # tidy, not download: the generated go.mod lists direct requires only, so
                # downloading the build list leaves the transitive ones missing and the build
                # still fails. Verified against a real toolchain.
                args=("mod", "tidy"),
                cwd=str(api_dir),
            )
        )
        steps.append(
            RunStep(
                label=f"start backend API (go run) on {api_url}",
                program="go",
                args=("run", "."),
                cwd=str(api_dir),
                env=(
                    ("DATABASE_URL", database_url),
                    ("JWT_SECRET", jwt_secret),
                    ("PORT", str(api_port)),
                    ("ADDR", f":{api_port}"),
                ) + extra_tuples,
                background=True,
            )
        )

    # --- web surfaces (R-553): one loop over whatever apps/ actually contains ---
    # `web` and `admin` keep their ids, ports and base paths so existing previews are unchanged;
    # anything else is a role-scoped surface an ecosystem plan produced. Adding a surface used to
    # mean copying this block again, which is the ceiling that stopped an ecosystem being
    # previewable at all.
    for index, app_id in enumerate(web_apps):
        app_dir = root / "apps" / app_id
        port = app_ports[app_id]
        url = f"http://127.0.0.1:{port}"
        base_path = f"{base}/{app_id}" if multi_app else ""
        steps.append(
            RunStep(
                # --ignore-scripts avoids pnpm's ERR_PNPM_IGNORED_BUILDS exit-1 on native build
                # scripts (e.g. sharp), which `next dev` does not need.
                label=f"install {app_id} dependencies (pnpm)",
                program="pnpm",
                args=("install", "--ignore-scripts", "--ignore-workspace"),
                cwd=str(app_dir),
            )
        )
        steps.append(
            RunStep(
                label=f"start {app_id} app (next dev) on {url}",
                program="./node_modules/.bin/next",
                args=("dev", "-p", str(port)),
                cwd=str(app_dir),
                env=(
                    ("NEXT_PUBLIC_API_URL", public_api_url),
                    ("BASE_PATH", base_path),
                    ("NEXT_PUBLIC_BASE_PATH", base_path),
                    # R-573: the in-app QR swaps localhost for this, so a phone can open the page.
                    ("NEXT_PUBLIC_LAN_HOST", web_lan),
                ) + extra_tuples,
                background=True,
            )
        )

    # --- mobile (R-545): Expo in LAN mode, so Expo Go on a real phone can open it ---
    # R-562: one of these per Expo app. An ecosystem can hold a courier app and a customer app over
    # one API, and this used to start whichever one happened to be called `mobile`.
    for surface in mobile_surfaces:
        surface_dir = root / "apps" / surface["id"]
        steps.append(
            RunStep(
                label=f"install {surface['id']} dependencies (pnpm)",
                program="pnpm",
                args=("install", "--ignore-scripts", "--ignore-workspace"),
                cwd=str(surface_dir),
            )
        )
        steps.append(
            RunStep(
                label=f"start {surface['id']} app (expo) on {surface['url']}",
                program="./node_modules/.bin/expo",
                args=("start", "--lan", "--port", str(surface["port"])),
                cwd=str(surface_dir),
                env=(
                    # The phone is a different device: a loopback API base fails every call.
                    ("EXPO_PUBLIC_API_URL", f"http://{lan}:{api_port}"),
                    ("CI", "1"),  # keeps Expo non-interactive; it otherwise waits on a keypress.
                    ("BROWSER", "none"),
                ) + extra_tuples,
                background=True,
            )
        )

    return RunPlan(
        repo_dir=str(root),
        app_slug=app_slug,
        db_name=database,
        backend_kind=backend_kind,
        has_web=has_web,
        api_url=api_url,
        web_url=web_url,
        db_password=db_password,
        has_admin=has_admin,
        admin_url=admin_url,
        multi_app=multi_app,
        public_base=base,
        has_mobile=has_mobile,
        mobile_surfaces=mobile_surfaces,
        mobile_url=mobile_url,
        web_surfaces=tuple((app_id, f"http://127.0.0.1:{app_ports[app_id]}") for app_id in web_apps),
        expo_url=expo_url,
        web_health_url=f"{web_url}{web_base_path}",
        admin_health_url=f"{admin_url}{admin_base_path}" if has_admin else "",
        steps=tuple(steps),
    )

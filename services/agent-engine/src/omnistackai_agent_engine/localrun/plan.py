"""Deterministic run plan for a generated app repo (R-419).

``build_run_plan(repo_dir, ...)`` inspects a generated customer repo and composes an
ordered, JSON-safe plan to run it locally: recreate a per-app PostgreSQL database in the
local container, apply migrations, start the backend, and start the web app. Pure and
offline (it only reads the repo layout and composes commands as data); the opt-in
``localrun.run`` module executes it.
"""

from __future__ import annotations

import re
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
    steps: tuple[RunStep, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        mask = (self.db_password,) if self.db_password else ()
        return {
            "repo_dir": self.repo_dir,
            "app_slug": self.app_slug,
            "db_name": self.db_name,
            "backend_kind": self.backend_kind,
            "has_web": self.has_web,
            "api_url": self.api_url,
            "web_url": self.web_url,
            "steps": [step.to_dict(mask=mask) for step in self.steps],
        }


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
    jwt_secret: str = "local-dev-secret",
) -> RunPlan:
    """Compose the ordered plan to run the generated repo at ``repo_dir`` locally."""
    root = Path(repo_dir)
    api_dir = root / "services" / "api"
    web_dir = root / "apps" / "web"
    app_slug = _slug(root.name)
    database = db_name or app_slug
    backend_kind = _backend_kind(api_dir)
    has_web = (web_dir / "package.json").is_file()

    api_url = f"http://{db_host}:{api_port}"
    web_url = f"http://127.0.0.1:{web_port}"
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{database}"

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
                "-c", f'DROP DATABASE IF EXISTS "{database}";',
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
                env=(("DATABASE_URL", database_url), ("JWT_SECRET", jwt_secret)),
                background=True,
            )
        )
    elif backend_kind == "go":
        steps.append(
            RunStep(
                label=f"start backend API (go run) on {api_url}",
                program="go",
                args=("run", "."),
                cwd=str(api_dir),
                env=(("DATABASE_URL", database_url), ("JWT_SECRET", jwt_secret)),
                background=True,
            )
        )

    # --- web (run the Next binary directly, never `pnpm dev`) ---
    if has_web:
        steps.append(
            RunStep(
                # --ignore-scripts avoids pnpm's ERR_PNPM_IGNORED_BUILDS exit-1 on native
                # build scripts (e.g. sharp), which `next dev` does not need.
                label="install web dependencies (pnpm)",
                program="pnpm",
                args=("install", "--ignore-scripts"),
                cwd=str(web_dir),
            )
        )
        steps.append(
            RunStep(
                label=f"start web app (next dev) on {web_url}",
                program="./node_modules/.bin/next",
                args=("dev", "-p", str(web_port)),
                cwd=str(web_dir),
                env=(("NEXT_PUBLIC_API_URL", api_url),),
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
        steps=tuple(steps),
    )

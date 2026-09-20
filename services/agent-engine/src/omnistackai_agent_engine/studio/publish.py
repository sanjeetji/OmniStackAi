"""Publish readiness evaluator for generated projects (G-01 Publish v1 / R-509).

Evaluates whether a workspace repository is:
- Path 1: Web only (deploys completely to Vercel or Netlify)
- Path 2: Web + Backend (web to Vercel/Netlify, backend to Render/Fly.io)
- Path 3: Full-stack with Database (requires external PostgreSQL like Neon/Supabase)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

DEFAULT_RENDER_YAML = """services:
  - type: web
    name: backend-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PORT
        value: 8000
"""

DEFAULT_FLY_TOML = """app = "omnistack-backend"
primary_region = "iad"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
"""


def evaluate_publish_readiness(repo_dir: Path) -> dict[str, Any]:
    """Scan the repository files to classify deploy path, backend, db, and env requirements."""
    if not repo_dir.is_dir():
        return {
            "path": 1,
            "path_description": "Web-only application (deploys completely to Vercel or Netlify).",
            "has_backend": False,
            "has_db": False,
            "render_yaml": "",
            "fly_toml": "",
            "missing_secrets": [],
            "env_suggestions": [],
        }

    has_db = _detect_database(repo_dir)
    has_backend = _detect_backend(repo_dir)

    # Path classification
    if has_db:
        path = 3
        path_desc = (
            "Full-stack application with database. The web frontend deploys to Vercel or Netlify. "
            "A PostgreSQL database (Neon, Supabase, or AWS RDS) is required and should be configured via DATABASE_URL."
        )
    elif has_backend:
        path = 2
        path_desc = (
            "Web + separate backend service. The web frontend deploys to Vercel or Netlify. "
            "The backend service can be deployed to Render, Fly.io, or Railway using the generated configuration."
        )
    else:
        path = 1
        path_desc = "Web-only application. Deploys completely and seamlessly to Vercel or Netlify."

    # Render YAML / Fly TOML configurations
    render_yaml = ""
    fly_toml = ""
    if has_backend or has_db:
        render_file = repo_dir / "render.yaml"
        if render_file.is_file():
            try:
                render_yaml = render_file.read_text(encoding="utf-8")
            except OSError:
                render_yaml = DEFAULT_RENDER_YAML
        else:
            render_yaml = DEFAULT_RENDER_YAML

        fly_file = repo_dir / "fly.toml"
        if fly_file.is_file():
            try:
                fly_toml = fly_file.read_text(encoding="utf-8")
            except OSError:
                fly_toml = DEFAULT_FLY_TOML
        else:
            fly_toml = DEFAULT_FLY_TOML

    env_suggestions = _detect_env_vars(repo_dir, has_db)

    return {
        "path": path,
        "path_description": path_desc,
        "has_backend": has_backend,
        "has_db": has_db,
        "render_yaml": render_yaml,
        "fly_toml": fly_toml,
        "missing_secrets": [],
        "env_suggestions": env_suggestions,
    }


def _detect_database(repo_dir: Path) -> bool:
    """Check for migrations, Prisma, or database drivers."""
    # 1. Directory signals
    db_dirs = [
        repo_dir / "migrations",
        repo_dir / "db" / "migrations",
        repo_dir / "database" / "migrations",
        repo_dir / "alembic",
        repo_dir / "prisma",
        repo_dir / "services" / "api" / "migrations",
    ]
    for d in db_dirs:
        if d.is_dir() and any(d.iterdir()):
            return True

    # 2. File signals
    db_files = [
        repo_dir / "prisma" / "schema.prisma",
        repo_dir / "alembic.ini",
    ]
    for f in db_files:
        if f.is_file():
            return True

    # 3. Content signals in backend files or package.json
    keywords = [
        b"DATABASE_URL",
        b"POSTGRES_URL",
        b"psycopg",
        b"asyncpg",
        b"sqlalchemy",
        b"@prisma/client",
        b"pgx",
        b"typeorm",
    ]
    scan_extensions = {".py", ".ts", ".js", ".go", ".json", ".env.example"}

    for path in repo_dir.rglob("*"):
        # Avoid scanning large build directories
        if any(part in {".git", "node_modules", ".next", ".venv", "__pycache__", "dist", "build"} for part in path.parts):
            continue
        if path.is_file() and path.suffix in scan_extensions:
            try:
                content = path.read_bytes()
                for kw in keywords:
                    if kw in content:
                        return True
            except OSError:
                continue

    return False


def _detect_backend(repo_dir: Path) -> bool:
    """Check for separate Python, Go, or Node backend services."""
    # 1. Directory structure
    backend_dirs = [
        repo_dir / "services" / "api",
        repo_dir / "services" / "backend",
        repo_dir / "backend",
        repo_dir / "server",
    ]
    for d in backend_dirs:
        if d.is_dir():
            return True

    # 2. Root backend files
    backend_files = [
        repo_dir / "main.py",
        repo_dir / "app.py",
        repo_dir / "main.go",
        repo_dir / "Dockerfile",
        repo_dir / "requirements.txt",
    ]
    for f in backend_files:
        if f.is_file():
            return True

    return False


def _detect_env_vars(repo_dir: Path, has_db: bool) -> list[str]:
    """Detect expected environment variables from example env files or code."""
    suggestions: set[str] = set()

    if has_db:
        suggestions.add("DATABASE_URL")

    env_files = [
        repo_dir / ".env.example",
        repo_dir / ".env.sample",
        repo_dir / ".env.template",
    ]

    for env_file in env_files:
        if env_file.is_file():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key = line.split("=", 1)[0].strip()
                        if key:
                            suggestions.add(key)
            except OSError:
                pass

    return sorted(suggestions)

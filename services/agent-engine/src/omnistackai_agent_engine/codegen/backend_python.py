"""Python (FastAPI) backend framework adapter.

Turns an Application IR into a real FastAPI backend as a `GeneratedProject`: Pydantic models from
entities, FastAPI routers from the IR APIs (grouped by resource), a main app with a health endpoint,
config, and packaging files. Pure and deterministic — nothing is installed, built, run, or written to
disk here. Paired with the Next.js web adapter, one IR emits web + backend together.
"""

from __future__ import annotations

import re

from ..application_ir import ApplicationIR, ApiEndpoint, DatabaseStrategy, Entity, FieldType
from .adapter import GenerationTarget
from .auth_guard import PYJWT_REQUIREMENT, needs_auth, python_auth_file
from .data_access import PSYCOPG_REQUIREMENT, python_data_access_files
from .errors import GenerationError
from .files import GeneratedFile, GeneratedProject
from .route_wiring import Op, wire_endpoint
from .schema_sql import render_postgres_schema

_PY_TYPE: dict[FieldType, str] = {
    FieldType.STRING: "str",
    FieldType.TEXT: "str",
    FieldType.UUID: "str",
    FieldType.INT: "int",
    FieldType.FLOAT: "float",
    FieldType.BOOL: "bool",
    FieldType.DATETIME: "datetime",
    FieldType.JSON: "dict",
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "app"


def _segment(path: str) -> str:
    first = path.strip("/").split("/")[0] if path.strip("/") else ""
    module = re.sub(r"\W+", "_", first).strip("_").lower()
    return module or "root"


def _fn_name(method: str, path: str) -> str:
    body = re.sub(r"_+", "_", re.sub(r"\W+", "_", path)).strip("_").lower()
    return f"{method.lower()}_{body}" if body else f"{method.lower()}_root"


def _path_params(path: str) -> list[str]:
    return re.findall(r"\{(\w+)\}", path)


def _models_file(ir: ApplicationIR) -> str:
    needs_datetime = any(f.type is FieldType.DATETIME for e in ir.entities for f in e.fields)
    needs_optional = any(not f.required for e in ir.entities for f in e.fields)
    lines = ["from __future__ import annotations", ""]
    if needs_datetime:
        lines.append("from datetime import datetime")
    if needs_optional:
        lines.append("from typing import Optional")
    lines.append("from pydantic import BaseModel")
    lines.append("")
    if not ir.entities:
        lines.append("# No entities in the IR.")
        return "\n".join(lines) + "\n"
    for entity in ir.entities:
        lines.append("")
        lines.append(f"class {entity.name}(BaseModel):")
        for field in entity.fields:
            py = _PY_TYPE[field.type]
            if field.required:
                lines.append(f"    {field.name}: {py}")
            else:
                lines.append(f"    {field.name}: Optional[{py}] = None")
        if entity.relations:
            rels = ", ".join(f"{r.name}->{r.target_entity}" for r in entity.relations)
            lines.append(f"    # relations: {rels}")
    return "\n".join(lines) + "\n"


def _router_file(segment: str, apis: list[ApiEndpoint], repo_entities: frozenset[str]) -> str:
    wirings = [(api, wire_endpoint(api, repo_entities)) for api in apis]
    tables = sorted({w.table for _, w in wirings if w is not None})
    models_used = sorted({w.entity for _, w in wirings if w is not None and w.op is Op.CREATE})

    seg_needs_auth = any(api.auth for api in apis)
    uses_roles = any(api.required_roles for api in apis)
    uses_auth_only = any(api.auth and not api.required_roles for api in apis)
    fastapi_import = "from fastapi import APIRouter, Depends, HTTPException" if seg_needs_auth else "from fastapi import APIRouter, HTTPException"
    header = [fastapi_import]
    if seg_needs_auth:
        auth_names = [n for n, use in (("require_auth", uses_auth_only), ("require_roles", uses_roles)) if use]
        header.append("")
        header.append(f"from app.auth import {', '.join(auth_names)}")
    if models_used:
        header.append("")
        header += [f"from app.models import {name}" for name in models_used]
    if tables:
        header.append("")
        header += [f"from app.repositories import {table}" for table in tables]
    lines = [*header, "", f'router = APIRouter(tags=["{segment}"])', ""]

    for api, wiring in wirings:
        params = _path_params(api.path)
        auth = "required" if api.auth else "public"
        fn = _fn_name(api.method.value, api.path)
        if api.required_roles:
            role_args = ", ".join(f'"{role}"' for role in api.required_roles)
            guard = f", dependencies=[Depends(require_roles({role_args}))]"
        elif api.auth:
            guard = ", dependencies=[Depends(require_auth)]"
        else:
            guard = ""
        lines.append("")
        lines.append(f'@router.{api.method.value.lower()}("{api.path}"{guard})')
        if wiring is None:
            args = ", ".join(f"{p}: str" for p in params)
            lines.append(f"async def {fn}({args}) -> dict:")
            lines.append(f"    # {api.method.value} {api.path} (auth: {auth}) — scaffold; no unambiguous entity mapping.")
            lines.append('    raise HTTPException(status_code=501, detail="not_implemented")')
        elif wiring.op is Op.LIST:
            lines.append(f"async def {fn}() -> list[dict]:")
            lines.append(f"    return await {wiring.table}.list_{wiring.table}()")
        elif wiring.op is Op.GET:
            lines.append(f"async def {fn}({wiring.id_param}: str) -> dict:")
            lines.append(f"    row = await {wiring.table}.get_{wiring.table}({wiring.id_param})")
            lines.append("    if row is None:")
            lines.append('        raise HTTPException(status_code=404, detail="not_found")')
            lines.append("    return row")
        elif wiring.op is Op.CREATE:
            lines.append(f"async def {fn}(payload: {wiring.entity}) -> dict:")
            lines.append(f"    return await {wiring.table}.create_{wiring.table}(payload.model_dump())")
        else:  # Op.DELETE
            lines.append(f"async def {fn}({wiring.id_param}: str) -> dict:")
            lines.append(f"    deleted = await {wiring.table}.delete_{wiring.table}({wiring.id_param})")
            lines.append("    if not deleted:")
            lines.append('        raise HTTPException(status_code=404, detail="not_found")')
            lines.append('    return {"deleted": True}')
    return "\n".join(lines) + "\n"


def _main_file(ir: ApplicationIR, segments: list[str]) -> str:
    imports = "".join(f"from app.routers import {seg}\n" for seg in segments)
    includes = "".join(f"app.include_router({seg}.router)\n" for seg in segments)
    return (
        "from fastapi import FastAPI\n\n"
        + imports
        + "\n"
        + f'app = FastAPI(title="{_escape(ir.name)}")\n\n'
        + '@app.get("/healthz")\n'
        + "async def healthz() -> dict:\n"
        + '    return {"status": "ok"}\n\n'
        + includes
    )


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class PythonBackendAdapter:
    """Generates a FastAPI (Python) backend from an Application IR."""

    @property
    def target(self) -> GenerationTarget:
        return GenerationTarget.BACKEND_PYTHON

    def generate(self, ir: ApplicationIR) -> GeneratedProject:
        if not isinstance(ir, ApplicationIR):
            raise GenerationError("ir must be an ApplicationIR")

        by_segment: dict[str, list[ApiEndpoint]] = {}
        for api in ir.apis:
            by_segment.setdefault(_segment(api.path), []).append(api)
        segments = sorted(by_segment)

        has_db = bool(ir.entities) and ir.project_strategy.database_strategy is DatabaseStrategy.POSTGRES
        has_auth = needs_auth(ir)
        requirements = "fastapi==0.115.0\nuvicorn[standard]==0.30.6\npydantic==2.9.2\n"
        if has_db:
            requirements += f"{PSYCOPG_REQUIREMENT}\n"
        if has_auth:
            requirements += f"{PYJWT_REQUIREMENT}\n"

        env_example = f"# Backend config placeholders only. Never commit secrets.\nAPP_NAME={ir.name}\nDATABASE_URL=postgresql://localhost:5432/{_slug(ir.name)}\n"
        if has_auth:
            env_example += "JWT_SECRET=\n"

        files: list[GeneratedFile] = [
            GeneratedFile("requirements.txt", requirements),
            GeneratedFile("app/__init__.py", ""),
            GeneratedFile("app/config.py", _CONFIG % (_escape(ir.name),)),
            GeneratedFile("app/models.py", _models_file(ir)),
            GeneratedFile("app/main.py", _main_file(ir, segments)),
            GeneratedFile("app/routers/__init__.py", ""),
            GeneratedFile(".gitignore", "__pycache__/\n.venv/\n*.pyc\n.env\n"),
            GeneratedFile(".env.example", env_example),
            GeneratedFile("README.md", f"# {ir.name} — backend\n\n{ir.description}\n\nGenerated by OmniStackAI from the Application IR.\n\n```\npython -m venv .venv && . .venv/bin/activate\npip install -r requirements.txt\nuvicorn app.main:app --reload\n```\n"),
        ]
        if has_auth:
            files.append(GeneratedFile("app/auth.py", python_auth_file(ir)))

        repo_entities = frozenset(entity.name for entity in ir.entities) if has_db else frozenset()
        for segment in segments:
            files.append(
                GeneratedFile(f"app/routers/{segment}.py", _router_file(segment, by_segment[segment], repo_entities))
            )

        if has_db:
            files.append(GeneratedFile("migrations/0001_init.sql", render_postgres_schema(ir)))
            for path, content in python_data_access_files(ir, _slug(ir.name)):
                files.append(GeneratedFile(path, content))

        return GeneratedProject(self.target.value, tuple(files))


_CONFIG = (
    "import os\n\n\n"
    "class Settings:\n"
    '    app_name = os.getenv("APP_NAME", "%s")\n'
    '    database_url = os.getenv("DATABASE_URL", "postgresql://localhost:5432/app")\n\n\n'
    "settings = Settings()\n"
)

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
from .auth_guard import PYJWT_REQUIREMENT, needs_auth, python_auth_file, python_auth_router_file
from .auth_templates import EMAIL_ENV_EXAMPLE, is_account_route
from .data_access import PSYCOPG_REQUIREMENT, python_data_access_files
from .errors import GenerationError
from .field_validation import filter_fields, parse_field_rules
from .files import GeneratedFile, GeneratedProject
from .openapi import render_openapi_json
from .route_wiring import Op, fk_relations, wire_endpoint
from .workflow_routes import transition_routes
from .schema_sql import render_postgres_schema
from .seed_sql import render_postgres_seed

_PY_TYPE: dict[FieldType, str] = {
    FieldType.STRING: "str",
    FieldType.TEXT: "str",
    FieldType.UUID: "str",
    FieldType.INT: "int",
    FieldType.FLOAT: "float",
    FieldType.BOOL: "bool",
    FieldType.DATETIME: "datetime",
    FieldType.JSON: "dict",
    FieldType.ATTACHMENT: "str",
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


def _py_field_line(field, rules) -> str:
    typ = _PY_TYPE[field.type]
    if rules.enum:
        typ = "Literal[" + ", ".join(repr(value) for value in rules.enum) + "]"
    constraints: list[str] = []
    if rules.max_length is not None and field.type in (FieldType.STRING, FieldType.TEXT):
        constraints.append(f"max_length={rules.max_length}")
    if field.type in (FieldType.INT, FieldType.FLOAT):
        if rules.minimum is not None:
            constraints.append(f"ge={rules.minimum}")
        if rules.maximum is not None:
            constraints.append(f"le={rules.maximum}")
    if field.required:
        if constraints:
            return f"    {field.name}: {typ} = Field({', '.join(constraints)})"
        return f"    {field.name}: {typ}"
    if constraints:
        return f"    {field.name}: Optional[{typ}] = Field(default=None, {', '.join(constraints)})"
    return f"    {field.name}: Optional[{typ}] = None"


def _models_file(ir: ApplicationIR) -> str:
    rules_by_field = {id(f): parse_field_rules(f) for e in ir.entities for f in e.fields}
    # R-502: audit timestamps always use datetime, so always import it when entities exist.
    needs_datetime = bool(ir.entities) or any(f.type is FieldType.DATETIME for e in ir.entities for f in e.fields)
    # R-502: audit fields are Optional, so always need Optional when entities exist.
    needs_optional = bool(ir.entities) or any(not f.required for e in ir.entities for f in e.fields)
    needs_field = any(r.max_length is not None for r in rules_by_field.values())
    needs_literal = any(r.enum for r in rules_by_field.values())

    lines = ["from __future__ import annotations", ""]
    if needs_datetime:
        lines.append("from datetime import datetime")
    typing_imports = [name for name, use in (("Literal", needs_literal), ("Optional", needs_optional)) if use]
    if typing_imports:
        lines.append(f"from typing import {', '.join(typing_imports)}")
    lines.append("from pydantic import BaseModel, Field" if needs_field else "from pydantic import BaseModel")
    lines.append("")
    if not ir.entities:
        lines.append("# No entities in the IR.")
        return "\n".join(lines) + "\n"
    for entity in ir.entities:
        declared_names = {field.name for field in entity.fields}
        lines.append("")
        lines.append(f"class {entity.name}(BaseModel):")
        for field in entity.fields:
            lines.append(_py_field_line(field, rules_by_field[id(field)]))
        # R-502: audit timestamp fields — omitted if the IR already declares them.
        if "created_at" not in declared_names:
            lines.append("    created_at: Optional[datetime] = None")
        if "updated_at" not in declared_names:
            lines.append("    updated_at: Optional[datetime] = None")
        if entity.relations:
            rels = ", ".join(f"{r.name}->{r.target_entity}" for r in entity.relations)
            lines.append(f"    # relations: {rels}")
    return "\n".join(lines) + "\n"


def _router_file(
    segment: str,
    apis: list[ApiEndpoint],
    repo_entities: frozenset[str],
    fk_by_entity: dict[str, tuple[str, ...]] | None = None,
    entities_by_name: dict[str, Entity] | None = None,
    transitions: tuple = (),
) -> str:
    wirings = [(api, wire_endpoint(api, repo_entities, fk_by_entity)) for api in apis]
    tables = sorted({w.table for _, w in wirings if w is not None})
    models_used = sorted({w.entity for _, w in wirings if w is not None and w.op in (Op.CREATE, Op.UPDATE)})

    seg_needs_auth = any(api.auth for api in apis)
    uses_roles = any(api.required_roles for api in apis) or any(r.roles for r in transitions)
    uses_auth_only = any(api.auth and not api.required_roles for api in apis)
    uses_list = any(w is not None and w.op in (Op.LIST, Op.LIST_BY) for _, w in wirings)

    fastapi_imports = ["APIRouter"]
    if seg_needs_auth:
        fastapi_imports.append("Depends")
    fastapi_imports.append("HTTPException")
    if uses_list:
        fastapi_imports.append("Response")
    fastapi_import = f"from fastapi import {', '.join(fastapi_imports)}"
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
            entity_obj = entities_by_name.get(wiring.entity) if entities_by_name else None
            ffields = filter_fields(entity_obj) if entity_obj else []
            fsig = "".join(f", {f.name}: {'bool' if kind == 'bool' else 'str'} | None = None" for f, kind in ffields)
            fcall = "".join(f", {f.name}={f.name}" for f, _ in ffields)
            lines.append(f'async def {fn}(response: Response, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None{fsig}) -> list[dict]:')
            lines.append(f"    total = await {wiring.table}.count_{wiring.table}(q=q{fcall})")
            lines.append('    response.headers["X-Total-Count"] = str(total)')
            lines.append(f"    return await {wiring.table}.list_{wiring.table}(limit=limit, offset=offset, sort=sort, order=order, q=q{fcall})")
        elif wiring.op is Op.LIST_BY:
            entity_obj = entities_by_name.get(wiring.entity) if entities_by_name else None
            ffields = filter_fields(entity_obj) if entity_obj else []
            fsig = "".join(f", {f.name}: {'bool' if kind == 'bool' else 'str'} | None = None" for f, kind in ffields)
            fcall = "".join(f", {f.name}={f.name}" for f, _ in ffields)
            lines.append(f'async def {fn}({wiring.id_param}: str, response: Response, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None{fsig}) -> list[dict]:')
            lines.append(f"    total = await {wiring.table}.count_{wiring.table}_by_{wiring.relation}({wiring.id_param}, q=q{fcall})")
            lines.append('    response.headers["X-Total-Count"] = str(total)')
            lines.append(f"    return await {wiring.table}.list_{wiring.table}_by_{wiring.relation}({wiring.id_param}, limit=limit, offset=offset, sort=sort, order=order, q=q{fcall})")
        elif wiring.op is Op.GET:
            lines.append(f"async def {fn}({wiring.id_param}: str) -> dict:")
            lines.append(f"    row = await {wiring.table}.get_{wiring.table}({wiring.id_param})")
            lines.append("    if row is None:")
            lines.append('        raise HTTPException(status_code=404, detail="not_found")')
            lines.append("    return row")
        elif wiring.op is Op.CREATE:
            lines.append(f"async def {fn}(payload: {wiring.entity}) -> dict:")
            lines.append(f"    return await {wiring.table}.create_{wiring.table}(payload.model_dump())")
        elif wiring.op is Op.UPDATE:
            lines.append(f"async def {fn}({wiring.id_param}: str, payload: {wiring.entity}) -> dict:")
            lines.append(f"    row = await {wiring.table}.update_{wiring.table}({wiring.id_param}, payload.model_dump())")
            lines.append("    if row is None:")
            lines.append('        raise HTTPException(status_code=404, detail="not_found")')
            lines.append("    return row")
        else:  # Op.DELETE
            lines.append(f"async def {fn}({wiring.id_param}: str) -> dict:")
            lines.append(f"    deleted = await {wiring.table}.delete_{wiring.table}({wiring.id_param})")
            lines.append("    if not deleted:")
            lines.append('        raise HTTPException(status_code=404, detail="not_found")')
            lines.append('    return {"deleted": True}')

    # R-566: the lifecycle transitions. Refused here rather than merely hidden in the interface —
    # not showing a courier the "accept" button is presentation; refusing the request is the rule.
    for route in transitions:
        role_args = ", ".join(f'"{role}"' for role in route.roles)
        guard = f", dependencies=[Depends(require_roles({role_args}))]" if role_args else ""
        allowed = route.transition.sources or route.workflow.states
        lines.append("")
        lines.append(f'@router.post("{route.path}"{guard})')
        lines.append(f"async def {route.function}({route.id_param}: str) -> dict:")
        lines.append(f"    row = await {route.table}.get_{route.table}({route.id_param})")
        lines.append("    if row is None:")
        lines.append('        raise HTTPException(status_code=404, detail="not_found")')
        lines.append(f"    allowed = {tuple(allowed)!r}")
        lines.append(f'    if row.get("{route.workflow.field}") not in allowed:')
        lines.append("        raise HTTPException(")
        lines.append("            status_code=409,")
        lines.append(
            f'            detail=f"cannot {route.transition.name} from {{row.get(\'{route.workflow.field}\')}};'
            f' allowed from: {{\', \'.join(allowed)}}",'
        )
        lines.append("        )")
        lines.append(
            f'    return await {route.table}.set_{route.table}_{route.workflow.field}'
            f'({route.id_param}, "{route.transition.to}")'
        )
    return "\n".join(lines) + "\n"


def _main_file(ir: ApplicationIR, segments: list[str], has_auth: bool = False) -> str:
    imports = "".join(f"from app.routers import {seg}\n" for seg in segments)
    includes = "".join(f"app.include_router({seg}.router)\n" for seg in segments)
    auth_import = "from app.routers import auth\n" if has_auth else ""
    auth_include = 'app.include_router(auth.router, prefix="/auth", tags=["auth"])\n' if has_auth else ""
    return (
        "import os\n"
        "from fastapi import FastAPI\n"
        "from fastapi.middleware.cors import CORSMiddleware\n\n"
        + auth_import
        + imports
        + "\n"
        + f'app = FastAPI(title="{_escape(ir.name)}")\n\n'
        + 'cors_origin = os.getenv("CORS_ALLOWED_ORIGIN", "*")\n'
        + "app.add_middleware(\n"
        + "    CORSMiddleware,\n"
        + '    allow_origins=[cors_origin] if cors_origin != "*" else ["*"],\n'
        + "    allow_credentials=True,\n"
        + '    allow_methods=["*"],\n'
        + '    allow_headers=["*"],\n'
        + '    expose_headers=["X-Total-Count"],\n'
        + ")\n\n"
        + '@app.get("/healthz")\n'
        + "async def healthz() -> dict:\n"
        + '    return {"status": "ok"}\n\n'
        + auth_include
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

        has_db = bool(ir.entities) and ir.project_strategy.database_strategy is DatabaseStrategy.POSTGRES
        has_auth = needs_auth(ir)

        by_segment: dict[str, list[ApiEndpoint]] = {}
        for api in ir.apis:
            if has_auth and is_account_route(api.path):
                continue  # R-591: the generated account flow owns /auth/*
            by_segment.setdefault(_segment(api.path), []).append(api)
        segments = sorted(by_segment)
        requirements = "fastapi==0.115.0\nuvicorn[standard]==0.30.6\npydantic==2.9.2\n"
        if has_db:
            requirements += f"{PSYCOPG_REQUIREMENT}\n"
        if has_auth:
            requirements += f"{PYJWT_REQUIREMENT}\n"

        env_example = f"# Backend config placeholders only. Never commit secrets.\nAPP_NAME={ir.name}\nDATABASE_URL=postgresql://localhost:5432/{_slug(ir.name)}\nCORS_ALLOWED_ORIGIN=*\n"
        if has_auth:
            env_example += "JWT_SECRET=\n" + EMAIL_ENV_EXAMPLE
        env_example += "STORAGE_ENDPOINT=http://localhost:9000\nSTORAGE_BUCKET=uploads\nSTORAGE_ACCESS_KEY=minioadmin\nSTORAGE_SECRET_KEY=minioadmin\n"

        files: list[GeneratedFile] = [
            GeneratedFile("requirements.txt", requirements),
            GeneratedFile("app/__init__.py", ""),
            GeneratedFile("app/config.py", _CONFIG % (_escape(ir.name),)),
            GeneratedFile("app/models.py", _models_file(ir)),
            GeneratedFile("app/main.py", _main_file(ir, segments, has_auth=has_auth)),
            GeneratedFile("app/routers/__init__.py", ""),
            GeneratedFile(".gitignore", "__pycache__/\n.venv/\n*.pyc\n.env\n"),
            GeneratedFile(".env.example", env_example),
            GeneratedFile("README.md", f"# {ir.name} — backend\n\n{ir.description}\n\nGenerated by OmniStackAI from the Application IR.\n\n```\npython -m venv .venv && . .venv/bin/activate\npip install -r requirements.txt\nuvicorn app.main:app --reload\n```\n"),
        ]
        if has_auth:
            files.append(GeneratedFile("app/auth.py", python_auth_file(ir)))
            files.append(GeneratedFile("app/routers/auth.py", python_auth_router_file(ir)))

        repo_entities = frozenset(entity.name for entity in ir.entities) if has_db else frozenset()
        fk_by_entity = fk_relations(ir) if has_db else None
        entities_by_name = {entity.name: entity for entity in ir.entities} if has_db else None
        for segment in segments:
            files.append(
                GeneratedFile(
                    f"app/routers/{segment}.py",
                    _router_file(
                        segment,
                        by_segment[segment],
                        repo_entities,
                        fk_by_entity,
                        entities_by_name,
                        # Matched on the path's first segment, which is what names the
                        # router file — `posts.py` holds `/posts/...`, and the table is
                        # the singular `post`.
                        tuple(
                            r
                            for r in transition_routes(ir)
                            if r.path.strip("/").split("/")[0] == segment
                        ),
                    ),
                )
            )

        if has_db:
            files.append(GeneratedFile("migrations/0001_init.sql", render_postgres_schema(ir)))
            for path, content in python_data_access_files(ir, _slug(ir.name)):
                files.append(GeneratedFile(path, content))
            seed = render_postgres_seed(ir)
            if seed:
                files.append(GeneratedFile("migrations/0002_seed.sql", seed))

        if ir.apis:
            files.append(GeneratedFile("openapi.json", render_openapi_json(ir)))

        return GeneratedProject(self.target.value, tuple(files))


_CONFIG = (
    "import os\n\n\n"
    "class Settings:\n"
    '    app_name = os.getenv("APP_NAME", "%s")\n'
    '    database_url = os.getenv("DATABASE_URL", "postgresql://localhost:5432/app")\n\n\n'
    "settings = Settings()\n"
)

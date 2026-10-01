"""Python (FastAPI) backend framework adapter.

Turns an Application IR into a real FastAPI backend as a `GeneratedProject`: Pydantic models from
entities, FastAPI routers from the IR APIs (grouped by resource), a main app with a health endpoint,
config, and packaging files. Pure and deterministic — nothing is installed, built, run, or written to
disk here. Paired with the Next.js web adapter, one IR emits web + backend together.
"""

from __future__ import annotations

import re

from .ownership_wiring import owned_transition, owner_scoped_op, rules_by_entity
from ..application_ir.money import money_of
from .money_python import MONEY_ENV_EXAMPLE, python_money_file
from ..application_ir.jobs import jobs_of
from .jobs_python import JOBS_ENV_EXAMPLE, python_jobs_file
from ..application_ir.realtime import realtime_of
from .realtime_python import python_realtime_file
from ..application_ir import ApplicationIR, ApiEndpoint, DatabaseStrategy, Entity, FieldType, RelationKind
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
    FieldType.RICH_TEXT: "str",
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
    # PC-104: rich text is cleaned by a validator on every create and update.
    from .rich_text import has_rich_text, python_validator, rich_fields

    pydantic_names = ["BaseModel", *(["Field"] if needs_field else []), *(["field_validator"] if has_rich_text(ir) else [])]
    lines.append(f"from pydantic import {', '.join(pydantic_names)}")
    if has_rich_text(ir):
        lines.append("")
        lines.append("from app.rich_text import clean_html")
    lines.append("")
    if not ir.entities:
        lines.append("# No entities in the IR.")
        return "\n".join(lines) + "\n"
    from ..application_ir.workflow import workflows_of

    lifecycle_fields = {(w.entity, w.field) for w in workflows_of(ir)}
    for entity in ir.entities:
        declared_names = {field.name for field in entity.fields}
        lines.append("")
        lines.append(f"class {entity.name}(BaseModel):")
        for field in entity.fields:
            if field.name == "id":
                # R-590 (found live): the database assigns the id (DEFAULT gen_random_uuid()), but the
                # model required one in every request body, so a create through the API answered 422
                # to every client that did not invent its own id — the web and mobile apps included.
                lines.append("    id: Optional[str] = None  # assigned by the database")
                continue
            if field.name in ("created_at", "updated_at"):
                # PC-100, found live: a plan that declares its own created_at made every create
                # body require one, although the database fills it in and inserts never write it.
                lines.append(f"    {field.name}: Optional[datetime] = None  # set by the database")
                continue
            if (entity.name, field.name) in lifecycle_fields:
                # R-590: returned, never required or written from a request — only a transition
                # moves it, so a create/update body without it is valid and one with it changes nothing.
                lines.append(f"    {field.name}: Optional[str] = None  # lifecycle; changed by its transitions")
                continue
            lines.append(_py_field_line(field, rules_by_field[id(field)]))
        # R-502: audit timestamp fields — omitted if the IR already declares them.
        if "created_at" not in declared_names:
            lines.append("    created_at: Optional[datetime] = None")
        if "updated_at" not in declared_names:
            lines.append("    updated_at: Optional[datetime] = None")
        # PC-100: a foreign key the request may set (Pydantic drops a field the model lacks).
        for relation in entity.relations:
            if relation.kind in (RelationKind.MANY_TO_ONE, RelationKind.ONE_TO_ONE) and f"{relation.name}_id" not in declared_names:
                lines.append(f"    {relation.name}_id: Optional[str] = None")
        if entity.relations:
            rels = ", ".join(f"{r.name}->{r.target_entity}" for r in entity.relations)
            lines.append(f"    # relations: {rels}")
        if rich_fields(entity):
            lines.extend(python_validator(rich_fields(entity)))
    return "\n".join(lines) + "\n"


def _assignee_arg(rule) -> str:
    return f', "{rule.assignee}"' if rule is not None and rule.assignee else ""


def _router_file(
    segment: str,
    apis: list[ApiEndpoint],
    repo_entities: frozenset[str],
    fk_by_entity: dict[str, tuple[str, ...]] | None = None,
    entities_by_name: dict[str, Entity] | None = None,
    transitions: tuple = (),
    rules: dict | None = None,
) -> str:
    rules = rules or {}
    wirings = [(api, wire_endpoint(api, repo_entities, fk_by_entity)) for api in apis]
    tables = sorted({w.table for _, w in wirings if w is not None} | {r.table for r in transitions})
    models_used = sorted({w.entity for _, w in wirings if w is not None and w.op in (Op.CREATE, Op.UPDATE)})

    # R-570: per endpoint - its ownership rule, whether it really needs sign-in (an owner-scoped
    # read does, whatever the plan said: the rule wins), and whether the handler needs the
    # caller's claims (to record a creator, or to check whose row it is).
    plans = []
    for api, wiring in wirings:
        rule = rules.get(wiring.entity) if wiring is not None else None
        scoped = owner_scoped_op(rule, wiring)
        auth = api.auth or scoped
        # PC-111: with an assignee, a create or change also needs to know whether the caller may assign.
        assigns = rule is not None and rule.assignee is not None and wiring.op in (Op.CREATE, Op.UPDATE)
        claims = wiring is not None and auth and (wiring.op is Op.CREATE or scoped or assigns)
        plans.append((api, wiring, rule, scoped, auth, claims))
    owned_transitions = [(route, owned_transition(rules, route)) for route in transitions]

    seg_needs_auth = any(auth for *_, auth, _ in plans) or any(r.roles for r in transitions) \
        or any(rule for _, rule in owned_transitions)
    uses_roles = any(api.required_roles for api in apis) or any(r.roles for r in transitions)
    uses_auth_only = any(auth and not api.required_roles for api, _, _, _, auth, _ in plans) \
        or any(rule for _, rule in owned_transitions)
    uses_list = any(w is not None and w.op in (Op.LIST, Op.LIST_BY) for _, w in wirings)
    owner_helpers = [
        name
        for name, use in (
            ("can_touch", any(scoped and w.op is not Op.LIST and w.op is not Op.LIST_BY for _, w, _, scoped, _, _ in plans)
             or any(rule for _, rule in owned_transitions)),
            ("owner_of", any(claims and w.op is Op.CREATE for _, w, _, _, _, claims in plans)),
            ("owner_scope", any(scoped and w.op in (Op.LIST, Op.LIST_BY) for _, w, _, scoped, _, _ in plans)),
            ("sees_all", any(r is not None and r.assignee and claims and w.op in (Op.CREATE, Op.UPDATE)
                             for _, w, r, _, _, claims in plans)),
        )
        if use
    ]

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
        header.append(f"from app.auth import {', '.join(auth_names + owner_helpers)}")
    if models_used:
        header.append("")
        header += [f"from app.models import {name}" for name in models_used]
    if tables:
        header.append("")
        # PC-100, found live: `from app.repositories import order` was shadowed by the list
        # handler's own `order` (sort direction) parameter, so GET /orders answered 500 for every
        # app with an Order entity. Each repository is imported under a name no parameter can take.
        header += [f"from app.repositories import {table} as {table}_repo" for table in tables]
    lines = [*header, "", f'router = APIRouter(tags=["{segment}"])', ""]

    for api, wiring, rule, scoped, auth_required, wants_claims in plans:
        params = _path_params(api.path)
        auth = "required" if auth_required else "public"
        fn = _fn_name(api.method.value, api.path)
        if api.required_roles:
            role_args = ", ".join(f'"{role}"' for role in api.required_roles)
            dependency = f"require_roles({role_args})"
        elif auth_required:
            dependency = "require_auth"
        else:
            dependency = ""
        guard = f", dependencies=[Depends({dependency})]" if dependency and not wants_claims else ""
        claims_param = f"claims: dict = Depends({dependency})" if wants_claims else ""
        bypass = repr(rule.bypass_roles) if rule is not None else "()"
        lines.append("")
        lines.append(f'@router.{api.method.value.lower()}("{api.path}"{guard})')
        if wiring is None:
            args = ", ".join(f"{p}: str" for p in params)
            lines.append(f"async def {fn}({args}) -> dict:")
            lines.append(f"    # {api.method.value} {api.path} (auth: {auth}) — scaffold; no unambiguous entity mapping.")
            lines.append('    raise HTTPException(status_code=501, detail="not_implemented")')
        elif wiring.op in (Op.LIST, Op.LIST_BY):
            entity_obj = entities_by_name.get(wiring.entity) if entities_by_name else None
            ffields = filter_fields(entity_obj) if entity_obj else []
            fsig = "".join(f", {f.name}: {'bool' if kind == 'bool' else 'str'} | None = None" for f, kind in ffields)
            fcall = "".join(f", {f.name}={f.name}" for f, _ in ffields)
            if scoped:
                fsig += f", {claims_param}"
                fcall += ", owner=owner"
            if wiring.op is Op.LIST:
                lines.append(f'async def {fn}(response: Response, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None{fsig}) -> list[dict]:')
                count_call = f"{wiring.table}_repo.count_{wiring.table}(q=q{fcall})"
                list_call = f"{wiring.table}_repo.list_{wiring.table}(limit=limit, offset=offset, sort=sort, order=order, q=q{fcall})"
            else:
                lines.append(f'async def {fn}({wiring.id_param}: str, response: Response, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None{fsig}) -> list[dict]:')
                count_call = f"{wiring.table}_repo.count_{wiring.table}_by_{wiring.relation}({wiring.id_param}, q=q{fcall})"
                list_call = f"{wiring.table}_repo.list_{wiring.table}_by_{wiring.relation}({wiring.id_param}, limit=limit, offset=offset, sort=sort, order=order, q=q{fcall})"
            if scoped:
                lines.append(f"    owner = owner_scope(claims, {bypass})  # R-570: only the user's own, unless they see all")
            lines.append(f"    total = await {count_call}")
            lines.append('    response.headers["X-Total-Count"] = str(total)')
            lines.append(f"    return await {list_call}")
        elif wiring.op is Op.GET:
            extra = f", {claims_param}" if scoped else ""
            lines.append(f"async def {fn}({wiring.id_param}: str{extra}) -> dict:")
            lines.append(f"    row = await {wiring.table}_repo.get_{wiring.table}({wiring.id_param})")
            if scoped:
                lines.append(f"    if row is None or not can_touch(row, claims, {bypass}{_assignee_arg(rule)}):  # R-570: not theirs is not found")
            else:
                lines.append("    if row is None:")
            lines.append('        raise HTTPException(status_code=404, detail="not_found")')
            lines.append("    return row")
        elif wiring.op is Op.CREATE:
            extra = f", {claims_param}" if wants_claims else ""
            creator = ", created_by=owner_of(claims)" if wants_claims else ""
            lines.append(f"async def {fn}(payload: {wiring.entity}{extra}) -> dict:")
            if wants_claims:
                lines.append("    # R-570: who created it comes from the verified token, never from the request.")
            if wants_claims and rule is not None and rule.assignee:
                lines.append("    data = payload.model_dump()")
                lines.append(f"    if not sees_all(claims, {bypass}):")
                lines.append(f'        data["{rule.assignee}"] = None  # PC-111: only {", ".join(rule.bypass_roles)} assign')
                lines.append(f"    return await {wiring.table}_repo.create_{wiring.table}(data{creator})")
            else:
                lines.append(f"    return await {wiring.table}_repo.create_{wiring.table}(payload.model_dump(){creator})")
        else:  # UPDATE or DELETE
            extra = f", {claims_param}" if wants_claims else ""
            payload = f", payload: {wiring.entity}" if wiring.op is Op.UPDATE else ""
            lines.append(f"async def {fn}({wiring.id_param}: str{payload}{extra}) -> dict:")
            assigns = wiring.op is Op.UPDATE and wants_claims and rule is not None and rule.assignee
            if scoped or assigns:
                # Deleting stays the creator's (PC-111): the assignee may change a record, not remove it.
                assignee = _assignee_arg(rule) if wiring.op is Op.UPDATE else ""
                lines.append(f"    current = await {wiring.table}_repo.get_{wiring.table}({wiring.id_param})")
                if scoped:
                    lines.append(f"    if current is None or not can_touch(current, claims, {bypass}{assignee}):  # R-570: only the owner")
                else:
                    lines.append("    if current is None:")
                lines.append('        raise HTTPException(status_code=404, detail="not_found")')
            if wiring.op is Op.UPDATE:
                if assigns:
                    lines.append("    data = payload.model_dump()")
                    lines.append(f"    if not sees_all(claims, {bypass}):")
                    lines.append(f'        data["{rule.assignee}"] = current.get("{rule.assignee}")  # PC-111: the assignment is not theirs to change')
                    lines.append(f"    row = await {wiring.table}_repo.update_{wiring.table}({wiring.id_param}, data)")
                else:
                    lines.append(f"    row = await {wiring.table}_repo.update_{wiring.table}({wiring.id_param}, payload.model_dump())")
                lines.append("    if row is None:")
                lines.append('        raise HTTPException(status_code=404, detail="not_found")')
                lines.append("    return row")
            else:
                lines.append(f"    deleted = await {wiring.table}_repo.delete_{wiring.table}({wiring.id_param})")
                lines.append("    if not deleted:")
                lines.append('        raise HTTPException(status_code=404, detail="not_found")')
                lines.append('    return {"deleted": True}')

    # R-566: the lifecycle transitions. Refused here rather than merely hidden in the interface —
    # not showing a courier the "accept" button is presentation; refusing the request is the rule.
    for route, owned in owned_transitions:
        role_args = ", ".join(f'"{role}"' for role in route.roles)
        guard = f", dependencies=[Depends(require_roles({role_args}))]" if role_args else ""
        allowed = route.transition.sources or route.workflow.states
        lines.append("")
        lines.append(f'@router.post("{route.path}"{guard})')
        if owned is not None:
            # R-570: a transition open to any role on an owner-scoped entity is the owner's to make;
            # PC-111: one granted to a role is made only on records assigned to the caller.
            guard_fn = f"require_roles({role_args})" if role_args else "require_auth"
            lines[-1] = f'@router.post("{route.path}")'
            lines.append(f"async def {route.function}({route.id_param}: str, claims: dict = Depends({guard_fn})) -> dict:")
        else:
            lines.append(f"async def {route.function}({route.id_param}: str) -> dict:")
        lines.append(f"    row = await {route.table}_repo.get_{route.table}({route.id_param})")
        if owned is not None:
            # The assignee makes the moves granted to their role; a move open to no role is the creator's.
            assignee = _assignee_arg(owned) if route.roles else ""
            lines.append(f"    if row is None or not can_touch(row, claims, {owned.bypass_roles!r}{assignee}):")
        else:
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
            f'    return await {route.table}_repo.set_{route.table}_{route.workflow.field}'
            f'({route.id_param}, "{route.transition.to}")'
        )
    return "\n".join(lines) + "\n"


def _main_file(ir: ApplicationIR, segments: list[str], has_auth: bool = False, has_db: bool = False,
               money: bool = False, jobs: bool = False, realtime: bool = False) -> str:
    imports = "".join(f"from app.routers import {seg}\n" for seg in segments)
    includes = "".join(f"app.include_router({seg}.router)\n" for seg in segments)
    if money:  # R-567
        imports += "from app import money\n"
        includes += "app.include_router(money.router)\n"
    lifespan, lifespan_arg = "", ""
    # R-568: the scheduler, R-569: the live listener - each starts and stops with the app.
    background = [name for name, wanted in (("jobs", jobs), ("realtime", realtime)) if wanted]
    for name in background:
        imports += f"from app import {name}\n"
        includes += f"app.include_router({name}.router)\n"
    if background:
        lifespan = (
            "\n@asynccontextmanager\n"
            "async def lifespan(_app: FastAPI):\n"
            + "".join(f"    await {name}.start()\n" for name in background)
            + "    yield\n"
            + "".join(f"    await {name}.stop()\n" for name in background)
            + "\n"
        )
        lifespan_arg = ", lifespan=lifespan"
    auth_import = "from app.routers import auth\n" if has_auth else ""
    auth_include = 'app.include_router(auth.router, prefix="/auth", tags=["auth"])\n' if has_auth else ""
    return (
        "import os\n"
        + ("from contextlib import asynccontextmanager\n" if background else "")
        + "from fastapi import FastAPI\n"
        "from fastapi.middleware.cors import CORSMiddleware\n\n"
        + auth_import
        + imports
        + lifespan
        + "\n"
        + f'app = FastAPI(title="{_escape(ir.name)}"{lifespan_arg})\n\n'
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
        + (_DATA_ERROR_HANDLER if has_db else "")
        + auth_include
        + includes
    )


#: PC-004: a value the database cannot read — `GET /posts/not-a-uuid`, a malformed foreign key in a
#: body — used to surface as an unexplained 500. It is the caller's mistake, so it answers 422.
_DATA_ERROR_HANDLER = (
    "from fastapi import Request\n"
    "from fastapi.responses import JSONResponse\n"
    "from psycopg import errors as _pg_errors\n\n\n"
    "@app.exception_handler(_pg_errors.DataError)\n"
    "async def _invalid_value(request: Request, exc: _pg_errors.DataError) -> JSONResponse:\n"
    '    return JSONResponse(status_code=422, content={"detail": "invalid_value"})\n\n\n'
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
        # PC-102: an app with attachment fields gets /uploads and /files (unless the plan owns them).
        from .upload_policy import has_uploads
        from .uploads import PYTHON_UPLOAD_REQUIREMENTS, python_upload_files

        uploads = has_uploads(ir) and not ({"uploads", "files"} & set(segments))
        requirements = "fastapi==0.115.0\nuvicorn[standard]==0.30.6\npydantic==2.9.2\n"
        if uploads:
            requirements += "".join(f"{line}\n" for line in PYTHON_UPLOAD_REQUIREMENTS)
        from .rich_text import PYTHON_REQUIREMENT, has_rich_text, python_module

        if has_rich_text(ir):
            requirements += f"{PYTHON_REQUIREMENT}\n"
        if has_db:
            requirements += f"{PSYCOPG_REQUIREMENT}\n"
        if has_auth:
            requirements += f"{PYJWT_REQUIREMENT}\n"

        env_example = f"# Backend config placeholders only. Never commit secrets.\nAPP_NAME={ir.name}\nDATABASE_URL=postgresql://localhost:5432/{_slug(ir.name)}\nCORS_ALLOWED_ORIGIN=*\n"
        if has_auth:
            env_example += "JWT_SECRET=\n" + EMAIL_ENV_EXAMPLE
        # PC-102: uploads go to S3-compatible storage (Cloudflare R2, AWS S3) when these are set,
        # else to the local disk. (The MinIO placeholders that stood here were never read.)
        env_example += ("# File storage: leave empty for the local disk.\nSTORAGE_DRIVER=auto\nS3_ENDPOINT=\n"
                        "S3_REGION=\nS3_BUCKET=\nS3_ACCESS_KEY_ID=\nS3_SECRET_ACCESS_KEY=\nLOCAL_STORAGE_DIR=./uploads\n")

        # R-567: money needs the database and sign-in; it runs on the mock provider until keys exist.
        has_money = has_db and has_auth and money_of(ir) is not None
        if has_money:
            env_example += MONEY_ENV_EXAMPLE
        # R-568: scheduled jobs run against the app's database and are watched by its admin.
        has_jobs = has_db and has_auth and jobs_of(ir) is not None
        if has_jobs:
            env_example += JOBS_ENV_EXAMPLE
        has_realtime = has_db and has_auth and realtime_of(ir) is not None  # R-569
        files: list[GeneratedFile] = [
            GeneratedFile("requirements.txt", requirements),
            GeneratedFile("app/__init__.py", ""),
            GeneratedFile("app/config.py", _CONFIG % (_escape(ir.name),)),
            GeneratedFile("app/models.py", _models_file(ir)),
            GeneratedFile("app/main.py", _main_file(ir, [*segments, *(["uploads"] if uploads else [])],
                                                    has_auth=has_auth, has_db=has_db, money=has_money,
                                                    jobs=has_jobs, realtime=has_realtime)),
            GeneratedFile("app/routers/__init__.py", ""),
            GeneratedFile(".gitignore", "__pycache__/\n.venv\n*.pyc\n.env\nuploads/\n"),
            GeneratedFile(".env.example", env_example),
            GeneratedFile("README.md", f"# {ir.name} — backend\n\n{ir.description}\n\nGenerated by OmniStackAI from the Application IR.\n\n```\npython -m venv .venv && . .venv/bin/activate\npip install -r requirements.txt\nuvicorn app.main:app --reload\n```\n"),
        ]
        if uploads:
            files.extend(GeneratedFile(path, content) for path, content in python_upload_files(ir, has_auth))
        if has_rich_text(ir):
            files.append(GeneratedFile("app/rich_text.py", python_module()))
        if has_money:
            files.append(GeneratedFile("app/money.py", python_money_file(ir)))
        if has_jobs:
            files.append(GeneratedFile("app/jobs.py", python_jobs_file(ir)))
        if has_realtime:
            files.append(GeneratedFile("app/realtime.py", python_realtime_file(ir)))
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
                        rules_by_entity(ir),
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

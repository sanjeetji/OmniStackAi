"""Map an IR API endpoint to a repository operation — deterministically and conservatively.

Only the unambiguous CRUD shapes are wired to the R-239 data-access layer; anything else stays a clearly
labelled scaffold (so we never generate plausible-but-wrong behaviour). The endpoint's entity is taken
from its ``response_schema`` (else ``request_schema``); the operation is inferred from the HTTP method
and path shape:

- GET with no path params, entity known           -> LIST
- GET whose last path segment is a param           -> GET (by that id)
- POST with a request_schema entity and no params  -> CREATE
- DELETE whose last path segment is a param         -> DELETE (by that id)

Everything else returns None (leave the handler as a scaffold).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from ..application_ir import ApiEndpoint
from .schema_sql import table_name


class Op(StrEnum):
    LIST = "list"
    GET = "get"
    CREATE = "create"
    DELETE = "delete"


@dataclass(frozen=True, slots=True)
class Wiring:
    op: Op
    entity: str          # entity name (PascalCase, as in the IR / model)
    table: str           # snake_case table + repository/module name
    id_param: str | None  # path parameter used by GET/DELETE


def wire_endpoint(api: ApiEndpoint, repo_entities: frozenset[str]) -> Wiring | None:
    entity = api.response_schema or api.request_schema
    if not entity or entity not in repo_entities:
        return None

    params = re.findall(r"\{(\w+)\}", api.path)
    segments = [seg for seg in api.path.strip("/").split("/") if seg]
    last_is_param = bool(segments) and segments[-1].startswith("{")
    method = api.method.value
    table = table_name(entity)

    if method == "GET" and not params:
        return Wiring(Op.LIST, entity, table, None)
    if method == "GET" and last_is_param and len(params) == 1:
        return Wiring(Op.GET, entity, table, params[0])
    if method == "POST" and api.request_schema == entity and not params:
        return Wiring(Op.CREATE, entity, table, None)
    if method == "DELETE" and last_is_param and len(params) == 1:
        return Wiring(Op.DELETE, entity, table, params[0])
    return None

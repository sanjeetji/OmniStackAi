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

from ..application_ir import ApplicationIR, ApiEndpoint, RelationKind
from .schema_sql import table_name

_FK_KINDS = frozenset({RelationKind.MANY_TO_ONE, RelationKind.ONE_TO_ONE})


class Op(StrEnum):
    LIST = "list"
    GET = "get"
    CREATE = "create"
    UPDATE = "update"  # PATCH /entities/{id} — partial update (R-253)
    DELETE = "delete"
    LIST_BY = "list_by"  # parent-scoped list: a sub-collection filtered by a foreign-key relation


@dataclass(frozen=True, slots=True)
class Wiring:
    op: Op
    entity: str          # entity name (PascalCase, as in the IR / model)
    table: str           # snake_case table + repository/module name
    id_param: str | None  # path parameter used by GET/DELETE/LIST_BY
    relation: str | None = None  # FK relation name used by LIST_BY (filters <relation>_id)


def fk_relations(ir: ApplicationIR) -> dict[str, tuple[str, ...]]:
    """Map each entity name to the names of its foreign-key relations (many_to_one / one_to_one)."""

    return {
        entity.name: tuple(rel.name for rel in entity.relations if rel.kind in _FK_KINDS)
        for entity in ir.entities
    }


def wire_endpoint(
    api: ApiEndpoint,
    repo_entities: frozenset[str],
    fk_by_entity: dict[str, tuple[str, ...]] | None = None,
) -> Wiring | None:
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
    if method == "PATCH" and api.request_schema == entity and last_is_param and len(params) == 1:
        return Wiring(Op.UPDATE, entity, table, params[0])
    if method == "DELETE" and last_is_param and len(params) == 1:
        return Wiring(Op.DELETE, entity, table, params[0])
    # Sub-collection list: GET /<parents>/{parentId}/<children>, child has exactly one FK relation.
    if method == "GET" and not last_is_param and len(params) == 1 and fk_by_entity is not None:
        relations = fk_by_entity.get(entity, ())
        if len(relations) == 1:
            return Wiring(Op.LIST_BY, entity, table, params[0], relation=relations[0])
    return None

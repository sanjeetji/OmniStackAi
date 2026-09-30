"""PC-101: every record a form must point at can be listed, so the form can pick it.

Seen in PC-102: the planner declared a job posting's required ``recruiter_id`` and a Recruiter
entity, but gave Recruiter no API. No form could fill the field - the admin console's picker loads
the target's list, and there was none - so no job posting could ever be created. Deterministically,
after planning: an entity that another entity refers to (a foreign-key relation, or a field named
``<entity>_id``) and that has no list endpoint gets the plain ones - list, read and create - so the
picker has something to load and the admin console can add the first one. Reading follows the
app's sign-in; creating is for the admin where the app has one (the admin passes every role check).

Also seen in PC-102: an entity whose only create was nested (``POST /job_postings/{id}/applications``)
had no create any backend wires and no "New" in the admin console. It gets a plain create, under the
same roles as the nested one; the parent is a foreign key in the body, picked in the form.
"""

from __future__ import annotations

import re
from dataclasses import replace

from ..application_ir import ApiEndpoint, ApplicationIR, HttpMethod, RelationKind
from .auth_guard import needs_auth
from .route_wiring import Op, fk_relations, wire_endpoint
from .schema_sql import table_name

_FK_KINDS = frozenset({RelationKind.MANY_TO_ONE, RelationKind.ONE_TO_ONE})


def _plural(word: str) -> str:
    if word.endswith("y") and word[-2:-1] not in "aeiou":
        return word[:-1] + "ies"
    if word.endswith(("s", "x", "ch", "sh")):
        return word + "es"
    return word + "s"


def referenced_entities(ir: ApplicationIR) -> list[str]:
    """Entities some other entity points at, in plan order."""
    names = {entity.name for entity in ir.entities}
    by_table = {table_name(entity.name): entity.name for entity in ir.entities}
    wanted: list[str] = []
    for entity in ir.entities:
        targets = [rel.target_entity for rel in entity.relations if rel.kind in _FK_KINDS]
        targets += [by_table[f.name[:-3]] for f in entity.fields if f.name.endswith("_id") and f.name[:-3] in by_table]
        for target in targets:
            if target in names and target != entity.name and target not in wanted:
                wanted.append(target)
    return wanted


def _nested_creates(ir: ApplicationIR) -> dict[str, ApiEndpoint]:
    """Entity -> its first create that sits under a parent's path (POST /parents/{id}/children)."""
    found: dict[str, ApiEndpoint] = {}
    for api in ir.apis:
        if api.method is HttpMethod.POST and api.request_schema and "{" in api.path:
            found.setdefault(api.request_schema, api)
    return found


def with_reachable_references(ir: ApplicationIR) -> ApplicationIR:
    repo = frozenset(entity.name for entity in ir.entities)
    fks = fk_relations(ir)
    ops: dict[str, set[Op]] = {}
    for api in ir.apis:
        wiring = wire_endpoint(api, repo, fks)
        if wiring is not None:
            ops.setdefault(wiring.entity, set()).add(wiring.op)
    auth = needs_auth(ir)
    writer = ("admin",) if auth and any(role.id == "admin" for role in ir.roles) else ()
    taken = {(api.method.value, api.path) for api in ir.apis}
    added: list[ApiEndpoint] = []
    nested = _nested_creates(ir)
    targets = referenced_entities(ir) + [name for name in nested if name not in referenced_entities(ir)]
    for target in targets:
        has = ops.get(target, set())
        if Op.LIST in has and (Op.CREATE in has or target not in nested):
            continue
        # The account flow owns /auth/* and its users; a plan's User is not re-exposed here.
        if auth and target.lower() in ("user", "account"):
            continue
        base = f"/{_plural(table_name(target))}"
        # PC-101, seen live: a plan with /projects/{projectId}/tasks got /projects/{id} beside it,
        # and Next refused two slug names at one level. Use the name the plan already uses there.
        param = next((m.group(1) for api in ir.apis
                      if (m := re.match(re.escape(base) + r"/\{(\w+)\}", api.path))), "id")
        item = f"{base}/{{{param}}}"
        wanted = [] if Op.LIST in has else [ApiEndpoint(HttpMethod.GET, base, auth=auth, response_schema=target)]
        if Op.GET not in has:
            wanted.append(ApiEndpoint(HttpMethod.GET, item, auth=auth, response_schema=target))
        if Op.CREATE not in has:
            model = nested.get(target)
            wanted.append(ApiEndpoint(HttpMethod.POST, base, auth=model.auth if model else auth, request_schema=target,
                                      response_schema=target,
                                      required_roles=model.required_roles if model else writer))
        # Edits and deletes that also exist only under the parent get plain ones too, same roles.
        for method, op in ((HttpMethod.PUT, Op.UPDATE), (HttpMethod.PATCH, Op.UPDATE), (HttpMethod.DELETE, Op.DELETE)):
            parent = nested.get(target)
            under = next((a for a in ir.apis if parent is not None and a.method is method
                          and re.fullmatch(re.escape(parent.path) + r"/\{\w+\}", a.path)), None)
            if under is not None and op not in has and not any(w.method is method for w in wanted if "{" in w.path):
                has = has | {op}
                wanted.append(ApiEndpoint(method, item, auth=under.auth, required_roles=under.required_roles,
                                          request_schema=target if method is not HttpMethod.DELETE else None,
                                          response_schema=target))
        added += [api for api in wanted if (api.method.value, api.path) not in taken]
    if not added:
        return ir
    return replace(ir, apis=ir.apis + tuple(added))


def with_detail_screens(ir: ApplicationIR) -> ApplicationIR:
    """A listed entity gets a page to read one record in full (PC-101).

    Seen in PC-050 to PC-104: a blog planned with an article list and no article page showed each
    article cut short, with nowhere to read the rest. The list pages already link to a detail
    screen when the plan has one; this adds the screen the plan left out.
    """
    from ..application_ir import Screen
    from .nextjs import _get_ops_by_entity, _match_entity, _screen_intent

    ops = _get_ops_by_entity(ir)
    shown: dict[str, str] = {}  # entity -> the role of its first list screen
    has_detail: set[str] = set()
    for screen in ir.screens:
        entity = _match_entity(screen, ir)
        if entity is None:
            continue
        intent = _screen_intent(screen)
        if intent == "collection":
            shown.setdefault(entity.name, screen.role)
        elif intent == "detail":
            has_detail.add(entity.name)
    ids = {screen.id for screen in ir.screens}
    added = []
    for name, role in shown.items():
        screen_id = f"{table_name(name)}_detail"
        # The detail template reads the record by id, or finds it in the list when there is no GET.
        if name in has_detail or not ops.get(name, set()) & {Op.GET, Op.LIST} or screen_id in ids:
            continue
        screen = Screen(id=screen_id, role=role, components=("detail",))
        if (entity := _match_entity(screen, ir)) is None or entity.name != name:
            continue  # the new screen must resolve to its entity, or it would be a wrong page
        added.append(screen)
    if not added:
        return ir
    return replace(ir, screens=ir.screens + tuple(added))

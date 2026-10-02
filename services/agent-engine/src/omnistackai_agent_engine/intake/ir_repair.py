"""Repair the two mistakes models make most, instead of rejecting the whole build (PC-093).

Measured on 2026-09-26 (PC-047): of six real intake runs on NVIDIA nemotron-3-ultra and Gemini 3
Flash, three were rejected for the same reason. The model wrote a "change status" endpoint —
`PATCH /orders/{orderId}/status` — and gave it a request body named after a type that does not
exist: `OrderStatusUpdate`, `TaskTransition`, or simply `json`. The validator is right that the
reference is wrong. Rejecting the *build* for it is not: everything else in the plan was fine, and
the user got an error for a prompt any person would have understood. Roughly half of real prompts
failed at the first step this way, on both models, which made the model choice nearly irrelevant.

Two repairs, both deterministic and both reported rather than silent:

1. **A schema name that is not a declared entity is resolved or dropped.** `OrderUpdate`,
   `orders`, `OrderResponse` and `order_dto` all clearly mean `Order`, and become it. A name that
   refers to nothing (`json`, `StatusPayload`) is removed — the endpoint then has no typed body,
   which the generators already handle — rather than failing validation.

2. **A status-change endpoint becomes a real lifecycle when the entity says what its states are.**
   If `Order.status` carries `enum:placed|accepted|delivered`, the ad-hoc `PATCH .../status` is
   replaced by a `workflow` capability over those states. That generates role-checked transition
   endpoints on every backend (R-566, R-588, R-589) — real behaviour instead of an unwired stub. If
   a workflow for the entity already exists, the ad-hoc endpoint is redundant and is removed. If
   the field lists no states, repair 1 alone applies: we do not invent a lifecycle nobody described.

PC-094 adds round two, found testing weaker models on 2026-09-26:

3. **Duplicates collapse to one.** qwen2.5-coder:7b declared the role `user` twice; the validator
   rejected the whole plan. The first of each role, entity, field, relation, screen, endpoint and
   capability is kept, and a repeated entity's extra fields are merged into the first.

4. **A lifecycle names a declared entity, or goes.** nemotron wrote a lifecycle for `Orders` when
   the entity was `Order`; that is resolved the same way schema names are. A lifecycle for an entity
   the plan never declared, or over a field the entity does not have, is removed rather than
   failing the build. Transition roles the plan never declared are dropped from the transition.

This runs on the decoded dict, after `_sanitize_ir_dict` and before the IR is constructed, so every
caller of `parse_ir_response` gets it.
"""

from __future__ import annotations

import re
from typing import Any

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,48}$")

#: Suffixes a model adds to an entity name to mean "a view of that entity".
_SCHEMA_SUFFIXES = (
    "statusupdate", "statuschange", "createrequest", "updaterequest", "request", "response",
    "create", "update", "input", "output", "payload", "body", "patch", "dto", "data", "details",
    "summary", "list", "item", "items", "record", "model", "schema", "out", "in",
)

#: Last path segments that mean "change this record's state".
_STATUS_SEGMENTS = frozenset({"status", "state", "transition", "transitions", "stage"})

#: Endpoints every app with accounts already has (R-591's /auth/* contract). A plan that declares
#: its own collides with them: seen live, POST /login became a route beside the sign-in page and the
#: production build failed.
_ACCOUNT_PATHS = frozenset({"/login", "/logout", "/signup", "/sign-up", "/register", "/signin", "/sign-in",
                            "/auth/login", "/auth/logout", "/auth/register", "/auth/signup", "/auth/me",
                            "/me", "/forgot-password", "/reset-password", "/auth/forgot-password",
                            "/auth/reset-password"})

_STATUS_PATH = re.compile(r"^/(?P<collection>[A-Za-z0-9_-]+)/\{[^/{}]+\}/(?P<action>[A-Za-z0-9_-]+)$")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def _singular(word: str) -> str:
    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"
    if word.endswith("ses") or word.endswith("xes") or word.endswith("ches") or word.endswith("shes"):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def resolve_entity_reference(reference: str, entity_names: list[str]) -> str | None:
    """The declared entity a schema name means, or None when it names nothing we have."""
    if reference in entity_names:
        return reference
    by_norm = {_norm(name): name for name in entity_names}
    ref = _norm(reference)
    if not ref:
        return None
    # R-570: "-ses" plurals are "-se" words as often as "-s" ones ("expenses", "courses", "cases").
    for candidate in (ref, _singular(ref), ref[:-1] if ref.endswith("s") else ref):
        if candidate in by_norm:
            return by_norm[candidate]
    # Longest entity name that the reference starts with, followed only by a known suffix.
    for norm_name in sorted(by_norm, key=len, reverse=True):
        if ref.startswith(norm_name):
            rest = ref[len(norm_name):]
            # "OrdersResponse" (plural) and "OrderStatusUpdate" (an 's' that starts a word) both
            # begin their remainder with 's'; try it with and without.
            if rest in _SCHEMA_SUFFIXES or (rest.startswith("s") and rest[1:] in _SCHEMA_SUFFIXES):
                return by_norm[norm_name]
    return None


def _entity_for_collection(collection: str, entity_names: list[str]) -> str | None:
    by_norm = {_norm(name): name for name in entity_names}
    col = _norm(collection)
    return by_norm.get(col) or by_norm.get(_singular(col))


def _enum_states(field: dict[str, Any]) -> tuple[str, ...]:
    for rule in field.get("validation") or ():
        rule = str(rule)
        if rule.startswith("enum:"):
            return tuple(part.strip() for part in rule.split(":", 1)[1].split("|") if part.strip())
    return ()


def _existing_workflow_entities(data: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for capability in data.get("capabilities") or ():
        if isinstance(capability, dict) and capability.get("kind") == "workflow":
            config = capability.get("config") or {}
            if isinstance(config, dict) and config.get("entity"):
                out.add(str(config["entity"]))
    return out


def _workflow_for(entity: str, field: str, states: tuple[str, ...], roles: list[str]) -> dict[str, Any] | None:
    if len(states) < 2 or len(set(states)) != len(states):
        return None
    if not all(_IDENTIFIER.match(s) for s in states):
        return None
    transitions = [
        {"name": f"mark_{state}"[:49], "to": state, "from": [], "roles": list(roles)}
        for state in states[1:]
    ]
    if len({t["name"] for t in transitions}) != len(transitions):
        return None
    return {
        "kind": "workflow",
        "name": f"{_norm(entity)}_lifecycle",
        "config": {
            "entity": entity,
            "field": field,
            "states": list(states),
            "initial": states[0],
            "transitions": transitions,
        },
    }


def _dedupe(items: Any, key, what: str, notes: list[str], merge=None) -> Any:
    if not isinstance(items, list):
        return items
    kept: dict[Any, Any] = {}
    out: list[Any] = []
    for item in items:
        k = key(item) if isinstance(item, dict) else None
        if k is None:
            out.append(item)
            continue
        if k in kept:
            if merge is not None:
                merge(kept[k], item)
            notes.append(f"{what} {k!r} was declared more than once; kept one")
            continue
        kept[k] = item
        out.append(item)
    return out


def _merge_entity(first: dict[str, Any], again: dict[str, Any]) -> None:
    fields = first.setdefault("fields", [])
    if isinstance(fields, list) and isinstance(again.get("fields"), list):
        names = {f.get("name") for f in fields if isinstance(f, dict)}
        fields.extend(f for f in again["fields"] if isinstance(f, dict) and f.get("name") not in names)


def _repair_structure(data: dict[str, Any], notes: list[str]) -> None:
    """Repairs 3 and 4: duplicates, and lifecycles that point at nothing."""
    data["roles"] = _dedupe(data.get("roles"), lambda r: r.get("id"), "role", notes)
    data["entities"] = _dedupe(data.get("entities"), lambda e: e.get("name"), "entity", notes, _merge_entity)
    for entity in data.get("entities") or ():
        if isinstance(entity, dict):
            name = entity.get("name")
            entity["fields"] = _dedupe(entity.get("fields"), lambda f: f.get("name"), f"{name} field", notes)
            if "relations" in entity:
                entity["relations"] = _dedupe(entity.get("relations"), lambda r: r.get("name"),
                                              f"{name} relation", notes)
    data["screens"] = _dedupe(data.get("screens"), lambda s: s.get("id"), "screen", notes)
    data["apis"] = _dedupe(data.get("apis"), lambda a: f"{str(a.get('method', '')).upper()} {a.get('path')}",
                           "endpoint", notes)
    data["capabilities"] = _dedupe(data.get("capabilities"), lambda c: c.get("name"), "capability", notes)
    for key in ("roles", "entities", "screens", "apis", "capabilities"):
        if data[key] is None:
            del data[key]

    entities = {str(e.get("name")): e for e in data.get("entities") or () if isinstance(e, dict) and e.get("name")}
    role_ids = {str(r.get("id")) for r in data.get("roles") or () if isinstance(r, dict)}
    kept: list[Any] = []
    for capability in data.get("capabilities") or ():
        config = capability.get("config") if isinstance(capability, dict) else None
        if isinstance(config, dict) and capability.get("kind") == "ownership":
            # R-570: an ownership rule names a declared entity, once, and declared roles - or goes.
            label = capability.get("name", "ownership")
            named = str(config.get("entity") or "")
            entity = resolve_entity_reference(named, list(entities)) if named else None
            if entity is None:
                notes.append(f"ownership {label!r}: entity {named!r} is not in the plan; removed")
                continue
            if any(isinstance(c, dict) and c.get("kind") == "ownership" and (c.get("config") or {}).get("entity") == entity
                   for c in kept):
                notes.append(f"ownership {label!r}: {entity} already has a rule; removed")
                continue
            config["entity"] = entity
            _drop_owner_reference(entities[entity], entity, notes)
            see_all = config.get("see_all")
            if isinstance(see_all, list) and role_ids:
                unknown = [r for r in see_all if str(r) not in role_ids and r != "admin"]
                if unknown:
                    config["see_all"] = [r for r in see_all if r not in unknown]
                    notes.append(f"ownership {label!r}: undeclared role(s) {', '.join(map(str, unknown))} dropped")
            kept.append(capability)
            continue
        if isinstance(config, dict) and capability.get("kind") == "money":
            # R-567: money is charged for declared entities by number fields, once per app.
            if any(isinstance(c, dict) and c.get("kind") == "money" for c in kept):
                notes.append("a second money capability removed (an app has one)")
                continue
            charges = []
            for charge in config.get("charges") or ():
                if not isinstance(charge, dict):
                    continue
                named = str(charge.get("entity") or "")
                entity = resolve_entity_reference(named, list(entities)) if named else None
                if entity is None:
                    notes.append(f"money: {named!r} is not in the plan; its charge removed")
                    continue
                fields = {f.get("name"): f for f in entities[entity].get("fields") or () if isinstance(f, dict)}
                if (fields.get(charge.get("amount")) or {}).get("type") not in ("float", "int"):
                    number = next((n for n, f in fields.items() if f.get("type") in ("float", "int")
                                   and any(w in str(n) for w in ("price", "total", "amount", "fee", "cost"))), None)
                    if number is None:
                        notes.append(f"money: {entity} has no price field; its charge removed")
                        continue
                    notes.append(f"money: {entity}'s price is {number}")
                    charge["amount"] = number
                if charge.get("payee") and (fields.get(charge["payee"]) or {}).get("type") not in ("uuid", "string"):
                    notes.append(f"money: {entity}.{charge['payee']} is not a user field; the platform keeps the sale")
                    charge.pop("payee")
                charges.append({**charge, "entity": entity})
            if not charges:
                notes.append("money: nothing left to charge for; removed")
                continue
            config["charges"] = charges
            if isinstance(config.get("refund_roles"), list) and role_ids:
                config["refund_roles"] = [r for r in config["refund_roles"] if str(r) in role_ids or r == "admin"]
            kept.append(capability)
            continue
        if not (isinstance(config, dict) and capability.get("kind") == "workflow"):
            kept.append(capability)
            continue
        label = capability.get("name", "lifecycle")
        named = str(config.get("entity") or "")
        entity = resolve_entity_reference(named, list(entities)) if named else None
        if entity is None:
            notes.append(f"lifecycle {label!r}: entity {named!r} is not in the plan; removed")
            continue
        if entity != named:
            config["entity"] = entity
            notes.append(f"lifecycle {label!r}: entity {named!r} resolved to {entity}")
        fields = {f.get("name") for f in entities[entity].get("fields") or () if isinstance(f, dict)}
        if config.get("field") not in fields:
            notes.append(f"lifecycle {label!r}: {entity} has no field {config.get('field')!r}; removed")
            continue
        for transition in config.get("transitions") or ():
            # PC-101, seen live: a model wrote "to": ["in_progress"]; the whole build failed on it.
            target = transition.get("to") if isinstance(transition, dict) else None
            if isinstance(target, list) and len(target) == 1 and isinstance(target[0], str):
                transition["to"] = target[0]
                notes.append(f"lifecycle {label!r}: transition target {target!r} read as {target[0]!r}")
            if isinstance(transition, dict) and isinstance(transition.get("roles"), list) and role_ids:
                unknown = [r for r in transition["roles"] if str(r) not in role_ids]
                if unknown:
                    transition["roles"] = [r for r in transition["roles"] if str(r) in role_ids]
                    notes.append(f"lifecycle {label!r}: undeclared role(s) {', '.join(map(str, unknown))} dropped")
        kept.append(capability)
    if "capabilities" in data:
        data["capabilities"] = kept
    _repair_jobs(data, entities, notes)
    _repair_realtime(data, entities, notes)


#: Names a model gives "the user this belongs to". Not "author": an Author is often a real entity.
_OWNER_REFERENCES = frozenset({"user", "owner", "creator", "created_by", "account"})


def _drop_owner_reference(entity: dict[str, Any], name: str, notes: list[str]) -> None:
    """R-570, seen live: a private-notes plan gave Note a required `user_id` and a relation to `User`.

    With an ownership rule the platform records the creator from the verified token, so a field the
    client fills in would be both redundant and a way to claim to be someone else (and every create
    failed with 422 until the client sent it). The owner reference goes; `created_by` is the owner.
    """
    fields = entity.get("fields") or []
    kept = [f for f in fields if not (isinstance(f, dict) and str(f.get("name", "")).removesuffix("_id") in _OWNER_REFERENCES
                                      and str(f.get("name", "")) != "id")]
    if len(kept) != len(fields):
        entity["fields"] = kept
        notes.append(f"ownership of {name}: the owner is recorded from sign-in; owner field(s) removed")
    relations = entity.get("relations") or []
    rel_kept = [r for r in relations if not (isinstance(r, dict) and str(r.get("name", "")) in _OWNER_REFERENCES)]
    if len(rel_kept) != len(relations):
        entity["relations"] = rel_kept
        notes.append(f"ownership of {name}: the owner relation is the platform's created_by; removed")


#: PC-112: names a plan gives "the people who sign in" - the accounts table every app with sign-in has.
_ACCOUNT_ENTITIES = frozenset({"user", "users", "account", "accounts", "appuser", "useraccount"})
_PASSWORD_FIELDS = frozenset({"password", "password_hash", "passwordhash", "hashed_password", "pass_hash", "password_digest"})
_IDENTITY_FIELDS = _PASSWORD_FIELDS | {"id", "email", "username", "name", "full_name", "first_name", "last_name",
                                       "role", "roles", "created_at", "updated_at", "is_active", "last_login"}


def _has_sign_in(data: dict[str, Any]) -> bool:
    apis = [a for a in data.get("apis") or () if isinstance(a, dict)]
    owned = any(isinstance(c, dict) and c.get("kind") == "ownership" for c in data.get("capabilities") or ())
    return owned or any(a.get("auth", True) for a in apis)


def _drop_account_duplicates(data: dict[str, Any], notes: list[str]) -> None:
    """PC-112, seen in R-570's private-notes build: the plan declared User(email, password_hash) next
    to the accounts table every app with sign-in already has. A second, unprotected place for users
    and their password hashes is a security bug and a source of confusion ("which users?").

    A User/Account entity that only repeats the account (email, password, name, role) is removed
    with everything that points at it; one that also holds profile data (a bio, an avatar) is kept
    as that profile, without its password fields.
    """
    if not _has_sign_in(data):
        return
    entities = [e for e in data.get("entities") or () if isinstance(e, dict)]
    for entity in list(entities):
        name = str(entity.get("name") or "")
        if _norm(name) not in _ACCOUNT_ENTITIES:
            continue
        fields = [f for f in entity.get("fields") or () if isinstance(f, dict)]
        extra = [f for f in fields if _norm(str(f.get("name", ""))).replace("_", "") not in
                 {n.replace("_", "") for n in _IDENTITY_FIELDS}]
        if extra:
            kept = [f for f in fields if _norm(str(f.get("name", ""))).replace("_", "") not in
                    {n.replace("_", "") for n in _PASSWORD_FIELDS}]
            if len(kept) != len(fields):
                entity["fields"] = kept
                notes.append(f"{name}: passwords live only in the app's accounts; password field(s) removed")
            continue
        data["entities"] = [e for e in data["entities"] if e is not entity]
        notes.append(f"{name} repeated the app's accounts (sign-in, roles and who-created-what already exist); removed")
        for other in data["entities"]:
            if not isinstance(other, dict):
                continue
            relations = [r for r in other.get("relations") or () if isinstance(r, dict)]
            gone = [r for r in relations if r.get("target_entity") == name]
            if gone:
                other["relations"] = [r for r in relations if r.get("target_entity") != name]
                dropped = {f"{r.get('name')}_id" for r in gone}
                other["fields"] = [f for f in other.get("fields") or () if not (isinstance(f, dict) and f.get("name") in dropped)]
                notes.append(f"{other.get('name')}: relation(s) to {name} removed (the creator is recorded from sign-in)")
        before = len(data.get("apis") or ())
        data["apis"] = [a for a in data.get("apis") or () if not (isinstance(a, dict) and (
            name in (a.get("request_schema"), a.get("response_schema"))
            or _norm(str(a.get("path", "")).strip("/").split("/")[0]) in _ACCOUNT_ENTITIES))]
        if len(data["apis"]) != before:
            notes.append(f"{before - len(data['apis'])} endpoint(s) for {name} removed (accounts have /auth/*)")
        for key in ("fixtures",):
            if key in data:
                data[key] = [x for x in data.get(key) or () if not (isinstance(x, dict) and x.get("entity") == name)]
        if "capabilities" in data:
            data["capabilities"] = [c for c in data.get("capabilities") or () if not (
                isinstance(c, dict) and (c.get("config") or {}).get("entity") == name)]


def repair_ir_dict(data: dict[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Repair `data` in place where it can; return it and a human-readable note per repair."""
    notes: list[str] = []
    _repair_structure(data, notes)
    _drop_account_duplicates(data, notes)
    apis = data.get("apis")
    entities = data.get("entities")
    if not isinstance(apis, list) or not isinstance(entities, list):
        return data, tuple(notes)

    entity_by_name = {str(e.get("name")): e for e in entities if isinstance(e, dict) and e.get("name")}
    entity_names = list(entity_by_name)
    role_ids = {str(r.get("id")) for r in data.get("roles") or () if isinstance(r, dict)}
    with_workflow = _existing_workflow_entities(data)

    has_accounts = any(isinstance(a, dict) and a.get("auth") for a in apis)
    kept: list[dict[str, Any]] = []
    for api in apis:
        if not isinstance(api, dict):
            continue
        location = f"{api.get('method', '?')} {api.get('path', '?')}"
        if has_accounts and str(api.get("path", "")).rstrip("/").lower() in _ACCOUNT_PATHS:
            notes.append(f"{location}: removed; sign-up and sign-in are built in under /auth")
            continue

        # Repair 2 first: a status-change endpoint may be replaced outright.
        match = _STATUS_PATH.match(str(api.get("path", "")))
        method = str(api.get("method", "")).upper()
        if match and method in ("PATCH", "PUT", "POST") and _norm(match.group("action")) in _STATUS_SEGMENTS:
            entity = _entity_for_collection(match.group("collection"), entity_names)
            if entity is not None:
                if entity in with_workflow:
                    notes.append(f"{location}: removed; {entity} already has a lifecycle whose transitions replace it")
                    continue
                fields = [f for f in entity_by_name[entity].get("fields") or () if isinstance(f, dict)]
                action_field = _norm(match.group("action"))
                status_field = next(
                    (f for f in fields if _norm(f.get("name", "")) in (action_field, "status", "state", "stage")),
                    None,
                )
                states = _enum_states(status_field) if status_field else ()
                roles = [r for r in api.get("required_roles") or () if str(r) in role_ids]
                workflow = _workflow_for(entity, str(status_field["name"]), states, roles) if states else None
                if workflow is not None:
                    data.setdefault("capabilities", []).append(workflow)
                    with_workflow.add(entity)
                    notes.append(
                        f"{location}: replaced by a {entity} lifecycle over {', '.join(states)} "
                        f"with role-checked transitions"
                    )
                    continue

        # Repair 1: every schema reference names a declared entity, or none.
        for key in ("request_schema", "response_schema", "error_schema"):
            reference = api.get(key)
            if reference in (None, "") or reference in entity_by_name:
                continue
            resolved = resolve_entity_reference(str(reference), entity_names)
            api[key] = resolved
            if resolved is None:
                notes.append(f"{location}: {key} {reference!r} names no entity; removed")
            else:
                notes.append(f"{location}: {key} {reference!r} resolved to {resolved}")
        kept.append(api)

    data["apis"] = kept
    return data, tuple(notes)


def _repair_jobs(data: dict[str, Any], entities: dict[str, Any], notes: list[str]) -> None:
    """R-568: one jobs capability, whose schedules name the plan's entities, fields and transitions.

    A schedule that cannot be made to fit is dropped with a note rather than failing the build: the
    rest of the app is still worth building, and the note says what was left out.
    """
    from ..application_ir.errors import InvalidIRError
    from ..application_ir.ir import _check_job_values
    from ..application_ir.jobs import AUDIT_FIELDS, Schedule

    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list):
        return
    jobs = [c for c in capabilities if isinstance(c, dict) and c.get("kind") == "jobs"]
    if not jobs:
        return
    raw: list[Any] = []
    for capability in jobs:
        config = capability.get("config")
        raw += (config.get("schedules") or []) if isinstance(config, dict) else []
    if len(jobs) > 1:
        notes.append("jobs: the schedules of several jobs capabilities merged into one")
    workflows = {
        str((c.get("config") or {}).get("entity")): c.get("config") or {}
        for c in capabilities if isinstance(c, dict) and c.get("kind") == "workflow"
    }
    kept: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = f"schedule {item.get('name')!r}"
        named = str(item.get("entity") or "")
        entity = resolve_entity_reference(named, list(entities)) if named else None
        if entity is None:
            notes.append(f"jobs: {label} names {named!r}, which is not in the plan; removed")
            continue
        item["entity"] = entity
        types = {str(f.get("name")): str(f.get("type")) for f in entities[entity].get("fields") or () if isinstance(f, dict)}
        for audit in AUDIT_FIELDS:
            types.setdefault(audit, "datetime")
        workflow = workflows.get(entity) or {}
        try:
            schedule = Schedule.from_dict(item)
            for name, values in schedule.where:
                if name not in types:
                    raise InvalidIRError(f"{entity} has no field {name!r}")
                _check_job_values(label, name, types[name], values)
            if schedule.older_than is not None and types.get(schedule.older_than[0]) != "datetime":
                raise InvalidIRError(f"{schedule.older_than[0]!r} is not a datetime field of {entity}")
            if schedule.transition is not None and schedule.transition not in {
                    str(t.get("name")) for t in workflow.get("transitions") or () if isinstance(t, dict)}:
                raise InvalidIRError(f"{entity} has no transition {schedule.transition!r}")
            for name, value in schedule.set:
                if name not in types or name == workflow.get("field"):
                    raise InvalidIRError(f"{name!r} cannot be set on {entity}")
                _check_job_values(label, name, types[name], (value,))
        except InvalidIRError as error:
            notes.append(f"jobs: {label} removed ({error})")
            continue
        if any(k.get("name") == item.get("name") for k in kept):
            notes.append(f"jobs: a second {label} removed")
            continue
        kept.append(item)
    first = jobs[0]
    zone = next((c.get("config", {}).get("timezone") for c in jobs
                 if isinstance(c.get("config"), dict) and c["config"].get("timezone")), None)
    data["capabilities"] = [c for c in capabilities if not (isinstance(c, dict) and c.get("kind") == "jobs")]
    if kept:
        first["config"] = {"schedules": kept[:16], **({"timezone": zone} if zone else {})}
        data["capabilities"].append(first)
    else:
        notes.append("jobs: no schedule left; removed")


def _repair_realtime(data: dict[str, Any], entities: dict[str, Any], notes: list[str]) -> None:
    """R-569: one realtime capability, naming the plan's entities (merged, resolved, deduplicated)."""
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list):
        return
    live = [c for c in capabilities if isinstance(c, dict) and c.get("kind") == "realtime"]
    if not live:
        return
    names: list[str] = []
    for capability in live:
        config = capability.get("config")
        for named in (config.get("entities") or []) if isinstance(config, dict) else []:
            entity = resolve_entity_reference(str(named), list(entities))
            if entity is None:
                notes.append(f"live updates: {named!r} is not in the plan; left out")
            elif entity not in names:
                names.append(entity)
    if len(live) > 1:
        notes.append("live updates: several realtime capabilities merged into one")
    data["capabilities"] = [c for c in capabilities if not (isinstance(c, dict) and c.get("kind") == "realtime")]
    if names:
        first = live[0]
        first["config"] = {"entities": names[:32]}
        data["capabilities"].append(first)
    else:
        notes.append("live updates: no entity left; removed")

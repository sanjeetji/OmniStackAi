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
    for candidate in (ref, _singular(ref)):
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


def repair_ir_dict(data: dict[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Repair `data` in place where it can; return it and a human-readable note per repair."""
    notes: list[str] = []
    apis = data.get("apis")
    entities = data.get("entities")
    if not isinstance(apis, list) or not isinstance(entities, list):
        return data, ()

    entity_by_name = {str(e.get("name")): e for e in entities if isinstance(e, dict) and e.get("name")}
    entity_names = list(entity_by_name)
    role_ids = {str(r.get("id")) for r in data.get("roles") or () if isinstance(r, dict)}
    with_workflow = _existing_workflow_entities(data)

    kept: list[dict[str, Any]] = []
    for api in apis:
        if not isinstance(api, dict):
            continue
        location = f"{api.get('method', '?')} {api.get('path', '?')}"

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

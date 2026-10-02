"""Notifications read from the prompt (PC-053): who hears of what.

The planning model is told about the `notifications` capability; this is the deterministic floor
under it. Two kinds of sentence, and only what the plan can carry out:

    a rule      "notify the customer when their order is shipped", "email staff when a new order is
                placed", "tell the courier when an order is assigned to them"
    a reminder  "remind patients a day before their appointment", "send a reminder 2 hours before
                each booking" - a scheduled job (R-568) that notifies once per record

Who hears: a role the plan coordinates with (staff, dispatcher, admin) hears as that role; the role an
entity is assigned to (PC-111) hears as its assignee; anyone else ("the customer", "them") is the
person who made the record. "email" adds the email channel; everything is in the app.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from .ir_repair import resolve_entity_reference
from .ownership_intent import _COORDINATORS, _plan_role

_RULE = re.compile(r"\b(?P<verb>notify|notifies|tell|alert|alerts|email|emails|e-mail|message|let|"
                   r"send (?:a |an )?(?:push |email |e-mail )?(?:notification|alert|message)s?)\b(?P<who>[^.;\n]{0,60}?)"
                   r"\b(?:when|whenever|once|as soon as|after)\b(?P<what>[^.;\n]{1,100})", re.I)
_REMIND = re.compile(r"\b(?:remind|reminds|send (?:a |an )?reminders?(?: to)?)\b(?P<who>[^.;\n]{0,40}?)\b"
                     r"(?P<n>\d{1,3}|a|an|one)\s*(?P<unit>min(?:ute)?s?|hours?|days?|weeks?)\s+before\b(?P<what>[^.;\n]{1,60})", re.I)
_CREATED = re.compile(r"\b(?:new|created|placed|submitted|booked|added|made|comes? in|arrives?|signs? up|registered|opened)\b", re.I)
_ASSIGNED = re.compile(r"\bassigned\b", re.I)
_DELETED = re.compile(r"\b(?:deleted|removed)\b", re.I)
_CHANGED = re.compile(r"\b(?:changes?|changed|updated?|edited)\b", re.I)
_STATUS_WORD = re.compile(r"\b(?:is|gets|becomes|has been|was|are)\s+(?:marked\s+(?:as\s+)?)?([a-z]+(?:ed|en)|ready|done|complete|out for delivery)\b", re.I)
_WHEN_FIELDS = ("starts_at", "start_time", "start_at", "scheduled_at", "scheduled_for", "appointment_at", "date_time",
                "datetime", "date", "due_date", "due_at", "deadline", "begins_at", "event_date", "check_in")
_LABEL_FIELDS = ("name", "title", "subject", "number", "reference", "code")


def _entities(data: dict[str, Any]) -> list[str]:
    return [str(e.get("name")) for e in data.get("entities") or () if isinstance(e, dict) and e.get("name")]


def _fields(data: dict[str, Any], entity: str) -> dict[str, str]:
    for item in data.get("entities") or ():
        if isinstance(item, dict) and item.get("name") == entity:
            return {str(f.get("name")): str(f.get("type")) for f in item.get("fields") or () if isinstance(f, dict)}
    return {}


def _capability(data: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [c for c in data.get("capabilities") or () if isinstance(c, dict) and c.get("kind") == kind]


def _assignee(data: dict[str, Any], entity: str) -> str | None:
    for c in _capability(data, "ownership"):
        config = c.get("config") or {}
        if config.get("entity") == entity and config.get("assignee"):
            return str(config["assignee"])
    return None


def _entity_in(text: str, entities: list[str]) -> str | None:
    for word in re.findall(r"[a-zA-Z]+", text):
        found = resolve_entity_reference(word, entities)
        if found:
            return found
    return None


def _who(text: str, data: dict[str, Any], entity: str) -> list[str]:
    roles = [str(r.get("id")) for r in data.get("roles") or () if isinstance(r, dict) and r.get("id")]
    assignee = _assignee(data, entity)
    out: list[str] = []
    for word in re.findall(r"[a-zA-Z]+", text.lower()):
        singular = word[:-1] if word.endswith("s") and not word.endswith("ss") else word
        role = _plan_role(singular, roles) or _plan_role(word, roles) or ("admin" if singular == "admin" else None)
        if role is None:
            continue
        if assignee and assignee == f"{role}_id":
            target = "assignee"
        elif role in _COORDINATORS or role == "admin":
            target = f"role:{role}"
        else:
            target = "creator"
        if target not in out:
            out.append(target)
    return out or ["creator"]  # "the customer", "them", "the user": whoever made the record


def _label(fields: dict[str, str]) -> str:
    field = next((f for f in _LABEL_FIELDS if f in fields), None)
    return f": {{{field}}}" if field else ""


def _add_rule(data: dict[str, Any], rule: dict[str, Any], notes: list[str], note: str) -> None:
    from ..application_ir import ApplicationIR
    from ..application_ir.errors import ApplicationIRError

    trial = copy.deepcopy(data)
    caps = trial.setdefault("capabilities", [])
    existing = next((c for c in caps if c.get("kind") == "notifications"), None)
    if existing is None:
        existing = {"kind": "notifications", "name": "app_notifications", "config": {"rules": []}}
        caps.append(existing)
    rules = existing.setdefault("config", {}).setdefault("rules", [])
    if any(r.get("entity") == rule["entity"] and r.get("when") == rule["when"] and r.get("to") == rule["to"] for r in rules):
        return
    while any(r.get("name") == rule["name"] for r in rules):
        rule["name"] += "_"
    rules.append(rule)
    try:
        ApplicationIR.from_dict(trial)
    except (ApplicationIRError, ValueError, TypeError, KeyError):
        return
    data["capabilities"] = caps
    notes.append(note)


def notifications_from_prompt(prompt: str, data: dict[str, Any]) -> list[str]:
    entities = _entities(data)
    if not prompt or not entities:
        return []
    notes: list[str] = []
    for sentence in re.split(r"[;\n!?]+|\.(?!\d)(?:\s|$)", prompt):
        _rule_from(sentence, data, entities, notes)
        _reminder_from(sentence, data, entities, notes)
    return notes


def _rule_from(sentence: str, data: dict[str, Any], entities: list[str], notes: list[str]) -> None:
    match = _RULE.search(sentence)
    if not match or _REMIND.search(sentence):
        return
    what = match.group("what")
    entity = _entity_in(what, entities) or _entity_in(match.group("who"), entities)
    if entity is None:
        return
    fields = _fields(data, entity)
    workflow = next((c.get("config") or {} for c in _capability(data, "workflow") if (c.get("config") or {}).get("entity") == entity), {})
    words = {w.lower() for w in re.findall(r"[a-zA-Z_]+", what)}
    state = next((s for s in workflow.get("states") or () if str(s) in words and s != workflow.get("initial")), None)
    label = _label(fields)
    if _ASSIGNED.search(what) and _assignee(data, entity):
        when: Any = "assigned"
        title = f"{entity} assigned to you{label}"
    elif state:
        when = {"field": str(workflow.get("field") or "status"), "becomes": state}
        title = f"{entity} {state.replace('_', ' ')}{label}"
    elif _DELETED.search(what):
        when, title = "deleted", f"{entity} removed{label}"
    elif _CREATED.search(what):
        when, title = "created", f"New {entity.lower()}{label}"
    elif not workflow and fields.get("status") in ("string", "text") and (word := _STATUS_WORD.search(what)):
        # No lifecycle, a plain status: "when their order is delivered" -> status becomes "delivered".
        value = word.group(1).lower()
        when, title = {"field": "status", "becomes": value}, f"{entity} {value}{label}"
    elif _CHANGED.search(what):
        when, title = "changed", f"{entity} updated{label}"
    else:
        return
    to = _who(match.group("who") + (" them" if not match.group("who").strip() else ""), data, entity)
    if when == "assigned":
        to = ["assignee"]
    channels = ["in_app", "email"] if match.group("verb").lower().startswith(("email", "e-mail")) or "email" in sentence.lower() else ["in_app"]
    if re.search(r"\b(?:push|phone|mobile)\b", sentence, re.I):  # PC-121: to the phone app too
        channels.append("push")
    event = when if isinstance(when, str) else f"{when['field']}_{when['becomes']}"
    rule = {"name": f"{entity.lower()}_{event}", "entity": entity, "when": when, "to": to, "title": title, "channels": channels}
    _add_rule(data, rule, notes, f"a notification: {', '.join(to)} hear when {entity} is {event.replace('_', ' ')}"
                                   f" ({' and '.join(channels)})")


def _reminder_from(sentence: str, data: dict[str, Any], entities: list[str], notes: list[str]) -> None:
    from ..application_ir import ApplicationIR
    from ..application_ir.errors import ApplicationIRError

    match = _REMIND.search(sentence)
    if not match:
        return
    entity = _entity_in(match.group("what"), entities) or _entity_in(match.group("who"), entities)
    if entity is None:
        return
    fields = _fields(data, entity)
    due = next((f for f in _WHEN_FIELDS if fields.get(f) == "datetime"), None)
    if due is None:
        return
    count = 1 if match.group("n").lower() in ("a", "an", "one") else int(match.group("n"))
    unit = match.group("unit").lower()
    age = f"{count}m" if unit.startswith("min") else f"{count}h" if unit.startswith("hour") else \
        f"{count}d" if unit.startswith("day") else f"{count * 7}d"
    every = "5m" if unit.startswith(("min", "hour")) else "15m"
    channels = ["in_app", "email"] if "email" in sentence.lower() else ["in_app"]
    if re.search(r"\b(?:push|phone|mobile)\b", sentence, re.I):
        channels.append("push")
    schedule = {"name": f"remind_{entity.lower()}", "entity": entity, "every": every,
                "due_within": {"field": due, "age": age},
                "do": {"notify": {"to": _who(match.group("who"), data, entity), "title": f"Reminder: {entity.lower()} at {{{due}}}",
                                  "channels": channels}}}
    trial = copy.deepcopy(data)
    caps = trial.setdefault("capabilities", [])
    jobs = next((c for c in caps if c.get("kind") == "jobs"), None)
    if jobs is None:
        caps.append({"kind": "jobs", "name": "app_jobs", "config": {"schedules": [schedule]}})
    else:
        schedules = jobs.setdefault("config", {}).setdefault("schedules", [])
        if any(s.get("name") == schedule["name"] for s in schedules):
            return
        schedules.append(schedule)
    try:
        ApplicationIR.from_dict(trial)
    except (ApplicationIRError, ValueError, TypeError, KeyError):
        return
    data["capabilities"] = caps
    notes.append(f"a reminder: {', '.join(schedule['do']['notify']['to'])} hear {age} before each {entity}'s {due}")

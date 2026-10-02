"""Scheduled jobs read from the prompt (R-568): what the app should do on its own.

The planning model is told about the `jobs` capability; this is the deterministic floor under it,
as `money_intent` is for money. Two kinds of sentence are read, and only when the plan can carry
them out - a schedule is added for an entity the plan has, through a transition its workflow has
or a flag field it has, and never otherwise:

    an age      "cancel unpaid orders after 30 minutes", "orders not paid within 2 hours are
                cancelled", "delete drafts older than 30 days", "archive completed tasks after 90 days"
    a due date  "mark invoices as overdue when the due date passes", "tasks become overdue after
                their deadline"

What people may do themselves is not a job: "customers can cancel an order within 2 hours" is a
rule for a button, so a sentence whose verb follows can / may / allowed to is left alone.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from .ir_repair import resolve_entity_reference

_UNIT_SECONDS = {"min": 60, "minute": 60, "hour": 3600, "hr": 3600, "day": 86400, "week": 7 * 86400, "month": 30 * 86400,
                 "year": 365 * 86400}
_COUNT = r"(?P<n>\d{1,4}|an?|one)\s*(?P<unit>min(?:ute)?s?|hours?|hrs?|days?|weeks?|months?|years?)\b"
_VERBS = r"(?P<verb>auto-?cancel|cancel|expire|close|archive|delete|remove|purge)"
# "cancel unpaid orders after 30 minutes" / "delete drafts older than 30 days"
_ACTIVE = re.compile(_VERBS + r"\w*\b(?P<what>[^.;\n]{1,80}?)\b(?:after|older than|within|in)\s+" + _COUNT, re.I)
# "orders not paid within 30 minutes are cancelled" / "drafts are deleted after 30 days"
_PASSIVE = re.compile(r"(?P<what>[^.;\n]{1,80}?)\b(?:are|is|get|gets|will be|should be|be)\s+(?:automatically\s+|auto-?)?"
                      + _VERBS + r"\w*\b(?P<rest>[^.;\n]{0,40}?)\b(?:after|older than|within|in)\s+" + _COUNT, re.I)
_PASSIVE_BEFORE = re.compile(r"(?P<what>[^.;\n]{1,80}?)\b(?:not\s+\w+|unpaid|unconfirmed)\s+(?:within|in)\s+" + _COUNT
                             + r"[^.;\n]{0,30}?\b(?:are|is|get|gets|will be|should be|be)\s+(?:automatically\s+)?" + _VERBS, re.I)
_MAY = re.compile(r"\b(?:can|may|able to|allowed to|allow\w*|let|lets|option to)\s+(?:\w+\s+){0,2}$", re.I)
_DUE_WORDS = re.compile(r"\b(overdue|late|expired)\b", re.I)
_DUE_FIELDS = ("due_date", "due_at", "deadline", "due", "expires_at", "expiry_date", "expiration_date", "end_date",
               "ends_at", "valid_until")
# PC-117: "every night at 2am", "daily at 09:30", "every Monday at 9am", "at midnight".
_CLOCK = re.compile(r"\b(?:at\s+)?(?:(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ampm>am|pm|a\.m\.|p\.m\.)|(?P<word>midnight|noon))\b"
                    r"|\bat\s+(?P<h24>[01]?\d|2[0-3]):(?P<m24>[0-5]\d)\b", re.I)
_DAILY = re.compile(r"\b(?:every\s+(?:day|night|morning|evening)|daily|nightly|each\s+(?:day|night))\b", re.I)
_WEEKLY = re.compile(r"\b(?:every|each|on)\s+(?P<day>monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?\b", re.I)
_ZONES = (("Asia/Kolkata", ("india", "rupee", "₹", " inr", " ist")), ("Europe/London", ("london", " uk ", "britain")),
          ("America/New_York", ("new york", " est ", "eastern time")), ("Europe/Berlin", ("germany", "berlin")))
_UNPAID = re.compile(r"\b(?:unpaid|not\s+(?:been\s+)?paid|without\s+payment)\b", re.I)


def _clock(sentence: str) -> tuple[str | None, str | None, str | None]:
    """(every, at, on) for a sentence that names a time of day, else (None, None, None)."""
    clock = _CLOCK.search(sentence)
    weekly = _WEEKLY.search(sentence)
    if clock is None or not (_DAILY.search(sentence) or weekly or re.search(r"\bat\s", sentence, re.I)):
        return None, None, None
    if clock.group("word"):
        hours, minutes = (0, 0) if clock.group("word").lower() == "midnight" else (12, 0)
    elif clock.group("h24"):
        hours, minutes = int(clock.group("h24")), int(clock.group("m24"))
    else:
        hours, minutes = int(clock.group("h")) % 12, int(clock.group("m") or 0)
        if clock.group("ampm").lower().startswith("p"):
            hours += 12
    if hours > 23 or minutes > 59:
        return None, None, None
    at = f"{hours:02d}:{minutes:02d}"
    if weekly:
        return "7d", at, weekly.group("day").lower()
    return "1d", at, None


def _zone(prompt: str) -> str | None:
    text = f" {prompt.lower()} "
    return next((zone for zone, signs in _ZONES if any(sign in text for sign in signs)), None)


def _age(n: str, unit: str) -> str | None:
    count = 1 if n.lower() in ("a", "an", "one") else int(n)
    key = unit.lower().rstrip("s")
    key = "min" if key.startswith("min") and key != "minute" else key
    seconds = count * _UNIT_SECONDS.get(key, 0)
    if seconds <= 0 or seconds > 365 * 86400:
        return None
    if seconds % 86400 == 0:
        return f"{seconds // 86400}d"
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    return f"{seconds // 60}m"


def _every(age_seconds: int) -> str:
    """Look often enough that a row is acted on soon after its time: a minute for minutes, five for
    hours, an hour for days."""
    return "1m" if age_seconds <= 3600 else "5m" if age_seconds <= 86400 else "1h"


def _seconds(age: str) -> int:
    return int(age[:-1]) * {"m": 60, "h": 3600, "d": 86400}[age[-1]]


def _entity_in(text: str, entities: list[str]) -> str | None:
    for word in re.findall(r"[a-zA-Z]+", text):
        found = resolve_entity_reference(word, entities)
        if found:
            return found
    return None


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _workflow(data: dict[str, Any], entity: str) -> dict[str, Any] | None:
    for capability in data.get("capabilities") or ():
        if isinstance(capability, dict) and capability.get("kind") == "workflow":
            config = capability.get("config") or {}
            if config.get("entity") == entity:
                return config
    return None


def _fields(data: dict[str, Any], entity: str) -> dict[str, str]:
    for item in data.get("entities") or ():
        if isinstance(item, dict) and item.get("name") == entity:
            return {str(f.get("name")): str(f.get("type")) for f in item.get("fields") or () if isinstance(f, dict)}
    return {}


def _action(data: dict[str, Any], entity: str, verb: str) -> dict[str, Any] | None:
    """What `verb` means for this entity: delete, its workflow's transition, or its flag."""
    root = verb.lower().replace("auto-", "").replace("auto", "")
    if root in ("delete", "remove", "purge"):
        return {"delete": True}
    stem = root.rstrip("e")  # cancel, expir, clos, archiv
    workflow = _workflow(data, entity)
    if workflow:
        for transition in workflow.get("transitions") or ():
            name, to = str(transition.get("name", "")), str(transition.get("to", ""))
            if name.startswith(stem) or to.startswith(stem):
                return {"transition": name}
    fields = _fields(data, entity)
    for flag in (f"is_{stem}ed", f"{stem}ed", f"is_{stem}led", f"{stem}led"):
        if fields.get(flag) == "bool" and flag != (workflow or {}).get("field"):
            return {"set": {flag: True}}
    return None


def _where(data: dict[str, Any], entity: str, text: str, do: dict[str, Any]) -> dict[str, list[Any]]:
    """The adjectives that narrow which rows: 'unpaid' (a paid flag), or a state the workflow has."""
    where: dict[str, list[Any]] = {}
    fields = _fields(data, entity)
    if _UNPAID.search(text):
        flag = next((f for f in ("paid", "is_paid") if fields.get(f) == "bool"), None)
        if flag:
            where[flag] = [False]
    workflow = _workflow(data, entity)
    if workflow and not do.get("set"):
        words = {w.lower() for w in re.findall(r"[a-zA-Z_]+", text)}
        states = [s for s in workflow.get("states") or () if str(s) in words]
        transition = next((t for t in workflow.get("transitions") or () if t.get("name") == do.get("transition")), None)
        sources = list((transition or {}).get("from") or [])
        if states and (not sources or all(s in sources for s in states)):
            where[str(workflow.get("field") or "status")] = states
    return where


def _at_time(schedule: dict[str, Any], sentence: str) -> None:
    """PC-117: "every night at 2am" runs the schedule at that local time instead of every few minutes."""
    every, at, on = _clock(sentence)
    if at is None:
        return
    schedule["every"], schedule["at"] = every, at
    if on:
        schedule["on"] = on


def _add(data: dict[str, Any], schedule: dict[str, Any], notes: list[str], note: str) -> None:
    """Add a schedule only if the plan, with it, is still valid."""
    from ..application_ir import ApplicationIR
    from ..application_ir.errors import ApplicationIRError

    capabilities = data.setdefault("capabilities", [])
    jobs = next((c for c in capabilities if isinstance(c, dict) and c.get("kind") == "jobs"), None)
    if jobs is not None:
        existing = (jobs.get("config") or {}).get("schedules") or []
        if any(s.get("entity") == schedule["entity"] and s.get("do") == schedule["do"] for s in existing if isinstance(s, dict)):
            return
        names = {s.get("name") for s in existing if isinstance(s, dict)}
        if schedule["name"] in names:
            schedule["name"] = f"{schedule['name']}_{len(names) + 1}"
    trial = copy.deepcopy(data)
    trial_caps = trial.setdefault("capabilities", [])
    trial_jobs = next((c for c in trial_caps if isinstance(c, dict) and c.get("kind") == "jobs"), None)
    if trial_jobs is None:
        trial_caps.append({"kind": "jobs", "name": "app_jobs", "config": {"schedules": [schedule]}})
    else:
        trial_jobs.setdefault("config", {}).setdefault("schedules", []).append(schedule)
    try:
        ApplicationIR.from_dict(trial)
    except (ApplicationIRError, ValueError, TypeError, KeyError):
        return
    data["capabilities"] = trial_caps
    notes.append(note)


def jobs_from_prompt(prompt: str, data: dict[str, Any]) -> list[str]:
    if not prompt:
        return []
    entities = [str(e.get("name")) for e in data.get("entities") or () if isinstance(e, dict) and e.get("name")]
    if not entities:
        return []
    notes: list[str] = []
    for sentence in re.split(r"[;\n!?]+|\.(?!\d)(?:\s|$)", prompt):
        _age_rule(sentence, data, entities, notes)
        _due_rule(sentence, data, entities, notes)
    zone = _zone(prompt)
    jobs = next((c for c in data.get("capabilities") or () if isinstance(c, dict) and c.get("kind") == "jobs"), None)
    timed = jobs and any(isinstance(s, dict) and s.get("at") for s in (jobs.get("config") or {}).get("schedules") or ())
    if timed and zone and not jobs["config"].get("timezone"):
        jobs["config"]["timezone"] = zone  # PC-117: times of day are the app's local time
        notes.append(f"scheduled times are in {zone}")
    return notes


def _age_rule(sentence: str, data: dict[str, Any], entities: list[str], notes: list[str]) -> None:
    for pattern in (_ACTIVE, _PASSIVE, _PASSIVE_BEFORE):
        match = pattern.search(sentence)
        if not match:
            continue
        if pattern is _ACTIVE and _MAY.search(sentence[:match.start()]):
            return  # "customers can cancel an order within 2 hours": a button, not a job
        entity = _entity_in(match.group("what"), entities)
        age = _age(match.group("n"), match.group("unit"))
        if entity is None or age is None:
            continue
        do = _action(data, entity, match.group("verb"))
        if do is None:
            return
        where = _where(data, entity, sentence, do)
        verb = next(iter(do)) if "transition" not in do else do["transition"]
        name = f"{'delete' if 'delete' in do else verb if 'transition' in do else 'flag'}_{_snake(entity)}s"
        schedule: dict[str, Any] = {"name": name, "entity": entity, "every": _every(_seconds(age)),
                                    "older_than": {"field": "created_at", "age": age}, "do": do}
        _at_time(schedule, sentence)
        if where:
            schedule["where"] = where
        what = do.get("transition") or ("delete" if "delete" in do else f"set {next(iter(do['set']))}")
        _add(data, schedule, notes, f"a scheduled job: {what} {entity} records {age} after they are created")
        return


def _due_rule(sentence: str, data: dict[str, Any], entities: list[str], notes: list[str]) -> None:
    state = _DUE_WORDS.search(sentence)
    if not state or not re.search(r"\b(?:due|deadline|expir\w*|end date|ends?)\b", sentence, re.I):
        return
    # The entity the sentence names that has a due date ("remove products ... mark invoices overdue").
    entity, due = None, None
    for word in re.findall(r"[a-zA-Z]+", sentence):
        found = resolve_entity_reference(word, entities)
        if found:
            fields = _fields(data, found)
            due = next((f for f in _DUE_FIELDS if fields.get(f) == "datetime"), None)
            if due:
                entity = found
                break
    if entity is None or due is None:
        return
    fields = _fields(data, entity)
    word = state.group(1).lower()
    workflow = _workflow(data, entity)
    do = None
    if workflow:
        transition = next((t for t in workflow.get("transitions") or ()
                           if str(t.get("to")) == word or str(t.get("name", "")).endswith(word)), None)
        if transition:
            do = {"transition": str(transition.get("name"))}
    if do is None:
        flag = next((f for f in (f"is_{word}", word) if fields.get(f) == "bool"), None)
        if flag is None:
            return
        do = {"set": {flag: True}}
    schedule = {"name": f"mark_{word}_{_snake(entity)}s", "entity": entity, "every": "5m",
                "older_than": {"field": due, "age": "0m"}, "do": do}
    _at_time(schedule, sentence)
    _add(data, schedule, notes, f"a scheduled job: {entity} records become {word} once {due} passes")

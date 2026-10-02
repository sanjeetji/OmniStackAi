"""R-582: the plan is checked against the prompt before anything is generated.

A model asked once for a whole application plans most of it and forgets some: "customers book
appointments and leave reviews" comes back with Appointment and no Review. Nothing downstream can
add what the plan left out. So after the first plan:

1. **critique** - deterministic, no model call: what the prompt asks for that the plan lacks -
   things it names after a verb ("book appointments", "write reviews"), features (reviews, uploads,
   a map, messages, approvals, a dashboard, favourites, comments), roles it names, and entities with
   no endpoints;
2. **revise** - only when there are gaps: one more model call, given its own plan and the list,
   asked for the complete plan with them added;
3. **accept** - the revision is kept only if it is a valid plan that keeps every entity, role and
   capability the first one had and closes at least one gap. Otherwise the first plan stands, and
   the build notes say what was missing.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from ..application_ir import ApplicationIR, FieldType
from .ir_repair import resolve_entity_reference

MAX_GAPS = 10

_VERB_NOUN = re.compile(
    r"\b(?:manage|track|create|add|book|list|browse|review|rate|upload|schedule|assign|post|write|send|leave|"
    r"log|record|submit|request|buy|sell|rent|reserve|enrol|enroll|join|follow|share|save|favou?rite|bookmark|"
    r"comment on|publish|organi[sz]e|plan|order)\s+(?:(?:their|his|her|a|an|the|new|own|all|multiple|many|"
    r"several|any|and|or|daily|weekly|online)\s+)*(?P<noun>[a-z]{3,})",
    re.I,
)
#: Words a verb can be followed by that are not things an app stores.
_NOT_THINGS = {
    "them", "it", "this", "that", "these", "those", "account", "accounts", "app", "data", "information", "details",
    "time", "way", "people", "users", "user", "list", "things", "item", "items", "everything", "anything", "online",
    "track", "progress", "status", "money", "payment", "payments", "notifications", "updates", "who", "what", "when",
    "where", "how", "with", "from", "into", "for", "about", "out", "up", "back", "more", "each", "other", "one", "two",
    "pay", "reviews_", "orders_", "new", "live", "real", "it's", "their",
}
_ROLE_WORDS = ("customer", "driver", "courier", "doctor", "patient", "teacher", "student", "tutor", "seller", "buyer",
               "vendor", "merchant", "host", "guest", "manager", "staff", "agent", "instructor", "member", "employee",
               "recruiter", "candidate", "landlord", "tenant", "mentor", "trainer", "client", "freelancer", "nurse",
               "dispatcher", "technician", "volunteer", "organizer", "organiser", "attendee", "coach", "parent")

#: (words in the prompt, the plan has it when ..., what to ask for)
_FEATURES: tuple[tuple[str, str, str], ...] = (
    (r"\b(?:reviews?|ratings?|rate|stars)\b", "entity:review|rating|feedback|testimonial,field:rating",
     "reviews and ratings: a Review entity with an int rating (1-5) and a text comment, linked to what is reviewed"),
    (r"\b(?:upload|uploads|photos?|images?|pictures?|attachments?|documents?|resumes?|avatars?|files?)\b", "type:attachment",
     "file uploads: an attachment field on the entity the prompt attaches photos or documents to"),
    (r"\b(?:maps?|locations?|gps|nearby|directions)\b", "field:latitude|lat|location|address",
     "locations: float latitude and longitude fields (and an address string) on the entity that has a place"),
    (r"\b(?:chat|chats|messages?|messaging|inbox|conversations?)\b", "entity:message|conversation|chat|thread",
     "messages: a Message entity (text body, sender and recipient uuid fields) for people to write to each other"),
    (r"\b(?:approve|approves|approved|approval|approvals|reject|rejected)\b", "workflow:approve|approved|approval",
     "an approval lifecycle: a workflow capability with states such as pending, approved and rejected"),
    (r"\b(?:dashboard|analytics|reports?|statistics|stats|insights|kpis?)\b", "screen:dashboard|report|analytics|stats|insight",
     "a dashboard screen with the figures the prompt asks for"),
    (r"\b(?:favou?rites?|wishlists?|bookmarks?|saved items|save for later)\b", "entity:favorite|favourite|wishlist|bookmark|saved",
     "favourites: a Favorite entity linking a user to what they saved"),
    (r"\bcomments?\b", "entity:comment|reply|note",
     "comments: a Comment entity with a text body linked to what it comments on"),
)


@dataclass(frozen=True, slots=True)
class Gap:
    kind: str  # entity | feature | role | endpoints
    text: str


def _words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-zA-Z_]+", text)}


def _has(ir: ApplicationIR, rule: str) -> bool:
    for part in rule.split(","):
        kind, _, names = part.partition(":")
        options = names.split("|")
        if kind == "entity" and any(any(o in e.name.lower() for o in options) for e in ir.entities):
            return True
        if kind == "field" and any(f.name.lower() in options or any(f.name.lower().startswith(o) for o in options)
                                   for e in ir.entities for f in e.fields):
            return True
        if kind == "type" and any(f.type is FieldType.ATTACHMENT for e in ir.entities for f in e.fields):
            return True
        if kind == "screen" and any(any(o in s.id.lower() for o in options) for s in ir.screens):
            return True
        if kind == "workflow":
            for c in ir.capabilities:
                if c.kind == "workflow":
                    words = _words(json.dumps(c.config))
                    if any(o in w for w in words for o in options):
                        return True
    return False


_SPELLING = (("favourite", "favorite"), ("colour", "color"), ("organisation", "organization"), ("catalogue", "catalog"),
             ("programme", "program"), ("enrolment", "enrollment"), ("cheque", "check"), ("licence", "license"))


def _american(word: str) -> str:
    for british, american in _SPELLING:
        word = word.replace(british, american)
    return word


def critique(prompt: str, ir: ApplicationIR) -> list[Gap]:
    """What the prompt asks for that the plan lacks."""
    gaps: list[Gap] = []
    prompt = _american(prompt.lower())
    entities = [e.name for e in ir.entities]
    field_names = {f.name.lower() for e in ir.entities for f in e.fields}
    roles = {r.id for r in ir.roles}
    from .ownership_intent import _plan_role

    seen: set[str] = set()
    for match in _VERB_NOUN.finditer(prompt):
        noun = match.group("noun").lower()
        singular = noun[:-3] + "y" if noun.endswith("ies") else noun[:-1] if noun.endswith("s") and not noun.endswith("ss") else noun
        if noun in _NOT_THINGS or singular in _NOT_THINGS or singular in seen:
            continue
        if resolve_entity_reference(noun, entities) or resolve_entity_reference(singular, entities):
            continue
        if singular in field_names or noun in field_names or _plan_role(singular, list(roles)) or singular in _ROLE_WORDS:
            continue
        seen.add(singular)
        gaps.append(Gap("entity", f"the prompt says \"{match.group(0).strip()}\" but the plan has no {singular.title()} entity"))
    for pattern, rule, ask in _FEATURES:
        if re.search(pattern, prompt, re.I) and not _has(ir, rule):
            wanted = {o for part in rule.split(",") if part.startswith("entity:") for o in part[7:].split("|")}
            if any(w in seen for w in wanted):
                continue  # already asked for as a missing entity
            gaps.append(Gap("feature", ask))
    words = _words(prompt)
    for word in _ROLE_WORDS:
        if resolve_entity_reference(word, entities):
            continue  # "customers" in a shop's dashboard are data, not people who sign in
        if (word in words or f"{word}s" in words) and _plan_role(word, list(roles)) is None and word not in roles:
            gaps.append(Gap("role", f"the prompt mentions {word}s but the plan has no {word} role"))
    for entity in _without_endpoints(ir):
        gaps.append(Gap("endpoints", f"{entity.name} has no endpoints (list, get, create, update, delete)"))
    return gaps[:MAX_GAPS]


def _without_endpoints(ir: ApplicationIR) -> list:
    served = {name for a in ir.apis for name in (a.request_schema, a.response_schema) if name}
    return [e for e in ir.entities if e.name not in served]


def with_endpoints(ir: ApplicationIR) -> tuple[ApplicationIR, tuple[str, ...]]:
    """An entity nobody can reach is given the standard five endpoints - deterministic, no model."""
    missing = _without_endpoints(ir)
    if not missing or not ir.apis:
        return ir, ()
    from ..codegen.nextjs import _plural

    data = ir.to_dict()
    auth = sum(1 for a in ir.apis if a.auth) * 2 >= len(ir.apis)
    taken = {(a["method"], a["path"]) for a in data["apis"]}
    for entity in missing:
        table = re.sub(r"(?<!^)(?=[A-Z])", "_", entity.name).lower()
        base = "/" + _plural(table)
        item = f"{base}/{{{entity.name[:1].lower() + entity.name[1:]}Id}}"
        for method, path, request, response in (("GET", base, None, entity.name), ("POST", base, entity.name, entity.name),
                                                ("GET", item, None, entity.name), ("PUT", item, entity.name, entity.name),
                                                ("DELETE", item, None, None)):
            if (method, path) not in taken:
                data["apis"].append({"method": method, "path": path, "auth": auth, "request_schema": request,
                                     "response_schema": response, "required_roles": [], "error_schema": None})
    return ApplicationIR.from_dict(data), tuple(f"{e.name} had no endpoints; the standard five were added" for e in missing)


def revision_request(gaps: list[Gap], ir: ApplicationIR) -> str:
    listed = "\n".join(f"- {g.text}" for g in gaps)
    return (
        "Here is the Application IR you produced:\n"
        f"{json.dumps(ir.to_dict(), separators=(',', ':'))}\n\n"
        "Checked against the application description, it is missing:\n"
        f"{listed}\n\n"
        "Return the COMPLETE revised Application IR as one JSON object. Keep every entity, field, relation, role, "
        "screen, API endpoint and capability you already have, and add what is missing - with fields, relations, "
        "CRUD endpoints and list/detail screens for each new entity. Return only the JSON object."
    )


def accept(original: ApplicationIR, revised: ApplicationIR, gaps: list[Gap], prompt: str) -> tuple[bool, str]:
    """Keep the revision only if it loses nothing and closes at least one gap."""
    lost_entities = {e.name for e in original.entities} - {e.name for e in revised.entities}
    if lost_entities:
        return False, f"the revision dropped {', '.join(sorted(lost_entities))}"
    lost_roles = {r.id for r in original.roles} - {r.id for r in revised.roles}
    if lost_roles:
        return False, f"the revision dropped the role(s) {', '.join(sorted(lost_roles))}"
    lost_caps = {c.kind + ":" + c.name for c in original.capabilities} - {c.kind + ":" + c.name for c in revised.capabilities}
    if lost_caps:
        return False, f"the revision dropped {', '.join(sorted(lost_caps))}"
    remaining = critique(prompt, with_endpoints(revised)[0])  # missing endpoints are added without a model anyway
    if len(remaining) >= len(gaps):
        return False, "the revision closed none of the gaps"
    return True, f"closed {len(gaps) - len(remaining)} of {len(gaps)} gaps"


def enabled() -> bool:
    return os.environ.get("OMNISTACKAI_PLAN_REVIEW", "1").strip().lower() not in ("0", "false", "no", "off")


def describe(gaps: list[Gap]) -> list[str]:
    return [f"plan review: {g.text}" for g in gaps]


def as_dict(gap: Gap) -> dict[str, Any]:
    return {"kind": gap.kind, "text": gap.text}

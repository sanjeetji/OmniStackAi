"""Bounded typed follow-up delta schema for editing an existing app (R-468).

A generic sibling of `solution_packs/ai_delta.py`, minus the Solution-Pack coupling: given the app's
CURRENT Application IR and a follow-up instruction ("now add a favorites feature"), the model proposes a
small, strictly bounded, validated delta -- net-new entities, API endpoints, and screens only, never a
restatement of the whole app -- which `apply_app_delta` merges onto the base IR by tuple concatenation.
This module never mutates an IR itself, generates source code, writes files, or calls a cloud model outside
the one explicit `generate_app_delta_proposal` boundary.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, replace
from typing import Any

from ..application_ir import (
    ApiEndpoint,
    ApplicationIR,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    Relation,
    RelationKind,
    Screen,
    validate_ir,
)
from ..application_ir.errors import ApplicationIRError
from . import ir_changes
from ..application_ir.validate import has_errors
from ..model_gateway import ChatRole, GenerateRequest, Message, ModelProvider, ModelRef
from .context import assemble_context

MAX_DELTA_ENTITIES = 8
MAX_DELTA_APIS = 16
MAX_DELTA_SCREENS = 16
MAX_RATIONALE_LENGTH = 500
MAX_FIELDS_PER_ENTITY = 16
MAX_RELATIONS_PER_ENTITY = 8

DEFAULT_APP_DELTA_MAX_OUTPUT_TOKENS = 2_048
DEFAULT_APP_DELTA_TIMEOUT_SECONDS = 300.0
DEFAULT_MAX_ATTEMPTS = 3

_REQUEST_ID_PREFIX = "r468-app-delta"
_MAX_RESPONSE_LENGTH = 64_000
_MAX_ECHO_CHARS = 4_000
_IDENT = re.compile(r"^[a-z][a-z0-9_]*$")
_ENTITY_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
_API_PATH = re.compile(r"^/[A-Za-z0-9/_{}-]*$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_SENSITIVE_FIELD_NAMES = frozenset({
    "api_key",
    "credential",
    "credentials",
    "jwt",
    "password",
    "password_hash",
    "secret",
    "token",
})

_ALLOWED_RELATIONS = frozenset(member.value for member in RelationKind)
_ALLOWED_FIELD_TYPES = frozenset(member.value for member in FieldType)
_ALLOWED_HTTP_METHODS = frozenset(member.value for member in HttpMethod)
_VALID_PROPOSAL_KEYS = frozenset({"entities", "apis", "screens", "rationale", "changes"})


class AppDeltaError(Exception):
    """Raised when a follow-up delta proposal is malformed, invalid, or collides with the base IR."""


#: R-584: how many things one edit may change. Bounded for the same reason the additions are —
#: a follow-up that rewrites half an application is not an edit, and an unbounded list of removals
#: is the shape of a very bad afternoon.
MAX_DELTA_CHANGES = 12


@dataclass(frozen=True, slots=True)
class IrChange:
    """One change to something that already exists (R-584).

    `op` is the name of a function in `ir_changes`. Keeping the operation as data rather than as a
    branch means the reply can say what an edit will do — including that it destroys data — before
    anything is applied.
    """

    op: str
    entity: str = ""
    name: str = ""
    new_name: str = ""
    field_type: str = ""
    required: bool = False
    method: str = ""
    path: str = ""

    def __post_init__(self) -> None:
        if self.op not in _CHANGE_OPS:
            raise AppDeltaError(
                f"unknown change operation {self.op!r}; allowed: {', '.join(sorted(_CHANGE_OPS))}"
            )

    @property
    def is_destructive(self) -> bool:
        return self.op in ir_changes.DESTRUCTIVE


@dataclass(frozen=True, slots=True)
class AppDeltaProposal:
    """A bounded, validated follow-up delta.

    R-584: `changes` describes what happens to things that already exist. Before it, this carried
    net-new entities, endpoints and screens only, and the parser raised on anything else — so
    "rename Post to Article" and "remove the published field" had no way through, and "add a notes
    field" either errored or proposed nothing and reported that no files needed changing.
    """

    entities: tuple[Entity, ...] = ()
    apis: tuple[ApiEndpoint, ...] = ()
    screens: tuple[Screen, ...] = ()
    changes: tuple[IrChange, ...] = ()
    rationale: str = ""
    context_truncated: bool = False
    active_skills: tuple[str, ...] = ()
    truncated_skills: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.entities, tuple):
            raise AppDeltaError("entities must be a tuple")
        if len(self.entities) > MAX_DELTA_ENTITIES:
            raise AppDeltaError(f"entities count cannot exceed {MAX_DELTA_ENTITIES}")
        for entity in self.entities:
            if not isinstance(entity, Entity):
                raise AppDeltaError("entities items must be Entity instances")
        entity_names = [e.name for e in self.entities]
        if len(set(entity_names)) != len(entity_names):
            raise AppDeltaError("entity names must be unique within the proposal")

        if not isinstance(self.apis, tuple):
            raise AppDeltaError("apis must be a tuple")
        if len(self.apis) > MAX_DELTA_APIS:
            raise AppDeltaError(f"apis count cannot exceed {MAX_DELTA_APIS}")
        for api in self.apis:
            if not isinstance(api, ApiEndpoint):
                raise AppDeltaError("apis items must be ApiEndpoint instances")
        api_signatures = [(api.method, api.path) for api in self.apis]
        if len(set(api_signatures)) != len(api_signatures):
            raise AppDeltaError("api endpoint (method, path) pairs must be unique within the proposal")

        if not isinstance(self.screens, tuple):
            raise AppDeltaError("screens must be a tuple")
        if len(self.screens) > MAX_DELTA_SCREENS:
            raise AppDeltaError(f"screens count cannot exceed {MAX_DELTA_SCREENS}")
        for screen in self.screens:
            if not isinstance(screen, Screen):
                raise AppDeltaError("screens items must be Screen instances")
        screen_ids = [s.id for s in self.screens]
        if len(set(screen_ids)) != len(screen_ids):
            raise AppDeltaError("screen ids must be unique within the proposal")

        if not isinstance(self.rationale, str):
            raise AppDeltaError("rationale must be a string")
        if len(self.rationale) > MAX_RATIONALE_LENGTH:
            raise AppDeltaError(f"rationale must not exceed {MAX_RATIONALE_LENGTH} characters")
        if _CONTROL.search(self.rationale):
            raise AppDeltaError("rationale must not contain control characters")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "entities": [entity.to_dict() for entity in self.entities],
            "apis": [api.to_dict() for api in self.apis],
            "screens": [screen.to_dict() for screen in self.screens],
            "rationale": self.rationale,
        }
        if self.context_truncated or self.active_skills or self.truncated_skills:
            d["context_truncated"] = self.context_truncated
            d["active_skills"] = list(self.active_skills)
            d["truncated_skills"] = list(self.truncated_skills)
        return d


def build_app_delta_messages(
    base_ir: ApplicationIR,
    follow_up_prompt: str,
    *,
    context_text: str | None = None,
) -> tuple[Message, Message]:
    """Build the bounded JSON-only instruction for proposing a follow-up delta onto ``base_ir``."""
    if not isinstance(follow_up_prompt, str) or not follow_up_prompt.strip():
        raise AppDeltaError("follow-up prompt must be non-empty text")

    field_types = ", ".join(sorted(_ALLOWED_FIELD_TYPES))
    relation_types = ", ".join(sorted(_ALLOWED_RELATIONS))
    http_methods = ", ".join(sorted(_ALLOWED_HTTP_METHODS))

    existing_entities = [{"name": e.name, "fields": [f.name for f in e.fields]} for e in base_ir.entities]
    existing_apis = [f"{api.method.value} {api.path}" for api in base_ir.apis]
    existing_screens = [s.id for s in base_ir.screens]
    existing_roles = [r.id for r in base_ir.roles]

    system = (
        "You are OmniStackAI's bounded App Follow-Up Delta Proposer.\n"
        "The user already has a working app and wants to change it. Propose the new entities, APIs "
        "and screens they need, and describe anything that happens to what already exists as a "
        "`changes` entry -- never restate an existing entity in `entities` to modify it.\n"
        "Return ONLY one JSON object with exactly these allowed keys: entities, apis, screens, "
        "changes, rationale. No markdown or prose.\n\n"
        # R-584: before this, the only way to say "add a notes field" was to restate the entity,
        # which the parser rejected -- or to propose nothing, which reported that no files needed
        # changing. Both looked like the platform ignoring the request.
        f"- changes: 0 to {MAX_DELTA_CHANGES} objects describing what happens to existing things. "
        "Each has an `op` and the fields that operation needs:\n"
        "  * add_field: {op, entity, name, field_type, required} -- add a field to an existing entity\n"
        "  * remove_field: {op, entity, name} -- removes the column and its data\n"
        "  * rename_field: {op, entity, name, new_name}\n"
        "  * rename_entity: {op, name, new_name} -- every endpoint, screen and relation follows it\n"
        "  * remove_entity: {op, name} -- removes its endpoints, screens and fixtures too\n"
        "  * remove_api: {op, method, path}\n"
        "  * remove_screen: {op, name}\n"
        "  Use add_field for \"add a notes field to X\"; do NOT put X in `entities`.\n\n"
        "Bounds and rules:\n"
        f"- entities: 0 to {MAX_DELTA_ENTITIES} objects {{name, fields, relations}}. Names must be PascalCase "
        "alphanumeric and MUST NOT collide with any existing entity listed below.\n"
        f"- Every entity has 1-{MAX_FIELDS_PER_ENTITY} fields: {{name, type, required}}. Field name MUST be "
        "lower_snake_case. Every entity MUST include a required uuid field named id.\n"
        f"- Field types must be one of: {field_types}.\n"
        f"- Relations: 0 to {MAX_RELATIONS_PER_ENTITY} objects {{name, target_entity, kind}}. Relation names "
        f"must be lower_snake_case. Kind must be one of: {relation_types}. target_entity must be an existing "
        "entity or one of the new entities in this same proposal.\n"
        "- NEVER output credentials, secrets, tokens, passwords, password hashes, jwt, or api keys. "
        "Identity and auth are handled by the platform.\n"
        f"- apis: 0 to {MAX_DELTA_APIS} objects {{method, path, auth}}. Method must be one of: {http_methods}. "
        "Path must start with /, use lower_snake_case for literal segments, and camelCase for any "
        "{param} placeholder (e.g. {counterId}, not {counter_id}) — reuse the exact same placeholder "
        "name already used elsewhere in this app for the same resource, never invent a new spelling "
        "for it. Path MUST NOT collide with any existing endpoint listed below.\n"
        f"- screens: 0 to {MAX_DELTA_SCREENS} objects {{id, role}}. Screen id must be lower_snake_case and MUST "
        "NOT collide with any existing screen listed below; role MUST be one of the existing roles listed below "
        "(a new role cannot be created).\n"
        f"- rationale: concise explanation of the delta, at most {MAX_RATIONALE_LENGTH} characters.\n"
        "- Do not output source code, file paths, shell commands, or values not justified by the request."
    )
    if context_text and context_text.strip():
        system = f"{context_text.strip()}\n\n{system}"
    user = (
        f"Existing Entities: {json.dumps(existing_entities, sort_keys=True)}\n"
        f"Existing APIs: {json.dumps(existing_apis, sort_keys=True)}\n"
        f"Existing Screens: {json.dumps(existing_screens, sort_keys=True)}\n"
        f"Existing Roles: {json.dumps(existing_roles, sort_keys=True)}\n\n"
        f"Requested change:\n{follow_up_prompt.strip()}\n\n"
        "Return the bounded proposal JSON object only."
    )
    return (Message(ChatRole.SYSTEM, system), Message(ChatRole.USER, user))


def _extract_json_object(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise AppDeltaError("model returned an empty response")
    if len(text) > _MAX_RESPONSE_LENGTH:
        raise AppDeltaError(f"model response exceeded {_MAX_RESPONSE_LENGTH} characters")
    if _CONTROL.search(text):
        raise AppDeltaError("model response contained invalid control characters")

    stripped = text.strip()
    if "```" in stripped:
        start = stripped.find("\n", stripped.find("```"))
        end = stripped.find("```", start + 1)
        if start != -1 and end != -1:
            stripped = stripped[start + 1 : end].strip()
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first == -1 or last < first:
        raise AppDeltaError("model response did not contain a valid JSON object")
    try:
        parsed = json.loads(stripped[first : last + 1])
    except json.JSONDecodeError as error:
        raise AppDeltaError(f"model response was not valid JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise AppDeltaError("model response JSON must be a dict")
    return parsed


def parse_app_delta_proposal(text: str, *, base_ir: ApplicationIR) -> AppDeltaProposal:
    """Strictly parse and validate untrusted model output into an AppDeltaProposal."""
    data = _extract_json_object(text)

    extra_keys = set(data.keys()) - _VALID_PROPOSAL_KEYS
    if extra_keys:
        raise AppDeltaError(f"model response contained unknown keys: {sorted(extra_keys)}")

    existing_entity_names = {e.name for e in base_ir.entities}
    raw_entities = data.get("entities", [])
    if not isinstance(raw_entities, list):
        raise AppDeltaError("entities must be a list")
    if len(raw_entities) > MAX_DELTA_ENTITIES:
        raise AppDeltaError(f"entities count cannot exceed {MAX_DELTA_ENTITIES}")

    parsed_entities: list[Entity] = []
    new_entity_names: set[str] = set()
    for idx, raw_entity in enumerate(raw_entities):
        if not isinstance(raw_entity, dict):
            raise AppDeltaError(f"entities[{idx}] must be an object")
        allowed_entity_keys = {"name", "fields", "relations"}
        unknown = set(raw_entity.keys()) - allowed_entity_keys
        if unknown:
            raise AppDeltaError(f"entities[{idx}] contains unknown keys: {sorted(unknown)}")

        name = raw_entity.get("name")
        if not isinstance(name, str) or not _ENTITY_NAME.fullmatch(name) or len(name) > 64:
            raise AppDeltaError(f"entities[{idx}].name must be a 1-64 char alphanumeric identifier: {name!r}")
        if name in existing_entity_names:
            raise AppDeltaError(f"proposed entity '{name}' already exists in the app")
        if name in new_entity_names:
            raise AppDeltaError(f"duplicate proposed entity name: {name!r}")
        new_entity_names.add(name)

        raw_fields = raw_entity.get("fields")
        if not isinstance(raw_fields, list) or not raw_fields:
            raise AppDeltaError(f"entity {name} fields must be a non-empty list")
        if len(raw_fields) > MAX_FIELDS_PER_ENTITY:
            raise AppDeltaError(f"entity {name} cannot declare more than {MAX_FIELDS_PER_ENTITY} fields")

        parsed_fields: list[Field] = []
        has_id = False
        for f_idx, raw_field in enumerate(raw_fields):
            if not isinstance(raw_field, dict):
                raise AppDeltaError(f"entity {name} fields[{f_idx}] must be an object")
            f_name = raw_field.get("name")
            if not isinstance(f_name, str) or not _IDENT.fullmatch(f_name) or len(f_name) > 64:
                raise AppDeltaError(f"entity {name} field name must be lower_snake_case: {f_name!r}")
            if f_name.lower() in _SENSITIVE_FIELD_NAMES:
                raise AppDeltaError(f"credential field disallowed in entity {name}: {f_name!r}")

            f_type_str = raw_field.get("type")
            if f_type_str not in _ALLOWED_FIELD_TYPES:
                raise AppDeltaError(f"entity {name} field {f_name} has unsupported type: {f_type_str!r}")
            f_type = FieldType(f_type_str)

            f_required = raw_field.get("required")
            if not isinstance(f_required, bool):
                raise AppDeltaError(f"entity {name} field {f_name} required must be a boolean")

            if f_name == "id":
                if f_type is not FieldType.UUID or not f_required:
                    raise AppDeltaError(f"entity {name} id field must be a required UUID")
                has_id = True

            parsed_fields.append(Field(name=f_name, type=f_type, required=f_required))

        if not has_id:
            raise AppDeltaError(f"entity {name} must include a required UUID id field")

        raw_relations = raw_entity.get("relations", [])
        if not isinstance(raw_relations, list):
            raise AppDeltaError(f"entity {name} relations must be a list")
        if len(raw_relations) > MAX_RELATIONS_PER_ENTITY:
            raise AppDeltaError(f"entity {name} cannot declare more than {MAX_RELATIONS_PER_ENTITY} relations")
        parsed_relations: list[Relation] = []
        for r_idx, raw_rel in enumerate(raw_relations):
            if not isinstance(raw_rel, dict):
                raise AppDeltaError(f"entity {name} relations[{r_idx}] must be an object")
            r_name = raw_rel.get("name")
            if not isinstance(r_name, str) or not _IDENT.fullmatch(r_name):
                raise AppDeltaError(f"entity {name} relation name must be lower_snake_case: {r_name!r}")
            r_target = raw_rel.get("target_entity")
            if not isinstance(r_target, str) or not _ENTITY_NAME.fullmatch(r_target):
                raise AppDeltaError(f"entity {name} relation target_entity must be PascalCase: {r_target!r}")
            r_kind_str = raw_rel.get("kind")
            if r_kind_str not in _ALLOWED_RELATIONS:
                raise AppDeltaError(f"entity {name} relation {r_name} has unsupported kind: {r_kind_str!r}")
            parsed_relations.append(Relation(name=r_name, target_entity=r_target, kind=RelationKind(r_kind_str)))

        try:
            parsed_entities.append(Entity(name=name, fields=tuple(parsed_fields), relations=tuple(parsed_relations)))
        except ApplicationIRError as error:
            raise AppDeltaError(f"proposed entity {name} is invalid: {error}") from error

    existing_api_signatures = {(api.method, api.path) for api in base_ir.apis}
    raw_apis = data.get("apis", [])
    if not isinstance(raw_apis, list):
        raise AppDeltaError("apis must be a list")
    if len(raw_apis) > MAX_DELTA_APIS:
        raise AppDeltaError(f"apis count cannot exceed {MAX_DELTA_APIS}")

    parsed_apis: list[ApiEndpoint] = []
    for idx, raw_api in enumerate(raw_apis):
        if not isinstance(raw_api, dict):
            raise AppDeltaError(f"apis[{idx}] must be an object")
        method_str = raw_api.get("method")
        if method_str not in _ALLOWED_HTTP_METHODS:
            raise AppDeltaError(f"apis[{idx}] has unsupported method: {method_str!r}")
        method = HttpMethod(method_str)

        path = raw_api.get("path")
        if not isinstance(path, str) or not _API_PATH.fullmatch(path) or len(path) > 256:
            raise AppDeltaError(f"apis[{idx}] has invalid path: {path!r}")
        if (method, path) in existing_api_signatures:
            raise AppDeltaError(f"proposed endpoint {method.value} {path} already exists in the app")

        auth = raw_api.get("auth", True)
        if not isinstance(auth, bool):
            raise AppDeltaError(f"apis[{idx}].auth must be a boolean")

        try:
            parsed_apis.append(
                ApiEndpoint(
                    method=method,
                    path=path,
                    auth=auth,
                    request_schema=raw_api.get("request_schema"),
                    response_schema=raw_api.get("response_schema"),
                )
            )
        except ApplicationIRError as error:
            raise AppDeltaError(f"proposed endpoint {method.value} {path} is invalid: {error}") from error

    existing_screen_ids = {s.id for s in base_ir.screens}
    existing_role_ids = {r.id for r in base_ir.roles}
    raw_screens = data.get("screens", [])
    if not isinstance(raw_screens, list):
        raise AppDeltaError("screens must be a list")
    if len(raw_screens) > MAX_DELTA_SCREENS:
        raise AppDeltaError(f"screens count cannot exceed {MAX_DELTA_SCREENS}")

    parsed_screens: list[Screen] = []
    for idx, raw_screen in enumerate(raw_screens):
        if not isinstance(raw_screen, dict):
            raise AppDeltaError(f"screens[{idx}] must be an object")
        s_id = raw_screen.get("id")
        if not isinstance(s_id, str) or not _IDENT.fullmatch(s_id) or len(s_id) > 64:
            raise AppDeltaError(f"screens[{idx}].id must be lower_snake_case: {s_id!r}")
        if s_id in existing_screen_ids:
            raise AppDeltaError(f"proposed screen '{s_id}' already exists in the app")

        role = raw_screen.get("role", "public")
        if not isinstance(role, str) or not _IDENT.fullmatch(role) or len(role) > 64:
            raise AppDeltaError(f"screens[{idx}].role must be lower_snake_case: {role!r}")
        if role not in existing_role_ids:
            raise AppDeltaError(f"screens[{idx}].role {role!r} is not one of the app's existing roles: {sorted(existing_role_ids)}")

        try:
            parsed_screens.append(Screen(id=s_id, role=role))
        except ApplicationIRError as error:
            raise AppDeltaError(f"proposed screen {s_id} is invalid: {error}") from error

    rationale = data.get("rationale", "")
    if not isinstance(rationale, str):
        raise AppDeltaError("rationale must be text")
    if len(rationale) > MAX_RATIONALE_LENGTH:
        raise AppDeltaError(f"rationale cannot exceed {MAX_RATIONALE_LENGTH} characters")
    if _CONTROL.search(rationale):
        raise AppDeltaError("rationale cannot contain control characters")

    # R-584: what happens to things that already exist. Absent from a proposal that only adds,
    # which is every proposal written before this existed.
    raw_changes = data.get("changes", []) or []
    if not isinstance(raw_changes, list):
        raise AppDeltaError("changes must be a list")
    if len(raw_changes) > MAX_DELTA_CHANGES:
        raise AppDeltaError(f"changes count cannot exceed {MAX_DELTA_CHANGES}")
    parsed_changes = []
    for item in raw_changes:
        if not isinstance(item, dict):
            raise AppDeltaError("each change must be an object")
        change = IrChange(
            op=str(item.get("op", "")),
            entity=str(item.get("entity", "") or ""),
            name=str(item.get("name", "") or ""),
            new_name=str(item.get("new_name", "") or ""),
            field_type=str(item.get("field_type", "") or ""),
            required=bool(item.get("required", False)),
            method=str(item.get("method", "") or ""),
            path=str(item.get("path", "") or ""),
        )
        if change.field_type and change.field_type not in _ALLOWED_FIELD_TYPES:
            raise AppDeltaError(f"change field_type must be one of: {', '.join(sorted(_ALLOWED_FIELD_TYPES))}")
        parsed_changes.append(change)

    return AppDeltaProposal(
        entities=tuple(parsed_entities),
        apis=tuple(parsed_apis),
        screens=tuple(parsed_screens),
        changes=tuple(parsed_changes),
        rationale=rationale,
    )


#: The operations a change may name, mapped to how each is applied. Registered here rather than
#: branched inside the applier, so adding one is a line and not a new `elif`.
_CHANGE_OPS: dict[str, str] = {
    "add_field": "add a field to an existing entity",
    "remove_field": "remove a field and the fixture values for it",
    "rename_field": "rename a field, carrying its fixture values",
    "rename_entity": "rename an entity and every reference to it",
    "remove_entity": "remove an entity, its endpoints, screens and fixtures",
    "remove_api": "remove one endpoint",
    "remove_screen": "remove one screen",
}


def _apply_change(ir: ApplicationIR, change: IrChange) -> ApplicationIR:
    """Apply one change, translating a bounded description into an `ir_changes` call."""
    try:
        if change.op == "add_field":
            return ir_changes.add_field(
                ir,
                change.entity,
                Field(
                    name=change.name,
                    type=FieldType(change.field_type or "string"),
                    required=bool(change.required),
                ),
            )
        if change.op == "remove_field":
            return ir_changes.remove_field(ir, change.entity, change.name)
        if change.op == "rename_field":
            return ir_changes.rename_field(ir, change.entity, change.name, change.new_name)
        if change.op == "rename_entity":
            return ir_changes.rename_entity(ir, change.name, change.new_name)
        if change.op == "remove_entity":
            return ir_changes.remove_entity(ir, change.name)
        if change.op == "remove_api":
            return ir_changes.remove_api(ir, change.method, change.path)
        if change.op == "remove_screen":
            return ir_changes.remove_screen(ir, change.name)
    except (ValueError, KeyError) as error:
        raise AppDeltaError(f"{change.op} failed: {error}") from error
    raise AppDeltaError(f"unknown change operation {change.op!r}")


def apply_app_delta(base_ir: ApplicationIR, proposal: AppDeltaProposal) -> ApplicationIR:
    """Merge a validated follow-up delta onto ``base_ir`` and return the new, re-validated IR.

    Independently re-checks every collision (defense in depth, mirroring `solution_packs/application.py`'s
    merge) even though `parse_app_delta_proposal` already rejected them once -- a proposal reaching here
    might not have come through that parser. Never mutates `base_ir`.
    """
    if not isinstance(base_ir, ApplicationIR):
        raise AppDeltaError("base_ir must be an ApplicationIR")
    if not isinstance(proposal, AppDeltaProposal):
        raise AppDeltaError("proposal must be an AppDeltaProposal")

    # R-584: changes first, additions second. A rename has to land before a new endpoint that
    # names the renamed entity, and a removal before an addition that reuses the freed name — the
    # other order makes "rename Post to Article and add a Post draft" impossible to express.
    working = base_ir
    for change in proposal.changes:
        working = _apply_change(working, change)

    base_entity_names = {e.name for e in working.entities}
    for entity in proposal.entities:
        if entity.name in base_entity_names:
            raise AppDeltaError(f"proposed entity '{entity.name}' collides with an existing entity")

    base_api_signatures = {(api.method, api.path) for api in working.apis}
    for api in proposal.apis:
        if (api.method, api.path) in base_api_signatures:
            raise AppDeltaError(f"proposed endpoint '{api.method.value} {api.path}' collides with an existing endpoint")

    base_screen_ids = {s.id for s in working.screens}
    base_role_ids = {r.id for r in working.roles}
    for screen in proposal.screens:
        if screen.id in base_screen_ids:
            raise AppDeltaError(f"proposed screen '{screen.id}' collides with an existing screen")
        if screen.role not in base_role_ids:
            raise AppDeltaError(f"proposed screen '{screen.id}' references unknown role '{screen.role}'")

    all_entity_names = base_entity_names | {e.name for e in proposal.entities}
    for entity in proposal.entities:
        for relation in entity.relations:
            if relation.target_entity not in all_entity_names:
                raise AppDeltaError(
                    f"proposed entity '{entity.name}' relation targets undeclared entity '{relation.target_entity}'"
                )

    try:
        derived_ir = replace(
            # R-584: `working`, not `base_ir`. Rebuilding from the original keeps its fixtures and
            # roles, so a rename produced an IR whose entities said Article while its fixtures
            # still said Post — and validation rejected the edit for a reason the user could do
            # nothing about.
            working,
            entities=working.entities + proposal.entities,
            apis=working.apis + proposal.apis,
            screens=working.screens + proposal.screens,
        )
    except ApplicationIRError as error:
        raise AppDeltaError(f"merged IR is invalid: {error}") from error

    if has_errors(validate_ir(derived_ir)):
        raise AppDeltaError("merged IR failed semantic validation")
    return derived_ir


def _safe_echo(text: str, limit: int = _MAX_ECHO_CHARS) -> str:
    clipped = (text or "")[:limit]
    cleaned = "".join(ch if ch == "\n" or (ch >= " " and ch != "\x7f") else " " for ch in clipped)
    return cleaned.strip() or "(empty response)"


async def generate_app_delta_proposal(
    base_ir: ApplicationIR,
    follow_up_prompt: str,
    provider: ModelProvider,
    *,
    model_id: str | None = None,
    max_output_tokens: int = DEFAULT_APP_DELTA_MAX_OUTPUT_TOKENS,
    timeout_seconds: float = DEFAULT_APP_DELTA_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    context: dict[str, Any] | str | None = None,
) -> AppDeltaProposal:
    """Generate a validated AppDeltaProposal, retrying only on a parse/validation rejection.

    A provider exception (timeout, HTTP error, ...) is never retried -- it propagates immediately, exactly
    like R-465's `_synthesize_file`. Up to `max_attempts` model calls total.
    """
    ref = provider.model_ref() if hasattr(provider, "model_ref") else None
    resolved_provider_id = getattr(provider, "provider_id", None) or (ref.provider_id if ref else "provider")
    resolved_model_id = model_id or (ref.model_id if ref else "model")
    target = ModelRef(resolved_provider_id, resolved_model_id)

    context_text = ""
    is_truncated = False
    active_skills: list[str] = []
    truncated_skills: list[str] = []
    if isinstance(context, dict):
        context_text, is_truncated, active_skills, truncated_skills = assemble_context(context)
    elif isinstance(context, str):
        context_text = context

    messages = list(build_app_delta_messages(base_ir, follow_up_prompt, context_text=context_text))
    attempts_allowed = max(1, int(max_attempts))
    last_reason = ""
    for attempt in range(1, attempts_allowed + 1):
        request = GenerateRequest(
            request_id=f"{_REQUEST_ID_PREFIX}-{uuid.uuid4().hex[:12]}",
            model=target,
            messages=tuple(messages),
            max_output_tokens=max_output_tokens,
            timeout_seconds=timeout_seconds,
        )
        response = await provider.generate(request)  # exceptions propagate immediately; never retried
        try:
            prop = parse_app_delta_proposal(response.text, base_ir=base_ir)
            return AppDeltaProposal(
                entities=prop.entities,
                apis=prop.apis,
                screens=prop.screens,
                rationale=prop.rationale,
                context_truncated=is_truncated,
                active_skills=tuple(active_skills),
                truncated_skills=tuple(truncated_skills),
            )
        except AppDeltaError as error:
            last_reason = str(error)
            if attempt >= attempts_allowed:
                raise
            messages.append(Message(ChatRole.ASSISTANT, _safe_echo(response.text)))
            messages.append(
                Message(
                    ChatRole.USER,
                    f"Your previous proposal was REJECTED: {last_reason}\n"
                    "Return ONLY the corrected, complete JSON object (entities, apis, screens, rationale).",
                )
            )
    raise AppDeltaError(last_reason or "no proposal produced")  # pragma: no cover - loop always returns/raises

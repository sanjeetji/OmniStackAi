"""Bounded typed Solution Pack AI-delta proposal schema and local ModelProvider boundary (R-438).

This module defines a strict, typed proposal schema and an explicit opt-in model boundary that turns
pending manifest AI-delta intents into validated proposal data. It does NOT mutate or apply changes
to an Application IR, generate source code, build repositories, or call cloud models. Manifests
with zero AI-delta changes bypass the provider completely (0 calls).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
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
)
from ..application_ir.errors import ApplicationIRError
from ..model_gateway import (
    ChatRole,
    GenerateRequest,
    Message,
    ModelProvider,
    ModelRef,
)
from .manifest import (
    ChangeArea,
    ChangeOperation,
    ChangeSource,
    SolutionPackChange,
    SolutionPackManifest,
    validate_solution_pack_manifest,
)
from .registry import (
    DEFAULT_SOLUTION_PACK_REGISTRY,
    SolutionPackError,
    SolutionPackRegistry,
    canonical_ir_digest,
)

MAX_DELTA_ENTITIES = 8
MAX_DELTA_APIS = 16
MAX_DELTA_SCREENS = 16
MAX_DELTA_CAPABILITIES = 16
MAX_RATIONALE_LENGTH = 500

DEFAULT_AI_DELTA_MAX_OUTPUT_TOKENS = 2_048
DEFAULT_AI_DELTA_TIMEOUT_SECONDS = 300.0

_REQUEST_ID = "r438-solution-pack-ai-delta"
_MAX_RESPONSE_LENGTH = 64_000
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
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
_VALID_PROPOSAL_KEYS = frozenset({
    "addressed_change_ids",
    "entities",
    "apis",
    "screens",
    "capabilities",
    "rationale",
})


@dataclass(frozen=True, slots=True)
class AIDeltaProposal:
    """A strictly bounded, validated proposal for pending manifest AI-delta intents."""

    pack_id: str
    pack_version: str
    base_ir_sha256: str
    addressed_change_ids: tuple[str, ...]
    entities: tuple[Entity, ...] = ()
    apis: tuple[ApiEndpoint, ...] = ()
    screens: tuple[Screen, ...] = ()
    capabilities: tuple[str, ...] = ()
    rationale: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.pack_id, str) or not self.pack_id:
            raise SolutionPackError("proposal pack_id must be non-empty text")
        if not isinstance(self.pack_version, str) or not self.pack_version:
            raise SolutionPackError("proposal pack_version must be non-empty text")
        if (
            not isinstance(self.base_ir_sha256, str)
            or _SHA256.fullmatch(self.base_ir_sha256) is None
        ):
            raise SolutionPackError("proposal base_ir_sha256 must be a lowercase 64-character SHA-256")

        if not isinstance(self.addressed_change_ids, tuple):
            raise SolutionPackError("addressed_change_ids must be a tuple")
        for cid in self.addressed_change_ids:
            if not isinstance(cid, str) or not cid:
                raise SolutionPackError("addressed_change_ids items must be non-empty strings")
        if len(set(self.addressed_change_ids)) != len(self.addressed_change_ids):
            raise SolutionPackError("addressed_change_ids must not contain duplicates")
        if self.addressed_change_ids != tuple(sorted(self.addressed_change_ids)):
            raise SolutionPackError("addressed_change_ids must be canonically sorted")

        if not isinstance(self.entities, tuple):
            raise SolutionPackError("entities must be a tuple")
        if len(self.entities) > MAX_DELTA_ENTITIES:
            raise SolutionPackError(f"entities count cannot exceed {MAX_DELTA_ENTITIES}")
        for entity in self.entities:
            if not isinstance(entity, Entity):
                raise SolutionPackError("entities items must be Entity instances")
        entity_names = [e.name for e in self.entities]
        if len(set(entity_names)) != len(entity_names):
            raise SolutionPackError("entity names must be unique within the proposal")

        if not isinstance(self.apis, tuple):
            raise SolutionPackError("apis must be a tuple")
        if len(self.apis) > MAX_DELTA_APIS:
            raise SolutionPackError(f"apis count cannot exceed {MAX_DELTA_APIS}")
        for api in self.apis:
            if not isinstance(api, ApiEndpoint):
                raise SolutionPackError("apis items must be ApiEndpoint instances")
        api_signatures = [(api.method, api.path) for api in self.apis]
        if len(set(api_signatures)) != len(api_signatures):
            raise SolutionPackError("api endpoint (method, path) pairs must be unique within the proposal")

        if not isinstance(self.screens, tuple):
            raise SolutionPackError("screens must be a tuple")
        if len(self.screens) > MAX_DELTA_SCREENS:
            raise SolutionPackError(f"screens count cannot exceed {MAX_DELTA_SCREENS}")
        for screen in self.screens:
            if not isinstance(screen, Screen):
                raise SolutionPackError("screens items must be Screen instances")
        screen_ids = [s.id for s in self.screens]
        if len(set(screen_ids)) != len(screen_ids):
            raise SolutionPackError("screen ids must be unique within the proposal")

        if not isinstance(self.capabilities, tuple):
            raise SolutionPackError("capabilities must be a tuple")
        if len(self.capabilities) > MAX_DELTA_CAPABILITIES:
            raise SolutionPackError(f"capabilities count cannot exceed {MAX_DELTA_CAPABILITIES}")
        for cap in self.capabilities:
            if not isinstance(cap, str) or _SLUG.fullmatch(cap) is None:
                raise SolutionPackError("capabilities items must be lowercase hyphenated identifiers")
        if len(set(self.capabilities)) != len(self.capabilities):
            raise SolutionPackError("capabilities must not contain duplicates")
        if self.capabilities != tuple(sorted(self.capabilities)):
            raise SolutionPackError("capabilities must be canonically sorted")

        if not isinstance(self.rationale, str):
            raise SolutionPackError("rationale must be a string")
        if len(self.rationale) > MAX_RATIONALE_LENGTH:
            raise SolutionPackError(f"rationale must not exceed {MAX_RATIONALE_LENGTH} characters")
        if _CONTROL.search(self.rationale):
            raise SolutionPackError("rationale must not contain control characters")

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "base_ir_sha256": self.base_ir_sha256,
            "addressed_change_ids": list(self.addressed_change_ids),
            "entities": [entity.to_dict() for entity in self.entities],
            "apis": [api.to_dict() for api in self.apis],
            "screens": [screen.to_dict() for screen in self.screens],
            "capabilities": list(self.capabilities),
            "rationale": self.rationale,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )


def build_ai_delta_messages(
    manifest: SolutionPackManifest, base_ir: ApplicationIR
) -> tuple[Message, ...]:
    """Build the bounded JSON-only instruction for proposing pending manifest AI-delta intents."""
    ai_delta_changes = [
        change for change in manifest.changes if change.source is ChangeSource.AI_DELTA
    ]
    if not ai_delta_changes:
        raise SolutionPackError("manifest does not contain any pending AI-delta changes")

    field_types = ", ".join(sorted(_ALLOWED_FIELD_TYPES))
    relation_types = ", ".join(sorted(_ALLOWED_RELATIONS))
    http_methods = ", ".join(sorted(_ALLOWED_HTTP_METHODS))

    existing_entities = [
        {"name": e.name, "fields": [f.name for f in e.fields]}
        for e in base_ir.entities
    ]
    existing_apis = [f"{api.method.value} {api.path}" for api in base_ir.apis]
    existing_screens = [s.id for s in base_ir.screens]

    delta_intents = [
        {
            "change_id": c.change_id,
            "operation": c.operation.value,
            "area": c.area.value,
            "target": c.target,
            "summary": c.summary,
            "acceptance_criteria": list(c.acceptance_criteria),
        }
        for c in ai_delta_changes
    ]

    system = (
        "You are OmniStackAI's bounded Solution Pack AI-Delta Proposer.\n"
        "Your role is to propose concrete, typed schema extensions (entities, APIs, screens, capabilities) "
        "to fulfill the specific pending AI-delta intent items from the customization manifest.\n"
        "Return ONLY one JSON object with exactly these allowed keys: "
        "addressed_change_ids, entities, apis, screens, capabilities, rationale. No markdown or prose.\n\n"
        "Bounds and rules:\n"
        f"- addressed_change_ids: list of change IDs addressed from the manifest.\n"
        f"- entities: 0 to {MAX_DELTA_ENTITIES} objects {{name, fields, relations}}. Names must be PascalCase alphanumeric "
        "and MUST NOT collide with existing base entities.\n"
        "- Every entity has 1-16 fields: {name, type, required}. Field name MUST be lower_snake_case. "
        "Every entity MUST include a required uuid field named id.\n"
        f"- Field types must be one of: {field_types}.\n"
        "- Relations: 0 to 8 objects {name, target_entity, kind}. Relation names must be lower_snake_case. "
        f"Kind must be one of: {relation_types}.\n"
        "- NEVER output credentials, secrets, tokens, passwords, password hashes, jwt, or api keys. "
        "Identity and auth are handled by the platform.\n"
        f"- apis: 0 to {MAX_DELTA_APIS} objects {{method, path, auth}}. Method must be one of: {http_methods}. "
        "Path must start with / and use lower_snake_case segments. Auth is a boolean.\n"
        f"- screens: 0 to {MAX_DELTA_SCREENS} objects {{id, role}}. Screen id and role must be lower_snake_case.\n"
        f"- capabilities: 0 to {MAX_DELTA_CAPABILITIES} lowercase hyphenated slugs.\n"
        f"- rationale: concise explanation of the delta, at most {MAX_RATIONALE_LENGTH} characters.\n"
        "- Do not output source code, file paths, shell commands, or values not justified by the intent."
    )

    user = (
        f"Base Solution Pack: {manifest.pack_id}@{manifest.pack_version}\n"
        f"Base Entities: {json.dumps(existing_entities, sort_keys=True)}\n"
        f"Base APIs: {json.dumps(existing_apis, sort_keys=True)}\n"
        f"Base Screens: {json.dumps(existing_screens, sort_keys=True)}\n\n"
        f"Pending AI-Delta Intents to satisfy:\n"
        f"{json.dumps(delta_intents, indent=2, sort_keys=True)}\n\n"
        "Return the bounded proposal JSON object only."
    )

    return (Message(ChatRole.SYSTEM, system), Message(ChatRole.USER, user))


def _extract_json_object(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise SolutionPackError("model returned an empty response")
    if len(text) > _MAX_RESPONSE_LENGTH:
        raise SolutionPackError(f"model response exceeded {_MAX_RESPONSE_LENGTH} characters")
    if _CONTROL.search(text):
        raise SolutionPackError("model response contained invalid control characters")

    stripped = text.strip()
    if "```" in stripped:
        start = stripped.find("\n", stripped.find("```"))
        end = stripped.find("```", start + 1)
        if start != -1 and end != -1:
            stripped = stripped[start + 1 : end].strip()
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first == -1 or last < first:
        raise SolutionPackError("model response did not contain a valid JSON object")
    try:
        parsed = json.loads(stripped[first : last + 1])
    except json.JSONDecodeError as err:
        raise SolutionPackError(f"model response was not valid JSON: {err}") from err
    if not isinstance(parsed, dict):
        raise SolutionPackError("model response JSON must be a dict")
    return parsed


def parse_ai_delta_proposal(
    text: str, *, manifest: SolutionPackManifest, base_ir: ApplicationIR
) -> AIDeltaProposal:
    """Strictly parse and validate untrusted model output into an AIDeltaProposal."""
    data = _extract_json_object(text)

    extra_keys = set(data.keys()) - _VALID_PROPOSAL_KEYS
    if extra_keys:
        raise SolutionPackError(f"model response contained unknown keys: {sorted(extra_keys)}")

    pending_change_ids = {
        c.change_id for c in manifest.changes if c.source is ChangeSource.AI_DELTA
    }

    raw_addressed = data.get("addressed_change_ids")
    if not isinstance(raw_addressed, list) or not raw_addressed:
        raise SolutionPackError("addressed_change_ids must be a non-empty list of change IDs")
    for cid in raw_addressed:
        if not isinstance(cid, str) or cid not in pending_change_ids:
            raise SolutionPackError(f"addressed change id {cid!r} is not a pending AI-delta in the manifest")
    addressed_change_ids = tuple(sorted(set(raw_addressed)))

    existing_entity_names = {e.name for e in base_ir.entities}
    raw_entities = data.get("entities", [])
    if not isinstance(raw_entities, list):
        raise SolutionPackError("entities must be a list")
    if len(raw_entities) > MAX_DELTA_ENTITIES:
        raise SolutionPackError(f"entities count cannot exceed {MAX_DELTA_ENTITIES}")

    parsed_entities: list[Entity] = []
    new_entity_names: set[str] = set()

    for idx, raw_entity in enumerate(raw_entities):
        if not isinstance(raw_entity, dict):
            raise SolutionPackError(f"entities[{idx}] must be an object")
        allowed_entity_keys = {"name", "fields", "relations", "indexes"}
        if set(raw_entity.keys()) - allowed_entity_keys:
            raise SolutionPackError(f"entities[{idx}] contains unknown keys: {sorted(set(raw_entity.keys()) - allowed_entity_keys)}")

        name = raw_entity.get("name")
        if not isinstance(name, str) or not _ENTITY_NAME.fullmatch(name) or len(name) > 64:
            raise SolutionPackError(f"entities[{idx}].name must be a 1-64 char alphanumeric identifier: {name!r}")
        if name in existing_entity_names:
            raise SolutionPackError(f"proposed entity {name!r} already exists in the base Application IR")
        if name in new_entity_names:
            raise SolutionPackError(f"duplicate proposed entity name: {name!r}")
        new_entity_names.add(name)

        raw_fields = raw_entity.get("fields")
        if not isinstance(raw_fields, list) or not raw_fields:
            raise SolutionPackError(f"entity {name} fields must be a non-empty list")
        if len(raw_fields) > 16:
            raise SolutionPackError(f"entity {name} cannot declare more than 16 fields")

        parsed_fields: list[Field] = []
        has_id = False
        for f_idx, raw_field in enumerate(raw_fields):
            if not isinstance(raw_field, dict):
                raise SolutionPackError(f"entity {name} fields[{f_idx}] must be an object")
            f_name = raw_field.get("name")
            if not isinstance(f_name, str) or not _IDENT.fullmatch(f_name) or len(f_name) > 64:
                raise SolutionPackError(f"entity {name} field name must be lower_snake_case: {f_name!r}")
            if f_name.lower() in _SENSITIVE_FIELD_NAMES:
                raise SolutionPackError(f"credential field disallowed in entity {name}: {f_name!r}")

            f_type_str = raw_field.get("type")
            if f_type_str not in _ALLOWED_FIELD_TYPES:
                raise SolutionPackError(f"entity {name} field {f_name} has unsupported type: {f_type_str!r}")
            f_type = FieldType(f_type_str)

            f_required = raw_field.get("required")
            if not isinstance(f_required, bool):
                raise SolutionPackError(f"entity {name} field {f_name} required must be a boolean")

            if f_name == "id":
                if f_type is not FieldType.UUID or not f_required:
                    raise SolutionPackError(f"entity {name} id field must be a required UUID")
                has_id = True

            raw_val = raw_field.get("validation", [])
            if not isinstance(raw_val, list):
                raise SolutionPackError(f"entity {name} field {f_name} validation must be a list")
            raw_unique = raw_field.get("unique", False)
            if not isinstance(raw_unique, bool):
                raise SolutionPackError(f"entity {name} field {f_name} unique must be a boolean")

            parsed_fields.append(
                Field(
                    name=f_name,
                    type=f_type,
                    required=f_required,
                    validation=tuple(str(v) for v in raw_val),
                    unique=raw_unique,
                )
            )

        if not has_id:
            raise SolutionPackError(f"entity {name} must include a required UUID id field")

        raw_relations = raw_entity.get("relations", [])
        if not isinstance(raw_relations, list):
            raise SolutionPackError(f"entity {name} relations must be a list")
        parsed_relations: list[Relation] = []
        for r_idx, raw_rel in enumerate(raw_relations):
            if not isinstance(raw_rel, dict):
                raise SolutionPackError(f"entity {name} relations[{r_idx}] must be an object")
            r_name = raw_rel.get("name")
            if not isinstance(r_name, str) or not _IDENT.fullmatch(r_name):
                raise SolutionPackError(f"entity {name} relation name must be lower_snake_case: {r_name!r}")
            r_target = raw_rel.get("target_entity")
            if not isinstance(r_target, str) or not _ENTITY_NAME.fullmatch(r_target):
                raise SolutionPackError(f"entity {name} relation target_entity must be PascalCase: {r_target!r}")
            r_kind_str = raw_rel.get("kind")
            if r_kind_str not in _ALLOWED_RELATIONS:
                raise SolutionPackError(f"entity {name} relation {r_name} has unsupported kind: {r_kind_str!r}")
            parsed_relations.append(
                Relation(name=r_name, target_entity=r_target, kind=RelationKind(r_kind_str))
            )

        try:
            parsed_entities.append(
                Entity(
                    name=name,
                    fields=tuple(parsed_fields),
                    relations=tuple(parsed_relations),
                )
            )
        except ApplicationIRError as err:
            raise SolutionPackError(f"proposed entity {name} is invalid: {err}") from err

    existing_api_signatures = {(api.method, api.path) for api in base_ir.apis}
    raw_apis = data.get("apis", [])
    if not isinstance(raw_apis, list):
        raise SolutionPackError("apis must be a list")
    if len(raw_apis) > MAX_DELTA_APIS:
        raise SolutionPackError(f"apis count cannot exceed {MAX_DELTA_APIS}")

    parsed_apis: list[ApiEndpoint] = []
    for idx, raw_api in enumerate(raw_apis):
        if not isinstance(raw_api, dict):
            raise SolutionPackError(f"apis[{idx}] must be an object")
        method_str = raw_api.get("method")
        if method_str not in _ALLOWED_HTTP_METHODS:
            raise SolutionPackError(f"apis[{idx}] has unsupported method: {method_str!r}")
        method = HttpMethod(method_str)

        path = raw_api.get("path")
        if not isinstance(path, str) or not _API_PATH.fullmatch(path) or len(path) > 256:
            raise SolutionPackError(f"apis[{idx}] has invalid path: {path!r}")

        if (method, path) in existing_api_signatures:
            raise SolutionPackError(f"proposed endpoint {method.value} {path} already exists in base IR")

        auth = raw_api.get("auth", True)
        if not isinstance(auth, bool):
            raise SolutionPackError(f"apis[{idx}].auth must be a boolean")

        roles = raw_api.get("required_roles", [])
        if not isinstance(roles, list):
            raise SolutionPackError(f"apis[{idx}].required_roles must be a list")

        try:
            parsed_apis.append(
                ApiEndpoint(
                    method=method,
                    path=path,
                    auth=auth,
                    request_schema=raw_api.get("request_schema"),
                    response_schema=raw_api.get("response_schema"),
                    error_schema=raw_api.get("error_schema"),
                    required_roles=tuple(str(r) for r in roles),
                )
            )
        except ApplicationIRError as err:
            raise SolutionPackError(f"proposed endpoint {method.value} {path} is invalid: {err}") from err

    existing_screen_ids = {s.id for s in base_ir.screens}
    raw_screens = data.get("screens", [])
    if not isinstance(raw_screens, list):
        raise SolutionPackError("screens must be a list")
    if len(raw_screens) > MAX_DELTA_SCREENS:
        raise SolutionPackError(f"screens count cannot exceed {MAX_DELTA_SCREENS}")

    parsed_screens: list[Screen] = []
    for idx, raw_screen in enumerate(raw_screens):
        if not isinstance(raw_screen, dict):
            raise SolutionPackError(f"screens[{idx}] must be an object")
        s_id = raw_screen.get("id")
        if not isinstance(s_id, str) or not _IDENT.fullmatch(s_id) or len(s_id) > 64:
            raise SolutionPackError(f"screens[{idx}].id must be lower_snake_case: {s_id!r}")
        if s_id in existing_screen_ids:
            raise SolutionPackError(f"proposed screen {s_id!r} already exists in base IR")

        role = raw_screen.get("role", "public")
        if not isinstance(role, str) or not _IDENT.fullmatch(role) or len(role) > 64:
            raise SolutionPackError(f"screens[{idx}].role must be lower_snake_case: {role!r}")

        comps = raw_screen.get("components", [])
        actions = raw_screen.get("actions", [])
        nav = raw_screen.get("navigation", [])

        try:
            parsed_screens.append(
                Screen(
                    id=s_id,
                    role=role,
                    components=tuple(str(c) for c in comps),
                    actions=tuple(str(a) for a in actions),
                    navigation=tuple(str(n) for n in nav),
                )
            )
        except ApplicationIRError as err:
            raise SolutionPackError(f"proposed screen {s_id} is invalid: {err}") from err

    raw_capabilities = data.get("capabilities", [])
    if not isinstance(raw_capabilities, list):
        raise SolutionPackError("capabilities must be a list")
    if len(raw_capabilities) > MAX_DELTA_CAPABILITIES:
        raise SolutionPackError(f"capabilities count cannot exceed {MAX_DELTA_CAPABILITIES}")
    parsed_capabilities: list[str] = []
    for c_idx, cap in enumerate(raw_capabilities):
        if not isinstance(cap, str) or _SLUG.fullmatch(cap) is None or len(cap) > 64:
            raise SolutionPackError(f"capabilities[{c_idx}] must be a lowercase hyphenated slug: {cap!r}")
        parsed_capabilities.append(cap)
    capabilities = tuple(sorted(set(parsed_capabilities)))

    rationale = data.get("rationale", "")
    if not isinstance(rationale, str):
        raise SolutionPackError("rationale must be text")
    if len(rationale) > MAX_RATIONALE_LENGTH:
        raise SolutionPackError(f"rationale cannot exceed {MAX_RATIONALE_LENGTH} characters")
    if _CONTROL.search(rationale):
        raise SolutionPackError("rationale cannot contain control characters")

    return AIDeltaProposal(
        pack_id=manifest.pack_id,
        pack_version=manifest.pack_version,
        base_ir_sha256=manifest.pack_ir_sha256,
        addressed_change_ids=addressed_change_ids,
        entities=tuple(parsed_entities),
        apis=tuple(parsed_apis),
        screens=tuple(parsed_screens),
        capabilities=capabilities,
        rationale=rationale,
    )


async def generate_ai_delta_proposal(
    manifest: SolutionPackManifest,
    base_ir: ApplicationIR,
    provider: ModelProvider,
    *,
    model_id: str | None = None,
    max_output_tokens: int = DEFAULT_AI_DELTA_MAX_OUTPUT_TOKENS,
    timeout_seconds: float = DEFAULT_AI_DELTA_TIMEOUT_SECONDS,
    registry: SolutionPackRegistry = DEFAULT_SOLUTION_PACK_REGISTRY,
) -> AIDeltaProposal:
    """Generate a validated AIDeltaProposal using the provider, or bypass when no AI deltas exist."""
    validate_solution_pack_manifest(manifest, registry=registry)

    ai_delta_changes = tuple(
        change for change in manifest.changes if change.source is ChangeSource.AI_DELTA
    )
    if not ai_delta_changes:
        # Zero model calls when no AI-delta changes are pending
        return AIDeltaProposal(
            pack_id=manifest.pack_id,
            pack_version=manifest.pack_version,
            base_ir_sha256=manifest.pack_ir_sha256,
            addressed_change_ids=(),
            entities=(),
            apis=(),
            screens=(),
            capabilities=(),
            rationale="No AI-delta changes requested in manifest.",
        )

    ref = provider.model_ref() if hasattr(provider, "model_ref") else None
    resolved_provider_id = getattr(provider, "provider_id", None) or (ref.provider_id if ref else "provider")
    resolved_model_id = model_id or (ref.model_id if ref else "model")
    messages = build_ai_delta_messages(manifest, base_ir)
    request = GenerateRequest(
        _REQUEST_ID,
        ModelRef(resolved_provider_id, resolved_model_id),
        messages,
        max_output_tokens,
        timeout_seconds,
    )
    response = await provider.generate(request)
    return parse_ai_delta_proposal(response.text, manifest=manifest, base_ir=base_ir)

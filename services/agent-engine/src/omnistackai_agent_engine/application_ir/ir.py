"""Framework-neutral Application IR (Brief 9).

The IR is the validated source of truth between user intent and generated targets. It is pure data:
no network, no framework knowledge, no code generation. Every record is immutable and validated on
construction; the top-level `ApplicationIR` additionally cross-validates references and round-trips
losslessly through `to_dict`/`from_dict` with an explicit schema version.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .errors import InvalidIRError, UnsupportedIRVersionError

IR_SCHEMA_VERSION = 1

_IDENT = re.compile(r"^[a-z][a-z0-9_]*$")
_ENTITY_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
_API_PATH = re.compile(r"^/[A-Za-z0-9/_{}-]*$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class Platform(StrEnum):
    MOBILE = "mobile"
    WEB = "web"
    ADMIN = "admin"
    BACKEND = "backend"


class MobileProfile(StrEnum):
    AUTO = "auto"
    FLUTTER = "flutter"
    REACT_NATIVE = "react_native"
    NATIVE = "native"
    NONE = "none"


class WebStrategy(StrEnum):
    NEXTJS = "nextjs"
    FLUTTER_WEB = "flutter_web"
    RN_WEB = "rn_web"
    PWA = "pwa"
    NONE = "none"


class AdminStrategy(StrEnum):
    NEXTJS = "nextjs"
    NONE = "none"


class BackendStrategy(StrEnum):
    GO = "go"
    PYTHON = "python"
    NODE = "node"


class DatabaseStrategy(StrEnum):
    POSTGRES = "postgres"
    OTHER = "other"


class RepoStrategy(StrEnum):
    CUSTOMER_PROJECT_MONOREPO = "customer_project_monorepo"
    APPROVED_MULTI_REPO = "approved_multi_repo"


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class FieldType(StrEnum):
    STRING = "string"
    TEXT = "text"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    DATETIME = "datetime"
    UUID = "uuid"
    JSON = "json"


class RelationKind(StrEnum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"


def _ident(value: str, name: str) -> str:
    if not isinstance(value, str) or not _IDENT.fullmatch(value):
        raise InvalidIRError(f"{name} must be a lower snake_case identifier: {value!r}")
    if len(value) > 64:
        raise InvalidIRError(f"{name} must be at most 64 characters")
    return value


def _entity_name(value: str, name: str = "entity name") -> str:
    if not isinstance(value, str) or not _ENTITY_NAME.fullmatch(value) or len(value) > 64:
        raise InvalidIRError(f"{name} must be a 1-64 char alphanumeric identifier: {value!r}")
    return value


def _text(value: str, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise InvalidIRError(f"{name} must be a non-empty trimmed string")
    if len(value) > maximum or _CONTROL.search(value):
        raise InvalidIRError(f"{name} must be at most {maximum} characters without control chars")
    return value


def _str_tuple(value: Any, name: str, maximum: int = 128) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise InvalidIRError(f"{name} must be a tuple")
    for item in value:
        _text(item, f"{name} item", maximum)
    return value


def _enum(value: Any, enum_cls: type[StrEnum], name: str) -> Any:
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except ValueError as error:
        allowed = ", ".join(member.value for member in enum_cls)
        raise InvalidIRError(f"{name} must be one of: {allowed}") from error


@dataclass(frozen=True, slots=True)
class ProjectStrategy:
    mobile_profile: MobileProfile
    web_strategy: WebStrategy
    admin_strategy: AdminStrategy
    backend_strategy: BackendStrategy
    database_strategy: DatabaseStrategy
    repo_strategy: RepoStrategy

    def __post_init__(self) -> None:
        object.__setattr__(self, "mobile_profile", _enum(self.mobile_profile, MobileProfile, "mobile_profile"))
        object.__setattr__(self, "web_strategy", _enum(self.web_strategy, WebStrategy, "web_strategy"))
        object.__setattr__(self, "admin_strategy", _enum(self.admin_strategy, AdminStrategy, "admin_strategy"))
        object.__setattr__(self, "backend_strategy", _enum(self.backend_strategy, BackendStrategy, "backend_strategy"))
        object.__setattr__(self, "database_strategy", _enum(self.database_strategy, DatabaseStrategy, "database_strategy"))
        object.__setattr__(self, "repo_strategy", _enum(self.repo_strategy, RepoStrategy, "repo_strategy"))

    def to_dict(self) -> dict[str, str]:
        return {
            "mobile_profile": self.mobile_profile.value,
            "web_strategy": self.web_strategy.value,
            "admin_strategy": self.admin_strategy.value,
            "backend_strategy": self.backend_strategy.value,
            "database_strategy": self.database_strategy.value,
            "repo_strategy": self.repo_strategy.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectStrategy":
        return cls(
            data["mobile_profile"], data["web_strategy"], data["admin_strategy"],
            data["backend_strategy"], data["database_strategy"], data["repo_strategy"],
        )


@dataclass(frozen=True, slots=True)
class Role:
    id: str
    permissions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ident(self.id, "role id")
        _str_tuple(self.permissions, "role permissions")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "permissions": list(self.permissions)}


@dataclass(frozen=True, slots=True)
class Field:
    name: str
    type: FieldType
    required: bool = True
    validation: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ident(self.name, "field name")
        object.__setattr__(self, "type", _enum(self.type, FieldType, "field type"))
        if not isinstance(self.required, bool):
            raise InvalidIRError("field required must be a boolean")
        _str_tuple(self.validation, "field validation")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type.value, "required": self.required, "validation": list(self.validation)}


@dataclass(frozen=True, slots=True)
class Relation:
    name: str
    target_entity: str
    kind: RelationKind

    def __post_init__(self) -> None:
        _ident(self.name, "relation name")
        _entity_name(self.target_entity, "relation target_entity")
        object.__setattr__(self, "kind", _enum(self.kind, RelationKind, "relation kind"))

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "target_entity": self.target_entity, "kind": self.kind.value}


@dataclass(frozen=True, slots=True)
class Entity:
    name: str
    fields: tuple[Field, ...]
    relations: tuple[Relation, ...] = ()

    def __post_init__(self) -> None:
        _entity_name(self.name)
        if not isinstance(self.fields, tuple) or not self.fields:
            raise InvalidIRError(f"entity {self.name} must declare at least one field")
        if any(not isinstance(item, Field) for item in self.fields):
            raise InvalidIRError("entity fields must be Field records")
        _require_unique((f.name for f in self.fields), f"entity {self.name} field names")
        if any(not isinstance(item, Relation) for item in self.relations):
            raise InvalidIRError("entity relations must be Relation records")
        _require_unique((r.name for r in self.relations), f"entity {self.name} relation names")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "fields": [f.to_dict() for f in self.fields],
            "relations": [r.to_dict() for r in self.relations],
        }


@dataclass(frozen=True, slots=True)
class ApiEndpoint:
    method: HttpMethod
    path: str
    auth: bool = True
    request_schema: str | None = None
    response_schema: str | None = None
    error_schema: str | None = None
    required_roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", _enum(self.method, HttpMethod, "api method"))
        if not isinstance(self.path, str) or not _API_PATH.fullmatch(self.path) or len(self.path) > 256:
            raise InvalidIRError(f"api path must start with / and be a bounded URL path: {self.path!r}")
        if not isinstance(self.auth, bool):
            raise InvalidIRError("api auth must be a boolean")
        for schema_name in ("request_schema", "response_schema", "error_schema"):
            value = getattr(self, schema_name)
            if value is not None:
                _entity_name(value, f"api {schema_name}")
        object.__setattr__(self, "required_roles", _str_tuple(self.required_roles, "api required_roles"))
        if self.required_roles and not self.auth:
            raise InvalidIRError("an api endpoint with required_roles must require auth")

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method.value, "path": self.path, "auth": self.auth,
            "request_schema": self.request_schema, "response_schema": self.response_schema,
            "error_schema": self.error_schema, "required_roles": list(self.required_roles),
        }


@dataclass(frozen=True, slots=True)
class Screen:
    id: str
    role: str
    components: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()
    navigation: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ident(self.id, "screen id")
        _ident(self.role, "screen role")
        _str_tuple(self.components, "screen components")
        _str_tuple(self.actions, "screen actions")
        _str_tuple(self.navigation, "screen navigation")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "role": self.role, "components": list(self.components),
            "actions": list(self.actions), "navigation": list(self.navigation),
        }


@dataclass(frozen=True, slots=True)
class AcceptanceCriterion:
    requirement_id: str
    expected_result: str

    def __post_init__(self) -> None:
        _ident(self.requirement_id, "acceptance requirement_id")
        _text(self.expected_result, "acceptance expected_result", 1000)

    def to_dict(self) -> dict[str, Any]:
        return {"requirement_id": self.requirement_id, "expected_result": self.expected_result}


def _require_unique(values: Any, name: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise InvalidIRError(f"{name} must be unique; duplicate: {value!r}")
        seen.add(value)


@dataclass(frozen=True, slots=True)
class ApplicationIR:
    name: str
    description: str
    platforms: tuple[Platform, ...]
    project_strategy: ProjectStrategy
    roles: tuple[Role, ...] = ()
    entities: tuple[Entity, ...] = ()
    apis: tuple[ApiEndpoint, ...] = ()
    screens: tuple[Screen, ...] = ()
    acceptance_criteria: tuple[AcceptanceCriterion, ...] = ()
    schema_version: int = IR_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != IR_SCHEMA_VERSION:
            raise UnsupportedIRVersionError(
                f"unsupported IR schema version {self.schema_version}; expected {IR_SCHEMA_VERSION}"
            )
        _text(self.name, "application name", 128)
        _text(self.description, "application description", 4000)
        if not isinstance(self.platforms, tuple) or not self.platforms:
            raise InvalidIRError("platforms must be a non-empty tuple")
        object.__setattr__(
            self, "platforms", tuple(_enum(p, Platform, "platform") for p in self.platforms)
        )
        _require_unique((p.value for p in self.platforms), "platforms")
        if not isinstance(self.project_strategy, ProjectStrategy):
            raise InvalidIRError("project_strategy must be a ProjectStrategy")
        for tuple_name, records, record_type in (
            ("roles", self.roles, Role),
            ("entities", self.entities, Entity),
            ("apis", self.apis, ApiEndpoint),
            ("screens", self.screens, Screen),
            ("acceptance_criteria", self.acceptance_criteria, AcceptanceCriterion),
        ):
            if not isinstance(records, tuple) or any(not isinstance(r, record_type) for r in records):
                raise InvalidIRError(f"{tuple_name} must be a tuple of {record_type.__name__}")

        role_ids = {role.id for role in self.roles}
        _require_unique((role.id for role in self.roles), "role ids")
        entity_names = {entity.name for entity in self.entities}
        _require_unique((entity.name for entity in self.entities), "entity names")
        _require_unique((screen.id for screen in self.screens), "screen ids")
        _require_unique((f"{api.method.value} {api.path}" for api in self.apis), "api method+path")

        for entity in self.entities:
            for relation in entity.relations:
                if relation.target_entity not in entity_names:
                    raise InvalidIRError(
                        f"relation {entity.name}.{relation.name} targets unknown entity "
                        f"{relation.target_entity!r}"
                    )
        for screen in self.screens:
            if screen.role not in role_ids:
                raise InvalidIRError(f"screen {screen.id!r} references unknown role {screen.role!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "description": self.description,
            "platforms": [p.value for p in self.platforms],
            "project_strategy": self.project_strategy.to_dict(),
            "roles": [r.to_dict() for r in self.roles],
            "entities": [e.to_dict() for e in self.entities],
            "apis": [a.to_dict() for a in self.apis],
            "screens": [s.to_dict() for s in self.screens],
            "acceptance_criteria": [c.to_dict() for c in self.acceptance_criteria],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApplicationIR":
        if not isinstance(data, dict):
            raise InvalidIRError("IR document must be a mapping")
        version = data.get("schema_version")
        if version != IR_SCHEMA_VERSION:
            raise UnsupportedIRVersionError(
                f"unsupported IR schema version {version!r}; expected {IR_SCHEMA_VERSION}"
            )
        try:
            return cls(
                name=data["name"],
                description=data["description"],
                platforms=tuple(data.get("platforms", ())),
                project_strategy=ProjectStrategy.from_dict(data["project_strategy"]),
                roles=tuple(Role(r["id"], tuple(r.get("permissions", ()))) for r in data.get("roles", ())),
                entities=tuple(
                    Entity(
                        name=e["name"],
                        fields=tuple(
                            Field(f["name"], f["type"], f.get("required", True), tuple(f.get("validation", ())))
                            for f in e.get("fields", ())
                        ),
                        relations=tuple(
                            Relation(rel["name"], rel["target_entity"], rel["kind"])
                            for rel in e.get("relations", ())
                        ),
                    )
                    for e in data.get("entities", ())
                ),
                apis=tuple(
                    ApiEndpoint(
                        a["method"], a["path"], a.get("auth", True),
                        a.get("request_schema"), a.get("response_schema"), a.get("error_schema"),
                        tuple(a.get("required_roles", ())),
                    )
                    for a in data.get("apis", ())
                ),
                screens=tuple(
                    Screen(
                        s["id"], s["role"], tuple(s.get("components", ())),
                        tuple(s.get("actions", ())), tuple(s.get("navigation", ())),
                    )
                    for s in data.get("screens", ())
                ),
                acceptance_criteria=tuple(
                    AcceptanceCriterion(c["requirement_id"], c["expected_result"])
                    for c in data.get("acceptance_criteria", ())
                ),
                schema_version=version,
            )
        except (KeyError, TypeError) as error:
            raise InvalidIRError(f"IR document is structurally invalid: {error}") from error

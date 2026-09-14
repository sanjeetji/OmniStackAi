"""Solution Pack Ecosystem Unified State Binding and Lifecycle Flows (R-447).

Defines canonical entity state bindings, role-gated state flow transitions,
cross-app API endpoint consumption maps, and shared environment bindings across surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class SharedEntityBinding:
    """Ownership and access topology for an entity shared across ecosystem surfaces."""

    entity_name: str
    authoritative_surface: str
    reading_surfaces: tuple[str, ...]
    writing_surfaces: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_name": self.entity_name,
            "authoritative_surface": self.authoritative_surface,
            "reading_surfaces": list(self.reading_surfaces),
            "writing_surfaces": list(self.writing_surfaces),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SharedEntityBinding:
        return cls(
            entity_name=str(data["entity_name"]),
            authoritative_surface=str(data.get("authoritative_surface", "")),
            reading_surfaces=tuple(data.get("reading_surfaces", ())),
            writing_surfaces=tuple(data.get("writing_surfaces", ())),
        )


@dataclass(frozen=True)
class StateTransition:
    """One allowable state transition within an entity's lifecycle."""

    from_state: str
    to_state: str
    authorized_roles: tuple[str, ...]
    trigger_surface: str
    action_name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_state": self.from_state,
            "to_state": self.to_state,
            "authorized_roles": list(self.authorized_roles),
            "trigger_surface": self.trigger_surface,
            "action_name": self.action_name,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> StateTransition:
        return cls(
            from_state=str(data["from_state"]),
            to_state=str(data["to_state"]),
            authorized_roles=tuple(data.get("authorized_roles", ())),
            trigger_surface=str(data.get("trigger_surface", "")),
            action_name=str(data.get("action_name", "")),
        )


@dataclass(frozen=True)
class EntityStateFlow:
    """Lifecycle state machine for a specific domain entity."""

    entity_name: str
    state_field: str
    initial_state: str
    terminal_states: tuple[str, ...]
    transitions: tuple[StateTransition, ...]

    def can_transition(self, from_state: str, to_state: str, role_id: str) -> bool:
        """Check whether a transition between states is authorized for the given role."""
        for t in self.transitions:
            if t.from_state == from_state and t.to_state == to_state:
                if role_id in t.authorized_roles or role_id == "admin":
                    return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_name": self.entity_name,
            "state_field": self.state_field,
            "initial_state": self.initial_state,
            "terminal_states": list(self.terminal_states),
            "transitions": [t.to_dict() for t in self.transitions],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EntityStateFlow:
        transitions = tuple(StateTransition.from_dict(t) for t in data.get("transitions", ()))
        return cls(
            entity_name=str(data["entity_name"]),
            state_field=str(data.get("state_field", "status")),
            initial_state=str(data.get("initial_state", "draft")),
            terminal_states=tuple(data.get("terminal_states", ())),
            transitions=transitions,
        )


@dataclass(frozen=True)
class CrossAppEndpointBinding:
    """Mapping of an API endpoint to its consuming surfaces and roles."""

    endpoint_path: str
    http_method: str
    target_entity: str
    consuming_surfaces: tuple[str, ...]
    required_roles: tuple[str, ...] = ()
    is_mutation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint_path": self.endpoint_path,
            "http_method": self.http_method,
            "target_entity": self.target_entity,
            "consuming_surfaces": list(self.consuming_surfaces),
            "required_roles": list(self.required_roles),
            "is_mutation": self.is_mutation,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CrossAppEndpointBinding:
        return cls(
            endpoint_path=str(data["endpoint_path"]),
            http_method=str(data["http_method"]),
            target_entity=str(data.get("target_entity", "")),
            consuming_surfaces=tuple(data.get("consuming_surfaces", ())),
            required_roles=tuple(data.get("required_roles", ())),
            is_mutation=bool(data.get("is_mutation", False)),
        )


@dataclass(frozen=True)
class SurfaceEnvBinding:
    """Environment configuration binding for a specific surface."""

    surface_slug: str
    env_vars: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_slug": self.surface_slug,
            "env_vars": [list(item) for item in self.env_vars],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SurfaceEnvBinding:
        raw_vars = data.get("env_vars", ())
        env_vars = tuple((str(k), str(v)) for k, v in raw_vars)
        return cls(
            surface_slug=str(data["surface_slug"]),
            env_vars=env_vars,
        )


@dataclass(frozen=True)
class EcosystemStateBinding:
    """Unified cross-surface state binding contract for an ecosystem."""

    ecosystem_id: str
    database_strategy: str = "postgres"
    shared_entities: tuple[SharedEntityBinding, ...] = ()
    state_flows: tuple[EntityStateFlow, ...] = ()
    cross_app_endpoints: tuple[CrossAppEndpointBinding, ...] = ()
    environment_bindings: tuple[SurfaceEnvBinding, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "database_strategy": self.database_strategy,
            "shared_entities": [e.to_dict() for e in self.shared_entities],
            "state_flows": [f.to_dict() for f in self.state_flows],
            "cross_app_endpoints": [ep.to_dict() for ep in self.cross_app_endpoints],
            "environment_bindings": [env.to_dict() for env in self.environment_bindings],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemStateBinding:
        shared = tuple(SharedEntityBinding.from_dict(e) for e in data.get("shared_entities", ()))
        flows = tuple(EntityStateFlow.from_dict(f) for f in data.get("state_flows", ()))
        eps = tuple(CrossAppEndpointBinding.from_dict(ep) for ep in data.get("cross_app_endpoints", ()))
        envs = tuple(SurfaceEnvBinding.from_dict(env) for env in data.get("environment_bindings", ()))
        return cls(
            ecosystem_id=str(data["ecosystem_id"]),
            database_strategy=str(data.get("database_strategy", "postgres")),
            shared_entities=shared,
            state_flows=flows,
            cross_app_endpoints=eps,
            environment_bindings=envs,
        )


def synthesize_ecosystem_state(ecosystem_id: str, surfaces: Sequence[Any]) -> EcosystemStateBinding:
    """Deterministically derive an EcosystemStateBinding from an ecosystem's surfaces."""
    # Map entity -> reading surfaces & writing surfaces
    entity_readers: dict[str, set[str]] = {}
    entity_writers: dict[str, set[str]] = {}
    entity_authors: dict[str, str] = {}
    endpoints: dict[tuple[str, str], dict[str, Any]] = {}
    detected_state_fields: dict[str, list[str]] = {}

    for s in surfaces:
        slug = getattr(s, "slug", s.get("slug", "") if isinstance(s, dict) else "")
        surface_kind = getattr(s, "surface_kind", s.get("surface_kind", "") if isinstance(s, dict) else "")
        is_admin = "admin" in surface_kind

        # Extract entities from IR dict
        ir_dict = getattr(s, "ir_dict", s.get("ir_dict") if isinstance(s, dict) else None)
        raw_entities = []
        if ir_dict and isinstance(ir_dict, dict) and "entities" in ir_dict:
            raw_entities = ir_dict["entities"]
        elif hasattr(s, "ir") and getattr(s.ir, "entities", None):
            raw_entities = [e.to_dict() if hasattr(e, "to_dict") else vars(e) for e in s.ir.entities]

        for ent in raw_entities:
            name = ent.get("name") if isinstance(ent, dict) else getattr(ent, "name", "")
            if not name:
                continue
            entity_readers.setdefault(name, set()).add(slug)
            if is_admin or not ("read_only" in surface_kind):
                entity_writers.setdefault(name, set()).add(slug)
            if is_admin and name not in entity_authors:
                entity_authors[name] = slug
            elif name not in entity_authors:
                entity_authors[name] = slug

            # Check for state fields
            fields = ent.get("fields", []) if isinstance(ent, dict) else getattr(ent, "fields", [])
            for f in fields:
                fname = f.get("name") if isinstance(f, dict) else getattr(f, "name", "")
                if fname in ("published", "status", "stage", "state"):
                    detected_state_fields.setdefault(name, []).append(fname)

        # Extract APIs
        raw_apis = []
        if ir_dict and isinstance(ir_dict, dict) and "apis" in ir_dict:
            raw_apis = ir_dict["apis"]
        elif hasattr(s, "ir") and getattr(s.ir, "apis", None):
            raw_apis = [a.to_dict() if hasattr(a, "to_dict") else vars(a) for a in s.ir.apis]

        for api in raw_apis:
            path = api.get("path") if isinstance(api, dict) else getattr(api, "path", "")
            method = api.get("method") if isinstance(api, dict) else getattr(api, "method", "")
            if hasattr(method, "value"):
                method = method.value
            req_roles = api.get("required_roles", ()) if isinstance(api, dict) else getattr(api, "required_roles", ())
            schema = api.get("response_schema") or api.get("request_schema") or ""

            key = (str(path), str(method))
            if key not in endpoints:
                endpoints[key] = {
                    "path": str(path),
                    "method": str(method),
                    "entity": str(schema),
                    "surfaces": set([slug]),
                    "roles": set(req_roles),
                    "is_mutation": str(method).upper() in ("POST", "PUT", "DELETE", "PATCH"),
                }
            else:
                endpoints[key]["surfaces"].add(slug)
                endpoints[key]["roles"].update(req_roles)

    # Build shared entity bindings
    shared_entities: list[SharedEntityBinding] = []
    for ent_name in sorted(entity_readers.keys()):
        readers = tuple(sorted(entity_readers[ent_name]))
        writers = tuple(sorted(entity_writers.get(ent_name, ())))
        author = entity_authors.get(ent_name, readers[0] if readers else "")
        shared_entities.append(
            SharedEntityBinding(
                entity_name=ent_name,
                authoritative_surface=author,
                reading_surfaces=readers,
                writing_surfaces=writers,
            )
        )

    # Build state flows
    state_flows: list[EntityStateFlow] = []
    for ent_name, fnames in sorted(detected_state_fields.items()):
        state_field = fnames[0]
        if state_field == "published":
            flow = EntityStateFlow(
                entity_name=ent_name,
                state_field="published",
                initial_state="draft",
                terminal_states=("published", "archived"),
                transitions=(
                    StateTransition(
                        from_state="draft",
                        to_state="published",
                        authorized_roles=("admin", "author", "editor"),
                        trigger_surface=entity_authors.get(ent_name, ""),
                        action_name="publish",
                    ),
                    StateTransition(
                        from_state="published",
                        to_state="archived",
                        authorized_roles=("admin",),
                        trigger_surface=entity_authors.get(ent_name, ""),
                        action_name="archive",
                    ),
                ),
            )
            state_flows.append(flow)
        elif state_field in ("status", "stage", "state"):
            flow = EntityStateFlow(
                entity_name=ent_name,
                state_field=state_field,
                initial_state="pending",
                terminal_states=("completed", "cancelled"),
                transitions=(
                    StateTransition(
                        from_state="pending",
                        to_state="active",
                        authorized_roles=("admin", "operator"),
                        trigger_surface=entity_authors.get(ent_name, ""),
                        action_name="activate",
                    ),
                    StateTransition(
                        from_state="active",
                        to_state="completed",
                        authorized_roles=("admin", "operator"),
                        trigger_surface=entity_authors.get(ent_name, ""),
                        action_name="complete",
                    ),
                ),
            )
            state_flows.append(flow)

    # Build cross-app endpoint bindings
    cross_app_endpoints: list[CrossAppEndpointBinding] = []
    for (path, method), ep_info in sorted(endpoints.items()):
        cross_app_endpoints.append(
            CrossAppEndpointBinding(
                endpoint_path=path,
                http_method=method,
                target_entity=ep_info["entity"],
                consuming_surfaces=tuple(sorted(ep_info["surfaces"])),
                required_roles=tuple(sorted(ep_info["roles"])),
                is_mutation=ep_info["is_mutation"],
            )
        )

    # Build environment bindings
    env_bindings: list[SurfaceEnvBinding] = []
    for s in surfaces:
        slug = getattr(s, "slug", s.get("slug", "") if isinstance(s, dict) else "")
        env_bindings.append(
            SurfaceEnvBinding(
                surface_slug=slug,
                env_vars=(
                    ("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000"),
                    ("JWT_SECRET", "local-dev-secret"),
                    ("DATABASE_URL", "postgresql://app:app@127.0.0.1:5432/app"),
                ),
            )
        )

    return EcosystemStateBinding(
        ecosystem_id=ecosystem_id,
        database_strategy="postgres",
        shared_entities=tuple(shared_entities),
        state_flows=tuple(state_flows),
        cross_app_endpoints=tuple(cross_app_endpoints),
        environment_bindings=tuple(env_bindings),
    )

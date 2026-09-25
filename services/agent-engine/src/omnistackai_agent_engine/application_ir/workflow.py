"""An entity's lifecycle: the states it moves through, and who may move it (R-566).

An order goes placed -> accepted -> picked_up -> delivered. A courier may pick one up but may not
accept it, and nothing may go back to placed once it has been delivered. None of that could be
written down: the IR had entities, fields, relations, CRUD, screens and roles, so a status column
was just a string anybody could set to anything, and `POST /orders/{orderId}/accept` wired to
nothing — the Python backend emitted a 501 stub for it, which is visible but is not a product.

This is the first capability kind with code generation behind it. R-564 shipped the registry empty
on purpose, because a kind that can be declared but not built is the failure R-559 removed for
stacks, wearing different clothes.

Two decisions are worth stating, because both could reasonably have gone the other way.

**The states live in the database, not only in the application.** The generated schema constrains
the column, so a row cannot hold a state the workflow never declared — not even by a hand-written
`UPDATE`. A lifecycle enforced only in application code is a lifecycle that survives exactly as
long as every writer remembers it.

**A transition is refused by the backend, not merely hidden in the interface.** Not showing a
courier the "accept" button is presentation; refusing the request is the rule. The screens hide
what a role cannot do because that is kinder, and the API refuses it because that is what makes it
true.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .errors import InvalidIRError

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,48}$")

#: A lifecycle with one state cannot move, and one with dozens is a diagram nobody reads. The
#: bounds exist to keep a generated product comprehensible rather than to be strict for its own sake.
MAX_STATES = 16
MAX_TRANSITIONS = 32


@dataclass(frozen=True, slots=True)
class Transition:
    """One move between states, and who may make it."""

    name: str
    to: str
    #: Empty means "from any state". Written out rather than implied, because "any" is a decision.
    sources: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _IDENTIFIER.match(self.name or ""):
            raise InvalidIRError(f"transition name must be lower_snake_case: {self.name!r}")
        if not _IDENTIFIER.match(self.to or ""):
            raise InvalidIRError(f"transition target state must be lower_snake_case: {self.to!r}")
        object.__setattr__(self, "sources", tuple(self.sources or ()))
        object.__setattr__(self, "roles", tuple(self.roles or ()))
        for source in self.sources:
            if not _IDENTIFIER.match(source):
                raise InvalidIRError(f"transition source state must be lower_snake_case: {source!r}")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "to": self.to, "from": list(self.sources), "roles": list(self.roles)}

    @classmethod
    def from_dict(cls, data: Any) -> "Transition":
        if not isinstance(data, dict):
            raise InvalidIRError("a transition must be a mapping")
        return cls(
            name=str(data.get("name", "")),
            to=str(data.get("to", "")),
            sources=tuple(data.get("from", ()) or ()),
            roles=tuple(data.get("roles", ()) or ()),
        )


@dataclass(frozen=True, slots=True)
class Workflow:
    """The lifecycle of one entity, read from a `workflow` capability's config."""

    entity: str
    field: str
    states: tuple[str, ...]
    initial: str
    transitions: tuple[Transition, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.entity:
            raise InvalidIRError("a workflow must name an entity")
        if not _IDENTIFIER.match(self.field or ""):
            raise InvalidIRError(f"workflow field must be lower_snake_case: {self.field!r}")
        if not self.states:
            raise InvalidIRError("a workflow must declare at least one state")
        if len(self.states) > MAX_STATES:
            raise InvalidIRError(f"a workflow cannot declare more than {MAX_STATES} states")
        if len(set(self.states)) != len(self.states):
            raise InvalidIRError("workflow states must be unique")
        for state in self.states:
            if not _IDENTIFIER.match(state):
                raise InvalidIRError(f"workflow state must be lower_snake_case: {state!r}")
        if self.initial not in self.states:
            raise InvalidIRError(
                f"initial state {self.initial!r} is not one of the declared states: {', '.join(self.states)}"
            )
        if len(self.transitions) > MAX_TRANSITIONS:
            raise InvalidIRError(f"a workflow cannot declare more than {MAX_TRANSITIONS} transitions")

        names = [t.name for t in self.transitions]
        if len(set(names)) != len(names):
            raise InvalidIRError("transition names must be unique within a workflow")
        for transition in self.transitions:
            if transition.to not in self.states:
                raise InvalidIRError(
                    f"transition {transition.name!r} moves to undeclared state {transition.to!r}"
                )
            for source in transition.sources:
                if source not in self.states:
                    raise InvalidIRError(
                        f"transition {transition.name!r} comes from undeclared state {source!r}"
                    )

    def transitions_from(self, state: str) -> tuple[Transition, ...]:
        """Everything legal from `state`. A transition with no sources is legal from anywhere."""
        return tuple(t for t in self.transitions if not t.sources or state in t.sources)

    def to_config(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "field": self.field,
            "states": list(self.states),
            "initial": self.initial,
            "transitions": [t.to_dict() for t in self.transitions],
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Workflow":
        if not isinstance(config, dict):
            raise InvalidIRError("a workflow config must be a mapping")
        states = tuple(str(s) for s in config.get("states", ()) or ())
        return cls(
            entity=str(config.get("entity", "")),
            field=str(config.get("field", "status")),
            states=states,
            initial=str(config.get("initial", states[0] if states else "")),
            transitions=tuple(Transition.from_dict(t) for t in config.get("transitions", ()) or ()),
        )


def validate_workflow_config(name: str, config: dict[str, Any]) -> None:
    """The capability kind's validator: the shape is checked here, the references by the IR.

    What a workflow says about itself can be judged alone — a transition cannot move to a state the
    workflow never declared. Whether the entity, the field and the roles exist is a question about
    the rest of the IR, and is answered in `application_ir.ir` where the rest of the IR is in scope.
    """
    try:
        Workflow.from_config(config)
    except InvalidIRError as error:
        raise InvalidIRError(f"workflow {name!r}: {error}") from error


def workflows_of(ir: Any) -> tuple[Workflow, ...]:
    """Every workflow an IR declares, in declaration order."""
    return tuple(
        Workflow.from_config(capability.config)
        for capability in getattr(ir, "capabilities", ())
        if capability.kind == "workflow"
    )


def workflow_for_entity(ir: Any, entity_name: str) -> "Workflow | None":
    for workflow in workflows_of(ir):
        if workflow.entity == entity_name:
            return workflow
    return None

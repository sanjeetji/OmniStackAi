"""The endpoints a workflow contributes, derived once and used everywhere (R-566).

A lifecycle implies endpoints: `POST /orders/{orderId}/accept` moves an order from one state to
another. They are *derived* rather than declared, because the workflow already says everything
needed to write them down, and asking a model to restate them is asking it to disagree with itself.

Derived in one place because three things need the same answer — the backend that implements them,
the OpenAPI contract that documents them, and the screens that offer them. Three separate
derivations would be three chances for the button, the contract and the handler to describe
different endpoints, which is the failure mode this repository keeps meeting in other forms.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..application_ir import ApplicationIR
from ..application_ir.workflow import Transition, Workflow, workflows_of
from .route_wiring import table_name


@dataclass(frozen=True, slots=True)
class TransitionRoute:
    """One transition, as an endpoint."""

    workflow: Workflow
    transition: Transition
    path: str
    id_param: str
    function: str

    @property
    def table(self) -> str:
        return table_name(self.workflow.entity)

    @property
    def method(self) -> str:
        return "POST"

    @property
    def roles(self) -> tuple[str, ...]:
        return self.transition.roles


def _camel(name: str) -> str:
    return name[0].lower() + name[1:] if name else name


def transition_routes(ir: ApplicationIR) -> tuple[TransitionRoute, ...]:
    """Every transition endpoint this IR implies, in a stable order.

    The path mirrors the CRUD shapes around it — `/posts/{postId}/publish` sits beside
    `/posts/{postId}` — so a generated API reads as one surface rather than as two conventions
    stitched together.
    """
    routes: list[TransitionRoute] = []
    for workflow in workflows_of(ir):
        table = table_name(workflow.entity)
        id_param = f"{_camel(workflow.entity)}Id"
        for transition in workflow.transitions:
            routes.append(
                TransitionRoute(
                    workflow=workflow,
                    transition=transition,
                    path=f"/{table}s/{{{id_param}}}/{transition.name}",
                    id_param=id_param,
                    function=f"{transition.name}_{table}",
                )
            )
    return tuple(routes)


def setter_name(workflow: Workflow) -> str:
    """The repository function a transition calls.

    Its own function rather than the generated `update_<table>`: that one writes every column from
    a full payload, so a transition passing only the state would blank the rest of the row.
    """
    return f"set_{table_name(workflow.entity)}_{workflow.field}"

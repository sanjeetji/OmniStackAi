"""What in a generated app is not connected to real data yet, by name (PC-004).

The founder's rule for Vibe Mode is that the API and database behind every feature are real. The
generators already wire every endpoint that matches a CRUD shape and every screen that matches an
entity. What they cannot wire used to be dressed up: Node answered unknown endpoints with 200 and a
placeholder body, "cart" and "review" screens showed invented products and reviews, and fallback
pages carried buttons that did nothing.

Those are honest now (501, and a "not connected yet" page). This report is the other half: the
build result and the README list every such endpoint and screen, so the user is told what is real
and what is not instead of discovering it by clicking.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR
from .auth_guard import needs_auth
from .auth_templates import is_account_route
from .route_wiring import Op, fk_relations, wire_endpoint


def wiring_gaps(ir: ApplicationIR) -> tuple[dict[str, str], ...]:
    """Endpoints and screens with no real data behind them, each with a reason a person can act on."""
    from .nextjs import _get_ops_by_entity, _match_entity, _screen_intent

    gaps: list[dict[str, str]] = []
    entities = frozenset(e.name for e in ir.entities)
    fks = fk_relations(ir)
    auth = needs_auth(ir)
    for api in ir.apis:
        if auth and is_account_route(api.path):
            continue  # served by the generated account flow (R-591)
        if wire_endpoint(api, entities, fks) is None:
            gaps.append({
                "kind": "endpoint",
                "name": f"{api.method.value} {api.path}",
                "reason": "no entity and CRUD shape match it, so it answers 501 until it is built",
            })

    ops_by_entity = _get_ops_by_entity(ir)
    needed = {"collection": {Op.LIST}, "form": {Op.CREATE, Op.UPDATE}, "detail": {Op.GET, Op.LIST}}
    for screen in ir.screens:
        entity = _match_entity(screen, ir)
        if entity is None:
            gaps.append({
                "kind": "screen",
                "name": screen.id,
                "reason": "no entity in the plan matches it, so it shows 'Not connected to data yet'",
            })
            continue
        intent = _screen_intent(screen)
        if not (needed.get(intent, set()) & ops_by_entity.get(entity.name, set())):
            gaps.append({
                "kind": "screen",
                "name": screen.id,
                "reason": f"{entity.name} has no endpoint this {intent or 'screen'} can use, "
                          "so it shows 'Not connected to data yet'",
            })
    return tuple(gaps)


def readme_section(ir: ApplicationIR) -> str:
    gaps = wiring_gaps(ir)
    if not gaps:
        return "## Connected\n\nEvery endpoint and screen in this app is backed by the real API and database.\n"
    lines = [
        "## Not connected to data yet",
        "",
        "These parts of the plan have no real data behind them. They say so in the app rather than",
        "pretending; ask for them in the chat and they are built with a real API and database.",
        "",
    ]
    lines += [f"- **{g['kind']}** `{g['name']}` — {g['reason']}" for g in gaps]
    return "\n".join(lines) + "\n"

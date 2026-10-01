"""R-570: which generated operations an ownership rule narrows - one answer for every backend.

Python, Go and Node each enforce an entity's `ownership` rule in their own idiom; what they enforce
must not differ, so the decisions live here and the generators only render them.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR
from ..application_ir.ownership import OwnershipRule, ownership_rules
from .route_wiring import Op


def rules_by_entity(ir: ApplicationIR) -> dict[str, OwnershipRule]:
    return {rule.entity: rule for rule in ownership_rules(ir)}


def owner_scoped_op(rule: OwnershipRule | None, wiring) -> bool:
    """Whether this operation is narrowed to the caller's own records.

    Reading is narrowed when the rule reads "own"; changing and deleting when it writes "own" (or
    reads "own" - what you cannot see you cannot change). Creating never is: it records the creator.
    """
    if rule is None or wiring is None:
        return False
    if wiring.op in (Op.LIST, Op.LIST_BY, Op.GET):
        return rule.reads_own
    if wiring.op in (Op.UPDATE, Op.DELETE):
        return rule.writes_own
    return False


def owned_transition(rules: dict[str, OwnershipRule], route) -> OwnershipRule | None:
    """A lifecycle transition open to any role on an owner-scoped entity is the owner's to make.

    A transition that names roles was granted to those roles on purpose (a courier accepts an order a
    customer created), so it stays role-only.
    """
    rule = rules.get(route.workflow.entity)
    return rule if rule is not None and rule.writes_own and not route.roles else None

"""Whose records are whose: ownership and row-level rules (R-570).

Roles answered "may a courier call this endpoint at all"; nothing answered "which orders may this
courier see". Seen live in PC-008: a published notes app saved every note with `created_by` empty,
and listed everybody's notes to everybody - private notes were not private. The pieces existed (a
`created_by` column, `require_owner` helpers) and nothing used them.

Two things are now true of every generated app with sign-in:

**Every record a signed-in user creates says who created it.** The backend fills `created_by` from
the verified token; a client cannot set it, because it is not part of any request model.

**An entity can be owner-scoped**, with an `ownership` capability:

    {"kind": "ownership", "name": "note_ownership",
     "config": {"entity": "Note", "read": "own", "write": "own", "see_all": ["moderator"]}}

    read   "own": lists show only the user's own records and anyone else's is not found
           "all": everyone signed in (or the public, if the endpoint is public) reads every record
    write  "own": only the record's creator may change or delete it
           "all": anyone the endpoint's roles allow may
    see_all  roles that see and change every record regardless (admin always does)
    assignee (PC-111) a field holding the user a record is assigned to - a delivery's driver:
             "own" then also means "assigned to me". The assignee may read and change the record
             and make the transitions their role is granted (only on records assigned to them);
             deleting stays the creator's; only see_all roles set or change the assignment.

Refusals answer 404, not 403: telling a stranger "this exists but is not yours" is itself a leak.
The rule is enforced by the API, never only by hiding things in the interface, and an owner-scoped
read requires sign-in even where the plan marked the endpoint public - the rule wins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .errors import InvalidIRError

_ROLE = re.compile(r"^[a-z][a-z0-9_]{0,48}$")
SCOPES = ("own", "all")
#: The column every backend fills from the token. One name everywhere, so a rule never has to say it.
OWNER_COLUMN = "created_by"


@dataclass(frozen=True, slots=True)
class OwnershipRule:
    entity: str
    read: str = "all"
    write: str = "own"
    see_all: tuple[str, ...] = ()
    assignee: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.entity, str) or not self.entity.strip():
            raise InvalidIRError("an ownership rule needs an entity")
        for name, value in (("read", self.read), ("write", self.write)):
            if value not in SCOPES:
                raise InvalidIRError(f"ownership {name} must be 'own' or 'all', got {value!r}")
        roles = tuple(self.see_all or ())
        for role in roles:
            if not isinstance(role, str) or not _ROLE.match(role):
                raise InvalidIRError(f"ownership see_all role must be lower_snake_case: {role!r}")
        object.__setattr__(self, "see_all", roles)
        if self.assignee is not None and not _ROLE.match(str(self.assignee)):
            raise InvalidIRError(f"ownership assignee must name a lower_snake_case field: {self.assignee!r}")

    @property
    def reads_own(self) -> bool:
        return self.read == "own"

    @property
    def writes_own(self) -> bool:
        return self.write == "own" or self.read == "own"  # what you cannot see you cannot change

    @property
    def bypass_roles(self) -> tuple[str, ...]:
        """Roles that see and change every record: the rule's own, and admin always."""
        return tuple(dict.fromkeys((*self.see_all, "admin")))

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "OwnershipRule":
        if not isinstance(config, dict):
            raise InvalidIRError("an ownership config must be an object")
        unknown = set(config) - {"entity", "read", "write", "see_all", "assignee"}
        if unknown:
            raise InvalidIRError(f"unknown ownership keys: {', '.join(sorted(unknown))}")
        return cls(
            entity=config.get("entity", ""),
            read=config.get("read", "all"),
            write=config.get("write", "own"),
            see_all=tuple(config.get("see_all") or ()),
            assignee=config.get("assignee") or None,
        )

    def to_config(self) -> dict[str, Any]:
        config = {"entity": self.entity, "read": self.read, "write": self.write, "see_all": list(self.see_all)}
        if self.assignee:
            config["assignee"] = self.assignee
        return config


def validate_ownership_config(name: str, config: dict[str, Any]) -> None:
    """The capability kind's validator: the shape here; the entity and roles in `ir.py`."""
    try:
        OwnershipRule.from_config(config)
    except InvalidIRError as error:
        raise InvalidIRError(f"ownership {name!r}: {error}") from error


def ownership_rules(ir: Any) -> tuple[OwnershipRule, ...]:
    return tuple(
        OwnershipRule.from_config(capability.config)
        for capability in getattr(ir, "capabilities", ())
        if capability.kind == "ownership"
    )


def ownership_for_entity(ir: Any, entity_name: str) -> "OwnershipRule | None":
    for rule in ownership_rules(ir):
        if rule.entity == entity_name:
            return rule
    return None

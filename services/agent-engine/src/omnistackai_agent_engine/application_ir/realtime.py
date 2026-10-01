"""Live updates (R-569): the entities whose changes reach people as they happen.

An order's status moving while the customer watches, a delivery's position, a support ticket's
new reply. `{"kind": "realtime", "name": "live_updates", "config": {"entities": ["Order"]}}`
makes every change to an Order - created, changed, deleted, by a person or by a scheduled job -
reach the signed-in people who may see that order, without a reload.

Two decisions:

**Changes travel through the app's own Postgres.** A trigger publishes each change with
LISTEN/NOTIFY and every API replica listens, so a change made through one replica reaches people
connected to another. No Supabase, Ably or Redis.

**An event says what changed, never what it now says.** It carries the entity, the operation and
the id; the page fetches the record through the API, which applies every rule it always does. The
stream itself is filtered by the entity's ownership rule, so nobody learns even the id of a record
they may not see.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import InvalidIRError

API_PREFIX = "/realtime"
MAX_ENTITIES = 32


@dataclass(frozen=True, slots=True)
class Realtime:
    entities: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.entities:
            raise InvalidIRError("realtime needs at least one entity")
        if len(self.entities) > MAX_ENTITIES:
            raise InvalidIRError(f"realtime names at most {MAX_ENTITIES} entities")
        if len(set(self.entities)) != len(self.entities):
            raise InvalidIRError("realtime names each entity once")
        for name in self.entities:
            if not isinstance(name, str) or not name:
                raise InvalidIRError("realtime entities are entity names")

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Realtime":
        if not isinstance(config, dict):
            raise InvalidIRError("a realtime config must be a mapping")
        unknown = set(config) - {"entities"}
        if unknown:
            raise InvalidIRError(f"unknown realtime keys: {', '.join(sorted(unknown))}")
        raw = config.get("entities") or []
        if not isinstance(raw, list):
            raise InvalidIRError("realtime entities must be a list")
        return cls(entities=tuple(str(e) for e in raw))

    def to_config(self) -> dict[str, Any]:
        return {"entities": list(self.entities)}


def validate_realtime_config(name: str, config: dict[str, Any]) -> None:
    try:
        Realtime.from_config(config)
    except (InvalidIRError, ValueError, TypeError) as error:
        raise InvalidIRError(f"realtime {name!r}: {error}") from error


def realtime_of(ir: Any) -> "Realtime | None":
    """The app's live entities (one realtime capability per app), or None."""
    for capability in getattr(ir, "capabilities", ()):
        if capability.kind == "realtime":
            return Realtime.from_config(capability.config)
    return None


def live_entities(ir: Any) -> frozenset[str]:
    live = realtime_of(ir)
    return frozenset(live.entities) if live else frozenset()

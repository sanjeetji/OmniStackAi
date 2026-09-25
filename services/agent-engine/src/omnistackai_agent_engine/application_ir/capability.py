"""What a product does, beyond storing rows (R-564).

The IR describes entities, fields, relations, CRUD endpoints, screens and roles. That is a database
with pages over it, and it is the whole ceiling: `route_wiring.wire_endpoint` matches six CRUD
shapes and returns `None` for everything else, so an endpoint like `POST /orders/{id}/assign-driver`
is silently dropped. An order lifecycle, a payout ledger, a nightly settlement, a live tracking
channel and "a driver sees only their own orders" have nowhere to be written down — which is why no
model, however capable, produces them.

A capability is the place to write one down. This module is only the frame: a record, a registry of
kinds, and the rule that a kind must be registered before it can appear in an IR. The kinds
themselves — workflows, money, jobs, realtime, permissions, and the escape hatch for behaviour we
have not modelled — arrive one task at a time, each bringing the code generation that makes it real.

**Declared is not implemented.** The registry keeps the two apart on purpose, because this
repository has been bitten repeatedly by the opposite: `GenerationTarget` declared FLUTTER and
NATIVE_* with nothing behind them, and a request for either produced a website in silence until
R-559. A kind that is declared but not implemented is a promise we have not kept, and the platform
has to be able to say so rather than accept the request and quietly drop it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import InvalidIRError

#: A validator checks a capability's `config` for its kind and raises InvalidIRError if it is wrong.
Validator = Callable[[str, dict[str, Any]], None]


@dataclass(frozen=True, slots=True)
class CapabilityKind:
    """One kind of capability, and whether anything actually generates code for it."""

    name: str
    summary: str
    implemented: bool = False
    validator: Validator | None = None


class CapabilityRegistry:
    """The kinds an IR may declare, and which of them are real.

    Registered rather than hardcoded into the IR, so a later task adds a kind and its code
    generation together without editing this module — the same seam R-559 established for
    generation targets, for the same reason.
    """

    def __init__(self) -> None:
        self._kinds: dict[str, CapabilityKind] = {}

    def register(self, kind: CapabilityKind) -> None:
        if not isinstance(kind, CapabilityKind):
            raise InvalidIRError("a capability kind must be a CapabilityKind")
        if not kind.name or not kind.name.replace("_", "").isalnum():
            raise InvalidIRError(f"capability kind name must be alphanumeric: {kind.name!r}")
        if kind.name in self._kinds:
            raise InvalidIRError(f"capability kind already registered: {kind.name}")
        self._kinds[kind.name] = kind

    def get(self, name: str) -> CapabilityKind | None:
        return self._kinds.get(name)

    def known(self) -> tuple[str, ...]:
        return tuple(sorted(self._kinds))

    def implemented(self) -> tuple[str, ...]:
        """The kinds something can actually build. What intake is allowed to offer."""
        return tuple(sorted(name for name, kind in self._kinds.items() if kind.implemented))

    def __len__(self) -> int:
        return len(self._kinds)


#: The kinds this build of the platform knows about. Phase 2 fills it; R-564 ships it empty on
#: purpose, so that nothing can declare a capability before anything can build one.
CAPABILITY_KINDS = CapabilityRegistry()


@dataclass(frozen=True, slots=True)
class Capability:
    """One thing a product does that CRUD cannot express.

    `config` is deliberately untyped here: an order lifecycle and a payout ledger have nothing in
    common except that neither is a table. Each kind's validator owns its shape, which is what
    keeps this module from growing a branch per feature.
    """

    kind: str
    name: str
    config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise InvalidIRError("capability kind must be a non-empty string")
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidIRError("capability name must be a non-empty string")
        if len(self.name) > 120:
            raise InvalidIRError(f"capability name is too long: {self.name[:40]}...")
        if not isinstance(self.config, dict):
            raise InvalidIRError("capability config must be a mapping")

        registered = CAPABILITY_KINDS.get(self.kind)
        if registered is None:
            known = ", ".join(CAPABILITY_KINDS.known()) or "none yet"
            raise InvalidIRError(
                f"unknown capability kind {self.kind!r}; registered kinds: {known}. A kind must be "
                "registered with the code that generates it before an IR may declare it."
            )
        if registered.validator is not None:
            registered.validator(self.name, self.config)

    @property
    def is_implemented(self) -> bool:
        """False for a kind that is declared but generates nothing yet.

        Callers use this to *say so* rather than to skip quietly. A capability accepted and then
        ignored is the failure R-559 removed for stacks.
        """
        registered = CAPABILITY_KINDS.get(self.kind)
        return bool(registered and registered.implemented)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "name": self.name, "config": dict(self.config)}

    @classmethod
    def from_dict(cls, data: Any) -> "Capability":
        if not isinstance(data, dict):
            raise InvalidIRError("a capability must be a mapping")
        return cls(
            kind=data.get("kind", ""),
            name=data.get("name", ""),
            config=data.get("config", {}) or {},
        )


def parse_capabilities(raw: Any) -> tuple[Capability, ...]:
    """Read the `capabilities` list of an IR document, rejecting duplicates by name."""
    if raw in (None, ()):
        return ()
    if not isinstance(raw, (list, tuple)):
        raise InvalidIRError("capabilities must be a list")
    parsed = tuple(Capability.from_dict(item) for item in raw)
    names = [c.name for c in parsed]
    duplicates = {name for name in names if names.count(name) > 1}
    if duplicates:
        raise InvalidIRError(f"duplicate capability names: {', '.join(sorted(duplicates))}")
    return parsed

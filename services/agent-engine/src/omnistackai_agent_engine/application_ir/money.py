"""Money: payments, a double-entry ledger, refunds, commission and payouts (R-567).

R-512 gave the Studio a Stripe/Razorpay checkout injected into the web app: the amount came from the
client, nothing was recorded, and with no keys it answered 500. Real products need the money to be
part of the application - a shop takes payment for an order, a marketplace keeps a commission and
owes its sellers the rest, a refund reverses both, a seller withdraws what they earned.

One `money` capability per app:

    {"kind": "money", "name": "shop_money", "config": {
        "currency": "INR",
        "charges": [{"entity": "Order", "amount": "total_amount", "payee": "vendor_id"}],
        "commission_bps": 1000,
        "refund_roles": ["manager"]}}

    currency        ISO 4217; every amount is stored in its minor unit (paise, cents) as an integer
    charges         what can be paid for: an entity, the field holding its price, and optionally the
                    field naming the user who earns the sale (a vendor, a driver)
    commission_bps  the platform's share of a sale with a payee, in basis points (1000 = 10%)
    refund_roles    who may refund (admin always)

Decisions worth stating:

**The amount is never the client's.** Checkout reads the price from the stored record.

**Balances are never stored.** Every movement is a ledger entry (debit one account, credit another,
amount > 0), and a balance is the sum of an account's entries - so the books always balance and
cannot drift from a forgotten update.

**Keys come last.** The provider is chosen at runtime: `mock` works offline end to end (checkout,
confirm, refund), so an app is fully usable before anyone has a Stripe or Razorpay account; with
keys set, the same flow goes through the real provider and its signed, idempotent webhooks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .errors import InvalidIRError

_IDENT = re.compile(r"^[a-z][a-z0-9_]{0,48}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
#: ISO 4217 currencies with no minor unit: an amount of 500 is 500, not 5.00.
ZERO_DECIMAL = frozenset({"JPY", "KRW", "VND", "CLP", "ISK", "UGX", "XAF", "XOF", "PYG", "RWF"})


@dataclass(frozen=True, slots=True)
class Charge:
    entity: str
    amount: str
    payee: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.entity, str) or not self.entity.strip():
            raise InvalidIRError("a charge names an entity")
        for label, value in (("amount", self.amount), ("payee", self.payee)):
            if value is not None and not _IDENT.match(str(value)):
                raise InvalidIRError(f"charge {label} must name a lower_snake_case field: {value!r}")


@dataclass(frozen=True, slots=True)
class Money:
    currency: str
    charges: tuple[Charge, ...]
    commission_bps: int = 0
    refund_roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.currency, str) or not _CURRENCY.match(self.currency):
            raise InvalidIRError(f"money currency must be an ISO 4217 code like INR or USD: {self.currency!r}")
        if not self.charges:
            raise InvalidIRError("money needs at least one charge (what is paid for)")
        entities = [c.entity for c in self.charges]
        if len(set(entities)) != len(entities):
            raise InvalidIRError("one charge per entity")
        if not isinstance(self.commission_bps, int) or not 0 <= self.commission_bps <= 10000:
            raise InvalidIRError("commission_bps is 0..10000 (1000 = 10%)")
        for role in self.refund_roles:
            if not _IDENT.match(str(role)):
                raise InvalidIRError(f"refund role must be lower_snake_case: {role!r}")

    @property
    def minor_unit(self) -> int:
        """How many minor units one major unit is (100 for INR/USD, 1 for JPY)."""
        return 1 if self.currency in ZERO_DECIMAL else 100

    @property
    def refunders(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.refund_roles, "admin")))

    def charge_for(self, entity: str) -> Charge | None:
        return next((c for c in self.charges if c.entity == entity), None)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Money":
        if not isinstance(config, dict):
            raise InvalidIRError("a money config must be an object")
        unknown = set(config) - {"currency", "charges", "commission_bps", "refund_roles"}
        if unknown:
            raise InvalidIRError(f"unknown money keys: {', '.join(sorted(unknown))}")
        raw = config.get("charges") or []
        if not isinstance(raw, list):
            raise InvalidIRError("money charges must be a list")
        charges = []
        for item in raw:
            if not isinstance(item, dict):
                raise InvalidIRError("each charge is an object")
            extra = set(item) - {"entity", "amount", "payee"}
            if extra:
                raise InvalidIRError(f"unknown charge keys: {', '.join(sorted(extra))}")
            charges.append(Charge(item.get("entity", ""), item.get("amount", ""), item.get("payee") or None))
        return cls(
            currency=str(config.get("currency") or "USD").upper(),
            charges=tuple(charges),
            commission_bps=int(config.get("commission_bps") or 0),
            refund_roles=tuple(config.get("refund_roles") or ()),
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "currency": self.currency,
            "charges": [{"entity": c.entity, "amount": c.amount, **({"payee": c.payee} if c.payee else {})}
                        for c in self.charges],
            "commission_bps": self.commission_bps,
            "refund_roles": list(self.refund_roles),
        }


def validate_money_config(name: str, config: dict[str, Any]) -> None:
    try:
        Money.from_config(config)
    except (InvalidIRError, ValueError, TypeError) as error:
        raise InvalidIRError(f"money {name!r}: {error}") from error


def money_of(ir: Any) -> "Money | None":
    """The app's money configuration (one per app), or None."""
    for capability in getattr(ir, "capabilities", ()):
        if capability.kind == "money":
            return Money.from_config(capability.config)
    return None

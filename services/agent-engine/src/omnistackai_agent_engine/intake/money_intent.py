"""Money read from the prompt (R-567): what is paid for, in what currency, and who keeps what.

The planning model is told about the `money` capability; this is the deterministic floor under it,
as `ownership_intent` is for ownership. When the prompt clearly says that something is paid for
("customers pay for their orders", "book and pay", "checkout") and the plan has no money, a rule is
added for the entity whose price it names:

    the entity     the one with a price-like number field (price, total, amount, fee, cost)
    the currency   ₹ / rupee / INR -> INR, $ -> USD, € -> EUR, £ -> GBP; else USD
    a commission   "a 10% commission" / "takes 15%" -> commission_bps, paid to the plan's seller-like
                   role (vendor, seller, driver, host, ...) through a `<role>_id` field on the entity
"""

from __future__ import annotations

import re
from typing import Any

_PAYS = re.compile(r"\b(pay|pays|paying|paid|payment|payments|checkout|check out|purchase|buy|buys|charge|charged)\b", re.I)
_COMMISSION = re.compile(r"(\d{1,2}(?:\.\d+)?)\s*%\s*(?:commission|fee|cut|platform fee|service fee)|"
                         r"(?:commission|fee|cut|takes?|keeps?)\s+(?:of\s+)?(\d{1,2}(?:\.\d+)?)\s*%", re.I)
_PRICE_FIELDS = ("total_amount", "total", "amount", "price", "total_price", "fee", "cost", "subtotal")
_SELLERS = ("vendor", "seller", "merchant", "driver", "host", "provider", "instructor", "freelancer", "courier",
            "restaurant", "owner", "tutor", "trainer", "artist", "creator")
_CURRENCIES = (("INR", ("₹", "rupee", " inr", "india")), ("EUR", ("€", " eur", "euro")), ("GBP", ("£", " gbp", "pound")),
               ("USD", ("$", " usd", "dollar")))


def _currency(prompt: str) -> str:
    text = f" {prompt.lower()}"
    for code, signs in _CURRENCIES:
        if any(sign in text for sign in signs):
            return code
    return "USD"


def money_from_prompt(prompt: str, data: dict[str, Any]) -> list[str]:
    if not prompt or not _PAYS.search(prompt):
        return []
    capabilities = data.setdefault("capabilities", [])
    if any(isinstance(c, dict) and c.get("kind") == "money" for c in capabilities):
        return []
    entities = [e for e in data.get("entities") or () if isinstance(e, dict)]
    priced = []
    for entity in entities:
        fields = {str(f.get("name")): f for f in entity.get("fields") or () if isinstance(f, dict)}
        field = next((n for n in _PRICE_FIELDS if n in fields and fields[n].get("type") in ("float", "int")), None)
        if field:
            mentioned = str(entity.get("name", "")).lower().rstrip("s") in prompt.lower()
            priced.append((not mentioned, str(entity.get("name")), field, entity))
    if not priced:
        return []
    _, name, amount, entity = sorted(priced, key=lambda p: p[0])[0]  # one the prompt names, first
    charge: dict[str, Any] = {"entity": name, "amount": amount}
    config: dict[str, Any] = {"currency": _currency(prompt), "charges": [charge], "commission_bps": 0, "refund_roles": []}
    notes = [f"payments for {name} ({name}.{amount}, {config['currency']}); refunds by admin"]
    match = _COMMISSION.search(prompt)
    roles = [str(r.get("id")) for r in data.get("roles") or () if isinstance(r, dict)]
    seller = next((r for r in roles if r in _SELLERS), None)
    if match and seller:
        percent = float(match.group(1) or match.group(2))
        config["commission_bps"] = int(round(percent * 100))
        payee = f"{seller}_id"
        fields = entity.setdefault("fields", [])
        if not any(isinstance(f, dict) and f.get("name") == payee for f in fields):
            fields.append({"name": payee, "type": "uuid", "required": False})
        charge["payee"] = payee
        notes.append(f"a {percent:g}% commission; the rest is owed to the {seller} ({name}.{payee}) and paid out")
    capabilities.append({"kind": "money", "name": "app_money", "config": config})
    return notes

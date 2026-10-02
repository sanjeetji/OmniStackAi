"""R-580: the privacy a two-sided domain implies, when the prompt does not say.

"A logistics app where customers book parcel shipments" names no rule, yet in every logistics business
a shipment is the customer's who booked it and the driver's it is assigned to - not every other
customer's. Found in R-580's live proof: without this, any signed-in customer listed every shipment.

Only where the plan has no rule for the entity already, and only for domains where creator plus
assignee is the whole story. Food delivery and marketplaces are left out on purpose: their merchants
must see the orders of their own restaurant or listings, which needs ownership through a relation
(PC-120) - a creator rule would hide every order from them.
"""

from __future__ import annotations

from typing import Any

#: domain -> (entity, the role it is assigned to, roles that coordinate and see all)
_DEFAULTS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "logistics": ("Shipment", "driver", ("dispatcher",)),
    "rideshare": ("Trip", "driver", ("dispatcher",)),
    "home-services": ("Job", "technician", ("dispatcher", "manager")),
}


def domain_defaults(domain: str, data: dict[str, Any]) -> list[str]:
    spec = _DEFAULTS.get(domain)
    if spec is None:
        return []
    entity_name, role, coordinators = spec
    roles = {str(r.get("id")) for r in data.get("roles") or () if isinstance(r, dict)}
    entity = next((e for e in data.get("entities") or () if isinstance(e, dict) and e.get("name") == entity_name), None)
    capabilities = data.setdefault("capabilities", [])
    if entity is None or role not in roles:
        return []
    if any(isinstance(c, dict) and c.get("kind") == "ownership" and (c.get("config") or {}).get("entity") == entity_name
           for c in capabilities):
        return []
    field = f"{role}_id"
    fields = entity.setdefault("fields", [])
    if not any(isinstance(f, dict) and f.get("name") == field for f in fields):
        fields.append({"name": field, "type": "uuid", "required": False})
    see_all = [r for r in coordinators if r in roles]
    capabilities.append({"kind": "ownership", "name": f"{entity_name.lower()}_ownership", "config": {
        "entity": entity_name, "read": "own", "write": "own", "see_all": see_all, "assignee": field}})
    return [f"a {domain.replace('-', ' ')} {entity_name.lower()} is its customer's and its assigned {role}'s "
            f"({entity_name}.{field}); {', '.join(see_all) or 'admin'} see all"]

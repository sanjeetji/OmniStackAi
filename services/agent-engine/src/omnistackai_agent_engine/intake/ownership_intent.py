"""Who owns what, read from the prompt itself (R-570).

The planning model is told about `ownership` rules, but a weak or hurried model can leave them out,
and "private notes" that everyone can read is the failure PC-008 found live. So the words that can
only mean "each user's own records" are read here too, deterministically, and a rule is added when
the plan has none for that entity:

    "private notes", "personal journal entries"    -> Note: read own, write own
    "my own recipes", "your own expenses"           -> Recipe / Expense: read own, write own

An owner is the user who *created* the record. "A driver sees only their own orders" means the
orders a driver is *assigned*, which a customer created - a creator rule would hide every order from
every driver - so "their own" is left to the model, which is told the difference, and assigned-to
visibility is a later rule kind.
"""

from __future__ import annotations

import re
from typing import Any

from .ir_repair import _drop_owner_reference, resolve_entity_reference

_OWN_PHRASES = (
    re.compile(r"\b(?:private|personal)\s+(?P<a>[a-z]+)(?:\s+(?P<b>[a-z]+))?", re.IGNORECASE),
    re.compile(r"\b(?:my|your)\s+own\s+(?P<a>[a-z]+)(?:\s+(?P<b>[a-z]+))?", re.IGNORECASE),
)


def _entity_for(word: str, entities: list[str]) -> str | None:
    return resolve_entity_reference(word, entities)


def ownership_from_prompt(prompt: str, data: dict[str, Any]) -> list[str]:
    """Add an own/own rule for each entity the prompt calls private; return a note per rule added."""
    entities = [str(e.get("name")) for e in data.get("entities") or () if isinstance(e, dict) and e.get("name")]
    if not entities or not prompt:
        return []
    capabilities = data.setdefault("capabilities", [])
    ruled = {
        str((c.get("config") or {}).get("entity"))
        for c in capabilities
        if isinstance(c, dict) and c.get("kind") == "ownership"
    }
    names = {str(c.get("name")) for c in capabilities if isinstance(c, dict)}
    notes: list[str] = []
    for pattern in _OWN_PHRASES:
        for match in pattern.finditer(prompt):
            # Only a plural reads as "each user's records": "private notes" is, "a private clinic" is
            # a kind of clinic. "personal journal entries": the second word, then the first.
            entity = None
            for word in (match.group("b"), match.group("a")):
                if word and word.lower().endswith("s"):
                    entity = entity or _entity_for(word, entities) or _entity_for(f"{match.group('a')}{word}", entities)
            if entity is None or entity in ruled:
                continue
            name = f"{entity.lower()}_ownership"
            while name in names:
                name += "_"
            capabilities.append({"kind": "ownership", "name": name,
                                 "config": {"entity": entity, "read": "own", "write": "own", "see_all": []}})
            ruled.add(entity)
            names.add(name)
            target = next(e for e in data["entities"] if isinstance(e, dict) and e.get("name") == entity)
            _drop_owner_reference(target, entity, notes)
            notes.append(f"'{match.group(0)}': each user sees and changes only their own {entity} records")
    return notes

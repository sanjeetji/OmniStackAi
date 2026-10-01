"""Live updates read from the prompt (R-569): which entities change while people watch.

The planning model is told about the `realtime` capability; this is the deterministic floor under it.
A sentence that asks for something to be seen as it happens - "live order status", "track the
delivery in real time", "see new messages instantly", "updates without refreshing" - makes live the
entities it names. When it names none ("everything updates live"), the entities with a lifecycle or
a position (latitude / longitude) are the ones that change while someone watches.
"""

from __future__ import annotations

import re
from typing import Any

from .ir_repair import resolve_entity_reference

_LIVE = re.compile(
    r"\b(?:real[- ]?time|live\b|instantly|instant updates?|as (?:it|they) happens?|without (?:a )?refresh\w*|"
    r"track(?:s|ed|ing)?\b|push updates?|auto[- ]?refresh\w*)",
    re.I,
)
_WATCHING = {"see", "sees", "watch", "watches", "track", "tracks", "get", "gets", "receive", "receives", "can",
             "will", "should", "follow", "follows", "know", "knows", "view", "views"}
# "live music", "where they live", "deliver..." are not live updates.
_NOT_LIVE = re.compile(r"\b(?:live (?:music|stream\w*|event|concert|chat support)|where (?:they|you|we|people) live|live in)\b", re.I)


def realtime_from_prompt(prompt: str, data: dict[str, Any]) -> list[str]:
    if not prompt:
        return []
    capabilities = data.setdefault("capabilities", [])
    if any(isinstance(c, dict) and c.get("kind") == "realtime" for c in capabilities):
        return []
    entities = [str(e.get("name")) for e in data.get("entities") or () if isinstance(e, dict) and e.get("name")]
    if not entities:
        return []
    live: list[str] = []
    asked = False
    for sentence in re.split(r"[.;\n!?]+", prompt):
        if not _LIVE.search(sentence) or _NOT_LIVE.search(sentence):
            continue
        asked = True
        words = re.findall(r"[a-zA-Z]+", sentence)
        for i, word in enumerate(words):
            # "Customers see live order status": the customers watch; the order is what changes.
            if i + 1 < len(words) and words[i + 1].lower() in _WATCHING:
                continue
            found = resolve_entity_reference(word, entities)
            if found and found not in live:
                live.append(found)
    if not asked:
        return []
    if not live:
        with_lifecycle = {str((c.get("config") or {}).get("entity")) for c in capabilities
                          if isinstance(c, dict) and c.get("kind") == "workflow"}
        for entity in data.get("entities") or ():
            fields = {str(f.get("name")) for f in entity.get("fields") or () if isinstance(f, dict)}
            if entity.get("name") in with_lifecycle or {"latitude", "longitude"} <= fields or {"lat", "lng"} <= fields:
                live.append(str(entity.get("name")))
    if not live:
        return []
    capabilities.append({"kind": "realtime", "name": "live_updates", "config": {"entities": live}})
    return [f"live updates for {', '.join(live)}: changes reach the people who may see them as they happen"]

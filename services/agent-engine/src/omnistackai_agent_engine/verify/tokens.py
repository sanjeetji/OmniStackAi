"""PC-125: text in a background colour is invisible - the design tokens a model confuses, put right.

The generated apps' design system pairs each surface colour with a text colour: `bg-muted` with
`text-muted-foreground`, `bg-card` with `text-card-foreground`. A model writing a page reaches for
`text-muted` for quiet text - which is the *surface* colour, the page's own background. The PC-122
benchmark's clinic home page measured 1.00:1 contrast: a paragraph nobody could read. 64 uses across
three projects, every one in a model-written page.

The fix is certain - the surface token used as a text colour always means its foreground pair - so
it is applied without asking the model. `text-primary` and `text-destructive` are real text colours
and are left alone; so is `text-background` (light text on a dark surface is a deliberate inversion).
"""

from __future__ import annotations

import re
from pathlib import Path

#: Surface colours that are never text colours, each with the text colour that belongs on it.
SURFACE_TEXT = {"muted": "muted-foreground", "card": "card-foreground", "popover": "popover-foreground",
                "secondary": "secondary-foreground", "accent": "accent-foreground", "input": "foreground",
                "border": "muted-foreground"}
# `text-muted` but not `text-muted-foreground`; an optional opacity (`/70`) and variants (`hover:`) stay.
_SURFACE_AS_TEXT = re.compile(r"(?<![\w-])text-(" + "|".join(SURFACE_TEXT) + r")(?![\w-])")


def fix_invisible_text(text: str) -> tuple[str, int]:
    """Every surface colour used as a text colour, as the text colour that belongs on it."""
    count = 0

    def _swap(match: re.Match) -> str:
        nonlocal count
        count += 1
        return "text-" + SURFACE_TEXT[match.group(1)]

    return _SURFACE_AS_TEXT.sub(_swap, text), count


def fix_invisible_text_in(web_dir: str | Path, paths: list[str]) -> dict[str, int]:
    """Apply to these web-app-relative files; returns how many classes changed in each."""
    web = Path(web_dir)
    changed: dict[str, int] = {}
    for rel in paths:
        file = web / rel
        if not file.is_file():
            continue
        text = file.read_text(encoding="utf-8", errors="replace")
        fixed, count = fix_invisible_text(text)
        if count:
            file.write_text(fixed, encoding="utf-8")
            changed[rel] = count
    return changed

"""Layout variants, so two products in one archetype do not render the same page (R-556).

R-543 stopped a shop, a blog and a booking site looking alike. Two shops still did:
`_public_home_page` rendered one structure — centred hero, offering grid, browse row, footer — and
only the words changed. Two people building storefronts got the same page with different nouns.

The variant is chosen from a seed derived from the product itself, which gives the two properties
that matter and are in tension: **two different products differ**, and **one product is stable**.
Randomness would give the first and destroy the second, and a stable-but-identical default gives
the second and never the first.

Each variant is a genuinely different arrangement — where the hero sits, whether the offering is a
grid or a list, whether the sections are banded or open — not a different padding value. A visitor
should not be able to tell two of these came from the same generator.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum


class Layout(StrEnum):
    """The arrangements the deterministic generator can produce for a public home page."""

    #: Centred hero over a card grid. The safest arrangement, and the one that reads as a product
    #: page rather than a document.
    CENTERED = "centered"
    #: Hero text on the left beside a panel, offering as a numbered list. Reads as a service.
    SPLIT = "split"
    #: A full-bleed colour band carrying the hero, offering as wide rows. Reads as a brand.
    BANNER = "banner"
    #: Large type, no eyebrow, offering as a plain two-column index. Reads as editorial.
    EDITORIAL = "editorial"


#: Ordered so the seed maps stably: appending a variant later must not reshuffle existing projects.
LAYOUTS: tuple[Layout, ...] = (Layout.CENTERED, Layout.SPLIT, Layout.BANNER, Layout.EDITORIAL)


@dataclass(frozen=True, slots=True)
class LayoutChoice:
    """Which arrangement, and why — so a surprising page can be explained rather than guessed at."""

    layout: Layout
    seed: str

    @property
    def reason(self) -> str:
        return f"layout {self.layout.value}, chosen from the product name so it stays stable"


def pick_layout(seed: str, *, allowed: tuple[Layout, ...] = LAYOUTS) -> LayoutChoice:
    """Choose a layout for `seed`, deterministically.

    Hashed rather than taken from `len(seed) % n` or similar: a short name and a long one should be
    as likely to differ as any other pair, and adjacent names ("Bakery One", "Bakery Two") should
    not collapse onto the same arrangement.
    """
    if not allowed:
        raise ValueError("at least one layout must be allowed")
    digest = hashlib.sha256((seed or "app").encode("utf-8")).digest()
    return LayoutChoice(allowed[digest[0] % len(allowed)], seed or "app")


#: Some archetypes read badly in some arrangements, and forcing variety at the cost of fit is how
#: a generator produces something that is different but worse. A publication belongs in editorial
#: or centred; a storefront needs its grid and is wrong as an index.
ARCHETYPE_LAYOUTS: dict[str, tuple[Layout, ...]] = {
    "storefront": (Layout.CENTERED, Layout.BANNER, Layout.SPLIT),
    "publication": (Layout.EDITORIAL, Layout.CENTERED),
    "booking": (Layout.SPLIT, Layout.CENTERED, Layout.BANNER),
    "directory": (Layout.CENTERED, Layout.SPLIT),
    "saas": (Layout.SPLIT, Layout.CENTERED, Layout.BANNER),
    "marketing": (Layout.CENTERED, Layout.BANNER, Layout.SPLIT, Layout.EDITORIAL),
}


def layout_for(name: str, archetype: str | None = None) -> LayoutChoice:
    """The layout for a product, restricted to the arrangements its archetype reads well in."""
    allowed = ARCHETYPE_LAYOUTS.get(archetype or "", LAYOUTS)
    return pick_layout(name, allowed=allowed)

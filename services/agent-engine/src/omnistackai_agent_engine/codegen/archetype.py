"""What kind of product is this? (R-543)

Until now there were two answers — `public_website` and `admin_panel` — chosen by matching eight
keywords against the prompt and defaulting to the console. Two consequences the founder kept
hitting: "a website to sell my product" matched none of those keywords and so generated an
internal dashboard, and every public site that *was* recognised got the same landing page
regardless of whether it sold shoes, published articles or took bookings.

This module answers the question properly, and does it deterministically so the answer is the same
with or without a model:

* it reads the **IR** as well as the prompt. Entity names are the strongest signal available —
  a project with `Product`, `Order` and `Cart` is a storefront whatever words the user typed —
  and they come from the model's own understanding of the request, so they are usually a better
  description of the product than the sentence that produced them;
* it **scores** every archetype rather than taking the first keyword that matches, so a phrase
  like "a blog to sell my art prints" resolves to whichever evidence is stronger instead of
  whichever rule happens to be first;
* it returns `admin_panel` only when the caller asks for the staff console, never as a default
  for a public app.

Pure and offline: no model call, no I/O, and the same inputs always give the same answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from ..application_ir import ApplicationIR


class Archetype(StrEnum):
    """The kinds of product the generator knows how to shape a home page for."""

    STOREFRONT = "storefront"
    TRACKER = "tracker"
    PUBLICATION = "publication"
    BOOKING = "booking"
    DIRECTORY = "directory"
    SAAS = "saas"
    MARKETING = "marketing"
    ADMIN_PANEL = "admin_panel"


#: The archetypes a public, visitor-facing app can be. `admin_panel` is deliberate, never inferred.
PUBLIC_ARCHETYPES = (
    Archetype.STOREFRONT,
    Archetype.TRACKER,
    Archetype.PUBLICATION,
    Archetype.BOOKING,
    Archetype.DIRECTORY,
    Archetype.SAAS,
    Archetype.MARKETING,
)


@dataclass(frozen=True, slots=True)
class _Signals:
    """What suggests one archetype. Entities outweigh wording; see the module docstring."""

    entities: tuple[str, ...] = ()
    phrases: tuple[str, ...] = ()
    screens: tuple[str, ...] = ()


# Weights. An entity name is worth more than a phrase because it survives paraphrasing: a user can
# describe a shop a hundred ways, but the IR still ends up with a Product and an Order.
_ENTITY_WEIGHT = 3
_PHRASE_WEIGHT = 2
_SCREEN_WEIGHT = 1

_SIGNALS: dict[Archetype, _Signals] = {
    Archetype.STOREFRONT: _Signals(
        entities=("product", "order", "cart", "basket", "sku", "inventory", "payment", "checkout",
                  "shipment", "discount", "coupon", "catalog", "catalogue", "variant"),
        phrases=("sell my", "sell our", "sell online", "online store", "online shop", "ecommerce",
                 "e-commerce", "storefront", "shop for", "webshop", "marketplace to buy",
                 "buy and sell", "add to cart", "checkout"),
        screens=("cart", "checkout", "product", "catalog", "catalogue", "orders"),
    ),
    Archetype.TRACKER: _Signals(
        entities=("habit", "checkin", "streak", "goal", "todo", "task", "reminder", "journal",
                  "mood", "workout", "exercise", "expense", "budget", "meal", "medication",
                  "routine", "milestone"),
        phrases=("habit tracker", "track my", "keep track", "to-do", "todo", "task list",
                 "expense tracker", "budget tracker", "fitness tracker", "workout log", "journal",
                 "personal tracker", "daily check", "goal tracker"),
        screens=("habits", "tasks", "today", "goals", "streaks", "checkins"),
    ),
    Archetype.PUBLICATION: _Signals(
        entities=("post", "article", "story", "author", "category", "tag", "comment", "issue",
                  "newsletter", "publication", "editorial"),
        phrases=("blog", "news site", "news website", "magazine", "publish articles",
                 "publishing platform", "newsletter", "editorial", "cms", "write posts",
                 "publish posts"),
        # PC-006: not "editor" — every generated CRUD app has `*_editor` screens, so a habit
        # tracker with no other evidence became a blog ("Start reading", "What we cover").
        screens=("posts", "articles", "feed", "archive"),
    ),
    Archetype.BOOKING: _Signals(
        entities=("appointment", "booking", "reservation", "slot", "schedule", "session",
                  "availability", "service", "patient", "guest", "table", "room", "class"),
        phrases=("book an", "booking", "appointment", "reservation", "reserve a", "schedule a",
                 "scheduling", "calendar of", "time slot", "clinic", "salon", "consultation"),
        screens=("book", "booking", "appointments", "calendar", "schedule", "slots"),
    ),
    Archetype.DIRECTORY: _Signals(
        entities=("listing", "provider", "vendor", "profile", "member", "business", "venue",
                  "property", "job", "review", "rating"),
        phrases=("directory", "listings", "find a", "browse providers", "classifieds",
                 "job board", "property portal", "compare providers", "search for local"),
        screens=("listings", "directory", "search", "browse", "profiles"),
    ),
    Archetype.SAAS: _Signals(
        entities=("workspace", "team", "subscription", "plan", "usage", "project", "invoice",
                  "organization", "organisation", "seat", "metric", "report"),
        phrases=("saas", "dashboard for", "analytics platform", "internal tool", "team workspace",
                 "project management", "track metrics", "reporting tool", "b2b tool"),
        screens=("dashboard", "reports", "analytics", "workspace", "billing"),
    ),
    Archetype.MARKETING: _Signals(
        entities=("lead", "contact", "enquiry", "inquiry", "testimonial", "feature", "faq",
                  "subscriber"),
        phrases=("landing page", "marketing website", "marketing site", "portfolio",
                 "promote my", "showcase", "brochure site", "coming soon", "waitlist",
                 "one page site", "company website"),
        screens=("contact", "pricing", "about", "features"),
    ),
}

_WORD_RE = re.compile(r"[a-z0-9]+")


def _words(text: str) -> set[str]:
    """Lowercase word set, with a naive singular so `products` matches `product`."""
    found = set()
    # PC-006: entity names are CamelCase ("DailyCheckIn"); read them as words, and joined.
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    for word in _WORD_RE.findall(spaced.lower()) + _WORD_RE.findall(text.lower()):
        found.add(word)
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            found.add(word[:-1])
    return found


def score_archetypes(ir: ApplicationIR | None, prompt: str = "") -> dict[Archetype, int]:
    """Score every public archetype against the IR and the prompt. Higher is a better fit.

    Exposed because a caller debugging a surprising classification wants the evidence, not just
    the verdict — and because the tests assert on the margins, not only the winner.
    """
    text = prompt.lower()
    entity_words: set[str] = set()
    screen_words: set[str] = set()
    if ir is not None:
        text = f"{text} {ir.name} {ir.description}".lower()
        for entity in ir.entities:
            entity_words |= _words(entity.name)
        for screen in ir.screens:
            screen_words |= _words(screen.id)
            screen_words |= {w for component in screen.components for w in _words(component)}

    scores: dict[Archetype, int] = {}
    for archetype, signals in _SIGNALS.items():
        score = 0
        score += _ENTITY_WEIGHT * sum(1 for name in signals.entities if name in entity_words)
        score += _PHRASE_WEIGHT * sum(1 for phrase in signals.phrases if phrase in text)
        score += _SCREEN_WEIGHT * sum(1 for name in signals.screens if name in screen_words)
        scores[archetype] = score
    return scores


def detect_archetype(ir: ApplicationIR | None, prompt: str = "") -> Archetype:
    """The archetype of the public, visitor-facing app.

    Never returns `admin_panel`: the staff console is a decision the assembler makes, not something
    inferred from wording. With no evidence either way the answer is `MARKETING` — a hero, what the
    product offers and a way in, which is the least wrong thing to show a visitor who arrives at a
    product we know nothing else about. It is emphatically not a dashboard, which is what the old
    default produced.
    """
    scores = score_archetypes(ir, prompt)
    best = max(scores.values(), default=0)
    if best == 0:
        return Archetype.MARKETING
    # Ties resolve by PUBLIC_ARCHETYPES order, which is stable, so the answer is deterministic.
    for archetype in PUBLIC_ARCHETYPES:
        if scores.get(archetype) == best:
            return archetype
    return Archetype.MARKETING


#: What each archetype's landing page leads with, and what it invites the visitor to do. Used by
#: the deterministic generator; the model prompt carries the longer form in `llm_ui`.
HOME_COPY: dict[Archetype, dict[str, str]] = {
    Archetype.STOREFRONT: {
        "eyebrow": "Shop",
        "lede": "Browse the range and check out in a few taps.",
        "section": "What's in store",
        "section_lede": "Everything available to buy right now.",
        "cta": "Start shopping",
        "explore": "Shop by",
    },
    Archetype.TRACKER: {
        "eyebrow": "Stay on track",
        "lede": "Everything you track, in one calm place — add it once, check in every day.",
        "section": "What you'll track",
        "section_lede": "Start with one, and build the rest as you go.",
        "cta": "Get started",
        "explore": "Go to",
    },
    Archetype.PUBLICATION: {
        "eyebrow": "Latest",
        "lede": "Stories, updates and long reads, published as they land.",
        "section": "What we cover",
        "section_lede": "The subjects this publication follows.",
        "cta": "Start reading",
        "explore": "Read more",
    },
    Archetype.BOOKING: {
        "eyebrow": "Book online",
        "lede": "Pick a time that suits you and book it in under a minute.",
        "section": "What you can book",
        "section_lede": "Every service available to reserve.",
        "cta": "Book now",
        "explore": "Browse",
    },
    Archetype.DIRECTORY: {
        "eyebrow": "Directory",
        "lede": "Search, compare and get in touch — all in one place.",
        "section": "What you'll find",
        "section_lede": "Everything listed here, ready to search.",
        "cta": "Start browsing",
        "explore": "Explore",
    },
    Archetype.SAAS: {
        "eyebrow": "Platform",
        "lede": "Everything your team needs, in one workspace.",
        "section": "What it does",
        "section_lede": "The work this platform takes off your plate.",
        "cta": "Open the app",
        "explore": "Jump to",
    },
    Archetype.MARKETING: {
        "eyebrow": "Welcome",
        "lede": "",
        "section": "What you can do here",
        "section_lede": "Everything this product keeps track of, in one place.",
        "cta": "Get started",
        "explore": "Explore",
    },
}

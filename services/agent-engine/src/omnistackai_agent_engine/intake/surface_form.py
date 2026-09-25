"""Whether a surface is an app or a website, and why (R-562).

"A platform for food delivery with a marketing website, admin panel, customer + driver apps"
returned four Next.js websites. Every surface was built with `MobileProfile.NONE` and
`WebStrategy.NEXTJS` hardcoded, so the driver "app" was a web page and nothing anywhere said so.

R-559 established the rule for stacks: when we cannot build what was asked for, build the nearest
thing and explain. This is the same failure with a worse excuse — here we *can* build the app, and
simply did not.

Two signals decide it, in order:

* **What the prompt asked for.** "driver app", "an app for couriers", "customer + driver apps" —
  if a person said the word app next to a role, that role gets an app. This wins over everything
  else, because it is the one signal that is actually a request rather than an inference.
* **What the role does.** A courier is outdoors holding a phone; a dispatcher is at a desk. Where
  the prompt says nothing, the work decides, and the default for anything unrecognised is a web
  app — a storefront that no search engine can read is a worse failure than a missing app.

Every answer carries its reason, because "why is my admin panel not an app?" deserves better than
silence, and because the reason is what makes a wrong decision reportable instead of mysterious.

One judgement worth writing down: **"a delivery app" is a product noun, not a form-factor request.**
People say app about web products constantly, so a bare mention does not make anything mobile —
only the word next to a role does. Reading it the other way would turn "a blog app" into React
Native, and being handed a phone project you did not want is worse than being handed a web page you
can open anywhere. The founder's default stands behind this: a web app with a PWA unless somebody
actually asked for an app.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Surface kinds whose work happens on a phone, away from a desk. Used only when the prompt did not
#: say either way. Deliberately short: guessing that someone wants a mobile app is a bigger
#: imposition than guessing they want a web page, which every device can open.
FIELD_KINDS = frozenset({"driver_portal", "courier_portal", "rider_portal", "delivery_portal"})

#: Kinds that stay on the web whatever the words around them suggest. An operations console is
#: tables, filters and bulk actions; a marketing site lives or dies on being indexed.
DESK_KINDS = frozenset(
    {"admin_dashboard", "operations_console", "public_web", "marketing_site", "ops_console"}
)

#: Words that mean "phone app" rather than "application" in the general sense.
_APP_WORDS = ("app", "apps", "mobile app", "mobile apps", "android", "ios")


@dataclass(frozen=True, slots=True)
class FormFactor:
    """What a surface will be built as, and the sentence explaining it."""

    #: "mobile" or "web".
    form: str
    reason: str

    @property
    def is_mobile(self) -> bool:
        return self.form == "mobile"


def _clauses(prompt: str) -> list[str]:
    """The prompt split on the punctuation people use to list surfaces.

    "marketing website, admin-panel, customer + driver apps" is three requests, not one sentence.
    Splitting first is what lets "customer + driver apps" make both of those roles mobile while
    "admin-panel" stays a web app, without a window wide enough to swallow the whole list.
    """
    return [part for part in re.split(r"[,;.\n]| with | and then ", (prompt or "").lower()) if part.strip()]


def _tight_app_phrase(prompt: str, *terms: str) -> bool:
    """The role and the word app, side by side: "driver app", "app for the courier".

    Tight on purpose. "a delivery app with an admin panel" must not turn the admin panel into an
    app, and only adjacency can tell that apart from a genuine request.
    """
    text = (prompt or "").lower()
    for term in terms:
        term = (term or "").strip().lower()
        if not term:
            continue
        word = re.escape(term.rstrip("s"))
        for app_word in _APP_WORDS:
            if re.search(rf"(?<![a-z]){word}s?[\s-]+{app_word}(?![a-z])", text):
                return True
            if re.search(rf"(?<![a-z]){app_word}\s+(?:for|to)\s+(?:the\s+)?{word}s?(?![a-z])", text):
                return True
    return False


def _listed_as_an_app(prompt: str, *terms: str) -> bool:
    """The role appears in the same listed item as the word app.

    "customer + driver apps" names two roles and one word; both of them were asked for as apps.
    Scoped to the clause so a role listed somewhere else in the sentence is unaffected.
    """
    for clause in _clauses(prompt):
        if not any(re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", clause) for w in _APP_WORDS):
            continue
        for term in terms:
            term = (term or "").strip().lower()
            if term and re.search(rf"(?<![a-z]){re.escape(term.rstrip('s'))}s?(?![a-z])", clause):
                return True
    return False


def form_for_surface(
    *,
    kind: str,
    actor: str = "",
    name: str = "",
    prompt: str = "",
) -> FormFactor:
    """Decide whether one planned surface is a mobile app or a web app."""
    kind = (kind or "").strip().lower()
    actor = (actor or "").strip()
    role_words = (actor, kind.replace("_portal", "").replace("_", " "), name)

    # Desk work is checked first, and only an explicit "admin app" overrides it. Otherwise the
    # clause test below would read "a delivery app with an admin panel" as a request for two apps.
    if kind in DESK_KINDS:
        if _tight_app_phrase(prompt, actor, kind.replace("_", " ")):
            return FormFactor("mobile", f"you asked for an app for the {actor or kind.replace('_', ' ')}")
        return FormFactor("web", f"a {kind.replace('_', ' ')} is desk work, so this is a web app")

    if _tight_app_phrase(prompt, *role_words) or _listed_as_an_app(prompt, *role_words):
        who = actor or name or kind.replace("_", " ")
        return FormFactor("mobile", f"you asked for an app for the {who}, so this is a React Native app")

    if kind in FIELD_KINDS:
        who = actor or kind.replace("_portal", "").replace("_", " ")
        return FormFactor(
            "mobile", f"a {who} works from a phone rather than a desk, so this is a React Native app"
        )

    return FormFactor("web", "this is a web app, which opens on every device without an install")


def app_replaces_web(audience: str) -> bool:
    """Whether a mobile app takes the surface's place, or is built alongside it.

    An operator's app replaces their portal: a courier on a bike has no use for a website, and
    generating both would be two things to maintain for one job.

    A customer's app is *additional*. The public surface is how a product is found — it is the
    thing search engines read, the thing a link opens, and in the prompt that exposed this it was
    named outright ("a marketing website, ... customer + driver apps"). Replacing it with an app
    would answer one request by deleting another, which is the same disappearing act this task
    exists to end. It also matches the standing default: a web app, plus an app when one is asked
    for.
    """
    return (audience or "").strip().lower() != "customer"

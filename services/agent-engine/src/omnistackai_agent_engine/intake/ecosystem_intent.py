"""Does this prompt want one app, or a whole ecosystem? (R-555)

The planner is keyword-driven and confident: `propose_ecosystem` plans three surfaces for
"a simple blog" and two for "a todo list app". Building its `complete` option every time would
hand someone four directories they never asked for, which is a worse failure than building one
app — a user who wanted a blog can ask for an admin panel, but a user handed four apps has to
work out which ones to delete.

The signal that actually separates the two cases is whether the prompt **names more than one kind
of person**. "a food delivery app with customers, drivers and restaurants" names three;
"a simple blog" names none. That is a property of what the user wrote, not of the domain the
classifier guessed, and it is the one thing they are unambiguously telling us.

Deterministic and offline on purpose. Whether a build produces one app or four is not a decision
that should vary between runs of the same sentence, and it is not one a small local model should
be making.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Words naming a kind of person who uses the product, grouped so that synonyms for one role count
#: once — "restaurants and merchants" is one other party, not two. The customer group is listed
#: because a prompt naming only customers wants a single app.
_ACTOR_GROUPS: dict[str, tuple[str, ...]] = {
    "customer": ("customer", "customers", "shopper", "shoppers", "buyer", "buyers",
                 "guest", "guests", "client", "clients", "passenger", "passengers",
                 "patient", "patients", "reader", "readers", "student", "students"),
    # "shop", "store" and "business" are deliberately absent: they name the thing being built far
    # more often than a second party. "an online store to sell my products" is one app, not two.
    "merchant": ("merchant", "merchants", "restaurant", "restaurants", "vendor", "vendors",
                 "seller", "sellers", "supplier", "suppliers", "shopkeeper", "shopkeepers"),
    "courier": ("driver", "drivers", "courier", "couriers", "rider", "riders",
                "delivery partner", "delivery partners", "dispatcher", "dispatchers"),
    "provider": ("staff", "employee", "employees", "provider", "providers", "author",
                 "authors", "writer", "writers", "doctor", "doctors", "teacher",
                 "teachers", "agent", "agents", "stylist", "stylists", "therapist",
                 "therapists", "instructor", "instructors", "host", "hosts",
                 # R-580: the people a home-services business sends out.
                 "technician", "technicians", "plumber", "plumbers", "electrician", "electricians",
                 "cleaner", "cleaners", "handyman", "handymen"),
    "admin": ("admin", "admins", "administrator", "administrators", "moderator",
              "moderators", "operator", "operators", "superadmin", "super admin"),
}


@dataclass(frozen=True, slots=True)
class EcosystemIntent:
    """Whether to build the whole ecosystem, and the reason — so a build can explain itself."""

    build_ecosystem: bool
    actors: tuple[str, ...]
    reason: str

    #: The planner's build-scope option this implies.
    @property
    def option_id(self) -> str:
        return "complete" if self.build_ecosystem else "customer-only"


#: Words that name a record's fields. An actor word listed among them is a field too.
_FIELD_WORDS = frozenset((
    "title", "name", "date", "price", "status", "description", "note", "notes", "email", "phone",
    "isbn", "genre", "rating", "cover", "category", "tags", "tag", "quantity", "amount", "summary",
    "body", "image", "photo", "url", "link", "address", "priority", "due", "deadline", "year",
))


def _without_field_lists(text: str) -> str:
    """Drop actor words that sit alone in a list of a record's fields (PC-014, found live).

    "books with a title, author, a short note and a read/unread status" named no author - it named
    a field - yet it built a three-app publishing platform. A list item that is only an actor word,
    beside items that are field words, is a field. "customers, restaurants and drivers" has no field
    words, so it still names three kinds of people.
    """
    out = []
    for sentence in re.split(r"[.!?\n]", text):
        items = [i.strip() for i in re.split(r",|;|:|\band\b|\bwith\b", sentence)]
        words = [re.sub(r"^(a|an|the|its|their)\s+", "", i) for i in items]
        if sum(1 for w in words if any(f in re.findall(r"[a-z]+", w) for f in _FIELD_WORDS)) >= 2:
            actor_words = {w for group in _ACTOR_GROUPS.values() for w in group}
            items = [i for i, w in zip(items, words) if w not in actor_words]
        out.append(", ".join(items))
    return ". ".join(out)


def named_actors(prompt: str) -> tuple[str, ...]:
    """The kinds of person this prompt names, deduplicated by role group and sorted.

    Matched on word boundaries so "drivers" counts and "driven" does not, and so "storage" is not
    read as a "store".
    """
    text = _without_field_lists((prompt or "").lower())
    found = set()
    for group, words in _ACTOR_GROUPS.items():
        for word in words:
            if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text):
                found.add(group)
                break
    return tuple(sorted(found))


#: R-580: domains with a second party built in, and the words that say the prompt is about one. A
#: ride-hailing app has drivers whether or not the prompt names them; "plan a trip" is not ride-hailing.
_IMPLIED: dict[str, tuple[tuple[str, ...], str, tuple[str, ...]]] = {
    "food-delivery": (("merchant", "courier"), "restaurants and couriers", ("food delivery", "deliver food", "food ordering")),
    "rideshare": (("courier",), "drivers", ("rideshare", "ride sharing", "ride-sharing", "ride hailing", "ride-hailing", "taxi")),
    "marketplace": (("merchant",), "sellers", ("marketplace", "multi-vendor", "multi vendor")),
    "logistics": (("courier",), "drivers", ("logistics", "shipment", "shipments", "parcel", "parcels", "package delivery",
                                            "courier service", "freight", "last mile", "last-mile")),
    "home-services": (("provider",), "technicians", ("home services", "home service", "plumber", "plumbing", "electrician",
                                                      "handyman", "cleaning service", "house cleaning", "appliance repair",
                                                      "pest control")),
}


def implied_parties(prompt: str) -> tuple[str, tuple[str, ...], str] | None:
    """(domain, actor groups, who) when the prompt is about a two-sided domain, else None."""
    from .scope_compiler import classify_domain

    match = classify_domain(prompt)
    if match is None or match.domain not in _IMPLIED:
        return None
    groups, who, core = _IMPLIED[match.domain]
    text = " ".join((prompt or "").lower().split())
    if not any(re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text) for word in core):
        return None
    return match.domain, groups, who


def detect_ecosystem_intent(prompt: str) -> EcosystemIntent:
    """Decide from the prompt alone whether the user asked for more than one app.

    An ecosystem needs a second party. One kind of person — or none named at all — is a single
    app, which already comes with its own admin console, so nothing is lost by defaulting there.
    """
    actors = named_actors(prompt)
    # Neither a customer nor an admin makes an ecosystem on its own: a single app is already a
    # customer-facing app *plus* an admin console (R-541), so naming either changes nothing. What
    # makes this an ecosystem is a second party with their own job — a courier, a merchant, a
    # doctor — who needs a different app from the person they serve.
    second_parties = tuple(a for a in actors if a not in ("customer", "admin"))

    if second_parties:
        listed = " and ".join(
            [", ".join(second_parties[:-1]), second_parties[-1]] if len(second_parties) > 1
            else list(second_parties)
        )
        return EcosystemIntent(
            True,
            actors,
            f"the request names {listed} alongside the people they serve, so each side gets its "
            f"own app over one shared API and database",
        )
    implied = implied_parties(prompt)
    if implied is not None:
        domain, groups, who = implied
        return EcosystemIntent(
            True,
            tuple(sorted(set(actors) | set(groups))),
            f"a {domain.replace('-', ' ')} business has {who} as well as the customers they serve, so each side "
            f"gets its own app over one shared API and database",
        )
    if actors:
        return EcosystemIntent(
            False,
            actors,
            f"the request names one kind of user ({', '.join(actors)}), so this is a single app "
            f"with its own admin console",
        )
    return EcosystemIntent(
        False,
        (),
        "the request names no second kind of user, so this is a single app with its own admin console",
    )

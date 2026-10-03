"""PC-128: the project brief - a few questions after the prompt, every answer pre-filled.

The founder's direction: after the prompt, ask what the platform needs to build what the person
actually wants - different questions for different prompts, a smart default for every one, skip any
of it, and "use smart defaults" to build at once. Simple for someone non-technical, complete for a
developer.

``propose_brief(prompt, locale=, timezone=)`` answers instantly, with no model call:

* **apps** - the scope (PC-127);
* **features** - the building blocks the product needs, ticked when the prompt asks for them or the
  kind of product calls for them, each with its reason; the rest offered as suggestions;
* **questions** - only what this prompt leaves open (how customers pay, when reminders go out, who
  may sign up, the commission a marketplace keeps ...), each with an answer already chosen;
* **brand** - name, colours, style and fonts, chosen for this kind of product (PC-099);
* **region** - languages, currency and time zone, from the prompt or the person's own browser;
* **advanced** - the backend language and the database.

``apply_brief`` turns the answers into facts the build cannot drift from: chosen features and
answers become plain sentences in the plan's description, which the planner and the deterministic
readers (payments, reminders, live updates, notifications, privacy) already understand; a feature
switched off is removed from the plan after planning; name, brand and backend are set directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

from .scope import MOBILE, ProjectScope, propose_scope

#: Most specific first: "a clinic booking system ... appointments" reminds of the appointment.
_TRANSACTIONS = ("appointment", "reservation", "class", "lesson", "session", "visit", "delivery", "ride", "trip", "rental",
                 "shipment", "ticket", "order", "job", "event", "invoice", "subscription", "loan", "booking")


@dataclass(frozen=True)
class Feature:
    id: str
    label: str
    included: bool
    reason: str
    #: The plan's capability kind it switches, when it is one of the platform's building blocks.
    capability: str = ""
    #: Named in the prompt: on, and kept on (the prompt is the person's own words).
    from_prompt: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label, "included": self.included, "reason": self.reason,
                "capability": self.capability, "from_prompt": self.from_prompt}


@dataclass(frozen=True)
class Question:
    id: str
    question: str
    options: tuple[tuple[str, str], ...]  # (value, label)
    answer: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "question": self.question, "options": [{"value": v, "label": l} for v, l in self.options],
                "answer": self.answer, "reason": self.reason}


@dataclass(frozen=True)
class Brief:
    prompt: str
    scope: ProjectScope
    features: tuple[Feature, ...]
    questions: tuple[Question, ...]
    name: str = ""
    brand: dict[str, str] = field(default_factory=dict)  # primary_color, accent_color, style, font, heading_font
    region: dict[str, Any] = field(default_factory=dict)  # languages, currency, timezone
    advanced: dict[str, str] = field(default_factory=dict)  # backend, database

    def to_dict(self) -> dict[str, Any]:
        return {"prompt": self.prompt, "scope": self.scope.to_dict(), "features": [f.to_dict() for f in self.features],
                "questions": [q.to_dict() for q in self.questions], "name": self.name, "brand": dict(self.brand),
                "region": dict(self.region), "advanced": dict(self.advanced)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Brief":
        """A brief the person edited. Anything missing or unreadable falls back to the proposal for the prompt."""
        prompt = str(data.get("prompt") or "")
        proposed = propose_brief(prompt) if prompt else None
        scope = ProjectScope.from_dict(data["scope"]) if isinstance(data.get("scope"), dict) else (
            proposed.scope if proposed else ProjectScope("single", "", "", ""))
        by_id = {f.id: f for f in (proposed.features if proposed else ())}
        features = []
        for raw in data.get("features") or []:
            if isinstance(raw, dict) and raw.get("id") in by_id:
                base = by_id[raw["id"]]
                features.append(replace(base, included=base.from_prompt or bool(raw.get("included"))))
        features_t = tuple(features) or (proposed.features if proposed else ())
        q_by_id = {q.id: q for q in (proposed.questions if proposed else ())}
        questions = []
        for raw in data.get("questions") or []:
            if isinstance(raw, dict) and raw.get("id") in q_by_id:
                base = q_by_id[raw["id"]]
                answer = str(raw.get("answer") or base.answer)
                questions.append(replace(base, answer=answer if answer in {v for v, _ in base.options} else base.answer))
        questions_t = tuple(questions) or (proposed.questions if proposed else ())
        brand = {k: str(v) for k, v in (data.get("brand") or {}).items() if k in _BRAND_KEYS and isinstance(v, str)}
        region = dict(data.get("region") or {}) if isinstance(data.get("region"), dict) else {}
        advanced = {k: str(v) for k, v in (data.get("advanced") or {}).items() if k in ("backend", "database")}
        return cls(prompt, scope, features_t, questions_t, _clean_name(str(data.get("name") or "")),
                   brand or (proposed.brand if proposed else {}), region or (proposed.region if proposed else {}),
                   advanced or (proposed.advanced if proposed else {}))


_BRAND_KEYS = ("primary_color", "accent_color", "style", "font", "heading_font")
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _clean_name(name: str) -> str:
    return re.sub(r"[^\w &'.\-]", "", name, flags=re.UNICODE).strip()[:60]


# --- features ------------------------------------------------------------------------------------

#: (id, label, capability, words in the prompt that ask for it, sentence added to the plan)
_FEATURES: tuple[tuple[str, str, str, str, str], ...] = (
    ("payments", "Online payments", "money", r"\b(?:pay|pays|paying|paid|payment|payments|checkout|purchase|buy|sell|price)\b",
     "Customers pay online at checkout."),
    ("workflow", "Stages and approvals", "workflow", r"\b(?:approv\w*|reject\w*|status|stages?|pipeline|lifecycle|track (?:the |their |its )?(?:order|delivery|shipment|status|progress)\w*)",
     "Each request or order moves through clear stages, and only the right people can move it on."),
    ("privacy", "Private records", "ownership", r"\b(?:their own|only see|private|own (?:orders|bookings|records))\b",
     "Each person sees only their own records; admins see everything."),
    ("notifications", "Notifications", "notifications", r"\b(?:notif\w*|alert\w*|email\w*|let \w+ know)\b",
     "Notify people by email and in the app when anything that concerns them is created or changes."),
    ("reminders", "Reminders and schedules", "jobs", r"\b(?:remind\w*|schedul\w*|every (?:day|week|month)|overdue|recurring)\b",
     ""),
    ("live", "Live updates", "realtime", r"\b(?:live updates?|real[- ]?time|instantly|updated live|track (?:the |their |its )?(?:order|delivery|shipment|ride|driver|courier|location)\w*)",
     "Everyone sees changes live, without refreshing."),
    ("uploads", "Photo and file uploads", "", r"\b(?:upload\w*|photos?|images?|files?|documents?|attachments?|resumes?|receipts?)\b",
     "People can upload photos and documents."),
    ("reviews", "Reviews and ratings", "", r"\b(?:reviews?|ratings?|rate|stars?)\b",
     "Customers can leave a review with a 1-5 star rating."),
    ("messages", "Messages between people", "", r"\b(?:chat|messages?|messaging|inbox|conversations?)\b",
     "People can send messages to each other."),
    ("map", "Maps and locations", "", r"\b(?:maps?|locations?|nearby|address|gps|directions)\b",
     "Places have an address and a location shown on a map."),
    ("dashboard", "Dashboard and reports", "", r"\b(?:dashboard|analytics|reports?|statistics|stats|insights)\b",
     "Admins see a dashboard with the key figures and trends."),
    ("favourites", "Favourites", "", r"\b(?:favou?rites?|wishlists?|bookmarks?|save for later)\b",
     "People can save favourites to come back to."),
)

#: Kinds of product that need a building block even when the prompt does not say so.
_SUGGEST: tuple[tuple[str, tuple[str, ...]], ...] = (
    (r"\b(?:store|shop|marketplace|sell|order|delivery|ticket|course|subscription|rental|booking|book|invoice|donat)\w*",
     ("payments",)),
    (r"\b(?:book|booking|appointment|reservation|class|session|visit|event|rental|loan|due)\w*", ("reminders", "notifications")),
    (r"\b(?:delivery|courier|ride|driver|shipment|order|ticket|support|kitchen)\w*", ("live", "workflow", "notifications")),
    (r"\b(?:marketplace|seller|vendor|restaurant|salon|hotel|course|recipe|product|service|plumber|electrician)\w*",
     ("reviews",)),
    (r"\b(?:customers?|patients?|members?|clients?|students?|tenants?|users?)\b", ("privacy",)),
    (r"\b(?:delivery|courier|ride|driver|property|rental|hotel|restaurant|store|nearby)\w*", ("map",)),
    (r"\b(?:admin|manage|business|sales|orders?|inventory|stock|crm)\b", ("dashboard",)),
    (r"\b(?:habits?|routines?|medicines?|medication|water|workouts?|study|practice)\b", ("reminders",)),
)


def _transaction(prompt: str) -> str:
    text = prompt.lower()
    return next((w for w in _TRANSACTIONS if re.search(rf"\b{w}(?:e?s)?\b", text)), "")


def _features(prompt: str, scope: ProjectScope) -> tuple[Feature, ...]:
    suggested: dict[str, str] = {}
    for pattern, ids in _SUGGEST:
        match = re.search(pattern, prompt, re.I)
        if match:
            for fid in ids:
                suggested.setdefault(fid, match.group(0).lower())
    features = []
    for fid, label, capability, pattern, _sentence in _FEATURES:
        asked = re.search(pattern, prompt, re.I)
        if asked:
            features.append(Feature(fid, label, True, f"you mentioned \"{asked.group(0).lower()}\"", capability, True))
        elif fid in suggested:
            features.append(Feature(fid, label, True, f"a product with {suggested[fid]} usually needs it", capability))
        else:
            features.append(Feature(fid, label, False, "not needed by default; tick it to add it", capability))
    if scope.included(MOBILE):
        features.append(Feature("push", "Push notifications on phones", True,
                                 "the phone app tells people about what concerns them", "notifications"))
    return tuple(features)


# --- questions -----------------------------------------------------------------------------------

def _questions(prompt: str, features: tuple[Feature, ...], scope: ProjectScope) -> tuple[Question, ...]:
    on = {f.id for f in features if f.included}
    text = prompt.lower()
    questions = []
    thing = _transaction(prompt)
    if "payments" in on and not re.search(r"\b(?:cash|card|upi|stripe|razorpay|paypal)\b", text):
        questions.append(Question(
            "payment_method", "How do customers pay?",
            (("online", "Online, by card or UPI"), ("cash", "Cash, in person"), ("both", "Both")), "online",
            "online payments are recorded and reconciled automatically"))
    if re.search(r"\b(?:marketplace|seller|vendor|host|freelancer|merchant|restaurants?)\b", text) and "payments" in on \
            and not re.search(r"\d+\s*%", text):
        questions.append(Question(
            "commission", "What share of each sale does the platform keep?",
            (("0", "None"), ("5", "5%"), ("10", "10%"), ("15", "15%"), ("20", "20%")), "10",
            "a marketplace earns a commission on each sale; you can change it later"))
    if "reminders" in on and thing and not re.search(r"\d+\s*(?:hours?|days?|minutes?)\s+before", text):
        questions.append(Question(
            "reminder", f"When should people be reminded of {'an' if thing[:1] in 'aeiou' else 'a'} {thing}?",
            (("1 day", "A day before"), ("2 hours", "Two hours before"), ("none", "No reminders")), "1 day",
            f"a reminder the day before cuts missed {thing}s"))
    from .scope import _PERSONAL

    if not re.search(r"\b(?:invite|invited|sign ?up|register)\b", text) and not _PERSONAL.search(prompt):
        internal = not scope.included("site") and scope.shape != "ecosystem" and not re.search(r"\bcustomers?\b", text)
        questions.append(Question(
            "signup", "Who can create an account?",
            (("anyone", "Anyone can sign up"), ("invite", "Only people an admin invites")), "invite" if internal else "anyone",
            "an internal tool is for your team only" if internal else "customers sign themselves up"))
    if "workflow" in on and re.search(r"\b(?:request|application|submission|listing|expense|leave)\w*", text) \
            and not re.search(r"\bapprov\w*", text):
        questions.append(Question(
            "approval", "Does a new request need approval before it goes live?",
            (("yes", "Yes, an admin approves it"), ("no", "No, it is live at once")), "yes",
            "a quick check keeps mistakes and spam out"))
    return tuple(questions)


def _answer_sentences(brief: "Brief") -> list[str]:
    answers = {q.id: q.answer for q in brief.questions}
    thing = _transaction(brief.prompt)
    out = []
    if answers.get("payment_method") == "cash":
        out.append("Customers pay in cash in person; the app records each payment as paid or unpaid, with no online checkout.")
    elif answers.get("payment_method") == "both":
        out.append("Customers pay online at checkout, or in cash in person, which staff mark as paid.")
    if answers.get("commission") not in (None, "0"):
        out.append(f"The platform keeps a {answers['commission']}% commission on each sale.")
    if answers.get("reminder") not in (None, "none"):
        out.append(f"Send reminders {answers['reminder']} before each {thing}.")
    if answers.get("signup") == "invite":
        out.append("Only people an admin invites can sign in; there is no public sign-up.")
    if answers.get("approval") == "yes":
        out.append("A new request starts as pending, and an admin approves or rejects it.")
    return out


# --- brand, region, advanced ---------------------------------------------------------------------

_LANGUAGES = ("English", "Hindi", "Spanish", "French", "German", "Portuguese", "Arabic", "Bengali", "Tamil", "Telugu",
              "Marathi", "Gujarati", "Japanese", "Chinese", "Indonesian")
_LOCALE_CURRENCY = {"IN": "INR", "US": "USD", "GB": "GBP", "AE": "AED", "SG": "SGD", "AU": "AUD", "CA": "CAD",
                    "JP": "JPY", "ID": "IDR", "BR": "BRL", "MX": "MXN", "ZA": "ZAR", "NG": "NGN", "KE": "KES"}
_EURO = ("DE", "FR", "ES", "IT", "NL", "IE", "PT", "BE", "AT", "FI", "GR")
CURRENCIES = ("USD", "EUR", "GBP", "INR", "AED", "SGD", "AUD", "CAD", "JPY", "IDR", "BRL", "MXN", "ZAR", "NGN", "KES")


def _region(prompt: str, locale: str, timezone: str) -> dict[str, Any]:
    from .money_intent import _currency

    languages = [lang for lang in _LANGUAGES if re.search(rf"\b{lang}\b", prompt, re.I)] or ["English"]
    country = (locale.replace("_", "-").split("-")[1].upper() if "-" in locale or "_" in locale else "")
    currency = _currency(prompt)
    if currency == "USD" and not re.search(r"\$|\busd\b|dollar", prompt, re.I) and country:
        currency = "EUR" if country in _EURO else _LOCALE_CURRENCY.get(country, "USD")
    return {"languages": languages, "currency": currency, "timezone": timezone or "UTC"}


def _brand(prompt: str) -> dict[str, str]:
    from ..codegen.design_direction import choose_direction

    direction = choose_direction(prompt)
    return {"primary_color": direction.primary, "accent_color": direction.accent, "style": direction.style,
            "font": direction.body_font, "heading_font": direction.heading_font}


def _name_from_prompt(prompt: str) -> str:
    match = re.search(r"\b(?:called|named|brand(?:ed)? as|name it)\s+[\"“']?([A-Z][\w&'.\- ]{1,40}?)[\"”']?(?:[,.;:]|$|\s+(?:for|that|where|with|to)\b)",
                      prompt)
    return _clean_name(match.group(1)) if match else ""


# --- the brief -----------------------------------------------------------------------------------

def propose_brief(prompt: str, *, locale: str = "", timezone: str = "") -> Brief:
    """The brief for this prompt, every answer chosen. No model call."""
    from .backend_choice import backend_for_prompt

    scope = propose_scope(prompt)
    features = _features(prompt, scope)
    return Brief(
        prompt=prompt, scope=scope, features=features, questions=_questions(prompt, features, scope),
        name=_name_from_prompt(prompt), brand=_brand(prompt), region=_region(prompt, locale, timezone),
        advanced={"backend": backend_for_prompt(prompt).value, "database": "postgres"},
    )


def plan_prompt(brief: Brief) -> str:
    """The prompt the plan is made from: the person's words, then the brief's answers as facts."""
    sentences = []
    for fid, _label, _cap, _pattern, sentence in _FEATURES:
        feature = next((f for f in brief.features if f.id == fid), None)
        thing = _transaction(brief.prompt)
        if fid == "reminders" and not thing:
            sentence = "Send each person a daily reminder."
        # The readers attach a rule to a record, so the sentence names it when the prompt has one.
        if fid == "live" and thing:
            sentence = f"{thing.capitalize()}s update live for the people who follow them, without refreshing."
        if fid == "notifications" and thing:
            article = "an" if thing[0] in "aeiou" else "a"
            sentence = (f"Notify people by email when a new {thing} is placed. "
                        f"Notify people in the app when {article} {thing} is updated.")
        if feature and feature.included and not feature.from_prompt and sentence:
            sentences.append(sentence)
    sentences += _answer_sentences(brief)
    if brief.name:
        sentences.append(f"The product is called {brief.name}.")
    languages = [lang for lang in brief.region.get("languages") or [] if lang in _LANGUAGES]
    if languages and languages != ["English"]:
        sentences.append(f"The app is available in {', '.join(languages)}.")
    currency = str(brief.region.get("currency") or "")
    if currency in CURRENCIES and currency != "USD":
        sentences.append(f"Prices are in {currency}.")
    if not sentences:
        return brief.prompt
    return brief.prompt.rstrip() + "\n\nProject brief (confirmed by the owner):\n" + "\n".join(f"- {s}" for s in sentences)


def removed_capabilities(brief: Brief) -> set[str]:
    """Building blocks the person switched off: removed from the plan after planning."""
    kept = {f.capability for f in brief.features if f.included and f.capability}
    return {f.capability for f in brief.features if not f.included and f.capability and f.capability not in kept}


def apply_brief(ir: Any, brief: Brief, *, rename: bool = True) -> Any:
    """Name, brand, backend and switched-off building blocks, set on a plan."""
    from ..application_ir import BackendStrategy, BrandTokens
    from ..codegen.brand import mix

    changes: dict[str, Any] = {}
    if rename and brief.name:
        changes["name"] = brief.name
    primary = brief.brand.get("primary_color", "")
    if _HEX.match(primary):
        accent = brief.brand.get("accent_color", "")
        font = brief.brand.get("font", "")
        heading = brief.brand.get("heading_font", "") or font
        try:
            changes["brand"] = BrandTokens(
                primary_color=primary.lower(), dark_primary_color=mix(primary, "#ffffff", 0.18),
                font_family=font or BrandTokens().font_family,
                border_radius=ir.brand.border_radius if ir.brand != BrandTokens() else BrandTokens().border_radius,
                accent_color=accent.lower() if _HEX.match(accent) else "", heading_font=heading,
                style=brief.brand.get("style", ""), density=ir.brand.density)
        except Exception:  # noqa: BLE001 - an unusable font or colour keeps the chosen direction
            pass
    backend = brief.advanced.get("backend", "")
    if backend in {b.value for b in BackendStrategy}:
        changes["project_strategy"] = replace(ir.project_strategy, backend_strategy=BackendStrategy(backend))
    removed = removed_capabilities(brief)
    if removed:
        changes["capabilities"] = tuple(c for c in ir.capabilities if c.kind not in removed)
    return replace(ir, **changes) if changes else ir

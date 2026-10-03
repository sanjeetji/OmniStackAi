"""PC-127: what the platform will build for a prompt, shown before it builds and editable.

The founder's direction: the platform decides the scope from the prompt - one app, an app and its
admin, a few apps, or a whole ecosystem - and the person can change it before anything is built.

``propose_scope(prompt)`` answers without a model call (deterministic, instant, so it can be shown
the moment the prompt is sent):

* **an ecosystem** when the prompt names, or its domain implies, a second kind of person with their
  own job (R-555, R-580): one app per side over one API and database, each phone or web by who uses
  it (R-562);
* otherwise **one product**: its web app, the admin console to run it, and a phone app when the
  prompt asks for one or the product is something people use on the move;
* in both, a **public website** to introduce the product when it has customers to win.

Every app comes with the reason it is there, in words, and can be switched off or on; the build then
follows the edited scope exactly (``apply_to_ir`` for one product, ``apply_to_plan`` for an
ecosystem). A build without a scope keeps today's behaviour, and records the proposal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

WEB, ADMIN, MOBILE, SITE = "web", "admin", "mobile", "site"
SHAPES = {
    "single": "One app",
    "single_admin": "An app and its admin console",
    "few": "A few apps for one product",
    "ecosystem": "A complete ecosystem",
}

_MOBILE_WORDS = re.compile(
    r"\b(?:mobile|android|ios|iphone|ipad|phone app|smartphone|play store|app store|on (?:their|my|your|the) phones?|"
    r"expo|react native)\b", re.I)
#: Products people mostly use away from a desk: a phone app is suggested even when not asked for.
_ON_THE_MOVE = re.compile(
    r"\b(?:habit|fitness|workout|gym|run(?:ning)?|steps|diet|meal|recipe|delivery|ride|taxi|courier|driver|"
    r"travel|trip|expense|budget|wallet|attendance|check[- ]in|event ticket|tickets?|pet|journal|meditation|"
    r"social|chat|dating|community|church|parish|podcast)\w*", re.I)
_SITE_WORDS = re.compile(r"\b(?:marketing|landing page|website|web site|home ?page|seo|promote|brochure)\b", re.I)
#: Products with customers to win: a public website is suggested.
_HAS_CUSTOMERS = re.compile(
    r"\b(?:customers?|clients?|patients?|members?|guests?|buyers?|shoppers?|subscribers?|donors?|students?|"
    r"store|shop|marketplace|booking|book|reserve|order|sell|saas|subscription|clinic|salon|gym|hotel|"
    r"restaurant|school|course|agency|ngo|church|rental|event)\w*", re.I)
_PERSONAL = re.compile(r"\b(?:my own|personal|for myself|for me|my daily|track my|my habits|private)\b", re.I)
_NO_ADMIN = re.compile(r"\b(?:no admin|without an? admin|don'?t need an? admin)\b", re.I)
_ADMIN_ONLY = re.compile(r"\b(?:internal tool|back[- ]office|admin (?:panel|dashboard|console) only|only an? admin)\b", re.I)


@dataclass(frozen=True)
class ScopeApp:
    id: str
    name: str
    kind: str  # web | admin | mobile | site
    audience: str  # customer | operator | public
    included: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "kind": self.kind, "audience": self.audience,
                "included": self.included, "reason": self.reason}


@dataclass(frozen=True)
class ProjectScope:
    shape: str
    summary: str
    reason: str
    domain: str
    apps: tuple[ScopeApp, ...] = field(default_factory=tuple)
    #: Which planner the apps come from: "ecosystem" (one app per side) or "product" (one product).
    plan: str = "product"

    def included(self, kind: str | None = None) -> tuple[ScopeApp, ...]:
        return tuple(a for a in self.apps if a.included and (kind is None or a.kind == kind))

    def to_dict(self) -> dict[str, Any]:
        return {"shape": self.shape, "shape_label": SHAPES.get(self.shape, self.shape), "summary": self.summary,
                "reason": self.reason, "domain": self.domain, "plan": self.plan,
                "apps": [a.to_dict() for a in self.apps]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectScope":
        apps = []
        for raw in data.get("apps") or []:
            if not isinstance(raw, dict) or not raw.get("id"):
                continue
            kind = str(raw.get("kind") or WEB)
            apps.append(ScopeApp(str(raw["id"]), str(raw.get("name") or raw["id"]),
                                 kind if kind in (WEB, ADMIN, MOBILE, SITE) else WEB,
                                 str(raw.get("audience") or "customer"), bool(raw.get("included", True)),
                                 str(raw.get("reason") or "")))
        shape = str(data.get("shape") or "single")
        plan = "ecosystem" if data.get("plan") == "ecosystem" else "product"
        return cls(shape if shape in SHAPES else "single", str(data.get("summary") or ""), str(data.get("reason") or ""),
                   str(data.get("domain") or ""), tuple(apps), plan)


def _site(prompt: str, customer_app: bool = False) -> ScopeApp:
    asked = bool(_SITE_WORDS.search(prompt))
    customers = (customer_app or bool(_HAS_CUSTOMERS.search(prompt))) and not _PERSONAL.search(prompt)
    if asked:
        reason = "you asked for a website to introduce the product"
    elif customers:
        reason = "the product has customers to win, and a public website is how they find it"
    else:
        reason = "a personal or internal tool needs no public website; switch it on to introduce it to others"
    # Honest about today (PC-131 builds the separate site): until then the web app's home page is public.
    reason += "; for now your web app's public home page, with a separate marketing site to come"
    return ScopeApp(SITE, "Public website", SITE, "public", asked or customers, reason)


def _parties(apps: tuple[ScopeApp, ...]) -> int:
    """How many kinds of people have an app of their own (a phone companion is the same person)."""
    return len({re.sub(r"\s*\(mobile\)$", "", a.name) for a in apps if a.included and a.kind in (WEB, MOBILE)})


def _shape(apps: tuple[ScopeApp, ...], ecosystem: bool) -> str:
    # An ecosystem is two or more kinds of people, each with their own app. A web app and its admin
    # console is one product, however it was planned.
    if ecosystem and _parties(apps) > 1:
        return "ecosystem"
    kinds = {a.kind for a in apps if a.included and a.kind != SITE}
    if kinds <= {WEB} or kinds <= {ADMIN} or not kinds:
        return "single"
    if kinds == {WEB, ADMIN}:
        return "single_admin"
    return "few"


def _summary(apps: tuple[ScopeApp, ...]) -> str:
    names = [a.name for a in apps if a.included]
    if not names:
        return "Nothing selected yet."
    return "We'll build " + (names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]) + \
        ", over one API and one database."


def _single(prompt: str) -> ProjectScope:
    from .ecosystem_intent import detect_ecosystem_intent

    intent = detect_ecosystem_intent(prompt)
    admin_only = bool(_ADMIN_ONLY.search(prompt))
    asked_mobile = bool(_MOBILE_WORDS.search(prompt))
    on_the_move = bool(_ON_THE_MOVE.search(prompt))
    personal = bool(_PERSONAL.search(prompt))
    apps = [
        ScopeApp(WEB, "Web app", WEB, "customer", not admin_only,
                 "an internal tool is used from the admin console alone" if admin_only
                 else "the product itself, in any browser on any device"),
        ScopeApp(ADMIN, "Admin console", ADMIN, "operator", not _NO_ADMIN.search(prompt) and (admin_only or not personal),
                 "you asked for it" if admin_only else
                 "a personal app is managed from inside the app; switch it on to manage it separately" if personal else
                 "to manage the records, people and settings behind the product"),
        ScopeApp(MOBILE, "Phone app (Android and iOS)", MOBILE, "customer", asked_mobile or on_the_move,
                 "you asked for a phone app" if asked_mobile else
                 "people use this on the move, so it comes as a phone app too" if on_the_move else
                 "switch it on if people will use it from their phones"),
        _site(prompt),
    ]
    apps_t = tuple(apps)
    who = f" (only {', '.join(a for a in intent.actors if a != 'admin')})" if [a for a in intent.actors if a != "admin"] else ""
    reason = f"No second kind of person with a job of their own is named{who}, so this is one product."
    return ProjectScope(_shape(apps_t, False), _summary(apps_t), reason, "custom-application", apps_t)


def _ecosystem(prompt: str) -> ProjectScope | None:
    from ..application_ir import MobileProfile
    from ..codegen.ecosystem_assembler import surface_directory
    from .ecosystem import plan_ecosystem_from_prompt
    from .ecosystem_intent import detect_ecosystem_intent
    from .surface_form import form_for_surface

    intent = detect_ecosystem_intent(prompt)
    if not intent.build_ecosystem:
        return None
    plan = plan_ecosystem_from_prompt(prompt, "complete")
    if len(plan.apps) < 2:
        return None
    taken: set[str] = set()
    apps: list[ScopeApp] = []
    for app in plan.apps:
        directory = surface_directory(app.surface.kind, taken)
        taken.add(directory)
        mobile = app.ir.project_strategy.mobile_profile is MobileProfile.REACT_NATIVE
        kind = MOBILE if mobile else ADMIN if "admin" in app.surface.kind or "console" in app.surface.kind else WEB
        form = form_for_surface(kind=app.surface.kind, actor=app.surface.actor, name=app.surface.name, prompt=prompt)
        who = app.surface.actor or app.surface.audience
        reason = f"for {who.lower()}s: {app.surface.description[:1].lower() + app.surface.description[1:]}".rstrip(".")
        if mobile:
            reason += f" ({form.reason})"
        apps.append(ScopeApp(directory, app.ir.name, kind, app.surface.audience, True, reason))
    shape = _shape(tuple(apps), True)
    # Customers of a two-sided business are found through a public site; staff of an internal tool are not.
    apps.append(_site(prompt, customer_app=shape == "ecosystem" and any(a.audience == "customer" for a in apps)))
    apps_t = tuple(apps)
    reason = intent.reason if shape == "ecosystem" else "one kind of user and the staff who run it"
    return ProjectScope(shape, _summary(apps_t), reason[:1].upper() + reason[1:] + ".", plan.domain, apps_t, "ecosystem")


def propose_scope(prompt: str) -> ProjectScope:
    """The scope this prompt implies, every app with its reason. No model call."""
    return _ecosystem(prompt) or _single(prompt)


def with_choices(scope: ProjectScope, included: dict[str, bool]) -> ProjectScope:
    """The scope with apps switched on or off by id; the shape and summary follow."""
    apps = tuple(replace(a, included=bool(included.get(a.id, a.included))) for a in scope.apps)
    shape = _shape(apps, scope.shape == "ecosystem")
    return replace(scope, apps=apps, shape=shape, summary=_summary(apps))


def apply_to_ir(ir: Any, scope: ProjectScope) -> Any:
    """One product: its strategy follows the scope (web, admin console, phone app). Something is always built."""
    from ..application_ir import AdminStrategy, MobileProfile, WebStrategy

    web, admin, mobile = (bool(scope.included(k)) for k in (WEB, ADMIN, MOBILE))
    if not (web or admin or mobile):
        web = True  # an empty selection builds the web app rather than nothing
    strategy = replace(
        ir.project_strategy,
        web_strategy=WebStrategy.NEXTJS if web else WebStrategy.NONE,
        admin_strategy=AdminStrategy.NEXTJS if admin else AdminStrategy.NONE,
        mobile_profile=MobileProfile.REACT_NATIVE if mobile else MobileProfile.NONE,
    )
    return replace(ir, project_strategy=strategy)


def apply_to_plan(plan: Any, scope: ProjectScope) -> Any:
    """An ecosystem: only the apps the scope includes (at least one), in the planned order."""
    from ..codegen.ecosystem_assembler import surface_directory

    wanted = {a.id for a in scope.included() if a.kind != SITE}
    taken: set[str] = set()
    kept = []
    for app in plan.apps:
        directory = surface_directory(app.surface.kind, taken)
        taken.add(directory)
        if directory in wanted:
            kept.append(app)
    return replace(plan, apps=tuple(kept or plan.apps[:1]))

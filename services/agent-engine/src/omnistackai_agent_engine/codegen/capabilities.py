"""What this platform can actually build, and what it does when asked for something else (R-559).

Asking for a Flutter app, a native iOS/Android app or a React-Native-for-Web site used to return a
Next.js website and an admin panel, with no error and nothing anywhere saying why. Measured across
all four mobile profiles: only `react_native` emitted `apps/mobile`; `flutter`, `native` and `auto`
dropped it in silence. `nl_to_ir` meanwhile instructed the model to choose `flutter` when a mobile
app was requested, so the most likely path through the product was a guaranteed silent drop.

The information was not even missing. `_plan_assembly` computed a list of skip reasons and the only
thing that ever read it was the generated README — a file a user reads after wondering where their
app went, if they find it at all.

So this module replaces *dropping* with *substituting*: build the nearest thing we really do
support, keep the record of what was asked, and say why in one plain sentence that reaches the
person who asked.

**Support is derived, never declared.** `supported()` asks the adapter registry which targets have
an implementation behind them. Registering a Flutter or native adapter is therefore the only change
needed to make that stack real: the substitution stops, the sentence stops being produced, and no
intake prompt, planner or message needs editing. A hardcoded list of unsupported stacks would have
to be found and corrected by somebody who remembered it existed, which is the failure this module
is named after.

The reasons are written for the person waiting for their app, not for a log. They say what was
asked, what was built instead, and what that means for them — a React Native app still reaches both
stores, which is the part that decides whether the substitution is acceptable.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..application_ir import MobileProfile, ProjectStrategy, WebStrategy
from .adapter import AdapterRegistry, GenerationTarget


@dataclass(frozen=True, slots=True)
class Substitution:
    """One thing the user asked for, and the thing that was built instead.

    `asked` is kept because the IR keeps recording the request: substituting must never quietly
    rewrite what the person wanted. When the missing adapter eventually lands we can find every
    project that wanted it and offer to rebuild.
    """

    layer: str
    asked: str
    built: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        """JSON-safe, for the build result and the console."""
        return {"layer": self.layer, "asked": self.asked, "built": self.built, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class StackPlan:
    """The stack that will actually be built, and every substitution made to get there."""

    strategy: ProjectStrategy
    substitutions: tuple[Substitution, ...] = ()

    @property
    def notes(self) -> tuple[str, ...]:
        return tuple(s.reason for s in self.substitutions)


#: Which generation targets a strategy value needs before it can be called supported. A tuple means
#: every target in it must exist — native is not half-built if only Android has an adapter.
_MOBILE_TARGETS: dict[MobileProfile, tuple[GenerationTarget, ...]] = {
    MobileProfile.REACT_NATIVE: (GenerationTarget.REACT_NATIVE,),
    MobileProfile.FLUTTER: (GenerationTarget.FLUTTER,),
    MobileProfile.NATIVE: (GenerationTarget.NATIVE_ANDROID, GenerationTarget.NATIVE_IOS),
}

#
# An empty tuple means "no target renders this yet". It is not the same as a missing adapter: a
# React Native adapter exists and renders a *phone* app, so mapping `rn_web` to it would have
# reported react-native-web as supported while `_plan_assembly` laid out nothing at all — which is
# exactly what it did on the first draft of this file, producing a project with **zero apps**.
# Flutter-for-web would acquire the same trap the moment a Flutter *mobile* adapter is registered.
#
# The rule this encodes: a strategy counts as supported only when the assembler can really lay it
# out. Adding one later means a line here *and* a branch in `_plan_assembly`; the gate in
# `test_stack_substitution.py` fails if those two ever disagree again.
_WEB_TARGETS: dict[WebStrategy, tuple[GenerationTarget, ...]] = {
    WebStrategy.NEXTJS: (GenerationTarget.NEXTJS_WEB,),
    WebStrategy.FLUTTER_WEB: (),
    WebStrategy.RN_WEB: (),
    # A PWA is a Next.js app plus a manifest and a service worker. Since R-573 every generated
    # Next.js app has both, so a PWA request is simply honoured.
    WebStrategy.PWA: (GenerationTarget.NEXTJS_WEB,),
}

#: What we fall back to. One per layer, deliberately: a second-choice list is a way of quietly
#: making a worse decision when the first two are unavailable.
MOBILE_FALLBACK = MobileProfile.REACT_NATIVE
WEB_FALLBACK = WebStrategy.NEXTJS

#: How to name a stack to somebody who is not reading our enum.
_SPOKEN = {
    "flutter": "Flutter",
    "native": "native iOS and Android",
    "react_native": "React Native",
    "rn_web": "React Native for Web",
    "flutter_web": "Flutter for web",
    "nextjs": "Next.js",
    "pwa": "an installable PWA",
    "auto": "a mobile app",
}


def spoken(value: str) -> str:
    return _SPOKEN.get(value, value)


def supported(targets: tuple[GenerationTarget, ...], registry: AdapterRegistry) -> bool:
    """True when every target has a registered adapter behind it."""
    available = set(registry.targets())
    return bool(targets) and all(target in available for target in targets)


def supported_mobile_profiles(registry: AdapterRegistry) -> frozenset[MobileProfile]:
    """The mobile profiles this build of the platform can really produce."""
    return frozenset(
        profile for profile, targets in _MOBILE_TARGETS.items() if supported(targets, registry)
    )


def supported_web_strategies(registry: AdapterRegistry) -> frozenset[WebStrategy]:
    """The web strategies this build of the platform can really produce."""
    return frozenset(
        strategy for strategy, targets in _WEB_TARGETS.items() if supported(targets, registry)
    )


def _mobile_reason(asked: MobileProfile, built: MobileProfile) -> str:
    if asked is MobileProfile.AUTO:
        # Not a downgrade: the request left the choice to us, so this states the decision rather
        # than apologising for one.
        return (
            f"You asked for a mobile app without naming a framework, so it is built in "
            f"{spoken(built.value)} — one codebase that publishes to both the App Store and "
            f"Google Play."
        )
    if asked is MobileProfile.NATIVE:
        return (
            f"You asked for {spoken(asked.value)} apps. OmniStackAI does not generate Swift or "
            f"Kotlin yet, so this is built in {spoken(built.value)}, which still publishes to both "
            f"the App Store and Google Play from one codebase."
        )
    return (
        f"You asked for {spoken(asked.value)}. OmniStackAI does not generate "
        f"{spoken(asked.value)} yet, so this is built in {spoken(built.value)}, which still "
        f"publishes to both the App Store and Google Play from one codebase."
    )


def _web_reason(asked: WebStrategy, built: WebStrategy) -> str:
    if asked is WebStrategy.PWA:
        return (
            f"You asked for {spoken(asked.value)}. It is built in {spoken(built.value)}; the "
            f"offline manifest that makes it installable is not generated yet, so treat it as a "
            f"normal web app for now."
        )
    return (
        f"You asked for {spoken(asked.value)}. OmniStackAI does not generate "
        f"{spoken(asked.value)} yet, so the web app is built in {spoken(built.value)}."
    )


def resolve_stack(strategy: ProjectStrategy, registry: AdapterRegistry | None = None) -> StackPlan:
    """The stack that will actually be built, with a reason for anything that changed.

    Pure and deterministic. Both the assembler and the build result call *this* rather than each
    deciding for themselves — two places deciding the same thing is how the console came to report
    a build that did not match the repository on disk.
    """
    if registry is None:  # imported here: assembler imports this module at module scope
        from .assembler import default_registry

        registry = default_registry()

    substitutions: list[Substitution] = []
    resolved = strategy

    mobile = strategy.mobile_profile
    if mobile is not MobileProfile.NONE and mobile not in supported_mobile_profiles(registry):
        resolved = replace(resolved, mobile_profile=MOBILE_FALLBACK)
        substitutions.append(
            Substitution("mobile", mobile.value, MOBILE_FALLBACK.value, _mobile_reason(mobile, MOBILE_FALLBACK))
        )

    web = strategy.web_strategy
    if web is not WebStrategy.NONE and web not in supported_web_strategies(registry):
        resolved = replace(resolved, web_strategy=WEB_FALLBACK)
        substitutions.append(
            Substitution("web", web.value, WEB_FALLBACK.value, _web_reason(web, WEB_FALLBACK))
        )
    elif web is WebStrategy.PWA:
        # R-573: every Next.js app is installable now, so the request is met as asked; it builds
        # with the same adapter and needs no substitution note.
        resolved = replace(resolved, web_strategy=WEB_FALLBACK)

    return StackPlan(resolved, tuple(substitutions))


def offerable_mobile_profiles(registry: AdapterRegistry | None = None) -> tuple[str, ...]:
    """The mobile profiles intake may offer a model, newest-safe order.

    `nl_to_ir` used to name `flutter` in its instructions, which is how a silent drop began: the
    model did as it was told and the assembler discarded the result. The list of what may be
    offered has to come from the same place as the list of what exists.
    """
    if registry is None:
        from .assembler import default_registry

        registry = default_registry()
    profiles = supported_mobile_profiles(registry)
    return tuple(p.value for p in MobileProfile if p in profiles or p is MobileProfile.NONE)


# --- Stacks the plan has no field for (PC-003) --------------------------------------------------
#
# `resolve_stack` can only speak about what the IR records, and the IR has no value for React.js,
# Vue, Angular, Spring, Laravel, MySQL or MongoDB. A user who asked for one of those got Next.js or
# Python or PostgreSQL with nothing anywhere saying so — the silent substitution R-559 removed for
# Flutter, still alive one level up, because the model quietly writes the nearest value the schema
# allows. So the prompt itself is read, deterministically, for stacks it names that we do not build,
# and each becomes the same kind of note R-559 sends to the console.
#
# Patterns are deliberately narrow — a word-bounded name, not a guess at intent. A false "you asked
# for Vue" is worse than none, so ambiguous words ("go", "rails", "rust" on their own) are not here.

#: (layer, asked label, regex, how we describe what was built instead)
_NAMED_STACKS: tuple[tuple[str, str, str, str], ...] = (
    ("web", "React.js", r"\b(?:react(?:\.js|js)?|create[- ]react[- ]app|vite)\b(?!\s*native)",
     "Next.js is React with routing and server rendering built in, so the web app is React code "
     "you can keep extending"),
    ("web", "Vue", r"\b(?:vue(?:\.js|js)?|nuxt(?:\.js)?)\b", "the web app is built in Next.js (React)"),
    ("web", "Angular", r"\bangular(?:js)?\b", "the web app is built in Next.js (React)"),
    ("web", "Svelte", r"\bsvelte(?:kit)?\b", "the web app is built in Next.js (React)"),
    ("mobile", "Ionic / Capacitor", r"\b(?:ionic|capacitorjs|capacitor\s+(?:app|js))\b",
     "the app is built in React Native, which publishes to both the App Store and Google Play"),
    ("mobile", "Xamarin / .NET MAUI", r"(?:\bxamarin\b|\.net\s*maui\b)",
     "the app is built in React Native, which publishes to both the App Store and Google Play"),
    ("backend", "Java / Spring", r"\b(?:spring\s*boot|spring\s+framework|java)\b", ""),
    ("backend", "PHP / Laravel", r"\b(?:laravel|php|symfony)\b", ""),
    ("backend", "Ruby on Rails", r"\b(?:ruby\s+on\s+rails|ruby\s+(?:backend|api|server))\b", ""),
    ("backend", ".NET / C#", r"(?:\basp\.net\b|\.net\s*core\b|\bc#)", ""),
    ("backend", "Django / Flask", r"\b(?:django|flask)\b", ""),
    ("database", "MySQL", r"\b(?:mysql|mariadb)\b", ""),
    ("database", "MongoDB", r"\bmongo(?:db)?\b", ""),
    ("database", "SQLite", r"\bsqlite\b", ""),
    ("database", "Firebase / Supabase", r"\b(?:firebase|firestore|supabase)\b", ""),
)

_BACKEND_SPOKEN = {"python": "Python (FastAPI)", "go": "Go", "node": "Node.js"}


def _named_reason(layer: str, asked: str, built_text: str) -> str:
    if layer == "database" and asked == "MongoDB":
        return ("You asked for MongoDB. MongoDB support is planned; until it ships the data is "
                "stored in PostgreSQL, a production relational database.")
    if layer == "database" and asked.startswith("Firebase"):
        return (f"You asked for {asked}. Your app gets its own real API and a PostgreSQL database "
                f"instead, so the code and data are fully yours.")
    if asked == "React.js":
        return ("You asked for React.js. OmniStackAI builds web apps in Next.js, which is React with "
                "routing and server rendering built in, so your web app is React code you can keep "
                "extending.")
    if asked == "Django / Flask":
        return f"You asked for {asked}. The backend is built in {built_text}, the Python framework OmniStackAI generates."
    return f"You asked for {asked}. OmniStackAI does not generate {asked} yet, so {built_text}."


def named_stack_substitutions(prompt: str, strategy: ProjectStrategy) -> tuple[Substitution, ...]:
    """Stacks the prompt names that no IR field can hold, and what was built instead."""
    import re

    text = " ".join(str(prompt or "").lower().split())
    if not text:
        return ()
    # React Native is something we build; take it out before looking for React.js.
    text = re.sub(r"\breact[\s-]*native\b", " rn-mobile ", text)
    out: list[Substitution] = []
    for layer, asked, pattern, built_phrase in _NAMED_STACKS:
        if not re.search(pattern, text):
            continue
        if layer == "web":
            if strategy.web_strategy is WebStrategy.NONE and strategy.admin_strategy.value == "none":
                continue
            built, built_text = "nextjs", built_phrase
        elif layer == "mobile":
            if strategy.mobile_profile is MobileProfile.NONE:
                continue
            built, built_text = MOBILE_FALLBACK.value, built_phrase
        elif layer == "backend":
            built = strategy.backend_strategy.value
            built_text = _BACKEND_SPOKEN.get(built, built)
            built_phrase = f"the backend is built in {built_text}"
            built_text = built_text if asked == "Django / Flask" else built_phrase
        else:
            built, built_text = "postgres", "the data is stored in PostgreSQL"
        out.append(Substitution(layer, asked, built, _named_reason(layer, asked, built_text)))
    return tuple(out)

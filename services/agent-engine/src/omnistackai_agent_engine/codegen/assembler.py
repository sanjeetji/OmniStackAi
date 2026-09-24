"""Customer project assembler.

Turns one Application IR into a complete customer monorepo (Brief 6/34/35): it selects the framework
adapters implied by the IR project strategy, generates each target, places it under the monorepo
layout (`apps/web` for the Next.js web app, `services/api` for the Go/Python backend), and merges
everything into a single `GeneratedProject`. With the Git service, one IR becomes one customer-owned
repository. Pure and deterministic — nothing is installed, built, run, or written to disk here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace

from ..application_ir import ApplicationIR, BackendStrategy, BrandTokens, MobileProfile, WebStrategy
from ..model_gateway import ModelProvider
from .adapter import AdapterRegistry, GenerationTarget
from .brand_project import brand_files
from .backend_go import GoBackendAdapter
from .backend_python import PythonBackendAdapter
from .backend_node import NodeBackendAdapter
from .files import GeneratedFile, GeneratedProject
from .nextjs import NextjsAdminAdapter, NextjsWebAdapter, _slug
from .openapi import render_openapi_json
from .react_native import ReactNativeAdapter

# ---------------------------------------------------------------------------
# Brand token extraction (R-514) — deterministic, 0 model calls
# ---------------------------------------------------------------------------

_HEX_RE = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")

# R-544: colour *names*, because almost nobody types a hex code. "a red shop" and "green brand"
# were both read as "no colour mentioned", so the app came out the default blue either way.
# Values are the Tailwind 600 weight, which reads as the colour on white without glaring.
_COLOR_WORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(crimson|scarlet|red)\b", re.I), "#dc2626"),
    (re.compile(r"\b(orange|amber)\b", re.I), "#ea580c"),
    (re.compile(r"\b(yellow|gold(en)?)\b", re.I), "#ca8a04"),
    (re.compile(r"\b(lime)\b", re.I), "#65a30d"),
    (re.compile(r"\b(emerald|green)\b", re.I), "#16a34a"),
    (re.compile(r"\b(teal|aqua)\b", re.I), "#0d9488"),
    (re.compile(r"\b(cyan|sky)\b", re.I), "#0891b2"),
    (re.compile(r"\b(navy|indigo)\b", re.I), "#4338ca"),
    (re.compile(r"\b(violet|purple)\b", re.I), "#7c3aed"),
    (re.compile(r"\b(magenta|fuchsia)\b", re.I), "#c026d3"),
    (re.compile(r"\b(pink|rose)\b", re.I), "#e11d48"),
    (re.compile(r"\b(brown|chocolate)\b", re.I), "#92400e"),
    (re.compile(r"\b(slate|grey|gray|monochrome)\b", re.I), "#475569"),
    (re.compile(r"\b(black|midnight|dark)\b", re.I), "#1e293b"),
    # "blue" last: it is the default, so an explicit mention changes nothing but costs no harm,
    # and putting it first would let the word "blueprint" beat a real colour later in the sentence.
    (re.compile(r"\bblue\b", re.I), "#2563eb"),
]

# Common web-safe font family names we recognise by keyword
_KNOWN_FONTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\binter\b", re.I), "Inter"),
    (re.compile(r"\bgeist\b", re.I), "Geist"),
    (re.compile(r"\broboto\b", re.I), "Roboto"),
    (re.compile(r"\bpoppins\b", re.I), "Poppins"),
    (re.compile(r"\bmontserrat\b", re.I), "Montserrat"),
    (re.compile(r"\bopen.?sans\b", re.I), "Open Sans"),
    (re.compile(r"\blato\b", re.I), "Lato"),
    (re.compile(r"\bnunito\b", re.I), "Nunito"),
    (re.compile(r"\braboto\b", re.I), "Raleway"),
    (re.compile(r"\braleway\b", re.I), "Raleway"),
    (re.compile(r"\bplayfair\b", re.I), "Playfair Display"),
    (re.compile(r"\bmerriweather\b", re.I), "Merriweather"),
    (re.compile(r"\bsource.?sans\b", re.I), "Source Sans 3"),
    (re.compile(r"\bnoto.?sans\b", re.I), "Noto Sans"),
    (re.compile(r"\bubuntu\b", re.I), "Ubuntu"),
    (re.compile(r"\boxanium\b", re.I), "Oxanium"),
    (re.compile(r"\bspace.?grotesk\b", re.I), "Space Grotesk"),
    (re.compile(r"\bdm.?sans\b", re.I), "DM Sans"),
    (re.compile(r"\bfigtree\b", re.I), "Figtree"),
    (re.compile(r"\bmanrope\b", re.I), "Manrope"),
]

# Radius keyword → BrandTokens radius alias
_RADIUS_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsharp\b|\bno.?rounded?\b|\bsquare\b", re.I), "none"),
    (re.compile(r"\bslightly.?rounded?\b", re.I), "sm"),
    (re.compile(r"\bpill\b|\bfully.?rounded?\b|\bvery.?rounded?\b", re.I), "full"),
    (re.compile(r"\blarge.?rounded?\b|\bextra.?rounded?\b", re.I), "xl"),
    (re.compile(r"\bsoft\b|\brounded?\b", re.I), "lg"),
]


def extract_brand_tokens(user_prompt: str, *, ir_name: str = "") -> BrandTokens:
    """Deterministically extract brand cues from the user prompt (R-514).

    Searches for hex color mentions, known font-family keywords, and radius adjectives.
    Falls back silently to BrandTokens defaults when nothing is found.
    No model calls — zero credits.
    """
    # R-544: `BrandTokens.font_family` on the class returns the slot descriptor, not the default —
    # a slotted dataclass has no class-level values. This function was never called from anywhere
    # in src or the tests, so it raised on every invocation without anyone noticing. Read the
    # defaults off an instance.
    defaults = BrandTokens()
    text = f"{user_prompt} {ir_name}"

    # -- primary_color: an explicit hex wins, else a colour word ---------------
    hex_match = _HEX_RE.search(text)
    if hex_match is not None:
        primary_color = hex_match.group(0)
    else:
        primary_color = defaults.primary_color
        for pattern, value in _COLOR_WORDS:
            if pattern.search(text):
                primary_color = value
                break

    # -- font_family: first known font keyword --------------------------------
    font_family = defaults.font_family
    for pattern, font_name in _KNOWN_FONTS:
        if pattern.search(text):
            font_family = font_name
            break

    # -- border_radius: first radius keyword ----------------------------------
    border_radius = defaults.border_radius
    for pattern, alias in _RADIUS_MAP:
        if pattern.search(text):
            border_radius = alias
            break

    try:
        return BrandTokens(
            primary_color=primary_color,
            font_family=font_family,
            border_radius=border_radius,
        )
    except Exception:  # noqa: BLE001 — bad hex from prompt; use defaults
        return BrandTokens(font_family=font_family, border_radius=border_radius)


MONOREPO_TARGET = "customer-monorepo"

_BACKEND_TARGET = {
    BackendStrategy.GO: GenerationTarget.BACKEND_GO,
    BackendStrategy.PYTHON: GenerationTarget.BACKEND_PYTHON,
    BackendStrategy.NODE: GenerationTarget.BACKEND_NODE,
}


def default_registry() -> AdapterRegistry:
    """An AdapterRegistry with every currently-implemented framework adapter registered."""

    registry = AdapterRegistry()
    registry.register(NextjsWebAdapter())
    registry.register(NextjsAdminAdapter())
    registry.register(PythonBackendAdapter())
    registry.register(GoBackendAdapter())
    registry.register(ReactNativeAdapter())
    registry.register(NodeBackendAdapter())
    return registry


@dataclass(frozen=True, slots=True)
class AssembledApp:
    label: str
    directory: str
    target: str


def _prefixed(project: GeneratedProject, directory: str) -> list[GeneratedFile]:
    # R-549: carry *every* attribute across, not just the path and the executable bit. Dropping
    # `base64_encoded` here silently turned each generated icon into a text file the moment it moved
    # into apps/mobile/ — the adapter's own tests passed because they never went through assembly.
    return [
        GeneratedFile(
            f"{directory}/{f.path}",
            f.content,
            executable=f.executable,
            base64_encoded=f.base64_encoded,
        )
        for f in project.files()
    ]


def _root_readme(ir: ApplicationIR, apps: list[AssembledApp], skipped: list[str]) -> str:
    lines = [
        f"# {ir.name}",
        "",
        ir.description,
        "",
        "Customer monorepo generated by OmniStackAI from a single Application IR.",
        "",
        "## Apps",
        "",
    ]
    for app in apps:
        lines.append(f"- **{app.label}** — `{app.directory}/` (target `{app.target}`)")
    if ir.apis:
        lines.append("")
        lines.append("## API Contracts")
        lines.append("")
        lines.append("- **OpenAPI 3.1** — `contracts/openapi.json`")
    if skipped:
        lines.append("")
        lines.append("## Not yet assembled")
        lines.append("")
        for note in skipped:
            lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines) + "\n"


def _plan_assembly(ir: ApplicationIR) -> tuple[list[AssembledApp], list[str]]:
    """Decide which apps the IR assembles and where — the single source of the monorepo layout."""

    apps: list[AssembledApp] = []
    skipped: list[str] = []
    strategy = ir.project_strategy

    wants_admin = strategy.admin_strategy.value == "nextjs"

    if strategy.web_strategy is WebStrategy.NEXTJS:
        apps.append(AssembledApp("web (Next.js)", "apps/web", GenerationTarget.NEXTJS_WEB.value))
        # R-541: a public app and a staff console are two apps. Until now the console was recorded
        # as "not assembled yet" and silently dropped, so a prompt asking for a site *and* a panel
        # produced one app that was neither.
        if wants_admin:
            apps.append(AssembledApp("admin (Next.js)", "apps/admin", GenerationTarget.NEXTJS_ADMIN.value))
    elif strategy.web_strategy is WebStrategy.NONE and wants_admin:
        # Admin-only project: it is the only app, so it keeps the single-app layout.
        apps.append(AssembledApp("admin (Next.js)", "apps/web", GenerationTarget.NEXTJS_ADMIN.value))
    elif strategy.web_strategy is not WebStrategy.NONE:
        skipped.append(f"web_strategy {strategy.web_strategy.value!r} has no adapter yet")

    backend_target = _BACKEND_TARGET.get(strategy.backend_strategy)
    if backend_target is not None:
        apps.append(AssembledApp(f"backend ({strategy.backend_strategy.value})", "services/api", backend_target.value))
    else:
        skipped.append(f"backend_strategy {strategy.backend_strategy.value!r} has no adapter yet")

    if strategy.admin_strategy.value not in ("none", "nextjs"):
        skipped.append(f"admin_strategy {strategy.admin_strategy.value!r} has no adapter yet")
    if strategy.mobile_profile is MobileProfile.REACT_NATIVE:
        apps.append(AssembledApp("mobile (React Native)", "apps/mobile", GenerationTarget.REACT_NATIVE.value))
    elif strategy.mobile_profile.value != "none":
        skipped.append(f"mobile_profile {strategy.mobile_profile.value!r} is not assembled yet")
    return apps, skipped


def assembled_targets(ir: ApplicationIR, registry: AdapterRegistry | None = None) -> tuple[AssembledApp, ...]:
    """The apps an IR assembles (label, directory, target) — without generating any files.

    `registry` is accepted for signature symmetry with `assemble_project` (the layout does not depend
    on it); passing one lets a caller reason about a custom adapter set.
    """

    if not isinstance(ir, ApplicationIR):
        raise TypeError("assembled_targets expects an ApplicationIR")
    apps, _ = _plan_assembly(ir)
    return tuple(apps)


def assemble_project(
    ir: ApplicationIR,
    registry: AdapterRegistry | None = None,
    *,
    provider: ModelProvider | None = None,
    prompt: str = "",
    model_id: str | None = None,
    synthesize_screens: bool = False,
    ui_outcomes: list | None = None,
) -> GeneratedProject:
    """Assemble one customer monorepo GeneratedProject from an Application IR.

    ``synthesize_screens`` (R-465) opts the Next.js target into model-written screen pages as well as the
    overview page; it is a silent no-op without a ``provider``. ``ui_outcomes`` collects one JSON-safe
    ``UiSynthesisOutcome`` per synthesized file when supplied.
    """

    if not isinstance(ir, ApplicationIR):
        raise TypeError("assemble_project expects an ApplicationIR")
    registry = registry if registry is not None else default_registry()

    # R-544: `nl_to_ir` never asks the model for a brand, so a prompt-built IR always arrives with
    # the defaults and the user's "red shop" was lost before codegen ever saw it. Read the cues
    # from the prompt here — deterministically, no model call — and only when the IR has not set a
    # brand of its own, so an explicit brand always wins.
    if prompt and ir.brand == BrandTokens():
        derived = extract_brand_tokens(prompt, ir_name=ir.name)
        if derived != BrandTokens():
            ir = replace(ir, brand=derived)

    apps, skipped = _plan_assembly(ir)
    files: list[GeneratedFile] = []
    for app in apps:
        adapter = registry.get(app.target)
        if isinstance(adapter, NextjsWebAdapter) and provider is not None:
            project = adapter.generate(
                ir,
                provider=provider,
                prompt=prompt,
                model_id=model_id,
                synthesize_screens=synthesize_screens,
                ui_outcomes=ui_outcomes,
            )
        else:
            project = adapter.generate(ir)
        files += _prefixed(project, app.directory)

    if ir.apis:
        files.append(GeneratedFile("contracts/openapi.json", render_openapi_json(ir)))

    # R-548: one brand.json every surface derives from, at the monorepo root because it serves
    # the web app, the admin console and the mobile app alike.
    if any(app.target.startswith("nextjs") or app.target == "react-native" for app in apps):
        files.extend(brand_files(ir, _slug(ir.name)))

    files.append(GeneratedFile("README.md", _root_readme(ir, apps, skipped)))
    files.append(GeneratedFile(".gitignore", "node_modules/\n.next/\n.venv/\n__pycache__/\nbin/\n.env\n"))
    # R-549: `pnpm run brand` regenerates what cannot be derived while a page renders — the icons.
    if any(app.target.startswith("nextjs") or app.target == "react-native" for app in apps):
        files.append(
            GeneratedFile(
                "package.json",
                json.dumps(
                    {
                        "name": _slug(ir.name),
                        "private": True,
                        "scripts": {
                            "brand": "node brand/generate.mjs",
                        },
                    },
                    indent=2,
                )
                + "\n",
            )
        )

    return GeneratedProject(MONOREPO_TARGET, tuple(files))

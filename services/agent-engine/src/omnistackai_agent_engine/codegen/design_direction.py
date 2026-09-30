"""A design direction per project (PC-099).

Every project generated before this task shared one byte-identical stylesheet - same blue, same
system font, same corners - so every app looked like every other, whatever it was for. A direction
is chosen here for each project instead: a style, a primary and an accent colour, a body and a
heading font, a corner radius and a density.

It is deterministic: no model call, and the same prompt always gives the same direction (a person
who rebuilds must not get a different-looking app). Variety comes from the domain (a clinic is not
a food app), the style words in the prompt ("luxury", "playful", "minimal"), the product's archetype
when the prompt names no style, and the project's own name choosing between a domain's curated
palettes, so two food apps still differ. Anything the prompt states outright - a colour, a font,
"rounded" - wins over the choice.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace

from ..application_ir import ApplicationIR
from ..application_ir.ir import BrandTokens

#: Style words in a prompt, first match wins.
_STYLE_WORDS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(luxury|luxurious|premium|elegant|high.?end|sophisticated|boutique)\b", re.I), "elegant"),
    (re.compile(r"\b(playful|fun|kids?|children|cheerful|colou?rful|cute)\b", re.I), "playful"),
    (re.compile(r"\b(minimal(ist)?|clean|simple|zen)\b", re.I), "minimal"),
    (re.compile(r"\b(bold|vibrant|energetic|striking|cool|futuristic|neon)\b", re.I), "bold"),
    (re.compile(r"\b(corporate|professional|enterprise|business)\b", re.I), "professional"),
    (re.compile(r"\b(editorial|magazine|news|journal)\b", re.I), "editorial"),
    (re.compile(r"\b(calm|relaxing|soothing|wellness|mindful)\b", re.I), "calm"),
    (re.compile(r"\b(friendly|warm|welcoming|community)\b", re.I), "friendly"),
)

#: When the prompt names no style: what each kind of product usually wants.
_ARCHETYPE_STYLE = {
    "storefront": "vibrant",
    "booking": "calm",
    "tracker": "professional",
    "publication": "editorial",
    "directory": "friendly",
    "saas": "bold",
    "marketing": "bold",
    "admin_panel": "professional",
}

#: Domain -> curated (primary, accent) pairs. Each primary carries white text at WCAG AA.
_DOMAIN_PALETTES: tuple[tuple[re.Pattern[str], tuple[tuple[str, str], ...]], ...] = (
    (re.compile(r"\b(fashion|beauty|salon|spa|cosmetic|jewel|boutique|wedding)\b", re.I),
     (("#be185d", "#a16207"), ("#9d174d", "#0d9488"), ("#6b21a8", "#db2777"))),
    (re.compile(r"\b(food|restaurant|delivery|meal|recipe|kitchen|cafe|bakery|pizza|burger|grocery|dining)\b", re.I),
     (("#dc2626", "#f59e0b"), ("#ea580c", "#16a34a"), ("#be123c", "#f97316"))),
    (re.compile(r"\b(health|healthcare|clinic|medical|doctor|hospital|patient|pharmacy|dental)\b", re.I),
     (("#0f766e", "#0284c7"), ("#0e7490", "#10b981"), ("#1d4ed8", "#14b8a6"))),
    (re.compile(r"\b(finance|bank|fintech|invest|wallet|payment|accounting|insurance|loan|budget)\b", re.I),
     (("#1e3a8a", "#10b981"), ("#0f172a", "#22c55e"), ("#1d4ed8", "#f59e0b"))),
    (re.compile(r"\b(travel|trip|hotel|flight|tour|vacation|holiday|airbnb)\b", re.I),
     (("#0369a1", "#f97316"), ("#0e7490", "#eab308"), ("#1d4ed8", "#f43f5e"))),
    (re.compile(r"\b(school|course|learn|education|student|teacher|tutor|classroom|university)\b", re.I),
     (("#4338ca", "#f59e0b"), ("#6d28d9", "#10b981"), ("#1d4ed8", "#f97316"))),
    (re.compile(r"\b(fitness|gym|workout|sport|yoga|training|athlete)\b", re.I),
     (("#15803d", "#f97316"), ("#b91c1c", "#0ea5e9"), ("#111827", "#84cc16"))),
    (re.compile(r"\b(real.?estate|property|properties|rental|apartment|housing|realtor)\b", re.I),
     (("#047857", "#b45309"), ("#1e3a8a", "#16a34a"), ("#334155", "#d97706"))),
    (re.compile(r"\b(game|gaming|music|event|party|concert|stream)\b", re.I),
     (("#7c3aed", "#ec4899"), ("#4f46e5", "#06b6d4"), ("#c026d3", "#f59e0b"))),
    (re.compile(r"\b(logistics|fleet|shipping|courier|warehouse|inventory|supply)\b", re.I),
     (("#1e40af", "#f59e0b"), ("#0f766e", "#f97316"), ("#334155", "#0ea5e9"))),
    (re.compile(r"\b(crm|saas|dashboard|analytics|project|task|team|productivity)\b", re.I),
     (("#4f46e5", "#06b6d4"), ("#2563eb", "#8b5cf6"), ("#0f766e", "#6366f1"))),
    (re.compile(r"\b(blog|news|magazine|publication|article|writing)\b", re.I),
     (("#1f2937", "#dc2626"), ("#1e3a8a", "#d97706"), ("#7c2d12", "#0f766e"))),
)

#: Used when no domain matches: still varied, never the old default blue for everyone.
_GENERAL_PALETTES = (
    ("#4f46e5", "#f59e0b"), ("#0f766e", "#f97316"), ("#be123c", "#0ea5e9"),
    ("#7c3aed", "#10b981"), ("#1d4ed8", "#f43f5e"), ("#047857", "#8b5cf6"),
)

#: Style -> (body font, heading font, corner radius, density). Every font is on Google Fonts.
_STYLE_TYPE: dict[str, tuple[str, str, str, str]] = {
    "professional": ("Inter", "Inter", "lg", "compact"),
    "bold": ("Manrope", "Space Grotesk", "xl", "comfortable"),
    "playful": ("Nunito", "Poppins", "xl", "comfortable"),
    "elegant": ("DM Sans", "Playfair Display", "sm", "spacious"),
    "minimal": ("Figtree", "Figtree", "md", "spacious"),
    "editorial": ("Source Sans 3", "Merriweather", "sm", "comfortable"),
    "friendly": ("DM Sans", "Poppins", "xl", "comfortable"),
    "calm": ("Manrope", "Manrope", "xl", "spacious"),
    "vibrant": ("Poppins", "Poppins", "xl", "comfortable"),
}

#: Style -> a short brief for the page writer (what the direction means on a page).
STYLE_BRIEFS: dict[str, str] = {
    "professional": "Crisp and trustworthy: dense information, clear tables, restrained colour, strong alignment.",
    "bold": "Confident and modern: large headings, strong contrast, generous hero sections, vivid accent highlights.",
    "playful": "Warm and lively: rounded shapes, friendly copy, colourful accents, illustrations via emoji/icons.",
    "elegant": "Refined and premium: serif headings, lots of whitespace, subtle borders, understated colour, fine detail.",
    "minimal": "Quiet and focused: few colours, plenty of space, simple typography, no decoration without purpose.",
    "editorial": "Reading-first: serif headings, comfortable line length, clear hierarchy, images with captions.",
    "friendly": "Approachable: soft corners, warm tone, clear calls to action, helpful empty states.",
    "calm": "Soothing: soft colours, rounded cards, slow visual rhythm, gentle emphasis.",
    "vibrant": "Energetic and appetising: rich imagery areas, bold accent badges and offers, cards that invite clicks.",
}


@dataclass(frozen=True, slots=True)
class Direction:
    style: str
    primary: str
    accent: str
    body_font: str
    heading_font: str
    radius: str
    density: str


def _pick(options: tuple, seed: str):
    """A stable choice among options for this project (same name -> same choice)."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return options[digest[0] % len(options)]


def choose_direction(prompt: str, *, name: str = "", archetype: str = "") -> Direction:
    """The direction for a project, from its prompt, name and archetype. Deterministic."""
    text = f"{prompt} {name}"
    style = next((s for pattern, s in _STYLE_WORDS if pattern.search(text)), "")
    if not style:
        style = _ARCHETYPE_STYLE.get(archetype, "friendly")
    palettes = next((p for pattern, p in _DOMAIN_PALETTES if pattern.search(text)), _GENERAL_PALETTES)
    primary, accent = _pick(palettes, f"{name.lower().strip()}|{style}")
    body, heading, radius, density = _STYLE_TYPE[style]
    if style == "elegant":
        # Premium reads as deep and restrained: darken whatever the domain suggested.
        from .brand import mix

        primary = mix(primary, "#000000", 0.35)
    return Direction(style, primary, accent, body, heading, radius, density)


def with_design_direction(ir: ApplicationIR, prompt: str) -> ApplicationIR:
    """The IR with a design direction in its brand, unless it already has one.

    Explicit cues in the prompt (a colour, a font, a corner word) win over the chosen direction.
    A brand the plan already carries - set earlier, or by the person - is never replaced.
    """
    if ir.brand != BrandTokens():
        return ir
    from .archetype import detect_archetype
    from .assembler import extract_brand_tokens
    from .brand import mix

    explicit = extract_brand_tokens(prompt, ir_name=ir.name)
    defaults = BrandTokens()
    direction = choose_direction(prompt, name=ir.name, archetype=detect_archetype(ir, prompt).value)
    primary = explicit.primary_color if explicit.primary_color != defaults.primary_color else direction.primary
    body = explicit.font_family if explicit.font_family != defaults.font_family else direction.body_font
    heading = body if explicit.font_family != defaults.font_family else direction.heading_font
    radius = explicit.border_radius if explicit.border_radius != defaults.border_radius else direction.radius
    return replace(ir, brand=BrandTokens(
        primary_color=primary,
        dark_primary_color=mix(primary, "#ffffff", 0.18),
        font_family=body,
        border_radius=radius,
        accent_color=direction.accent,
        heading_font=heading,
        style=direction.style,
        density=direction.density,
    ))


def describe(brand: BrandTokens) -> str:
    """One line a person can read: what the app will look like."""
    if not brand.style:
        return ""
    fonts = brand.font_family if brand.heading_font in ("", brand.font_family) else f"{brand.heading_font} headings, {brand.font_family} text"
    return (f"{brand.style.capitalize()} design: {fonts}; primary {brand.primary_color}, accent "
            f"{brand.accent_color}; {brand.border_radius} corners; {brand.density} spacing.")


def page_brief(brand: BrandTokens) -> str:
    """The DESIGN DIRECTION block for the page writer (short: it is in every page request)."""
    if not brand.style:
        return ""
    return (
        "DESIGN DIRECTION (follow it; it is this product's own look):\n"
        f"- Style: {brand.style} - {STYLE_BRIEFS.get(brand.style, '')}\n"
        f"- Colours: primary = bg-primary/text-primary; accent (highlights, badges, offers) = "
        f"var(--color-accent). Fonts: headings use var(--font-heading), text var(--font-sans).\n"
        f"- Corners: {brand.border_radius}; spacing: {brand.density}.\n"
        "- The app's layout already shows the top navigation bar: do NOT add another top header, logo "
        "bar or site navigation in this page. Start with the page's own content.\n"
        "- Never invent numbers, ratings, reviews, testimonials or claims (no '4.9/5', '10k users', "
        "'100% certified'): show real data from the hooks, or leave it out."
    )


#: The default blues the component library was written in, and what each stands for.
_THEME_SWAPS: tuple[tuple[str, str], ...] = (
    ("#2563eb", "var(--color-primary)"),
    ("#3b82f6", "var(--color-primary)"),
    ("#1d4ed8", "var(--color-primary-hover)"),
    ("#1e40af", "var(--color-primary-focus)"),
    # PC-101: the library uses this indigo as a strong fill under white text; the accent is often a
    # light colour (cyan, amber) where white text fails contrast, the primary never is.
    ("#4f46e5", "var(--color-primary)"),
    ("#dbeafe", "var(--color-primary-subtle)"),
    ("#eff6ff", "var(--color-primary-subtle)"),
    ("#bfdbfe", "var(--color-primary-subtle)"),
)


def theme_component(source: str) -> str:
    """A component's hard-coded default blues, as the project's own colours (PC-099).

    Found live: 76 of the ~110 generated components were written in fixed blues, so a burgundy
    salon still had a blue navigation bar, blue checkboxes and blue tags. Values in style objects,
    strings and Tailwind arbitrary classes become the brand's CSS variables; a hex used directly as
    an SVG or HTML attribute (`fill="#2563eb"`) is left alone, since a variable does not work there.
    """
    if "getContext(" in source or 'type="color"' in source:
        # A canvas cannot read CSS variables, and a colour input needs a real hex: left as written.
        return source
    for hex_value, variable in _THEME_SWAPS:
        source = re.sub(rf"(?<!=\")(?<!=')(?i:{re.escape(hex_value)})\b", variable, source)
    return source

"""Turn a brand into the design tokens every generated component already reads (R-544).

The pipeline this closes was broken in three places at once. `nl_to_ir` never asked the model for a
brand, so a prompt-built IR always carried the defaults. `extract_brand_tokens` (R-514) existed but
was called from nowhere in `src` or the tests, so the cues sitting in the prompt were never read.
And `styles/tokens.css` was emitted as a static string that never consulted `ir.brand`, so even a
brand that *was* set changed nothing. The single place a requested colour surfaced was a swatch
inside `components/color-picker.tsx`. Ask for a red shop, get a blue one.

Tailwind's generated config already maps `primary` to `var(--color-primary)`, and every generated
component styles with `var(--color-*)`, so the token stylesheet is the one seam that makes the
whole app follow. Substituting there is enough; nothing else needs to know about brands.

Pure and offline: colour maths in plain Python, no dependency, no model call, and the same brand
always produces the same stylesheet.
"""

from __future__ import annotations

import re

from ..application_ir import BrandTokens

# --- colour maths -------------------------------------------------------------------------------

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


def _rgb(hex_color: str) -> tuple[int, int, int]:
    match = _HEX_RE.match(hex_color.strip())
    if match is None:
        raise ValueError(f"not a 6-digit hex colour: {hex_color!r}")
    value = match.group(1)
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c))) for c in rgb))


def mix(hex_color: str, toward: str, amount: float) -> str:
    """Blend `hex_color` toward `toward` by `amount` (0 keeps it, 1 reaches the target).

    Used instead of HSL lightness so the result stays on a straight line between two known colours:
    a shade produced this way can never wander to a different hue, which is what makes the derived
    hover and focus states recognisably the same brand.
    """
    r1, g1, b1 = _rgb(hex_color)
    r2, g2, b2 = _rgb(toward)
    amount = max(0.0, min(1.0, amount))
    return _hex((
        r1 + (r2 - r1) * amount,
        g1 + (g2 - g1) * amount,
        b1 + (b2 - b1) * amount,
    ))


def relative_luminance(hex_color: str) -> float:
    """WCAG relative luminance, used to decide whether text on the brand should be black or white."""
    channels = []
    for channel in _rgb(hex_color):
        c = channel / 255
        channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def readable_foreground(hex_color: str) -> str:
    """Black or white, whichever a user can actually read on this brand colour.

    A generated app with a yellow brand had white text on yellow buttons before this existed, which
    is a real accessibility failure and not a matter of taste.
    """
    return "#0f172a" if relative_luminance(hex_color) > 0.45 else "#ffffff"


# --- the palette a brand implies ----------------------------------------------------------------

_BLACK = "#000000"
_WHITE = "#ffffff"


def light_palette(primary: str) -> dict[str, str]:
    """The light-theme `--color-primary-*` values for one brand colour."""
    return {
        "--color-primary": primary,
        "--color-primary-hover": mix(primary, _BLACK, 0.14),
        "--color-primary-focus": mix(primary, _BLACK, 0.28),
        "--color-primary-subtle": mix(primary, _WHITE, 0.86),
        "--color-primary-foreground": readable_foreground(primary),
        # The focus ring is the brand too. Left out, a red app keeps focusing things in the
        # default blue, which reads as a bug to anyone who tabs through the page.
        "--color-border-focus": primary,
    }


def dark_palette(primary: str) -> dict[str, str]:
    """The dark-theme values. Derived from the same brand, so dark mode is not left behind.

    Lighter rather than darker: on a dark surface the brand has to come *forward*, which is why
    hover and focus lift toward white here and sink toward black in the light palette.
    """
    return {
        "--color-primary": mix(primary, _WHITE, 0.18),
        "--color-primary-hover": mix(primary, _WHITE, 0.34),
        "--color-primary-focus": mix(primary, _WHITE, 0.5),
        "--color-primary-subtle": "rgba({}, {}, {}, 0.15)".format(*_rgb(primary)),
        "--color-primary-foreground": readable_foreground(mix(primary, _WHITE, 0.18)),
        "--color-border-focus": mix(primary, _WHITE, 0.18),
    }


# --- applying it to the stylesheet ----------------------------------------------------------------

#: Radius alias -> the value `--radius-md` takes, since that is what components use by default.
_RADIUS_VALUES = {
    "none": "0",
    "sm": "0.25rem",
    "md": "0.375rem",
    "lg": "0.5rem",
    "xl": "0.75rem",
    "full": "9999px",
}


def _replace_var(css: str, name: str, value: str, *, start: int = 0, end: int | None = None) -> str:
    """Replace the first `--name: ...;` after `start` (and before `end`), leaving the rest alone."""
    stop = len(css) if end is None else end
    pattern = re.compile(rf"(--{re.escape(name.lstrip('-'))}\s*:\s*)([^;]+)(;)")
    match = pattern.search(css, start, stop)
    if match is None:
        return css
    return css[: match.start()] + f"{match.group(1)}{value}{match.group(3)}" + css[match.end():]


def apply_brand(css: str, brand: BrandTokens) -> str:
    """Return `css` with this brand's colours, font and corner radius substituted in.

    The light block is `:root {...}`; every later `--color-primary` belongs to a dark-theme block,
    so the light palette is applied inside the first block only and the dark palette to the rest.
    A default brand produces the stylesheet unchanged, byte for byte — which is what keeps every
    existing generated project and its recorded digests valid.
    """
    if brand == BrandTokens():
        return css

    root_start = css.find(":root {")
    root_end = css.find("\n}", root_start) if root_start != -1 else -1
    if root_start == -1 or root_end == -1:
        return css

    for name, value in light_palette(brand.primary_color).items():
        css = _replace_var(css, name, value, start=root_start, end=root_end)
        # The block can grow or shrink as values change length; re-find its end each time.
        root_end = css.find("\n}", root_start)

    # Font and radius live in the same root block.
    css = _replace_var(css, "--font-sans", brand.font_family, start=root_start, end=css.find("\n}", root_start))
    radius = _RADIUS_VALUES.get(brand.border_radius)
    if radius is not None:
        css = _replace_var(css, "--radius-md", radius, start=root_start, end=css.find("\n}", root_start))

    # Everything after the light block is dark-theme territory.
    after = css.find("\n}", root_start) + 2
    for name, value in dark_palette(brand.primary_color).items():
        # Dark blocks may repeat (media query and an explicit class); update each occurrence.
        cursor = after
        while True:
            css = _replace_var(css, name, value, start=cursor)
            probe = re.compile(rf"--{re.escape(name.lstrip('-'))}\s*:\s*{re.escape(value)}\s*;")
            found = probe.search(css, cursor)
            if found is None:
                break
            cursor = found.end()
            if not re.search(rf"--{re.escape(name.lstrip('-'))}\s*:", css[cursor:]):
                break
    return css

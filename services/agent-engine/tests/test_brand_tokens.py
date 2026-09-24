"""R-544: the brand a user asks for reaches the app they get.

The pipeline was broken in three independent places, which is why asking for a red shop produced
the same blue app as everything else:

1. `nl_to_ir` never asks the model for a brand, so a prompt-built IR always carried the defaults.
2. `extract_brand_tokens` (R-514) was called from nowhere in `src` or the tests — and, because
   `BrandTokens.font_family` on a slotted dataclass returns the slot descriptor rather than the
   default, it raised on every invocation. Dead code that also did not work.
3. `styles/tokens.css` was emitted as a static string that never consulted `ir.brand`.

Tailwind maps `primary` to `var(--color-primary)` and every generated component styles with
`var(--color-*)`, so the token stylesheet is the one seam that makes the whole app follow.
"""

import re
from unittest import TestCase

from omnistackai_agent_engine.application_ir import BrandTokens, example_ir
from omnistackai_agent_engine.codegen.assembler import assemble_project, extract_brand_tokens
from omnistackai_agent_engine.codegen.brand import (
    apply_brand,
    dark_palette,
    light_palette,
    mix,
    readable_foreground,
)
from omnistackai_agent_engine.codegen.nextjs import _DESIGN_TOKENS_CSS

_HEX = re.compile(r"^#[0-9a-f]{6}$")


def _var(css: str, name: str) -> str:
    match = re.search(rf"--{name}\s*:\s*([^;]+);", css)
    return match.group(1).strip() if match else ""


class TheExtractorWorksAtAll(TestCase):
    def test_it_does_not_raise(self) -> None:
        """It raised on every call before this: a slotted dataclass has no class-level defaults."""
        self.assertEqual(extract_brand_tokens(""), BrandTokens())

    def test_colour_names_are_read_not_only_hex(self) -> None:
        """Almost nobody types a hex code; "a red shop" was read as "no colour mentioned"."""
        self.assertEqual(extract_brand_tokens("a red shop for my bakery").primary_color, "#dc2626")
        self.assertEqual(extract_brand_tokens("a green booking site").primary_color, "#16a34a")
        self.assertEqual(extract_brand_tokens("a teal directory").primary_color, "#0d9488")

    def test_an_explicit_hex_wins_over_a_colour_word(self) -> None:
        self.assertEqual(extract_brand_tokens("a red shop, brand #00ff88").primary_color, "#00ff88")

    def test_font_and_corner_style_are_read_too(self) -> None:
        brand = extract_brand_tokens("a green booking site with rounded corners in Poppins")
        self.assertEqual(brand.font_family, "Poppins")
        self.assertEqual(brand.border_radius, "lg")

    def test_no_cue_means_no_brand(self) -> None:
        self.assertEqual(extract_brand_tokens("a plain internal tool"), BrandTokens())


class TheDerivedPaletteIsUsable(TestCase):
    def test_every_derived_shade_is_valid_hex(self) -> None:
        for value in light_palette("#dc2626").values():
            with self.subTest(value=value):
                self.assertRegex(value, _HEX)

    def test_the_shades_are_actually_different(self) -> None:
        palette = light_palette("#dc2626")
        shades = [palette["--color-primary"], palette["--color-primary-hover"], palette["--color-primary-focus"]]
        self.assertEqual(len(set(shades)), 3, shades)

    def test_dark_mode_lifts_toward_white_and_light_sinks_toward_black(self) -> None:
        """On a dark surface the brand has to come forward, not recede."""
        light, dark = light_palette("#2563eb"), dark_palette("#2563eb")
        self.assertLess(light["--color-primary-hover"], light["--color-primary"])  # darker hex sorts lower
        self.assertNotEqual(dark["--color-primary"], light["--color-primary"])

    def test_text_on_the_brand_stays_readable(self) -> None:
        """A yellow brand with white button text is an accessibility failure, not a taste call."""
        self.assertEqual(readable_foreground("#facc15"), "#0f172a")
        self.assertEqual(readable_foreground("#1e3a8a"), "#ffffff")

    def test_mixing_is_bounded_and_deterministic(self) -> None:
        self.assertEqual(mix("#000000", "#ffffff", 0.0), "#000000")
        self.assertEqual(mix("#000000", "#ffffff", 1.0), "#ffffff")
        self.assertEqual(mix("#123456", "#abcdef", 0.37), mix("#123456", "#abcdef", 0.37))


class TheStylesheetFollowsTheBrand(TestCase):
    def test_a_default_brand_changes_nothing(self) -> None:
        """Byte-for-byte, so every existing project and recorded digest stays valid."""
        self.assertEqual(apply_brand(_DESIGN_TOKENS_CSS, BrandTokens()), _DESIGN_TOKENS_CSS)

    def test_the_brand_colour_replaces_the_default(self) -> None:
        css = apply_brand(_DESIGN_TOKENS_CSS, BrandTokens(primary_color="#dc2626"))
        self.assertEqual(_var(css, "color-primary"), "#dc2626")

    def test_no_default_blue_survives_anywhere(self) -> None:
        """Including the dark theme and the focus ring — a red app must not focus things in blue."""
        css = apply_brand(_DESIGN_TOKENS_CSS, BrandTokens(primary_color="#dc2626"))
        self.assertNotIn("#2563eb", css)
        self.assertNotIn("#3b82f6", css)

    def test_the_font_and_radius_reach_the_css(self) -> None:
        css = apply_brand(_DESIGN_TOKENS_CSS, BrandTokens(font_family="Poppins", border_radius="full"))
        self.assertEqual(_var(css, "font-sans"), "Poppins")
        self.assertEqual(_var(css, "radius-md"), "9999px")


class TheWholePipelineIsConnected(TestCase):
    def _tokens_for(self, prompt: str) -> str:
        return assemble_project(example_ir("minimal-blog"), prompt=prompt).get("apps/web/styles/tokens.css").content

    def test_a_red_prompt_produces_a_red_app(self) -> None:
        self.assertEqual(_var(self._tokens_for("a red shop for my bakery"), "color-primary"), "#dc2626")

    def test_a_green_rounded_prompt_produces_a_green_rounded_app(self) -> None:
        css = self._tokens_for("a green booking site with rounded corners")
        self.assertEqual(_var(css, "color-primary"), "#16a34a")
        self.assertEqual(_var(css, "radius-md"), "0.5rem")

    def test_a_prompt_with_no_cue_keeps_the_default_palette(self) -> None:
        self.assertEqual(_var(self._tokens_for("a plain internal tool"), "color-primary"), "#2563eb")

    def test_the_admin_console_follows_the_same_brand(self) -> None:
        """Both apps are one product; a red shop with a blue back office would be a bug."""
        project = assemble_project(example_ir("minimal-blog"), prompt="a red shop")
        self.assertEqual(
            project.get("apps/web/styles/tokens.css").content,
            project.get("apps/admin/styles/tokens.css").content,
        )

    def test_an_explicit_ir_brand_is_not_overridden_by_the_prompt(self) -> None:
        import dataclasses

        ir = dataclasses.replace(example_ir("minimal-blog"), brand=BrandTokens(primary_color="#00ff88"))
        css = assemble_project(ir, prompt="a red shop").get("apps/web/styles/tokens.css").content
        self.assertEqual(_var(css, "color-primary"), "#00ff88")

    def test_the_output_is_byte_stable(self) -> None:
        self.assertEqual(self._tokens_for("a red shop"), self._tokens_for("a red shop"))

"""Unit tests for the Generated Design Tokens & CSS Custom Properties Theming Engine (R-324).

Validates:
- Standalone generation of styles/tokens.css
- Semantic color tokens for light and dark modes
- Scale tokens: spacing, typography, radii, shadows, z-indices, motion
- Accessibility and reduced motion support
- Integration into app/globals.css
- NextjsWebAdapter project generation and diff invariance
"""

import dataclasses
import unittest
from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_design_tokens,
    render_globals_css,
)


class ThemingTokensTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.adapter = NextjsWebAdapter()
        self.project = self.adapter.generate(self.ir)
        self.tokens_css = render_design_tokens()
        self.globals_css = render_globals_css()

    def test_render_design_tokens_returns_css(self) -> None:
        self.assertIsInstance(self.tokens_css, str)
        self.assertIn(":root {", self.tokens_css)
        self.assertIn("OmniStackAI Design Tokens", self.tokens_css)

    def test_tokens_contain_semantic_colors(self) -> None:
        for prop in (
            "--color-primary:",
            "--color-primary-hover:",
            "--color-primary-foreground:",
            "--color-secondary:",
            "--color-secondary-hover:",
            "--color-accent:",
            "--color-background:",
            "--color-surface:",
            "--color-surface-subtle:",
            "--color-surface-elevated:",
            "--color-text:",
            "--color-text-muted:",
            "--color-text-subtle:",
            "--color-text-inverse:",
            "--color-border:",
            "--color-border-subtle:",
            "--color-border-focus:",
            "--color-ring:",
        ):
            self.assertIn(prop, self.tokens_css, f"Missing semantic color token: {prop}")

    def test_tokens_contain_status_feedback_colors(self) -> None:
        for prop in (
            "--color-success:",
            "--color-success-bg:",
            "--color-success-border:",
            "--color-success-foreground:",
            "--color-warning:",
            "--color-warning-bg:",
            "--color-warning-border:",
            "--color-warning-foreground:",
            "--color-danger:",
            "--color-danger-bg:",
            "--color-danger-border:",
            "--color-danger-foreground:",
            "--color-info:",
            "--color-info-bg:",
            "--color-info-border:",
            "--color-info-foreground:",
        ):
            self.assertIn(prop, self.tokens_css, f"Missing status color token: {prop}")

    def test_tokens_contain_spacing_scale(self) -> None:
        for step in ("0", "1", "2", "3", "4", "5", "6", "8", "10", "12", "16", "20", "24"):
            self.assertIn(f"--space-{step}:", self.tokens_css, f"Missing spacing token: --space-{step}")

    def test_tokens_contain_typography_scale(self) -> None:
        for prop in (
            "--font-sans:",
            "--font-mono:",
            "--font-size-xs:",
            "--font-size-sm:",
            "--font-size-base:",
            "--font-size-lg:",
            "--font-size-xl:",
            "--font-size-2xl:",
            "--font-size-3xl:",
            "--font-weight-normal:",
            "--font-weight-medium:",
            "--font-weight-semibold:",
            "--font-weight-bold:",
            "--line-height-tight:",
            "--line-height-normal:",
            "--line-height-relaxed:",
        ):
            self.assertIn(prop, self.tokens_css, f"Missing typography token: {prop}")

    def test_tokens_contain_border_radii(self) -> None:
        for r in ("none", "sm", "md", "lg", "xl", "2xl", "full"):
            self.assertIn(f"--radius-{r}:", self.tokens_css, f"Missing radius token: --radius-{r}")

    def test_tokens_contain_elevation_shadows(self) -> None:
        for s in ("none", "sm", "md", "lg", "xl", "inner"):
            self.assertIn(f"--shadow-{s}:", self.tokens_css, f"Missing shadow token: --shadow-{s}")

    def test_tokens_contain_z_indices(self) -> None:
        for z in ("dropdown", "sticky", "modal", "popover", "toast", "tooltip"):
            self.assertIn(f"--z-{z}:", self.tokens_css, f"Missing z-index token: --z-{z}")

    def test_tokens_contain_transitions(self) -> None:
        for t in ("--transition-fast:", "--transition-normal:", "--transition-slow:"):
            self.assertIn(t, self.tokens_css, f"Missing transition token: {t}")

    def test_tokens_contain_dark_theme_mappings(self) -> None:
        self.assertIn('[data-theme="dark"]', self.tokens_css)
        self.assertIn(":root.dark", self.tokens_css)
        self.assertIn("@media (prefers-color-scheme: dark)", self.tokens_css)
        self.assertIn(":root:not([data-theme=\"light\"])", self.tokens_css)

    def test_tokens_contain_reduced_motion(self) -> None:
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.tokens_css)
        self.assertIn("--transition-duration-fast: 0ms;", self.tokens_css)
        self.assertIn("--transition-duration-normal: 0ms;", self.tokens_css)
        self.assertIn("--transition-duration-slow: 0ms;", self.tokens_css)

    def test_globals_css_imports_tokens_and_applies_base(self) -> None:
        self.assertIn('@import "../styles/tokens.css";', self.globals_css)
        self.assertIn("box-sizing: border-box;", self.globals_css)
        self.assertIn("font-family: var(--font-sans);", self.globals_css)
        self.assertIn("background-color: var(--color-background);", self.globals_css)
        self.assertIn("color: var(--color-text);", self.globals_css)

    def test_adapter_generates_tokens_and_globals_files(self) -> None:
        paths = set(self.project.paths())
        self.assertIn("styles/tokens.css", paths)
        self.assertIn("app/globals.css", paths)

        tokens_file = self.project.get("styles/tokens.css").content
        self.assertEqual(tokens_file, self.tokens_css)

        globals_file = self.project.get("app/globals.css").content
        self.assertEqual(globals_file, self.globals_css)

    def test_exports_in_codegen_package(self) -> None:
        self.assertTrue(callable(cg.render_design_tokens))
        self.assertTrue(callable(cg.render_globals_css))
        self.assertEqual(cg.render_design_tokens(), self.tokens_css)
        self.assertEqual(cg.render_globals_css(), self.globals_css)

    def test_tokens_and_globals_diff_invariance(self) -> None:
        ir1 = self.ir
        ir2 = dataclasses.replace(ir1, description="Completely altered description for testing invariance")
        proj1 = self.adapter.generate(ir1)
        proj2 = self.adapter.generate(ir2)

        self.assertEqual(proj1.get("styles/tokens.css").content, proj2.get("styles/tokens.css").content)
        self.assertEqual(proj1.get("app/globals.css").content, proj2.get("app/globals.css").content)


if __name__ == "__main__":
    unittest.main()

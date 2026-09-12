"""Tests for the Accessible Futuristic Slug / URL Input Suite (components/slug-input.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_slug_input_component,
)


class TestSlugInputComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Slug / URL Input Suite (R-411)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_slug_input_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/slug-input.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/slug-input.tsx")
        f2 = proj2.get("components/slug-input.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_slug_input_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<SlugInputHandle, SlugInputProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("getValue:", "getFullUrl:", "setValue:", "slugify:", "clear:", "focus:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type SlugInputVariant",
            "export type SlugInputSize",
            "export interface SlugInputHandle",
            "export interface SlugInputProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const SlugInput =",
            "export const Slugify =",
            "export const UrlSlugInput =",
            "export const PermalinkInput =",
            "export default SlugInputComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "SlugInputComponent.displayName = 'SlugInput'",
            "Slugify.displayName = 'Slugify'",
            "UrlSlugInput.displayName = 'UrlSlugInput'",
            "PermalinkInput.displayName = 'PermalinkInput'",
        ):
            self.assertIn(line, self.source)

    def test_variants_present(self) -> None:
        self.assertIn("'default' | 'card' | 'glass' | 'neon'", self.source)
        for key in ("default: {", "card: {", "glass: {", "neon: {"):
            self.assertIn(key, self.source)

    def test_sizes_present(self) -> None:
        self.assertIn("'sm' | 'md' | 'lg'", self.source)
        for key in ("sm: {", "md: {", "lg: {"):
            self.assertIn(key, self.source)

    def test_slugify_logic(self) -> None:
        for token in ("slugify", "toLowerCase", "normalize"):
            self.assertIn(token, self.source)

    def test_diacritics_normalize(self) -> None:
        self.assertIn("NFKD", self.source)
        self.assertIn("0x300", self.source)
        self.assertIn("charCodeAt", self.source)

    def test_source_sync(self) -> None:
        self.assertIn("source", self.source)
        self.assertIn("autoSyncFromSource", self.source)

    def test_prefix_and_full_url(self) -> None:
        self.assertIn("prefix", self.source)

    def test_copy_to_clipboard(self) -> None:
        self.assertIn("navigator.clipboard", self.source)
        self.assertIn("writeText", self.source)

    def test_aria(self) -> None:
        self.assertIn("aria-label", self.source)
        self.assertIn("aria-live", self.source)

    def test_callbacks_and_controlled(self) -> None:
        for token in ("onChange", "value", "defaultValue"):
            self.assertIn(token, self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_slug_input_component"))
        self.assertTrue(callable(cg.render_slug_input_component))
        self.assertIn("render_slug_input_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()

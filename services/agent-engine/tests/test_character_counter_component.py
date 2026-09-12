"""Tests for the Accessible Futuristic Character & Word Counter Textarea Suite (components/character-counter.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_character_counter_component,
)


class TestCharacterCounterComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Character & Word Counter Textarea Suite (R-412)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_character_counter_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/character-counter.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/character-counter.tsx")
        f2 = proj2.get("components/character-counter.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_character_counter_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<CharacterCounterHandle, CharacterCounterProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("getValue:", "setValue:", "getStats:", "clear:", "focus:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type CharacterCounterVariant",
            "export type CharacterCounterSize",
            "export interface CharacterCounterStats",
            "export interface CharacterCounterHandle",
            "export interface CharacterCounterProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const CharacterCounter =",
            "export const CharCounter =",
            "export const WordCounter =",
            "export const TextCounter =",
            "export default CharacterCounterComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "CharacterCounterComponent.displayName = 'CharacterCounter'",
            "CharCounter.displayName = 'CharCounter'",
            "WordCounter.displayName = 'WordCounter'",
            "TextCounter.displayName = 'TextCounter'",
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

    def test_counting_logic(self) -> None:
        for token in ("characters", "words", "Array.from", "split"):
            self.assertIn(token, self.source)

    def test_limits(self) -> None:
        for token in ("maxLength", "remaining", "overLimit"):
            self.assertIn(token, self.source)

    def test_word_counting(self) -> None:
        self.assertIn("countWords", self.source)
        self.assertIn("trim", self.source)

    def test_progress_and_threshold(self) -> None:
        self.assertIn("showProgress", self.source)
        self.assertIn("warnThreshold", self.source)

    def test_aria_semantics(self) -> None:
        self.assertIn('role="status"', self.source)
        self.assertIn("aria-live", self.source)
        self.assertIn("aria-describedby", self.source)

    def test_hard_limit(self) -> None:
        self.assertIn("hardLimit", self.source)

    def test_callbacks_and_controlled(self) -> None:
        for token in ("onChange", "value", "defaultValue"):
            self.assertIn(token, self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_character_counter_component"))
        self.assertTrue(callable(cg.render_character_counter_component))
        self.assertIn("render_character_counter_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()

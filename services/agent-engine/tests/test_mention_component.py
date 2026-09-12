"""Tests for the Accessible Futuristic Mention / @-Autocomplete Textarea Suite (components/mention.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_mention_component,
)


class TestMentionComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Mention / @-Autocomplete Textarea Suite (R-405)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_mention_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/mention.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/mention.tsx")
        f2 = proj2.get("components/mention.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_mention_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<MentionHandle, MentionProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("getValue:", "setValue:", "getMentions:", "focus:", "clear:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type MentionVariant",
            "export type MentionSize",
            "export interface MentionItem",
            "export interface MentionHandle",
            "export interface MentionProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const Mention =",
            "export const MentionInput =",
            "export const MentionTextarea =",
            "export const AtMention =",
            "export default MentionComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "MentionComponent.displayName = 'Mention'",
            "MentionInput.displayName = 'MentionInput'",
            "MentionTextarea.displayName = 'MentionTextarea'",
            "AtMention.displayName = 'AtMention'",
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

    def test_trigger_detection(self) -> None:
        self.assertIn("detectTrigger", self.source)
        self.assertIn("trigger", self.source)
        self.assertIn("selectionStart", self.source)

    def test_suggestion_listbox(self) -> None:
        self.assertIn('role="listbox"', self.source)
        self.assertIn('role="option"', self.source)
        self.assertIn("maxSuggestions", self.source)

    def test_keyboard_navigation(self) -> None:
        for token in ("ArrowDown", "ArrowUp", "Enter", "Escape", "activeIndex"):
            self.assertIn(token, self.source)

    def test_combobox_aria(self) -> None:
        for token in ("aria-expanded", "aria-activedescendant", "aria-autocomplete", "aria-controls"):
            self.assertIn(token, self.source)

    def test_callbacks(self) -> None:
        self.assertIn("onChange", self.source)
        self.assertIn("onMention", self.source)

    def test_controlled_and_uncontrolled(self) -> None:
        self.assertIn("value", self.source)
        self.assertIn("defaultValue", self.source)

    def test_mentions_extraction(self) -> None:
        self.assertIn("mentions", self.source)
        self.assertIn("items", self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_mention_component"))
        self.assertTrue(callable(cg.render_mention_component))
        self.assertIn("render_mention_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()

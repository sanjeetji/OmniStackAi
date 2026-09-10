"""Tests for Task R-339: Generated Accessible Futuristic Reusable Tag & Chip Input Tokenizer Component.

Verifies that NextjsWebAdapter emits an accessible, futuristic, reusable TagInput component suite
(apps/web/components/tag-input.tsx) supporting:
- TagItem and TagValue interfaces (id, label, color, disabled, icon)
- TagInputVariant ("default" | "glass" | "neon" | "bordered") and TagInputSize ("sm" | "md" | "lg")
- Delimiter parsing on Enter, Comma, Tab
- Backspace deletion and ArrowLeft/ArrowRight chip traversal
- Autocomplete suggestions dropdown with keyboard selection (ArrowDown/Up, Enter, Escape)
- Validation: maxTags limits, duplicate rejection, and custom tag validation
- Clear-all button and prefix icon slot
- WAI-ARIA Combobox / Listbox 1.2 semantics: role="combobox", role="listbox", role="option", aria-expanded, aria-activedescendant
- Inline SVG icons: TagIcon, XIcon, ClearIcon
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_tag_input_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TagInputComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the TagInput component."""

    def setUp(self) -> None:
        self.code = render_tag_input_component()
        self.ir = example_ir("rideshare-favourites")

    def test_tag_input_component_is_client_component(self) -> None:
        """The TagInput component must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "TagInput must have 'use client' as the first statement.",
        )

    def test_tag_input_component_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export interface TagItem", self.code)
        self.assertIn("export type TagValue", self.code)
        self.assertIn("export type TagInputVariant", self.code)
        self.assertIn('"default"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn("export type TagInputSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export interface TagInputProps", self.code)

    def test_tag_input_component_exports_component(self) -> None:
        """Verify TagInput component and default export."""
        self.assertIn("export function TagInput", self.code)
        self.assertIn("export default TagInput;", self.code)

    def test_tag_input_component_uses_wai_aria_combobox_semantics(self) -> None:
        """Verify WAI-ARIA Combobox / Listbox 1.2 roles and container attributes."""
        self.assertIn('role="combobox"', self.code)
        self.assertIn('role="listbox"', self.code)
        self.assertIn('role="option"', self.code)
        self.assertIn('aria-autocomplete="list"', self.code)
        self.assertIn("aria-expanded=", self.code)
        self.assertIn("aria-activedescendant=", self.code)

    def test_tag_input_component_handles_keyboard_navigation(self) -> None:
        """Verify complete keyboard navigation handling for chips and dropdown."""
        self.assertIn('e.key === "Backspace"', self.code)
        self.assertIn('e.key === "ArrowLeft"', self.code)
        self.assertIn('e.key === "ArrowRight"', self.code)
        self.assertIn('e.key === "ArrowDown"', self.code)
        self.assertIn('e.key === "ArrowUp"', self.code)
        self.assertIn('e.key === "Escape"', self.code)

    def test_tag_input_component_supports_delimiters(self) -> None:
        """Verify delimiter support for splitting and adding tags."""
        self.assertIn("delimiters", self.code)
        self.assertIn('"Enter"', self.code)
        self.assertIn('","', self.code)

    def test_tag_input_component_supports_autocomplete_suggestions(self) -> None:
        """Verify suggestions dropdown and search filtering."""
        self.assertIn("suggestions", self.code)
        self.assertIn("filteredSuggestions", self.code)
        self.assertIn("highlightedIndex", self.code)
        self.assertIn("tag-input-suggestions", self.code)

    def test_tag_input_component_supports_max_tags_and_validation(self) -> None:
        """Verify max tags limits and duplicate prevention."""
        self.assertIn("maxTags", self.code)
        self.assertIn("allowDuplicates", self.code)
        self.assertIn("validateTag", self.code)
        self.assertIn("isDuplicateFeedback", self.code)

    def test_tag_input_component_supports_variants_and_sizes(self) -> None:
        """Verify visual variant styling and size dimension mapping."""
        self.assertIn("neon", self.code)
        self.assertIn("glass", self.code)
        self.assertIn("bordered", self.code)
        self.assertIn("sizeConfig", self.code)

    def test_tag_input_component_includes_built_in_svg_icons(self) -> None:
        """Verify inline vector icons for tag, close, and clear."""
        self.assertIn("TagIcon", self.code)
        self.assertIn("XIcon", self.code)
        self.assertIn("ClearIcon", self.code)

    def test_tag_input_component_supports_clearable(self) -> None:
        """Verify clear-all action and icon trigger."""
        self.assertIn("clearable", self.code)
        self.assertIn("clearAll", self.code)

    def test_adapter_emits_tag_input_file(self) -> None:
        """NextjsWebAdapter emits components/tag-input.tsx in generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/tag-input.tsx")
        self.assertIsNotNone(f, "components/tag-input.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_tag_input_diff_invariant(self) -> None:
        """TagInput output is 100% diff-invariant across ir.description changes."""
        ir_b = dataclasses.replace(self.ir, description="Completely different description")
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/tag-input.tsx")
        f_b = adapter.generate(ir_b).get("components/tag-input.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(f_a.content, f_b.content)

    def test_tag_input_zero_external_dependencies(self) -> None:
        """TagInput uses only React; zero external package imports."""
        modules = re.findall(r'from\s+"([^"]+)"', self.code)
        for mod in modules:
            self.assertEqual(mod, "react", f"Unexpected external import: {mod}")

    def test_package_codegen_exports_render_tag_input_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_tag_input_component."""
        self.assertTrue(callable(cg.render_tag_input_component))
        self.assertIn("render_tag_input_component", cg.__all__)
        self.assertEqual(cg.render_tag_input_component(), self.code)


if __name__ == "__main__":
    unittest.main()

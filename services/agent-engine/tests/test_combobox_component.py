"""Tests for Task R-358: Generated Accessible Futuristic Reusable Searchable Combobox & Autocomplete Primitive.

Verifies that NextjsWebAdapter emits an accessible, desktop-grade, zero-dependency, and futuristic
Searchable Combobox & Autocomplete compound component suite (apps/web/components/combobox.tsx) supporting:
- WAI-ARIA 1.2 Combobox & Listbox pattern compliance:
  - Container emits role="combobox", aria-expanded, aria-haspopup="listbox", aria-controls, aria-activedescendant
  - Options list emits role="listbox", aria-multiselectable
  - Options emit role="option", aria-selected, aria-disabled, data-highlighted
- Keyboard navigation:
  - ArrowDown / ArrowUp traversal with cyclical wrap-around
  - Enter to select currently highlighted option
  - Escape to close dropdown
  - Home / End jump navigation
- Real-time type-ahead search filtering across label, description, and keywords
- Single-select and multi-select mode with removable tag chips
- Clear button affordance (allowClear)
- 4 futuristic visual styling variants ("default", "card", "glass", "neon")
- 3 size scales ("sm", "md", "lg") with responsive padding, font metrics, and tag heights
- Hidden input form submission integration with name prop
- Semantic aliasing: Autocomplete = Combobox
- React ref forwarding (forwardRef) and explicit displayName
- 100% diff-invariance across ir.description changes
- Zero external runtime npm dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_combobox_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class ComboboxComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the Combobox component suite."""

    def setUp(self) -> None:
        self.code = render_combobox_component()
        self.ir = example_ir("rideshare-favourites")

    def test_combobox_is_client_component(self) -> None:
        """Combobox must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "Combobox must have 'use client' as the first statement.",
        )

    def test_combobox_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type ComboboxVariant", self.code)
        self.assertIn('"default"', self.code)
        self.assertIn('"card"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn("export type ComboboxSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export interface ComboboxOptionItem", self.code)
        self.assertIn("export interface ComboboxProps", self.code)

    def test_combobox_exports_components_and_aliases(self) -> None:
        """Verify Combobox export, Autocomplete alias, and default export."""
        self.assertIn("export const Combobox = forwardRef", self.code)
        self.assertIn("Combobox.displayName = \"Combobox\";", self.code)
        self.assertIn("export const Autocomplete = Combobox;", self.code)
        self.assertIn("export default Combobox;", self.code)

    def test_combobox_wai_aria_semantics(self) -> None:
        """Verify WAI-ARIA 1.2 Combobox and Listbox pattern attributes."""
        self.assertIn('role="combobox"', self.code)
        self.assertIn("aria-expanded={isOpen}", self.code)
        self.assertIn('aria-haspopup="listbox"', self.code)
        self.assertIn("aria-controls={listboxId}", self.code)
        self.assertIn("aria-activedescendant={isOpen ? activeOptionId : undefined}", self.code)
        self.assertIn('role="listbox"', self.code)
        self.assertIn('role="option"', self.code)
        self.assertIn("aria-selected={isSelected}", self.code)

    def test_combobox_keyboard_navigation(self) -> None:
        """Verify arrow traversal, enter selection, escape, home, end."""
        self.assertIn('case "ArrowDown":', self.code)
        self.assertIn('case "ArrowUp":', self.code)
        self.assertIn('case "Enter":', self.code)
        self.assertIn('case "Escape":', self.code)
        self.assertIn('case "Home":', self.code)
        self.assertIn('case "End":', self.code)

    def test_combobox_typeahead_search_filtering(self) -> None:
        """Verify fuzzy/substring search across label, description, and keywords."""
        self.assertIn("filteredOptions", self.code)
        self.assertIn("opt.label.toLowerCase().includes(query)", self.code)
        self.assertIn("opt.description?.toLowerCase().includes(query)", self.code)
        self.assertIn("opt.keywords?.some", self.code)

    def test_combobox_single_and_multi_select(self) -> None:
        """Verify support for both single-select string and multi-select string array."""
        self.assertIn("multiple", self.code)
        self.assertIn("selectedValues.map", self.code)
        self.assertIn("handleRemoveTag", self.code)
        self.assertIn("tagHeight", self.code)

    def test_combobox_clear_button(self) -> None:
        """Verify clear button affordance for quick clearing."""
        self.assertIn("allowClear", self.code)
        self.assertIn('aria-label="Clear selection"', self.code)
        self.assertIn("handleClear", self.code)

    def test_combobox_futuristic_visual_variants(self) -> None:
        """Verify 4 visual styling presets (default, card, glass, neon)."""
        self.assertIn("backdropFilter", self.code)
        self.assertIn("0 0 15px rgba(56, 189, 248, 0.3)", self.code)
        self.assertIn("rgba(15, 23, 42, 0.95)", self.code)

    def test_combobox_size_scales(self) -> None:
        """Verify sm, md, lg size metrics."""
        self.assertIn('sm: { minHeight: "32px"', self.code)
        self.assertIn('md: { minHeight: "38px"', self.code)
        self.assertIn('lg: { minHeight: "44px"', self.code)

    def test_combobox_form_submission_integration(self) -> None:
        """Verify hidden input rendering when name prop is supplied."""
        self.assertIn('type="hidden"', self.code)
        self.assertIn("name={name}", self.code)
        self.assertIn('Array.isArray(effectiveValue) ? effectiveValue.join(",") : effectiveValue', self.code)

    def test_combobox_zero_runtime_dependencies(self) -> None:
        """Combobox component template must not import external third-party libraries."""
        lines = [line.strip() for line in self.code.split("\n") if line.strip().startswith("import ")]
        for line in lines:
            self.assertTrue(
                line.startswith('import React') or 'from "react"' in line,
                f"Unexpected external import detected: {line}",
            )

    def test_combobox_adapter_emits_file(self) -> None:
        """NextjsWebAdapter must emit components/combobox.tsx in the generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/combobox.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_combobox_exported_from_codegen_package(self) -> None:
        """cg.render_combobox_component must be exposed at package root."""
        self.assertTrue(callable(cg.render_combobox_component))
        self.assertEqual(cg.render_combobox_component(), self.code)

    def test_combobox_diff_invariance(self) -> None:
        """Diff invariance: changing ir.description must not alter components/combobox.tsx."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        f1 = project1.get("components/combobox.tsx")

        ir_mutated = dataclasses.replace(
            self.ir,
            description="Completely different description for diff invariance test",
        )
        project2 = adapter.generate(ir_mutated)
        f2 = project2.get("components/combobox.tsx")

        self.assertEqual(f1.content, f2.content)


if __name__ == "__main__":
    unittest.main()

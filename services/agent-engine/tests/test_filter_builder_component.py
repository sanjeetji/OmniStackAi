"""Tests for the Query Filter Builder & Dynamic Rule Bar Suite codegen (R-369).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName.
4. Exported types (FilterBuilderVariant, FilterBuilderSize, FilterCombinator,
   FilterOperator, FilterFieldType, FilterFieldOption, FilterFieldDefinition,
   FilterRule, FilterGroup, FilterBuilderProps).
5. Semantic aliases (QueryBuilder, FilterBar, default export).
6. 4 visual styling variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. WAI-ARIA 1.2 group and toolbar semantics (role="group", role="toolbar", aria-label, aria-pressed).
9. Built-in zero-dependency vector icons (PlusIcon, TrashIcon, FilterIcon, CheckIcon, RefreshCwIcon).
10. Combinator toggle (AND / OR) and rule management (add, remove, change).
11. Context-aware operators by field type (text, number, date, boolean, select) and unary operators.
12. Hidden input form submission integration when name prop is present.
13. Apply and reset action triggers.
14. NextjsWebAdapter emits components/filter-builder.tsx.
15. Codegen package export render_filter_builder_component in __all__.
16. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_filter_builder_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestFilterBuilderComponent(unittest.TestCase):
    """Test suite for components/filter-builder.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_filter_builder_component()
        self.ir = example_ir("rideshare-favourites")

    def test_zero_runtime_dependencies(self) -> None:
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+"([^"]+)"', self.code)
        for imp in imports:
            self.assertEqual(imp, "react", f"Forbidden external import: {imp}")

    def test_use_client_directive(self) -> None:
        """Must have 'use client' as first statement for Next.js App Router."""
        lines = [line.strip() for line in self.code.splitlines() if line.strip()]
        self.assertEqual(lines[0], '"use client";')

    def test_forward_ref_and_display_name(self) -> None:
        """Must use React.forwardRef and set explicit displayName."""
        self.assertIn("forwardRef", self.code)
        self.assertIn('FilterBuilder.displayName = "FilterBuilder"', self.code)
        self.assertIn('QueryBuilder.displayName = "QueryBuilder"', self.code)
        self.assertIn('FilterBar.displayName = "FilterBar"', self.code)

    def test_exported_types(self) -> None:
        """Must export canonical TypeScript types and interfaces."""
        self.assertIn("export type FilterBuilderVariant =", self.code)
        self.assertIn("export type FilterBuilderSize =", self.code)
        self.assertIn("export type FilterCombinator =", self.code)
        self.assertIn("export type FilterOperator =", self.code)
        self.assertIn("export type FilterFieldType =", self.code)
        self.assertIn("export interface FilterFieldOption", self.code)
        self.assertIn("export interface FilterFieldDefinition", self.code)
        self.assertIn("export interface FilterRule", self.code)
        self.assertIn("export interface FilterGroup", self.code)
        self.assertIn("export interface FilterBuilderProps", self.code)

    def test_semantic_aliases_and_default_export(self) -> None:
        """Must export FilterBuilder, QueryBuilder, FilterBar, and default export."""
        self.assertIn("export const FilterBuilder =", self.code)
        self.assertIn("export const QueryBuilder = FilterBuilder", self.code)
        self.assertIn("export const FilterBar = FilterBuilder", self.code)
        self.assertIn("export default FilterBuilder", self.code)

    def test_four_visual_variants(self) -> None:
        """Must support 'default', 'card', 'glass', 'neon' visual variants."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f'"{variant}"', self.code)
        self.assertIn("backdropFilter", self.code)  # glass
        self.assertIn("boxShadow", self.code)  # card / neon glow
        self.assertTrue(
            "22d3ee" in self.code or "rgba(6, 182, 212" in self.code,
            "Must feature neon cyan accent styling",
        )

    def test_three_size_presets(self) -> None:
        """Must support 'sm', 'md', and 'lg' size scales."""
        for size in ["sm", "md", "lg"]:
            self.assertIn(f'"{size}"', self.code)
        self.assertIn("SIZE_CONFIGS", self.code)

    def test_wai_aria_semantics(self) -> None:
        """Must implement WAI-ARIA 1.2 group and toolbar pattern semantics."""
        self.assertIn('role="group"', self.code)
        self.assertIn('role="toolbar"', self.code)
        self.assertIn("aria-pressed", self.code)
        self.assertIn("aria-label", self.code)

    def test_builtin_vector_icons(self) -> None:
        """Must provide zero-dependency SVG navigation and indicator icons."""
        self.assertIn("PlusIcon", self.code)
        self.assertIn("TrashIcon", self.code)
        self.assertIn("FilterIcon", self.code)
        self.assertIn("CheckIcon", self.code)
        self.assertIn("RefreshCwIcon", self.code)

    def test_dynamic_rule_management_and_combinator(self) -> None:
        """Must support adding, removing, updating rules, and toggling combinator."""
        self.assertIn("handleAddRule", self.code)
        self.assertIn("handleRemoveRule", self.code)
        self.assertIn("handleFieldChange", self.code)
        self.assertIn("handleOperatorChange", self.code)
        self.assertIn("handleValueChange", self.code)
        self.assertIn("handleCombinatorChange", self.code)

    def test_context_aware_operators(self) -> None:
        """Must define operator dictionaries and unary operators."""
        self.assertIn("DEFAULT_OPERATORS_BY_TYPE", self.code)
        self.assertIn("OPERATOR_LABELS", self.code)
        self.assertIn("UNARY_OPERATORS", self.code)
        self.assertIn("is_empty", self.code)
        self.assertIn("is_not_empty", self.code)

    def test_form_integration_hidden_input(self) -> None:
        """Must render hidden input when name prop is supplied."""
        self.assertIn('type="hidden"', self.code)
        self.assertIn("name={name}", self.code)
        self.assertIn("JSON.stringify(group)", self.code)

    def test_apply_and_reset_buttons(self) -> None:
        """Must provide Apply and Reset actions."""
        self.assertIn("handleReset", self.code)
        self.assertIn("handleApply", self.code)

    def test_adapter_emits_filter_builder_file(self) -> None:
        """NextjsWebAdapter must generate components/filter-builder.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/filter-builder.tsx")
        self.assertIsNotNone(f, "components/filter-builder.tsx must be emitted")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_filter_builder_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_filter_builder_component."""
        self.assertTrue(
            hasattr(cg, "render_filter_builder_component"),
            "render_filter_builder_component must be exported from codegen package",
        )
        self.assertIn("render_filter_builder_component", cg.__all__)
        self.assertTrue(callable(cg.render_filter_builder_component))
        self.assertEqual(cg.render_filter_builder_component(), self.code)

    def test_diff_invariance_across_description(self) -> None:
        """Component code must be 100% diff-invariant across ir.description changes."""
        modified_ir = dataclasses.replace(
            self.ir,
            description="Completely different prompt description for filter builder diff invariance test",
        )
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/filter-builder.tsx")
        f_b = adapter.generate(modified_ir).get("components/filter-builder.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(f_a.content, f_b.content)


if __name__ == "__main__":
    unittest.main()

"""Tests for the Transfer / Dual Listbox Picker component codegen (R-364).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName.
4. Exported types (TransferVariant, TransferSize, TransferDirection, TransferItem, TransferProps, TransferListProps).
5. Compound and alias exports (Transfer, TransferList, TransferItemComponent, DualListbox, PickList).
6. 4 visual variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. WAI-ARIA 1.2 dual listbox semantics (role="group", role="listbox", role="option", aria-multiselectable).
9. Built-in vector icons (ChevronRight, ChevronLeft, ChevronsRight, ChevronsLeft, Search, X, Check, Dash).
10. Live search filter inputs with clear button.
11. Header select all checkbox with indeterminate state and counts badge.
12. Central move operation buttons (Move right, Move left, Move all right, Move all left).
13. Double-click transfer support.
14. Hidden form input integration when name prop is provided.
15. Keyboard navigation (Space, Enter, roving tabIndex).
16. NextjsWebAdapter generates components/transfer.tsx.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_transfer_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestTransferComponent(unittest.TestCase):
    """Test suite for components/transfer.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_transfer_component()
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
        self.assertIn('Transfer.displayName = "Transfer"', self.code)
        self.assertIn('TransferList.displayName = "TransferList"', self.code)

    def test_exported_types(self) -> None:
        """Must export all canonical TypeScript types and interfaces."""
        self.assertIn("export type TransferVariant =", self.code)
        self.assertIn("export type TransferSize =", self.code)
        self.assertIn("export type TransferDirection =", self.code)
        self.assertIn("export interface TransferItem", self.code)
        self.assertIn("export interface TransferProps", self.code)
        self.assertIn("export interface TransferListProps", self.code)

    def test_compound_and_alias_exports(self) -> None:
        """Must export Transfer, subcomponents, and semantic aliases."""
        self.assertIn("export const Transfer =", self.code)
        self.assertIn("export const TransferList =", self.code)
        self.assertIn("export function TransferItemComponent", self.code)
        self.assertIn("export const DualListbox = Transfer", self.code)
        self.assertIn('DualListbox.displayName = "DualListbox"', self.code)
        self.assertIn("export const PickList = Transfer", self.code)
        self.assertIn('PickList.displayName = "PickList"', self.code)
        self.assertIn("export default Transfer", self.code)

    def test_four_visual_variants(self) -> None:
        """Must support 'default', 'card', 'glass', 'neon' variants."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f'"{variant}"', self.code)
        self.assertIn("backdropFilter", self.code)  # glass
        self.assertIn("boxShadow", self.code)  # card and neon
        self.assertIn("06b6d4", self.code)  # neon cyan glow

    def test_three_size_presets(self) -> None:
        """Must support 'sm', 'md', and 'lg' size scales."""
        for size in ["sm", "md", "lg"]:
            self.assertIn(f'"{size}"', self.code)
        self.assertIn("SIZE_CONFIGS", self.code)

    def test_wai_aria_semantics(self) -> None:
        """Must satisfy WAI-ARIA 1.2 dual listbox accessibility guidelines."""
        self.assertIn('role="group"', self.code)
        self.assertIn('role="listbox"', self.code)
        self.assertIn('role="option"', self.code)
        self.assertIn('role="checkbox"', self.code)
        self.assertIn('aria-multiselectable="true"', self.code)
        self.assertIn("aria-selected", self.code)
        self.assertIn("aria-disabled", self.code)
        self.assertIn("aria-checked", self.code)
        self.assertIn("tabIndex", self.code)

    def test_builtin_vector_icons(self) -> None:
        """Must include zero-dependency SVG icons for navigation and actions."""
        self.assertIn("ChevronRightIcon", self.code)
        self.assertIn("ChevronLeftIcon", self.code)
        self.assertIn("ChevronsRightIcon", self.code)
        self.assertIn("ChevronsLeftIcon", self.code)
        self.assertIn("SearchIcon", self.code)
        self.assertIn("XIcon", self.code)
        self.assertIn("CheckIcon", self.code)
        self.assertIn("DashIcon", self.code)

    def test_live_search_filtering(self) -> None:
        """Must support search inputs with clear button and filtering."""
        self.assertIn("showSearch", self.code)
        self.assertIn("searchPlaceholder", self.code)
        self.assertIn("searchValue", self.code)
        self.assertIn("onSearchChange", self.code)
        self.assertIn('aria-label="Clear search"', self.code)

    def test_header_select_all_and_counts(self) -> None:
        """Must provide Select All checkbox with indeterminate state and counts badge."""
        self.assertIn("isAllChecked", self.code)
        self.assertIn("isIndeterminate", self.code)
        self.assertIn("selectedAvailableCount", self.code)
        self.assertIn("fontVariantNumeric", self.code)

    def test_central_move_buttons(self) -> None:
        """Must provide central operation buttons with accessibility labels."""
        self.assertIn('aria-label="Move selected right"', self.code)
        self.assertIn('aria-label="Move selected left"', self.code)
        self.assertIn('aria-label="Move all right"', self.code)
        self.assertIn('aria-label="Move all left"', self.code)
        self.assertIn("canMoveRight", self.code)
        self.assertIn("canMoveLeft", self.code)

    def test_double_click_transfer(self) -> None:
        """Must support double-click to instantly transfer item."""
        self.assertIn("onDoubleClick", self.code)
        self.assertIn("onItemDoubleClick", self.code)
        self.assertIn("handleItemDoubleClick", self.code)

    def test_form_integration_hidden_inputs(self) -> None:
        """Must support native HTML forms with hidden input elements."""
        self.assertIn('type="hidden"', self.code)
        self.assertIn("name", self.code)

    def test_keyboard_navigation(self) -> None:
        """Must handle Space and Enter keys for item toggling and transfer."""
        self.assertIn('e.key === " "', self.code)
        self.assertIn('e.key === "Enter"', self.code)
        self.assertIn("e.preventDefault()", self.code)

    def test_adapter_emits_transfer_file(self) -> None:
        """NextjsWebAdapter must generate components/transfer.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/transfer.tsx")
        self.assertIsNotNone(f, "components/transfer.tsx must be emitted")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_transfer_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_transfer_component."""
        self.assertTrue(
            hasattr(cg, "render_transfer_component"),
            "render_transfer_component must be exported from codegen package",
        )
        self.assertIn("render_transfer_component", cg.__all__)
        self.assertTrue(callable(cg.render_transfer_component))
        self.assertEqual(cg.render_transfer_component(), self.code)

    def test_diff_invariance_across_description(self) -> None:
        """Component code must be 100% diff-invariant across ir.description changes."""
        modified_ir = dataclasses.replace(
            self.ir,
            description="Completely different prompt description for transfer diff invariance test",
        )
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/transfer.tsx")
        f_b = adapter.generate(modified_ir).get("components/transfer.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(f_a.content, f_b.content)


if __name__ == "__main__":
    unittest.main()

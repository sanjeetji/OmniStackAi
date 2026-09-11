"""Tests for the High-Performance Infinite Virtual List & Windowed Scroller Suite codegen (R-368).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName.
4. Exported types (VirtualListVariant, VirtualListSize, VirtualScrollAlignment,
   VirtualItemInfo, VirtualListHandle, VirtualListProps).
5. Semantic aliases (VirtualScroller, WindowedList, default export).
6. 4 visual styling variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. WAI-ARIA 1.2 feed semantics (role="feed", role="article", aria-posinset, aria-setsize, aria-busy).
9. Mathematical windowing logic (startIndex, endIndex, overscan, phantom total height).
10. Dynamic and fixed item height calculations (itemHeight as number or function).
11. Infinite scroll trigger and distance threshold (onEndReached, endReachedThreshold).
12. Imperative handle (scrollTo, scrollToIndex, scrollToTop, scrollToBottom).
13. Fast-scrolling detection (isScrolling flag).
14. NextjsWebAdapter emits components/virtual-list.tsx.
15. Codegen package export render_virtual_list_component in __all__.
16. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_virtual_list_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestVirtualListComponent(unittest.TestCase):
    """Test suite for components/virtual-list.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_virtual_list_component()
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
        self.assertIn('VirtualList.displayName = "VirtualList"', self.code)
        self.assertIn('VirtualScroller.displayName = "VirtualScroller"', self.code)
        self.assertIn('WindowedList.displayName = "WindowedList"', self.code)

    def test_exported_types(self) -> None:
        """Must export canonical TypeScript types and interfaces."""
        self.assertIn("export type VirtualListVariant =", self.code)
        self.assertIn("export type VirtualListSize =", self.code)
        self.assertIn("export type VirtualScrollAlignment =", self.code)
        self.assertIn("export interface VirtualItemInfo", self.code)
        self.assertIn("export interface VirtualListHandle", self.code)
        self.assertIn("export interface VirtualListProps", self.code)

    def test_semantic_aliases_and_default_export(self) -> None:
        """Must export VirtualList, VirtualScroller, WindowedList, and default export."""
        self.assertIn("export const VirtualList =", self.code)
        self.assertIn("export const VirtualScroller = VirtualList", self.code)
        self.assertIn("export const WindowedList = VirtualList", self.code)
        self.assertIn("export default VirtualList", self.code)

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
        """Must implement WAI-ARIA 1.2 feed & article pattern semantics."""
        self.assertIn('role="feed"', self.code)
        self.assertIn('role="article"', self.code)
        self.assertIn("aria-posinset", self.code)
        self.assertIn("aria-setsize", self.code)
        self.assertIn("aria-busy", self.code)

    def test_windowing_math_and_overscan(self) -> None:
        """Must compute visible range and support overscan buffer."""
        self.assertIn("startIndex", self.code)
        self.assertIn("endIndex", self.code)
        self.assertIn("overscan", self.code)
        self.assertIn("totalHeight", self.code)

    def test_dynamic_and_fixed_item_heights(self) -> None:
        """Must support fixed numeric itemHeight and dynamic height function."""
        self.assertIn("typeof itemHeight === \"number\"", self.code)
        self.assertIn("offsets", self.code)

    def test_infinite_scroll_and_threshold(self) -> None:
        """Must support infinite scroll trigger when approaching bottom."""
        self.assertIn("onEndReached", self.code)
        self.assertIn("endReachedThreshold", self.code)
        self.assertIn("distanceFromBottom", self.code)

    def test_imperative_handle_scroll_methods(self) -> None:
        """Must expose imperative scroll control methods."""
        self.assertIn("useImperativeHandle", self.code)
        self.assertIn("scrollToIndex", self.code)
        self.assertIn("scrollToTop", self.code)
        self.assertIn("scrollToBottom", self.code)

    def test_fast_scrolling_detection(self) -> None:
        """Must detect fast scrolling state for lightweight rendering."""
        self.assertIn("isScrolling", self.code)
        self.assertIn("setIsScrolling", self.code)

    def test_adapter_emits_virtual_list_file(self) -> None:
        """NextjsWebAdapter must generate components/virtual-list.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/virtual-list.tsx")
        self.assertIsNotNone(f, "components/virtual-list.tsx must be emitted")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_virtual_list_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_virtual_list_component."""
        self.assertTrue(
            hasattr(cg, "render_virtual_list_component"),
            "render_virtual_list_component must be exported from codegen package",
        )
        self.assertIn("render_virtual_list_component", cg.__all__)
        self.assertTrue(callable(cg.render_virtual_list_component))
        self.assertEqual(cg.render_virtual_list_component(), self.code)

    def test_diff_invariance_across_description(self) -> None:
        """Component code must be 100% diff-invariant across ir.description changes."""
        modified_ir = dataclasses.replace(
            self.ir,
            description="Completely different prompt description for virtual list diff invariance test",
        )
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/virtual-list.tsx")
        f_b = adapter.generate(modified_ir).get("components/virtual-list.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(f_a.content, f_b.content)


if __name__ == "__main__":
    unittest.main()

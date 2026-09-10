"""Tests for Task R-338: Generated Accessible Reusable Hierarchical Tree View Component.

Verifies that NextjsWebAdapter emits an accessible, reusable, hierarchical TreeView component suite
(apps/web/components/tree-view.tsx) supporting:
- TreeNode interface with id, label, icon, children, disabled, badge, data
- TreeViewVariant ("default" | "bordered" | "ghost" | "lines")
- Single-select and multi-select modes with keyboard and mouse interactions
- Controlled and uncontrolled expansion state (expandedIds, onToggle, defaultExpanded)
- Search filter with automated ancestor auto-expansion and match highlighting
- Connecting guide lines (showLines / variant="lines")
- WAI-ARIA Tree View 1.2 compliance: role="tree", role="treeitem", role="group", aria-expanded, aria-selected, aria-level, aria-posinset, aria-setsize, aria-disabled
- Full keyboard navigation: ArrowDown, ArrowUp, ArrowRight, ArrowLeft, Home, End, Enter, Space, *
- Inline SVG icons: ChevronRight, FolderClosed, FolderOpen, FileText, Search
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_tree_view_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TreeViewComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the TreeView component."""

    def setUp(self) -> None:
        self.code = render_tree_view_component()
        self.ir = example_ir("rideshare-favourites")

    def test_tree_view_component_is_client_component(self) -> None:
        """The TreeView component must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "TreeView must have 'use client' as the first statement.",
        )

    def test_tree_view_component_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export interface TreeNode", self.code)
        self.assertIn("export type TreeViewVariant", self.code)
        self.assertIn('"default"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn('"ghost"', self.code)
        self.assertIn('"lines"', self.code)
        self.assertIn("export interface TreeViewProps", self.code)

    def test_tree_view_component_exports_component(self) -> None:
        """Verify TreeView component and default export."""
        self.assertIn("export function TreeView", self.code)
        self.assertIn("export default TreeView;", self.code)

    def test_tree_view_component_uses_wai_aria_tree_semantics(self) -> None:
        """Verify WAI-ARIA Tree View 1.2 roles and container attributes."""
        self.assertIn('role="tree"', self.code)
        self.assertIn('role="treeitem"', self.code)
        self.assertIn('role="group"', self.code)
        self.assertIn("aria-label={ariaLabel}", self.code)
        self.assertIn("aria-multiselectable=", self.code)

    def test_tree_view_component_handles_aria_attributes(self) -> None:
        """Verify treeitem accessibility states and position attributes."""
        self.assertIn("aria-expanded=", self.code)
        self.assertIn("aria-selected=", self.code)
        self.assertIn("aria-level=", self.code)
        self.assertIn("aria-posinset=", self.code)
        self.assertIn("aria-setsize=", self.code)
        self.assertIn("aria-disabled=", self.code)

    def test_tree_view_component_handles_keyboard_navigation(self) -> None:
        """Verify complete keyboard navigation handling per WAI-ARIA 1.2."""
        self.assertIn('case "ArrowDown":', self.code)
        self.assertIn('case "ArrowUp":', self.code)
        self.assertIn('case "ArrowRight":', self.code)
        self.assertIn('case "ArrowLeft":', self.code)
        self.assertIn('case "Home":', self.code)
        self.assertIn('case "End":', self.code)
        self.assertIn('case "Enter":', self.code)
        self.assertIn('case " ":', self.code)
        self.assertIn('case "*":', self.code)

    def test_tree_view_component_supports_single_and_multi_select(self) -> None:
        """Verify support for both single-select and multi-select modes."""
        self.assertIn("selectedId", self.code)
        self.assertIn("onSelect", self.code)
        self.assertIn("selectedIds", self.code)
        self.assertIn("onMultiSelect", self.code)
        self.assertIn("multiSelect", self.code)
        self.assertIn('type="checkbox"', self.code)

    def test_tree_view_component_supports_expansion_control(self) -> None:
        """Verify expansion state control and toggle handlers."""
        self.assertIn("expandedIds", self.code)
        self.assertIn("onToggle", self.code)
        self.assertIn("defaultExpanded", self.code)
        self.assertIn("toggleExpand", self.code)

    def test_tree_view_component_supports_search_filter(self) -> None:
        """Verify search filtering, auto-expansion, and match highlighting."""
        self.assertIn("filter", self.code)
        self.assertIn("showSearch", self.code)
        self.assertIn("searchPlaceholder", self.code)
        self.assertIn("highlightMatch", self.code)
        self.assertIn("<mark", self.code)

    def test_tree_view_component_supports_variants_and_guide_lines(self) -> None:
        """Verify styling options including connector guide lines."""
        self.assertIn("showLines", self.code)
        self.assertIn("borderLeft", self.code)
        self.assertIn("variant", self.code)

    def test_tree_view_component_includes_built_in_svg_icons(self) -> None:
        """Verify inline vector icons for folder, file, chevron, and search."""
        self.assertIn("ChevronRightIcon", self.code)
        self.assertIn("FolderClosedIcon", self.code)
        self.assertIn("FolderOpenIcon", self.code)
        self.assertIn("FileTextIcon", self.code)
        self.assertIn("SearchIcon", self.code)

    def test_adapter_emits_tree_view_file(self) -> None:
        """NextjsWebAdapter emits components/tree-view.tsx in generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/tree-view.tsx")
        self.assertIsNotNone(f, "components/tree-view.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_tree_view_diff_invariant(self) -> None:
        """TreeView output is 100% diff-invariant across ir.description changes."""
        ir_b = dataclasses.replace(self.ir, description="Completely different description")
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/tree-view.tsx")
        f_b = adapter.generate(ir_b).get("components/tree-view.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(f_a.content, f_b.content)

    def test_tree_view_zero_external_dependencies(self) -> None:
        """TreeView uses only React; zero external package imports."""
        modules = re.findall(r'from\s+"([^"]+)"', self.code)
        for mod in modules:
            self.assertEqual(mod, "react", f"Unexpected external import: {mod}")

    def test_package_codegen_exports_render_tree_view_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_tree_view_component."""
        self.assertTrue(callable(cg.render_tree_view_component))
        self.assertIn("render_tree_view_component", cg.__all__)
        self.assertEqual(cg.render_tree_view_component(), self.code)


if __name__ == "__main__":
    unittest.main()

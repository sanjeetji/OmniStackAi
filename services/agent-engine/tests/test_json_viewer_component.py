"""Tests for the Accessible Futuristic Interactive JSON Viewer & Schema Tree Inspector Suite (components/json-viewer.tsx)."""

from __future__ import annotations

import unittest
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_json_viewer_component,
)


class TestJsonViewerComponent(unittest.TestCase):
    """Unit tests for Accessible Futuristic Interactive JSON Viewer & Schema Tree Inspector Suite."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_json_viewer_component()

    def test_file_generated(self) -> None:
        """components/json-viewer.tsx must be emitted by NextjsWebAdapter."""
        adapter = NextjsWebAdapter()
        ir = example_ir("minimal-blog")
        project = adapter.generate(ir)
        f = project.get("components/json-viewer.tsx")
        self.assertIsNotNone(f)

    def test_diff_invariance_and_codegen_export(self) -> None:
        """render_json_viewer_component must be exported and output diff-invariant."""
        src1 = render_json_viewer_component()
        adapter = NextjsWebAdapter()
        proj1 = adapter.generate(example_ir("minimal-blog"))
        proj2 = adapter.generate(example_ir("rideshare-favourites"))

        f1 = proj1.get("components/json-viewer.tsx")
        f2 = proj2.get("components/json-viewer.tsx")

        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, src1)

    def test_zero_runtime_dependencies(self) -> None:
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        import re
        imports = re.findall(r'from\s+[\'"]([^\'"]+)[\'"]', self.source)
        for pkg in imports:
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected non-react import found: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        """Must wrap component in forwardRef and expose useImperativeHandle with JsonViewerHandle."""
        self.assertIn("forwardRef<JsonViewerHandle, JsonViewerProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        self.assertIn("expandAll,", self.source)
        self.assertIn("collapseAll,", self.source)
        self.assertIn("setDepth,", self.source)
        self.assertIn("getJson:", self.source)
        self.assertIn("setJson:", self.source)

    def test_typescript_types_present(self) -> None:
        """All required TypeScript type exports must be present."""
        expected_types = [
            "export type JsonViewerVariant",
            "export type JsonViewerSize",
            "export type JsonViewMode",
            "export type JsonValueType",
            "export interface JsonViewerHandle",
            "export interface JsonViewerToolbarProps",
            "export interface JsonTreeNodeProps",
            "export interface JsonViewerProps",
        ]
        for t in expected_types:
            self.assertIn(t, self.source, f"Missing TypeScript type export: {t}")

    def test_compound_and_alias_exports(self) -> None:
        """Must export JsonViewer, JsonTree, ObjectInspector, SchemaViewer, JsonViewerToolbar, and default export."""
        self.assertIn("export const JsonViewer =", self.source)
        self.assertIn("export const JsonTree =", self.source)
        self.assertIn("export const ObjectInspector =", self.source)
        self.assertIn("export const SchemaViewer =", self.source)
        self.assertIn("export const JsonViewerToolbar", self.source)
        self.assertIn("export default JsonViewerComponent", self.source)

    def test_display_names_defined(self) -> None:
        """Must define explicit displayName on all compound and alias exports."""
        self.assertIn("JsonTreeNode.displayName = 'JsonTreeNode'", self.source)
        self.assertIn("JsonViewerToolbar.displayName = 'JsonViewerToolbar'", self.source)
        self.assertIn("JsonViewerComponent.displayName = 'JsonViewer'", self.source)
        self.assertIn("JsonViewer.displayName = 'JsonViewer'", self.source)
        self.assertIn("JsonTree.displayName = 'JsonTree'", self.source)
        self.assertIn("ObjectInspector.displayName = 'ObjectInspector'", self.source)
        self.assertIn("SchemaViewer.displayName = 'SchemaViewer'", self.source)

    def test_variants_present(self) -> None:
        """Must define all 4 required visual styling variants: default, card, glass, neon."""
        self.assertIn("'default' | 'card' | 'glass' | 'neon'", self.source)
        self.assertIn("default: {", self.source)
        self.assertIn("card: {", self.source)
        self.assertIn("glass: {", self.source)
        self.assertIn("neon: {", self.source)

    def test_sizes_present(self) -> None:
        """Must define sm, md, lg size scales."""
        self.assertIn("'sm' | 'md' | 'lg'", self.source)
        self.assertIn("sm: {", self.source)
        self.assertIn("md: {", self.source)
        self.assertIn("lg: {", self.source)

    def test_view_modes_present(self) -> None:
        """Must support tree and raw view modes."""
        self.assertIn("'tree' | 'raw'", self.source)
        self.assertIn("TreeIcon", self.source)
        self.assertIn("CodeIcon", self.source)

    def test_type_colors_present(self) -> None:
        """Must define distinct syntax colors for all JSON value types."""
        self.assertIn("TYPE_COLORS: Record<JsonValueType", self.source)
        for t in ["string", "number", "boolean", "null", "undefined", "object", "array"]:
            self.assertIn(f"{t}:", self.source)

    def test_tree_node_and_expansion_logic(self) -> None:
        """Must implement hierarchical tree node rendering and toggle expansion."""
        self.assertIn("function collectPathsToDepth", self.source)
        self.assertIn("function collectAllExpandablePaths", self.source)
        self.assertIn("toggleExpand", self.source)
        self.assertIn("expandedPaths.has(path)", self.source)
        self.assertIn("childCount", self.source)

    def test_search_and_highlight_filtering(self) -> None:
        """Must implement search filtering with match counter and highlight marks."""
        self.assertIn("function countMatches", self.source)
        self.assertIn("matchCount", self.source)
        self.assertIn("renderHighlighted", self.source)
        self.assertIn("<mark", self.source)
        self.assertIn("SearchIcon", self.source)

    def test_depth_controls(self) -> None:
        """Must implement Expand All, Collapse All, and default depth settings."""
        self.assertIn("onExpandAll", self.source)
        self.assertIn("onCollapseAll", self.source)
        self.assertIn("Expand All", self.source)
        self.assertIn("Collapse All", self.source)
        self.assertIn("defaultDepth", self.source)

    def test_inline_editing_logic(self) -> None:
        """Must support inline editing of primitive values with type parser and tree updater."""
        self.assertIn("isEditing", self.source)
        self.assertIn("handleStartEdit", self.source)
        self.assertIn("handleCommitEdit", self.source)
        self.assertIn("function parseInputPrimitive", self.source)
        self.assertIn("function updateAtPath", self.source)

    def test_copy_and_export_actions(self) -> None:
        """Must implement copy path, copy value, copy all, and download export."""
        self.assertIn("handleCopyPath", self.source)
        self.assertIn("handleCopyValue", self.source)
        self.assertIn("handleCopyAll", self.source)
        self.assertIn("handleExport", self.source)
        self.assertIn("CopyIcon", self.source)
        self.assertIn("CheckIcon", self.source)
        self.assertIn("DownloadIcon", self.source)

    def test_wai_aria_accessibility(self) -> None:
        """Must include appropriate WAI-ARIA tree and toolbar roles."""
        self.assertIn('role="tree"', self.source)
        self.assertIn('role="treeitem"', self.source)
        self.assertIn('role="group"', self.source)
        self.assertIn('role="toolbar"', self.source)
        self.assertIn('role="searchbox"', self.source)
        self.assertIn('aria-expanded=', self.source)
        self.assertIn('aria-level=', self.source)


if __name__ == "__main__":
    unittest.main()

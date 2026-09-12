"""Tests for the Accessible Futuristic Reusable Mind Map & Concept Tree Suite (components/mind-map.tsx)."""

from __future__ import annotations

import re
import unittest
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_mind_map_component,
)


class TestMindMapComponent(unittest.TestCase):
    """Unit tests for Accessible Futuristic Reusable Mind Map & Concept Tree Suite (R-397)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_mind_map_component()

    def test_file_generated(self) -> None:
        """components/mind-map.tsx must be emitted by NextjsWebAdapter."""
        adapter = NextjsWebAdapter()
        ir = example_ir("minimal-blog")
        project = adapter.generate(ir)
        f = project.get("components/mind-map.tsx")
        self.assertIsNotNone(f)

    def test_diff_invariance_and_codegen_export(self) -> None:
        """render_mind_map_component must be exported and output diff-invariant."""
        src1 = render_mind_map_component()
        adapter = NextjsWebAdapter()
        proj1 = adapter.generate(example_ir("minimal-blog"))
        proj2 = adapter.generate(example_ir("rideshare-favourites"))

        f1 = proj1.get("components/mind-map.tsx")
        f2 = proj2.get("components/mind-map.tsx")

        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, src1)

    def test_use_client_directive(self) -> None:
        """Must have 'use client' as first statement for Next.js App Router."""
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+[\'"]([^\'"]+)[\'"]', self.source)
        for pkg in imports:
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected non-react import found: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        """Must wrap component in forwardRef and expose useImperativeHandle with MindMapHandle methods."""
        self.assertIn("forwardRef<MindMapHandle, MindMapProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        self.assertIn("zoomIn:", self.source)
        self.assertIn("zoomOut:", self.source)
        self.assertIn("resetZoom:", self.source)
        self.assertIn("fitToView:", self.source)
        self.assertIn("selectNode:", self.source)
        self.assertIn("expandAll:", self.source)
        self.assertIn("collapseAll:", self.source)
        self.assertIn("exportAsPng:", self.source)
        self.assertIn("exportAsSvg:", self.source)
        self.assertIn("exportAsJson:", self.source)
        self.assertIn("addNode:", self.source)
        self.assertIn("deleteNode:", self.source)
        self.assertIn("getNodes:", self.source)

    def test_typescript_types_present(self) -> None:
        """All required TypeScript type exports must be present."""
        expected_types = [
            "export type MindMapVariant",
            "export type MindMapSize",
            "export type MindMapLayout",
            "export interface MindMapNode",
            "export interface MindMapHandle",
            "export interface MindMapControlsProps",
            "export interface NodeInspectorProps",
            "export interface MindMapProps",
        ]
        for t in expected_types:
            self.assertIn(t, self.source, f"Missing TypeScript type export: {t}")

    def test_compound_and_alias_exports(self) -> None:
        """Must export MindMap, ConceptTree, BrainstormMap, IdeaGraph, MindMapControls, NodeInspector, and default export."""
        self.assertIn("export const MindMap =", self.source)
        self.assertIn("export const ConceptTree =", self.source)
        self.assertIn("export const BrainstormMap =", self.source)
        self.assertIn("export const IdeaGraph =", self.source)
        self.assertIn("export const MindMapControls =", self.source)
        self.assertIn("export const NodeInspector =", self.source)
        self.assertIn("export default MindMapComponent", self.source)

    def test_display_names_defined(self) -> None:
        """Must define explicit displayName on all compound and alias exports."""
        self.assertIn("MindMapControls.displayName = 'MindMapControls'", self.source)
        self.assertIn("NodeInspector.displayName = 'NodeInspector'", self.source)
        self.assertIn("MindMapComponent.displayName = 'MindMap'", self.source)

    def test_variants_present(self) -> None:
        """Must define all 4 required visual styling variants: default, card, glass, neon."""
        self.assertIn("'default' | 'card' | 'glass' | 'neon'", self.source)
        self.assertIn("isNeon", self.source)
        self.assertIn("isGlass", self.source)
        self.assertIn("isCard", self.source)

    def test_sizes_present(self) -> None:
        """Must define sm, md, lg size scales."""
        self.assertIn("'sm' | 'md' | 'lg'", self.source)

    def test_layouts_present(self) -> None:
        """Must define radial, tree-horizontal, and tree-vertical tree layouts."""
        self.assertIn("'radial' | 'tree-horizontal' | 'tree-vertical'", self.source)
        self.assertIn("computeLayout", self.source)
        self.assertIn("tree-horizontal", self.source)
        self.assertIn("tree-vertical", self.source)

    def test_wai_aria_accessibility(self) -> None:
        """Must include appropriate WAI-ARIA roles, labels, and keyboard navigation."""
        self.assertIn('role="application"', self.source)
        self.assertIn('role="tree"', self.source)
        self.assertIn('role="treeitem"', self.source)
        self.assertIn('role="toolbar"', self.source)
        self.assertIn('role="complementary"', self.source)
        self.assertIn('aria-label="Mind Map Canvas"', self.source)

    def test_node_actions_and_tree_manipulation(self) -> None:
        """Must support node adding, deleting, updating, and selecting."""
        self.assertIn("addChildToTree", self.source)
        self.assertIn("deleteNodeFromTree", self.source)
        self.assertIn("updateNodeInTree", self.source)
        self.assertIn("setSelectedNodeId", self.source)
        self.assertIn("handleAddChild", self.source)
        self.assertIn("handleDeleteNode", self.source)
        self.assertIn("handleUpdateNode", self.source)

    def test_collapsible_subtrees(self) -> None:
        """Must support collapsing/expanding subtrees recursively and toggling node collapse."""
        self.assertIn("collapsed", self.source)
        self.assertIn("setCollapseRecursive", self.source)
        self.assertIn("toggleCollapse", self.source)

    def test_export_functions(self) -> None:
        """Must support PNG, SVG, and JSON exports."""
        self.assertIn("exportAsPng", self.source)
        self.assertIn("exportAsSvg", self.source)
        self.assertIn("exportAsJson", self.source)
        self.assertIn("image/png", self.source)
        self.assertIn("image/svg+xml", self.source)
        self.assertIn("application/json", self.source)

    def test_search_query_filtering(self) -> None:
        """Must support searching/filtering nodes by label and description."""
        self.assertIn("searchQuery", self.source)
        self.assertIn("isMatch", self.source)
        self.assertIn("Search concepts...", self.source)

    def test_package_codegen_exports_render_mind_map_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_mind_map_component."""
        import omnistackai_agent_engine.codegen as cg

        self.assertTrue(hasattr(cg, "render_mind_map_component"))
        self.assertTrue(callable(cg.render_mind_map_component))
        self.assertIn("render_mind_map_component", cg.__all__)

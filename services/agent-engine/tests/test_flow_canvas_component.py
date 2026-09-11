"""Tests for the Accessible Futuristic Reusable Flowchart & Node-Based Workflow Canvas Suite codegen (R-380).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName across compound exports.
4. Exported canonical TypeScript types & interfaces.
5. Compound and semantic alias exports (FlowCanvas, WorkflowBuilder, NodeGraph, FlowNodeItem, FlowEdgeLine, FlowMinimap, FlowControls, default).
6. Node types and port connections ("input", "output", "action", "condition").
7. 4 visual styling variants ("default", "card", "glass", "neon").
8. 3 size presets ("sm", "md", "lg").
9. SVG cubic bezier connection curves and arrow markers.
10. Animated edge dataflow rendering.
11. Grid pattern and snapping math (snapToGrid, gridSize).
12. Minimap preview calculation and viewport indicator box.
13. Zoom and pan canvas transform calculations.
14. WAI-ARIA application and keyboard navigation semantics (role="application", aria-label="Workflow Canvas").
15. Imperative handle methods (zoomIn, zoomOut, fitView, resetView, getNodes, getEdges, addNode, deleteSelected, exportJson).
16. NextjsWebAdapter emits components/flow-canvas.tsx and codegen package exports render_flow_canvas_component.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_flow_canvas_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestFlowCanvasComponent(unittest.TestCase):
    """Test suite for components/flow-canvas.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_flow_canvas_component()
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
        """Must use React.forwardRef and set explicit displayName across compound exports."""
        self.assertIn("forwardRef", self.code)
        self.assertIn('FlowCanvas.displayName = "FlowCanvas"', self.code)
        self.assertIn('WorkflowBuilder.displayName = "WorkflowBuilder"', self.code)
        self.assertIn('NodeGraph.displayName = "NodeGraph"', self.code)
        self.assertIn('FlowNodeItem.displayName = "FlowNodeItem"', self.code)
        self.assertIn('FlowEdgeLine.displayName = "FlowEdgeLine"', self.code)
        self.assertIn('FlowMinimap.displayName = "FlowMinimap"', self.code)
        self.assertIn('FlowControls.displayName = "FlowControls"', self.code)

    def test_exported_canonical_types(self) -> None:
        """Canonical TypeScript types and interfaces must be exported."""
        self.assertIn("export type FlowVariant =", self.code)
        self.assertIn("export type FlowSize =", self.code)
        self.assertIn("export type FlowNodeType =", self.code)
        self.assertIn("export type FlowNodeStatus =", self.code)
        self.assertIn("export type FlowEdgeStyle =", self.code)
        self.assertIn("export type FlowPortPosition =", self.code)
        self.assertIn("export interface FlowPort", self.code)
        self.assertIn("export interface FlowNode", self.code)
        self.assertIn("export interface FlowEdge", self.code)
        self.assertIn("export interface FlowCanvasHandle", self.code)
        self.assertIn("export interface FlowCanvasProps", self.code)

    def test_compound_and_alias_exports(self) -> None:
        """Must export FlowCanvas, WorkflowBuilder, NodeGraph, FlowNodeItem, FlowEdgeLine, FlowMinimap, FlowControls, and default."""
        self.assertIn("export const FlowCanvas =", self.code)
        self.assertIn("export const WorkflowBuilder =", self.code)
        self.assertIn("export const NodeGraph =", self.code)
        self.assertIn("export const FlowNodeItem", self.code)
        self.assertIn("export const FlowEdgeLine", self.code)
        self.assertIn("export const FlowMinimap", self.code)
        self.assertIn("export const FlowControls", self.code)
        self.assertIn("export default FlowCanvas;", self.code)

    def test_node_types_and_ports(self) -> None:
        """Must support node types and input/output port definitions."""
        self.assertIn('"input"', self.code)
        self.assertIn('"output"', self.code)
        self.assertIn('"action"', self.code)
        self.assertIn('"condition"', self.code)
        self.assertIn("defaultInputs", self.code)
        self.assertIn("defaultOutputs", self.code)

    def test_four_visual_variants(self) -> None:
        """Must support 4 visual styling variants."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f'"{variant}"', self.code)
        self.assertIn("backdropFilter", self.code)
        self.assertIn("rgba(6, 182, 212", self.code)

    def test_three_size_presets(self) -> None:
        """Must define sm, md, lg size presets."""
        self.assertIn("size === \"sm\"", self.code)
        self.assertIn("size === \"lg\"", self.code)

    def test_svg_cubic_bezier_curves_and_arrows(self) -> None:
        """Must render SVG cubic bezier paths and arrow markers for edge connections."""
        self.assertIn("<svg", self.code)
        self.assertIn("<path", self.code)
        self.assertIn("<defs>", self.code)
        self.assertIn("<marker", self.code)
        self.assertIn("<polygon", self.code)
        self.assertIn("Math.max(Math.abs(x2 - x1) * 0.5, 40)", self.code)

    def test_animated_dataflow_rendering(self) -> None:
        """Must support animated dataflow dashed stroke."""
        self.assertIn("edge.animated", self.code)
        self.assertIn("strokeDasharray", self.code)

    def test_grid_pattern_and_snapping(self) -> None:
        """Must render background grid pattern and compute grid snapping."""
        self.assertIn("<pattern", self.code)
        self.assertIn("snapToGrid", self.code)
        self.assertIn("gridSize", self.code)
        self.assertIn("Math.round(val / gridSize) * gridSize", self.code)

    def test_minimap_preview_and_viewport_box(self) -> None:
        """Must render FlowMinimap with node rectangles and viewport box."""
        self.assertIn("FlowMinimap", self.code)
        self.assertIn("Workflow Minimap", self.code)
        self.assertIn("minimapWidth", self.code)
        self.assertIn("minimapHeight", self.code)

    def test_canvas_pan_and_zoom_transform(self) -> None:
        """Must apply 2D pan and zoom transform to canvas world container."""
        self.assertIn("transformOrigin: \"0 0\"", self.code)
        self.assertIn("translate(${pan.x}px, ${pan.y}px) scale(${zoom})", self.code)
        self.assertIn("handleWheel", self.code)
        self.assertIn("handleCanvasMouseDown", self.code)

    def test_wai_aria_application_semantics(self) -> None:
        """Must contain WAI-ARIA application semantics and keyboard support."""
        self.assertIn('role="application"', self.code)
        self.assertIn('aria-label="Workflow Canvas"', self.code)
        self.assertIn("handleKeyDown", self.code)
        self.assertIn("ArrowLeft", self.code)
        self.assertIn("Delete", self.code)

    def test_imperative_handle_methods(self) -> None:
        """Must expose imperative handle methods via useImperativeHandle."""
        self.assertIn("useImperativeHandle", self.code)
        self.assertIn("zoomIn", self.code)
        self.assertIn("zoomOut", self.code)
        self.assertIn("resetView", self.code)
        self.assertIn("fitView", self.code)
        self.assertIn("getNodes:", self.code)
        self.assertIn("getEdges:", self.code)
        self.assertIn("addNode:", self.code)
        self.assertIn("deleteSelected:", self.code)
        self.assertIn("exportJson:", self.code)

    def test_nextjs_adapter_and_codegen_exports(self) -> None:
        """NextjsWebAdapter emits components/flow-canvas.tsx and codegen exposes render function."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        flow_file = project.get("components/flow-canvas.tsx")
        self.assertIsNotNone(flow_file, "components/flow-canvas.tsx must be generated")
        self.assertEqual(flow_file.content, self.code)

        self.assertIn("render_flow_canvas_component", cg.__all__)
        self.assertTrue(callable(cg.render_flow_canvas_component))
        self.assertEqual(cg.render_flow_canvas_component(), self.code)

    def test_diff_invariance(self) -> None:
        """Component code must be 100% diff-invariant across varying IR descriptions."""
        adapter = NextjsWebAdapter()
        ir1 = self.ir
        ir2 = dataclasses.replace(self.ir, description="Modified IR for flow canvas invariance")

        file1 = adapter.generate(ir1).get("components/flow-canvas.tsx")
        file2 = adapter.generate(ir2).get("components/flow-canvas.tsx")

        self.assertIsNotNone(file1)
        self.assertIsNotNone(file2)
        self.assertEqual(file1.content, file2.content)


if __name__ == "__main__":
    unittest.main()

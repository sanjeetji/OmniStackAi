"""Tests for the Accessible Futuristic Network Graph & Topology Map Suite (components/network-graph.tsx)."""

from __future__ import annotations

import re
import unittest
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_network_graph_component,
)


class TestNetworkGraphComponent(unittest.TestCase):
    """Unit tests for Accessible Futuristic Network Graph & Topology Map Suite (R-395)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_network_graph_component()

    def test_file_generated(self) -> None:
        """components/network-graph.tsx must be emitted by NextjsWebAdapter."""
        adapter = NextjsWebAdapter()
        ir = example_ir("minimal-blog")
        project = adapter.generate(ir)
        f = project.get("components/network-graph.tsx")
        self.assertIsNotNone(f)

    def test_diff_invariance_and_codegen_export(self) -> None:
        """render_network_graph_component must be exported and output diff-invariant."""
        src1 = render_network_graph_component()
        adapter = NextjsWebAdapter()
        proj1 = adapter.generate(example_ir("minimal-blog"))
        proj2 = adapter.generate(example_ir("rideshare-favourites"))

        f1 = proj1.get("components/network-graph.tsx")
        f2 = proj2.get("components/network-graph.tsx")

        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, src1)

    def test_zero_runtime_dependencies(self) -> None:
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+[\'"]([^\'"]+)[\'"]', self.source)
        for pkg in imports:
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected non-react import found: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        """Must wrap component in forwardRef and expose useImperativeHandle with NetworkGraphHandle."""
        self.assertIn("forwardRef<NetworkGraphHandle, NetworkGraphProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        self.assertIn("zoomIn,", self.source)
        self.assertIn("zoomOut,", self.source)
        self.assertIn("resetZoom,", self.source)
        self.assertIn("selectNode:", self.source)
        self.assertIn("pauseSimulation:", self.source)
        self.assertIn("resumeSimulation:", self.source)
        self.assertIn("reheatSimulation,", self.source)
        self.assertIn("exportAsPng,", self.source)
        self.assertIn("getNodes:", self.source)
        self.assertIn("getEdges:", self.source)

    def test_typescript_types_present(self) -> None:
        """All required TypeScript type exports must be present."""
        expected_types = [
            "export type NetworkGraphVariant",
            "export type NetworkGraphSize",
            "export type GraphNodeType",
            "export type GraphNodeStatus",
            "export interface GraphNodeMetrics",
            "export interface GraphNode",
            "export interface GraphEdge",
            "export interface NetworkGraphHandle",
            "export interface GraphControlsProps",
            "export interface NodeDetailsPanelProps",
            "export interface NetworkGraphProps",
        ]
        for t in expected_types:
            self.assertIn(t, self.source, f"Missing TypeScript type export: {t}")

    def test_compound_and_alias_exports(self) -> None:
        """Must export NetworkGraph, TopologyMap, ForceGraph, GraphVisualizer, GraphControls, NodeDetailsPanel, and default export."""
        self.assertIn("export const NetworkGraph =", self.source)
        self.assertIn("export const TopologyMap =", self.source)
        self.assertIn("export const ForceGraph =", self.source)
        self.assertIn("export const GraphVisualizer =", self.source)
        self.assertIn("export const GraphControls", self.source)
        self.assertIn("export const NodeDetailsPanel", self.source)
        self.assertIn("export default NetworkGraphComponent", self.source)

    def test_display_names_defined(self) -> None:
        """Must define explicit displayName on all compound and alias exports."""
        self.assertIn("GraphControls.displayName = 'GraphControls'", self.source)
        self.assertIn("NodeDetailsPanel.displayName = 'NodeDetailsPanel'", self.source)
        self.assertIn("NetworkGraphComponent.displayName = 'NetworkGraph'", self.source)
        self.assertIn("NetworkGraph.displayName = 'NetworkGraph'", self.source)
        self.assertIn("TopologyMap.displayName = 'TopologyMap'", self.source)
        self.assertIn("ForceGraph.displayName = 'ForceGraph'", self.source)
        self.assertIn("GraphVisualizer.displayName = 'GraphVisualizer'", self.source)

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

    def test_node_types_and_icons(self) -> None:
        """Must support 6 node types with custom SVGs: server, database, client, service, gateway, ai."""
        self.assertIn("'server' | 'database' | 'client' | 'service' | 'gateway' | 'ai'", self.source)
        self.assertIn("ServerIcon", self.source)
        self.assertIn("DatabaseIcon", self.source)
        self.assertIn("ClientIcon", self.source)
        self.assertIn("ServiceIcon", self.source)
        self.assertIn("GatewayIcon", self.source)
        self.assertIn("AiIcon", self.source)

    def test_statuses_present(self) -> None:
        """Must support 4 node statuses: healthy, warning, error, idle."""
        self.assertIn("'healthy' | 'warning' | 'error' | 'idle'", self.source)
        self.assertIn("healthy: {", self.source)
        self.assertIn("warning: {", self.source)
        self.assertIn("error: {", self.source)
        self.assertIn("idle: {", self.source)

    def test_force_directed_physics_simulation(self) -> None:
        """Must implement force-directed layout with repulsion, spring attraction, and requestAnimationFrame."""
        self.assertIn("repulsionForce", self.source)
        self.assertIn("linkDistance", self.source)
        self.assertIn("requestAnimationFrame", self.source)
        self.assertIn("centerGravity", self.source)
        self.assertIn("springForce", self.source)

    def test_pan_and_zoom_viewport(self) -> None:
        """Must provide pan, zoom, scale transform, and drag interactions."""
        self.assertIn("zoomIn", self.source)
        self.assertIn("zoomOut", self.source)
        self.assertIn("resetZoom", self.source)
        self.assertIn("handleMouseDown", self.source)
        self.assertIn("handleMouseMove", self.source)
        self.assertIn("handleMouseUp", self.source)
        self.assertIn("translate(${pan.x}, ${pan.y}) scale(${zoom})", self.source)

    def test_node_selection_and_drawer(self) -> None:
        """Must provide node selection and slide-over inspector drawer with live metrics."""
        self.assertIn("selectedNodeId", self.source)
        self.assertIn("NodeDetailsPanel", self.source)
        self.assertIn("connectedEdges", self.source)
        self.assertIn("CPU Load", self.source)
        self.assertIn("Memory", self.source)
        self.assertIn("Latency", self.source)
        self.assertIn("Throughput", self.source)

    def test_search_and_type_filtering(self) -> None:
        """Must provide search by label/tag and filtering by node type."""
        self.assertIn("searchQuery", self.source)
        self.assertIn("selectedType", self.source)
        self.assertIn("matchesFilter", self.source)
        self.assertIn("Search nodes or tags...", self.source)

    def test_png_export_capability(self) -> None:
        """Must support exporting graph canvas to PNG."""
        self.assertIn("exportAsPng", self.source)
        self.assertIn("toDataURL('image/png')", self.source)
        self.assertIn("network-topology.png", self.source)

    def test_wai_aria_semantics(self) -> None:
        """Must include WAI-ARIA 1.2 application semantics and accessible labels."""
        self.assertIn('role="application"', self.source)
        self.assertIn('aria-label="Network Topology Graph"', self.source)
        self.assertIn('role="toolbar"', self.source)
        self.assertIn('role="complementary"', self.source)
        self.assertIn('role="button"', self.source)


if __name__ == "__main__":
    unittest.main()

"""
R-387: Accessible Futuristic Reusable Interactive Geo Map & Location Pinpoint Suite
Unit tests for render_geo_map_component and the generated components/geo-map.tsx.
"""
from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_geo_map_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter, _GEO_MAP_COMPONENT


class TestGeoMapComponent(unittest.TestCase):
    """Test suite for components/geo-map.tsx codegen (R-387)."""

    def setUp(self) -> None:
        self.code = render_geo_map_component()
        self.ir = example_ir("rideshare-favourites")
        project = NextjsWebAdapter().generate(self.ir)
        self.file = project.get("components/geo-map.tsx")

    # ------------------------------------------------------------------
    # 1. File is generated at the correct path
    # ------------------------------------------------------------------
    def test_file_generated(self):
        """components/geo-map.tsx must be emitted by NextjsWebAdapter."""
        ir = example_ir("minimal-blog")
        project = NextjsWebAdapter().generate(ir)
        paths = project.paths()
        self.assertIn("components/geo-map.tsx", paths)

    # ------------------------------------------------------------------
    # 2. Zero external npm dependencies (only 'react' imports allowed)
    # ------------------------------------------------------------------
    def test_zero_runtime_dependencies(self):
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+[\'"]([^\'"]+)[\'"]', self.code)
        for pkg in imports:
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Forbidden external import detected: {pkg}",
            )

    # ------------------------------------------------------------------
    # 3. TypeScript type interfaces present
    # ------------------------------------------------------------------
    def test_typescript_types_present(self):
        """All required TypeScript type exports must be present."""
        required_types = [
            "GeoMapVariant",
            "GeoMapSize",
            "MarkerStyle",
            "MapMarker",
            "MapRoute",
            "GeoMapHandle",
            "MapCalloutProps",
            "MapControlsProps",
            "GeoMapProps",
        ]
        for t in required_types:
            self.assertIn(t, self.code, f"Missing TypeScript type: {t}")

    # ------------------------------------------------------------------
    # 4. All 4 visual variants present
    # ------------------------------------------------------------------
    def test_variants_present(self):
        """All four visual variants must be implemented: default, card, glass, neon."""
        for variant in ("default", "card", "glass", "neon"):
            self.assertIn(f"'{variant}'", self.code, f"Missing variant: {variant}")

    # ------------------------------------------------------------------
    # 5. All 3 size scales present
    # ------------------------------------------------------------------
    def test_sizes_present(self):
        """All three size scales must be configured: sm, md, lg."""
        for size in ("sm", "md", "lg"):
            self.assertIn(f"'{size}'", self.code, f"Missing size: {size}")

    # ------------------------------------------------------------------
    # 6. Compound and semantic alias exports present
    # ------------------------------------------------------------------
    def test_compound_exports(self):
        """All compound and semantic alias exports must be present."""
        exports = [
            "export const GeoMap",
            "export const InteractiveMap",
            "export const LocationPicker",
            "export const MapPin",
            "export const MapCallout",
            "export const MapControls",
            "export const RouteLine",
        ]
        for exp in exports:
            self.assertIn(exp, self.code, f"Missing export: {exp}")

    # ------------------------------------------------------------------
    # 7. Default export present
    # ------------------------------------------------------------------
    def test_default_export(self):
        """A default export must be present."""
        self.assertIn("export default GeoMapComponent", self.code)

    # ------------------------------------------------------------------
    # 8. WAI-ARIA 1.2 semantics present
    # ------------------------------------------------------------------
    def test_aria_semantics(self):
        """WAI-ARIA 1.2 application & region semantics must be present."""
        for attr in ('role="application"', 'aria-label="Interactive Map"'):
            self.assertIn(attr, self.code, f"Missing ARIA attribute: {attr}")

    # ------------------------------------------------------------------
    # 9. forwardRef and useImperativeHandle present
    # ------------------------------------------------------------------
    def test_forward_ref_and_imperative_handle(self):
        """forwardRef and useImperativeHandle must be used for the imperative handle API."""
        self.assertIn("forwardRef", self.code)
        self.assertIn("useImperativeHandle", self.code)

    # ------------------------------------------------------------------
    # 10. Marker styles supported
    # ------------------------------------------------------------------
    def test_marker_styles_present(self):
        """Marker styles pin, dot, pulse, beacon must be supported."""
        for style in ("'pin'", "'dot'", "'pulse'", "'beacon'"):
            self.assertIn(style, self.code, f"Missing marker style: {style}")

    # ------------------------------------------------------------------
    # 11. Coordinate projection utilities present
    # ------------------------------------------------------------------
    def test_projection_helpers(self):
        """lngToX, latToY, xToLng, and yToLat projection utilities must be present."""
        for helper in ("lngToX", "latToY", "xToLng", "yToLat"):
            self.assertIn(helper, self.code, f"Missing helper: {helper}")

    # ------------------------------------------------------------------
    # 12. Imperative handle methods present
    # ------------------------------------------------------------------
    def test_imperative_handle_methods(self):
        """Imperative handle must expose zoomIn, zoomOut, resetView, panTo, selectMarker, getSelectedMarker, getCoordinates."""
        methods = [
            "zoomIn",
            "zoomOut",
            "resetView",
            "panTo",
            "selectMarker",
            "getSelectedMarker",
            "getCoordinates",
        ]
        for m in methods:
            self.assertIn(m, self.code, f"Missing imperative handle method: {m}")

    # ------------------------------------------------------------------
    # 13. 'use client' directive present
    # ------------------------------------------------------------------
    def test_use_client_directive(self):
        """'use client' must be the first statement for Next.js App Router."""
        self.assertTrue(
            self.code.strip().startswith("'use client'") or self.code.strip().startswith('"use client"'),
            "Missing 'use client' directive",
        )

    # ------------------------------------------------------------------
    # 14. Explicit displayName on compound exports
    # ------------------------------------------------------------------
    def test_display_names(self):
        """All compound exports must have explicit displayName properties."""
        names = [
            'GeoMap.displayName = "GeoMap"',
            'InteractiveMap.displayName = "InteractiveMap"',
            'LocationPicker.displayName = "LocationPicker"',
            'MapPin.displayName = "MapPin"',
            'MapCallout.displayName = "MapCallout"',
            'MapControls.displayName = "MapControls"',
            'RouteLine.displayName = "RouteLine"',
        ]
        for name in names:
            # Check normalized single or double quotes
            single_quote = name.replace('"', "'")
            self.assertTrue(
                name in self.code or single_quote in self.code,
                f"Missing displayName: {name}",
            )

    # ------------------------------------------------------------------
    # 15. Diff invariance across ir.description
    # ------------------------------------------------------------------
    def test_diff_invariance_across_description(self):
        """Generated map content must be identical regardless of ir.description."""
        ir1 = example_ir("rideshare-favourites")
        ir2 = example_ir("minimal-blog")
        proj1 = NextjsWebAdapter().generate(ir1)
        proj2 = NextjsWebAdapter().generate(ir2)
        self.assertEqual(
            proj1.get("components/geo-map.tsx").content,
            proj2.get("components/geo-map.tsx").content,
        )

    # ------------------------------------------------------------------
    # 16. Package codegen exports render_geo_map_component
    # ------------------------------------------------------------------
    def test_package_codegen_exports(self):
        """omnistackai_agent_engine.codegen exposes render_geo_map_component."""
        self.assertTrue(hasattr(cg, "render_geo_map_component"))
        self.assertIn("render_geo_map_component", cg.__all__)
        self.assertEqual(cg.render_geo_map_component(), _GEO_MAP_COMPONENT)

    # ------------------------------------------------------------------
    # 17. Routes and Waypoints rendering support
    # ------------------------------------------------------------------
    def test_routes_and_waypoints_support(self):
        """RouteLine, animated routes, and waypoint lines must be supported."""
        self.assertIn("RouteLine", self.code)
        self.assertIn("route.points", self.code)
        self.assertIn("strokeDasharray", self.code)

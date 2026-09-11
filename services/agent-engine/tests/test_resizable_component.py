"""Tests for Task R-344: Generated Accessible Futuristic Reusable Resizable Panels & Splitter Component.

Verifies that NextjsWebAdapter emits an accessible, futuristic, reusable Resizable compound component
suite (apps/web/components/resizable.tsx) supporting:
- Compound suite (ResizablePanelGroup, ResizablePanel, ResizableHandle, Resizable)
- 4 futuristic visual variants ("neon", "glass", "bordered", "minimal")
- Split directions ("horizontal", "vertical")
- Pointer and touch drag resizing with responsive coordinate tracking
- Full keyboard navigation per WAI-ARIA Separator (Window Splitter) Pattern
- Full WAI-ARIA accessibility semantics (role="separator", aria-orientation,
  aria-valuenow, aria-valuemin, aria-valuemax, aria-label, tabIndex)
- Min and max size constraints (minSize, maxSize)
- Collapsible panels (collapsible, collapsedSize, onCollapse, onExpand)
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_resizable_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class ResizableComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the Resizable component."""

    def setUp(self) -> None:
        self.code = render_resizable_component()
        self.ir = example_ir("rideshare-favourites")

    def test_resizable_component_is_client_component(self) -> None:
        """The Resizable component must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "Resizable must have 'use client' as the first statement.",
        )

    def test_resizable_component_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type ResizableDirection", self.code)
        self.assertIn('"horizontal"', self.code)
        self.assertIn('"vertical"', self.code)
        self.assertIn("export type ResizableVariant", self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export interface ResizablePanelGroupProps", self.code)
        self.assertIn("export interface ResizablePanelProps", self.code)
        self.assertIn("export interface ResizableHandleProps", self.code)
        self.assertIn("export interface ResizablePanelContextValue", self.code)

    def test_resizable_component_exports_compound(self) -> None:
        """Verify Resizable compound component and subcomponents."""
        self.assertIn("export const ResizablePanelGroup =", self.code)
        self.assertIn("export const ResizablePanel =", self.code)
        self.assertIn("export const ResizableHandle =", self.code)
        self.assertIn("export const Resizable =", self.code)
        self.assertIn("export function useResizable()", self.code)
        self.assertIn("export default ResizablePanelGroup;", self.code)

    def test_resizable_zero_external_dependencies(self) -> None:
        """Resizable uses only React; zero external package imports."""
        import_lines = [
            line for line in self.code.splitlines() if line.startswith("import ")
        ]
        self.assertTrue(len(import_lines) >= 1)
        for line in import_lines:
            self.assertIn(
                'from "react"',
                line,
                f"Unexpected external import in Resizable component: {line}",
            )

    def test_resizable_wai_aria_separator_semantics(self) -> None:
        """Verify WAI-ARIA separator (splitter) roles and attributes."""
        self.assertIn('role="separator"', self.code)
        self.assertIn('aria-orientation={isHoriz ? "vertical" : "horizontal"}', self.code)
        self.assertIn("aria-valuenow={Math.round(currentPanelSize)}", self.code)
        self.assertIn("aria-valuemin={Math.round(minSize)}", self.code)
        self.assertIn("aria-valuemax={Math.round(maxSize)}", self.code)
        self.assertIn("tabIndex={disabled ? -1 : 0}", self.code)
        self.assertIn("aria-label={ariaLabel", self.code)

    def test_resizable_keyboard_navigation(self) -> None:
        """Verify Arrow, Home, End, and Enter keyboard navigation support."""
        self.assertIn('"ArrowLeft"', self.code)
        self.assertIn('"ArrowRight"', self.code)
        self.assertIn('"ArrowUp"', self.code)
        self.assertIn('"ArrowDown"', self.code)
        self.assertIn('"Home"', self.code)
        self.assertIn('"End"', self.code)
        self.assertIn('"Enter"', self.code)
        self.assertIn("e.shiftKey ? 5 : 1", self.code)

    def test_resizable_pointer_dragging_support(self) -> None:
        """Verify pointerdown, pointer dragging, and window event tracking."""
        self.assertIn("onPointerDown={handlePointerDown}", self.code)
        self.assertIn("startDragging(handleIndexRef.current", self.code)
        self.assertIn("window.addEventListener(\"mousemove\"", self.code)
        self.assertIn("window.addEventListener(\"mouseup\"", self.code)
        self.assertIn("window.addEventListener(\"touchmove\"", self.code)
        self.assertIn("window.addEventListener(\"touchend\"", self.code)

    def test_resizable_min_max_constraints(self) -> None:
        """Verify enforcement of minSize and maxSize."""
        self.assertIn("minSize ?? 10", self.code)
        self.assertIn("maxSize ?? 90", self.code)
        self.assertIn("Math.max(leftMin, Math.min(leftMax", self.code)

    def test_resizable_collapsible_support(self) -> None:
        """Verify collapsible panel toggles and callbacks."""
        self.assertIn("collapsible", self.code)
        self.assertIn("collapsedSize", self.code)
        self.assertIn("onCollapse?.()", self.code)
        self.assertIn("onExpand?.()", self.code)
        self.assertIn("toggleCollapse", self.code)

    def test_resizable_visual_variants(self) -> None:
        """Verify styling presets for neon, glass, bordered, and minimal."""
        self.assertIn("HANDLE_VARIANT_STYLES", self.code)
        self.assertIn("#06b6d4", self.code)  # Neon cyan
        self.assertIn("backdropFilter", self.code)  # Glass blur
        self.assertIn("omnistack-resizable-${variant}", self.code)

    def test_resizable_directions_horizontal_and_vertical(self) -> None:
        """Verify direction-dependent flex layouts and cursor styles."""
        self.assertIn('direction === "horizontal" ? "row" : "column"', self.code)
        self.assertIn('isHoriz ? "col-resize" : "row-resize"', self.code)
        self.assertIn('isHoriz ? "6px" : "100%"', self.code)

    def test_resizable_grip_icons(self) -> None:
        """Verify SVG grip icons for vertical and horizontal handles."""
        self.assertIn("export function GripVerticalIcon()", self.code)
        self.assertIn("export function GripHorizontalIcon()", self.code)
        self.assertIn("omnistack-resizable-grip", self.code)

    def test_resizable_exported_in_codegen_init(self) -> None:
        """Verify render_resizable_component is exported in omnistackai_agent_engine.codegen."""
        self.assertTrue(callable(getattr(cg, "render_resizable_component", None)))
        self.assertIn("render_resizable_component", cg.__all__)

    def test_resizable_emitted_by_adapter(self) -> None:
        """Verify NextjsWebAdapter emits components/resizable.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/resizable.tsx")
        self.assertIsNotNone(f, "components/resizable.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_resizable_diff_invariance(self) -> None:
        """Verify 100% diff-invariance across ApplicationIR description changes."""
        mutated_ir = dataclasses.replace(
            self.ir,
            description="Completely mutated description with unpredictable tokens",
        )
        adapter = NextjsWebAdapter()
        f1 = adapter.generate(self.ir).get("components/resizable.tsx")
        f2 = adapter.generate(mutated_ir).get("components/resizable.tsx")

        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(self.code, f1.content)
        self.assertEqual(f1.content, f2.content)


if __name__ == "__main__":
    unittest.main()

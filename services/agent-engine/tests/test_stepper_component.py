"""Tests for Task R-334: Generated Accessible Reusable Stepper / Multi-step Wizard Component.

Verifies that NextjsWebAdapter emits an accessible, reusable Stepper component
(apps/web/components/stepper.tsx) supporting:
- StepperOrientation, StepStatus, StepperVariant, StepDef, StepperProps types
- Stepper root with horizontal and vertical orientation
- StepIndicator with numeric, checkmark (completed), error X states
- StepConnector between steps
- StepContent tabpanel with aria-labelledby
- useStepperState hook (goNext, goPrev, goTo, canGoNext, canGoPrev)
- WAI-ARIA tablist/tab/tabpanel pattern
- Keyboard navigation: ArrowRight, ArrowLeft, ArrowDown, ArrowUp, Home, End
- Controlled and uncontrolled modes
- 100% diff-invariance across ir.description changes
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_stepper_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class StepperComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_stepper_component()

    def test_stepper_component_is_client_component(self) -> None:
        """Stepper component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_stepper_component_exports_types(self) -> None:
        """Stepper component exports all required types."""
        self.assertIn('export type StepperOrientation = "horizontal" | "vertical";', self.code)
        self.assertIn('export type StepStatus = "idle" | "active" | "completed" | "error";', self.code)
        self.assertIn('export type StepperVariant = "default" | "dots" | "progress";', self.code)
        self.assertIn("export interface StepDef", self.code)
        self.assertIn("export interface StepperProps", self.code)

    def test_stepper_component_exports_functions(self) -> None:
        """Stepper component exports Stepper, StepContent, useStepperState."""
        self.assertIn("export function Stepper(", self.code)
        self.assertIn("export function StepContent(", self.code)
        self.assertIn("export function useStepperState(", self.code)
        self.assertIn("export default Stepper;", self.code)

    def test_stepper_wai_aria_tablist(self) -> None:
        """Stepper implements WAI-ARIA tablist on the step track."""
        self.assertIn('role="tablist"', self.code)
        self.assertIn('aria-orientation={orientation}', self.code)
        self.assertIn('aria-label="Wizard steps"', self.code)

    def test_stepper_wai_aria_tab(self) -> None:
        """Each step header implements WAI-ARIA tab semantics."""
        self.assertIn('role="tab"', self.code)
        self.assertIn("aria-selected={isActive}", self.code)
        self.assertIn("aria-controls={panelId}", self.code)
        self.assertIn("tabIndex={isActive ? 0 : -1}", self.code)

    def test_stepper_wai_aria_tabpanel(self) -> None:
        """StepContent implements WAI-ARIA tabpanel semantics."""
        self.assertIn('role="tabpanel"', self.code)
        self.assertIn("aria-labelledby={tabId}", self.code)
        self.assertIn("hidden={!isActive}", self.code)

    def test_stepper_keyboard_navigation_horizontal(self) -> None:
        """Stepper handles ArrowRight/Left for horizontal navigation."""
        self.assertIn('"ArrowLeft"', self.code)
        self.assertIn('"ArrowRight"', self.code)

    def test_stepper_keyboard_navigation_vertical(self) -> None:
        """Stepper handles ArrowDown/Up for vertical navigation."""
        self.assertIn('"ArrowDown"', self.code)
        self.assertIn('"ArrowUp"', self.code)

    def test_stepper_keyboard_home_end(self) -> None:
        """Stepper handles Home and End keys."""
        self.assertIn('"Home"', self.code)
        self.assertIn('"End"', self.code)

    def test_stepper_navigation_functions(self) -> None:
        """useStepperState provides goNext, goPrev, goTo, canGoNext, canGoPrev."""
        self.assertIn("goNext", self.code)
        self.assertIn("goPrev", self.code)
        self.assertIn("goTo", self.code)
        self.assertIn("canGoNext", self.code)
        self.assertIn("canGoPrev", self.code)

    def test_stepper_controlled_and_uncontrolled(self) -> None:
        """Stepper supports both controlled (value) and uncontrolled (defaultValue) modes."""
        self.assertIn("const isControlled = value !== undefined;", self.code)
        self.assertIn("const active = isControlled ? value : internalActive;", self.code)
        self.assertIn("if (!isControlled) setInternalActive(clamped);", self.code)

    def test_stepper_status_computation(self) -> None:
        """computeStatus resolves idle/active/completed based on index vs activeIndex."""
        self.assertIn('if (stepIndex < activeIndex) return "completed";', self.code)
        self.assertIn('if (stepIndex === activeIndex) return "active";', self.code)
        self.assertIn('return "idle";', self.code)

    def test_stepper_step_variants(self) -> None:
        """Stepper indicator handles dots and default (numeric) variants."""
        self.assertIn('if (variant === "dots")', self.code)
        self.assertIn('omnistackai-step-dot', self.code)
        self.assertIn('omnistackai-step-indicator', self.code)

    def test_stepper_progress_variant_bar(self) -> None:
        """Progress variant renders a progressbar with aria attributes."""
        self.assertIn('role="progressbar"', self.code)
        self.assertIn("aria-valuenow={active + 1}", self.code)
        self.assertIn("aria-valuemax={total}", self.code)
        self.assertIn('aria-label="Step progress"', self.code)

    def test_stepper_emitted_in_generated_app(self) -> None:
        """NextjsWebAdapter includes components/stepper.tsx in generated files."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        stepper_file = project.get("components/stepper.tsx")
        self.assertIsNotNone(stepper_file)

    def test_stepper_content_matches_template(self) -> None:
        """Generated stepper.tsx content exactly matches render_stepper_component()."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        stepper_file = project.get("components/stepper.tsx")
        self.assertIsNotNone(stepper_file)
        self.assertEqual(stepper_file.content, render_stepper_component())

    def test_stepper_diff_invariant(self) -> None:
        """Stepper output is identical regardless of ir.description."""
        ir_b = dataclasses.replace(self.ir, description="Totally different description XYZ 123")
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/stepper.tsx")
        f_b = adapter.generate(ir_b).get("components/stepper.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(f_a.content, f_b.content)

    def test_stepper_zero_external_dependencies(self) -> None:
        """Stepper component uses only React built-ins; no external package imports."""
        lines = [ln for ln in self.code.split("\n") if ln.startswith("import")]
        for line in lines:
            self.assertIn('"react"', line, f"Unexpected import: {line}")

    def test_package_codegen_exports_render_stepper_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_stepper_component."""
        self.assertTrue(callable(cg.render_stepper_component))
        self.assertIn("render_stepper_component", cg.__all__)
        self.assertEqual(cg.render_stepper_component(), self.code)


if __name__ == "__main__":
    unittest.main()

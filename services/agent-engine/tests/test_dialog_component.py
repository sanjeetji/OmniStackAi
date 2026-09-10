"""Tests for Task R-326: Generated Accessible Reusable Dialog / Modal Component.

Verifies that NextjsWebAdapter emits an accessible, reusable compound Dialog / Modal component
(apps/web/components/dialog.tsx) with Dialog, DialogTrigger, DialogPortal, DialogOverlay,
DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogBody, DialogFooter,
DialogClose subcomponents and useDialog hook, supporting WAI-ARIA modal dialog semantics.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_dialog_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class DialogComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_dialog_component()

    def test_dialog_component_is_client_component(self) -> None:
        """Dialog component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_dialog_component_exports_types_and_subcomponents(self) -> None:
        """Dialog component exports types, interfaces, compound subcomponents, and hook."""
        self.assertIn('export type DialogSize = "sm" | "md" | "lg" | "xl" | "full";', self.code)
        self.assertIn("export interface DialogProps", self.code)
        self.assertIn("export interface DialogTriggerProps", self.code)
        self.assertIn("export interface DialogPortalProps", self.code)
        self.assertIn("export interface DialogOverlayProps", self.code)
        self.assertIn("export interface DialogContentProps", self.code)
        self.assertIn("export interface DialogHeaderProps", self.code)
        self.assertIn("export interface DialogTitleProps", self.code)
        self.assertIn("export interface DialogDescriptionProps", self.code)
        self.assertIn("export interface DialogBodyProps", self.code)
        self.assertIn("export interface DialogFooterProps", self.code)
        self.assertIn("export interface DialogCloseProps", self.code)
        self.assertIn("export function Dialog(", self.code)
        self.assertIn("export function DialogTrigger(", self.code)
        self.assertIn("export function DialogPortal(", self.code)
        self.assertIn("export function DialogOverlay(", self.code)
        self.assertIn("export function DialogContent(", self.code)
        self.assertIn("export function DialogHeader(", self.code)
        self.assertIn("export function DialogTitle(", self.code)
        self.assertIn("export function DialogDescription(", self.code)
        self.assertIn("export function DialogBody(", self.code)
        self.assertIn("export function DialogFooter(", self.code)
        self.assertIn("export function DialogClose(", self.code)
        self.assertIn("export function useDialog(", self.code)
        self.assertIn("export default Dialog;", self.code)

    def test_dialog_component_wai_aria_dialog_semantics(self) -> None:
        """Dialog applies role='dialog', aria-modal='true', and dynamic labelling attributes."""
        self.assertIn('role="dialog"', self.code)
        self.assertIn('aria-modal="true"', self.code)
        self.assertIn("aria-labelledby=", self.code)
        self.assertIn("aria-describedby=", self.code)

    def test_dialog_component_supports_sizes(self) -> None:
        """Dialog supports sm, md, lg, xl, full size presets."""
        self.assertIn("sizeMap", self.code)
        self.assertIn("sm:", self.code)
        self.assertIn("md:", self.code)
        self.assertIn("lg:", self.code)
        self.assertIn("xl:", self.code)
        self.assertIn("full:", self.code)

    def test_dialog_component_handles_escape_key(self) -> None:
        """Dialog listens for Escape key to close when open."""
        self.assertIn('e.key === "Escape"', self.code)
        self.assertIn("closeOnEscape", self.code)

    def test_dialog_component_handles_backdrop_click(self) -> None:
        """Dialog supports backdrop overlay click to close."""
        self.assertIn("closeOnBackdropClick", self.code)
        self.assertIn("DialogOverlay", self.code)

    def test_dialog_component_accessible_close_button(self) -> None:
        """Dialog provides an accessible close button with aria-label."""
        self.assertIn('aria-label="Close dialog"', self.code)
        self.assertIn("showCloseButton", self.code)

    def test_dialog_component_manages_focus_and_scroll_lock(self) -> None:
        """Dialog locks document.body scroll and returns focus on close."""
        self.assertIn('document.body.style.overflow = "hidden"', self.code)
        self.assertIn("triggerRef", self.code)

    def test_dialog_component_supports_uncontrolled_and_controlled(self) -> None:
        """Dialog supports both controlled (open, onOpenChange) and uncontrolled (defaultOpen) usage."""
        self.assertIn("defaultOpen", self.code)
        self.assertIn("onOpenChange", self.code)

    def test_dialog_context_and_hook(self) -> None:
        """Dialog provides DialogContext and useDialog hook."""
        self.assertIn("DialogContext = createContext", self.code)
        self.assertIn("export function useDialog()", self.code)

    def test_codegen_module_exports_render_dialog_component(self) -> None:
        """render_dialog_component is exported from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_dialog_component"))
        self.assertEqual(cg.render_dialog_component(), self.code)

    def test_adapter_generate_registers_dialog_component(self) -> None:
        """NextjsWebAdapter.generate outputs components/dialog.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/dialog.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        """render_dialog_component is 100% diff-invariant across changes to ir.description."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-326")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/dialog.tsx")
        p2 = adapter.generate(ir2).get("components/dialog.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()

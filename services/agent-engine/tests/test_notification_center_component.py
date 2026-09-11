"""Tests for Task R-361: Generated Accessible Futuristic Reusable Notification Center Suite.

Verifies that NextjsWebAdapter emits an accessible, desktop-grade, zero-dependency, and futuristic
Notification Center & Notification List compound component suite
(apps/web/components/notification-center.tsx) supporting:
- WAI-ARIA dialog panel:
  - Panel: role="dialog", aria-modal="true", aria-label (panel title)
  - Notification list: role="list", aria-label="Notification list"
  - Each row: role="listitem", data-read, data-severity
- Bell trigger button:
  - aria-haspopup="dialog", aria-expanded, aria-controls
  - aria-label="Notifications, N unread" dynamic label
  - Unread badge count (capped at 99+), aria-hidden badge
- Item actions:
  - "Mark as read" button: aria-label="Mark as read"
  - "Dismiss notification" button: aria-label="Dismiss notification"
  - "Close notifications" close button: aria-label="Close notifications"
- Keyboard:
  - Escape closes panel and returns focus to trigger
- Notification item features:
  - title, description, timestamp (relativeTime helper, <time dateTime>)
  - severity: info | success | warning | error (dot color + bg tint)
  - read state (bold vs normal weight, transparent vs tinted background)
  - avatar: string URL or ReactNode slot
  - href: renders item as anchor
  - action: inline button slot
- Control actions:
  - "Mark all read" button (when onMarkAllRead provided + unread > 0)
  - "Clear all" button (when onClearAll provided + items exist)
- Empty state ("No notifications")
- Footer count ("N notification(s)")
- Placement prop: bottom-start | bottom-end | top-start | top-end
- 4 futuristic visual variants ("default", "card", "glass", "neon")
- 3 size scales ("sm", "md", "lg") with responsive panel widths
- Slide-in animation (nc-panel-in keyframe)
- Controlled and uncontrolled open modes
- maxHeight prop for scrollable list
- Custom trigger prop
- React ref forwarding (forwardRef) and explicit displayName
- 100% diff-invariance across ir.description changes
- Zero external runtime npm dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_notification_center_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class NotificationCenterComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the NotificationCenter component suite."""

    def setUp(self) -> None:
        self.code = render_notification_center_component()
        self.ir = example_ir("rideshare-favourites")

    # ------------------------------------------------------------------
    # Basic structure
    # ------------------------------------------------------------------

    def test_notification_center_is_client_component(self) -> None:
        """NotificationCenter must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "NotificationCenter must have 'use client' as the first statement.",
        )

    def test_notification_center_exports_types(self) -> None:
        """Verify export of TypeScript union types and interfaces."""
        self.assertIn("export type NotificationCenterVariant", self.code)
        self.assertIn('"default"', self.code)
        self.assertIn('"card"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn("export type NotificationCenterSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export type NotificationSeverity", self.code)
        self.assertIn('"info"', self.code)
        self.assertIn('"success"', self.code)
        self.assertIn('"warning"', self.code)
        self.assertIn('"error"', self.code)
        self.assertIn("export interface NotificationItem", self.code)
        self.assertIn("export interface NotificationCenterProps", self.code)

    def test_notification_center_exports_component_and_display_name(self) -> None:
        """Verify NotificationCenter export, forwardRef, displayName, and default export."""
        self.assertIn("export const NotificationCenter = forwardRef", self.code)
        self.assertIn('NotificationCenter.displayName = "NotificationCenter";', self.code)
        self.assertIn("export default NotificationCenter;", self.code)

    # ------------------------------------------------------------------
    # WAI-ARIA dialog
    # ------------------------------------------------------------------

    def test_notification_center_panel_role_dialog(self) -> None:
        """Panel must carry role=dialog."""
        self.assertIn('role="dialog"', self.code)

    def test_notification_center_panel_aria_modal(self) -> None:
        """Panel must have aria-modal=true."""
        self.assertIn('aria-modal="true"', self.code)

    def test_notification_center_panel_aria_label(self) -> None:
        """Panel must have aria-label bound to title prop."""
        self.assertIn("aria-label={title}", self.code)

    def test_notification_center_list_role(self) -> None:
        """Notification list container must have role=list."""
        self.assertIn('role="list"', self.code)
        self.assertIn('aria-label="Notification list"', self.code)

    def test_notification_center_item_role_listitem(self) -> None:
        """Each notification row must carry role=listitem."""
        self.assertIn('role="listitem"', self.code)

    def test_notification_center_item_data_attributes(self) -> None:
        """Notification rows must expose data-read and data-severity attributes."""
        self.assertIn("data-read={", self.code)
        self.assertIn("data-severity={sev}", self.code)

    # ------------------------------------------------------------------
    # Bell trigger
    # ------------------------------------------------------------------

    def test_notification_center_trigger_aria_haspopup(self) -> None:
        """Bell trigger must have aria-haspopup=dialog."""
        self.assertIn('aria-haspopup="dialog"', self.code)

    def test_notification_center_trigger_aria_expanded(self) -> None:
        """Bell trigger must reflect aria-expanded state."""
        self.assertIn("aria-expanded={isOpen}", self.code)

    def test_notification_center_trigger_aria_controls(self) -> None:
        """Bell trigger must link to panel via aria-controls."""
        self.assertIn("aria-controls={", self.code)
        self.assertIn("panelId", self.code)

    def test_notification_center_trigger_aria_label_dynamic(self) -> None:
        """Bell trigger aria-label must include unread count when non-zero."""
        self.assertIn("unread", self.code)
        self.assertIn("Notifications", self.code)

    def test_notification_center_unread_badge(self) -> None:
        """Unread badge must be rendered with aria-hidden and 99+ cap."""
        self.assertIn("unreadCount", self.code)
        self.assertIn('"99+"', self.code)
        self.assertIn('aria-hidden="true"', self.code)

    def test_notification_center_bell_icon(self) -> None:
        """Bell SVG icon must be included."""
        self.assertIn("BellIcon", self.code)

    # ------------------------------------------------------------------
    # Item action buttons
    # ------------------------------------------------------------------

    def test_notification_center_mark_as_read_button(self) -> None:
        """Mark-as-read button must have aria-label='Mark as read'."""
        self.assertIn('aria-label="Mark as read"', self.code)
        self.assertIn("CheckIcon", self.code)

    def test_notification_center_dismiss_button(self) -> None:
        """Dismiss button must have aria-label='Dismiss notification'."""
        self.assertIn('aria-label="Dismiss notification"', self.code)

    def test_notification_center_close_button(self) -> None:
        """Close button must have aria-label='Close notifications'."""
        self.assertIn('aria-label="Close notifications"', self.code)

    # ------------------------------------------------------------------
    # Keyboard navigation
    # ------------------------------------------------------------------

    def test_notification_center_escape_closes(self) -> None:
        """Escape key must close the panel."""
        self.assertIn('"Escape"', self.code)
        self.assertIn("close()", self.code)

    def test_notification_center_focus_trap_return(self) -> None:
        """On Escape, focus must be returned to the trigger."""
        self.assertIn("triggerRef.current?.focus()", self.code)

    # ------------------------------------------------------------------
    # Notification item features
    # ------------------------------------------------------------------

    def test_notification_center_timestamp_relative_time(self) -> None:
        """relativeTime helper must produce human-readable relative strings."""
        self.assertIn("function relativeTime(", self.code)
        self.assertIn('"just now"', self.code)
        self.assertIn("m ago", self.code)
        self.assertIn("h ago", self.code)
        self.assertIn("d ago", self.code)

    def test_notification_center_timestamp_time_element(self) -> None:
        """Timestamp must be rendered in a <time dateTime> element."""
        self.assertIn("dateTime={item.timestamp}", self.code)

    def test_notification_center_severity_colors(self) -> None:
        """Severity color map must cover all four levels."""
        self.assertIn("SEVERITY_COLOR", self.code)
        self.assertIn('"#3b82f6"', self.code)   # info
        self.assertIn('"#22c55e"', self.code)   # success
        self.assertIn('"#f59e0b"', self.code)   # warning
        self.assertIn('"#ef4444"', self.code)   # error

    def test_notification_center_severity_bg_tints(self) -> None:
        """Unread items must have a tinted severity background."""
        self.assertIn("SEVERITY_BG", self.code)
        self.assertIn("rgba(59,130,246,0.10)", self.code)

    def test_notification_center_avatar_slot(self) -> None:
        """Avatar must support both string URL (img) and ReactNode."""
        self.assertIn("item.avatar", self.code)
        self.assertIn('typeof item.avatar === "string"', self.code)

    def test_notification_center_href_anchor(self) -> None:
        """When href is set the item must render as an anchor."""
        self.assertIn("item.href", self.code)
        self.assertIn("<a href={item.href}", self.code)

    def test_notification_center_action_slot(self) -> None:
        """Item action button slot must be rendered."""
        self.assertIn("item.action", self.code)
        self.assertIn("item.action.label", self.code)
        self.assertIn("item.action.onClick", self.code)

    # ------------------------------------------------------------------
    # Header actions
    # ------------------------------------------------------------------

    def test_notification_center_mark_all_read(self) -> None:
        """Mark all read button must render when onMarkAllRead is provided."""
        self.assertIn("onMarkAllRead", self.code)
        self.assertIn("Mark all read", self.code)

    def test_notification_center_clear_all(self) -> None:
        """Clear all button must render when onClearAll is provided."""
        self.assertIn("onClearAll", self.code)
        self.assertIn("Clear all", self.code)

    # ------------------------------------------------------------------
    # Empty state & footer
    # ------------------------------------------------------------------

    def test_notification_center_empty_state(self) -> None:
        """Empty state message must appear when no notifications exist."""
        self.assertIn("No notifications", self.code)

    def test_notification_center_footer_count(self) -> None:
        """Footer must display total notification count."""
        self.assertIn("notification", self.code)
        self.assertIn("notifications.length", self.code)

    # ------------------------------------------------------------------
    # Placement
    # ------------------------------------------------------------------

    def test_notification_center_placement_variants(self) -> None:
        """All four placement options must be handled."""
        self.assertIn('"bottom-start"', self.code)
        self.assertIn('"bottom-end"', self.code)
        self.assertIn('"top-start"', self.code)
        self.assertIn('"top-end"', self.code)
        self.assertIn("placementStyle", self.code)

    # ------------------------------------------------------------------
    # Visual variants
    # ------------------------------------------------------------------

    def test_notification_center_glass_variant(self) -> None:
        """Glass variant must use backdropFilter blur."""
        self.assertIn("backdropFilter", self.code)
        self.assertIn("rgba(255,255,255,0.80)", self.code)

    def test_notification_center_neon_variant(self) -> None:
        """Neon variant must use cyan glow and dark background."""
        self.assertIn("rgba(56,189,248,0.3)", self.code)
        self.assertIn("rgba(9,13,22,0.98)", self.code)

    # ------------------------------------------------------------------
    # Size scales
    # ------------------------------------------------------------------

    def test_notification_center_size_sm(self) -> None:
        """sm size must set panel width to 320px."""
        self.assertIn('"320px"', self.code)

    def test_notification_center_size_md(self) -> None:
        """md size must set panel width to 380px."""
        self.assertIn('"380px"', self.code)

    def test_notification_center_size_lg(self) -> None:
        """lg size must set panel width to 440px."""
        self.assertIn('"440px"', self.code)

    # ------------------------------------------------------------------
    # Animation
    # ------------------------------------------------------------------

    def test_notification_center_slide_in_animation(self) -> None:
        """Panel must include the nc-panel-in keyframe animation."""
        self.assertIn("nc-panel-in", self.code)
        self.assertIn("@keyframes nc-panel-in", self.code)

    # ------------------------------------------------------------------
    # Controlled / uncontrolled
    # ------------------------------------------------------------------

    def test_notification_center_controlled_and_uncontrolled(self) -> None:
        """Controlled and uncontrolled open modes must coexist."""
        self.assertIn("isControlled", self.code)
        self.assertIn("controlledOpen", self.code)
        self.assertIn("internalOpen", self.code)
        self.assertIn("setInternalOpen", self.code)

    # ------------------------------------------------------------------
    # Outside-click and escape handling
    # ------------------------------------------------------------------

    def test_notification_center_outside_click_close(self) -> None:
        """Clicking outside the panel must close it."""
        self.assertIn("mousedown", self.code)
        self.assertIn("panelRef.current", self.code)

    # ------------------------------------------------------------------
    # Zero external dependencies
    # ------------------------------------------------------------------

    def test_notification_center_zero_runtime_dependencies(self) -> None:
        """NotificationCenter template must not import external third-party libraries."""
        lines = [
            line.strip()
            for line in self.code.split("\n")
            if line.strip().startswith("import ")
        ]
        for line in lines:
            self.assertTrue(
                line.startswith("import React") or 'from "react"' in line,
                f"Unexpected external import detected: {line}",
            )

    # ------------------------------------------------------------------
    # Adapter wiring
    # ------------------------------------------------------------------

    def test_notification_center_adapter_emits_file(self) -> None:
        """NextjsWebAdapter must emit components/notification-center.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/notification-center.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_notification_center_exported_from_codegen_package(self) -> None:
        """cg.render_notification_center_component must be exposed at package root."""
        self.assertTrue(callable(cg.render_notification_center_component))
        self.assertEqual(cg.render_notification_center_component(), self.code)

    # ------------------------------------------------------------------
    # Diff invariance
    # ------------------------------------------------------------------

    def test_notification_center_diff_invariance(self) -> None:
        """Diff invariance: changing ir.description must not alter components/notification-center.tsx."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        f1 = project1.get("components/notification-center.tsx")

        ir_mutated = dataclasses.replace(
            self.ir,
            description="Completely different description for diff invariance test",
        )
        project2 = adapter.generate(ir_mutated)
        f2 = project2.get("components/notification-center.tsx")

        self.assertEqual(f1.content, f2.content)


if __name__ == "__main__":
    unittest.main()

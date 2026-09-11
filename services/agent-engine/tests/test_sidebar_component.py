"""Tests for Task R-362: Generated Accessible Futuristic Reusable Sidebar Suite.

Verifies that NextjsWebAdapter emits an accessible, desktop-and-mobile-grade, zero-dependency,
and futuristic Sidebar & Side Navigation compound component suite (apps/web/components/sidebar.tsx) supporting:
- Compound subcomponents:
  - Sidebar (root navigation landmark)
  - SidebarHeader, SidebarContent, SidebarFooter
  - SidebarGroup, SidebarGroupLabel, SidebarGroupContent
  - SidebarMenu, SidebarMenuItem, SidebarMenuButton, SidebarMenuBadge
  - SidebarMenuSub, SidebarMenuSubItem, SidebarMenuSubButton
  - SidebarRail, SidebarTrigger, SidebarToggle, SideNav
- WAI-ARIA 1.2 navigation landmark and menu semantics:
  - Root <aside role="navigation"> with aria-label
  - Menu list <ul role="menu">, item <li role="none">
  - Button <button role="menuitem"> with aria-current="page" when active
  - Trigger <button aria-label="Toggle Sidebar" aria-expanded={open}>
- Keyboard navigation:
  - ArrowDown / ArrowUp item traversal with wrap-around
  - Home / End jump navigation
- Collapsible modes:
  - "icon" (collapses to icon rail width with tooltips)
  - "offcanvas" (slides offscreen with mobile backdrop)
  - "none" (fixed width)
- 4 futuristic visual styling variants ("default", "card", "glass", "neon")
- 3 size scales ("sm", "md", "lg") with responsive widths and heights
- Built-in SVG vector icons (PanelLeftIcon, ChevronRightIcon, ChevronLeftIcon, ChevronDownIcon, MenuIcon)
- Controlled and uncontrolled collapse modes
- React ref forwarding (forwardRef) and explicit displayName on all subcomponents
- 100% diff-invariance across ir.description changes
- Zero external runtime npm dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_sidebar_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class SidebarComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the Sidebar component suite."""

    def setUp(self) -> None:
        self.code = render_sidebar_component()
        self.ir = example_ir("rideshare-favourites")

    # ------------------------------------------------------------------
    # Basic structure
    # ------------------------------------------------------------------

    def test_sidebar_is_client_component(self) -> None:
        """Sidebar must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "Sidebar must have 'use client' as the first statement.",
        )

    def test_sidebar_exports_types(self) -> None:
        """Verify export of TypeScript union types and interfaces."""
        self.assertIn("export type SidebarVariant", self.code)
        self.assertIn('"default"', self.code)
        self.assertIn('"card"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"neon"', self.code)

        self.assertIn("export type SidebarSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)

        self.assertIn("export type SidebarCollapsible", self.code)
        self.assertIn('"icon"', self.code)
        self.assertIn('"offcanvas"', self.code)
        self.assertIn('"none"', self.code)

        self.assertIn("export type SidebarSide", self.code)
        self.assertIn('"left"', self.code)
        self.assertIn('"right"', self.code)

        self.assertIn("export type SidebarState", self.code)
        self.assertIn('"expanded"', self.code)
        self.assertIn('"collapsed"', self.code)

        self.assertIn("export interface SidebarContextValue", self.code)
        self.assertIn("export interface SidebarProps", self.code)
        self.assertIn("export interface SidebarHeaderProps", self.code)
        self.assertIn("export interface SidebarContentProps", self.code)
        self.assertIn("export interface SidebarFooterProps", self.code)
        self.assertIn("export interface SidebarGroupProps", self.code)
        self.assertIn("export interface SidebarGroupLabelProps", self.code)
        self.assertIn("export interface SidebarGroupContentProps", self.code)
        self.assertIn("export interface SidebarMenuProps", self.code)
        self.assertIn("export interface SidebarMenuItemProps", self.code)
        self.assertIn("export interface SidebarMenuButtonProps", self.code)
        self.assertIn("export interface SidebarMenuBadgeProps", self.code)
        self.assertIn("export interface SidebarMenuSubProps", self.code)
        self.assertIn("export interface SidebarMenuSubItemProps", self.code)
        self.assertIn("export interface SidebarMenuSubButtonProps", self.code)
        self.assertIn("export interface SidebarRailProps", self.code)
        self.assertIn("export interface SidebarTriggerProps", self.code)

    def test_sidebar_exports_components_and_display_name(self) -> None:
        """Verify all subcomponent exports, forwardRef, displayName, and default export."""
        self.assertIn("export const Sidebar = forwardRef", self.code)
        self.assertIn('Sidebar.displayName = "Sidebar";', self.code)

        self.assertIn("export const SidebarHeader = forwardRef", self.code)
        self.assertIn('SidebarHeader.displayName = "SidebarHeader";', self.code)

        self.assertIn("export const SidebarContent = forwardRef", self.code)
        self.assertIn('SidebarContent.displayName = "SidebarContent";', self.code)

        self.assertIn("export const SidebarFooter = forwardRef", self.code)
        self.assertIn('SidebarFooter.displayName = "SidebarFooter";', self.code)

        self.assertIn("export const SidebarGroup = forwardRef", self.code)
        self.assertIn('SidebarGroup.displayName = "SidebarGroup";', self.code)

        self.assertIn("export const SidebarGroupLabel = forwardRef", self.code)
        self.assertIn('SidebarGroupLabel.displayName = "SidebarGroupLabel";', self.code)

        self.assertIn("export const SidebarGroupContent = forwardRef", self.code)
        self.assertIn('SidebarGroupContent.displayName = "SidebarGroupContent";', self.code)

        self.assertIn("export const SidebarMenu = forwardRef", self.code)
        self.assertIn('SidebarMenu.displayName = "SidebarMenu";', self.code)

        self.assertIn("export const SidebarMenuItem = forwardRef", self.code)
        self.assertIn('SidebarMenuItem.displayName = "SidebarMenuItem";', self.code)

        self.assertIn("export const SidebarMenuButton = forwardRef", self.code)
        self.assertIn('SidebarMenuButton.displayName = "SidebarMenuButton";', self.code)

        self.assertIn("export const SidebarMenuBadge = forwardRef", self.code)
        self.assertIn('SidebarMenuBadge.displayName = "SidebarMenuBadge";', self.code)

        self.assertIn("export const SidebarMenuSub = forwardRef", self.code)
        self.assertIn('SidebarMenuSub.displayName = "SidebarMenuSub";', self.code)

        self.assertIn("export const SidebarMenuSubItem = forwardRef", self.code)
        self.assertIn('SidebarMenuSubItem.displayName = "SidebarMenuSubItem";', self.code)

        self.assertIn("export const SidebarMenuSubButton = forwardRef", self.code)
        self.assertIn('SidebarMenuSubButton.displayName = "SidebarMenuSubButton";', self.code)

        self.assertIn("export const SidebarRail = forwardRef", self.code)
        self.assertIn('SidebarRail.displayName = "SidebarRail";', self.code)

        self.assertIn("export const SidebarTrigger = forwardRef", self.code)
        self.assertIn('SidebarTrigger.displayName = "SidebarTrigger";', self.code)

        self.assertIn("export const SidebarToggle = SidebarTrigger;", self.code)
        self.assertIn('SidebarToggle.displayName = "SidebarToggle";', self.code)

        self.assertIn("export const SideNav = Sidebar;", self.code)
        self.assertIn('SideNav.displayName = "SideNav";', self.code)

        self.assertIn("export default Sidebar;", self.code)

    def test_sidebar_compound_attachments(self) -> None:
        """Verify compound subcomponent property attachments."""
        self.assertIn("(Sidebar as any).Header = SidebarHeader;", self.code)
        self.assertIn("(Sidebar as any).Content = SidebarContent;", self.code)
        self.assertIn("(Sidebar as any).Footer = SidebarFooter;", self.code)
        self.assertIn("(Sidebar as any).Group = SidebarGroup;", self.code)
        self.assertIn("(Sidebar as any).GroupLabel = SidebarGroupLabel;", self.code)
        self.assertIn("(Sidebar as any).GroupContent = SidebarGroupContent;", self.code)
        self.assertIn("(Sidebar as any).Menu = SidebarMenu;", self.code)
        self.assertIn("(Sidebar as any).MenuItem = SidebarMenuItem;", self.code)
        self.assertIn("(Sidebar as any).MenuButton = SidebarMenuButton;", self.code)
        self.assertIn("(Sidebar as any).MenuBadge = SidebarMenuBadge;", self.code)
        self.assertIn("(Sidebar as any).MenuSub = SidebarMenuSub;", self.code)
        self.assertIn("(Sidebar as any).MenuSubItem = SidebarMenuSubItem;", self.code)
        self.assertIn("(Sidebar as any).MenuSubButton = SidebarMenuSubButton;", self.code)
        self.assertIn("(Sidebar as any).Rail = SidebarRail;", self.code)
        self.assertIn("(Sidebar as any).Trigger = SidebarTrigger;", self.code)
        self.assertIn("(Sidebar as any).Toggle = SidebarToggle;", self.code)

    # ------------------------------------------------------------------
    # Context & Hook
    # ------------------------------------------------------------------

    def test_sidebar_context_and_hook(self) -> None:
        """Verify SidebarContext and useSidebar custom hook."""
        self.assertIn("export const SidebarContext = createContext", self.code)
        self.assertIn("export function useSidebar(): SidebarContextValue", self.code)
        self.assertIn("useSidebar must be used within a <Sidebar /> component.", self.code)

    # ------------------------------------------------------------------
    # WAI-ARIA and Semantics
    # ------------------------------------------------------------------

    def test_sidebar_navigation_landmark(self) -> None:
        """Root element must be an aside with role='navigation' and aria-label."""
        self.assertIn("<aside", self.code)
        self.assertIn('role="navigation"', self.code)
        self.assertIn("aria-label={ariaLabel}", self.code)

    def test_sidebar_menu_roles(self) -> None:
        """Verify menu semantics on list, item, and button."""
        self.assertIn('role="menu"', self.code)
        self.assertIn('role="none"', self.code)
        self.assertIn('role="menuitem"', self.code)

    def test_sidebar_menu_button_active_aria(self) -> None:
        """Active button must carry aria-current='page' and data-active."""
        self.assertIn('aria-current={isActive ? "page" : undefined}', self.code)
        self.assertIn("data-active={isActive}", self.code)

    def test_sidebar_trigger_aria(self) -> None:
        """Trigger button must provide aria-label and aria-expanded."""
        self.assertIn('aria-label="Toggle Sidebar"', self.code)
        self.assertIn("aria-expanded={open}", self.code)

    # ------------------------------------------------------------------
    # Keyboard Navigation
    # ------------------------------------------------------------------

    def test_sidebar_keyboard_navigation(self) -> None:
        """Menu must handle ArrowDown, ArrowUp, Home, and End key events."""
        self.assertIn('e.key === "ArrowDown"', self.code)
        self.assertIn('e.key === "ArrowUp"', self.code)
        self.assertIn('e.key === "Home"', self.code)
        self.assertIn('e.key === "End"', self.code)
        self.assertIn("e.preventDefault()", self.code)

    # ------------------------------------------------------------------
    # Visual Variants and Sizes
    # ------------------------------------------------------------------

    def test_sidebar_variant_styles(self) -> None:
        """Verify variant resolution for card, glass, neon, and default."""
        self.assertIn("getSidebarStyles", self.code)
        self.assertIn('"#1e293b"', self.code)
        self.assertIn('"rgba(15, 23, 42, 0.75)"', self.code)
        self.assertIn('backdropFilter: "blur(16px)"', self.code)
        self.assertIn('"#030712"', self.code)
        self.assertIn("rgba(6, 182, 212, 0.35)", self.code)

    def test_sidebar_size_presets(self) -> None:
        """Verify dimension definitions for sm, md, and lg sizes."""
        self.assertIn("SIDEBAR_SIZES", self.code)
        self.assertIn("expanded: 220", self.code)
        self.assertIn("collapsed: 56", self.code)
        self.assertIn("expanded: 260", self.code)
        self.assertIn("collapsed: 64", self.code)
        self.assertIn("expanded: 300", self.code)
        self.assertIn("collapsed: 72", self.code)

    # ------------------------------------------------------------------
    # Collapsible & Offcanvas
    # ------------------------------------------------------------------

    def test_sidebar_collapsible_modes(self) -> None:
        """Verify icon rail and offcanvas collapsible modes."""
        self.assertIn('collapsible === "icon"', self.code)
        self.assertIn('collapsible === "offcanvas"', self.code)
        self.assertIn("data-collapsible={collapsible}", self.code)

    def test_sidebar_mobile_backdrop(self) -> None:
        """Mobile open view must display backdrop overlay with click dismiss."""
        self.assertIn("isMobile && openMobile", self.code)
        self.assertIn("onClick={() => setOpenMobile(false)}", self.code)

    def test_sidebar_submenus(self) -> None:
        """Verify submenus hide when collapsed to icon rail."""
        self.assertIn(
            'isIconCollapsed = collapsible === "icon" && state === "collapsed"',
            self.code,
        )
        self.assertIn('data-sidebar="menu-sub"', self.code)

    # ------------------------------------------------------------------
    # Vector Icons
    # ------------------------------------------------------------------

    def test_sidebar_vector_icons(self) -> None:
        """Verify inline vector icons for panel toggle and arrows."""
        self.assertIn("function PanelLeftIcon", self.code)
        self.assertIn("function ChevronRightIcon", self.code)
        self.assertIn("function ChevronLeftIcon", self.code)
        self.assertIn("function ChevronDownIcon", self.code)
        self.assertIn("function MenuIcon", self.code)

    # ------------------------------------------------------------------
    # Codegen & Adapter integration
    # ------------------------------------------------------------------

    def test_adapter_emits_sidebar_file(self) -> None:
        """NextjsWebAdapter emits components/sidebar.tsx in generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/sidebar.tsx")
        self.assertIsNotNone(f, "components/sidebar.tsx must be emitted")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_sidebar_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_sidebar_component."""
        self.assertTrue(
            hasattr(cg, "render_sidebar_component"),
            "render_sidebar_component must be exported from codegen package",
        )
        self.assertIn("render_sidebar_component", cg.__all__)
        self.assertTrue(callable(cg.render_sidebar_component))
        self.assertEqual(cg.render_sidebar_component(), self.code)

    def test_sidebar_zero_external_dependencies(self) -> None:
        """Sidebar uses only React; zero external package imports."""
        modules = re.findall(r'from\s+"([^"]+)"', self.code)
        for mod in modules:
            self.assertEqual(mod, "react", f"Unexpected external import: {mod}")

    def test_sidebar_diff_invariant(self) -> None:
        """Sidebar output is 100% diff-invariant across ir.description changes."""
        modified_ir = dataclasses.replace(
            self.ir,
            description="Completely different prompt description for diff invariance test",
        )
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/sidebar.tsx")
        f_b = adapter.generate(modified_ir).get("components/sidebar.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(
            f_a.content,
            f_b.content,
            "components/sidebar.tsx must be 100% diff-invariant across ir.description changes",
        )

    # ------------------------------------------------------------------
    # Data Attributes & Subcomponent Slots
    # ------------------------------------------------------------------

    def test_sidebar_data_attributes(self) -> None:
        """Verify data-* attributes on sidebar sections for testing and styling."""
        self.assertIn('data-sidebar="header"', self.code)
        self.assertIn('data-sidebar="content"', self.code)
        self.assertIn('data-sidebar="footer"', self.code)
        self.assertIn('data-sidebar="group"', self.code)
        self.assertIn('data-sidebar="group-label"', self.code)
        self.assertIn('data-sidebar="group-content"', self.code)
        self.assertIn('data-sidebar="menu"', self.code)
        self.assertIn('data-sidebar="menu-item"', self.code)
        self.assertIn('data-sidebar="menu-button"', self.code)
        self.assertIn('data-sidebar="menu-icon"', self.code)
        self.assertIn('data-sidebar="menu-text"', self.code)
        self.assertIn('data-sidebar="menu-badge"', self.code)
        self.assertIn('data-sidebar="menu-sub"', self.code)
        self.assertIn('data-sidebar="menu-sub-item"', self.code)
        self.assertIn('data-sidebar="menu-sub-button"', self.code)
        self.assertIn('data-sidebar="rail"', self.code)
        self.assertIn('data-sidebar="trigger"', self.code)

    def test_sidebar_controlled_and_uncontrolled(self) -> None:
        """Verify support for both controlled (collapsed) and uncontrolled (defaultCollapsed) modes."""
        self.assertIn("defaultCollapsed = false", self.code)
        self.assertIn("collapsed: controlledCollapsed", self.code)
        self.assertIn("onCollapseChange", self.code)
        self.assertIn("controlledCollapsed !== undefined ? controlledCollapsed : uncontrolledCollapsed", self.code)

    def test_sidebar_tooltip_and_title_in_collapsed_mode(self) -> None:
        """Verify collapsed icon button fallback to tooltip or title."""
        self.assertIn("isIconCollapsed ? (tooltip || title || (typeof children === \"string\" ? children : undefined)) : title", self.code)

    def test_sidebar_right_side_positioning(self) -> None:
        """Verify support for right side navigation."""
        self.assertIn('side === "left" ? "translateX(-100%)" : "translateX(100%)"', self.code)
        self.assertIn('[side]: 0', self.code)

    def test_sidebar_aliases(self) -> None:
        """Verify semantic aliases SideNav and SidebarToggle."""
        self.assertIn("export const SideNav = Sidebar;", self.code)
        self.assertIn('SideNav.displayName = "SideNav";', self.code)
        self.assertIn("export const SidebarToggle = SidebarTrigger;", self.code)
        self.assertIn('SidebarToggle.displayName = "SidebarToggle";', self.code)

    def test_sidebar_resize_listener(self) -> None:
        """Verify window resize listener for mobile responsiveness."""
        self.assertIn('window.addEventListener("resize", checkMobile);', self.code)
        self.assertIn('window.removeEventListener("resize", checkMobile);', self.code)


if __name__ == "__main__":
    unittest.main()

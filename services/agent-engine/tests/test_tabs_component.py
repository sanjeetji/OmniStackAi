"""Task R-310: Generated Accessible Reusable Tabs Component (components/tabs.tsx).

Tests for:
1. Reusable Tabs and TabPanel components structure, TypeScript props interfaces, and exports.
2. WAI-ARIA 1.2 Tabs pattern compliance:
   - role="tablist" container with aria-label
   - role="tab" with aria-selected, aria-controls, id, and roving tabIndex
   - role="tabpanel" with aria-labelledby, id, and hidden attribute
3. Full keyboard navigation (ArrowRight, ArrowLeft, Home, End).
4. Variants support: "line" and "pills".
5. Count badge display for tabs with counts.
6. Export in omnistackai_agent_engine.codegen.
7. Registration in NextjsWebAdapter.generate() at components/tabs.tsx.
8. Diff invariance across ir.description changes.
9. Full project generation across example IR fixtures.
"""

from __future__ import annotations

import unittest

from omnistackai_agent_engine.application_ir import (
    AdminStrategy,
    ApiEndpoint,
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    MobileProfile,
    Platform,
    ProjectStrategy,
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import (
    render_tabs_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)

_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.GO,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _make_test_ir(description: str = "Test Blog Application") -> ApplicationIR:
    entities = (
        Entity(
            "Post",
            (
                Field("id", FieldType.STRING, required=True),
                Field("title", FieldType.STRING, required=True),
            ),
        ),
    )
    screens = (
        Screen("posts", "member", components=("list", "table")),
    )
    endpoints = (
        ApiEndpoint(HttpMethod.GET, "/posts", False, response_schema="Post"),
    )
    roles = (
        Role("member", ("read", "write")),
    )
    return ApplicationIR(
        name="TestApp",
        description=description,
        platforms=(Platform.WEB,),
        project_strategy=_STRATEGY,
        roles=roles,
        entities=entities,
        screens=screens,
        apis=endpoints,
    )


class TabsComponentUnitTests(unittest.TestCase):
    """Unit tests for render_tabs_component()."""

    def setUp(self) -> None:
        self.code = render_tabs_component()

    def test_client_component_directive(self) -> None:
        self.assertTrue(self.code.startswith('"use client";'))

    def test_exports_interfaces_and_components(self) -> None:
        self.assertIn("export interface TabItem", self.code)
        self.assertIn("export interface TabsProps", self.code)
        self.assertIn("export interface TabPanelProps", self.code)
        self.assertIn("export function Tabs(", self.code)
        self.assertIn("export function TabPanel(", self.code)

    def test_props_interface_fields(self) -> None:
        self.assertIn("id: string;", self.code)
        self.assertIn("label: string;", self.code)
        self.assertIn("count?: number;", self.code)
        self.assertIn("disabled?: boolean;", self.code)
        self.assertIn("tabs: TabItem[];", self.code)
        self.assertIn("activeTab: string;", self.code)
        self.assertIn("onChange: (id: string) => void;", self.code)
        self.assertIn('variant?: "line" | "pills";', self.code)

    def test_wai_aria_compliance(self) -> None:
        self.assertIn('role="tablist"', self.code)
        self.assertIn('role="tab"', self.code)
        self.assertIn('aria-selected={isActive}', self.code)
        self.assertIn("aria-controls={`tabpanel-${tab.id}`}", self.code)
        self.assertIn("id={`tab-${tab.id}`}", self.code)
        self.assertIn('tabIndex={isActive ? 0 : -1}', self.code)
        self.assertIn('role="tabpanel"', self.code)
        self.assertIn("aria-labelledby={`tab-${id}`}", self.code)
        self.assertIn("id={`tabpanel-${id}`}", self.code)
        self.assertIn("hidden={activeTab !== id}", self.code)

    def test_keyboard_navigation(self) -> None:
        self.assertIn('e.key === "ArrowRight"', self.code)
        self.assertIn('e.key === "ArrowLeft"', self.code)
        self.assertIn('e.key === "Home"', self.code)
        self.assertIn('e.key === "End"', self.code)

    def test_count_badge_display(self) -> None:
        self.assertIn("tab.count !== undefined", self.code)

    def test_variants_support(self) -> None:
        self.assertIn('variant === "pills"', self.code)


class TabsComponentIntegrationTests(unittest.TestCase):
    """Integration tests verifying adapter generation, export, and diff invariance."""

    def test_file_registered_in_generated_project(self) -> None:
        ir = _make_test_ir()
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        paths = project.paths()
        self.assertIn("components/tabs.tsx", paths)

        content = project.get("components/tabs.tsx").content
        self.assertIn("export function Tabs(", content)
        self.assertIn("export function TabPanel(", content)
        self.assertIn('role="tablist"', content)

    def test_codegen_package_exports_render_function(self) -> None:
        import omnistackai_agent_engine.codegen as cg

        self.assertTrue(hasattr(cg, "render_tabs_component"))
        fn = getattr(cg, "render_tabs_component")
        self.assertTrue(callable(fn))
        code = fn()
        self.assertIn("export function Tabs(", code)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        ir1 = _make_test_ir(description="Description A")
        ir2 = _make_test_ir(description="Description B with completely different words")
        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1)
        p2 = adapter.generate(ir2)

        content1 = p1.get("components/tabs.tsx").content
        content2 = p2.get("components/tabs.tsx").content
        self.assertEqual(content1, content2)

    def test_full_project_generation_minimal_blog(self) -> None:
        ir = example_ir("minimal-blog")
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        self.assertIn("components/tabs.tsx", project.paths())

    def test_full_project_generation_rideshare_favourites(self) -> None:
        ir = example_ir("rideshare-favourites")
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        self.assertIn("components/tabs.tsx", project.paths())


if __name__ == "__main__":
    unittest.main()

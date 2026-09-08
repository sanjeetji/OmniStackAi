"""Task R-273: Global Responsive Navigation Shell & Header Navbar in Generated Next.js Web App.

Tests for components/navbar.tsx generation, RootLayout integration in app/layout.tsx,
route detection with usePathname, dynamic collection/form screen links, role badges,
quick-create CTA button, and diff invariance.
"""

from dataclasses import replace
from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    AdminStrategy,
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
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter

_STRATEGY = ProjectStrategy(
    MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
    BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _sample_ir() -> ApplicationIR:
    return ApplicationIR(
        name="TripManager",
        description="A platform for managing trips and expenses.",
        platforms=(Platform.WEB,),
        project_strategy=_STRATEGY,
        roles=(Role("admin", ("read", "write")), Role("member", ("read",)), Role("public", ("read",))),
        entities=(
            Entity("Trip", (Field("id", FieldType.UUID), Field("title", FieldType.STRING))),
            Entity("Expense", (Field("id", FieldType.UUID), Field("amount", FieldType.FLOAT))),
        ),
        screens=(
            Screen("trip_list", "member", components=("list", "table")),
            Screen("new_trip", "admin", components=("form",), actions=("save", "create")),
            Screen("trip_detail", "member", components=("detail", "view")),
            Screen("expense_catalog", "public", components=("list",)),
        ),
    )


class NavbarNavigationTests(TestCase):
    def setUp(self) -> None:
        self.adapter = NextjsWebAdapter()
        self.ir = _sample_ir()
        self.project = self.adapter.generate(self.ir)
        self.navbar = self.project.get("components/navbar.tsx").content
        self.layout = self.project.get("app/layout.tsx").content

    def test_navbar_file_generated(self) -> None:
        self.assertIn("components/navbar.tsx", set(self.project.paths()))

    def test_layout_imports_and_renders_navbar(self) -> None:
        self.assertIn('import { Navbar } from "../components/navbar";', self.layout)
        self.assertIn("<Navbar />", self.layout)
        self.assertIn("{children}", self.layout)

    def test_navbar_is_client_component(self) -> None:
        self.assertTrue(self.navbar.startswith('"use client";'))

    def test_navbar_uses_usepathname(self) -> None:
        self.assertIn('import { usePathname } from "next/navigation";', self.navbar)
        self.assertIn("const pathname = usePathname();", self.navbar)
        self.assertIn("const isLinkActive =", self.navbar)

    def test_navbar_renders_app_brand(self) -> None:
        self.assertIn('href="/"', self.navbar)
        self.assertIn("TripManager", self.navbar)
        # Brand avatar initial
        self.assertIn(f">\n              {self.ir.name[:1]}\n", self.navbar)

    def test_navbar_renders_overview_link(self) -> None:
        self.assertIn('href="/"', self.navbar)
        self.assertIn("Overview", self.navbar)

    def test_navbar_renders_collection_screen_links(self) -> None:
        self.assertIn('href="/trip_list"', self.navbar)
        self.assertIn("Trip List", self.navbar)
        self.assertIn('href="/expense_catalog"', self.navbar)
        self.assertIn("Expense Catalog", self.navbar)

    def test_navbar_renders_form_screen_links(self) -> None:
        self.assertIn('href="/new_trip"', self.navbar)
        self.assertIn("New Trip", self.navbar)

    def test_navbar_omits_detail_screen_from_top_bar(self) -> None:
        # Detail screen should not appear in horizontal nav links
        self.assertNotIn('href="/trip_detail"', self.navbar)

    def test_navbar_active_route_styling(self) -> None:
        self.assertIn("navLinkStyle", self.navbar)
        self.assertIn("#eff6ff", self.navbar)
        self.assertIn("#1d4ed8", self.navbar)
        self.assertIn("pathname === href || pathname.startsWith(href + \"/\")", self.navbar)

    def test_navbar_role_badge_rendered(self) -> None:
        # trip_list has role "member" -> role badge rendered
        self.assertIn(">member<", self.navbar)
        # new_trip has role "admin" -> role badge rendered
        self.assertIn(">admin<", self.navbar)

    def test_navbar_role_badge_omitted_for_public_roles(self) -> None:
        # expense_catalog has role "public" -> should not render a badge saying "public"
        self.assertNotIn(">public<", self.navbar)

    def test_navbar_quick_create_button_rendered(self) -> None:
        # new_trip is a form screen matching entity Trip
        self.assertIn("+ New Trip", self.navbar)
        self.assertIn('href="/new_trip"', self.navbar)

    def test_navbar_quick_create_omitted_when_no_form_screen(self) -> None:
        # Create an IR without form screens
        ir_no_form = replace(
            self.ir,
            screens=(
                Screen("trip_list", "member", components=("list",)),
            ),
        )
        project = self.adapter.generate(ir_no_form)
        navbar = project.get("components/navbar.tsx").content
        self.assertNotIn("+ New", navbar)
        self.assertNotIn("+ Create", navbar)

    def test_navbar_renders_without_screens(self) -> None:
        ir_empty = replace(self.ir, screens=())
        project = self.adapter.generate(ir_empty)
        navbar = project.get("components/navbar.tsx").content
        self.assertIn("TripManager", navbar)
        self.assertIn("Overview", navbar)
        self.assertNotIn("+ New", navbar)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        ir_a = self.ir
        ir_b = replace(ir_a, description=ir_a.description + " Extra notes that do not affect navbar.")
        project_a = self.adapter.generate(ir_a)
        project_b = self.adapter.generate(ir_b)
        navbar_a = project_a.get("components/navbar.tsx").content
        navbar_b = project_b.get("components/navbar.tsx").content
        self.assertEqual(navbar_a, navbar_b)

    def test_full_project_generation_succeeds(self) -> None:
        for ex_name in ("rideshare-favourites", "minimal-blog"):
            ir = example_ir(ex_name)
            project = self.adapter.generate(ir)
            self.assertIn("components/navbar.tsx", set(project.paths()))
            self.assertIn("app/layout.tsx", set(project.paths()))
            navbar = project.get("components/navbar.tsx").content
            layout = project.get("app/layout.tsx").content
            self.assertIn("<Navbar />", layout)
            self.assertIn("export function Navbar()", navbar)

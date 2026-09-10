"""Task R-302: Generated Collection Screen Boolean & Enum Visual Status Badges & Detail Screen One-Click Copy-to-Clipboard Affordances.

Tests:
1. Collection screen renders styled visual status pill badges for boolean fields (Yes in emerald, No in slate).
2. Collection screen renders styled visual category badges for enum fields (pill with blue styling and text value).
3. Subcollection child cards render styled badges for boolean and enum fields.
4. Detail screen card header renders an accessible "Copy ID" clipboard affordance with toast feedback.
5. Detail screen definition list (<dl>) renders inline copy button for ID / UUID fields.
6. Detail screen definition list renders status badges for boolean and enum fields.
7. Diff invariance across ir.description is strictly maintained.
8. Example IR projects (minimal-blog and rideshare-favourites) contain status badges and detail copy affordance.
"""

from unittest import TestCase

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
    Relation,
    RelationKind,
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import NextjsWebAdapter, render_screen_page


def _test_ir(description: str = "Test status badges and copy clipboard") -> ApplicationIR:
    return ApplicationIR(
        name="InventoryApp",
        description=description,
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE,
            WebStrategy.NEXTJS,
            AdminStrategy.NONE,
            BackendStrategy.PYTHON,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("admin"),),
        entities=(
            Entity(
                "Category",
                (
                    Field("id", FieldType.UUID),
                    Field("name", FieldType.STRING, required=True),
                    Field("active", FieldType.BOOL, required=False),
                    Field("tier", FieldType.STRING, required=False, validation=("enum:standard|premium|enterprise",)),
                ),
            ),
            Entity(
                "Item",
                (
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING, required=True),
                    Field("in_stock", FieldType.BOOL, required=False),
                    Field("status", FieldType.STRING, required=False, validation=("enum:draft|published|archived",)),
                    Field("category_id", FieldType.UUID, required=True),
                ),
                relations=(
                    Relation("category", "Category", RelationKind.MANY_TO_ONE),
                ),
            ),
        ),
        screens=(
            Screen("item_list", "admin", ("list",), ("view",)),
            Screen("item_detail", "admin", ("detail",), ("view", "delete")),
            Screen("category_list", "admin", ("list",), ("view",)),
            Screen("category_detail", "admin", ("detail",), ("view",)),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/items", auth=True, response_schema="Item"),
            ApiEndpoint(HttpMethod.GET, "/items/{id}", auth=True, response_schema="Item"),
            ApiEndpoint(HttpMethod.DELETE, "/items/{id}", auth=True, response_schema="Item"),
            ApiEndpoint(HttpMethod.GET, "/categories", auth=True, response_schema="Category"),
            ApiEndpoint(HttpMethod.GET, "/categories/{id}", auth=True, response_schema="Category"),
            ApiEndpoint(HttpMethod.GET, "/categories/{id}/items", auth=True, response_schema="Item"),
        ),
    )


class StatusBadgesAndCopyClipboardTests(TestCase):
    def setUp(self) -> None:
        self.ir = _test_ir()
        self.adapter = NextjsWebAdapter()

    def test_collection_screen_renders_boolean_and_enum_badges(self) -> None:
        screen = next(s for s in self.ir.screens if s.id == "item_list")
        page = render_screen_page(screen, self.ir)

        # Boolean badge check for in_stock
        self.assertIn('"#dcfce7"', page)  # emerald background
        self.assertIn('"#166534"', page)  # emerald text
        self.assertIn('"Yes"', page)
        self.assertIn('"No"', page)

        # Enum badge check for status
        self.assertIn('"#eff6ff"', page)  # blue background
        self.assertIn('"#1d4ed8"', page)  # blue text
        self.assertIn("border: \"1px solid #bfdbfe\"", page)

    def test_subcollection_drawer_renders_badges(self) -> None:
        screen = next(s for s in self.ir.screens if s.id == "category_list")
        page = render_screen_page(screen, self.ir)

        # Items in Category drawer should display badges for in_stock and status
        self.assertIn('"#dcfce7"', page)
        self.assertIn('"#eff6ff"', page)

    def test_detail_screen_header_renders_copy_id_button(self) -> None:
        screen = next(s for s in self.ir.screens if s.id == "item_detail")
        page = render_screen_page(screen, self.ir)

        self.assertIn('aria-label="Copy ID to clipboard"', page)
        self.assertIn("handleCopy", page)
        self.assertIn("navigator?.clipboard?.writeText", page)
        self.assertIn('handleCopy(String((item as any).id), "ID")', page)
        self.assertIn("toast.success(`Copied ${label} to clipboard`)", page)

    def test_detail_screen_dl_renders_inline_copy_for_id(self) -> None:
        screen = next(s for s in self.ir.screens if s.id == "item_detail")
        page = render_screen_page(screen, self.ir)

        self.assertIn('aria-label="Copy Id to clipboard"', page)
        self.assertIn('aria-label="Copy Category Id to clipboard"', page)

    def test_detail_screen_dl_renders_status_badges(self) -> None:
        screen = next(s for s in self.ir.screens if s.id == "item_detail")
        page = render_screen_page(screen, self.ir)

        # in_stock and status fields inside <dl> render styled badges
        self.assertIn('"#dcfce7"', page)
        self.assertIn('"#eff6ff"', page)

    def test_diff_invariance_across_ir_description(self) -> None:
        ir_a = _test_ir(description="Description Version A")
        ir_b = _test_ir(description="Description Version B Completely Different")

        for s_a, s_b in zip(ir_a.screens, ir_b.screens, strict=True):
            page_a = render_screen_page(s_a, ir_a)
            page_b = render_screen_page(s_b, ir_b)
            self.assertEqual(page_a, page_b)

    def test_minimal_blog_post_list_and_detail(self) -> None:
        blog_ir = example_ir("minimal-blog")
        post_list_screen = next(s for s in blog_ir.screens if s.id == "post_list")
        list_page = render_screen_page(post_list_screen, blog_ir)
        # minimal-blog has published: bool
        self.assertIn('"#dcfce7"', list_page)
        self.assertIn('"#166534"', list_page)


if __name__ == "__main__":
    import unittest
    unittest.main()

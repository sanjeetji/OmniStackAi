"""Task R-301: Generated Web Search Input Clear Affordances & Form Screen First-Field AutoFocus.

Tests:
1. Collection screen search form renders an accessible inline Clear button (×) when searchInput is non-empty.
2. Clicking collection search Clear button clears searchInput, sets search to empty string, and refocuses input.
3. Subcollection search form renders an accessible Clear button (×) when search state is non-empty, clearing query on click.
4. Form screen automatically emits autoFocus on the first editable field (and only the first).
5. Form screen with select as first field emits autoFocus on the select element.
6. Diff invariance across ir.description is strictly maintained.
7. Generated projects (minimal-blog and rideshare-favourites) include search clear buttons and form first-field autofocus.
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


def _test_ir(description: str = "Test search clear and autofocus") -> ApplicationIR:
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
                ),
            ),
            Entity(
                "Item",
                (
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING, required=True),
                    Field("details", FieldType.TEXT),
                    Field("category_id", FieldType.UUID, required=True),
                ),
                relations=(
                    Relation("category", "Category", RelationKind.MANY_TO_ONE),
                ),
            ),
        ),
        screens=(
            Screen("item_list", "admin", ("list",), ("view",)),
            Screen("item_editor", "admin", ("form",), ("create",)),
            Screen("category_list", "admin", ("list",), ("view",)),
            Screen("category_editor", "admin", ("form",), ("create",)),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/items", auth=True, response_schema="Item"),
            ApiEndpoint(HttpMethod.POST, "/items", auth=True, request_schema="Item", response_schema="Item"),
            ApiEndpoint(HttpMethod.GET, "/categories", auth=True, response_schema="Category"),
            ApiEndpoint(HttpMethod.POST, "/categories", auth=True, request_schema="Category", response_schema="Category"),
            ApiEndpoint(HttpMethod.GET, "/categories/{id}/items", auth=True, response_schema="Item"),
        ),
    )


class SearchClearAndAutofocusTests(TestCase):
    def setUp(self) -> None:
        self.ir = _test_ir()
        self.adapter = NextjsWebAdapter()

    def test_collection_search_renders_clear_button(self) -> None:
        screen = next(s for s in self.ir.screens if s.id == "item_list")
        page = render_screen_page(screen, self.ir)

        self.assertIn('aria-label="Clear search"', page)
        self.assertIn("Boolean(searchInput)", page)
        self.assertIn('setSearchInput("")', page)
        self.assertIn('setSearch("")', page)
        self.assertIn("searchInputRef.current?.focus()", page)

    def test_subcollection_search_renders_clear_button(self) -> None:
        screen = next(s for s in self.ir.screens if s.id == "category_list")
        page = render_screen_page(screen, self.ir)

        self.assertIn('aria-label="Clear items search"', page)
        self.assertIn('setItemsSubcolSearch("")', page)
        self.assertIn('itemsSubcol.setSearch("")', page)

    def test_form_screen_first_field_has_autofocus(self) -> None:
        screen = next(s for s in self.ir.screens if s.id == "item_editor")
        page = render_screen_page(screen, self.ir)

        # Title is the first editable field for Item
        self.assertIn('placeholder="Enter title..." required autoFocus', page)
        # Details is the second field and must NOT have autoFocus
        self.assertIn('placeholder="Enter details..."', page)
        self.assertNotIn('placeholder="Enter details..." autoFocus', page)
        self.assertNotIn('placeholder="Enter details..." required autoFocus', page)

    def test_form_screen_first_field_select_has_autofocus(self) -> None:
        # Create an IR where the first editable field is a Category relation
        custom_ir = ApplicationIR(
            name="SelectFirstApp",
            description="App where relation is first",
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
                    "Dept",
                    (
                        Field("id", FieldType.UUID),
                        Field("name", FieldType.STRING),
                    ),
                ),
                Entity(
                    "Employee",
                    (
                        Field("id", FieldType.UUID),
                        Field("dept_id", FieldType.UUID, required=True),
                        Field("full_name", FieldType.STRING, required=True),
                    ),
                    relations=(
                        Relation("dept", "Dept", RelationKind.MANY_TO_ONE),
                    ),
                ),
            ),
            screens=(
                Screen("employee_editor", "admin", ("form",), ("create",)),
            ),
            apis=(
                ApiEndpoint(HttpMethod.GET, "/depts", auth=True, response_schema="Dept"),
                ApiEndpoint(HttpMethod.POST, "/employees", auth=True, request_schema="Employee", response_schema="Employee"),
            ),
        )
        screen = custom_ir.screens[0]
        page = render_screen_page(screen, custom_ir)

        # dept_id is the first field, so the <select> element gets autoFocus
        self.assertIn("aria-invalid={!!fieldErrors.dept_id} required autoFocus", page)
        # full_name is second, so input does not have autoFocus
        self.assertIn('placeholder="Enter full name..." required', page)
        self.assertNotIn('placeholder="Enter full name..." required autoFocus', page)

    def test_diff_invariance_across_ir_description(self) -> None:
        ir_a = _test_ir(description="Alpha description")
        ir_b = _test_ir(description="Beta description completely different")

        for s_a, s_b in zip(ir_a.screens, ir_b.screens, strict=True):
            page_a = render_screen_page(s_a, ir_a)
            page_b = render_screen_page(s_b, ir_b)
            self.assertEqual(page_a, page_b)

    def test_generated_project_minimal_blog_and_rideshare(self) -> None:
        blog_proj = self.adapter.generate(example_ir("minimal-blog"))
        post_list = blog_proj.get("app/post_list/page.tsx")
        self.assertIsNotNone(post_list)
        self.assertIn('aria-label="Clear search"', post_list.content)
        self.assertIn("Boolean(searchInput)", post_list.content)

        post_editor = blog_proj.get("app/post_editor/page.tsx")
        self.assertIsNotNone(post_editor)
        self.assertIn("autoFocus", post_editor.content)

        rideshare_proj = self.adapter.generate(example_ir("rideshare-favourites"))
        fav_page = rideshare_proj.get("app/favourites/page.tsx")
        self.assertIsNotNone(fav_page)
        self.assertIn('aria-label="Clear search"', fav_page.content)


if __name__ == "__main__":
    import unittest
    unittest.main()

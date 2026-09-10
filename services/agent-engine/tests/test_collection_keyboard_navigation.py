"""Task R-297: Generated Collection Keyboard Navigation & Shortcuts.

Verifies keyboard navigation in generated Next.js collection screens:
- Pressing '/' outside form inputs focuses the collection search input and prevents '/' insertion.
- Pressing 'Escape' in the search input clears the search and blurs it.
- Pressing 'Escape' when filters are active clears all filters.
- Preserves 100% diff-invariance across ir.description changes.
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
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import NextjsWebAdapter, render_screen_page


_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.PYTHON,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _ir(with_filters: bool = True, description: str = "Test App") -> ApplicationIR:
    fields = [
        Field("id", FieldType.UUID),
        Field("title", FieldType.STRING, required=True),
    ]
    if with_filters:
        fields.append(Field("published", FieldType.BOOL))
        fields.append(Field("category", FieldType.STRING, validation=("enum:news|tech|lifestyle",)))

    apis = (
        ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
        ApiEndpoint(HttpMethod.GET, "/articles/{id}", response_schema="Article"),
    )
    entities = (Entity("Article", tuple(fields)),)
    screens = (Screen("articles", "admin", components=("list", "search")),)
    return ApplicationIR(
        name="Article Platform",
        description=description,
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("admin"),),
        entities=entities,
        apis=apis,
        screens=screens,
    )


def _render(with_filters: bool = True, description: str = "Test App") -> str:
    app_ir = _ir(with_filters=with_filters, description=description)
    return render_screen_page(app_ir.screens[0], app_ir)


class CollectionKeyboardNavigationTests(TestCase):
    def test_search_ref_attached_to_search_input(self) -> None:
        page = _render(with_filters=True)
        self.assertIn("searchInputRef", page)
        self.assertIn('ref={searchInputRef}', page)

    def test_slash_shortcut_listener_registered(self) -> None:
        page = _render(with_filters=True)
        self.assertIn('e.key === "/"', page)
        self.assertIn('searchInputRef.current?.focus()', page)
        self.assertIn('e.preventDefault()', page)

    def test_slash_shortcut_ignores_editable_targets(self) -> None:
        page = _render(with_filters=True)
        self.assertIn('target.tagName === "INPUT"', page)
        self.assertIn('target.tagName === "TEXTAREA"', page)
        self.assertIn('target.tagName === "SELECT"', page)

    def test_escape_clears_search_when_focused(self) -> None:
        page = _render(with_filters=True)
        self.assertIn('e.key === "Escape"', page)
        self.assertIn('document.activeElement === searchInputRef.current', page)
        self.assertIn('setSearchInput("")', page)
        self.assertIn('setSearch("")', page)
        self.assertIn('searchInputRef.current?.blur()', page)

    def test_escape_clears_filters_when_active(self) -> None:
        page = _render(with_filters=True)
        self.assertIn("clearFilters()", page)

    def test_keyboard_navigation_without_filters(self) -> None:
        page = _render(with_filters=False)
        self.assertIn('e.key === "/"', page)
        self.assertIn('searchInputRef.current?.focus()', page)
        self.assertIn('e.key === "Escape"', page)

    def test_diff_invariance_across_ir_description(self) -> None:
        page1 = _render(with_filters=True, description="First desc")
        page2 = _render(with_filters=True, description="Second completely different desc")
        self.assertEqual(page1, page2)

    def test_generated_project_includes_keyboard_nav(self) -> None:
        for name in ("minimal-blog", "rideshare-favourites"):
            proj = NextjsWebAdapter().generate(example_ir(name))
            match_path = next((p for p in proj.paths() if p.endswith("post_list/page.tsx") or p.endswith("favourites/page.tsx")), None)
            self.assertIsNotNone(match_path)
            f = proj.get(match_path)
            self.assertIsNotNone(f)
            self.assertIn('e.key === "/"', f.content)
            self.assertIn('searchInputRef.current?.focus()', f.content)


if __name__ == "__main__":
    import unittest
    unittest.main()

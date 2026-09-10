"""Task R-298: Generated Detail Screen Keyboard Navigation & Shortcuts.

Verifies keyboard navigation in generated Next.js detail screens:
- ArrowLeft or '[' navigates to previous record when available.
- ArrowRight or ']' navigates to next record when available.
- 'e' / 'E' navigates to edit mode when can_edit and form screen exist.
- 'Escape' deselects the current record.
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


def _ir(can_edit: bool = True, can_list: bool = True, description: str = "Test App") -> ApplicationIR:
    fields = [
        Field("id", FieldType.UUID),
        Field("title", FieldType.STRING, required=True),
        Field("content", FieldType.TEXT),
    ]
    apis = [
        ApiEndpoint(HttpMethod.GET, "/articles/{id}", response_schema="Article"),
    ]
    if can_list:
        apis.append(ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"))
    if can_edit:
        apis.append(ApiEndpoint(HttpMethod.PUT, "/articles/{id}", request_schema="Article", response_schema="Article"))

    entities = (Entity("Article", tuple(fields)),)
    screens = [
        Screen("article_detail", "admin", components=("detail",)),
    ]
    if can_edit:
        screens.append(Screen("article_form", "admin", components=("form",)))

    return ApplicationIR(
        name="Article Platform",
        description=description,
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("admin"),),
        entities=entities,
        apis=tuple(apis),
        screens=tuple(screens),
    )


def _render(can_edit: bool = True, can_list: bool = True, description: str = "Test App") -> str:
    app_ir = _ir(can_edit=can_edit, can_list=can_list, description=description)
    return render_screen_page(app_ir.screens[0], app_ir)


class DetailKeyboardNavigationTests(TestCase):
    def test_prev_next_shortcuts_registered_when_listable(self) -> None:
        page = _render(can_edit=True, can_list=True)
        self.assertIn('e.key === "ArrowLeft" || e.key === "["', page)
        self.assertIn('prevItem && handleSelectId(prevItem.id)', page)
        self.assertIn('e.key === "ArrowRight" || e.key === "]"', page)
        self.assertIn('nextItem && handleSelectId(nextItem.id)', page)

    def test_edit_shortcut_registered_when_editable(self) -> None:
        page = _render(can_edit=True, can_list=True)
        self.assertIn('e.key === "e" || e.key === "E"', page)
        self.assertIn('/article_form?id=${selectedId}', page)

    def test_edit_shortcut_omitted_when_not_editable(self) -> None:
        page = _render(can_edit=False, can_list=True)
        self.assertNotIn('e.key === "e" || e.key === "E"', page)

    def test_escape_shortcut_clears_selection(self) -> None:
        page = _render(can_edit=True, can_list=True)
        self.assertIn('e.key === "Escape"', page)
        self.assertIn('handleSelectId(null)', page)

    def test_shortcuts_ignore_editable_targets(self) -> None:
        page = _render(can_edit=True, can_list=True)
        self.assertIn('target.tagName === "INPUT"', page)
        self.assertIn('target.tagName === "TEXTAREA"', page)
        self.assertIn('target.tagName === "SELECT"', page)

    def test_diff_invariance_across_ir_description(self) -> None:
        page1 = _render(can_edit=True, can_list=True, description="First desc")
        page2 = _render(can_edit=True, can_list=True, description="Second completely different desc")
        self.assertEqual(page1, page2)

    def test_example_projects_still_generate(self) -> None:
        for name in ("minimal-blog", "rideshare-favourites"):
            proj = NextjsWebAdapter().generate(example_ir(name))
            self.assertTrue(any(p.endswith("page.tsx") for p in proj.paths()))


if __name__ == "__main__":
    import unittest
    unittest.main()

"""R-285: generated Next.js subcollection controls use R-284 server filters."""

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
from omnistackai_agent_engine.codegen import render_hooks, render_screen_page


_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.PYTHON,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _ir(description: str = "Projects with filterable tasks") -> ApplicationIR:
    return ApplicationIR(
        name="Project Desk",
        description=description,
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("member"),),
        entities=(
            Entity("Project", (Field("id", FieldType.UUID), Field("name", FieldType.STRING))),
            Entity(
                "Task",
                (
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING),
                    Field("completed", FieldType.BOOL, required=False),
                    Field("status", FieldType.STRING, required=False, validation=("enum:todo|doing|done",)),
                ),
                relations=(Relation("project", "Project", RelationKind.MANY_TO_ONE),),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/projects", response_schema="Project"),
            ApiEndpoint(HttpMethod.GET, "/projects/{id}", response_schema="Project"),
            ApiEndpoint(HttpMethod.GET, "/projects/{projectId}/tasks", response_schema="Task"),
        ),
        screens=(
            Screen("project_list", "member", components=("list",), actions=("open",)),
            Screen("project_detail", "member", components=("detail",), actions=("view",)),
        ),
    )


def _pages(ir: ApplicationIR) -> tuple[str, str]:
    return tuple(render_screen_page(screen, ir) for screen in ir.screens)  # type: ignore[return-value]


class HookWiringTests(TestCase):
    def test_filterable_subcollection_hook_has_allowlisted_filter_state(self) -> None:
        hooks = render_hooks(_ir())
        self.assertIn('const taskFilterOptions: Record<string, readonly string[]> = {"completed": ["true", "false"], "status": ["todo", "doing", "done"]};', hooks)
        self.assertIn("initialParams: UseCollectionListParams = {},", hooks)
        self.assertIn("): UseCollectionListState<Task> {", hooks)
        self.assertIn("const [params, setParams] = useState<UseCollectionListParams>", hooks)
        self.assertIn("const setFilter = useCallback((field: string, value: string) => {", hooks)
        self.assertIn('taskFilterOptions[field]?.includes(value)', hooks)
        self.assertIn("const clearFilters = useCallback(() => {", hooks)

    def test_hook_flattens_filters_into_list_by_request(self) -> None:
        hooks = render_hooks(_ir())
        self.assertIn("const { filters, ...baseParams } = params;", hooks)
        self.assertIn("const requestParams = { ...baseParams, ...(filters ?? {}) };", hooks)
        self.assertIn(
            "api.listTasksByProjectWithCount(projectId, { params: requestParams, ...options, signal: controller.signal });",
            hooks,
        )
        self.assertIn("    setFilter,", hooks)
        self.assertIn("    clearFilters,", hooks)
        self.assertGreaterEqual(hooks.count("offset: 0,"), 4)

    def test_nonfilterable_subcollection_hook_is_unchanged(self) -> None:
        hooks = render_hooks(example_ir("minimal-blog"))
        self.assertNotIn("commentFilterOptions", hooks)
        section = hooks.split("export function useListCommentsByPost(", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("initialParams: UseListParams = {},", section)
        self.assertIn("): UseListState<Comment> {", section)
        self.assertNotIn("setFilter", section)
        self.assertNotIn("requestParams", section)


class ScreenWiringTests(TestCase):
    def test_both_subcollection_views_render_boolean_and_enum_controls(self) -> None:
        for page in _pages(_ir()):
            self.assertIn('tasksSubcol.setFilter("completed", "all")', page)
            self.assertIn('tasksSubcol.setFilter("completed", "true")', page)
            self.assertIn('tasksSubcol.setFilter("completed", "false")', page)
            self.assertIn("Completed: Yes", page)
            self.assertIn("Completed: No", page)
            self.assertIn('aria-label="Filter tasks by Status"', page)
            self.assertIn('tasksSubcol.setFilter("status", e.target.value)', page)
            self.assertIn('<option value="doing">Doing</option>', page)

    def test_both_views_use_hook_filter_state_and_reset(self) -> None:
        for page in _pages(_ir()):
            self.assertIn("Object.keys(tasksSubcol.params.filters ?? {}).length", page)
            self.assertIn("onClick={tasksSubcol.clearFilters}", page)
            self.assertIn("Clear filters", page)
            self.assertNotIn("tasksSubcol.data.filter", page)

    def test_nonfilterable_subcollection_ui_stays_clean(self) -> None:
        ir = example_ir("minimal-blog")
        for screen in ir.screens:
            page = render_screen_page(screen, ir)
            self.assertNotIn("commentsSubcol.setFilter", page)
            self.assertNotIn('aria-label="Filter comments', page)

    def test_description_only_changes_are_byte_stable(self) -> None:
        first = _ir("First")
        second = _ir("Second")
        self.assertEqual(render_hooks(first), render_hooks(second))
        self.assertEqual(_pages(first), _pages(second))


if __name__ == "__main__":
    import unittest

    unittest.main()

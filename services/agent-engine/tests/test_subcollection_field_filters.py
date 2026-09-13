"""R-284: boolean/enum filters on FK-scoped LIST_BY endpoints."""

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
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import GoBackendAdapter, PythonBackendAdapter, render_openapi


_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.PYTHON,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _ir(description: str = "Parents with filterable children") -> ApplicationIR:
    return ApplicationIR(
        name="Filtered Children",
        description=description,
        platforms=(Platform.BACKEND,),
        project_strategy=_STRATEGY,
        entities=(
            Entity("Parent", (Field("id", FieldType.UUID), Field("name", FieldType.STRING))),
            Entity(
                "Child",
                (
                    Field("id", FieldType.UUID),
                    Field("body", FieldType.TEXT),
                    Field("active", FieldType.BOOL, required=False),
                    Field("status", FieldType.STRING, validation=("enum:new|ready|done",)),
                ),
                (Relation("parent", "Parent", RelationKind.MANY_TO_ONE),),
            ),
        ),
        apis=(ApiEndpoint(HttpMethod.GET, "/parents/{parentId}/children", response_schema="Child"),),
    )


class PythonSubcollectionFilterTests(TestCase):
    def setUp(self) -> None:
        project = PythonBackendAdapter().generate(_ir())
        self.repo = project.get("app/repositories/child.py").content
        self.router = project.get("app/routers/parents.py").content

    def test_repository_signatures_and_parameterized_predicates(self) -> None:
        self.assertIn(
            'async def list_child_by_parent(parent_id: str, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None, active=None, status=None) -> list[dict[str, Any]]:',
            self.repo,
        )
        self.assertIn(
            "async def count_child_by_parent(parent_id: str, q: str | None = None, active=None, status=None) -> int:",
            self.repo,
        )
        self.assertIn('conditions: list[str] = [\'"parent_id" = %s\']', self.repo)
        self.assertIn("params: list[Any] = [parent_id]", self.repo)
        self.assertIn('conditions.append(\'(\"body\" ILIKE %s OR \"status\" ILIKE %s)\')', self.repo)
        self.assertIn('conditions.append(\'"active" = %s\')', self.repo)
        self.assertIn("params.append(active)", self.repo)
        self.assertIn('conditions.append(\'"status" = %s\')', self.repo)
        self.assertIn("params.append(status)", self.repo)
        self.assertIn("await cur.execute(sql, (*params, limit, offset))", self.repo)
        self.assertIn("await cur.execute(f'SELECT COUNT(*) AS count FROM {TABLE}{where}', tuple(params))", self.repo)

    def test_router_declares_and_forwards_typed_filters(self) -> None:
        self.assertIn(
            'async def get_parents_parentid_children(parentId: str, response: Response, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None, active: bool | None = None, status: str | None = None) -> list[dict]:',
            self.router,
        )
        self.assertIn("child.count_child_by_parent(parentId, q=q, active=active, status=status)", self.router)
        self.assertIn(
            "child.list_child_by_parent(parentId, limit=limit, offset=offset, sort=sort, order=order, q=q, active=active, status=status)",
            self.router,
        )


class GoSubcollectionFilterTests(TestCase):
    def setUp(self) -> None:
        project = GoBackendAdapter().generate(_ir())
        self.store = project.get("internal/store/child.go").content
        self.handler = project.get("internal/handlers/parents.go").content

    def test_relation_scoped_builder_preserves_placeholder_order(self) -> None:
        self.assertIn(
            "func childByParentFilters(parentID, q string, filters map[string]string) (string, []any) {",
            self.store,
        )
        self.assertIn('conds := []string{"\\\"parent_id\\\" = $1"}', self.store)
        self.assertIn("args := []any{parentID}", self.store)
        self.assertIn(
            'conds = append(conds, fmt.Sprintf("(\\\"body\\\" ILIKE $%[1]d OR \\\"status\\\" ILIKE $%[1]d)", len(args)+1))',
            self.store,
        )
        self.assertIn('conds = append(conds, fmt.Sprintf("\\\"active\\\" = $%d", len(args)+1))', self.store)
        self.assertIn('args = append(args, v == "true")', self.store)
        self.assertIn('conds = append(conds, fmt.Sprintf("\\\"status\\\" = $%d", len(args)+1))', self.store)
        self.assertIn('return " WHERE " + strings.Join(conds, " AND "), args', self.store)

    def test_list_and_count_share_builder_and_bound_arguments(self) -> None:
        self.assertIn(
            "func ListChildByParent(ctx context.Context, db *sql.DB, parentID string, limit, offset int, sort, order, q string, filters map[string]string) ([]models.Child, error)",
            self.store,
        )
        self.assertIn(
            "func CountChildByParent(ctx context.Context, db *sql.DB, parentID string, q string, filters map[string]string) (int, error)",
            self.store,
        )
        self.assertEqual(self.store.count("where, args := childByParentFilters(parentID, q, filters)"), 2)
        self.assertIn(
            'LIMIT $%d OFFSET $%d", where, col, dir, len(args)+1, len(args)+2)',
            self.store,
        )
        self.assertIn("args = append(args, limit, offset)", self.store)
        self.assertIn("db.QueryContext(ctx, query, args...)", self.store)
        self.assertIn("db.QueryRowContext(ctx, query, args...).Scan(&count)", self.store)

    def test_handler_parses_and_forwards_filters(self) -> None:
        self.assertIn("filters := parseFilters(r)", self.handler)
        self.assertIn(
            'store.CountChildByParent(r.Context(), h.DB, r.PathValue("parentId"), q, filters)',
            self.handler,
        )
        self.assertIn(
            'store.ListChildByParent(r.Context(), h.DB, r.PathValue("parentId"), limit, offset, sort, order, q, filters)',
            self.handler,
        )


class OpenApiSubcollectionFilterTests(TestCase):
    def test_list_by_documents_bool_and_enum_filters(self) -> None:
        operation = render_openapi(_ir())["paths"]["/parents/{parentId}/children"]["get"]
        params = {param["name"]: param["schema"] for param in operation["parameters"]}
        self.assertEqual(params["active"], {"type": "boolean"})
        self.assertEqual(params["status"], {"type": "string", "enum": ["new", "ready", "done"]})


class CompatibilityTests(TestCase):
    def test_non_filterable_minimal_blog_subcollection_is_unchanged(self) -> None:
        py = PythonBackendAdapter().generate(example_ir("minimal-blog"))
        py_repo = py.get("app/repositories/comment.py").content
        py_router = py.get("app/routers/posts.py").content
        self.assertIn("q: str | None = None) -> list[dict[str, Any]]:", py_repo)
        self.assertIn("comment.count_comment_by_post(postId, q=q)", py_router)
        self.assertNotIn("active=None", py_repo)

        go = GoBackendAdapter().generate(example_ir("minimal-blog"))
        go_store = go.get("internal/store/comment.go").content
        go_handler = go.get("internal/handlers/posts.go").content
        self.assertIn("sort, order, q string) ([]models.Comment, error)", go_store)
        self.assertIn('store.CountCommentByPost(r.Context(), h.DB, r.PathValue("postId"), q)', go_handler)
        self.assertNotIn("commentByPostFilters", go_store)

    def test_description_only_changes_are_byte_stable(self) -> None:
        for adapter, paths in (
            (PythonBackendAdapter(), ("app/repositories/child.py", "app/routers/parents.py")),
            (GoBackendAdapter(), ("internal/store/child.go", "internal/handlers/parents.go")),
        ):
            first = adapter.generate(_ir("First"))
            second = adapter.generate(_ir("Second"))
            for path in paths:
                self.assertEqual(first.get(path).content, second.get(path).content)


if __name__ == "__main__":
    import unittest

    unittest.main()

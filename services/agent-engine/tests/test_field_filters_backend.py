"""Tests for R-282: server-side boolean/enum field filters on top-level LIST endpoints.

The generated backends accept ?<field>=<value> query params for boolean and enum fields, compose them
into the SQL WHERE with parameterized values (identifiers stay whitelisted to IR field names), and
document them in OpenAPI. Non-filterable entities are byte-identical (no filter plumbing). LIST_BY
(subcollections) is intentionally out of scope.
"""

from unittest import TestCase

from omnistackai_agent_engine.application_ir.ir import (
    ApiEndpoint,
    ApplicationIR,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    MobileProfile,
    Platform,
    ProjectStrategy,
    WebStrategy,
    AdminStrategy,
    BackendStrategy,
    DatabaseStrategy,
    RepoStrategy,
)
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    GoBackendAdapter,
    PythonBackendAdapter,
    render_openapi,
)
from omnistackai_agent_engine.codegen.field_validation import filter_fields

_STRATEGY = ProjectStrategy(
    MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
    BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _ir(description: str = "A shop") -> ApplicationIR:
    return ApplicationIR(
        name="Shop",
        description=description,
        platforms=(Platform.BACKEND,),
        project_strategy=_STRATEGY,
        entities=(
            Entity(
                "Item",
                (
                    Field("id", FieldType.UUID),
                    Field("name", FieldType.STRING),
                    Field("active", FieldType.BOOL, required=False),
                    Field("status", FieldType.STRING, validation=("enum:new|used|sold",)),
                ),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/items", response_schema="Item"),
            ApiEndpoint(HttpMethod.POST, "/items", request_schema="Item", response_schema="Item"),
        ),
    )


class FilterFieldsHelperTests(TestCase):
    def test_selects_bool_and_enum_excludes_id_and_plain(self) -> None:
        item = _ir().entities[0]
        got = [(f.name, kind) for f, kind in filter_fields(item)]
        self.assertEqual(got, [("active", "bool"), ("status", "enum")])

    def test_non_filterable_entity_empty(self) -> None:
        for name in ("rideshare-favourites",):
            for entity in example_ir(name).entities:
                self.assertEqual(filter_fields(entity), [])


class PythonFilterRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.repo = PythonBackendAdapter().generate(_ir()).get("app/repositories/item.py").content

    def test_list_filters_helper_and_signatures(self) -> None:
        self.assertIn("def _list_filters(q=None, active=None, status=None):", self.repo)
        self.assertIn('async def list_item(limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None, active=None, status=None) -> list[dict[str, Any]]:', self.repo)
        self.assertIn("async def count_item(q: str | None = None, active=None, status=None) -> int:", self.repo)

    def test_conditions_are_parameterized(self) -> None:
        self.assertIn("if active is not None:", self.repo)
        self.assertIn('conditions.append(\'"active" = %s\')', self.repo)
        self.assertIn("params.append(active)", self.repo)
        self.assertIn('conditions.append(\'"status" = %s\')', self.repo)
        self.assertIn("params.append(status)", self.repo)
        self.assertIn("await cur.execute(sql, (*params, limit, offset))", self.repo)

    def test_router_declares_and_forwards_filter_params(self) -> None:
        router = PythonBackendAdapter().generate(_ir()).get("app/routers/items.py").content
        self.assertIn('async def get_items(response: Response, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None, active: bool | None = None, status: str | None = None) -> list[dict]:', router)
        self.assertIn("total = await item.count_item(q=q, active=active, status=status)", router)
        self.assertIn("return await item.list_item(limit=limit, offset=offset, sort=sort, order=order, q=q, active=active, status=status)", router)


class GoFilterStoreTests(TestCase):
    def setUp(self) -> None:
        self.project = GoBackendAdapter().generate(_ir())
        self.store = self.project.get("internal/store/item.go").content

    def test_filters_helper_and_signatures(self) -> None:
        self.assertIn("func itemFilters(q string, filters map[string]string) (string, []any) {", self.store)
        self.assertIn("func ListItem(ctx context.Context, db *sql.DB, limit, offset int, sort, order, q string, filters map[string]string) ([]models.Item, error)", self.store)
        self.assertIn("func CountItem(ctx context.Context, db *sql.DB, q string, filters map[string]string) (int, error)", self.store)

    def test_bool_and_enum_coercion_and_placeholders(self) -> None:
        self.assertIn('if v, ok := filters["active"]; ok && v != "" {', self.store)
        self.assertIn('conds = append(conds, fmt.Sprintf("\\\"active\\\" = $%d", len(args)+1))', self.store)
        self.assertIn('args = append(args, v == "true")', self.store)          # bool coercion
        self.assertIn('if v, ok := filters["status"]; ok && v != "" {', self.store)
        self.assertIn("args = append(args, v)", self.store)                     # enum stays string
        self.assertIn('return " WHERE " + strings.Join(conds, " AND "), args', self.store)
        self.assertIn("rows, err := db.QueryContext(ctx, query, args...)", self.store)

    def test_handler_parses_and_passes_filters(self) -> None:
        shared = self.project.get("internal/handlers/handlers.go").content
        self.assertIn("func parseFilters(r *http.Request) map[string]string {", shared)
        handler = self.project.get("internal/handlers/items.go").content
        self.assertIn("filters := parseFilters(r)", handler)
        self.assertIn("store.ListItem(r.Context(), h.DB, limit, offset, sort, order, q, filters)", handler)
        self.assertIn("store.CountItem(r.Context(), h.DB, q, filters)", handler)


class OpenApiFilterTests(TestCase):
    def test_list_operation_documents_bool_and_enum_filters(self) -> None:
        spec = render_openapi(_ir())
        params = {p["name"]: p["schema"] for p in spec["paths"]["/items"]["get"]["parameters"]}
        self.assertEqual(params["active"], {"type": "boolean"})
        self.assertEqual(params["status"], {"type": "string", "enum": ["new", "used", "sold"]})


class NonFilterableUnchangedTests(TestCase):
    def test_no_filter_plumbing_for_non_filterable_project(self) -> None:
        # rideshare-favourites has no boolean/enum fields on any entity.
        proj = GoBackendAdapter().generate(example_ir("rideshare-favourites"))
        shared = proj.get("internal/handlers/handlers.go").content
        self.assertNotIn("parseFilters", shared)
        for p in proj.paths():
            if p.startswith("internal/store/") and p.endswith(".go"):
                self.assertNotIn("Filters(q string, filters map[string]string)", proj.get(p).content)
                self.assertNotIn("filters map[string]string", proj.get(p).content)

    def test_python_non_filterable_signatures_unchanged(self) -> None:
        proj = PythonBackendAdapter().generate(example_ir("rideshare-favourites"))
        for p in proj.paths():
            if p.startswith("app/repositories/") and p.endswith(".py"):
                content = proj.get(p).content
                self.assertNotIn("_list_filters", content)


class DiffInvarianceTests(TestCase):
    def test_data_access_invariant_across_ir_description(self) -> None:
        a = PythonBackendAdapter().generate(_ir("First")).get("app/repositories/item.py").content
        b = PythonBackendAdapter().generate(_ir("Second, different")).get("app/repositories/item.py").content
        self.assertEqual(a, b)
        ga = GoBackendAdapter().generate(_ir("First")).get("internal/store/item.go").content
        gb = GoBackendAdapter().generate(_ir("Second, different")).get("internal/store/item.go").content
        self.assertEqual(ga, gb)


if __name__ == "__main__":
    import unittest

    unittest.main()

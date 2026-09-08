"""Tests for Task R-278: Collection Screen Boolean & Enum Field Filtering in Generated Next.js Web App."""

import unittest

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
    Relation,
    RelationKind,
    Role,
    Screen,
    WebStrategy,
    AdminStrategy,
    BackendStrategy,
    DatabaseStrategy,
    RepoStrategy,
)
from omnistackai_agent_engine.application_ir.examples import example_ir
from omnistackai_agent_engine.codegen import NextjsWebAdapter, render_screen_page


def _make_test_ir(
    with_boolean: bool = True,
    with_enum: bool = False,
    description: str = "Test App",
) -> ApplicationIR:
    fields = [
        Field("id", FieldType.STRING, required=True),
        Field("title", FieldType.STRING, required=True),
        Field("content", FieldType.TEXT, required=False),
    ]
    if with_boolean:
        fields.append(Field("published", FieldType.BOOL, required=False))
    if with_enum:
        fields.append(
            Field(
                "status",
                FieldType.STRING,
                required=False,
                validation=("enum:draft|in_review|published",),
            )
        )

    entities = (
        Entity(
            name="Article",
            fields=tuple(fields),
        ),
    )

    apis = (
        ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
        ApiEndpoint(HttpMethod.POST, "/articles", request_schema="Article", response_schema="Article"),
        ApiEndpoint(HttpMethod.GET, "/articles/{id}", response_schema="Article"),
        ApiEndpoint(HttpMethod.PUT, "/articles/{id}", request_schema="Article", response_schema="Article"),
        ApiEndpoint(HttpMethod.DELETE, "/articles/{id}", response_schema="Article"),
    )

    screens = (
        Screen("article_list", "admin", components=("list",), actions=("view", "delete"), navigation=("article_form",)),
        Screen("article_form", "admin", components=("form",), actions=("create", "update"), navigation=("article_list",)),
    )

    return ApplicationIR(
        name="Article Platform",
        description=description,
        platforms=(Platform.WEB,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE,
            WebStrategy.NEXTJS,
            AdminStrategy.NONE,
            BackendStrategy.PYTHON,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("admin"),),
        entities=entities,
        apis=apis,
        screens=screens,
    )


class CollectionFieldFiltersTests(unittest.TestCase):
    """Test suite for collection screen boolean & enum field filtering."""

    def test_collection_screen_imports_use_memo_when_filterable_fields_present(self) -> None:
        ir = _make_test_ir(with_boolean=True)
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn('import { useMemo, useState } from "react";', content)

    def test_collection_screen_omits_use_memo_when_no_filterable_fields(self) -> None:
        ir = _make_test_ir(with_boolean=False, with_enum=False)
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn('import { useState } from "react";', content)
        self.assertNotIn("useMemo", content)

    def test_collection_screen_declares_filter_state_and_handlers(self) -> None:
        ir = _make_test_ir(with_boolean=True)
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("const [filterValues, setFilterValues] = useState<Record<string, string>>({});", content)
        self.assertIn("const handleFilterChange = (field: string, val: string) => {", content)
        self.assertIn("setFilterValues((prev) => ({ ...prev, [field]: val }));", content)
        self.assertIn("const handleClearFilters = () => {", content)
        self.assertIn("setFilterValues({});", content)

    def test_collection_screen_computes_filtered_data_and_active_count(self) -> None:
        ir = _make_test_ir(with_boolean=True)
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn('const activeFilterCount = Object.values(filterValues).filter((v) => v && v !== "all").length;', content)
        self.assertIn("const filteredData = useMemo(() => {", content)
        self.assertIn("if (!data) return null;", content)
        self.assertIn('if (val === "true" && item[field] !== true) return false;', content)
        self.assertIn('if (val === "false" && item[field] !== false) return false;', content)
        self.assertIn("const displayData = filteredData ?? (data ?? []);", content)

    def test_collection_screen_renders_segmented_pill_for_boolean_field(self) -> None:
        ir = _make_test_ir(with_boolean=True)
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("Filters:</span>", content)
        self.assertIn('handleFilterChange("published", "all")', content)
        self.assertIn('handleFilterChange("published", "true")', content)
        self.assertIn('handleFilterChange("published", "false")', content)
        self.assertIn("Published: Yes", content)
        self.assertIn("Published: No", content)

    def test_collection_screen_renders_select_for_enum_field(self) -> None:
        ir = _make_test_ir(with_boolean=False, with_enum=True)
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("Filters:</span>", content)
        self.assertIn('aria-label="Filter by Status"', content)
        self.assertIn('<option value="all">All Statuss</option>', content)
        self.assertIn('<option value="draft">Draft</option>', content)
        self.assertIn('<option value="in_review">In Review</option>', content)
        self.assertIn('<option value="published">Published</option>', content)

    def test_collection_screen_renders_active_filter_badge_and_reset(self) -> None:
        ir = _make_test_ir(with_boolean=True)
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("{activeFilterCount > 0 && (", content)
        self.assertIn("{activeFilterCount} active", content)
        self.assertIn("onClick={handleClearFilters}", content)
        self.assertIn("Reset", content)

    def test_collection_screen_renders_dedicated_empty_filter_state(self) -> None:
        ir = _make_test_ir(with_boolean=True)
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("{data.length > 0 && activeFilterCount > 0 ? (", content)
        self.assertIn("No Articles match the active filter criteria.", content)
        self.assertIn("Clear all filters", content)

    def test_collection_screen_table_maps_display_data(self) -> None:
        ir = _make_test_ir(with_boolean=True)
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("{data && displayData.map((item, idx) => (", content)

    def test_collection_screen_empty_fallback_when_no_filters_present(self) -> None:
        ir = _make_test_ir(with_boolean=False, with_enum=False)
        content = render_screen_page(ir.screens[0], ir)
        self.assertNotIn("filterValues", content)
        self.assertNotIn("handleFilterChange", content)
        self.assertNotIn("activeFilterCount", content)
        self.assertNotIn("Filters:</span>", content)
        self.assertIn("{data && data.map((item, idx) => (", content)

    def test_collection_screen_diff_invariance(self) -> None:
        ir_a = _make_test_ir(with_boolean=True, with_enum=True, description="Description Alpha")
        ir_b = _make_test_ir(with_boolean=True, with_enum=True, description="Description Beta")
        self.assertEqual(
            render_screen_page(ir_a.screens[0], ir_a),
            render_screen_page(ir_b.screens[0], ir_b),
        )

    def test_minimal_blog_post_list_has_published_filter(self) -> None:
        ir = example_ir("minimal-blog")
        post_list_screen = next(s for s in ir.screens if s.id == "post_list")
        content = render_screen_page(post_list_screen, ir)
        self.assertIn('import { useMemo, useState } from "react";', content)
        self.assertIn("Filters:</span>", content)
        self.assertIn("Published: Yes", content)
        self.assertIn("Published: No", content)
        self.assertIn("No Posts match the active filter criteria.", content)

    def test_rideshare_favourites_driver_screen_omits_filters(self) -> None:
        ir = example_ir("rideshare-favourites")
        drivers_screen = next(s for s in ir.screens if s.id == "favourites")
        content = render_screen_page(drivers_screen, ir)
        self.assertNotIn("Filters:</span>", content)
        self.assertNotIn("activeFilterCount", content)

    def test_multiple_boolean_and_enum_fields(self) -> None:
        ir = _make_test_ir(with_boolean=True, with_enum=True)
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("Published: Yes", content)
        self.assertIn('aria-label="Filter by Status"', content)

    def test_minimal_blog_full_adapter_generate(self) -> None:
        ir = example_ir("minimal-blog")
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        self.assertIn("app/post_list/page.tsx", project.paths())
        post_list = project.get("app/post_list/page.tsx")
        self.assertIsNotNone(post_list)
        self.assertIn("Published: Yes", post_list.content)


if __name__ == "__main__":
    unittest.main()

"""Tests for Full-Stack Platform Feature Completeness across 4 phases:
- Phase 1: Frontend Search, Pagination & Filter UI Controls & LLM prompt hook descriptions.
- Phase 2: Audit Timestamps (created_at, updated_at) on all entity tables, models, TypeScript types, and detail metadata footer.
- Phase 3: RBAC / Row Ownership (created_by) when needs_auth(ir) is True across schema, data access, handlers, types, hooks, and RequireOwner middleware.
- Phase 4: S3-Compatible File Uploads with FieldType.ATTACHMENT and storage env contracts.
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
)
from omnistackai_agent_engine.codegen import (
    GoBackendAdapter,
    NextjsWebAdapter,
    PythonBackendAdapter,
)
from omnistackai_agent_engine.codegen.auth_guard import go_auth_file, python_auth_file
from omnistackai_agent_engine.codegen.data_access import (
    go_data_access_files,
    python_data_access_files,
)
from omnistackai_agent_engine.codegen.llm_ui import build_ui_synthesis_prompt
from omnistackai_agent_engine.codegen.schema_sql import render_postgres_schema


def _make_ir(with_auth: bool = False, with_attachment: bool = False) -> ApplicationIR:
    fields = [
        Field("id", FieldType.UUID),
        Field("name", FieldType.STRING),
    ]
    if with_attachment:
        fields.append(Field("document", FieldType.ATTACHMENT, required=False))

    roles = (Role("admin"), Role("member")) if with_auth else (Role("viewer"),)
    apis = [
        ApiEndpoint(HttpMethod.GET, "/projects", auth=with_auth, response_schema="Project"),
        ApiEndpoint(HttpMethod.GET, "/projects/{id}", auth=with_auth, response_schema="Project"),
        ApiEndpoint(HttpMethod.POST, "/projects", auth=with_auth, request_schema="Project"),
    ]
    return ApplicationIR(
        name="Fleet Portal",
        description="Fleet asset tracking and management system",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE,
            WebStrategy.NEXTJS,
            AdminStrategy.NONE,
            BackendStrategy.PYTHON,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=roles,
        entities=(Entity("Project", tuple(fields)),),
        apis=tuple(apis),
        screens=(
            Screen("projects", "admin" if with_auth else "viewer", components=("list",)),
            Screen("project_detail", "admin" if with_auth else "viewer", components=("detail",)),
        ),
    )


class TestPlatformFeatureCompletenessPhase1(TestCase):
    """Phase 1: Frontend Search, Pagination & Filter UI Controls + LLM prompt hook metadata."""

    def test_llm_ui_prompt_describes_complete_hooks(self) -> None:
        ir = _make_ir()
        prompt = build_ui_synthesis_prompt(ir, "Manage fleet projects")
        self.assertIn("useListProjects", prompt)
        # R-465: the prompt is grounded in the REAL generated hooks — list *params* are limit/offset,
        # page/pageSize are *state* fields (the old page?/pageSize? param assertions were the drift).
        self.assertIn("limit?: number", prompt)
        self.assertIn("offset?: number", prompt)
        self.assertIn("page: number", prompt)
        self.assertIn("pageSize: number", prompt)
        self.assertIn("setSearch", prompt)
        self.assertIn("setPage", prompt)
        self.assertIn("setPageSize", prompt)
        self.assertIn("setSort", prompt)
        self.assertIn("setFilter", prompt)
        self.assertIn("clearFilters", prompt)
        self.assertIn("refetch", prompt)

    def test_collection_screen_has_search_pagination_and_sort_controls(self) -> None:
        ir = _make_ir()
        proj = NextjsWebAdapter().generate(ir)
        screen_content = proj.get("app/projects/page.tsx").content
        # Search input and debounce
        self.assertIn('type="search"', screen_content)
        self.assertIn("setSearch", screen_content)
        self.assertIn("Clear search", screen_content)
        # Pagination controls
        self.assertIn("Previous", screen_content)
        self.assertIn("Next", screen_content)
        self.assertIn("Page {page} of {totalPages}", screen_content)
        self.assertIn("pageSizeSelect", screen_content)
        # Sort header
        self.assertIn("setSort", screen_content)


class TestPlatformFeatureCompletenessPhase2(TestCase):
    """Phase 2: Audit Timestamps (created_at, updated_at) on all entity tables, models, and UI."""

    def test_schema_sql_has_audit_columns_and_trigger(self) -> None:
        ir = _make_ir()
        sql = render_postgres_schema(ir)
        self.assertIn('"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()', sql)
        self.assertIn('"updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()', sql)
        self.assertIn("CREATE OR REPLACE FUNCTION set_updated_at()", sql)
        self.assertIn("CREATE TRIGGER \"trg_project_updated_at\"", sql)

    def test_python_models_have_audit_timestamps(self) -> None:
        ir = _make_ir()
        proj = PythonBackendAdapter().generate(ir)
        models_content = proj.get("app/models.py").content
        self.assertIn("created_at: Optional[datetime] = None", models_content)
        self.assertIn("updated_at: Optional[datetime] = None", models_content)

    def test_go_models_have_audit_timestamps(self) -> None:
        ir = _make_ir()
        proj = GoBackendAdapter().generate(ir)
        models_content = proj.get("internal/models/models.go").content
        self.assertIn('CreatedAt time.Time `json:"created_at"`', models_content)
        self.assertIn('UpdatedAt time.Time `json:"updated_at"`', models_content)

    def test_typescript_types_have_audit_timestamps(self) -> None:
        ir = _make_ir()
        proj = NextjsWebAdapter().generate(ir)
        types_content = proj.get("lib/types.ts").content
        self.assertIn("created_at?: string;", types_content)
        self.assertIn("updated_at?: string;", types_content)

    def test_detail_screen_renders_timestamps_footer(self) -> None:
        ir = _make_ir()
        proj = NextjsWebAdapter().generate(ir)
        detail_content = proj.get("app/project_detail/page.tsx").content
        self.assertIn("Created:", detail_content)
        self.assertIn("Last updated:", detail_content)


class TestPlatformFeatureCompletenessPhase3(TestCase):
    """Phase 3: RBAC / Row Ownership (created_by) when needs_auth(ir) is True."""

    def test_schema_emits_created_by_foreign_key_when_auth_enabled(self) -> None:
        ir_with_auth = _make_ir(with_auth=True)
        sql = render_postgres_schema(ir_with_auth)
        self.assertIn('"created_by" UUID REFERENCES "users"("id") ON DELETE SET NULL', sql)

    def test_schema_omits_created_by_when_auth_disabled(self) -> None:
        ir_no_auth = _make_ir(with_auth=False)
        sql = render_postgres_schema(ir_no_auth)
        self.assertNotIn('"created_by"', sql)

    def test_data_access_python_create_accepts_created_by(self) -> None:
        ir = _make_ir(with_auth=True)
        py_files = dict(python_data_access_files(ir, "fleet"))
        repo = py_files["app/repositories/project.py"]
        self.assertIn("async def create_project(data: dict[str, Any], created_by: str | None = None)", repo)
        self.assertIn("if created_by is not None:", repo)

    def test_auth_guard_provides_require_owner_helpers(self) -> None:
        ir = _make_ir(with_auth=True)
        py_auth = python_auth_file(ir)
        self.assertIn("def require_owner(", py_auth)
        self.assertIn("forbidden_not_owner", py_auth)

        go_auth = go_auth_file(ir)
        self.assertIn("func RequireOwner(ownerID string, claims jwt.MapClaims) bool", go_auth)

    def test_typescript_types_and_hooks_support_owner_fields(self) -> None:
        ir = _make_ir(with_auth=True)
        proj = NextjsWebAdapter().generate(ir)
        types_content = proj.get("lib/types.ts").content
        self.assertIn("created_by?: string | null;", types_content)

        hooks_content = proj.get("lib/hooks.ts").content
        self.assertIn("ownerOnly?: boolean;", hooks_content)
        self.assertIn("owner_only", hooks_content)


class TestPlatformFeatureCompletenessPhase4(TestCase):
    """Phase 4: S3-Compatible File Uploads with FieldType.ATTACHMENT & Storage Env Vars."""

    def test_attachment_field_type_in_schema_and_types(self) -> None:
        ir = _make_ir(with_attachment=True)
        # PostgreSQL column maps to TEXT
        sql = render_postgres_schema(ir)
        self.assertIn('"document" TEXT', sql)

        # TypeScript maps to string
        proj = NextjsWebAdapter().generate(ir)
        types_content = proj.get("lib/types.ts").content
        self.assertIn("document?: string;", types_content)

        # Python maps to str
        py_proj = PythonBackendAdapter().generate(ir)
        models_py = py_proj.get("app/models.py").content
        self.assertIn("document: Optional[str] = None", models_py)

        # Go maps to string
        go_proj = GoBackendAdapter().generate(ir)
        models_go = go_proj.get("internal/models/models.go").content
        self.assertIn("Document *string `json:\"document,omitempty\"`", models_go)

    def test_storage_env_vars_in_all_templates(self) -> None:
        ir = _make_ir()
        # Next.js web .env.example
        web_proj = NextjsWebAdapter().generate(ir)
        web_env = web_proj.get(".env.example").content
        self.assertIn("STORAGE_ENDPOINT", web_env)
        self.assertIn("STORAGE_BUCKET", web_env)

        # Python backend .env.example
        py_proj = PythonBackendAdapter().generate(ir)
        py_env = py_proj.get(".env.example").content
        self.assertIn("STORAGE_ENDPOINT", py_env)
        self.assertIn("STORAGE_BUCKET", py_env)
        self.assertIn("STORAGE_ACCESS_KEY", py_env)
        self.assertIn("STORAGE_SECRET_KEY", py_env)

        # Go backend .env.example
        go_proj = GoBackendAdapter().generate(ir)
        go_env = go_proj.get(".env.example").content
        self.assertIn("STORAGE_ENDPOINT", go_env)
        self.assertIn("STORAGE_BUCKET", go_env)
        self.assertIn("STORAGE_ACCESS_KEY", go_env)
        self.assertIn("STORAGE_SECRET_KEY", go_env)

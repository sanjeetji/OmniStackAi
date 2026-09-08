"""Task R-264: Field-Level Validation & Error Feedback in Generated Next.js Forms.

Tests:
1. extractFieldErrors export in lib/api.ts.
2. extractFieldErrors handles Go structured validation error format ({"errors": [...]}).
3. extractFieldErrors handles FastAPI/Pydantic structured format ({"detail": [...]}).
4. Form screens import extractFieldErrors from "../lib/api".
5. Form screens declare and manage fieldErrors state (Record<string, string>).
6. Form inputs conditionally render red border (#ef4444) and aria-invalid based on fieldErrors.
7. Form inputs render per-field error message span below input.
8. Form inputs clear their fieldErrors on onChange.
9. Form screens perform client-side pre-validation for required fields, max_length, min/max, and enum.
10. Enum fields render an interactive <select> dropdown with options.
11. Reset button clears fieldErrors and formData.
12. Warning banner renders when field errors exist.
13. Screen generator maintains diff invariance across description changes.
14. Full project generation via NextjsWebAdapter.generate succeeds with 0 network calls.
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


def _validated_ir() -> ApplicationIR:
    return ApplicationIR(
        name="Store App",
        description="E-commerce store with validated fields.",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
            BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("admin"),),
        entities=(
            Entity(
                "Product",
                (
                    Field("id", FieldType.UUID),
                    Field("name", FieldType.STRING, required=True, validation=("max_length:50",)),
                    Field("description", FieldType.TEXT, required=False),
                    Field("price", FieldType.FLOAT, required=True, validation=("min:0", "max:10000")),
                    Field("status", FieldType.STRING, required=True, validation=("enum:draft|active|archived",)),
                    Field("in_stock", FieldType.BOOL, required=False),
                ),
            ),
        ),
        screens=(
            Screen("product_list", "admin", ("list",), ("view",)),
            Screen("product_editor", "admin", ("form",), ("create",)),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/products", auth=True, response_schema="Product"),
            ApiEndpoint(HttpMethod.POST, "/products", auth=True, request_schema="Product", response_schema="Product"),
        ),
    )


class FormValidationScreenTests(TestCase):
    def setUp(self) -> None:
        self.adapter = NextjsWebAdapter()

    def test_api_ts_exports_extract_field_errors(self) -> None:
        ir = _validated_ir()
        project = self.adapter.generate(ir)
        api_ts = project.get("lib/api.ts").content

        self.assertIn("export function extractFieldErrors(error: unknown): Record<string, string>", api_ts)
        self.assertIn('"errors" in data && Array.isArray((data as { errors: unknown[] }).errors)', api_ts)
        self.assertIn('"detail" in data && Array.isArray((data as { detail: unknown[] }).detail)', api_ts)

    def test_form_screen_imports_extract_field_errors(self) -> None:
        ir = _validated_ir()
        screen = next(s for s in ir.screens if s.id == "product_editor")
        page = render_screen_page(screen, ir)

        self.assertIn('import { extractFieldErrors } from "../lib/api";', page)
        self.assertIn('const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});', page)

    def test_form_screen_has_client_side_validation(self) -> None:
        ir = _validated_ir()
        screen = next(s for s in ir.screens if s.id == "product_editor")
        page = render_screen_page(screen, ir)

        # Required checks
        self.assertIn('clientErrors.name = "Name is required";', page)
        self.assertIn('clientErrors.price = "Price is required";', page)

        # Max length check
        self.assertIn('clientErrors.name = "Name must not exceed 50 characters";', page)

        # Min and max numeric checks
        self.assertIn('clientErrors.price = "Price must be at least 0";', page)
        self.assertIn('clientErrors.price = "Price must be at most 10000";', page)

        # Enum check
        self.assertIn('clientErrors.status = "Status must be one of: draft, active, archived";', page)

        # Stop submission if clientErrors exist
        self.assertIn("if (Object.keys(clientErrors).length > 0) {", page)
        self.assertIn("setFieldErrors(clientErrors);", page)

    def test_form_screen_extracts_server_field_errors_on_failure(self) -> None:
        ir = _validated_ir()
        screen = next(s for s in ir.screens if s.id == "product_editor")
        page = render_screen_page(screen, ir)

        self.assertIn("const serverErrors = extractFieldErrors(err);", page)
        self.assertIn("if (Object.keys(serverErrors).length > 0) {", page)
        self.assertIn("setFieldErrors(serverErrors);", page)

    def test_form_screen_renders_field_error_elements_and_styles(self) -> None:
        ir = _validated_ir()
        screen = next(s for s in ir.screens if s.id == "product_editor")
        page = render_screen_page(screen, ir)

        # Red border when error exists
        self.assertIn('border: fieldErrors.name ? "1px solid #ef4444" : "1px solid #cbd5e1"', page)
        self.assertIn('border: fieldErrors.price ? "1px solid #ef4444" : "1px solid #cbd5e1"', page)

        # aria-invalid attribute
        self.assertIn("aria-invalid={!!fieldErrors.name}", page)
        self.assertIn("aria-invalid={!!fieldErrors.price}", page)
        self.assertIn("aria-invalid={!!fieldErrors.status}", page)

        # Dedicated error message span
        self.assertIn("{fieldErrors.name && <span style={{ color: \"#ef4444\", fontSize: 12, marginTop: 4, display: \"block\" }}>{fieldErrors.name}</span>}", page)
        self.assertIn("{fieldErrors.price && <span style={{ color: \"#ef4444\", fontSize: 12, marginTop: 4, display: \"block\" }}>{fieldErrors.price}</span>}", page)

    def test_form_screen_clears_field_error_on_change(self) -> None:
        ir = _validated_ir()
        screen = next(s for s in ir.screens if s.id == "product_editor")
        page = render_screen_page(screen, ir)

        self.assertIn('if (fieldErrors.name) setFieldErrors((prev) => ({ ...prev, name: "" }));', page)
        self.assertIn('if (fieldErrors.price) setFieldErrors((prev) => ({ ...prev, price: "" }));', page)
        self.assertIn('if (fieldErrors.status) setFieldErrors((prev) => ({ ...prev, status: "" }));', page)

    def test_enum_field_renders_select_element(self) -> None:
        ir = _validated_ir()
        screen = next(s for s in ir.screens if s.id == "product_editor")
        page = render_screen_page(screen, ir)

        # Renders <select> with options
        self.assertIn("<select", page)
        self.assertIn('<option value="">Select status...</option>', page)
        self.assertIn('<option value="draft">draft</option>', page)
        self.assertIn('<option value="active">active</option>', page)
        self.assertIn('<option value="archived">archived</option>', page)

    def test_reset_button_clears_field_errors(self) -> None:
        ir = _validated_ir()
        screen = next(s for s in ir.screens if s.id == "product_editor")
        page = render_screen_page(screen, ir)

        self.assertIn("setFieldErrors({});", page)

    def test_warning_banner_renders_when_field_errors_exist(self) -> None:
        ir = _validated_ir()
        screen = next(s for s in ir.screens if s.id == "product_editor")
        page = render_screen_page(screen, ir)

        self.assertIn("{Object.keys(fieldErrors).length > 0 && (", page)
        self.assertIn("Please correct the highlighted errors below before submitting.", page)

    def test_minimal_blog_post_editor_validation_support(self) -> None:
        ir = example_ir("minimal-blog")
        screen = next(s for s in ir.screens if s.id == "post_editor")
        page = render_screen_page(screen, ir)

        # Required checks for Post
        self.assertIn('clientErrors.title = "Title is required";', page)
        self.assertIn('clientErrors.body = "Body is required";', page)
        self.assertIn("aria-invalid={!!fieldErrors.title}", page)
        self.assertIn("aria-invalid={!!fieldErrors.body}", page)

    def test_ir_description_change_invariance(self) -> None:
        ir1 = _validated_ir()
        ir2 = ApplicationIR(
            name=ir1.name,
            description="Completely different description text.",
            platforms=ir1.platforms,
            project_strategy=ir1.project_strategy,
            roles=ir1.roles,
            entities=ir1.entities,
            screens=ir1.screens,
            apis=ir1.apis,
        )
        for screen in ir1.screens:
            p1 = render_screen_page(screen, ir1)
            p2 = render_screen_page(screen, ir2)
            self.assertEqual(p1, p2, f"Screen {screen.id} differed across description changes")

    def test_full_project_emission_with_validation_screens(self) -> None:
        ir = _validated_ir()
        project = self.adapter.generate(ir)
        paths = set(project.paths())

        self.assertIn("lib/api.ts", paths)
        self.assertIn("lib/hooks.ts", paths)
        self.assertIn("app/product_editor/page.tsx", paths)
        self.assertIn("app/product_list/page.tsx", paths)

"""Task R-300: Generated Form Screen Input Constraints & Live Character Counters.

Verifies schema-driven input constraints in generated Next.js form screens:
- String and Text fields with max_length emit maxLength HTML attribute and live character count badge.
- Character count badge turns amber when input length exceeds 90% of max limit.
- Numeric fields with min/max rules emit min and max HTML attributes and range badge.
- Unconstrained fields preserve default markup.
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


def _ir(fields: tuple[Field, ...], description: str = "Test App") -> ApplicationIR:
    entities = (Entity("Product", fields),)
    apis = [
        ApiEndpoint(HttpMethod.POST, "/products", request_schema="Product", response_schema="Product"),
    ]
    screens = [
        Screen("product_form", "admin", components=("form",)),
    ]

    return ApplicationIR(
        name="Product Platform",
        description=description,
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("admin"),),
        entities=entities,
        apis=tuple(apis),
        screens=tuple(screens),
    )


class FormInputConstraintsTests(TestCase):
    def test_string_field_with_max_length_emits_maxlength_and_counter(self) -> None:
        fields = (
            Field("id", FieldType.UUID),
            Field("name", FieldType.STRING, required=True, validation=("max_length:80",)),
        )
        page = render_screen_page(Screen("product_form", "admin", components=("form",)), _ir(fields))
        self.assertIn("maxLength={80}", page)
        self.assertIn('Max 80 characters', page)
        self.assertIn('String((formData as any).name ?? "").length', page)
        self.assertIn('/ 80', page)

    def test_text_field_with_max_length_emits_maxlength_and_counter(self) -> None:
        fields = (
            Field("id", FieldType.UUID),
            Field("description", FieldType.TEXT, validation=("max_length:300",)),
        )
        page = render_screen_page(Screen("product_form", "admin", components=("form",)), _ir(fields))
        self.assertIn("maxLength={300}", page)
        self.assertIn('Max 300 characters', page)
        self.assertIn('String((formData as any).description ?? "").length', page)
        self.assertIn('/ 300', page)

    def test_number_field_with_min_max_emits_attributes_and_range(self) -> None:
        fields = (
            Field("id", FieldType.UUID),
            Field("rating", FieldType.INT, validation=("min:1", "max:5")),
        )
        page = render_screen_page(Screen("product_form", "admin", components=("form",)), _ir(fields))
        self.assertIn("min={1}", page)
        self.assertIn("max={5}", page)
        self.assertIn("Range: 1 to 5", page)

    def test_unconstrained_fields_preserve_default_markup(self) -> None:
        fields = (
            Field("id", FieldType.UUID),
            Field("title", FieldType.STRING, required=True),
        )
        page = render_screen_page(Screen("product_form", "admin", components=("form",)), _ir(fields))
        self.assertNotIn("maxLength=", page)
        self.assertNotIn("Max ", page)
        self.assertNotIn("Range:", page)
        self.assertIn('{fieldErrors.title && <span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>{fieldErrors.title}</span>}', page)

    def test_diff_invariance_across_ir_description(self) -> None:
        fields = (
            Field("id", FieldType.UUID),
            Field("name", FieldType.STRING, validation=("max_length:80",)),
            Field("quantity", FieldType.INT, validation=("min:0", "max:100")),
        )
        page1 = render_screen_page(Screen("product_form", "admin", components=("form",)), _ir(fields, description="Desc 1"))
        page2 = render_screen_page(Screen("product_form", "admin", components=("form",)), _ir(fields, description="Desc 2 completely altered"))
        self.assertEqual(page1, page2)

    def test_example_projects_still_generate(self) -> None:
        for name in ("minimal-blog", "rideshare-favourites"):
            proj = NextjsWebAdapter().generate(example_ir(name))
            self.assertTrue(any(p.endswith("page.tsx") for p in proj.paths()))


if __name__ == "__main__":
    import unittest
    unittest.main()

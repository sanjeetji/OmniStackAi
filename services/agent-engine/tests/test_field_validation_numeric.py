import ast
from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    MobileProfile,
    Platform,
    ProjectStrategy,
    RepoStrategy,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.application_ir.ir import AdminStrategy
from omnistackai_agent_engine.codegen import GoBackendAdapter, PythonBackendAdapter, parse_field_rules, render_postgres_schema
from omnistackai_agent_engine.codegen.field_validation import go_validate_tag


def _ir(entity: Entity, *, backend=BackendStrategy.PYTHON) -> ApplicationIR:
    return ApplicationIR(
        name="Shop",
        description="A tiny shop.",
        platforms=(Platform.BACKEND,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NONE, AdminStrategy.NONE,
            backend, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        entities=(entity,),
    )


class ParseNumericTests(TestCase):
    def test_min_max_parsed_as_raw_tokens(self) -> None:
        rules = parse_field_rules(Field("rating", FieldType.FLOAT, validation=("min:0", "max:5")))
        self.assertEqual((rules.minimum, rules.maximum), ("0", "5"))

    def test_non_numeric_min_max_ignored(self) -> None:
        rules = parse_field_rules(Field("x", FieldType.INT, validation=("min:lots", "max:")))
        self.assertIsNone(rules.minimum)
        self.assertIsNone(rules.maximum)


class SchemaNumericTests(TestCase):
    def test_numeric_min_max_are_checks(self) -> None:
        entity = Entity("Product", (Field("id", FieldType.UUID), Field("rating", FieldType.FLOAT, required=False, validation=("min:0", "max:5"))))
        sql = render_postgres_schema(_ir(entity))
        self.assertIn('"rating" DOUBLE PRECISION CHECK ("rating" >= 0) CHECK ("rating" <= 5)', sql)

    def test_string_min_max_not_applied_as_numeric_check(self) -> None:
        # min/max only apply to numeric columns
        entity = Entity("Product", (Field("id", FieldType.UUID), Field("name", FieldType.STRING, validation=("min:1",))))
        self.assertNotIn('CHECK ("name" >=', render_postgres_schema(_ir(entity)))


class PydanticNumericTests(TestCase):
    def test_ge_le_constraints(self) -> None:
        entity = Entity("Product", (Field("id", FieldType.UUID), Field("qty", FieldType.INT, validation=("min:1", "max:99"))))
        models = PythonBackendAdapter().generate(_ir(entity)).get("app/models.py").content
        ast.parse(models)
        self.assertIn("qty: int = Field(ge=1, le=99)", models)


class GoTagTests(TestCase):
    def test_go_validate_tag_helper(self) -> None:
        self.assertEqual(go_validate_tag(Field("n", FieldType.STRING, validation=("max_length:80",)), parse_field_rules(Field("n", FieldType.STRING, validation=("max_length:80",)))), "max=80")
        rating = Field("rating", FieldType.FLOAT, validation=("min:0", "max:5"))
        self.assertEqual(go_validate_tag(rating, parse_field_rules(rating)), "gte=0,lte=5")
        status = Field("status", FieldType.STRING, validation=("enum:new|used",))
        self.assertEqual(go_validate_tag(status, parse_field_rules(status)), "oneof=new used")

    def test_go_struct_tags_emitted(self) -> None:
        entity = Entity(
            "Product",
            (
                Field("id", FieldType.UUID),
                Field("name", FieldType.STRING, validation=("max_length:80",)),
                Field("rating", FieldType.FLOAT, required=False, validation=("min:0", "max:5")),
            ),
        )
        models = GoBackendAdapter().generate(_ir(entity, backend=BackendStrategy.GO)).get("internal/models/models.go").content
        self.assertIn('Name string `json:"name" validate:"max=80"`', models)
        self.assertIn('Rating *float64 `json:"rating,omitempty" validate:"gte=0,lte=5"`', models)
        # a rule-free field keeps a plain json tag (no validate)
        self.assertIn('Id string `json:"id"`', models)


class UnchangedWhenNoRulesTests(TestCase):
    def test_examples_have_no_validate_tags(self) -> None:
        models = GoBackendAdapter().generate(example_ir("rideshare-favourites")).get("internal/models/models.go").content
        self.assertNotIn("validate:", models)

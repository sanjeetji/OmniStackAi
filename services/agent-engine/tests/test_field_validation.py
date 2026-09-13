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
from omnistackai_agent_engine.codegen import PythonBackendAdapter, parse_field_rules, render_postgres_schema


def _ir(entity: Entity) -> ApplicationIR:
    return ApplicationIR(
        name="Blog",
        description="A tiny blog.",
        platforms=(Platform.BACKEND,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NONE, AdminStrategy.NONE,
            BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        entities=(entity,),
    )


class ParseRulesTests(TestCase):
    def test_parses_max_length_and_enum(self) -> None:
        f = Field("status", FieldType.STRING, validation=("max_length:120", "enum:a|b|c"))
        rules = parse_field_rules(f)
        self.assertEqual(rules.max_length, 120)
        self.assertEqual(rules.enum, ("a", "b", "c"))

    def test_unknown_rule_ignored_and_defaults(self) -> None:
        rules = parse_field_rules(Field("x", FieldType.STRING, validation=("weird:thing", "not_a_rule")))
        self.assertIsNone(rules.max_length)
        self.assertEqual(rules.enum, ())

    def test_non_digit_max_length_ignored(self) -> None:
        self.assertIsNone(parse_field_rules(Field("x", FieldType.STRING, validation=("max_length:big",))).max_length)


class SchemaValidationTests(TestCase):
    def test_string_max_length_is_varchar(self) -> None:
        entity = Entity("Article", (Field("id", FieldType.UUID), Field("title", FieldType.STRING, validation=("max_length:120",))))
        sql = render_postgres_schema(_ir(entity))
        self.assertIn('"title" VARCHAR(120) NOT NULL', sql)

    def test_enum_is_check_constraint_escaped(self) -> None:
        entity = Entity("Article", (Field("id", FieldType.UUID), Field("status", FieldType.STRING, validation=("enum:draft|it's",))))
        sql = render_postgres_schema(_ir(entity))
        self.assertIn('"status" TEXT NOT NULL CHECK ("status" IN (\'draft\', \'it\'\'s\'))', sql)

    def test_string_without_max_length_stays_text(self) -> None:
        entity = Entity("Article", (Field("id", FieldType.UUID), Field("title", FieldType.STRING)))
        self.assertIn('"title" TEXT NOT NULL', render_postgres_schema(_ir(entity)))


class PydanticValidationTests(TestCase):
    def _models(self, entity: Entity) -> str:
        content = PythonBackendAdapter().generate(_ir(entity)).get("app/models.py").content
        ast.parse(content)  # valid Python
        return content

    def test_max_length_field_and_literal_enum(self) -> None:
        entity = Entity(
            "Article",
            (
                Field("id", FieldType.UUID),
                Field("title", FieldType.STRING, validation=("max_length:120",)),
                Field("status", FieldType.STRING, validation=("enum:draft|published",)),
            ),
        )
        models = self._models(entity)
        self.assertIn("from pydantic import BaseModel, Field", models)
        self.assertIn("from typing import Literal", models)
        self.assertIn("title: str = Field(max_length=120)", models)
        self.assertIn("status: Literal['draft', 'published']", models)

    def test_optional_field_with_constraint(self) -> None:
        entity = Entity("Article", (Field("id", FieldType.UUID), Field("summary", FieldType.STRING, required=False, validation=("max_length:280",))))
        self.assertIn("summary: Optional[str] = Field(default=None, max_length=280)", self._models(entity))

    def test_no_rules_no_field_import(self) -> None:
        # a field with no rules keeps the original plain model (no pydantic Field import)
        entity = Entity("Article", (Field("id", FieldType.UUID), Field("title", FieldType.STRING)))
        models = self._models(entity)
        self.assertIn("from pydantic import BaseModel\n", models)
        self.assertNotIn("import BaseModel, Field", models)
        self.assertIn("    title: str", models)


class ExamplesUnaffectedTests(TestCase):
    def test_example_schema_and_models_unchanged_by_this_feature(self) -> None:
        # examples declare no validation rules -> no VARCHAR/CHECK/Field/Literal appears
        for name in ("minimal-blog", "rideshare-favourites"):
            ir = example_ir(name)
            schema = render_postgres_schema(ir)
            self.assertNotIn("VARCHAR(", schema)
            self.assertNotIn("CHECK (", schema)
        models = PythonBackendAdapter().generate(example_ir("minimal-blog")).get("app/models.py").content
        self.assertIn("from pydantic import BaseModel\n", models)
        self.assertNotIn("Literal[", models)

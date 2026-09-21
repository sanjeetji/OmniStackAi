from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    Fixture,
    MobileProfile,
    Platform,
    ProjectStrategy,
    RepoStrategy,
    WebStrategy,
    example_ir,
    has_errors,
    normalize_ir,
    validate_ir,
)
from omnistackai_agent_engine.application_ir.ir import AdminStrategy
from omnistackai_agent_engine.codegen import GoBackendAdapter, PythonBackendAdapter, render_postgres_seed
from omnistackai_agent_engine.codegen.seed_sql import _sql_literal


def _ir(entities, fixtures=(), *, database=DatabaseStrategy.POSTGRES) -> ApplicationIR:
    return ApplicationIR(
        name="Shop",
        description="A tiny shop.",
        platforms=(Platform.WEB,),
        project_strategy=ProjectStrategy(
            mobile_profile=MobileProfile.NONE,
            web_strategy=WebStrategy.NONE,
            admin_strategy=AdminStrategy.NONE,
            backend_strategy=BackendStrategy.PYTHON,
            database_strategy=database,
            repo_strategy=RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        entities=entities,
        fixtures=fixtures,
    )


class SqlLiteralTests(TestCase):
    def test_scalar_rendering(self) -> None:
        self.assertEqual(_sql_literal(None), "NULL")
        self.assertEqual(_sql_literal(True), "TRUE")
        self.assertEqual(_sql_literal(False), "FALSE")
        self.assertEqual(_sql_literal(42), "42")
        self.assertEqual(_sql_literal(3.5), "3.5")

    def test_string_quotes_are_doubled(self) -> None:
        self.assertEqual(_sql_literal("it's fine"), "'it''s fine'")

    def test_json_container_is_jsonb(self) -> None:
        self.assertEqual(_sql_literal({"b": 1, "a": 2}), "'{\"a\": 2, \"b\": 1}'::jsonb")  # sorted keys
        self.assertEqual(_sql_literal([1, 2]), "'[1, 2]'::jsonb")


class RenderSeedTests(TestCase):
    def test_insert_shape_and_alphabetical_columns(self) -> None:
        entity = Entity("Widget", (Field("id", FieldType.UUID), Field("label", FieldType.STRING)))
        widget_id = "5b0f2c8e-7c1d-4e2a-9f3b-1a2b3c4d5e6f"
        fixtures = (Fixture("Widget", ({"label": "A", "id": widget_id},)),)
        sql = render_postgres_seed(_ir((entity,), fixtures))
        # columns sorted alphabetically (id before label), values parameter-free literals
        self.assertIn(f'INSERT INTO "widget" ("id", "label") VALUES (\'{widget_id}\', \'A\');', sql)

    def test_no_fixtures_is_empty(self) -> None:
        entity = Entity("Widget", (Field("id", FieldType.UUID),))
        self.assertEqual(render_postgres_seed(_ir((entity,))), "")

    def test_byte_stable(self) -> None:
        ir = example_ir("minimal-blog")
        self.assertEqual(render_postgres_seed(ir), render_postgres_seed(ir))

    def test_fk_column_seeded(self) -> None:
        sql = render_postgres_seed(example_ir("minimal-blog"))
        self.assertIn('INSERT INTO "comment" ("body", "id", "post_id") VALUES (', sql)


class AdapterEmissionTests(TestCase):
    def test_python_and_go_emit_seed_for_minimal_blog(self) -> None:
        py = PythonBackendAdapter().generate(example_ir("minimal-blog"))
        self.assertIn("migrations/0002_seed.sql", py.paths())
        self.assertIn('INSERT INTO "post"', py.get("migrations/0002_seed.sql").content)
        go = GoBackendAdapter().generate(example_ir("minimal-blog"))
        self.assertIn("migrations/0002_seed.sql", go.paths())

    def test_no_seed_without_fixtures(self) -> None:
        # rideshare-favourites has entities + postgres but no fixtures
        project = GoBackendAdapter().generate(example_ir("rideshare-favourites"))
        self.assertIn("migrations/0001_init.sql", project.paths())
        self.assertNotIn("migrations/0002_seed.sql", project.paths())

    def test_no_seed_without_postgres(self) -> None:
        entity = Entity("Widget", (Field("id", FieldType.UUID),))
        fixtures = (Fixture("Widget", ({"id": "x"},)),)
        project = PythonBackendAdapter().generate(_ir((entity,), fixtures, database=DatabaseStrategy.OTHER))
        self.assertNotIn("migrations/0002_seed.sql", project.paths())


class FixtureValidationTests(TestCase):
    def _entities(self):
        return (
            Entity("Post", (Field("id", FieldType.UUID), Field("title", FieldType.STRING))),
        )

    def test_unknown_fixture_entity_is_error(self) -> None:
        ir = _ir(self._entities(), (Fixture("Ghost", ({"id": "x"},)),))
        codes = {i.code for i in validate_ir(ir)}
        self.assertIn("unknown_fixture_entity", codes)
        self.assertTrue(has_errors(validate_ir(ir)))

    def test_unknown_fixture_column_is_error(self) -> None:
        ir = _ir(self._entities(), (Fixture("Post", ({"id": "x", "nope": 1},)),))
        codes = {i.code for i in validate_ir(ir)}
        self.assertIn("unknown_fixture_column", codes)

    def test_missing_required_is_warning_not_error(self) -> None:
        ir = _ir(self._entities(), (Fixture("Post", ({"id": "x"},)),))  # title (required) omitted
        issues = validate_ir(ir)
        self.assertIn("fixture_missing_required", {i.code for i in issues})
        self.assertFalse(has_errors(issues))  # advisory only


class RoundTripTests(TestCase):
    def test_fixtures_survive_serialize_and_normalize(self) -> None:
        ir = example_ir("minimal-blog")
        self.assertEqual(ApplicationIR.from_dict(ir.to_dict()), ir)
        self.assertEqual(normalize_ir(ir).fixtures, tuple(sorted(ir.fixtures, key=lambda f: f.entity)))
        self.assertTrue(normalize_ir(ir).fixtures)  # not dropped


class UuidFixtureLabelTests(TestCase):
    """R-521: models often write labels like "user123" into uuid columns. Postgres rejects them
    ("invalid input syntax for type uuid"), which aborted every preview of such an app. A label is
    mapped to a deterministic UUID, the same label always to the same UUID, so rows that refer to
    each other stay linked. Real UUIDs and non-uuid columns are left exactly as authored."""

    def _render(self) -> str:
        user = Entity(name="Member", fields=(Field("id", FieldType.UUID, required=True), Field("name", FieldType.STRING)))
        habit = Entity(
            name="Habit",
            fields=(
                Field("id", FieldType.UUID, required=True),
                Field("user_id", FieldType.UUID),
                Field("code", FieldType.STRING),
            ),
        )
        return render_postgres_seed(
            _ir(
                (user, habit),
                (
                    Fixture(entity="Member", rows=({"id": "user123", "name": "Asha"},)),
                    Fixture(
                        entity="Habit",
                        rows=(
                            {"id": "11111111-1111-1111-1111-111111111111", "user_id": "user123", "code": "user123"},
                        ),
                    ),
                ),
            )
        )

    def test_labels_in_uuid_columns_become_stable_uuids(self) -> None:
        import re
        import uuid

        sql = self._render()
        expected = str(uuid.uuid5(uuid.NAMESPACE_URL, "omnistackai:fixture:user123"))
        self.assertIn(f"'{expected}'", sql)
        self.assertEqual(sql.count(f"'{expected}'"), 2)  # Member.id and Habit.user_id stay linked
        self.assertIn("'11111111-1111-1111-1111-111111111111'", sql)  # a real UUID is untouched
        self.assertIn("VALUES ('user123', ", sql)  # the string column keeps the authored label
        for literal in re.findall(r"'([0-9a-f-]{36})'", sql):
            uuid.UUID(literal)

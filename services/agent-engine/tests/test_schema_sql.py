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
    Relation,
    RelationKind,
    RepoStrategy,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.application_ir.ir import AdminStrategy
from omnistackai_agent_engine.codegen import (
    GoBackendAdapter,
    PythonBackendAdapter,
    render_postgres_schema,
)


def _strategy(*, database: DatabaseStrategy = DatabaseStrategy.POSTGRES) -> ProjectStrategy:
    return ProjectStrategy(
        mobile_profile=MobileProfile.NONE,
        web_strategy=WebStrategy.NONE,
        admin_strategy=AdminStrategy.NONE,
        backend_strategy=BackendStrategy.PYTHON,
        database_strategy=database,
        repo_strategy=RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
    )


def _ir(entities: tuple[Entity, ...], *, database: DatabaseStrategy = DatabaseStrategy.POSTGRES) -> ApplicationIR:
    return ApplicationIR(
        name="Shop",
        description="A tiny shop.",
        platforms=(Platform.WEB,),
        project_strategy=_strategy(database=database),
        entities=entities,
    )


class TypeMapTests(TestCase):
    def test_field_types_and_not_null(self) -> None:
        entity = Entity(
            "Widget",
            (
                Field("id", FieldType.UUID, True),
                Field("label", FieldType.STRING, True),
                Field("notes", FieldType.TEXT, False),
                Field("qty", FieldType.INT, True),
                Field("price", FieldType.FLOAT, True),
                Field("active", FieldType.BOOL, False),
                Field("made_at", FieldType.DATETIME, False),
                Field("meta", FieldType.JSON, False),
            ),
        )
        sql = render_postgres_schema(_ir((entity,)))
        self.assertIn("CREATE TABLE widget (", sql)
        self.assertIn("id UUID PRIMARY KEY DEFAULT gen_random_uuid()", sql)
        self.assertIn("label TEXT NOT NULL", sql)
        self.assertIn("notes TEXT", sql)
        self.assertNotIn("notes TEXT NOT NULL", sql)
        self.assertIn("qty BIGINT NOT NULL", sql)
        self.assertIn("price DOUBLE PRECISION NOT NULL", sql)
        self.assertIn("active BOOLEAN", sql)
        self.assertIn("made_at TIMESTAMPTZ", sql)
        self.assertIn("meta JSONB", sql)


class PrimaryKeyTests(TestCase):
    def test_surrogate_id_added_when_absent(self) -> None:
        entity = Entity("Note", (Field("body", FieldType.TEXT, True),))
        sql = render_postgres_schema(_ir((entity,)))
        self.assertIn("id UUID PRIMARY KEY DEFAULT gen_random_uuid()", sql)

    def test_declared_id_becomes_primary_key(self) -> None:
        entity = Entity("Note", (Field("id", FieldType.UUID, True), Field("body", FieldType.TEXT, True)))
        sql = render_postgres_schema(_ir((entity,)))
        # the declared id is the only primary key; no surrogate id is prepended
        self.assertIn("    id UUID PRIMARY KEY DEFAULT gen_random_uuid()", sql)
        self.assertEqual(sql.count("PRIMARY KEY"), 1)


class ForeignKeyTests(TestCase):
    def test_many_to_one_emits_fk_column(self) -> None:
        driver = Entity("Driver", (Field("id", FieldType.UUID, True),))
        fav = Entity(
            "FavouriteDriver",
            (Field("id", FieldType.UUID, True),),
            (Relation("driver", "Driver", RelationKind.MANY_TO_ONE),),
        )
        sql = render_postgres_schema(_ir((driver, fav)))
        self.assertIn("driver_id UUID REFERENCES driver(id)", sql)

    def test_many_to_many_emits_single_join_table(self) -> None:
        a = Entity("Book", (Field("id", FieldType.UUID, True),), (Relation("tags", "Tag", RelationKind.MANY_TO_MANY),))
        b = Entity("Tag", (Field("id", FieldType.UUID, True),), (Relation("books", "Book", RelationKind.MANY_TO_MANY),))
        sql = render_postgres_schema(_ir((a, b)))
        # deterministic sorted pair -> one join table named book_tag
        self.assertEqual(sql.count("CREATE TABLE book_tag ("), 1)
        self.assertIn("PRIMARY KEY (book_id, tag_id)", sql)


class DeterminismAndGateTests(TestCase):
    def test_output_is_byte_stable(self) -> None:
        ir = example_ir("minimal-blog")
        self.assertEqual(render_postgres_schema(ir), render_postgres_schema(ir))

    def test_no_entities_is_empty(self) -> None:
        self.assertEqual(render_postgres_schema(_ir(())), "")


class AdapterEmissionTests(TestCase):
    def test_python_backend_emits_migration_for_postgres(self) -> None:
        project = PythonBackendAdapter().generate(example_ir("minimal-blog"))
        self.assertIn("migrations/0001_init.sql", project.paths())
        self.assertIn("CREATE TABLE post (", project.get("migrations/0001_init.sql").content)

    def test_go_backend_emits_migration_for_postgres(self) -> None:
        project = GoBackendAdapter().generate(example_ir("rideshare-favourites"))
        self.assertIn("migrations/0001_init.sql", project.paths())

    def test_no_migration_without_postgres(self) -> None:
        entity = Entity("Note", (Field("id", FieldType.UUID, True),))
        ir = _ir((entity,), database=DatabaseStrategy.OTHER)
        project = PythonBackendAdapter().generate(ir)
        self.assertNotIn("migrations/0001_init.sql", project.paths())

    def test_no_migration_without_entities(self) -> None:
        ir = _ir(())
        project = PythonBackendAdapter().generate(ir)
        self.assertNotIn("migrations/0001_init.sql", project.paths())

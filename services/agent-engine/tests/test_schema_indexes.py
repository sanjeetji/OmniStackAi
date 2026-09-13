from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    Index,
    InvalidIRError,
    MobileProfile,
    Platform,
    ProjectStrategy,
    RepoStrategy,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.application_ir.ir import AdminStrategy
from omnistackai_agent_engine.codegen import render_postgres_schema


def _ir(entity: Entity) -> ApplicationIR:
    return ApplicationIR(
        name="Acct",
        description="A tiny app.",
        platforms=(Platform.BACKEND,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NONE, AdminStrategy.NONE,
            BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        entities=(entity,),
    )


class UniqueColumnTests(TestCase):
    def test_unique_non_id_column_gets_unique(self) -> None:
        entity = Entity("Account", (Field("id", FieldType.UUID), Field("email", FieldType.STRING, unique=True)))
        sql = render_postgres_schema(_ir(entity))
        self.assertIn('"email" TEXT NOT NULL UNIQUE', sql)

    def test_id_is_never_unique_only_primary_key(self) -> None:
        # even if someone marks id unique, it stays PRIMARY KEY without a redundant UNIQUE
        entity = Entity("Account", (Field("id", FieldType.UUID, unique=True), Field("email", FieldType.STRING)))
        sql = render_postgres_schema(_ir(entity))
        self.assertIn('"id" UUID PRIMARY KEY DEFAULT gen_random_uuid()', sql)
        self.assertNotIn("PRIMARY KEY DEFAULT gen_random_uuid() UNIQUE", sql)


class IndexEmissionTests(TestCase):
    def test_single_nonunique_index_default_name(self) -> None:
        entity = Entity("Driver", (Field("id", FieldType.UUID), Field("name", FieldType.STRING)), indexes=(Index(("name",)),))
        sql = render_postgres_schema(_ir(entity))
        self.assertIn("-- Indexes", sql)
        self.assertIn('CREATE INDEX "driver_name_idx" ON "driver" ("name");', sql)

    def test_composite_unique_index_default_name(self) -> None:
        entity = Entity(
            "Account",
            (Field("id", FieldType.UUID), Field("tenant", FieldType.STRING), Field("handle", FieldType.STRING)),
            indexes=(Index(("tenant", "handle"), unique=True),),
        )
        sql = render_postgres_schema(_ir(entity))
        self.assertIn('CREATE UNIQUE INDEX "account_tenant_handle_key" ON "account" ("tenant", "handle");', sql)

    def test_named_index_is_respected(self) -> None:
        entity = Entity("Account", (Field("id", FieldType.UUID), Field("tenant", FieldType.STRING)), indexes=(Index(("tenant",), name="acct_tenant_lookup"),))
        sql = render_postgres_schema(_ir(entity))
        self.assertIn('CREATE INDEX "acct_tenant_lookup" ON "account" ("tenant");', sql)

    def test_no_index_section_without_indexes(self) -> None:
        entity = Entity("Account", (Field("id", FieldType.UUID),))
        self.assertNotIn("-- Indexes", render_postgres_schema(_ir(entity)))

    def test_example_driver_index_emitted(self) -> None:
        sql = render_postgres_schema(example_ir("rideshare-favourites"))
        self.assertIn('CREATE INDEX "driver_name_idx" ON "driver" ("name");', sql)


class ValidationTests(TestCase):
    def test_index_on_unknown_field_is_construction_error(self) -> None:
        with self.assertRaises(InvalidIRError):
            Entity("Account", (Field("id", FieldType.UUID),), indexes=(Index(("ghost",)),))

    def test_index_requires_nonempty_fields(self) -> None:
        with self.assertRaises(InvalidIRError):
            Index(())


class RoundTripTests(TestCase):
    def test_unique_and_indexes_survive_serialize(self) -> None:
        entity = Entity(
            "Account",
            (Field("id", FieldType.UUID), Field("email", FieldType.STRING, unique=True)),
            indexes=(Index(("email",), unique=True, name="acct_email_key"),),
        )
        ir = _ir(entity)
        restored = ApplicationIR.from_dict(ir.to_dict())
        self.assertEqual(restored, ir)
        self.assertTrue(restored.entities[0].fields[1].unique)
        self.assertEqual(restored.entities[0].indexes[0].name, "acct_email_key")

    def test_byte_stable(self) -> None:
        ir = example_ir("rideshare-favourites")
        self.assertEqual(render_postgres_schema(ir), render_postgres_schema(ir))

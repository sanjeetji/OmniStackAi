import ast
from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    Fixture,
    Index,
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
    go_data_access_files,
    python_data_access_files,
    render_postgres_schema,
    render_postgres_seed,
)


def _strategy() -> ProjectStrategy:
    return ProjectStrategy(
        mobile_profile=MobileProfile.NONE,
        web_strategy=WebStrategy.NONE,
        admin_strategy=AdminStrategy.NONE,
        backend_strategy=BackendStrategy.PYTHON,
        database_strategy=DatabaseStrategy.POSTGRES,
        repo_strategy=RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
    )


def _ir(entities: tuple[Entity, ...], fixtures: tuple[Fixture, ...] = ()) -> ApplicationIR:
    return ApplicationIR(
        name="SQL Safety",
        description="Exercises generated PostgreSQL identifiers and dependencies.",
        platforms=(Platform.WEB,),
        project_strategy=_strategy(),
        entities=entities,
        fixtures=fixtures,
    )


def _position(sql: str, statement: str) -> int:
    position = sql.find(statement)
    if position < 0:
        raise AssertionError(f"missing SQL statement: {statement}")
    return position


class QuotedIdentifierTests(TestCase):
    def setUp(self) -> None:
        self.user = Entity(
            "User",
            (Field("id", FieldType.UUID, True), Field("group", FieldType.STRING, True)),
        )
        self.order = Entity(
            "Order",
            (Field("id", FieldType.UUID, True), Field("select", FieldType.STRING, True)),
            (Relation("user", "User", RelationKind.MANY_TO_ONE),),
            (Index(("select",), name="where"),),
        )

    def test_schema_quotes_every_owned_identifier(self) -> None:
        sql = render_postgres_schema(_ir((self.order, self.user)))
        self.assertIn('CREATE TABLE "user" (', sql)
        self.assertIn('"group" TEXT NOT NULL', sql)
        self.assertIn('CREATE TABLE "order" (', sql)
        self.assertIn('"select" TEXT NOT NULL', sql)
        self.assertIn('"user_id" UUID REFERENCES "user"("id")', sql)
        self.assertIn('CREATE INDEX "where" ON "order" ("select");', sql)
        self.assertNotIn("CREATE TABLE order (", sql)

    def test_seed_and_repositories_use_the_same_quoted_names(self) -> None:
        fixtures = (
            Fixture("Order", ({"id": "o1", "select": "new", "user_id": "u1"},)),
            Fixture("User", ({"group": "buyer", "id": "u1"},)),
        )
        ir = _ir((self.order, self.user), fixtures)
        seed = render_postgres_seed(ir)
        self.assertLess(
            _position(seed, 'INSERT INTO "user" ("group", "id")'),
            _position(seed, 'INSERT INTO "order" ("id", "select", "user_id")'),
        )

        python_files = dict(python_data_access_files(ir, "sql-safety"))
        python_repo = python_files["app/repositories/order.py"]
        ast.parse(python_repo)
        self.assertIn("TABLE = '\"order\"'", python_repo)
        self.assertIn('"select"', python_repo)
        self.assertIn('"user_id"', python_repo)

        go_files = dict(go_data_access_files(ir, "sql-safety"))
        go_store = go_files["internal/store/order.go"]
        self.assertIn('FROM "order"', go_store)
        self.assertIn('INSERT INTO "order"', go_store)
        self.assertIn('"select"', go_store)
        self.assertIn('"user_id"', go_store)


class DependencyOrderingTests(TestCase):
    def test_transitive_child_before_parent_is_topologically_ordered(self) -> None:
        user = Entity("User", (Field("id", FieldType.UUID, True),))
        order = Entity(
            "Order",
            (Field("id", FieldType.UUID, True),),
            (Relation("user", "User", RelationKind.MANY_TO_ONE),),
        )
        line_item = Entity(
            "LineItem",
            (Field("id", FieldType.UUID, True),),
            (Relation("order", "Order", RelationKind.MANY_TO_ONE),),
        )
        sql = render_postgres_schema(_ir((line_item, order, user)))
        self.assertLess(_position(sql, 'CREATE TABLE "user"'), _position(sql, 'CREATE TABLE "order"'))
        self.assertLess(_position(sql, 'CREATE TABLE "order"'), _position(sql, 'CREATE TABLE "line_item"'))

    def test_independent_entities_keep_input_order(self) -> None:
        zebra = Entity("Zebra", (Field("id", FieldType.UUID, True),))
        apple = Entity("Apple", (Field("id", FieldType.UUID, True),))
        sql = render_postgres_schema(_ir((zebra, apple)))
        self.assertLess(_position(sql, 'CREATE TABLE "zebra"'), _position(sql, 'CREATE TABLE "apple"'))

    def test_self_reference_is_valid(self) -> None:
        node = Entity(
            "Node",
            (Field("id", FieldType.UUID, True),),
            (Relation("parent", "Node", RelationKind.MANY_TO_ONE),),
        )
        sql = render_postgres_schema(_ir((node,)))
        self.assertIn('"parent_id" UUID REFERENCES "node"("id")', sql)

    def test_non_self_cycle_fails_instead_of_emitting_invalid_sql(self) -> None:
        alpha = Entity(
            "Alpha",
            (Field("id", FieldType.UUID, True),),
            (Relation("beta", "Beta", RelationKind.MANY_TO_ONE),),
        )
        beta = Entity(
            "Beta",
            (Field("id", FieldType.UUID, True),),
            (Relation("alpha", "Alpha", RelationKind.ONE_TO_ONE),),
        )
        with self.assertRaisesRegex(ValueError, "cyclic foreign-key dependencies: Alpha, Beta"):
            render_postgres_schema(_ir((alpha, beta)))

    def test_output_remains_byte_stable(self) -> None:
        ir = example_ir("minimal-blog")
        self.assertEqual(render_postgres_schema(ir), render_postgres_schema(ir))
        self.assertEqual(render_postgres_seed(ir), render_postgres_seed(ir))

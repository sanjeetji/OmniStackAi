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
from omnistackai_agent_engine.codegen import (
    GoBackendAdapter,
    PythonBackendAdapter,
    go_data_access_files,
    python_data_access_files,
)


def _ir(entities: tuple[Entity, ...], *, backend=BackendStrategy.PYTHON, database=DatabaseStrategy.POSTGRES) -> ApplicationIR:
    return ApplicationIR(
        name="Shop App",
        description="A tiny shop.",
        platforms=(Platform.WEB,),
        project_strategy=ProjectStrategy(
            mobile_profile=MobileProfile.NONE,
            web_strategy=WebStrategy.NONE,
            admin_strategy=AdminStrategy.NONE,
            backend_strategy=backend,
            database_strategy=database,
            repo_strategy=RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        entities=entities,
    )


class PythonEmissionTests(TestCase):
    def test_repositories_emitted_and_valid_python(self) -> None:
        project = PythonBackendAdapter().generate(example_ir("minimal-blog"))
        paths = project.paths()
        self.assertIn("app/db.py", paths)
        self.assertIn("app/repositories/post.py", paths)
        self.assertIn("app/repositories/comment.py", paths)
        self.assertIn("psycopg", project.get("requirements.txt").content)
        for path in ("app/db.py", "app/repositories/post.py"):
            ast.parse(project.get(path).content)  # raises if not valid Python

    def test_values_are_parameterized(self) -> None:
        content = PythonBackendAdapter().generate(example_ir("minimal-blog")).get("app/repositories/post.py").content
        self.assertIn('WHERE "id" = %s', content)
        self.assertIn('", ".join(["%s"] * len(columns))', content)
        # the id value is passed as a parameter tuple, never formatted into the SQL string
        self.assertNotIn("WHERE id = '", content)


class GoEmissionTests(TestCase):
    def test_store_emitted_with_module_path_and_pgx(self) -> None:
        project = GoBackendAdapter().generate(example_ir("rideshare-favourites"))
        paths = project.paths()
        self.assertIn("internal/store/store.go", paths)
        self.assertIn("internal/store/driver.go", paths)
        self.assertIn("internal/store/favourite_driver.go", paths)
        self.assertIn("github.com/jackc/pgx/v5", project.get("go.mod").content)
        driver = project.get("internal/store/driver.go").content
        self.assertIn('"rideshare-favourites/internal/models"', driver)  # import path matches go.mod
        self.assertIn('WHERE "id" = $1', driver)
        self.assertIn("&m.Id", driver)  # scans into the generated model struct field


class GatingTests(TestCase):
    def test_no_data_access_without_postgres(self) -> None:
        ir = _ir((Entity("Note", (Field("id", FieldType.UUID, True),)),), database=DatabaseStrategy.OTHER)
        project = PythonBackendAdapter().generate(ir)
        self.assertNotIn("app/db.py", project.paths())
        self.assertNotIn("psycopg", project.get("requirements.txt").content)

    def test_no_data_access_without_entities(self) -> None:
        project = GoBackendAdapter().generate(_ir((), backend=BackendStrategy.GO))
        self.assertNotIn("internal/store/store.go", project.paths())
        self.assertNotIn("pgx", project.get("go.mod").content)


class IdOnlyEntityTests(TestCase):
    def test_id_only_entity_creates_via_default_values(self) -> None:
        ir = _ir((Entity("Ping", (Field("id", FieldType.UUID, True),)),))
        py = dict(python_data_access_files(ir, "shop-app"))["app/repositories/ping.py"]
        self.assertIn("INSERT INTO {TABLE} DEFAULT VALUES RETURNING *", py)
        go = dict(go_data_access_files(ir, "shop-app"))["internal/store/ping.go"]
        self.assertIn('INSERT INTO "ping" DEFAULT VALUES RETURNING "id"', go)


class DeterminismTests(TestCase):
    def test_output_is_byte_stable(self) -> None:
        ir = example_ir("minimal-blog")
        self.assertEqual(python_data_access_files(ir, "blog"), python_data_access_files(ir, "blog"))
        self.assertEqual(go_data_access_files(ir, "blog"), go_data_access_files(ir, "blog"))

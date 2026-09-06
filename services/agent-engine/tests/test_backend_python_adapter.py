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
    WebStrategy,
)
from omnistackai_agent_engine.codegen import (
    AdapterRegistry,
    FrameworkAdapter,
    GenerationTarget,
    PythonBackendAdapter,
)


def _ir() -> ApplicationIR:
    return ApplicationIR(
        name="Rideshare Favourites",
        description="Customers can favourite drivers.",
        platforms=(Platform.BACKEND,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NONE, AdminStrategy.NONE,
            BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        entities=(
            Entity("Driver", (Field("id", FieldType.UUID), Field("name", FieldType.STRING))),
            Entity("FavouriteDriver", (Field("id", FieldType.UUID), Field("created_at", FieldType.DATETIME, required=False))),
        ),
        apis=(
            ApiEndpoint(HttpMethod.POST, "/favourites/drivers/{driverId}", auth=True),
            ApiEndpoint(HttpMethod.GET, "/favourites/drivers", auth=True),
            ApiEndpoint(HttpMethod.GET, "/drivers", auth=False),
        ),
    )


class PythonBackendAdapterTests(TestCase):
    def setUp(self) -> None:
        self.project = PythonBackendAdapter().generate(_ir())

    def test_contract_and_target(self) -> None:
        adapter = PythonBackendAdapter()
        self.assertIsInstance(adapter, FrameworkAdapter)
        self.assertIs(adapter.target, GenerationTarget.BACKEND_PYTHON)

    def test_registry_wiring_alongside_web(self) -> None:
        from omnistackai_agent_engine.codegen import NextjsWebAdapter
        registry = AdapterRegistry()
        registry.register(NextjsWebAdapter())
        registry.register(PythonBackendAdapter())
        self.assertEqual(
            set(registry.targets()), {GenerationTarget.NEXTJS_WEB, GenerationTarget.BACKEND_PYTHON}
        )
        project = registry.get("backend-python").generate(_ir())
        self.assertEqual(project.target, "backend-python")

    def test_scaffold_files_present(self) -> None:
        paths = set(self.project.paths())
        for expected in (
            "requirements.txt", "app/__init__.py", "app/config.py", "app/models.py", "app/main.py",
            "app/routers/__init__.py", ".gitignore", ".env.example", "README.md",
        ):
            self.assertIn(expected, paths)

    def test_entities_become_pydantic_models(self) -> None:
        models = self.project.get("app/models.py").content
        self.assertIn("class Driver(BaseModel):", models)
        self.assertIn("class FavouriteDriver(BaseModel):", models)
        self.assertIn("name: str", models)
        self.assertIn("created_at: Optional[datetime] = None", models)
        self.assertIn("from pydantic import BaseModel", models)

    def test_routes_grouped_by_segment_with_params(self) -> None:
        paths = set(self.project.paths())
        self.assertIn("app/routers/favourites.py", paths)   # /favourites/* grouped
        self.assertIn("app/routers/drivers.py", paths)      # /drivers grouped
        fav = self.project.get("app/routers/favourites.py").content
        self.assertIn('@router.post("/favourites/drivers/{driverId}")', fav)
        self.assertIn("driverId: str", fav)                 # path param typed
        self.assertIn("status_code=501", fav)               # scaffold body

    def test_main_includes_routers_and_health(self) -> None:
        main = self.project.get("app/main.py").content
        self.assertIn("from fastapi import FastAPI", main)
        self.assertIn("app.include_router(favourites.router)", main)
        self.assertIn("app.include_router(drivers.router)", main)
        self.assertIn('@app.get("/healthz")', main)

    def test_requirements_and_no_secret(self) -> None:
        self.assertIn("fastapi==", self.project.get("requirements.txt").content)
        env = self.project.get(".env.example").content
        self.assertNotIn("sk-", env)
        self.assertIn("DATABASE_URL=", env)

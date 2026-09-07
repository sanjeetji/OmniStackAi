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
    GoBackendAdapter,
)


def _ir() -> ApplicationIR:
    return ApplicationIR(
        name="Rideshare Favourites",
        description="Customers can favourite drivers.",
        platforms=(Platform.BACKEND,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NONE, AdminStrategy.NONE,
            BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
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


class GoBackendAdapterTests(TestCase):
    def setUp(self) -> None:
        self.project = GoBackendAdapter().generate(_ir())

    def test_contract_and_target(self) -> None:
        adapter = GoBackendAdapter()
        self.assertIsInstance(adapter, FrameworkAdapter)
        self.assertIs(adapter.target, GenerationTarget.BACKEND_GO)

    def test_registry_wiring_tri_target(self) -> None:
        from omnistackai_agent_engine.codegen import NextjsWebAdapter, PythonBackendAdapter
        registry = AdapterRegistry()
        registry.register(NextjsWebAdapter())
        registry.register(PythonBackendAdapter())
        registry.register(GoBackendAdapter())
        self.assertEqual(
            set(registry.targets()),
            {GenerationTarget.NEXTJS_WEB, GenerationTarget.BACKEND_PYTHON, GenerationTarget.BACKEND_GO},
        )
        self.assertEqual(registry.get("backend-go").generate(_ir()).target, "backend-go")

    def test_scaffold_files_present(self) -> None:
        paths = set(self.project.paths())
        for expected in (
            "go.mod", "main.go", "internal/models/models.go", ".gitignore", ".env.example", "README.md",
        ):
            self.assertIn(expected, paths)

    def test_gomod_module_and_version(self) -> None:
        gomod = self.project.get("go.mod").content
        self.assertIn("module rideshare-favourites", gomod)
        self.assertIn("go 1.22", gomod)

    def test_entities_become_go_structs(self) -> None:
        models = self.project.get("internal/models/models.go").content
        self.assertIn("package models", models)
        self.assertIn("type Driver struct {", models)
        self.assertIn('Name string `json:"name"`', models)                         # required value type
        self.assertIn('CreatedAt *time.Time `json:"created_at,omitempty"`', models)  # optional pointer
        self.assertIn('"time"', models)                                             # import when used

    def test_routes_grouped_and_registered(self) -> None:
        paths = set(self.project.paths())
        self.assertIn("internal/handlers/favourites.go", paths)
        self.assertIn("internal/handlers/drivers.go", paths)
        fav = self.project.get("internal/handlers/favourites.go").content
        # POST /favourites/drivers/{driverId} has no unambiguous entity mapping -> stays a 501 method scaffold
        self.assertIn("func (h *Handlers) PostFavouritesDriversDriverId(w http.ResponseWriter, r *http.Request)", fav)
        self.assertIn("http.StatusNotImplemented", fav)
        main = self.project.get("main.go").content
        self.assertIn('mux.HandleFunc("POST /favourites/drivers/{driverId}", h.PostFavouritesDriversDriverId)', main)
        self.assertIn('mux.HandleFunc("GET /healthz"', main)
        self.assertIn('"rideshare-favourites/internal/handlers"', main)

    def test_no_secret_in_env_example(self) -> None:
        env = self.project.get(".env.example").content
        self.assertNotIn("sk-", env)
        self.assertIn("ADDR=:8080", env)

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
)
from omnistackai_agent_engine.codegen import (
    AdapterRegistry,
    FrameworkAdapter,
    GenerationTarget,
    ReactNativeAdapter,
    assemble_project,
    assembled_targets,
    default_registry,
)


def _ir(mobile: MobileProfile = MobileProfile.REACT_NATIVE) -> ApplicationIR:
    return ApplicationIR(
        name="TaskFlow Mobile",
        description="A mobile workflow manager for distributed teams.",
        platforms=(Platform.WEB, Platform.MOBILE, Platform.BACKEND),
        roles=(Role("user", ("read", "write")), Role("admin", ("read", "write", "admin"))),
        project_strategy=ProjectStrategy(
            mobile_profile=mobile,
            web_strategy=WebStrategy.NEXTJS,
            admin_strategy=AdminStrategy.NONE,
            backend_strategy=BackendStrategy.PYTHON,
            database_strategy=DatabaseStrategy.POSTGRES,
            repo_strategy=RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        entities=(
            Entity(
                "Task",
                (
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING),
                    Field("priority", FieldType.STRING),
                    Field("completed", FieldType.BOOL, required=False),
                ),
            ),
            Entity(
                "Project",
                (
                    Field("id", FieldType.UUID),
                    Field("name", FieldType.STRING),
                    Field("budget", FieldType.FLOAT, required=False),
                ),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/tasks", auth=True),
            ApiEndpoint(HttpMethod.POST, "/tasks", auth=True),
            ApiEndpoint(HttpMethod.GET, "/projects", auth=True),
        ),
        screens=(
            Screen("task_list", "user", ("list",), ("view", "delete")),
            Screen("task_editor", "user", ("form",), ("create", "edit")),
        ),
    )


class ReactNativeAdapterTests(TestCase):
    def setUp(self) -> None:
        self.ir = _ir()
        self.adapter = ReactNativeAdapter()
        self.project = self.adapter.generate(self.ir)

    def test_contract_and_target(self) -> None:
        self.assertIsInstance(self.adapter, FrameworkAdapter)
        self.assertIs(self.adapter.target, GenerationTarget.REACT_NATIVE)
        self.assertEqual(self.project.target, GenerationTarget.REACT_NATIVE.value)

    def test_registry_registration(self) -> None:
        registry = default_registry()
        adapter = registry.get(GenerationTarget.REACT_NATIVE)
        self.assertIsInstance(adapter, ReactNativeAdapter)

    def test_project_config_files_emitted(self) -> None:
        expected = [
            "package.json",
            "app.json",
            "tsconfig.json",
            "babel.config.js",
            "index.js",
        ]
        for path in expected:
            file = self.project.get(path)
            self.assertIsNotNone(file, f"missing {path}")
            self.assertGreater(len(file.content), 10)

        pkg = self.project.get("package.json")
        self.assertIn('"expo":', pkg.content)
        self.assertIn('"react-native":', pkg.content)
        self.assertIn('"@react-navigation/native":', pkg.content)

        app_json = self.project.get("app.json")
        self.assertIn('"name": "TaskFlow Mobile"', app_json.content)
        self.assertIn('"slug": "taskflow-mobile"', app_json.content)

    def test_design_system_emitted(self) -> None:
        expected = [
            "src/design-system/tokens.ts",
            "src/design-system/components/Button.tsx",
            "src/design-system/components/Card.tsx",
            "src/design-system/components/Badge.tsx",
            "src/design-system/components/Input.tsx",
            "src/design-system/components/StatCard.tsx",
            "src/design-system/components/ScreenContainer.tsx",
        ]
        for path in expected:
            file = self.project.get(path)
            self.assertIsNotNone(file, f"missing {path}")

        tokens = self.project.get("src/design-system/tokens.ts")
        self.assertIn("colors:", tokens.content)
        self.assertIn("radii:", tokens.content)

        btn = self.project.get("src/design-system/components/Button.tsx")
        self.assertIn("export const Button", btn.content)

    def test_shared_api_and_auth_emitted(self) -> None:
        client = self.project.get("src/shared/api/client.ts")
        self.assertIsNotNone(client)
        self.assertIn("apiClient =", client.content)

        auth = self.project.get("src/shared/auth/AuthContext.tsx")
        self.assertIsNotNone(auth)
        self.assertIn("export const AuthProvider", auth.content)

    def test_entity_features_emitted(self) -> None:
        for entity_slug, pascal in (("task", "Task"), ("project", "Project")):
            expected = [
                f"src/features/{entity_slug}/model/types.ts",
                f"src/features/{entity_slug}/api/client.ts",
                f"src/features/{entity_slug}/hooks/use{pascal}.ts",
                f"src/features/{entity_slug}/ui/{pascal}ListScreen.tsx",
                f"src/features/{entity_slug}/ui/{pascal}DetailScreen.tsx",
            ]
            for path in expected:
                file = self.project.get(path)
                self.assertIsNotNone(file, f"missing {path}")

            types = self.project.get(f"src/features/{entity_slug}/model/types.ts")
            self.assertIn(f"export interface {pascal}", types.content)

            hooks = self.project.get(f"src/features/{entity_slug}/hooks/use{pascal}.ts")
            self.assertIn(f"export const use{pascal}s", hooks.content)

    def test_navigation_and_app_root_emitted(self) -> None:
        overview = self.project.get("src/app/screens/OverviewScreen.tsx")
        self.assertIsNotNone(overview)
        self.assertIn("TaskFlow Mobile", overview.content)

        nav = self.project.get("src/app/navigation/RootNavigator.tsx")
        self.assertIsNotNone(nav)
        self.assertIn("createNativeStackNavigator", nav.content)
        self.assertIn('name="TaskList"', nav.content)
        self.assertIn('name="ProjectList"', nav.content)

        app = self.project.get("src/app/App.tsx")
        self.assertIsNotNone(app)
        self.assertIn("NavigationContainer", app.content)
        self.assertIn("SafeAreaProvider", app.content)
        self.assertIn("AuthProvider", app.content)

    def test_monorepo_assembly_with_react_native(self) -> None:
        targets = assembled_targets(self.ir)
        target_names = [t.target for t in targets]
        self.assertIn(GenerationTarget.REACT_NATIVE.value, target_names)
        self.assertIn(GenerationTarget.NEXTJS_WEB.value, target_names)
        self.assertIn(GenerationTarget.BACKEND_PYTHON.value, target_names)

        monorepo = assemble_project(self.ir)
        mobile_files = [f for f in monorepo.files() if f.path.startswith("apps/mobile/")]
        self.assertGreater(len(mobile_files), 15)

        app_json = monorepo.get("apps/mobile/app.json")
        self.assertIsNotNone(app_json)
        self.assertIn('"slug": "taskflow-mobile"', app_json.content)

    def test_skip_mobile_when_mobile_profile_none(self) -> None:
        web_only_ir = _ir(mobile=MobileProfile.NONE)
        targets = assembled_targets(web_only_ir)
        target_names = [t.target for t in targets]
        self.assertNotIn(GenerationTarget.REACT_NATIVE.value, target_names)

        monorepo = assemble_project(web_only_ir)
        mobile_files = [f for f in monorepo.files() if f.path.startswith("apps/mobile/")]
        self.assertEqual(len(mobile_files), 0)

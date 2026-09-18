import json
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
    Relation,
    RelationKind,
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
)
from omnistackai_agent_engine.codegen import (
    AdapterRegistry,
    FrameworkAdapter,
    GenerationTarget,
    NextjsWebAdapter,
)


def _ir() -> ApplicationIR:
    return ApplicationIR(
        name="Rideshare Favourites",
        description="Customers can favourite drivers.",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
            BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("customer"),),
        entities=(
            Entity("Driver", (Field("id", FieldType.UUID), Field("name", FieldType.STRING))),
            Entity(
                "FavouriteDriver",
                (Field("id", FieldType.UUID), Field("created_at", FieldType.DATETIME, required=False)),
                relations=(Relation("driver", "Driver", RelationKind.MANY_TO_ONE),),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.POST, "/favourites/drivers/{driverId}", auth=True),
            ApiEndpoint(HttpMethod.GET, "/favourites/drivers", auth=True, response_schema="FavouriteDriver"),
        ),
        screens=(Screen("favourites", "customer", components=("list",), actions=("add", "remove")),),
    )


class NextjsAdapterTests(TestCase):
    def setUp(self) -> None:
        self.project = NextjsWebAdapter().generate(_ir())

    def test_satisfies_contract_and_target(self) -> None:
        adapter = NextjsWebAdapter()
        self.assertIsInstance(adapter, FrameworkAdapter)
        self.assertIs(adapter.target, GenerationTarget.NEXTJS_WEB)

    def test_registry_wiring(self) -> None:
        registry = AdapterRegistry()
        registry.register(NextjsWebAdapter())
        project = registry.get("nextjs-web").generate(_ir())
        self.assertEqual(project.target, "nextjs-web")

    def test_scaffold_files_present(self) -> None:
        paths = set(self.project.paths())
        for expected in (
            "package.json", "tsconfig.json", "next.config.mjs", ".gitignore", ".env.example",
            "README.md", "app/layout.tsx", "app/page.tsx", "app/globals.css", "lib/types.ts",
            "lib/api.ts", "components/navbar.tsx", "app/favourites/page.tsx",
        ):
            self.assertIn(expected, paths)

    def test_package_json_is_valid_and_named(self) -> None:
        pkg = json.loads(self.project.get("package.json").content)
        self.assertEqual(pkg["name"], "rideshare-favourites")
        self.assertIn("next", pkg["dependencies"])

    def test_entities_become_typescript_interfaces(self) -> None:
        types = self.project.get("lib/types.ts").content
        self.assertIn("export interface Driver {", types)
        self.assertIn("export interface FavouriteDriver {", types)
        self.assertIn("created_at?: string;", types)   # optional field
        self.assertIn("name: string;", types)          # required field
        self.assertIn("driver?: Driver;", types)       # relation

    def test_dynamic_route_mapping_and_methods(self) -> None:
        paths = set(self.project.paths())
        self.assertIn("app/favourites/drivers/[driverId]/route.ts", paths)  # {driverId} -> [driverId]
        self.assertIn("app/favourites/drivers/route.ts", paths)
        post_route = self.project.get("app/favourites/drivers/[driverId]/route.ts").content
        self.assertIn("export async function POST(", post_route)
        get_route = self.project.get("app/favourites/drivers/route.ts").content
        self.assertIn("export async function GET(", get_route)

    def test_overview_and_no_secret(self) -> None:
        self.assertIn("Rideshare Favourites", self.project.get("app/page.tsx").content)
        env = self.project.get(".env.example").content
        self.assertNotIn("sk-", env)
        self.assertIn("NEXT_PUBLIC_APP_NAME", env)

    def test_next_config_has_security_headers(self) -> None:
        cfg = self.project.get("next.config.mjs").content
        self.assertIn("X-Frame-Options", cfg)
        self.assertIn("nosniff", cfg)


class DuplicateForeignKeyFieldTests(TestCase):
    """R-fix (2026-09-19): a real bug reproduced live - a follow-up edit's proposed entity can
    independently declare both an explicit field and a same-named relation for the same conceptual
    FK (e.g. an explicit `counter_id` field plus a `counter` relation), which used to emit a
    duplicate `counter_id?: string;` declaration in lib/types.ts - a real tsc failure (TS2300
    'Duplicate identifier', TS2687, TS2717) observed live. The explicit field's own declaration
    must always win; the synthesized one from the relation must never duplicate it."""

    def test_explicit_fk_field_is_not_duplicated_by_its_relation(self) -> None:
        ir = ApplicationIR(
            name="Counter App",
            description="A counter with favorites.",
            platforms=(Platform.WEB, Platform.BACKEND),
            project_strategy=ProjectStrategy(
                MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
                BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
            ),
            roles=(Role("user"),),
            entities=(
                Entity("Counter", (Field("id", FieldType.UUID), Field("value", FieldType.INT))),
                Entity(
                    "Favorite",
                    (
                        Field("id", FieldType.UUID),
                        # The exact shape observed live: an explicit FK field alongside a
                        # same-named to-one relation for the same conceptual foreign key.
                        Field("counter_id", FieldType.UUID),
                    ),
                    relations=(Relation("counter", "Counter", RelationKind.MANY_TO_ONE),),
                ),
            ),
            screens=(Screen("counters", "user", components=("list",)),),
        )
        types = NextjsWebAdapter().generate(ir).get("lib/types.ts").content
        self.assertEqual(types.count("counter_id"), 1, types)

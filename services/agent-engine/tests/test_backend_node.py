"""Unit tests for Node.js backend framework adapter (Express & Hono)."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

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
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import (
    ExpressBackendAdapter,
    FrameworkAdapter,
    GenerationTarget,
    HonoBackendAdapter,
    NodeBackendAdapter,
    default_registry,
)


def _make_test_ir(description: str = "Test backend API") -> ApplicationIR:
    entities = (
        Entity(
            name="Task",
            fields=(
                Field("id", FieldType.UUID, required=True),
                Field("title", FieldType.STRING, required=True),
                Field("description", FieldType.TEXT, required=False),
                Field("priority", FieldType.INT, required=False),
                Field("completed", FieldType.BOOL, required=True),
                Field("project_id", FieldType.UUID, required=False),
            ),
            relations=(
                Relation(name="project", target_entity="Project", kind=RelationKind.MANY_TO_ONE),
            ),
        ),
        Entity(
            name="Project",
            fields=(
                Field("id", FieldType.UUID, required=True),
                Field("name", FieldType.STRING, required=True),
            ),
        ),
    )
    apis = (
        ApiEndpoint(
            HttpMethod.GET,
            "/tasks",
            response_schema="Task",
            auth=False,
        ),
        ApiEndpoint(
            HttpMethod.GET,
            "/tasks/{id}",
            response_schema="Task",
            auth=False,
        ),
        ApiEndpoint(
            HttpMethod.POST,
            "/tasks",
            request_schema="Task",
            response_schema="Task",
            auth=True,
        ),
        ApiEndpoint(
            HttpMethod.PATCH,
            "/tasks/{id}",
            request_schema="Task",
            response_schema="Task",
            auth=True,
        ),
        ApiEndpoint(
            HttpMethod.DELETE,
            "/tasks/{id}",
            response_schema="Task",
            auth=True,
        ),
        ApiEndpoint(
            HttpMethod.GET,
            "/projects/{projectId}/tasks",
            response_schema="Task",
            auth=False,
        ),
        ApiEndpoint(
            HttpMethod.GET,
            "/custom/stats",
            auth=False,
        ),
    )
    return ApplicationIR(
        name="TaskMaster",
        description=description,
        platforms=(Platform.BACKEND,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE,
            WebStrategy.NONE,
            AdminStrategy.NONE,
            BackendStrategy.NODE,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        entities=entities,
        apis=apis,
        roles=(Role("admin"), Role("member")),
    )


class TestNodeBackendAdapter(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = _make_test_ir()
        self.adapter = NodeBackendAdapter(framework="express")
        self.project = self.adapter.generate(self.ir)

    def test_contract_and_target(self) -> None:
        self.assertIsInstance(self.adapter, FrameworkAdapter)
        self.assertIs(self.adapter.target, GenerationTarget.BACKEND_NODE)
        self.assertEqual(self.project.target, GenerationTarget.BACKEND_NODE.value)

    def test_registry_registration(self) -> None:
        registry = default_registry()
        adapter = registry.get(GenerationTarget.BACKEND_NODE)
        self.assertIsInstance(adapter, NodeBackendAdapter)

    def test_express_files_emitted(self) -> None:
        paths = set(self.project.paths())
        required_paths = {
            "package.json",
            "tsconfig.json",
            ".env.example",
            "README.md",
            "src/index.ts",
            "src/app.ts",
            "src/config.ts",
            "src/models/types.ts",
            "src/models/validation.ts",
            "src/db/pool.ts",
            "src/db/task.ts",
            "src/db/project.ts",
            "src/middleware/auth.ts",
            "src/routes/tasks.ts",
            "src/routes/projects.ts",
            "src/routes/custom.ts",
            "schema.sql",
            "seed.sql",
            "contracts/openapi.json",
        }
        for p in required_paths:
            self.assertIn(p, paths, f"Missing required path: {p}")

    def test_express_package_json(self) -> None:
        pkg_file = self.project.get("package.json")
        data = json.loads(pkg_file.content)
        self.assertEqual(data["name"], "taskmaster-api")
        self.assertEqual(data["type"], "module")
        self.assertIn("express", data["dependencies"])
        self.assertIn("cors", data["dependencies"])
        self.assertIn("zod", data["dependencies"])
        self.assertIn("pg", data["dependencies"])
        self.assertIn("tsx", data["devDependencies"])
        self.assertIn("typescript", data["devDependencies"])
        self.assertEqual(data["scripts"]["dev"], "tsx watch src/index.ts")

    def test_express_routes_and_crud(self) -> None:
        routes_ts = self.project.get("src/routes/tasks.ts").content
        # Router created
        self.assertIn("export const router = Router();", routes_ts)
        # requireAuth imported and used
        self.assertIn("requireAuth", routes_ts)
        # LIST op
        self.assertIn("TaskRepository.list", routes_ts)
        # GET op
        self.assertIn("TaskRepository.getById", routes_ts)
        # CREATE op with zod validation
        self.assertIn("createTaskSchema.safeParse", routes_ts)
        self.assertIn("TaskRepository.create", routes_ts)
        # UPDATE op with zod validation
        self.assertIn("updateTaskSchema.safeParse", routes_ts)
        self.assertIn("TaskRepository.update", routes_ts)
        # DELETE op
        self.assertIn("TaskRepository.delete", routes_ts)

    def test_models_and_zod_validation(self) -> None:
        types_ts = self.project.get("src/models/types.ts").content
        self.assertIn("export interface Task {", types_ts)
        self.assertIn("title: string;", types_ts)
        self.assertIn("completed: boolean;", types_ts)
        self.assertIn("export type CreateTaskInput =", types_ts)

        valid_ts = self.project.get("src/models/validation.ts").content
        self.assertIn("export const createTaskSchema = z.object({", valid_ts)
        self.assertIn("title: z.string(),", valid_ts)
        self.assertIn("completed: z.boolean(),", valid_ts)
        self.assertIn("export const updateTaskSchema = createTaskSchema.partial();", valid_ts)

    def test_hono_framework_variant(self) -> None:
        adapter = HonoBackendAdapter()
        project = adapter.generate(self.ir)
        paths = set(project.paths())

        self.assertIn("package.json", paths)
        pkg_data = json.loads(project.get("package.json").content)
        self.assertIn("hono", pkg_data["dependencies"])
        self.assertIn("@hono/node-server", pkg_data["dependencies"])
        self.assertNotIn("express", pkg_data["dependencies"])

        app_ts = project.get("src/app.ts").content
        self.assertIn("export const app = new Hono();", app_ts)
        self.assertIn("app.route('/api/tasks'", app_ts)

        index_ts = project.get("src/index.ts").content
        self.assertIn("serve({", index_ts)

        routes_ts = project.get("src/routes/tasks.ts").content
        self.assertIn("export const router = new Hono();", routes_ts)
        self.assertIn("c.json", routes_ts)

    def test_hono_auto_detection_from_prompt(self) -> None:
        ir_hono = _make_test_ir(description="High performance backend using Hono and TypeScript")
        adapter = NodeBackendAdapter(framework="express")
        project = adapter.generate(ir_hono)
        pkg_data = json.loads(project.get("package.json").content)
        # Should auto-detect Hono from description
        self.assertIn("hono", pkg_data["dependencies"])

    def test_determinism(self) -> None:
        proj1 = self.adapter.generate(self.ir)
        proj2 = self.adapter.generate(self.ir)
        self.assertEqual(proj1.paths(), proj2.paths())
        for path in proj1.paths():
            self.assertEqual(proj1.get(path).content, proj2.get(path).content)

    def test_node_syntax_validation(self) -> None:
        # Verify that emitted TypeScript files are syntactically valid and parseable by Node.js
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            types_file = tmp_path / "types.ts"
            types_file.write_text(self.project.get("src/models/types.ts").content, encoding="utf-8")

            res = subprocess.run(
                ["node", "--experimental-strip-types", str(types_file)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, f"TypeScript parse error: {res.stderr}")


if __name__ == "__main__":
    unittest.main()

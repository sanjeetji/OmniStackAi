"""Tests for Solution Pack Multi-Surface CI/CD Workflow & GitHub Actions Orchestration (R-452)."""

import io
import json
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from omnistackai_agent_engine.solution_packs.ecosystem_cicd import (
    CIJob,
    CIJobStep,
    CIWorkflow,
    EcosystemCICDContract,
    EcosystemCICDEngine,
    generate_github_actions_workflow,
    synthesize_ecosystem_cicd,
    to_workflow_yaml,
)


class FakePlan:
    has_web = True
    web_url = "http://127.0.0.1:3000"
    api_url = None
    backend_kind = "none"


class FakeSession:
    plan = FakePlan()
    web_ready = True
    api_ready = False

    def is_alive(self):
        return True

    def stop(self):
        pass


class TestEcosystemCICDContracts(unittest.TestCase):
    def test_job_step_roundtrip(self):
        step = CIJobStep(
            name="Run Test Suite",
            run="pnpm test:unit",
            working_directory="apps/web",
            env={"NODE_ENV": "test"},
            with_args={"cache": "pnpm"},
        )
        data = step.to_dict()
        restored = CIJobStep.from_dict(data)
        self.assertEqual(restored.name, "Run Test Suite")
        self.assertEqual(restored.run, "pnpm test:unit")
        self.assertEqual(restored.working_directory, "apps/web")
        self.assertEqual(restored.env, {"NODE_ENV": "test"})
        self.assertEqual(restored.with_args, {"cache": "pnpm"})

    def test_job_roundtrip(self):
        step = CIJobStep(
            name="Checkout",
            uses="actions/checkout@v4",
        )
        job = CIJob(
            job_id="verify-web",
            name="Verify Web Surface",
            runs_on="ubuntu-latest",
            surface_slug="web",
            needs=("setup-env",),
            steps=(step,),
            env={"CI": "true"},
            services={"postgres": {"image": "postgres:16-alpine"}},
        )
        data = job.to_dict()
        restored = CIJob.from_dict(data)
        self.assertEqual(restored.job_id, "verify-web")
        self.assertEqual(restored.runs_on, "ubuntu-latest")
        self.assertEqual(restored.surface_slug, "web")
        self.assertEqual(restored.needs, ("setup-env",))
        self.assertEqual(len(restored.steps), 1)
        self.assertEqual(restored.steps[0].uses, "actions/checkout@v4")
        self.assertEqual(restored.services["postgres"]["image"], "postgres:16-alpine")

    def test_workflow_and_contract_roundtrip(self):
        step = CIJobStep(name="Checkout", uses="actions/checkout@v4")
        job = CIJob(job_id="test", name="Run Tests", runs_on="ubuntu-latest", steps=(step,))
        wf = CIWorkflow(
            workflow_id="ci-main",
            name="CI Pipeline",
            triggers=("push", "pull_request"),
            jobs=(job,),
            env={"PLATFORM": "omnistackai"},
        )
        contract = EcosystemCICDContract(
            ecosystem_id="blog-eco",
            version="1.0.0",
            workflows=(wf,),
            surfaces_covered=("web",),
        )
        data = contract.to_dict()
        restored = EcosystemCICDContract.from_dict(data)
        self.assertEqual(restored.ecosystem_id, "blog-eco")
        self.assertEqual(restored.version, "1.0.0")
        self.assertEqual(len(restored.workflows), 1)
        self.assertEqual(restored.workflows[0].workflow_id, "ci-main")
        self.assertEqual(len(restored.workflows[0].jobs), 1)
        self.assertEqual(restored.workflows[0].jobs[0].job_id, "test")


class TestWorkflowYAMLGenerator(unittest.TestCase):
    def test_github_actions_yaml_generation(self):
        steps = (
            CIJobStep(name="Checkout Code", uses="actions/checkout@v4"),
            CIJobStep(
                name="Setup Node.js",
                uses="actions/setup-node@v4",
                with_args={"node-version": "20.x"},
            ),
            CIJobStep(
                name="Install Dependencies",
                run="pnpm install --frozen-lockfile",
                working_directory="apps/web",
            ),
        )
        job = CIJob(
            job_id="verify-web",
            name="Verify Web",
            runs_on="ubuntu-latest",
            surface_slug="web",
            steps=steps,
        )
        wf = CIWorkflow(
            workflow_id="ecosystem-ci",
            name="Ecosystem Continuous Integration",
            triggers=("push", "pull_request", "workflow_dispatch"),
            jobs=(job,),
        )
        yaml_content = generate_github_actions_workflow(wf)
        self.assertIn("name: Ecosystem Continuous Integration", yaml_content)
        self.assertIn("push:", yaml_content)
        self.assertIn("pull_request:", yaml_content)
        self.assertIn("workflow_dispatch:", yaml_content)
        self.assertIn("jobs:", yaml_content)
        self.assertIn("verify-web:", yaml_content)
        self.assertIn("runs-on: ubuntu-latest", yaml_content)
        self.assertIn("uses: actions/checkout@v4", yaml_content)
        self.assertIn("with:", yaml_content)
        self.assertIn("node-version: 20.x", yaml_content)
        self.assertIn("run: pnpm install --frozen-lockfile", yaml_content)
        self.assertIn("working-directory: apps/web", yaml_content)

    def test_services_and_needs_in_yaml(self):
        job1 = CIJob(
            job_id="db-setup",
            name="Setup DB",
            runs_on="ubuntu-latest",
            steps=(CIJobStep(name="Step 1", run="echo 1"),),
        )
        job2 = CIJob(
            job_id="api-test",
            name="Test API",
            runs_on="ubuntu-latest",
            needs=("db-setup",),
            services={
                "postgres": {
                    "image": "postgres:16-alpine",
                    "ports": ["5432:5432"],
                    "env": {"POSTGRES_PASSWORD": "test"},
                }
            },
            steps=(CIJobStep(name="Step 2", run="pytest"),),
        )
        wf = CIWorkflow(
            workflow_id="pipeline",
            name="Test Pipeline",
            triggers=("push",),
            jobs=(job1, job2),
        )
        contract = EcosystemCICDContract(ecosystem_id="test", workflows=(wf,))
        yaml_text = to_workflow_yaml(contract)
        self.assertIn("needs:\n      - db-setup", yaml_text)
        self.assertIn("services:", yaml_text)
        self.assertIn("postgres:", yaml_text)
        self.assertIn("image: postgres:16-alpine", yaml_text)


class TestEcosystemCICDEngine(unittest.TestCase):
    def test_valid_dag_validation_and_topological_sort(self):
        job_a = CIJob(job_id="build", name="Build", runs_on="ubuntu-latest", steps=())
        job_b = CIJob(job_id="test-unit", name="Unit Tests", runs_on="ubuntu-latest", needs=("build",), steps=())
        job_c = CIJob(job_id="test-e2e", name="E2E Tests", runs_on="ubuntu-latest", needs=("build",), steps=())
        job_d = CIJob(job_id="deploy", name="Deploy", runs_on="ubuntu-latest", needs=("test-unit", "test-e2e"), steps=())

        wf = CIWorkflow(workflow_id="ci", name="CI", triggers=("push",), jobs=(job_a, job_b, job_c, job_d))
        contract = EcosystemCICDContract(ecosystem_id="eco", workflows=(wf,))
        engine = EcosystemCICDEngine(contract)

        valid, msg = engine.validate_dag()
        self.assertTrue(valid)
        self.assertIn("Valid", msg)

        order = engine.topological_sort("ci")
        order_ids = [j.job_id for j in order]
        self.assertEqual(order_ids[0], "build")
        self.assertEqual(order_ids[-1], "deploy")
        self.assertTrue(order_ids.index("build") < order_ids.index("test-unit"))
        self.assertTrue(order_ids.index("build") < order_ids.index("test-e2e"))
        self.assertTrue(order_ids.index("test-unit") < order_ids.index("deploy"))
        self.assertTrue(order_ids.index("test-e2e") < order_ids.index("deploy"))

    def test_dag_cycle_detection(self):
        job1 = CIJob(job_id="j1", name="Job 1", runs_on="ubuntu-latest", needs=("j2",), steps=())
        job2 = CIJob(job_id="j2", name="Job 2", runs_on="ubuntu-latest", needs=("j1",), steps=())
        wf = CIWorkflow(workflow_id="cycle-wf", name="Cycle", triggers=("push",), jobs=(job1, job2))
        contract = EcosystemCICDContract(ecosystem_id="eco", workflows=(wf,))
        engine = EcosystemCICDEngine(contract)

        valid, err = engine.validate_dag()
        self.assertFalse(valid)
        self.assertIn("Cycle detected", err)

        with self.assertRaises(ValueError):
            engine.topological_sort("cycle-wf")

    def test_missing_dependency_detection(self):
        job1 = CIJob(job_id="j1", name="Job 1", runs_on="ubuntu-latest", needs=("non-existent",), steps=())
        wf = CIWorkflow(workflow_id="missing-dep-wf", name="Missing", triggers=("push",), jobs=(job1,))
        contract = EcosystemCICDContract(ecosystem_id="eco", workflows=(wf,))
        engine = EcosystemCICDEngine(contract)

        valid, err = engine.validate_dag()
        self.assertFalse(valid)
        self.assertIn("unknown job", err)

    def test_simulation_run(self):
        job1 = CIJob(
            job_id="setup",
            name="Setup",
            runs_on="ubuntu-latest",
            steps=(CIJobStep(name="S1", run="echo 1"),),
        )
        job2 = CIJob(
            job_id="verify",
            name="Verify",
            runs_on="ubuntu-latest",
            needs=("setup",),
            steps=(
                CIJobStep(name="S2", run="echo 2"),
                CIJobStep(name="S3", run="echo 3"),
            ),
        )
        wf = CIWorkflow(workflow_id="sim-wf", name="Sim", triggers=("push",), jobs=(job1, job2))
        contract = EcosystemCICDContract(ecosystem_id="eco", workflows=(wf,))
        engine = EcosystemCICDEngine(contract)

        res = engine.simulate_pipeline_run("sim-wf")
        self.assertEqual(res["status"], "passed")
        self.assertEqual(len(res["jobs"]), 2)
        self.assertEqual(res["jobs"][0]["job_id"], "setup")
        self.assertEqual(len(res["jobs"][0]["steps"]), 1)
        self.assertEqual(res["jobs"][1]["job_id"], "verify")
        self.assertEqual(len(res["jobs"][1]["steps"]), 2)
        self.assertGreater(res["total_duration_ms"], 0)


class TestEcosystemCICDSynthesis(unittest.TestCase):
    def test_synthesis_multi_surface(self):
        surfaces = (
            {
                "slug": "web",
                "app_name": "Blog Web",
                "surface_kind": "web",
                "runtime_target": "node",
                "ir": {"technology_stack": {"frontend_framework": "Next.js"}},
            },
            {
                "slug": "api",
                "app_name": "Blog API",
                "surface_kind": "api",
                "runtime_target": "python",
                "ir": {"technology_stack": {"backend_framework": "FastAPI", "database": "PostgreSQL"}},
            },
            {
                "slug": "worker",
                "app_name": "Event Worker",
                "surface_kind": "worker",
                "runtime_target": "go",
                "ir": {"technology_stack": {"backend_framework": "Go", "database": "PostgreSQL"}},
            },
        )
        contract = synthesize_ecosystem_cicd("blog-eco", surfaces)
        self.assertEqual(contract.ecosystem_id, "blog-eco")
        self.assertEqual(len(contract.workflows), 1)

        wf = contract.workflows[0]
        self.assertEqual(wf.workflow_id, "ecosystem-ci")
        # 3 surfaces + 1 ecosystem-integration job = 4 jobs
        self.assertEqual(len(wf.jobs), 4)

        job_ids = [j.job_id for j in wf.jobs]
        self.assertIn("test-web", job_ids)
        self.assertIn("test-api", job_ids)
        self.assertIn("test-worker", job_ids)
        self.assertIn("ecosystem-integration", job_ids)

        # test-web uses pnpm
        web_job = next(j for j in wf.jobs if j.job_id == "test-web")
        step_runs = [s.run for s in web_job.steps if s.run]
        self.assertTrue(any("pnpm install" in r for r in step_runs))

        # test-api uses python/pip and has postgres service
        api_job = next(j for j in wf.jobs if j.job_id == "test-api")
        self.assertIn("postgres", api_job.services)
        api_runs = [s.run for s in api_job.steps if s.run]
        self.assertTrue(any("pytest" in r for r in api_runs))

        # test-worker uses go test and has postgres service
        worker_job = next(j for j in wf.jobs if j.job_id == "test-worker")
        self.assertIn("postgres", worker_job.services)
        worker_runs = [s.run for s in worker_job.steps if s.run]
        self.assertTrue(any("go test" in r for r in worker_runs))

        # ecosystem-integration depends on all surface verification jobs
        verify_job = next(j for j in wf.jobs if j.job_id == "ecosystem-integration")
        self.assertIn("test-web", verify_job.needs)
        self.assertIn("test-api", verify_job.needs)
        self.assertIn("test-worker", verify_job.needs)

        # Engine validation should pass
        engine = EcosystemCICDEngine(contract)
        valid, err = engine.validate_dag()
        self.assertTrue(valid, err)


class TestEcosystemPackCICDIntegration(unittest.TestCase):
    def test_ecosystem_pack_bundling_and_integrity(self):
        from omnistackai_agent_engine.solution_packs.ecosystem_pack import synthesize_ecosystem_pack
        from omnistackai_agent_engine.solution_packs.registry import DEFAULT_SOLUTION_PACK_REGISTRY

        pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        self.assertIsNotNone(pack)

        eco_pkg = synthesize_ecosystem_pack(pack)
        self.assertIsNotNone(eco_pkg.cicd_contract)
        self.assertEqual(eco_pkg.cicd_contract.ecosystem_id, "minimal-blog-ecosystem")

        # Serialized JSON should include cicd_contract and verify integrity
        raw_json = eco_pkg.to_json()
        from omnistackai_agent_engine.solution_packs.ecosystem_pack import parse_ecosystem_pack_package
        restored = parse_ecosystem_pack_package(raw_json.encode("utf-8"))
        self.assertIsNotNone(restored.cicd_contract)
        self.assertEqual(len(restored.cicd_contract.workflows), 1)

    def test_ecosystem_registry_lookup(self):
        from omnistackai_agent_engine.solution_packs.ecosystem_registry import DEFAULT_ECOSYSTEM_PACK_REGISTRY

        eco_pack = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get("minimal-blog-ecosystem")
        self.assertIsNotNone(eco_pack)
        self.assertIsNotNone(eco_pack.cicd_contract)

        direct_lookup = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_cicd_contract("minimal-blog-ecosystem")
        self.assertIsNotNone(direct_lookup)
        self.assertEqual(direct_lookup.ecosystem_id, "minimal-blog-ecosystem")


class TestStudioCICDEndpoints(unittest.TestCase):
    def test_studio_preview_manager_cicd(self):
        from omnistackai_agent_engine.studio.preview import StudioPreviewManager

        manager = StudioPreviewManager(start_fn=lambda *args, **kwargs: FakeSession())
        surfaces = [
            {"slug": "web", "app_name": "Web", "surface_kind": "web"},
            {"slug": "admin", "app_name": "Admin", "surface_kind": "admin"},
        ]
        manager.replace_ecosystem("test-eco", surfaces=surfaces)

        status = manager.status()
        self.assertTrue(status["has_cicd"])
        self.assertGreater(status["cicd_workflow_count"], 0)
        self.assertGreater(status["cicd_job_count"], 0)
        self.assertEqual(status["cicd_status"], "configured")

        # Check methods
        cicd_info = manager.get_ecosystem_cicd()
        self.assertTrue(cicd_info["is_ecosystem"])
        self.assertIn("cicd_contract", cicd_info)

        yaml_text = manager.to_workflow_yaml()
        self.assertIn("name: \"Ecosystem Multi-Surface CI/CD (test-eco)\"", yaml_text)

        sim_res = manager.simulate_cicd_run()
        self.assertEqual(sim_res["status"], "ok")
        self.assertEqual(sim_res["simulation"]["status"], "passed")

    def test_studio_server_cicd_endpoints(self):
        from omnistackai_agent_engine.studio.preview import StudioPreviewManager
        from omnistackai_agent_engine.studio.server import create_studio_server

        manager = StudioPreviewManager(start_fn=lambda *args, **kwargs: FakeSession())
        surfaces = [
            {"slug": "web", "app_name": "Web", "surface_kind": "web"},
            {"slug": "admin", "app_name": "Admin", "surface_kind": "admin"},
        ]
        manager.replace_ecosystem("test-eco", surfaces=surfaces)

        server = create_studio_server(
            build_fn=lambda p, **kw: {},
            port=0,
            get_ecosystem_cicd_fn=manager.get_ecosystem_cicd,
            to_workflow_yaml_fn=manager.to_workflow_yaml,
            simulate_cicd_run_fn=manager.simulate_cicd_run,
        )
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        port = server.server_address[1]
        base_url = f"http://127.0.0.1:{port}"

        try:
            # 1. GET /api/ecosystem/cicd
            with urlopen(f"{base_url}/api/ecosystem/cicd") as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode())
                self.assertTrue(data["is_ecosystem"])
                self.assertIn("cicd_contract", data)
                self.assertGreater(data["job_count"], 0)

            # 2. GET /api/ecosystem/cicd/yaml
            with urlopen(f"{base_url}/api/ecosystem/cicd/yaml") as resp:
                self.assertEqual(resp.status, 200)
                self.assertEqual(resp.headers.get("Content-Type"), "text/yaml; charset=utf-8")
                yaml_str = resp.read().decode()
                self.assertIn("name: \"Ecosystem Multi-Surface CI/CD (test-eco)\"", yaml_str)

            # 3. POST /api/ecosystem/cicd/simulate
            req = Request(
                f"{base_url}/api/ecosystem/cicd/simulate",
                data=json.dumps({}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                sim_data = json.loads(resp.read().decode())
                self.assertEqual(sim_data["status"], "ok")
                self.assertEqual(sim_data["simulation"]["status"], "passed")
                self.assertGreater(len(sim_data["simulation"]["jobs"]), 0)
        finally:
            server.shutdown()
            server.server_close()


class TestEcosystemCLICICD(unittest.TestCase):
    def test_cli_cicd_subcommand(self):
        from omnistackai_agent_engine.solution_packs import ecosystem_cli

        # 1. Summary
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = ecosystem_cli.main(["cicd", "minimal-blog-ecosystem"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("Ecosystem CI/CD:", out)
        self.assertIn("minimal-blog-ecosystem", out)
        self.assertIn("Workflow 'ecosystem-ci'", out)

        # 2. JSON
        buf_json = io.StringIO()
        with patch("sys.stdout", buf_json):
            rc_json = ecosystem_cli.main(["cicd", "minimal-blog-ecosystem", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["ecosystem_id"], "minimal-blog-ecosystem")
        self.assertGreater(len(parsed["workflows"]), 0)

        # 3. YAML
        buf_yaml = io.StringIO()
        with patch("sys.stdout", buf_yaml):
            rc_yaml = ecosystem_cli.main(["cicd", "minimal-blog-ecosystem", "--yaml"])
        self.assertEqual(rc_yaml, 0)
        yaml_out = buf_yaml.getvalue()
        self.assertIn("name: \"Ecosystem Multi-Surface CI/CD (minimal-blog-ecosystem)\"", yaml_out)

        # 4. Simulate
        buf_sim = io.StringIO()
        with patch("sys.stdout", buf_sim):
            rc_sim = ecosystem_cli.main(["cicd", "minimal-blog-ecosystem", "--simulate"])
        self.assertEqual(rc_sim, 0)
        sim_out = buf_sim.getvalue()
        self.assertIn("CI/CD Simulation: PASSED", sim_out)
        self.assertIn("Executed Jobs", sim_out)


if __name__ == "__main__":
    unittest.main()

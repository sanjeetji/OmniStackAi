"""Unit and integration tests for Solution Pack Ecosystem Multi-Surface Export,
Deployment Manifest, and Live Gateway Orchestration (R-450)."""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from omnistackai_agent_engine.solution_packs.ecosystem_deployment import (
    EcosystemDeploymentManifest,
    EcosystemLiveGateway,
    GatewayRoute,
    SurfaceDeploymentSpec,
    generate_docker_compose,
    match_gateway_route,
    synthesize_ecosystem_deployment,
)
from omnistackai_agent_engine.solution_packs.ecosystem_pack import (
    EcosystemPackPackage,
    parse_ecosystem_pack_package,
    synthesize_ecosystem_pack,
    verify_ecosystem_pack,
)
from omnistackai_agent_engine.solution_packs.ecosystem_registry import (
    DEFAULT_ECOSYSTEM_PACK_REGISTRY,
)
from omnistackai_agent_engine.studio.preview import StudioPreviewManager


class TestGatewayRoute(unittest.TestCase):
    def test_gateway_route_creation_and_dict_roundtrip(self) -> None:
        route = GatewayRoute(
            route_id="route-admin",
            path_prefix="/admin",
            target_surface="cms-admin",
            target_port=3002,
            strip_prefix=False,
            auth_required=True,
            required_role="admin",
        )
        d = route.to_dict()
        self.assertEqual(d["route_id"], "route-admin")
        self.assertEqual(d["path_prefix"], "/admin")
        self.assertEqual(d["target_surface"], "cms-admin")
        self.assertEqual(d["target_port"], 3002)
        self.assertFalse(d["strip_prefix"])
        self.assertTrue(d["auth_required"])
        self.assertEqual(d["required_role"], "admin")

        restored = GatewayRoute.from_dict(d)
        self.assertEqual(restored, route)

    def test_gateway_route_matching(self) -> None:
        route_root = GatewayRoute("r-root", "/", "web", 3000)
        route_api = GatewayRoute("r-api", "/api", "backend", 8000)
        route_admin = GatewayRoute("r-admin", "/admin", "admin-panel", 3002)

        routes = (route_root, route_api, route_admin)

        # Longest prefix match
        match1 = match_gateway_route(routes, "/api/posts")
        self.assertIsNotNone(match1)
        self.assertEqual(match1.target_surface, "backend")

        match2 = match_gateway_route(routes, "/admin/settings")
        self.assertIsNotNone(match2)
        self.assertEqual(match2.target_surface, "admin-panel")

        match3 = match_gateway_route(routes, "/about")
        self.assertIsNotNone(match3)
        self.assertEqual(match3.target_surface, "web")


class TestSurfaceDeploymentSpec(unittest.TestCase):
    def test_surface_deployment_spec_dict_roundtrip(self) -> None:
        spec = SurfaceDeploymentSpec(
            surface_slug="author-studio",
            surface_kind="provider_portal",
            app_name="Author Studio",
            runtime_target="nextjs-web",
            container_port=3000,
            host_port=3001,
            env_vars={"PORT": "3001", "NODE_ENV": "production"},
            health_path="/api/health",
            depends_on=("backend-api",),
        )
        d = spec.to_dict()
        self.assertEqual(d["surface_slug"], "author-studio")
        self.assertEqual(d["runtime_target"], "nextjs-web")
        self.assertEqual(d["container_port"], 3000)
        self.assertEqual(d["host_port"], 3001)
        self.assertEqual(d["depends_on"], ["backend-api"])

        restored = SurfaceDeploymentSpec.from_dict(d)
        self.assertEqual(restored.surface_slug, spec.surface_slug)
        self.assertEqual(restored.depends_on, spec.depends_on)
        self.assertEqual(restored.env_vars, spec.env_vars)


class TestEcosystemDeploymentManifest(unittest.TestCase):
    def setUp(self) -> None:
        self.surf1 = SurfaceDeploymentSpec(
            surface_slug="web-app",
            surface_kind="public_web",
            app_name="Web App",
            runtime_target="nextjs-web",
            container_port=3000,
            host_port=3000,
            env_vars={"PORT": "3000"},
            health_path="/api/health",
            depends_on=(),
        )
        self.surf2 = SurfaceDeploymentSpec(
            surface_slug="api-svc",
            surface_kind="backend_api",
            app_name="API Service",
            runtime_target="backend-python",
            container_port=8000,
            host_port=8000,
            env_vars={"PORT": "8000", "DATABASE_URL": "postgresql://omnistackai:secret@postgres:5432/app_db"},
            health_path="/healthz",
            depends_on=("postgres",),
        )
        self.route1 = GatewayRoute("r-root", "/", "web-app", 3000)
        self.route2 = GatewayRoute("r-api", "/api", "api-svc", 8000)

        self.manifest = EcosystemDeploymentManifest(
            ecosystem_id="test-eco",
            version="1.0.0",
            gateway_port=8080,
            surfaces=(self.surf1, self.surf2),
            gateway_routes=(self.route1, self.route2),
            database_spec={
                "engine": "postgresql",
                "version": "16-alpine",
                "database_name": "app_db",
                "default_port": 5432,
            },
        )

    def test_manifest_dict_and_json_roundtrip(self) -> None:
        d = self.manifest.to_dict()
        self.assertEqual(d["ecosystem_id"], "test-eco")
        self.assertEqual(len(d["surfaces"]), 2)
        self.assertEqual(len(d["gateway_routes"]), 2)
        self.assertEqual(d["database_spec"]["engine"], "postgresql")

        restored = EcosystemDeploymentManifest.from_dict(d)
        self.assertEqual(restored.ecosystem_id, self.manifest.ecosystem_id)
        self.assertEqual(len(restored.surfaces), 2)
        self.assertEqual(len(restored.gateway_routes), 2)

        j = self.manifest.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["ecosystem_id"], "test-eco")

    def test_generate_docker_compose_valid_yaml_structure(self) -> None:
        yaml_content = generate_docker_compose(self.manifest)
        self.assertIn("name: test-eco", yaml_content)
        self.assertIn("services:", yaml_content)
        self.assertIn("postgres:", yaml_content)
        self.assertIn("web-app:", yaml_content)
        self.assertIn("api-svc:", yaml_content)
        self.assertIn("depends_on:", yaml_content)
        self.assertIn("ports:", yaml_content)
        self.assertIn("3000:3000", yaml_content)
        self.assertIn("8000:8000", yaml_content)
        self.assertIn("networks:", yaml_content)
        self.assertIn("volumes:", yaml_content)


class TestSynthesizeEcosystemDeployment(unittest.TestCase):
    def test_synthesize_for_minimal_blog(self) -> None:
        eco = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get("minimal-blog-ecosystem")
        self.assertIsNotNone(eco)
        assert eco is not None and eco.package is not None

        deployment = synthesize_ecosystem_deployment(
            ecosystem_id=eco.package.ecosystem_id,
            surfaces=eco.package.surfaces,
            base_port=3000,
        )

        self.assertEqual(deployment.ecosystem_id, "minimal-blog-ecosystem")
        self.assertEqual(len(deployment.surfaces), 3)
        self.assertGreaterEqual(len(deployment.gateway_routes), 3)

        slugs = [s.surface_slug for s in deployment.surfaces]
        self.assertIn("minimal-blog", slugs)
        self.assertIn("author-studio", slugs)
        self.assertIn("cms-admin", slugs)

        # Host ports must be non-colliding
        ports = [s.host_port for s in deployment.surfaces]
        self.assertEqual(len(ports), len(set(ports)))

        # Gateway routes must include root and sub-paths
        prefixes = [r.path_prefix for r in deployment.gateway_routes]
        self.assertIn("/", prefixes)
        self.assertTrue(any("/author-studio" in p for p in prefixes))
        self.assertTrue(any("/cms-admin" in p for p in prefixes))

    def test_synthesize_for_rideshare_favourites(self) -> None:
        eco = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get("rideshare-favourites-ecosystem")
        self.assertIsNotNone(eco)
        assert eco is not None and eco.package is not None

        deployment = synthesize_ecosystem_deployment(
            ecosystem_id=eco.package.ecosystem_id,
            surfaces=eco.package.surfaces,
            base_port=4000,
        )

        self.assertEqual(deployment.ecosystem_id, "rideshare-favourites-ecosystem")
        self.assertEqual(len(deployment.surfaces), 3)
        ports = [s.host_port for s in deployment.surfaces]
        self.assertEqual(len(ports), len(set(ports)))

    def test_compose_generation_for_synthesized_deployment(self) -> None:
        eco = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get("minimal-blog-ecosystem")
        self.assertIsNotNone(eco)
        assert eco is not None and eco.package is not None

        deployment = synthesize_ecosystem_deployment(
            ecosystem_id=eco.package.ecosystem_id,
            surfaces=eco.package.surfaces,
        )
        compose_yaml = deployment.to_compose_yaml()
        self.assertIn("name: minimal-blog-ecosystem", compose_yaml)
        self.assertIn("services:", compose_yaml)
        self.assertIn("postgres:", compose_yaml)


class TestEcosystemPackPackageWithDeployment(unittest.TestCase):
    def test_package_bundles_deployment_and_checksum_valid(self) -> None:
        eco = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get("minimal-blog-ecosystem")
        self.assertIsNotNone(eco)
        assert eco is not None and eco.package is not None

        # Newly synthesized pack package should bundle deployment_manifest
        pkg = synthesize_ecosystem_pack(eco.package.base_pack_id)
        self.assertIsNotNone(pkg.deployment_manifest)

        # Checksum must pass verification
        verify_ecosystem_pack(pkg)

        # Parse roundtrip
        raw = pkg.to_json()
        restored = parse_ecosystem_pack_package(raw)
        self.assertIsNotNone(restored.deployment_manifest)
        self.assertEqual(
            restored.deployment_manifest.ecosystem_id,
            pkg.deployment_manifest.ecosystem_id,
        )


class TestEcosystemLiveGateway(unittest.TestCase):
    def test_gateway_lifecycle_and_address(self) -> None:
        route = GatewayRoute("r-root", "/", "web", 3999)
        manifest = EcosystemDeploymentManifest(
            ecosystem_id="test-gw",
            version="1.0.0",
            gateway_port=0,  # 0 allocates ephemeral free port
            surfaces=(),
            gateway_routes=(route,),
        )
        gateway = EcosystemLiveGateway(manifest)
        self.assertFalse(gateway.is_running)

        gateway.start()
        try:
            self.assertTrue(gateway.is_running)
            self.assertGreater(gateway.port, 0)
            self.assertTrue(gateway.url.startswith("http://127.0.0.1:"))
        finally:
            gateway.stop()
            self.assertFalse(gateway.is_running)


class TestStudioPreviewManagerDeployment(unittest.TestCase):
    def test_preview_manager_tracks_deployment(self) -> None:
        mgr = StudioPreviewManager()
        status = mgr.status()
        self.assertFalse(status.get("has_deployment", False))

        eco = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get("minimal-blog-ecosystem")
        self.assertIsNotNone(eco)
        assert eco is not None and eco.package is not None

        mgr.replace_ecosystem(
            ecosystem_id=eco.package.ecosystem_id,
            surfaces=eco.package.surfaces,
            deployment_manifest=eco.package.deployment_manifest,
        )

        status = mgr.status()
        self.assertTrue(status.get("has_deployment", False))
        self.assertEqual(status.get("deployment_surface_count"), 3)
        self.assertIn("gateway_routes", status)

        dep = mgr.get_ecosystem_deployment()
        self.assertIsNotNone(dep)
        self.assertEqual(dep["ecosystem_id"], "minimal-blog-ecosystem")

        compose_text = mgr.to_compose_yaml()
        self.assertIsNotNone(compose_text)
        self.assertIn("services:", compose_text)

        mgr.stop()


class TestStudioServerDeploymentEndpoints(unittest.TestCase):
    def test_server_deployment_and_compose_routes(self) -> None:
        import threading
        import urllib.request
        from omnistackai_agent_engine.studio.server import create_studio_server

        mgr = StudioPreviewManager()
        eco = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get("minimal-blog-ecosystem")
        self.assertIsNotNone(eco)
        assert eco is not None and eco.package is not None
        mgr.replace_ecosystem(
            ecosystem_id=eco.package.ecosystem_id,
            surfaces=eco.package.surfaces,
            deployment_manifest=eco.package.deployment_manifest,
        )

        server = create_studio_server(
            build_fn=lambda prompt, **opts: {},
            host="127.0.0.1",
            port=0,
            status_fn=mgr.status,
            get_ecosystem_deployment_fn=mgr.get_ecosystem_deployment,
            to_compose_yaml_fn=mgr.to_compose_yaml,
        )
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        port = server.server_address[1]
        try:
            # GET /api/ecosystem/deployment
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ecosystem/deployment") as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data["ecosystem_id"], "minimal-blog-ecosystem")
                self.assertIn("gateway_routes", data)

            # GET /api/ecosystem/deployment/compose
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ecosystem/deployment/compose") as resp:
                self.assertEqual(resp.status, 200)
                content_type = resp.headers.get("Content-Type", "")
                self.assertIn("text/yaml", content_type)
                text = resp.read().decode("utf-8")
                self.assertIn("name: minimal-blog-ecosystem", text)
                self.assertIn("services:", text)
        finally:
            server.shutdown()
            server.server_close()
            mgr.stop()



class TestEcosystemCliDeploy(unittest.TestCase):
    def test_cli_deploy_subcommand_json_and_compose(self) -> None:
        from omnistackai_agent_engine.solution_packs.ecosystem_cli import main
        import io
        from contextlib import redirect_stdout

        # Test --json
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["deploy", "minimal-blog-ecosystem", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["ecosystem_id"], "minimal-blog-ecosystem")

        # Test --compose
        buf2 = io.StringIO()
        with redirect_stdout(buf2):
            ret2 = main(["deploy", "minimal-blog-ecosystem", "--compose"])
        self.assertEqual(ret2, 0)
        self.assertIn("name: minimal-blog-ecosystem", buf2.getvalue())
        self.assertIn("services:", buf2.getvalue())

        # Test human-readable output
        buf3 = io.StringIO()
        with redirect_stdout(buf3):
            ret3 = main(["deploy", "minimal-blog-ecosystem"])
        self.assertEqual(ret3, 0)
        self.assertIn("Ecosystem Deployment:", buf3.getvalue())
        self.assertIn("Gateway Routes", buf3.getvalue())


if __name__ == "__main__":
    unittest.main()

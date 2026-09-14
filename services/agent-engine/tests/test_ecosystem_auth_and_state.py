"""Unit and integration tests for Ecosystem Cross-App Auth and Unified State Binding (R-447)."""

from __future__ import annotations

import json
import time
import unittest
from unittest.mock import MagicMock

from omnistackai_agent_engine.application_ir import (
    ApplicationIR,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    Platform,
    ProjectStrategy,
    Role,
    Screen,
)
from omnistackai_agent_engine.solution_packs.ecosystem_auth import (
    CrossAppAuthMatrix,
    EcosystemAuthContract,
    EcosystemRoleBinding,
    generate_surface_tokens,
    mint_ecosystem_token,
    synthesize_ecosystem_auth,
    verify_ecosystem_token,
)
from omnistackai_agent_engine.solution_packs.ecosystem_state import (
    CrossAppEndpointBinding,
    EcosystemStateBinding,
    EntityStateFlow,
    SharedEntityBinding,
    StateTransition,
    SurfaceEnvBinding,
    synthesize_ecosystem_state,
)
from omnistackai_agent_engine.solution_packs.ecosystem_pack import (
    EcosystemPackPackage,
    EcosystemSurfacePackage,
    compute_ecosystem_checksum,
    parse_ecosystem_pack_package,
    synthesize_ecosystem_pack,
)
from omnistackai_agent_engine.solution_packs.ecosystem_registry import (
    DEFAULT_ECOSYSTEM_PACK_REGISTRY,
)


class TestEcosystemCrossAppAuth(unittest.TestCase):
    def setUp(self) -> None:
        self.roles = (
            EcosystemRoleBinding(
                surface_slug="customer-web",
                role_id="customer",
                display_name="Customer",
                allowed_surfaces=("customer-web",),
                authorized_actions=("read", "write"),
                scope_permissions=("post:read", "comment:write"),
            ),
            EcosystemRoleBinding(
                surface_slug="admin-portal",
                role_id="admin",
                display_name="Admin",
                allowed_surfaces=("customer-web", "admin-portal"),
                authorized_actions=("read", "write", "admin"),
                scope_permissions=("post:read", "post:write", "comment:read", "comment:write"),
            ),
        )
        self.contract = EcosystemAuthContract(
            ecosystem_id="test-blog-eco",
            jwt_algorithm="HS256",
            jwt_secret="super-secret-test-key-12345",
            issuer="omnistackai:test-blog-eco",
            audience="omnistackai:test-blog-eco:api",
            token_ttl_seconds=3600,
            roles=self.roles,
        )

    def test_mint_and_verify_token_success(self) -> None:
        token = mint_ecosystem_token(
            contract=self.contract,
            role_id="customer",
            subject="user-123",
            extra_claims={"email": "customer@example.com"},
        )
        self.assertIsInstance(token, str)
        self.assertEqual(token.count("."), 2)

        claims = verify_ecosystem_token(self.contract, token)
        self.assertEqual(claims["sub"], "user-123")
        self.assertEqual(claims["iss"], "omnistackai:test-blog-eco")
        self.assertEqual(claims["aud"], "omnistackai:test-blog-eco:api")
        self.assertEqual(claims["roles"], ["customer"])
        self.assertEqual(claims["surface_slug"], "customer-web")
        self.assertEqual(claims["email"], "customer@example.com")
        self.assertTrue(claims["exp"] > claims["iat"])

    def test_verify_token_expired(self) -> None:
        token = mint_ecosystem_token(
            contract=self.contract,
            role_id="customer",
            expires_in=-10,  # Already expired
        )
        with self.assertRaises(ValueError) as ctx:
            verify_ecosystem_token(self.contract, token)
        self.assertIn("expired", str(ctx.exception).lower())

    def test_verify_token_tampered_signature(self) -> None:
        token = mint_ecosystem_token(self.contract, role_id="customer")
        header_b64, payload_b64, sig_b64 = token.split(".")
        # Tamper payload
        tampered_token = f"{header_b64}.{payload_b64}extra.{sig_b64}"
        with self.assertRaises(ValueError) as ctx:
            verify_ecosystem_token(self.contract, tampered_token)
        self.assertIn("signature", str(ctx.exception).lower())

    def test_verify_token_wrong_secret(self) -> None:
        token = mint_ecosystem_token(self.contract, role_id="customer")
        wrong_contract = EcosystemAuthContract(
            ecosystem_id="test-blog-eco",
            jwt_secret="different-wrong-secret",
            roles=self.roles,
        )
        with self.assertRaises(ValueError) as ctx:
            verify_ecosystem_token(wrong_contract, token)
        self.assertIn("signature", str(ctx.exception).lower())

    def test_cross_app_auth_matrix_privilege_isolation(self) -> None:
        matrix = CrossAppAuthMatrix.from_contract(self.contract)

        # Customer can access customer-web, cannot access admin-portal
        self.assertTrue(matrix.can_access_surface("customer", "customer-web"))
        self.assertFalse(matrix.can_access_surface("customer", "admin-portal"))

        # Admin can access both surfaces
        self.assertTrue(matrix.can_access_surface("admin", "customer-web"))
        self.assertTrue(matrix.can_access_surface("admin", "admin-portal"))

        # Permissions check
        self.assertTrue(matrix.has_permission("customer", "comment:write"))
        self.assertFalse(matrix.has_permission("customer", "post:write"))
        self.assertTrue(matrix.has_permission("admin", "post:write"))

    def test_generate_surface_tokens(self) -> None:
        tokens = generate_surface_tokens(self.contract)
        self.assertIn("customer-web", tokens)
        self.assertIn("admin-portal", tokens)

        # Verify each generated surface token
        customer_claims = verify_ecosystem_token(self.contract, tokens["customer-web"])
        self.assertEqual(customer_claims["surface_slug"], "customer-web")
        self.assertEqual(customer_claims["roles"], ["customer"])

        admin_claims = verify_ecosystem_token(self.contract, tokens["admin-portal"])
        self.assertEqual(admin_claims["surface_slug"], "admin-portal")
        self.assertEqual(admin_claims["roles"], ["admin"])

    def test_contract_roundtrip_dict(self) -> None:
        data = self.contract.to_dict()
        reconstructed = EcosystemAuthContract.from_dict(data)
        self.assertEqual(self.contract, reconstructed)


class TestEcosystemUnifiedStateBinding(unittest.TestCase):
    def setUp(self) -> None:
        self.shared_entities = (
            SharedEntityBinding(
                entity_name="post",
                authoritative_surface="admin-portal",
                reading_surfaces=("customer-web", "admin-portal"),
                writing_surfaces=("admin-portal",),
            ),
            SharedEntityBinding(
                entity_name="comment",
                authoritative_surface="customer-web",
                reading_surfaces=("customer-web", "admin-portal"),
                writing_surfaces=("customer-web", "admin-portal"),
            ),
        )
        self.state_flows = (
            EntityStateFlow(
                entity_name="post",
                state_field="published",
                initial_state="draft",
                terminal_states=("published", "archived"),
                transitions=(
                    StateTransition(
                        from_state="draft",
                        to_state="published",
                        authorized_roles=("admin",),
                        trigger_surface="admin-portal",
                        action_name="publish",
                    ),
                    StateTransition(
                        from_state="published",
                        to_state="archived",
                        authorized_roles=("admin",),
                        trigger_surface="admin-portal",
                        action_name="archive",
                    ),
                ),
            ),
        )
        self.cross_app_endpoints = (
            CrossAppEndpointBinding(
                endpoint_path="/posts",
                http_method="GET",
                target_entity="post",
                consuming_surfaces=("customer-web", "admin-portal"),
                required_roles=(),
                is_mutation=False,
            ),
            CrossAppEndpointBinding(
                endpoint_path="/posts",
                http_method="POST",
                target_entity="post",
                consuming_surfaces=("admin-portal",),
                required_roles=("admin",),
                is_mutation=True,
            ),
        )
        self.env_bindings = (
            SurfaceEnvBinding(
                surface_slug="customer-web",
                env_vars=(
                    ("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000"),
                    ("JWT_SECRET", "local-dev-secret"),
                ),
            ),
            SurfaceEnvBinding(
                surface_slug="admin-portal",
                env_vars=(
                    ("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000"),
                    ("JWT_SECRET", "local-dev-secret"),
                ),
            ),
        )
        self.state_binding = EcosystemStateBinding(
            ecosystem_id="test-blog-eco",
            database_strategy="postgres",
            shared_entities=self.shared_entities,
            state_flows=self.state_flows,
            cross_app_endpoints=self.cross_app_endpoints,
            environment_bindings=self.env_bindings,
        )

    def test_state_transition_validation(self) -> None:
        flow = self.state_flows[0]
        # Valid transition by admin
        self.assertTrue(flow.can_transition(from_state="draft", to_state="published", role_id="admin"))
        # Invalid transition: customer cannot publish
        self.assertFalse(flow.can_transition(from_state="draft", to_state="published", role_id="customer"))
        # Nonexistent transition: draft -> archived directly not allowed
        self.assertFalse(flow.can_transition(from_state="draft", to_state="archived", role_id="admin"))

    def test_state_binding_roundtrip_dict(self) -> None:
        data = self.state_binding.to_dict()
        reconstructed = EcosystemStateBinding.from_dict(data)
        self.assertEqual(self.state_binding, reconstructed)


class TestSynthesisAndPackageIntegration(unittest.TestCase):
    def test_synthesize_auth_and_state_for_built_in_ecosystems(self) -> None:
        eco = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get("minimal-blog-ecosystem")
        self.assertIsNotNone(eco)
        pkg = eco.package

        auth_contract = synthesize_ecosystem_auth("minimal-blog-ecosystem", pkg.surfaces)
        self.assertIsInstance(auth_contract, EcosystemAuthContract)
        self.assertEqual(auth_contract.ecosystem_id, "minimal-blog-ecosystem")
        self.assertTrue(len(auth_contract.roles) >= 1)

        tokens = generate_surface_tokens(auth_contract)
        for surface in pkg.surfaces:
            if surface.slug in tokens:
                claims = verify_ecosystem_token(auth_contract, tokens[surface.slug])
                self.assertEqual(claims["surface_slug"], surface.slug)

        state_binding = synthesize_ecosystem_state("minimal-blog-ecosystem", pkg.surfaces)
        self.assertIsInstance(state_binding, EcosystemStateBinding)
        self.assertEqual(state_binding.ecosystem_id, "minimal-blog-ecosystem")
        self.assertTrue(len(state_binding.shared_entities) >= 1)

    def test_ecosystem_pack_package_preserves_auth_and_state(self) -> None:
        pkg = synthesize_ecosystem_pack("minimal-blog")
        auth = synthesize_ecosystem_auth(pkg.ecosystem_id, pkg.surfaces)
        state = synthesize_ecosystem_state(pkg.ecosystem_id, pkg.surfaces)

        # Update package with auth and state
        pkg_with_bindings = EcosystemPackPackage(
            schema_version=pkg.schema_version,
            ecosystem_id=pkg.ecosystem_id,
            version=pkg.version,
            display_name=pkg.display_name,
            description=pkg.description,
            domain=pkg.domain,
            base_pack_id=pkg.base_pack_id,
            surfaces=pkg.surfaces,
            auth_contract=auth,
            state_binding=state,
            package_sha256="",
        )
        checksum = compute_ecosystem_checksum(pkg_with_bindings.to_dict())
        final_pkg = EcosystemPackPackage(
            schema_version=pkg_with_bindings.schema_version,
            ecosystem_id=pkg_with_bindings.ecosystem_id,
            version=pkg_with_bindings.version,
            display_name=pkg_with_bindings.display_name,
            description=pkg_with_bindings.description,
            domain=pkg_with_bindings.domain,
            base_pack_id=pkg_with_bindings.base_pack_id,
            surfaces=pkg_with_bindings.surfaces,
            auth_contract=pkg_with_bindings.auth_contract,
            state_binding=pkg_with_bindings.state_binding,
            package_sha256=checksum,
        )

        # Serialize and parse back
        raw_dict = final_pkg.to_dict()
        self.assertIn("auth_contract", raw_dict)
        self.assertIn("state_binding", raw_dict)

        parsed = parse_ecosystem_pack_package(raw_dict)
        self.assertEqual(parsed.package_sha256, checksum)
        self.assertIsNotNone(parsed.auth_contract)
        self.assertIsNotNone(parsed.state_binding)
        self.assertEqual(parsed.auth_contract, auth)
        self.assertEqual(parsed.state_binding, state)


class FakeSurfaceSession:
    def __init__(self, repo_dir: str, *, web_port: int = 3000, api_port: int = 8000) -> None:
        from omnistackai_agent_engine.localrun import RunPlan

        self.repo_dir = repo_dir
        self.plan = RunPlan(
            repo_dir=repo_dir,
            app_slug=repo_dir.split("/")[-1],
            db_name="test_db",
            backend_kind="python",
            has_web=True,
            api_url=f"http://127.0.0.1:{api_port}",
            web_url=f"http://127.0.0.1:{web_port}",
            db_password="secret-password",
        )
        self.api_ready = True
        self.web_ready = True
        self.alive = True
        self.stop_calls = 0

    def is_alive(self) -> bool:
        return self.alive

    def stop(self) -> None:
        self.stop_calls += 1
        self.alive = False


class TestStudioAuthAndState(unittest.TestCase):
    def setUp(self) -> None:
        from omnistackai_agent_engine.studio.preview import StudioPreviewManager
        from omnistackai_agent_engine.studio.server import create_studio_server

        self.sessions: dict[str, FakeSurfaceSession] = {}
        port_counter = [34000]

        def start_fn(repo_dir: str, log=None):
            w_port = port_counter[0]
            a_port = port_counter[0] + 1000
            port_counter[0] += 1
            sess = FakeSurfaceSession(repo_dir, web_port=w_port, api_port=a_port)
            self.sessions[repo_dir] = sess
            return sess

        self.manager = StudioPreviewManager(start_fn=start_fn)
        self.surfaces = [
            {
                "slug": "customer-web",
                "app_name": "Customer Web",
                "surface_kind": "customer_web",
                "target_dir": "/tmp/eco/customer-web",
            },
            {
                "slug": "author-portal",
                "app_name": "Author Portal",
                "surface_kind": "provider_portal",
                "target_dir": "/tmp/eco/author-portal",
            },
        ]

        def build_fn(prompt: str, **kwargs):
            return {"status": "ok"}

        self.server = create_studio_server(
            build_fn,
            host="127.0.0.1",
            port=0,
            status_fn=self.manager.status,
            stop_fn=self.manager.stop,
            restart_fn=self.manager.restart,
            get_ecosystem_auth_fn=self.manager.get_ecosystem_auth,
            get_ecosystem_state_fn=self.manager.get_ecosystem_state,
        )
        self.port = self.server.server_address[1]
        import threading

        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.manager.stop()
        self.server.shutdown()
        self.server.server_close()

    def _get(self, path: str) -> tuple[int, dict]:
        from urllib.request import Request, urlopen

        req = Request(f"http://127.0.0.1:{self.port}{path}", method="GET")
        with urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body

    def test_preview_manager_ecosystem_auth_and_state_lifecycle(self) -> None:
        # Before ecosystem launched
        auth_before = self.manager.get_ecosystem_auth()
        self.assertFalse(auth_before["is_ecosystem"])
        self.assertIsNone(auth_before["auth_contract"])

        state_before = self.manager.get_ecosystem_state()
        self.assertFalse(state_before["is_ecosystem"])
        self.assertIsNone(state_before["state_binding"])

        # Replace ecosystem
        payload = self.manager.replace_ecosystem("test-eco", self.surfaces)
        self.assertTrue(payload["is_ecosystem"])
        self.assertTrue(payload["has_auth"])
        self.assertTrue(payload["has_state"])
        self.assertIsNotNone(payload["active_role"])
        self.assertIsNotNone(payload["active_token"])

        # Inspect auth
        auth_info = self.manager.get_ecosystem_auth()
        self.assertTrue(auth_info["is_ecosystem"])
        self.assertEqual(auth_info["ecosystem_id"], "test-eco")
        self.assertEqual(auth_info["auth_contract"]["jwt_secret"], "***")
        self.assertIn("customer-web", auth_info["tokens"])
        self.assertIn("author-portal", auth_info["tokens"])

        # Inspect state
        state_info = self.manager.get_ecosystem_state()
        self.assertTrue(state_info["is_ecosystem"])
        self.assertEqual(state_info["ecosystem_id"], "test-eco")
        self.assertIsNotNone(state_info["state_binding"])

        # Switch surface updates role and token
        switched = self.manager.switch_surface("author-portal")
        self.assertEqual(switched["active_surface"], "author-portal")
        self.assertEqual(switched["active_role"], "author_portal")
        self.assertEqual(switched["active_token"], auth_info["tokens"]["author-portal"])

    def test_studio_server_auth_and_state_endpoints(self) -> None:
        # Before replace: endpoints return is_ecosystem=False
        status, body = self._get("/api/ecosystem/auth")
        self.assertEqual(status, 200)
        self.assertFalse(body["is_ecosystem"])

        status, body = self._get("/api/ecosystem/state")
        self.assertEqual(status, 200)
        self.assertFalse(body["is_ecosystem"])

        # Launch ecosystem
        self.manager.replace_ecosystem("test-eco", self.surfaces)

        # Query GET /api/ecosystem/auth
        status, body = self._get("/api/ecosystem/auth")
        self.assertEqual(status, 200)
        self.assertTrue(body["is_ecosystem"])
        self.assertEqual(body["ecosystem_id"], "test-eco")
        self.assertIn("customer-web", body["tokens"])

        # Query GET /api/ecosystem/state
        status, body = self._get("/api/ecosystem/state")
        self.assertEqual(status, 200)
        self.assertTrue(body["is_ecosystem"])
        self.assertEqual(body["ecosystem_id"], "test-eco")
        self.assertIn("state_binding", body)


class TestEcosystemCLIAuthAndState(unittest.TestCase):
    def test_cli_auth_text_and_json(self) -> None:
        import io
        from unittest.mock import patch
        from omnistackai_agent_engine.solution_packs.ecosystem_cli import main

        # Text output
        out = io.StringIO()
        with patch("sys.stdout", out):
            code = main(["auth", "minimal-blog-ecosystem"])
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("Ecosystem Cross-App Auth", text)
        self.assertIn("Algorithm: HS256", text)

        # JSON output
        out_json = io.StringIO()
        with patch("sys.stdout", out_json):
            code = main(["auth", "minimal-blog-ecosystem", "--json"])
        self.assertEqual(code, 0)
        parsed = json.loads(out_json.getvalue())
        self.assertIn("auth_contract", parsed)
        self.assertIn("matrix", parsed)
        self.assertEqual(parsed["auth_contract"]["ecosystem_id"], "minimal-blog-ecosystem")

    def test_cli_state_text_and_json(self) -> None:
        import io
        from unittest.mock import patch
        from omnistackai_agent_engine.solution_packs.ecosystem_cli import main

        # Text output
        out = io.StringIO()
        with patch("sys.stdout", out):
            code = main(["state", "minimal-blog-ecosystem"])
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("Ecosystem Unified State", text)
        self.assertIn("Database: postgres", text)

        # JSON output
        out_json = io.StringIO()
        with patch("sys.stdout", out_json):
            code = main(["state", "minimal-blog-ecosystem", "--json"])
        self.assertEqual(code, 0)
        parsed = json.loads(out_json.getvalue())
        self.assertIn("database_strategy", parsed)
        self.assertIn("shared_entities", parsed)
        self.assertEqual(parsed["ecosystem_id"], "minimal-blog-ecosystem")

    def test_cli_unknown_target_returns_error(self) -> None:
        import io
        from unittest.mock import patch
        from omnistackai_agent_engine.solution_packs.ecosystem_cli import main

        err = io.StringIO()
        with patch("sys.stderr", err):
            code = main(["auth", "nonexistent-ecosystem-slug-xyz"])
        self.assertEqual(code, 1)
        self.assertIn("Error", err.getvalue())


if __name__ == "__main__":
    unittest.main()


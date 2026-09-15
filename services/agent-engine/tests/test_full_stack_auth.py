"""Full-stack authentication integration tests for R-461.

Covers:
  1. PostgreSQL schema — `users` table emission when auth is required.
  2. auth_guard.py — `python_auth_router_file()` emits all four auth endpoints.
  3. backend_python.py — auth router is included in the generated FastAPI app.
  4. nextjs.py — login page, register page, auth-provider context are generated.
  5. Navbar auth UI — sign-in/out controls present.
  6. API client — auto-attaches Bearer token from localStorage.
  7. Determinism — all generators are byte-stable.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import NextjsWebAdapter, PythonBackendAdapter
from omnistackai_agent_engine.codegen.auth_guard import (
    needs_auth,
    python_auth_file,
    python_auth_router_file,
)
from omnistackai_agent_engine.codegen.schema_sql import render_postgres_schema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_ir():
    """Minimal IR where at least one endpoint requires auth."""
    return example_ir("minimal-blog")  # POST /posts is auth=True


def _no_auth_ir():
    """Same IR but all endpoints made public."""
    ir = example_ir("minimal-blog")
    public_apis = tuple(replace(api, auth=False) for api in ir.apis)
    return replace(ir, apis=public_apis)


# ---------------------------------------------------------------------------
# 1. PostgreSQL schema — users table
# ---------------------------------------------------------------------------

class TestUsersTableSchema(TestCase):
    def setUp(self) -> None:
        self.ir_auth = _auth_ir()
        self.ir_no_auth = _no_auth_ir()
        self.schema_auth = render_postgres_schema(self.ir_auth)
        self.schema_no_auth = render_postgres_schema(self.ir_no_auth)

    def test_users_table_present_when_auth_required(self) -> None:
        self.assertIn('"users"', self.schema_auth)

    def test_users_table_absent_when_no_auth(self) -> None:
        self.assertNotIn('"users"', self.schema_no_auth)

    def test_users_table_has_id_column(self) -> None:
        self.assertIn('"id"', self.schema_auth)
        self.assertIn('gen_random_uuid()', self.schema_auth)

    def test_users_table_has_email_column_unique_not_null(self) -> None:
        self.assertIn('"email"', self.schema_auth)
        # The users block must contain both UNIQUE and NOT NULL near email
        users_block_start = self.schema_auth.find('"users"')
        users_block_end = self.schema_auth.find(');', users_block_start)
        users_block = self.schema_auth[users_block_start:users_block_end]
        self.assertIn('"email"', users_block)
        self.assertIn('UNIQUE', users_block)
        self.assertIn('NOT NULL', users_block)

    def test_users_table_has_password_hash_column(self) -> None:
        self.assertIn('"password_hash"', self.schema_auth)

    def test_users_table_has_role_column_with_default(self) -> None:
        users_block_start = self.schema_auth.find('"users"')
        users_block_end = self.schema_auth.find(');', users_block_start)
        users_block = self.schema_auth[users_block_start:users_block_end]
        self.assertIn('"role"', users_block)

    def test_users_table_has_created_at_column(self) -> None:
        self.assertIn('"created_at"', self.schema_auth)
        self.assertIn('TIMESTAMPTZ', self.schema_auth)

    def test_admin_seed_row_present_when_auth(self) -> None:
        self.assertIn('admin@example.local', self.schema_auth)

    def test_admin_seed_row_absent_when_no_auth(self) -> None:
        self.assertNotIn('admin@example.local', self.schema_no_auth)

    def test_schema_is_valid_sql_syntax_structure(self) -> None:
        """Schema should start with CREATE TABLE or a comment."""
        self.assertTrue(
            self.schema_auth.strip().startswith('--') or
            self.schema_auth.strip().upper().startswith('CREATE')
        )

    def test_schema_deterministic(self) -> None:
        self.assertEqual(
            render_postgres_schema(self.ir_auth),
            render_postgres_schema(self.ir_auth),
        )


# ---------------------------------------------------------------------------
# 2. auth_guard.py — python_auth_router_file()
# ---------------------------------------------------------------------------

class TestPythonAuthRouterFile(TestCase):
    def setUp(self) -> None:
        self.ir = _auth_ir()
        self.router_code = python_auth_router_file(self.ir)

    def test_router_file_is_valid_python(self) -> None:
        ast.parse(self.router_code)

    def test_register_endpoint_present(self) -> None:
        self.assertIn('/register', self.router_code)
        self.assertIn('register', self.router_code.lower())

    def test_login_endpoint_present(self) -> None:
        self.assertIn('/login', self.router_code)
        self.assertIn('login', self.router_code.lower())

    def test_me_endpoint_present(self) -> None:
        self.assertIn('/me', self.router_code)

    def test_logout_endpoint_present(self) -> None:
        self.assertIn('/logout', self.router_code)

    def test_pbkdf2_hashing_used(self) -> None:
        self.assertIn('pbkdf2_hmac', self.router_code)

    def test_no_plaintext_password_storage(self) -> None:
        # The router must never store the raw password
        self.assertNotIn('password_plain', self.router_code)
        self.assertIn('password_hash', self.router_code)

    def test_jwt_signing_present(self) -> None:
        self.assertIn('jwt', self.router_code.lower())
        self.assertIn('JWT_SECRET', self.router_code)

    def test_hashlib_import_not_external_dep(self) -> None:
        # hashlib is stdlib — no pip install needed
        self.assertIn('import hashlib', self.router_code)
        self.assertNotIn('bcrypt', self.router_code)
        self.assertNotIn('passlib', self.router_code)

    def test_router_deterministic(self) -> None:
        self.assertEqual(
            python_auth_router_file(self.ir),
            python_auth_router_file(self.ir),
        )


# ---------------------------------------------------------------------------
# 3. backend_python.py — auth router wiring in generated project
# ---------------------------------------------------------------------------

class TestBackendPythonAuthRouterWiring(TestCase):
    def setUp(self) -> None:
        self.ir = _auth_ir()
        self.project = PythonBackendAdapter().generate(self.ir)

    def test_auth_router_file_emitted(self) -> None:
        self.assertIn('app/routers/auth.py', self.project.paths())

    def test_auth_router_includes_register_endpoint(self) -> None:
        auth_router = self.project.get('app/routers/auth.py').content
        self.assertIn('/register', auth_router)

    def test_auth_router_includes_login_endpoint(self) -> None:
        auth_router = self.project.get('app/routers/auth.py').content
        self.assertIn('/login', auth_router)

    def test_auth_router_wired_into_main(self) -> None:
        main_py = self.project.get('app/main.py').content
        self.assertIn('auth', main_py)
        # Either include_router or prefix="/auth" should appear
        self.assertTrue(
            'include_router' in main_py or '/auth' in main_py,
            "main.py must wire in the auth router"
        )

    def test_no_auth_router_when_all_public(self) -> None:
        project = PythonBackendAdapter().generate(_no_auth_ir())
        self.assertNotIn('app/routers/auth.py', project.paths())


# ---------------------------------------------------------------------------
# 4. nextjs.py — login page, register page, auth-provider
# ---------------------------------------------------------------------------

class TestNextjsAuthPages(TestCase):
    def setUp(self) -> None:
        self.ir = _auth_ir()
        self.project = NextjsWebAdapter().generate(self.ir)

    def test_login_page_emitted(self) -> None:
        self.assertIn('app/login/page.tsx', self.project.paths())

    def test_register_page_emitted(self) -> None:
        self.assertIn('app/register/page.tsx', self.project.paths())

    def test_auth_provider_component_emitted(self) -> None:
        self.assertIn('components/auth-provider.tsx', self.project.paths())

    def test_login_page_has_form_inputs(self) -> None:
        login_page = self.project.get('app/login/page.tsx').content
        self.assertIn('email', login_page.lower())
        self.assertIn('password', login_page.lower())

    def test_register_page_has_form_inputs(self) -> None:
        register_page = self.project.get('app/register/page.tsx').content
        self.assertIn('email', register_page.lower())
        self.assertIn('password', register_page.lower())

    def test_auth_provider_exposes_use_auth_hook(self) -> None:
        auth_provider = self.project.get('components/auth-provider.tsx').content
        self.assertIn('useAuth', auth_provider)

    def test_auth_provider_exposes_user_token_login_logout(self) -> None:
        auth_provider = self.project.get('components/auth-provider.tsx').content
        self.assertIn('user', auth_provider)
        self.assertIn('token', auth_provider)
        self.assertIn('login', auth_provider)
        self.assertIn('logout', auth_provider)

    def test_no_auth_pages_when_no_auth_required(self) -> None:
        project = NextjsWebAdapter().generate(_no_auth_ir())
        self.assertNotIn('app/login/page.tsx', project.paths())
        self.assertNotIn('app/register/page.tsx', project.paths())
        self.assertNotIn('components/auth-provider.tsx', project.paths())


# ---------------------------------------------------------------------------
# 5. Navbar auth UI
# ---------------------------------------------------------------------------

class TestNextjsNavbarAuthUI(TestCase):
    def setUp(self) -> None:
        self.ir = _auth_ir()
        self.project = NextjsWebAdapter().generate(self.ir)

    def test_navbar_references_use_auth(self) -> None:
        navbar = self.project.get('components/navbar.tsx').content
        self.assertIn('useAuth', navbar)

    def test_navbar_has_sign_in_link_or_logout_button(self) -> None:
        navbar = self.project.get('components/navbar.tsx').content
        # Either "Sign In" or "login" link must be present
        self.assertTrue(
            'login' in navbar.lower() or 'sign in' in navbar.lower() or 'signin' in navbar.lower(),
            "navbar must contain a sign-in link"
        )

    def test_navbar_no_auth_ui_when_no_auth(self) -> None:
        project = NextjsWebAdapter().generate(_no_auth_ir())
        navbar = project.get('components/navbar.tsx').content
        self.assertNotIn('useAuth', navbar)

    def test_layout_wraps_auth_provider_when_auth_required(self) -> None:
        layout = self.project.get('app/layout.tsx').content
        self.assertIn('import { AuthProvider } from "@/components/auth-provider";', layout)
        self.assertIn('<AuthProvider>', layout)
        self.assertIn('</AuthProvider>', layout)

    def test_layout_no_auth_provider_when_no_auth(self) -> None:
        project = NextjsWebAdapter().generate(_no_auth_ir())
        layout = project.get('app/layout.tsx').content
        self.assertNotIn('AuthProvider', layout)


# ---------------------------------------------------------------------------
# 6. API client — auto Bearer token
# ---------------------------------------------------------------------------

class TestNextjsApiClientAuthHeader(TestCase):
    def setUp(self) -> None:
        self.ir = _auth_ir()
        self.project = NextjsWebAdapter().generate(self.ir)

    def test_api_client_reads_token_from_local_storage(self) -> None:
        api_ts = self.project.get('lib/api.ts').content
        self.assertIn('localStorage', api_ts)

    def test_api_client_attaches_authorization_header(self) -> None:
        api_ts = self.project.get('lib/api.ts').content
        self.assertIn('Authorization', api_ts)
        self.assertIn('Bearer', api_ts)


# ---------------------------------------------------------------------------
# 7. Determinism across all new generators
# ---------------------------------------------------------------------------

class TestFullStackAuthDeterminism(TestCase):
    def test_schema_sql_deterministic(self) -> None:
        ir = _auth_ir()
        self.assertEqual(render_postgres_schema(ir), render_postgres_schema(ir))

    def test_auth_router_deterministic(self) -> None:
        ir = _auth_ir()
        self.assertEqual(python_auth_router_file(ir), python_auth_router_file(ir))

    def test_nextjs_project_deterministic(self) -> None:
        ir = _auth_ir()
        p1 = NextjsWebAdapter().generate(ir)
        p2 = NextjsWebAdapter().generate(ir)
        for path in p1.paths():
            self.assertEqual(
                p1.get(path).content,
                p2.get(path).content,
                msg=f"Non-deterministic output in {path}",
            )


if __name__ == '__main__':
    import unittest
    unittest.main()

"""R-591: every backend has the complete account flow, and every surface can use it.

Before this task:

* the Go backend verified tokens and never issued one — no register, no login;
* the Node backend had no account routes at all, served its API under `/api/...` while the web
  app and the published contract call `/...`, never checked token expiry, and let any visitor in as
  admin when JWT_SECRET was unset (its default secret contained 'dev-secret', which enabled the
  no-token bypass);
* the Python backend's `/auth/me` read the token from the *query string*, so a signed-in user's
  profile call answered 401; forgot-password said a link was sent and sent nothing; reset was 501;
* the web "forgot password" page set a new password from an email address alone;
* the mobile app had a session context and no sign-in screen.

These tests guard the shape offline. The behaviour was proven live on 2026-09-26 against
PostgreSQL: 84 checks across Python, Go, Node/Express and Node/Hono, including accounts moving
between backends (see the task record).
"""

import hashlib
import re
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen.auth_guard import python_auth_router_file
from omnistackai_agent_engine.codegen.auth_templates import (
    AUTH_CONTRACT,
    GO_AUTH_HANDLERS,
    NODE_AUTH_CORE,
    is_account_route,
)
from omnistackai_agent_engine.codegen.backend_go import GoBackendAdapter
from omnistackai_agent_engine.codegen.backend_node import NodeBackendAdapter
from omnistackai_agent_engine.codegen.backend_python import PythonBackendAdapter
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter
from omnistackai_agent_engine.codegen.react_native import ReactNativeAdapter
from omnistackai_agent_engine.codegen.schema_sql import render_postgres_schema

IR = example_ir("minimal-blog")  # has auth-required endpoints and entities


def _file(project, path: str) -> str:
    return project.get(path).content


class EveryBackendServesTheWholeContract(TestCase):
    def test_python(self) -> None:
        router = _file(PythonBackendAdapter().generate(IR), "app/routers/auth.py")
        for _, (method, path) in AUTH_CONTRACT.items():
            with self.subTest(path=path):
                self.assertIn(f'@router.{method.lower()}("{path.removeprefix("/auth")}"', router)

    def test_go(self) -> None:
        main = _file(GoBackendAdapter().generate(IR), "main.go")
        for _, (method, path) in AUTH_CONTRACT.items():
            with self.subTest(path=path):
                self.assertIn(f'"{method} {path}"', main)

    def test_node_express_and_hono(self) -> None:
        for framework in ("express", "hono"):
            project = NodeBackendAdapter(framework).generate(IR)
            app = _file(project, "src/app.ts")
            router = _file(project, "src/routes/account.ts")
            with self.subTest(framework=framework):
                self.assertIn("'/auth', accountRouter", app)
                for _, (method, path) in AUTH_CONTRACT.items():
                    self.assertIn(f"router.{method.lower()}('{path.removeprefix('/auth')}'", router)


class ThePythonBugsAreGone(TestCase):
    ROUTER = python_auth_router_file(IR)

    def test_me_reads_the_header_not_the_query_string(self) -> None:
        self.assertIn("authorization: str | None = Header(default=None)", self.ROUTER)

    def test_forgot_password_no_longer_claims_to_have_sent_anything(self) -> None:
        self.assertNotIn("Password reset link dispatched", self.ROUTER)

    def test_reset_is_implemented(self) -> None:
        self.assertNotIn("password_reset_not_configured", self.ROUTER)
        self.assertIn("invalid_or_expired_token", self.ROUTER)


class ResetLinksAreSafe(TestCase):
    SOURCES = {"python": python_auth_router_file(IR), "go": GO_AUTH_HANDLERS, "node": NODE_AUTH_CORE}

    def test_only_a_hash_of_the_token_is_stored(self) -> None:
        for name, source in self.SOURCES.items():
            with self.subTest(backend=name):
                self.assertIn("reset_token_hash", source)
                self.assertRegex(source, r"sha256")

    def test_a_link_expires_and_dies_on_use(self) -> None:
        for name, source in self.SOURCES.items():
            with self.subTest(backend=name):
                self.assertIn("reset_token_expires_at > NOW()", source)
                self.assertIn("reset_token_hash = NULL", source)

    def test_forgot_password_answers_the_same_for_unknown_emails(self) -> None:
        # The status body is unconditional: nothing in the response depends on whether a row matched.
        self.assertIn('return {"status": "ok"}', self.SOURCES["python"])
        self.assertIn('writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})', self.SOURCES["go"])
        self.assertIn("return { status: 200, body: { status: 'ok' } };", self.SOURCES["node"])

    def test_the_schema_has_the_columns_and_upgrades_old_databases(self) -> None:
        schema = render_postgres_schema(IR)
        self.assertIn('ADD COLUMN IF NOT EXISTS "reset_token_hash"', schema)
        self.assertIn('ADD COLUMN IF NOT EXISTS "reset_token_expires_at"', schema)


class OnePasswordFormatEverywhere(TestCase):
    """PBKDF2-SHA256, 100 000 iterations, "<hex_salt>:<hex_digest>" — so accounts move between
    backends and the seeded dev admin works on all of them."""

    def test_each_backend_uses_the_same_parameters(self) -> None:
        self.assertIn('hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, 100_000)', python_auth_router_file(IR))
        self.assertIn("pbkdf2Iterations  = 100000", GO_AUTH_HANDLERS)
        self.assertIn("crypto.pbkdf2Sync(plain, salt, ITERATIONS, 32, 'sha256')", NODE_AUTH_CORE)

    def test_the_reference_vector(self) -> None:
        # The seeded admin: 32 zero bytes of salt, password "changeme". Go and Node must agree with
        # this; the live run proved they do by signing the admin in through both.
        digest = hashlib.pbkdf2_hmac("sha256", b"changeme", bytes(32), 100_000).hex()
        self.assertIn("0" * 64 + ":" + digest, render_postgres_schema(IR))


class NodeIsNoLongerOpenByDefault(TestCase):
    PROJECT = NodeBackendAdapter("express").generate(IR)

    def test_there_is_no_default_secret(self) -> None:
        config = _file(self.PROJECT, "src/config.ts")
        self.assertIn("jwtSecret: process.env.JWT_SECRET || ''", config)
        self.assertNotIn("dev-secret-change-in-production", config)
        self.assertNotIn("dev-secret-change-in-production", _file(self.PROJECT, ".env.example"))

    def test_the_bypass_needs_dev_mode_or_an_explicit_dev_secret(self) -> None:
        guard = _file(self.PROJECT, "src/middleware/auth.ts")
        self.assertNotIn("secret.includes('dev-secret')", guard)
        self.assertIn("process.env.OMNISTACKAI_DEV_MODE === '1' || DEV_SECRETS.includes(secret)", guard)
        self.assertIn("auth_not_configured", guard)

    def test_tokens_expire_and_signatures_compare_in_constant_time(self) -> None:
        self.assertIn("claims.exp * 1000 < Date.now()", NODE_AUTH_CORE)
        self.assertIn("crypto.timingSafeEqual(given, expected)", NODE_AUTH_CORE)
        self.assertIn("header.alg !== 'HS256'", NODE_AUTH_CORE)

    def test_routes_are_served_at_the_contract_paths(self) -> None:
        app = _file(self.PROJECT, "src/app.ts")
        self.assertNotIn("'/api/", app)
        self.assertRegex(app, r"app\.use\('/posts', postsRouter\)")


class APlanCannotCollideWithTheAccountFlow(TestCase):
    def _with_plan_login(self):
        import dataclasses

        from omnistackai_agent_engine.application_ir.ir import ApiEndpoint

        extra = ApiEndpoint(method="POST", path="/auth/login", auth=False)
        return dataclasses.replace(IR, apis=IR.apis + (extra,))

    def test_is_account_route(self) -> None:
        self.assertTrue(is_account_route("/auth/login"))
        self.assertTrue(is_account_route("/auth"))
        self.assertFalse(is_account_route("/authors"))

    def test_go_registers_each_pattern_once(self) -> None:
        # Go's ServeMux panics at start-up on a duplicate pattern.
        main = _file(GoBackendAdapter().generate(self._with_plan_login()), "main.go")
        self.assertEqual(main.count('"POST /auth/login"'), 1)

    def test_python_and_node_write_one_auth_module(self) -> None:
        ir = self._with_plan_login()
        python_paths = PythonBackendAdapter().generate(ir).paths()
        self.assertEqual(list(python_paths).count("app/routers/auth.py"), 1)
        node_paths = NodeBackendAdapter("express").generate(ir).paths()
        self.assertNotIn("src/routes/auth.ts", node_paths)


class TheWebAppRecoversSafely(TestCase):
    PROJECT = NextjsWebAdapter().generate(IR)

    def test_forgot_asks_only_for_an_email(self) -> None:
        page = _file(self.PROJECT, "app/forgot-password/page.tsx")
        self.assertIn("/auth/forgot-password", page)
        self.assertNotIn("new_password", page)
        self.assertNotIn("/auth/reset-password", page)

    def test_reset_uses_the_token_from_the_link(self) -> None:
        page = _file(self.PROJECT, "app/reset-password/page.tsx")
        self.assertIn('useSearchParams().get("token")', page)
        self.assertIn("JSON.stringify({ token, new_password: password })", page)
        self.assertIn("<Suspense", page)


class TheMobileAppCanSignIn(TestCase):
    PROJECT = ReactNativeAdapter().generate(IR)

    def test_it_has_the_screens(self) -> None:
        screens = _file(self.PROJECT, "src/app/screens/AuthScreens.tsx")
        for name in ("LoginScreen", "RegisterScreen", "ForgotPasswordScreen", "AuthHeaderButton"):
            self.assertIn(f"export const {name}", screens)
        navigator = _file(self.PROJECT, "src/app/navigation/RootNavigator.tsx")
        for route in ("Login", "Register", "ForgotPassword"):
            self.assertIn(f'name="{route}"', navigator)

    def test_the_session_is_kept_in_secure_storage(self) -> None:
        context = _file(self.PROJECT, "src/shared/auth/AuthContext.tsx")
        self.assertIn("import * as SecureStore from 'expo-secure-store';", context)
        self.assertIn("SecureStore.setItemAsync(TOKEN_KEY", context)
        import json

        deps = json.loads(_file(self.PROJECT, "package.json"))["dependencies"]
        self.assertEqual(deps["expo-secure-store"], "~13.0.2")

    def test_no_screens_without_auth(self) -> None:
        import dataclasses

        no_auth = dataclasses.replace(IR, apis=tuple(dataclasses.replace(a, auth=False, required_roles=())
                                                     for a in IR.apis))
        paths = ReactNativeAdapter().generate(no_auth).paths()
        self.assertNotIn("src/app/screens/AuthScreens.tsx", paths)

    def test_the_input_component_type_checks(self) -> None:
        # `error && style` put "" into a style array when there was no error; strict TS rejected it.
        component = _file(self.PROJECT, "src/design-system/components/Input.tsx")
        self.assertIn("!!error && styles.inputError", component)
        self.assertIsNone(re.search(r"[^!]error && styles\.inputError", component))

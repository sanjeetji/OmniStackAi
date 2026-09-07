import ast
from dataclasses import replace
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import GoBackendAdapter, PythonBackendAdapter
from omnistackai_agent_engine.codegen.auth_guard import go_auth_file, needs_auth, python_auth_file


class NeedsAuthTests(TestCase):
    def test_true_when_any_endpoint_requires_auth(self) -> None:
        self.assertTrue(needs_auth(example_ir("minimal-blog")))  # POST /posts is auth=true

    def test_false_when_no_endpoint_requires_auth(self) -> None:
        ir = example_ir("minimal-blog")
        public = tuple(replace(api, auth=False) for api in ir.apis)
        self.assertFalse(needs_auth(replace(ir, apis=public)))


class PythonAuthTests(TestCase):
    def setUp(self) -> None:
        self.project = PythonBackendAdapter().generate(example_ir("minimal-blog"))

    def test_auth_module_emitted_and_valid(self) -> None:
        self.assertIn("app/auth.py", self.project.paths())
        auth = self.project.get("app/auth.py").content
        ast.parse(auth)
        self.assertIn("status_code=401", auth)
        self.assertIn('ROLES = ("author", "reader")', auth)

    def test_jwt_verification_and_dependency(self) -> None:
        auth = self.project.get("app/auth.py").content
        self.assertIn("import jwt", auth)
        self.assertIn('jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])', auth)
        self.assertIn('os.environ.get("JWT_SECRET", "")', auth)
        self.assertIn("status_code=500", auth)  # secret not configured
        self.assertIn("PyJWT==2.9.0", self.project.get("requirements.txt").content)
        self.assertIn("JWT_SECRET=", self.project.get(".env.example").content)

    def test_no_fabricated_secret(self) -> None:
        auth = self.project.get("app/auth.py").content
        # the secret only ever comes from the environment; no default value is baked in
        self.assertNotIn('JWT_SECRET", "some', auth)
        self.assertIn('os.environ.get("JWT_SECRET", "")', auth)

    def test_auth_route_declares_dependency_public_does_not(self) -> None:
        posts = self.project.get("app/routers/posts.py").content
        self.assertIn("from app.auth import require_auth", posts)
        # POST /posts is auth=true -> guarded; GET /posts is auth=false -> not guarded
        self.assertIn('@router.post("/posts", dependencies=[Depends(require_auth)])', posts)
        self.assertIn('@router.get("/posts")', posts)

    def test_no_auth_module_when_all_public(self) -> None:
        ir = example_ir("minimal-blog")
        public = replace(ir, apis=tuple(replace(api, auth=False) for api in ir.apis))
        project = PythonBackendAdapter().generate(public)
        self.assertNotIn("app/auth.py", project.paths())
        self.assertNotIn("require_auth", project.get("app/routers/posts.py").content)


class GoAuthTests(TestCase):
    def setUp(self) -> None:
        self.project = GoBackendAdapter().generate(example_ir("rideshare-favourites"))

    def test_auth_file_emitted_with_middleware_and_roles(self) -> None:
        self.assertIn("internal/handlers/auth.go", self.project.paths())
        auth = self.project.get("internal/handlers/auth.go").content
        self.assertIn("func RequireAuth(next http.HandlerFunc) http.HandlerFunc", auth)
        self.assertIn("http.StatusUnauthorized", auth)
        self.assertIn('var Roles = []string{"customer", "admin"}', auth)

    def test_jwt_verification_and_dependency(self) -> None:
        auth = self.project.get("internal/handlers/auth.go").content
        self.assertIn('"github.com/golang-jwt/jwt/v5"', auth)
        self.assertIn("jwt.ParseWithClaims(", auth)
        self.assertIn('os.Getenv("JWT_SECRET")', auth)
        self.assertIn("SigningMethodHMAC", auth)  # reject non-HMAC tokens
        self.assertIn("github.com/golang-jwt/jwt/v5 v5.2.1", self.project.get("go.mod").content)
        self.assertIn("JWT_SECRET=", self.project.get(".env.example").content)

    def test_main_wraps_auth_endpoints_only(self) -> None:
        main = self.project.get("main.go").content
        # auth=true -> wrapped
        self.assertIn('mux.HandleFunc("GET /favourites/drivers", handlers.RequireAuth(h.GetFavouritesDrivers))', main)
        # auth=false -> registered directly (GET /drivers)
        self.assertIn('mux.HandleFunc("GET /drivers", h.GetDrivers)', main)

    def test_no_auth_file_when_all_public(self) -> None:
        ir = example_ir("rideshare-favourites")
        public = replace(ir, apis=tuple(replace(api, auth=False) for api in ir.apis))
        project = GoBackendAdapter().generate(public)
        self.assertNotIn("internal/handlers/auth.go", project.paths())
        self.assertNotIn("RequireAuth", project.get("main.go").content)


class DeterminismTests(TestCase):
    def test_byte_stable(self) -> None:
        ir = example_ir("minimal-blog")
        self.assertEqual(python_auth_file(ir), python_auth_file(ir))
        self.assertEqual(go_auth_file(ir), go_auth_file(ir))

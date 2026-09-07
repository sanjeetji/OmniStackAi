import ast
from dataclasses import replace
from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    ApiEndpoint,
    HttpMethod,
    InvalidIRError,
    example_ir,
    has_errors,
    validate_ir,
)
from omnistackai_agent_engine.codegen import GoBackendAdapter, PythonBackendAdapter


def _blog_with_role(role: str = "author") -> "object":
    ir = example_ir("minimal-blog")
    apis = tuple(
        replace(api, required_roles=(role,)) if api.method.value == "POST" and api.path == "/posts" else api
        for api in ir.apis
    )
    return replace(ir, apis=apis)


class IrRequiredRolesTests(TestCase):
    def test_required_roles_serialize_round_trip(self) -> None:
        api = ApiEndpoint(HttpMethod.POST, "/posts", True, response_schema="Post", required_roles=("author",))
        self.assertEqual(api.to_dict()["required_roles"], ["author"])

    def test_required_roles_imply_auth(self) -> None:
        with self.assertRaises(InvalidIRError):
            ApiEndpoint(HttpMethod.POST, "/posts", auth=False, required_roles=("author",))

    def test_unknown_role_is_a_validation_error(self) -> None:
        self.assertTrue(has_errors(validate_ir(_blog_with_role("ghost"))))

    def test_known_role_validates_clean(self) -> None:
        self.assertFalse(has_errors(validate_ir(_blog_with_role("author"))))


class PythonRoleWiringTests(TestCase):
    def test_route_uses_require_roles(self) -> None:
        project = PythonBackendAdapter().generate(_blog_with_role("author"))
        posts = project.get("app/routers/posts.py").content
        ast.parse(posts)
        self.assertIn("from app.auth import require_roles", posts)
        self.assertIn('dependencies=[Depends(require_roles("author"))]', posts)
        auth = project.get("app/auth.py").content
        ast.parse(auth)
        self.assertIn("def require_roles(*required: str):", auth)
        self.assertIn("status_code=403", auth)


class GoRoleWiringTests(TestCase):
    def test_main_uses_require_roles(self) -> None:
        project = GoBackendAdapter().generate(_blog_with_role("author"))
        main = project.get("main.go").content
        self.assertIn('handlers.RequireRoles(', main)
        self.assertIn('"author"', main)
        auth = project.get("internal/handlers/auth.go").content
        self.assertIn("func RequireRoles(next http.HandlerFunc, required ...string)", auth)
        self.assertIn("StatusForbidden", auth)

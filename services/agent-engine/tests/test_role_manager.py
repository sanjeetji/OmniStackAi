"""PC-011 (R-590): an app's admin can give people their roles, on every backend.

Live on 2026-09-27 against PostgreSQL, the same on Python, Go, Express and Hono: a new account
could not list users (403); the seeded admin listed them with the roles author, reader, admin and
user, made the new account an author, and the author role came with its next sign-in; an unknown
role was 422 and demoting the last admin 409.
"""

from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.codegen.backend_go import GoBackendAdapter
from omnistackai_agent_engine.codegen.backend_node import NodeBackendAdapter
from omnistackai_agent_engine.codegen.backend_python import PythonBackendAdapter
from omnistackai_agent_engine.codegen.role_manager import assignable_roles

IR = example_ir("minimal-blog")


class EveryBackendServesTheSameTwoEndpoints(TestCase):
    def test_the_plans_roles_then_admin_and_user(self) -> None:
        self.assertEqual(assignable_roles(IR), ["author", "reader", "admin", "user"])

    def test_python(self) -> None:
        router = PythonBackendAdapter().generate(IR).get("app/routers/auth.py").content
        self.assertIn('@router.get("/users")', router)
        self.assertIn('@router.put("/users/{user_id}/role"', router)
        self.assertIn("ASSIGNABLE_ROLES = ('author', 'reader', 'admin', 'user',)", router)
        self.assertIn('detail="last_admin"', router)

    def test_go(self) -> None:
        project = GoBackendAdapter().generate(IR)
        main = project.get("main.go").content
        self.assertIn('mux.HandleFunc("GET /auth/users", h.AuthListUsers)', main)
        self.assertIn('mux.HandleFunc("PUT /auth/users/{id}/role", h.AuthSetUserRole)', main)
        self.assertIn('hasAnyRole(claims, []string{"admin"})', project.get("internal/handlers/auth_roles.go").content)

    def test_node(self) -> None:
        for framework in ("express", "hono"):
            project = NodeBackendAdapter(framework).generate(IR)
            with self.subTest(framework=framework):
                self.assertIn("export async function setUserRole", project.get("src/auth/core.ts").content)
                self.assertIn("ASSIGNABLE_ROLES: readonly string[] = ['author', 'reader', 'admin', 'user']",
                              project.get("src/auth/core.ts").content)
                routes = project.get("src/routes/account.ts").content
                self.assertIn("router.get('/users'", routes)
                self.assertIn("router.put('/users/:id/role'", routes)


class TheAdminConsoleHasTheUsersPage(TestCase):
    def test_admin_only(self) -> None:
        project = assemble_project(IR)
        paths = {f.path for f in project.files()}
        self.assertIn("apps/admin/app/users/page.tsx", paths)
        self.assertNotIn("apps/web/app/users/page.tsx", paths, "the public site has no role manager")
        self.assertIn("Users and roles", project.get("apps/admin/components/navbar.tsx").content)
        self.assertNotIn("Users and roles", project.get("apps/web/components/navbar.tsx").content)

    def test_the_page_says_when_a_role_applies(self) -> None:
        page = assemble_project(IR).get("apps/admin/app/users/page.tsx").content
        self.assertIn("It applies from their next sign-in.", page)
        self.assertIn("The app must keep at least one admin.", page)

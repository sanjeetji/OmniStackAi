"""Tests for Next.js route handler synthesis and backend proxy CRUD logic (R-460)."""

import unittest

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
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
)
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestNextjsRoutesCrud(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = ApplicationIR(
            name="Worker Attendance Management",
            description="Manage worker attendance and shifts",
            platforms=(Platform.WEB, Platform.BACKEND),
            project_strategy=ProjectStrategy(
                MobileProfile.NONE,
                WebStrategy.NEXTJS,
                AdminStrategy.NONE,
                BackendStrategy.PYTHON,
                DatabaseStrategy.POSTGRES,
                RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
            ),
            roles=(Role("admin"),),
            entities=(
                Entity(
                    "Employee",
                    (
                        Field("id", FieldType.UUID),
                        Field("name", FieldType.STRING),
                        Field("email", FieldType.STRING),
                    ),
                ),
                Entity(
                    "AttendanceRecord",
                    (
                        Field("id", FieldType.UUID),
                        Field("employee_id", FieldType.UUID),
                        Field("clock_in", FieldType.DATETIME),
                        Field("clock_out", FieldType.DATETIME, required=False),
                    ),
                ),
            ),
            screens=(
                Screen("employees", role="admin"),
                Screen("attendance", role="admin"),
            ),
            apis=(
                ApiEndpoint(HttpMethod.GET, "/api/v1/employees", auth=True),
                ApiEndpoint(HttpMethod.POST, "/api/v1/employees", auth=True),
                ApiEndpoint(HttpMethod.GET, "/api/v1/attendance", auth=True),
                ApiEndpoint(HttpMethod.POST, "/api/v1/attendance", auth=True),
                ApiEndpoint(HttpMethod.DELETE, "/api/v1/attendance/{id}", auth=True),
            ),
        )
        adapter = NextjsWebAdapter()
        self.project = adapter.generate(self.ir)

    def test_no_501_not_implemented_in_routes(self) -> None:
        """Route handlers must NOT be scaffolded stubs returning 501 not_implemented."""
        route_files = [f for f in self.project.files() if f.path.endswith("/route.ts")]
        self.assertTrue(len(route_files) > 0, "Expected at least one route.ts file")
        for rf in route_files:
            self.assertNotIn(
                "not_implemented",
                rf.content,
                f"File {rf.path} still contains 'not_implemented' stub",
            )
            self.assertNotIn(
                "status: 501",
                rf.content,
                f"File {rf.path} still returns status 501",
            )

    def test_route_handlers_proxy_to_backend(self) -> None:
        """Route handlers should resolve backend URL and forward requests."""
        attendance_route = self.project.get("app/api/v1/attendance/route.ts")
        self.assertIsNotNone(attendance_route)
        content = attendance_route.content

        # Verifies HTTP methods are exported
        self.assertIn("export async function GET(", content)
        self.assertIn("export async function POST(", content)

        # Verifies backend URL resolution
        self.assertIn("BACKEND_INTERNAL_URL", content)
        self.assertIn("NEXT_PUBLIC_API_URL", content)

        # Verifies fetch call and error handling
        self.assertIn("fetch(", content)
        self.assertIn("status: 503", content)
        self.assertIn("backend_unavailable", content)

    def test_route_handler_dynamic_param(self) -> None:
        """Dynamic route handlers should support parameterized endpoints."""
        del_route = self.project.get("app/api/v1/attendance/[id]/route.ts")
        self.assertIsNotNone(del_route)
        content = del_route.content
        self.assertIn("export async function DELETE(", content)
        self.assertIn("fetch(", content)


if __name__ == "__main__":
    unittest.main()

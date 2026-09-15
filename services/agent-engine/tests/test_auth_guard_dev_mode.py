"""Tests for development authentication bypass and production security enforcement (R-461)."""

import os
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import GoBackendAdapter, PythonBackendAdapter
from omnistackai_agent_engine.codegen.auth_guard import go_auth_file, python_auth_file


class TestAuthGuardDevMode(TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")

    def test_python_auth_guard_contains_dev_mode_bypass(self) -> None:
        """Python auth guard should allow dev admin session when running with dev secret or dev mode."""
        auth_content = python_auth_file(self.ir)
        self.assertIn("OMNISTACKAI_DEV_MODE", auth_content)
        self.assertIn("local-dev-secret", auth_content)
        self.assertIn("dev-admin", auth_content)
        self.assertIn("status_code=401", auth_content)  # Still enforces 401 in production

    def test_go_auth_guard_contains_dev_mode_bypass(self) -> None:
        """Go auth guard should allow dev admin session when running with dev secret or dev mode."""
        auth_content = go_auth_file(self.ir)
        self.assertIn("OMNISTACKAI_DEV_MODE", auth_content)
        self.assertIn("local-dev-secret", auth_content)
        self.assertIn("dev-admin", auth_content)
        self.assertIn("http.StatusUnauthorized", auth_content)  # Still enforces 401 in production

    def test_python_adapter_generates_auth_module_with_dev_mode(self) -> None:
        """Generated python backend includes dev mode support."""
        project = PythonBackendAdapter().generate(self.ir)
        auth = project.get("app/auth.py").content
        self.assertIn("dev_session", auth)
        self.assertIn("dev-admin", auth)

    def test_go_adapter_generates_auth_module_with_dev_mode(self) -> None:
        """Generated go backend includes dev mode support."""
        project = GoBackendAdapter().generate(self.ir)
        auth = project.get("internal/handlers/auth.go").content
        self.assertIn("dev-admin", auth)


if __name__ == "__main__":
    import unittest
    unittest.main()

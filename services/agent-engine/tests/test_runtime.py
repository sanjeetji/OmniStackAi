from unittest import TestCase
from unittest.mock import patch

from omnistackai_agent_engine.runtime import (
    DeploySelectionError,
    LocalRuntimeProvider,
    RuntimeProvider,
    RuntimeSelectionError,
    UnsupportedRuntimeTargetError,
    build_deploy_from_env,
    build_runtime_from_env,
)


class LocalRuntimeTests(TestCase):
    def setUp(self) -> None:
        self.provider = LocalRuntimeProvider()

    def test_satisfies_contract(self) -> None:
        self.assertIsInstance(self.provider, RuntimeProvider)
        self.assertEqual(self.provider.id, "local")

    def test_nextjs_plan(self) -> None:
        plan = self.provider.preview_plan("apps/web", "nextjs-web")
        self.assertEqual(plan.url, "http://127.0.0.1:3000")
        self.assertEqual([s.label for s in plan.steps], ["install", "dev"])
        self.assertEqual(plan.steps[0].command.display(), "pnpm install")
        self.assertEqual(plan.steps[1].command.display(), "pnpm dev")

    def test_python_plan(self) -> None:
        plan = self.provider.preview_plan("services/api", "backend-python")
        self.assertEqual(plan.url, "http://127.0.0.1:8000")
        self.assertIn("uvicorn app.main:app", plan.steps[-1].command.display())

    def test_go_plan(self) -> None:
        plan = self.provider.preview_plan("services/api", "backend-go")
        self.assertEqual(plan.url, "http://127.0.0.1:8080")
        self.assertEqual(plan.steps[-1].command.display(), "go run .")

    def test_unsupported_target(self) -> None:
        with self.assertRaises(UnsupportedRuntimeTargetError):
            self.provider.preview_plan("x", "flutter")


class RuntimeBootstrapTests(TestCase):
    def test_default_is_local_no_cloud(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            setup = build_runtime_from_env()
        self.assertEqual(setup.selected, "local")
        self.assertEqual(setup.active_cloud, ())
        self.assertIsInstance(setup.local, LocalRuntimeProvider)

    def test_cloud_activates_with_key_and_selection(self) -> None:
        env = {"E2B_API_KEY": "sekret-value", "OMNISTACKAI_RUNTIME_PROVIDER": "e2b"}
        with patch.dict("os.environ", env, clear=True):
            setup = build_runtime_from_env()
        self.assertIn("e2b", setup.active_cloud)
        self.assertEqual(setup.selected, "e2b")
        # the key value must never surface in the setup object's repr
        self.assertNotIn("sekret-value", repr(setup))

    def test_selecting_cloud_without_key_errors(self) -> None:
        with patch.dict("os.environ", {"OMNISTACKAI_RUNTIME_PROVIDER": "e2b"}, clear=True):
            with self.assertRaises(RuntimeSelectionError):
                build_runtime_from_env()

    def test_unknown_runtime_selection_errors(self) -> None:
        with patch.dict("os.environ", {"OMNISTACKAI_RUNTIME_PROVIDER": "mystery"}, clear=True):
            with self.assertRaises(RuntimeSelectionError):
                build_runtime_from_env()


class DeployBootstrapTests(TestCase):
    def test_default_is_none(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            setup = build_deploy_from_env()
        self.assertIsNone(setup.selected)
        self.assertEqual(setup.active, ())

    def test_vercel_activates_with_token(self) -> None:
        env = {"VERCEL_TOKEN": "tok", "OMNISTACKAI_DEPLOY_PROVIDER": "vercel"}
        with patch.dict("os.environ", env, clear=True):
            setup = build_deploy_from_env()
        self.assertIn("vercel", setup.active)
        self.assertEqual(setup.selected, "vercel")

    def test_selecting_deploy_without_key_errors(self) -> None:
        with patch.dict("os.environ", {"OMNISTACKAI_DEPLOY_PROVIDER": "fly"}, clear=True):
            with self.assertRaises(DeploySelectionError):
                build_deploy_from_env()

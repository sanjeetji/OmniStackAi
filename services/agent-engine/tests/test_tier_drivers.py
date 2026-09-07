from unittest import TestCase
from unittest.mock import patch

from omnistackai_agent_engine.runtime import (
    DeploymentProvider,
    DeploySelectionError,
    RuntimeProvider,
    RuntimeSelectionError,
    deploy_driver,
    format_status,
    platform_status,
    resolve_platform,
    resolve_tier,
    run_deploy,
    sandbox_driver,
)
from omnistackai_agent_engine.runtime.drivers import _DEPLOY_RECIPES  # noqa: PLC2701 (test introspection)
from omnistackai_agent_engine.runtime.providers import DEPLOY_SPECS, RUNTIME_SPECS


class TierResolutionTests(TestCase):
    def test_default_tier_is_zero_local(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            setup = resolve_platform()
        self.assertEqual(setup.tier, 0)
        self.assertEqual(setup.runtime_provider.id, "local")
        self.assertIsNone(setup.deploy_provider)

    def test_tier_1_is_local(self) -> None:
        with patch.dict("os.environ", {"OMNISTACKAI_TIER": "1"}, clear=True):
            setup = resolve_platform()
        self.assertEqual(setup.runtime_provider.id, "local")

    def test_tier_0_ignores_cloud_selection(self) -> None:
        env = {"OMNISTACKAI_TIER": "0", "OMNISTACKAI_DEPLOY_PROVIDER": "vercel", "VERCEL_TOKEN": "x"}
        with patch.dict("os.environ", env, clear=True):
            setup = resolve_platform()
        self.assertIsNone(setup.deploy_provider)  # tier 0 forces no deploy

    def test_tier_2_selects_cloud_with_keys(self) -> None:
        env = {
            "OMNISTACKAI_TIER": "2",
            "OMNISTACKAI_RUNTIME_PROVIDER": "e2b", "E2B_API_KEY": "sekret",
            "OMNISTACKAI_DEPLOY_PROVIDER": "vercel", "VERCEL_TOKEN": "tok",
        }
        with patch.dict("os.environ", env, clear=True):
            setup = resolve_platform()
        self.assertEqual(setup.runtime_provider.id, "e2b")
        self.assertEqual(setup.deploy_provider.id, "vercel")

    def test_tier_2_keyless_selection_errors(self) -> None:
        with patch.dict("os.environ", {"OMNISTACKAI_TIER": "2", "OMNISTACKAI_DEPLOY_PROVIDER": "fly"}, clear=True):
            with self.assertRaises(DeploySelectionError):
                resolve_platform()

    def test_invalid_tier_errors(self) -> None:
        with patch.dict("os.environ", {"OMNISTACKAI_TIER": "9"}, clear=True):
            with self.assertRaises(RuntimeSelectionError):
                resolve_tier()


class DriverTests(TestCase):
    def test_every_provider_has_a_driver(self) -> None:
        for name in DEPLOY_SPECS:
            self.assertIsInstance(deploy_driver(name), DeploymentProvider)
        for name in RUNTIME_SPECS:
            self.assertIsInstance(sandbox_driver(name), RuntimeProvider)

    def test_deploy_plans_use_provider_cli(self) -> None:
        self.assertEqual(deploy_driver("vercel").deploy_plan("apps/web", "nextjs-web").steps[0].command.program, "vercel")
        self.assertEqual(deploy_driver("netlify").deploy_plan("apps/web", "nextjs-web").steps[0].command.program, "netlify")
        self.assertEqual(deploy_driver("fly").deploy_plan("services/api", "backend-go").steps[-1].command.program, "fly")
        self.assertEqual(deploy_driver("render").deploy_plan("services/api", "backend-python").steps[0].command.program, "render")

    def test_sandbox_plan_reuses_target_commands(self) -> None:
        plan = sandbox_driver("e2b").preview_plan("apps/web", "nextjs-web")
        self.assertEqual(plan.provider_id, "e2b")
        self.assertEqual(plan.steps[0].command.display(), "pnpm install")
        self.assertTrue(plan.url.startswith("https://"))

    def test_no_key_value_appears_in_any_plan(self) -> None:
        secret = "sk-super-secret"
        env = {name_spec.key_env: secret for name_spec in {**DEPLOY_SPECS, **RUNTIME_SPECS}.values()}
        with patch.dict("os.environ", env, clear=True):
            for name in DEPLOY_SPECS:
                plan = deploy_driver(name).deploy_plan("apps/web", "nextjs-web")
                self.assertTrue(deploy_driver(name).active)
                rendered = " ".join(s.command.display() for s in plan.steps)
                self.assertNotIn(secret, rendered)
            for name in RUNTIME_SPECS:
                plan2 = sandbox_driver(name).preview_plan("apps/web", "nextjs-web")
                rendered2 = " ".join(s.command.display() for s in plan2.steps) + plan2.url
                self.assertNotIn(secret, rendered2)

    def test_recipes_exist_for_all_deploy_specs(self) -> None:
        self.assertEqual(set(_DEPLOY_RECIPES), set(DEPLOY_SPECS))


class StatusTests(TestCase):
    def test_status_reports_tier_and_keys(self) -> None:
        env = {"OMNISTACKAI_TIER": "2", "OMNISTACKAI_DEPLOY_PROVIDER": "vercel", "VERCEL_TOKEN": "t", "E2B_API_KEY": "k"}
        with patch.dict("os.environ", env, clear=True):
            status = platform_status()
            text = format_status()
        self.assertEqual(status["tier"], 2)
        self.assertEqual(status["deploy"], "vercel")
        self.assertIn("vercel", status["deploy_keys_present"])
        self.assertIn("e2b", status["sandbox_keys_present"])
        self.assertIn("Tier:", text)

    def test_run_deploy_is_callable(self) -> None:
        # ensure the executor exists and is a function (not executed here)
        self.assertTrue(callable(run_deploy))

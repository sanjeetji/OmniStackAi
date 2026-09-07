import json
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.projectplan import AppPlan, ProjectPlan, build_project_plan
from omnistackai_agent_engine.runtime import deploy_driver

FAKE_KEY = "unit-test-key-do-not-use"


class CompositionTests(TestCase):
    def setUp(self) -> None:
        self.plan = build_project_plan(example_ir("rideshare-favourites"))

    def test_one_app_plan_per_assembled_app(self) -> None:
        self.assertIsInstance(self.plan, ProjectPlan)
        by_dir = {app.app_dir: app for app in self.plan.apps}
        self.assertEqual(set(by_dir), {"apps/web", "services/api"})
        self.assertTrue(all(isinstance(app, AppPlan) for app in self.plan.apps))

    def test_preview_and_verify_present_no_deploy_by_default(self) -> None:
        for app in self.plan.apps:
            self.assertIsNotNone(app.preview)   # both targets run locally
            self.assertIsNotNone(app.verify)    # both targets have a verify ladder
            self.assertIsNone(app.deploy)       # no deploy provider passed
        web = next(a for a in self.plan.apps if a.app_dir == "apps/web")
        self.assertEqual(web.preview.url, "http://127.0.0.1:3000")
        self.assertIn("install", [k.value for k in web.verify.gates()])

    def test_render_lists_each_app(self) -> None:
        text = self.plan.render()
        self.assertIn("web (Next.js)  [nextjs-web]  (apps/web)", text)
        self.assertIn("preview -> http://127.0.0.1:8080", text)  # go backend
        self.assertIn("verify gates:", text)


class DeployOptInTests(TestCase):
    def test_deploy_plan_included_only_when_provider_passed(self) -> None:
        provider = deploy_driver("vercel")
        plan = build_project_plan(example_ir("rideshare-favourites"), deploy=provider)
        for app in plan.apps:
            self.assertIsNotNone(app.deploy)
            self.assertEqual(app.deploy.provider_id, "vercel")


class SerializationTests(TestCase):
    def test_to_dict_is_json_serializable_and_secret_free(self) -> None:
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"VERCEL_TOKEN": FAKE_KEY}, clear=False):
            provider = deploy_driver("vercel")
            plan = build_project_plan(example_ir("minimal-blog"), deploy=provider)
        blob = json.dumps(plan.to_dict())  # raises if not serializable
        self.assertNotIn(FAKE_KEY, blob)
        self.assertIn('"appName"', blob)
        self.assertIn('"gates"', blob)

    def test_deterministic(self) -> None:
        ir = example_ir("minimal-blog")
        self.assertEqual(build_project_plan(ir).to_dict(), build_project_plan(ir).to_dict())

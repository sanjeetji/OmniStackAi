import json
from unittest import TestCase
from unittest.mock import patch

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.console_snapshot import platform_console_snapshot


class BuilderShowcaseTests(TestCase):
    def setUp(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.snapshot = platform_console_snapshot()
        self.showcase = self.snapshot["builderShowcase"]

    def test_real_project_plan_has_web_and_api_preview_and_verify(self) -> None:
        plan = self.showcase["projectPlan"]
        self.assertEqual(plan["appName"], example_ir("rideshare-favourites").name)
        apps = {app["appDir"]: app for app in plan["apps"]}
        self.assertEqual(set(apps), {"apps/web", "services/api"})
        for app in apps.values():
            self.assertIsNotNone(app["preview"])
            self.assertGreater(len(app["verify"]["steps"]), 0)
            self.assertIsNone(app["deploy"])

    def test_edit_preview_is_a_real_hunk_level_patch(self) -> None:
        edit = self.showcase["editPreview"]
        self.assertEqual(edit["baseExample"], "minimal-blog")
        self.assertEqual(
            {change["path"] for change in edit["changes"]},
            {
                "README.md",
                "apps/web/README.md",
                "apps/web/app/layout.tsx",
                "contracts/openapi.json",
                "services/api/README.md",
                "services/api/openapi.json",
            },
        )
        self.assertTrue(all(change["kind"] == "modified" for change in edit["changes"]))
        self.assertIn("--- a/README.md", edit["unifiedPatch"])
        self.assertIn("+++ b/README.md", edit["unifiedPatch"])
        self.assertIn("@@", edit["unifiedPatch"])
        self.assertLess(len(edit["unifiedPatch"]), 10_000)

    def test_snapshot_is_deterministic_and_json_serializable(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            again = platform_console_snapshot()
        self.assertEqual(self.snapshot, again)
        json.dumps(self.snapshot)


class SnapshotSafetyTests(TestCase):
    def test_provider_secret_value_is_not_serialized(self) -> None:
        secret = "r247-never-serialize-this-key"
        with patch.dict("os.environ", {"OPENAI_API_KEY": secret}, clear=True):
            snapshot = platform_console_snapshot()
        self.assertNotIn(secret, json.dumps(snapshot))

    def test_existing_model_fabric_overview_is_preserved(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            snapshot = platform_console_snapshot()
        self.assertEqual(snapshot["routingMode"], "balanced")
        self.assertIn("providers", snapshot)
        self.assertIn("priceBook", snapshot)
        self.assertIn("usage", snapshot)

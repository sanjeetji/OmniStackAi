"""R-574: store publishing from the Studio, complete except for the owner's accounts.

A project's mobile app is checked, built (EAS, in Expo's cloud) and submitted to Google Play and the
App Store with credentials that are the project's secrets. Key files exist only while a command
runs; `eas.json` is restored after an iOS submit fills in the owner's IDs; no secret reaches the
output. The eas-cli settings used here were checked against eas-cli 24.8.0's own code.
"""

import json
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.git_service.materialize import materialize_project
from omnistackai_agent_engine.publish import store_release as sr

FULL = {"EXPO_TOKEN": "expo-token-123456", "EAS_PROJECT_ID": "0f5a-project", "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON": '{"type":"service_account","private_key":"play-secret-key"}',
        "ASC_API_KEY_P8": "-" * 5 + "BEGIN " + "PRIVATE KEY" + "-" * 5 + "apple-test-value", "ASC_API_KEY_ID": "KEY123",
        "ASC_API_ISSUER_ID": "issuer-uuid", "APPLE_TEAM_ID": "A1B2C3D4E5", "ASC_APP_ID": "6478123456"}


class _Repo:
    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        blog = example_ir("minimal-blog")
        ir = replace(blog, project_strategy=replace(blog.project_strategy, mobile_profile="react_native"))
        root = Path(self._tmp.name) / "repo"
        materialize_project(assemble_project(ir), root)
        return root

    def __exit__(self, *exc) -> None:
        self._tmp.cleanup()


class TheCheckSaysWhatIsMissingAndWhere(TestCase):
    def test_nothing_set(self) -> None:
        with _Repo() as repo:
            android = sr.check(repo, "android", {})
            self.assertFalse(android.ok)
            self.assertEqual({m["name"] for m in android.missing}, {"EXPO_TOKEN", "EAS_PROJECT_ID", "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON"})
            self.assertTrue(all(m["where"] for m in android.missing), "each says where to get it")
            ios = sr.check(repo, "ios", {})
            self.assertIn("ASC_API_KEY_P8", {m["name"] for m in ios.missing})
            self.assertTrue(any("privacy policy" in w for w in ios.warnings))
            self.assertTrue(any("bundle identifier" in w for w in ios.warnings))

    def test_build_possible_before_the_upload_credentials(self) -> None:
        with _Repo() as repo:
            result = sr.check(repo, "android", {"EXPO_TOKEN": "x" * 10, "EAS_PROJECT_ID": "p"})
            self.assertTrue(result.details["can_build"])
            self.assertFalse(result.details["can_submit"])

    def test_a_project_without_a_mobile_app(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("no mobile app", sr.check(Path(tmp), "android", FULL).output)


class AReleaseRunsWithTheOwnersCredentialsAndKeepsNone(TestCase):
    def test_a_missing_credential_refuses_before_anything_runs(self) -> None:
        calls = []
        with _Repo() as repo:
            result = sr.release(repo, "ios", "submit", {"EXPO_TOKEN": "t" * 10}, runner=lambda *a: calls.append(a))
        self.assertFalse(result.ok)
        self.assertEqual(calls, [])

    def test_ios_submit_writes_the_key_fills_eas_json_then_cleans_both(self) -> None:
        seen = {}

        def runner(cmd, cwd, env):
            seen["cmd"], seen["env"] = cmd, env
            seen["key"] = (cwd / "credentials/asc-api-key.p8").read_text()
            seen["eas"] = json.loads((cwd / "eas.json").read_text())
            return subprocess.CompletedProcess(cmd, 0, stdout="submitted with expo-token-123456", stderr="")

        with _Repo() as repo:
            app = repo / "apps/mobile"
            before = (app / "eas.json").read_text()
            result = sr.release(repo, "ios", "submit", FULL, runner=runner)
            self.assertTrue(result.ok)
            self.assertFalse((app / "credentials/asc-api-key.p8").exists(), "the key file is deleted after the run")
            self.assertEqual((app / "eas.json").read_text(), before, "eas.json is restored byte for byte")
        self.assertEqual(seen["cmd"][2:5], ["eas-cli@24.8.0", "submit", "--platform"])
        self.assertIn("--non-interactive", seen["cmd"])
        self.assertIn("apple-test-value", seen["key"])
        ios = seen["eas"]["submit"]["production"]["ios"]
        self.assertEqual((ios["ascAppId"], ios["ascApiKeyId"], ios["ascApiKeyIssuerId"]), ("6478123456", "KEY123", "issuer-uuid"))
        for name in ("EXPO_TOKEN", "EXPO_ASC_API_KEY_PATH", "EXPO_ASC_KEY_ID", "EXPO_ASC_ISSUER_ID", "EXPO_APPLE_TEAM_ID"):
            self.assertIn(name, seen["env"])
        self.assertNotIn("expo-token-123456", result.output, "secrets never reach the output")

    def test_android_build_reports_the_build_link(self) -> None:
        def runner(cmd, cwd, env):
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps([{"id": "b1", "status": "NEW", "accountName": "me",
                                                                          "projectName": "blog"}]), stderr="")

        with _Repo() as repo:
            result = sr.release(repo, "android", "build", FULL, runner=runner)
        self.assertEqual(result.details["url"], "https://expo.dev/accounts/me/projects/blog/builds/b1")

    def test_a_rejected_token_says_what_to_do(self) -> None:
        def runner(cmd, cwd, env):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="npm warn deprecated glob@6\n    Error: GraphQL request failed.\n")

        with _Repo() as repo:
            result = sr.release(repo, "android", "build", FULL, runner=runner)
        self.assertFalse(result.ok)
        self.assertTrue(result.output.startswith("Expo did not accept EXPO_TOKEN"))
        self.assertNotIn("npm warn", result.output)


class TheGeneratedAppIsReadyForANonInteractiveRelease(TestCase):
    def test_eas_json_and_app_config(self) -> None:
        blog = example_ir("minimal-blog")
        ir = replace(blog, project_strategy=replace(blog.project_strategy, mobile_profile="react_native"))
        files = {f.path: f.content for f in assemble_project(ir).files()}
        ios = json.loads(files["apps/mobile/eas.json"])["submit"]["production"]["ios"]
        self.assertEqual(ios, {"ascApiKeyPath": "./credentials/asc-api-key.p8"}, "no Apple ID password flow")
        self.assertIn("process.env.EAS_PROJECT_ID", files["apps/mobile/app.config.js"])

import tempfile
import unittest
from pathlib import Path

from omnistackai_agent_engine.localrun.plan import build_run_plan
from omnistackai_agent_engine.studio.preview import StudioPreviewManager


class TestStudioWorkspaceSecrets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.tmp.name)
        # Create minimal structure
        (self.repo_dir / "services" / "api").mkdir(parents=True)
        (self.repo_dir / "services" / "api" / "requirements.txt").write_text("fastapi\n")
        (self.repo_dir / "apps" / "web").mkdir(parents=True)
        (self.repo_dir / "apps" / "web" / "package.json").write_text('{"name": "web"}')

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_run_plan_with_extra_env(self):
        secrets = {
            "STRIPE_API_KEY": "sk_test_123456",
            "SMTP_PASSWORD": "secret_smtp_password",
        }
        plan = build_run_plan(str(self.repo_dir), extra_env=secrets)

        # Check backend step
        backend_steps = [s for s in plan.steps if s.label.startswith("start backend API")]
        self.assertEqual(len(backend_steps), 1)
        backend_env = dict(backend_steps[0].env)
        self.assertEqual(backend_env.get("STRIPE_API_KEY"), "sk_test_123456")
        self.assertEqual(backend_env.get("SMTP_PASSWORD"), "secret_smtp_password")

        # Check web step
        web_steps = [s for s in plan.steps if s.label.startswith("start web app")]
        self.assertEqual(len(web_steps), 1)
        web_env = dict(web_steps[0].env)
        self.assertEqual(web_env.get("STRIPE_API_KEY"), "sk_test_123456")
        self.assertEqual(web_env.get("SMTP_PASSWORD"), "secret_smtp_password")

        # Verify secrets are NOT written to any file in repo
        for file_path in self.repo_dir.rglob("*"):
            if file_path.is_file():
                content = file_path.read_text()
                self.assertNotIn("sk_test_123456", content)
                self.assertNotIn("secret_smtp_password", content)

    def test_start_workspace_forwards_env(self):
        received_kwargs = {}

        def mock_start(repo_dir, log=None, on_phase=None, extra_env=None):
            received_kwargs["extra_env"] = extra_env
            plan = build_run_plan(str(self.repo_dir), extra_env=extra_env)
            from omnistackai_agent_engine.localrun import LocalAppSession
            sess = LocalAppSession(plan)
            sess.web_ready = True
            sess.api_ready = True
            sess.is_alive = lambda: True
            sess.stop = lambda: None
            return sess

        mgr = StudioPreviewManager(start_fn=mock_start)
        secrets = {"PAYMENT_SECRET": "ps_live_999"}
        res = mgr.start_workspace("ws-secrets", str(self.repo_dir), env=secrets)

        self.assertEqual(res["status"], "ready")
        self.assertEqual(received_kwargs.get("extra_env"), secrets)


if __name__ == "__main__":
    unittest.main()

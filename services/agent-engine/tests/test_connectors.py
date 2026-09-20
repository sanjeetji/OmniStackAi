"""Unit tests for Connectors framework and codegen hooks (G-03 / R-511)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from omnistackai_agent_engine.studio.connectors import (
    ConnectorError,
    apply_connector,
    remove_connector,
)
from omnistackai_agent_engine.studio.server import (
    StudioWorkspaceStore,
    create_studio_server,
)


class TestConnectorsCodegen(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.repo_dir = Path(self.tmp_dir) / "repo"
        self.repo_dir.mkdir(parents=True, exist_ok=True)

        # Initialize git repo in repo_dir
        subprocess.run(["git", "init", "-q"], cwd=str(self.repo_dir), check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(self.repo_dir), check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(self.repo_dir), check=True)

        # Create basic app/layout.tsx
        app_dir = self.repo_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        self.layout_file = app_dir / "layout.tsx"
        self.layout_file.write_text(
            """export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head />
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}
""",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "-A"], cwd=str(self.repo_dir), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "Initial commit"], cwd=str(self.repo_dir), check=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_ga4_apply_and_remove(self) -> None:
        # 1. Apply GA4
        res = apply_connector(self.repo_dir, "ga4", {"measurement_id": "G-ABC123XYZ"})
        self.assertEqual(res["status"], "applied")
        self.assertEqual(res["provider"], "ga4")

        # Verify GoogleAnalytics.tsx exists
        ga_file = self.repo_dir / "components" / "GoogleAnalytics.tsx"
        self.assertTrue(ga_file.is_file())
        self.assertIn("gtag('config', '${measurementId}')", ga_file.read_text())

        # Verify layout.tsx was modified with component and import
        layout_content = self.layout_file.read_text()
        self.assertIn("import { GoogleAnalytics } from '@/components/GoogleAnalytics';", layout_content)
        self.assertIn('<GoogleAnalytics measurementId="G-ABC123XYZ" />', layout_content)

        # Verify git commit was created
        log = subprocess.run(["git", "log", "-1", "--oneline"], cwd=str(self.repo_dir), capture_output=True, text=True, check=True)
        self.assertIn("enable Google Analytics 4", log.stdout)

        # 2. Remove GA4
        remove_res = remove_connector(self.repo_dir, "ga4")
        self.assertEqual(remove_res["status"], "removed")
        self.assertFalse(ga_file.is_file())

        cleaned_layout = self.layout_file.read_text()
        self.assertNotIn("GoogleAnalytics", cleaned_layout)

        log_after_remove = subprocess.run(["git", "log", "-1", "--oneline"], cwd=str(self.repo_dir), capture_output=True, text=True, check=True)
        self.assertIn("disable Google Analytics 4", log_after_remove.stdout)

    def test_ga4_validation(self) -> None:
        with self.assertRaises(ConnectorError):
            apply_connector(self.repo_dir, "ga4", {})

        with self.assertRaises(ConnectorError):
            apply_connector(self.repo_dir, "ga4", {"measurement_id": "invalid-id"})

    def test_resend_apply_and_remove(self) -> None:
        # 1. Apply Resend
        res = apply_connector(self.repo_dir, "resend", {
            "api_key": "re_123456789",
            "from_email": "notifications@myapp.com",
        })
        self.assertEqual(res["status"], "applied")

        email_ts = self.repo_dir / "lib" / "email.ts"
        route_ts = self.repo_dir / "app" / "api" / "send" / "route.ts"
        env_file = self.repo_dir / ".env.local"

        self.assertTrue(email_ts.is_file())
        self.assertTrue(route_ts.is_file())
        self.assertTrue(env_file.is_file())

        self.assertIn("https://api.resend.com/emails", email_ts.read_text())
        self.assertIn("RESEND_API_KEY=re_123456789", env_file.read_text())
        self.assertIn("RESEND_FROM_EMAIL=notifications@myapp.com", env_file.read_text())

        # 2. Remove Resend
        remove_res = remove_connector(self.repo_dir, "resend")
        self.assertEqual(remove_res["status"], "removed")
        self.assertFalse(email_ts.is_file())
        self.assertFalse(route_ts.is_file())
        self.assertNotIn("RESEND_", env_file.read_text())

    def test_smtp_apply_and_remove(self) -> None:
        # 1. Apply SMTP
        res = apply_connector(self.repo_dir, "smtp", {
            "host": "smtp.mailgun.org",
            "port": "587",
            "username": "postmaster@mail.example.com",
            "password": "secretpassword",
            "from_email": "alerts@example.com",
        })
        self.assertEqual(res["status"], "applied")

        email_ts = self.repo_dir / "lib" / "email.ts"
        route_ts = self.repo_dir / "app" / "api" / "send" / "route.ts"
        env_file = self.repo_dir / ".env.local"

        self.assertTrue(email_ts.is_file())
        self.assertTrue(route_ts.is_file())
        self.assertIn("SMTP_HOST=smtp.mailgun.org", env_file.read_text())
        self.assertIn("SMTP_USER=postmaster@mail.example.com", env_file.read_text())

        # 2. Remove SMTP
        remove_res = remove_connector(self.repo_dir, "smtp")
        self.assertEqual(remove_res["status"], "removed")
        self.assertFalse(email_ts.is_file())
        self.assertFalse(route_ts.is_file())
        self.assertNotIn("SMTP_", env_file.read_text())

    def test_unsupported_provider(self) -> None:
        with self.assertRaises(ConnectorError):
            apply_connector(self.repo_dir, "unknown_service", {})


class TestConnectorsHttpApi(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.ws_root = Path(self.tmp_dir) / "workspaces"
        self.ws_root.mkdir(parents=True, exist_ok=True)
        self.ws_store = StudioWorkspaceStore(self.ws_root)
        self.ws_id = "test-ws-1"
        self.ws_store.ensure_workspace(self.ws_id)

        # Initialize git repo in workspace repo
        repo_dir = self.ws_store.repo_path(self.ws_id)
        subprocess.run(["git", "init", "-q"], cwd=str(repo_dir), check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(repo_dir), check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(repo_dir), check=True)

        app_dir = repo_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "layout.tsx").write_text("export default function Layout({children}: any){return <body>{children}</body>}", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(repo_dir), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(repo_dir), check=True)

        self.server = create_studio_server(
            host="127.0.0.1",
            port=0,
            build_fn=lambda p: {},
            workspace_store=self.ws_store,
        )
        self.port = self.server.server_port
        import threading
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_http_apply_and_remove_ga4(self) -> None:
        import urllib.request

        # 1. Apply GA4
        url = f"http://127.0.0.1:{self.port}/api/workspaces/{self.ws_id}/connectors/apply"
        req = urllib.request.Request(
            url,
            data=json.dumps({"provider": "ga4", "config": {"measurement_id": "G-TEST999"}}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "applied")
            self.assertEqual(data["provider"], "ga4")

        # 2. Remove GA4
        remove_url = f"http://127.0.0.1:{self.port}/api/workspaces/{self.ws_id}/connectors/remove"
        req_del = urllib.request.Request(
            remove_url,
            data=json.dumps({"provider": "ga4"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req_del) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "removed")


if __name__ == "__main__":
    unittest.main()

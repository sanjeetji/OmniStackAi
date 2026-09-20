"""Unit tests for Payments framework and codegen hooks (G-04 / R-512)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from omnistackai_agent_engine.studio.payments import (
    PaymentsError,
    apply_payments,
    remove_payments,
)
from omnistackai_agent_engine.studio.server import (
    StudioWorkspaceStore,
    create_studio_server,
)


class TestPaymentsCodegen(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.repo_dir = Path(self.tmp_dir) / "repo"
        self.repo_dir.mkdir(parents=True, exist_ok=True)

        # Initialize git repo in repo_dir
        subprocess.run(["git", "init", "-q"], cwd=str(self.repo_dir), check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(self.repo_dir), check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(self.repo_dir), check=True)

        # Create basic app directory
        app_dir = self.repo_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "page.tsx").write_text("export default function Page() { return <h1>Store</h1>; }", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(self.repo_dir), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "Initial commit"], cwd=str(self.repo_dir), check=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_stripe_apply_and_remove(self) -> None:
        # 1. Apply Stripe
        res = apply_payments(self.repo_dir, "stripe")
        self.assertEqual(res["status"], "applied")
        self.assertEqual(res["gateway"], "stripe")

        # Verify generated files
        stripe_lib = self.repo_dir / "lib" / "payments" / "stripe.ts"
        self.assertTrue(stripe_lib.is_file())
        self.assertIn("createCheckoutSession", stripe_lib.read_text())
        self.assertIn("verifyStripeWebhookSignature", stripe_lib.read_text())

        checkout_route = self.repo_dir / "app" / "api" / "checkout" / "route.ts"
        self.assertTrue(checkout_route.is_file())
        self.assertIn("createCheckoutSession", checkout_route.read_text())

        webhook_route = self.repo_dir / "app" / "api" / "webhooks" / "stripe" / "route.ts"
        self.assertTrue(webhook_route.is_file())
        self.assertIn("verifyStripeWebhookSignature", webhook_route.read_text())
        self.assertIn("processedEvents", webhook_route.read_text())

        success_page = self.repo_dir / "app" / "checkout" / "success" / "page.tsx"
        self.assertTrue(success_page.is_file())
        self.assertIn("Payment Successful", success_page.read_text())

        cancel_page = self.repo_dir / "app" / "checkout" / "cancel" / "page.tsx"
        self.assertTrue(cancel_page.is_file())
        self.assertIn("Payment Cancelled", cancel_page.read_text())

        test_script = self.repo_dir / "tests" / "payments" / "test_stripe_webhook.js"
        self.assertTrue(test_script.is_file())

        # Verify .env.example contains Stripe keys
        env_ex = self.repo_dir / ".env.example"
        self.assertTrue(env_ex.is_file())
        env_text = env_ex.read_text()
        self.assertIn("STRIPE_SECRET_KEY=", env_text)
        self.assertIn("STRIPE_WEBHOOK_SECRET=", env_text)
        self.assertIn("NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=", env_text)

        # Verify git commit
        log = subprocess.run(["git", "log", "-1", "--oneline"], cwd=str(self.repo_dir), capture_output=True, text=True, check=True)
        self.assertIn("enable stripe payment gateway", log.stdout.lower())

        # Run verification test script via node
        node_check = subprocess.run(["node", str(test_script)], cwd=str(self.repo_dir), capture_output=True, text=True)
        self.assertEqual(node_check.returncode, 0, f"Node verification failed: {node_check.stderr} {node_check.stdout}")
        self.assertIn("3/3 tests passed successfully", node_check.stdout)

        # 2. Remove Stripe
        remove_res = remove_payments(self.repo_dir, "stripe")
        self.assertEqual(remove_res["status"], "removed")
        self.assertFalse(stripe_lib.is_file())
        self.assertFalse(checkout_route.is_file())
        self.assertFalse(webhook_route.is_file())
        self.assertFalse(success_page.is_file())
        self.assertFalse(cancel_page.is_file())
        self.assertFalse(test_script.is_file())

        # Verify .env.example cleaned
        cleaned_env = env_ex.read_text()
        self.assertNotIn("STRIPE_SECRET_KEY", cleaned_env)

        # Verify git commit
        log_remove = subprocess.run(["git", "log", "-1", "--oneline"], cwd=str(self.repo_dir), capture_output=True, text=True, check=True)
        self.assertIn("disable stripe payment gateway", log_remove.stdout.lower())

    def test_razorpay_apply_and_remove(self) -> None:
        # 1. Apply Razorpay
        res = apply_payments(self.repo_dir, "razorpay")
        self.assertEqual(res["status"], "applied")
        self.assertEqual(res["gateway"], "razorpay")

        # Verify generated files
        razorpay_lib = self.repo_dir / "lib" / "payments" / "razorpay.ts"
        self.assertTrue(razorpay_lib.is_file())
        self.assertIn("createRazorpayOrder", razorpay_lib.read_text())
        self.assertIn("verifyRazorpayWebhookSignature", razorpay_lib.read_text())

        checkout_route = self.repo_dir / "app" / "api" / "checkout" / "route.ts"
        self.assertTrue(checkout_route.is_file())
        self.assertIn("createRazorpayOrder", checkout_route.read_text())

        webhook_route = self.repo_dir / "app" / "api" / "webhooks" / "razorpay" / "route.ts"
        self.assertTrue(webhook_route.is_file())
        self.assertIn("verifyRazorpayWebhookSignature", webhook_route.read_text())
        self.assertIn("processedEvents", webhook_route.read_text())

        test_script = self.repo_dir / "tests" / "payments" / "test_razorpay_webhook.js"
        self.assertTrue(test_script.is_file())

        # Verify .env.example contains Razorpay keys
        env_ex = self.repo_dir / ".env.example"
        self.assertTrue(env_ex.is_file())
        env_text = env_ex.read_text()
        self.assertIn("RAZORPAY_KEY_ID=", env_text)
        self.assertIn("RAZORPAY_KEY_SECRET=", env_text)
        self.assertIn("RAZORPAY_WEBHOOK_SECRET=", env_text)

        # Run verification test script via node
        node_check = subprocess.run(["node", str(test_script)], cwd=str(self.repo_dir), capture_output=True, text=True)
        self.assertEqual(node_check.returncode, 0, f"Node verification failed: {node_check.stderr} {node_check.stdout}")
        self.assertIn("3/3 tests passed successfully", node_check.stdout)

        # 2. Remove Razorpay
        remove_res = remove_payments(self.repo_dir, "razorpay")
        self.assertEqual(remove_res["status"], "removed")
        self.assertFalse(razorpay_lib.is_file())
        self.assertFalse(checkout_route.is_file())
        self.assertFalse(webhook_route.is_file())

        # Verify .env.example cleaned
        cleaned_env = env_ex.read_text()
        self.assertNotIn("RAZORPAY_KEY_ID", cleaned_env)

    def test_unsupported_gateway(self) -> None:
        with self.assertRaises(PaymentsError):
            apply_payments(self.repo_dir, "paypal")

        with self.assertRaises(PaymentsError):
            remove_payments(self.repo_dir, "square")


class TestPaymentsHttpApi(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.ws_root = Path(self.tmp_dir) / "workspaces"
        self.ws_root.mkdir(parents=True, exist_ok=True)
        self.ws_store = StudioWorkspaceStore(self.ws_root)
        self.ws_id = "test-ws-pay"
        self.ws_store.ensure_workspace(self.ws_id)

        # Initialize git repo in workspace repo
        repo_dir = self.ws_store.repo_path(self.ws_id)
        subprocess.run(["git", "init", "-q"], cwd=str(repo_dir), check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(repo_dir), check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(repo_dir), check=True)

        app_dir = repo_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "page.tsx").write_text("export default function Page(){return <div>Hi</div>}", encoding="utf-8")
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

    def test_http_apply_and_remove_stripe(self) -> None:
        import urllib.request

        # 1. Apply Stripe
        url = f"http://127.0.0.1:{self.port}/api/workspaces/{self.ws_id}/payments/apply"
        req = urllib.request.Request(
            url,
            data=json.dumps({"gateway": "stripe"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "applied")
            self.assertEqual(data["gateway"], "stripe")

        # 2. Remove Stripe
        remove_url = f"http://127.0.0.1:{self.port}/api/workspaces/{self.ws_id}/payments/remove"
        req_del = urllib.request.Request(
            remove_url,
            data=json.dumps({"gateway": "stripe"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req_del) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "removed")
            self.assertEqual(data["gateway"], "stripe")


if __name__ == "__main__":
    unittest.main()

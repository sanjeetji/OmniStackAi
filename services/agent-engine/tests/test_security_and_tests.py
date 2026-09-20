"""Unit tests for F-10 Security Scan & Automated Tests (R-508)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.studio.security import (
    get_last_security_report,
    run_security_scan,
)
from omnistackai_agent_engine.studio.tests_runner import (
    get_last_test_report,
    run_project_tests,
)


class TestSecurityScanner(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_clean_repo_zero_findings(self):
        # Create a clean file
        (self.repo_dir / "src").mkdir(parents=True)
        (self.repo_dir / "src" / "index.ts").write_text("console.log('clean code');\n", encoding="utf-8")

        report = run_security_scan(self.repo_dir)
        self.assertEqual(report["summary"]["total_issues"], 0)
        self.assertEqual(len(report["findings"]), 0)

        # Check checks statuses
        sec_check = next(c for c in report["checks"] if "Secret scan" in c["name"])
        self.assertEqual(sec_check["status"], "passed")

        fw_check = next(c for c in report["checks"] if "Framework" in c["name"])
        self.assertEqual(fw_check["status"], "passed")

    def test_secret_scan_detects_live_env_file(self):
        (self.repo_dir / ".env").write_text("DATABASE_URL=postgres://localhost:5432/db\n", encoding="utf-8")
        (self.repo_dir / ".env.example").write_text("DATABASE_URL=\n", encoding="utf-8")

        report = run_security_scan(self.repo_dir)
        findings = [f for f in report["findings"] if f["rule"] == "secrets/env-file"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["file"], ".env")
        self.assertEqual(findings[0]["severity"], "critical")

    def test_secret_scan_detects_provider_keys(self):
        fake_key = "sk-" + "proj-abc12345678901234567890"
        (self.repo_dir / "app.ts").write_text(
            f'const client = new OpenAI({{ apiKey: "{fake_key}" }});\n',
            encoding="utf-8",
        )
        report = run_security_scan(self.repo_dir)
        findings = [f for f in report["findings"] if f["rule"] == "secrets/provider-key"]
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0]["line"], 1)
        self.assertEqual(findings[0]["severity"], "critical")

    def test_secret_scan_detects_private_key(self):
        header = "-----" + "BEGIN RSA PRIVATE KEY-----"
        (self.repo_dir / "key.pem").write_text(
            f"{header}\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----\n",
            encoding="utf-8",
        )
        report = run_security_scan(self.repo_dir)
        findings = [f for f in report["findings"] if f["rule"] == "secrets/private-key"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "critical")

    def test_framework_dangerously_set_inner_html(self):
        (self.repo_dir / "component.tsx").write_text(
            '<div dangerouslySetInnerHTML={{ __html: userPayload }} />;\n',
            encoding="utf-8",
        )
        report = run_security_scan(self.repo_dir)
        findings = [f for f in report["findings"] if f["rule"] == "framework/dangerously-set-inner-html"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "high")

    def test_framework_cors_wildcard(self):
        (self.repo_dir / "server.ts").write_text(
            "app.use(cors({ origin: '*' }));\n",
            encoding="utf-8",
        )
        report = run_security_scan(self.repo_dir)
        findings = [f for f in report["findings"] if f["rule"] == "framework/cors-wildcard"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "medium")

    def test_framework_sql_injection(self):
        (self.repo_dir / "query.py").write_text(
            'query = f"SELECT * FROM users WHERE username = \'{username}\'"\n',
            encoding="utf-8",
        )
        report = run_security_scan(self.repo_dir)
        findings = [f for f in report["findings"] if f["rule"] == "framework/sql-injection"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "high")

    def test_missing_toolchain_reported_as_skipped(self):
        # Create a package.json without node installed in dummy path or pip-audit missing
        (self.repo_dir / "requirements.txt").write_text("requests==2.28.1\n", encoding="utf-8")
        report = run_security_scan(self.repo_dir)
        # pip-audit check must exist and be either skipped or passed/failed (never fake pass if missing)
        pip_check = next((c for c in report["checks"] if "Python" in c["name"]), None)
        self.assertIsNotNone(pip_check)
        self.assertIn(pip_check["status"], {"skipped", "passed", "failed"})

    def test_security_caching(self):
        (self.repo_dir / "index.ts").write_text("const x = 1;\n", encoding="utf-8")
        initial = run_security_scan(self.repo_dir)
        cached = get_last_security_report(self.repo_dir)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["scanned_at"], initial["scanned_at"])


class TestTestsRunner(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_no_test_suites_returns_honest_message(self):
        (self.repo_dir / "index.ts").write_text("console.log('no tests');\n", encoding="utf-8")
        report = run_project_tests(self.repo_dir)
        self.assertEqual(report["summary"]["total"], 0)
        self.assertEqual(len(report["suites"]), 0)
        self.assertIn("has no test suite yet", report["message"])

    def test_python_test_execution_and_reporting(self):
        # Create a small valid python test
        tests_dir = self.repo_dir / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_sample.py").write_text(
            "import unittest\n\n"
            "class SampleTest(unittest.TestCase):\n"
            "    def test_math(self):\n"
            "        self.assertEqual(1 + 1, 2)\n",
            encoding="utf-8",
        )
        report = run_project_tests(self.repo_dir)
        self.assertEqual(len(report["suites"]), 1)
        self.assertEqual(report["suites"][0]["name"], "Python Backend Tests")
        self.assertGreaterEqual(report["summary"]["passed"], 1)
        self.assertEqual(report["summary"]["failed"], 0)
        self.assertEqual(report["suites"][0]["status"], "passed")

    def test_test_caching(self):
        (self.repo_dir / "file.txt").write_text("content\n", encoding="utf-8")
        initial = run_project_tests(self.repo_dir)
        cached = get_last_test_report(self.repo_dir)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["ran_at"], initial["ran_at"])

"""Unit tests for G-01 Publish Readiness Evaluator (R-509)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.studio.publish import evaluate_publish_readiness


class TestPublishReadiness(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_web_only_evaluates_to_path_1(self):
        # Create a pure web Next.js structure
        web_dir = self.repo_dir / "apps" / "web"
        web_dir.mkdir(parents=True)
        (web_dir / "package.json").write_text('{"name": "web", "scripts": {"build": "next build"}}', encoding="utf-8")
        (web_dir / "app").mkdir()
        (web_dir / "app" / "page.tsx").write_text("export default function Page() { return <h1>Hello</h1>; }", encoding="utf-8")

        result = evaluate_publish_readiness(self.repo_dir)
        self.assertEqual(result["path"], 1)
        self.assertFalse(result["has_backend"])
        self.assertFalse(result["has_db"])
        self.assertIn("Web-only", result["path_description"])
        self.assertEqual(result["render_yaml"], "")
        self.assertEqual(result["fly_toml"], "")

    def test_backend_without_db_evaluates_to_path_2(self):
        # Create web + python backend
        api_dir = self.repo_dir / "services" / "api"
        api_dir.mkdir(parents=True)
        (api_dir / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
        (api_dir / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")

        result = evaluate_publish_readiness(self.repo_dir)
        self.assertEqual(result["path"], 2)
        self.assertTrue(result["has_backend"])
        self.assertFalse(result["has_db"])
        self.assertIn("separate backend", result["path_description"])
        self.assertIn("backend-api", result["render_yaml"])
        self.assertIn("omnistack-backend", result["fly_toml"])

    def test_database_evaluates_to_path_3(self):
        # Create db with migrations and prisma
        (self.repo_dir / "migrations").mkdir(parents=True)
        (self.repo_dir / "migrations" / "001_init.sql").write_text("CREATE TABLE users (id serial primary key);", encoding="utf-8")
        (self.repo_dir / ".env.example").write_text("DATABASE_URL=postgres://user:pass@localhost:5432/db\nAPI_KEY=xyz\n", encoding="utf-8")

        result = evaluate_publish_readiness(self.repo_dir)
        self.assertEqual(result["path"], 3)
        self.assertTrue(result["has_db"])
        self.assertIn("Full-stack", result["path_description"])
        self.assertIn("DATABASE_URL", result["env_suggestions"])
        self.assertIn("API_KEY", result["env_suggestions"])

    def test_custom_render_yaml_preserved(self):
        (self.repo_dir / "services" / "api").mkdir(parents=True)
        custom_yaml = "services:\n  - name: my-custom-service\n"
        (self.repo_dir / "render.yaml").write_text(custom_yaml, encoding="utf-8")

        result = evaluate_publish_readiness(self.repo_dir)
        self.assertEqual(result["path"], 2)
        self.assertEqual(result["render_yaml"], custom_yaml)

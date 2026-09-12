"""Tests for the local run plan builder (localrun/plan.py, R-419).

Deterministic and offline: a real generated repo is materialized into a temp dir (git CLI,
like the git_service tests), then build_run_plan composes the plan as pure data. No docker,
pnpm, pip, servers, or network are invoked.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.intake import build_app_from_ir
from omnistackai_agent_engine.localrun import RunPlan, build_run_plan

AUTHOR = {"author_name": "sanjeetji", "author_email": "sk698166@gmail.com"}
DB = {
    "db_container": "test-pg",
    "db_user": "tester",
    "db_password": "secretpw",
    "db_host": "127.0.0.1",
    "db_port": 5432,
}


def _generate_repo(tmp: str, example: str = "minimal-blog") -> str:
    target = str(Path(tmp) / "app")
    build_app_from_ir(example_ir(example), target, **AUTHOR)
    return target


class TestBuildRunPlan(unittest.TestCase):
    def test_detects_python_backend_and_web(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_run_plan(_generate_repo(tmp), **DB)
            self.assertIsInstance(plan, RunPlan)
            self.assertEqual(plan.backend_kind, "python")
            self.assertTrue(plan.has_web)

    def test_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_run_plan(_generate_repo(tmp), api_port=8000, web_port=3000, **DB)
            self.assertEqual(plan.api_url, "http://127.0.0.1:8000")
            self.assertEqual(plan.web_url, "http://127.0.0.1:3000")

    def test_db_recreated_then_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_run_plan(_generate_repo(tmp), **DB)
            labels = [s.label for s in plan.steps]
            self.assertTrue(any(l.startswith("drop database") for l in labels))
            self.assertTrue(any(l.startswith("create database") for l in labels))
            migrations = [s for s in plan.steps if s.label.startswith("apply migration")]
            self.assertGreaterEqual(len(migrations), 1)
            # migrations carry the .sql file on stdin, in sorted order
            names = [Path(s.stdin_file).name for s in migrations]
            self.assertEqual(names, sorted(names))
            self.assertTrue(names[0].startswith("0001"))

    def test_backend_serve_step_has_database_url_and_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_run_plan(_generate_repo(tmp), **DB)
            serve = next(s for s in plan.steps if s.background and "uvicorn" in s.program)
            env = dict(serve.env)
            self.assertIn("DATABASE_URL", env)
            self.assertIn("secretpw", env["DATABASE_URL"])
            self.assertIn("/app", env["DATABASE_URL"])  # db name == repo slug "app"
            self.assertEqual(env["JWT_SECRET"], "local-dev-secret")

    def test_web_uses_next_binary_not_pnpm_dev(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_run_plan(_generate_repo(tmp), **DB)
            web_serve = next(s for s in plan.steps if s.background and "next" in s.program)
            self.assertIn("dev", web_serve.args)
            self.assertEqual(web_serve.program, "./node_modules/.bin/next")
            self.assertEqual(dict(web_serve.env)["NEXT_PUBLIC_API_URL"], "http://127.0.0.1:8000")
            # never shells `pnpm dev`
            self.assertFalse(
                any(s.program == "pnpm" and "dev" in s.args for s in plan.steps)
            )
            # pnpm install skips native build scripts (avoids ERR_PNPM_IGNORED_BUILDS exit 1)
            web_install = next(s for s in plan.steps if s.program == "pnpm")
            self.assertIn("--ignore-scripts", web_install.args)

    def test_step_order_db_then_backend_then_web(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_run_plan(_generate_repo(tmp), **DB)
            kinds = []
            for s in plan.steps:
                if s.program == "docker":
                    kinds.append("db")
                elif "uvicorn" in s.program or s.program in ("python3", ".venv/bin/pip"):
                    kinds.append("backend")
                elif "next" in s.program or s.program == "pnpm":
                    kinds.append("web")
            self.assertEqual(kinds, sorted(kinds, key=lambda k: {"db": 0, "backend": 1, "web": 2}[k]))

    def test_to_dict_is_json_safe_and_masks_password(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_run_plan(_generate_repo(tmp), **DB)
            payload = plan.to_dict()
            text = json.dumps(payload)  # must serialize
            self.assertNotIn("secretpw", text)
            self.assertIn("***", text)

    def test_default_db_name_is_repo_slug(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_run_plan(_generate_repo(tmp), **DB)
            self.assertEqual(plan.db_name, "app")

    def test_explicit_db_name_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_run_plan(_generate_repo(tmp), db_name="my_blog", **DB)
            self.assertEqual(plan.db_name, "my_blog")

    def test_no_backend_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # An empty repo dir: no services/api, no apps/web.
            empty = str(Path(tmp) / "empty")
            Path(empty).mkdir()
            plan = build_run_plan(empty, **DB)
            self.assertEqual(plan.backend_kind, "none")
            self.assertFalse(plan.has_web)
            # still creates the database
            self.assertTrue(any(s.label.startswith("create database") for s in plan.steps))

    def test_package_exports(self) -> None:
        import omnistackai_agent_engine.localrun as localrun

        for name in ("RunPlan", "RunStep", "build_run_plan"):
            self.assertTrue(hasattr(localrun, name))
            self.assertIn(name, localrun.__all__)

    def test_migration_steps_pipe_the_file_on_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_run_plan(_generate_repo(tmp), **DB)
            migration = next(s for s in plan.steps if s.label.startswith("apply migration"))
            self.assertIsNotNone(migration.stdin_file)
            self.assertTrue(Path(migration.stdin_file).is_file())


if __name__ == "__main__":
    unittest.main()

"""PC-110: a preview runs a generated Node (Express / Hono) API, as it runs Python and Go.

Found in R-570: the runner recognised only `requirements.txt` and `go.mod`, so a Node API was never
started and its app's pages had nothing to call.
"""

import tempfile
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.localrun.plan import build_run_plan
from omnistackai_agent_engine.localrun.run import _should_skip


def _node_repo(schema: str = "CREATE TABLE t (id int);") -> Path:
    root = Path(tempfile.mkdtemp()) / "shop"
    api = root / "services" / "api"
    (api / "src").mkdir(parents=True)
    (api / "package.json").write_text('{"name": "api"}')
    (api / "src" / "index.ts").write_text("// app")
    (api / "schema.sql").write_text(schema)
    (api / "seed.sql").write_text("")
    return root


class ANodeApiIsPreviewed(TestCase):
    def setUp(self) -> None:
        self.root = _node_repo()
        self.plan = build_run_plan(str(self.root), api_port=8123)
        self.labels = [s.label for s in self.plan.steps]

    def test_it_is_recognised(self) -> None:
        self.assertEqual(self.plan.backend_kind, "node")

    def test_its_schema_is_applied_as_the_apps_role_and_an_empty_seed_is_skipped(self) -> None:
        schema = next(s for s in self.plan.steps if s.label == "apply schema.sql")
        self.assertIn("-U", schema.args)
        self.assertEqual(schema.stdin_file, str(self.root / "services/api/schema.sql"))
        self.assertNotIn("apply seed.sql", self.labels)
        self.assertLess(self.labels.index("apply schema.sql"), self.labels.index("start backend API (node) on http://127.0.0.1:8123"))

    def test_it_starts_with_the_same_contract_as_python_and_go(self) -> None:
        start = next(s for s in self.plan.steps if s.label.startswith("start backend API (node)"))
        env = dict(start.env)
        self.assertEqual(start.program, "./node_modules/.bin/tsx")
        self.assertEqual(env["PORT"], "8123")
        self.assertTrue(env["DATABASE_URL"].startswith("postgresql://"))
        self.assertTrue(env["JWT_SECRET"])
        self.assertTrue(start.background)

    def test_dependencies_install_once(self) -> None:
        install = next(s for s in self.plan.steps if s.label == "install backend dependencies (pnpm)")
        self.assertIn("--ignore-scripts", install.args)
        self.assertFalse(_should_skip(install))
        tsx = self.root / "services/api/node_modules/.bin/tsx"
        tsx.parent.mkdir(parents=True)
        tsx.write_text("")
        self.assertTrue(_should_skip(install))

    def test_a_package_json_alone_is_not_an_api(self) -> None:
        root = _node_repo()
        (root / "services/api/src/index.ts").unlink()
        self.assertEqual(build_run_plan(str(root)).backend_kind, "none")

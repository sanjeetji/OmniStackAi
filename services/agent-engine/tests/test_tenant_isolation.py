"""PC-009: one user's project cannot reach another's, or the platform's.

Offline checks of what each isolation layer promises. The live proof — run against this machine's
PostgreSQL and Docker — is recorded in the CHANGELOG entry for PC-009:

* app A opening app B's database, or the platform's: "User does not have CONNECT privilege";
* app A creating a database: "permission denied"; app A is not a superuser.
"""

import os
import tempfile
from pathlib import Path
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.intake.build_app import build_app_from_ir
from omnistackai_agent_engine.localrun.plan import build_run_plan

DB = {"db_password": "platform-owner-secret", "db_user": "omnistackai", "maintenance_db": "omnistackai"}


def _workspace(tmp: str, workspace_id: str) -> str:
    repo = Path(tmp) / workspace_id / "repo"
    with mock.patch.dict(os.environ, {"OMNISTACKAI_BUILD_VERIFY": "off"}):
        build_app_from_ir(example_ir("minimal-blog"), str(repo), author_name="t", author_email="t@example.com",
                          overwrite=True)
    return str(repo)


class EachProjectHasItsOwnDatabase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.plans = [build_run_plan(_workspace(cls.tmp.name, ws), **DB)
                     for ws in ("7f1c2a90-aaaa", "e2b4c6d8-bbbb")]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def _database_url(self, plan) -> str:
        api = next(s for s in plan.steps if s.background and "uvicorn" in s.program)
        return dict(api.env)["DATABASE_URL"]

    def test_two_workspaces_never_share_a_database(self) -> None:
        # Every workspace keeps its code in a folder named `repo`; both previewed into "repo" before.
        names = {plan.db_name for plan in self.plans}
        self.assertEqual(len(names), 2)
        self.assertNotIn("repo", names)
        self.assertEqual(self.plans[0].db_name, "app_7f1c2a90_aaaa", "a leading digit gets a prefix")

    def test_the_app_never_holds_the_platform_credentials(self) -> None:
        for plan in self.plans:
            url = self._database_url(plan)
            with self.subTest(db=plan.db_name):
                self.assertNotIn("platform-owner-secret", url)
                self.assertTrue(url.startswith(f"postgresql://{plan.db_name}:"))

    def test_each_role_is_unprivileged_and_owns_only_its_database(self) -> None:
        sql = " ".join(" ".join(s.args) for s in self.plans[0].steps if s.program == "docker")
        role = self.plans[0].db_name
        self.assertIn(f'CREATE ROLE "{role}" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION', sql)
        self.assertIn(f'CREATE DATABASE "{role}" OWNER "{role}"', sql)
        self.assertIn(f'REVOKE CONNECT ON DATABASE "{role}" FROM PUBLIC', sql)
        self.assertIn('REVOKE CONNECT ON DATABASE "omnistackai" FROM PUBLIC', sql)

    def test_migrations_run_as_the_app_so_it_owns_its_tables(self) -> None:
        for step in self.plans[0].steps:
            if step.label.startswith("apply migration"):
                self.assertEqual(step.args[step.args.index("-U") + 1], self.plans[0].db_name)

    def test_passwords_differ_per_project_and_are_stable(self) -> None:
        a, b = (self._database_url(p) for p in self.plans)
        self.assertNotEqual(a.split("@")[0], b.split("@")[0])
        again = build_run_plan(self.plans[0].repo_dir, **DB)
        self.assertEqual(self._database_url(again), a)


class OnlyTheControlPlaneMayCallTheStudio(TestCase):
    """The Studio acts on whatever workspace it is asked about; ownership is checked in the control
    plane. With a service token set, a caller without it gets nothing."""

    def _serve(self, token: str):
        import threading

        from omnistackai_agent_engine.studio.server import create_studio_server

        with mock.patch.dict(os.environ, {"OMNISTACKAI_STUDIO_TOKEN": token}):
            server = create_studio_server(build_fn=lambda prompt, **opts: {"ok": True}, host="127.0.0.1", port=0,
                                          status_fn=lambda: {"status": "idle"})
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def _get(self, url: str, token: str | None = None) -> int:
        import urllib.error
        import urllib.request

        request = urllib.request.Request(url, headers={"X-OmniStack-Studio-Token": token} if token else {})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code

    def test_without_the_token_nothing_is_served(self) -> None:
        base = self._serve("the-service-token")
        self.assertEqual(self._get(base + "/api/preview"), 401)
        self.assertEqual(self._get(base + "/api/preview", "wrong"), 401)
        self.assertEqual(self._get(base + "/api/preview", "the-service-token"), 200)

    def test_the_health_check_stays_open(self) -> None:
        self.assertEqual(self._get(self._serve("the-service-token") + "/healthz"), 200)

    def test_single_operator_mode_is_unchanged(self) -> None:
        self.assertEqual(self._get(self._serve("") + "/api/preview"), 200)

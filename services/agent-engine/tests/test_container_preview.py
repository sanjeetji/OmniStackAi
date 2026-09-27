"""PC-007: a generated app previews with nothing but Docker on the machine.

Offline: Docker is never called here. The live proof — a preview started with node, pnpm and
python3 removed from PATH — is recorded in the CHANGELOG entry for PC-007.
"""

import tempfile
from pathlib import Path
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.intake.build_app import build_app_from_ir
from omnistackai_agent_engine.localrun import container_engine, engines
from omnistackai_agent_engine.localrun.plan import build_run_plan


class TheEngineSwitch(TestCase):
    def test_auto_keeps_local_where_the_toolchain_exists(self) -> None:
        with mock.patch.object(engines, "missing_toolchain", return_value=()), \
                mock.patch.object(engines, "docker_available", return_value=True):
            self.assertEqual(engines.resolve_engine("auto"), engines.LOCAL)

    def test_auto_uses_the_container_when_the_toolchain_is_missing(self) -> None:
        with mock.patch.object(engines, "missing_toolchain", return_value=("node", "pnpm")), \
                mock.patch.object(engines, "docker_available", return_value=True):
            self.assertEqual(engines.resolve_engine("auto"), engines.CONTAINER)

    def test_nothing_available_stays_local_and_fails_as_before(self) -> None:
        with mock.patch.object(engines, "missing_toolchain", return_value=("node",)), \
                mock.patch.object(engines, "docker_available", return_value=False):
            self.assertEqual(engines.resolve_engine("auto"), engines.LOCAL)

    def test_an_explicit_choice_wins(self) -> None:
        with mock.patch.dict("os.environ", {engines.ENGINE_ENV: "container"}):
            self.assertEqual(engines.resolve_engine(), engines.CONTAINER)

    def test_the_paid_browser_engine_is_a_key_not_a_default(self) -> None:
        with mock.patch.object(engines, "missing_toolchain", return_value=()), \
                mock.patch.object(engines, "docker_available", return_value=True), \
                mock.patch.dict("os.environ", {}, clear=True):
            status = engines.engine_status()
        webcontainer = next(e for e in status["engines"] if e["id"] == "webcontainer")
        self.assertFalse(webcontainer["available"])
        self.assertIn("licence", webcontainer["needs"])


class TheContainerRunsTheSamePlan(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.repo = f"{cls.tmp.name}/repo"
        with mock.patch.dict("os.environ", {"OMNISTACKAI_BUILD_VERIFY": "off"}):
            build_app_from_ir(example_ir("minimal-blog"), cls.repo, author_name="t",
                              author_email="t@example.com", overwrite=True)
        cls.plan = build_run_plan(cls.repo, db_password="pw", api_port=41000, web_port=41001,
                                  admin_port=41002, public_base="/preview/x")
        cls.script = container_engine.container_script(cls.plan, db_from="@127.0.0.1:5432/",
                                                       db_to="@omnistackai-local-postgres-1:5432/")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_database_steps_stay_on_the_host(self) -> None:
        self.assertNotIn("psql", self.script)
        self.assertNotIn("docker exec", self.script)

    def test_the_app_reaches_postgres_by_name(self) -> None:
        self.assertIn("@omnistackai-local-postgres-1:5432/", self.script)
        self.assertNotIn("@127.0.0.1:5432/", self.script)

    def test_the_api_listens_where_the_published_port_can_reach_it(self) -> None:
        uvicorn = next(line for line in self.script.splitlines() if "/omni-venv/bin/uvicorn app.main" in line)
        self.assertIn("0.0.0.0", uvicorn)
        self.assertIn("41000", uvicorn)

    def test_every_web_surface_starts_on_its_planned_port(self) -> None:
        for port in ("41001", "41002"):
            self.assertIn(f"-p {port}", self.script)

    def test_a_warm_environment_is_not_reinstalled(self) -> None:
        self.assertIn("[ -x /omni-venv/bin/uvicorn ] ||", self.script)
        self.assertIn("/omni-venv/bin/uvicorn app.main:app", self.script)

    def test_one_server_exiting_ends_the_container(self) -> None:
        self.assertTrue(self.script.rstrip().endswith('wait -n "${pids[@]}"\nexit 1'))

    def test_dependencies_live_in_volumes_not_on_the_host(self) -> None:
        mounts = container_engine._mounts(self.plan, "/tmp/run")
        joined = " ".join(mounts)
        self.assertIn(f"{Path(self.repo).resolve()}/apps/web/node_modules", joined.replace(self.repo, str(Path(self.repo).resolve())))
        self.assertIn("omnistackai-preview-pnpm-store:/pnpm-store", joined)
        self.assertIn(":/omni-venv", joined)
        self.assertNotIn(".venv", joined, "the project's own .venv on the host is left alone")

    def test_the_same_dependency_set_shares_a_volume(self) -> None:
        web = Path(self.repo) / "apps" / "web" / "package.json"
        self.assertEqual(container_engine._volume("node-modules", web),
                         container_engine._volume("node-modules", web))

    def test_projects_with_the_same_dependencies_share_a_volume(self) -> None:
        import json
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.json", Path(tmp) / "b.json"
            a.parent.mkdir(exist_ok=True)
            deps = {"dependencies": {"next": "15.5.4"}, "devDependencies": {"typescript": "5"}}
            (Path(tmp) / "a").mkdir(); (Path(tmp) / "b").mkdir()
            a, b = Path(tmp) / "a" / "package.json", Path(tmp) / "b" / "package.json"
            a.write_text(json.dumps({"name": "habit-tracker", **deps}))
            b.write_text(json.dumps({"name": "candle-store", **deps}))
            self.assertEqual(container_engine._volume("node-modules", a), container_engine._volume("node-modules", b))

    def test_a_host_link_is_removed_before_mounting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "node_modules"
            link.symlink_to(tmp)
            container_engine._drop_host_link(link)
            self.assertFalse(link.exists() or link.is_symlink())
            self.assertTrue(Path(tmp).is_dir(), "the cache it pointed at stays")


class AUniqueColumnIsNotIndexedTwice(TestCase):
    """Found live while proving PC-007: a habit tracker's User entity had `email` both UNIQUE and in
    a unique index. The index's default name is the one PostgreSQL gives the column's constraint,
    so the migration failed ("relation user_email_key already exists") and the app never started
    — on either engine."""

    def _schema(self, *, column_unique: bool, index_fields: tuple[str, ...]) -> str:
        import dataclasses

        from omnistackai_agent_engine.application_ir.ir import Entity, Field, FieldType, Index
        from omnistackai_agent_engine.codegen.schema_sql import render_postgres_schema

        ir = example_ir("minimal-blog")
        user = Entity(name="Member", fields=(
            Field(name="id", type=FieldType.UUID), Field(name="email", type=FieldType.STRING, unique=column_unique),
            Field(name="team", type=FieldType.STRING)), indexes=(Index(fields=index_fields, unique=True),))
        return render_postgres_schema(dataclasses.replace(ir, entities=ir.entities + (user,)))

    def test_the_redundant_index_is_skipped(self) -> None:
        sql = self._schema(column_unique=True, index_fields=("email",))
        self.assertNotIn('INDEX "member_email_key"', sql)
        self.assertIn('"email" TEXT NOT NULL UNIQUE', sql)

    def test_a_needed_unique_index_stays(self) -> None:
        self.assertIn('UNIQUE INDEX "member_email_key"', self._schema(column_unique=False, index_fields=("email",)))
        self.assertIn('UNIQUE INDEX "member_email_team_key"', self._schema(column_unique=True, index_fields=("email", "team")))

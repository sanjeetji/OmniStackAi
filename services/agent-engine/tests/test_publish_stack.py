"""PC-008: one-click publish of the whole app — database, API, web app, admin console.

Offline: Docker and HTTP are fakes here. The live proof (the local stand-in: every surface 200, a
real sign-up, sign-in and read-back through the live URL, rollback, then again through the
console) is recorded in the CHANGELOG entry for PC-008.
"""

import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.intake.build_app import build_app_from_ir
from omnistackai_agent_engine.publish import bundle
from omnistackai_agent_engine.publish.stack import StackPublisher, Target, target_from_env


def _repo(tmp: str) -> Path:
    target = f"{tmp}/repo"
    with mock.patch.dict(os.environ, {"OMNISTACKAI_BUILD_VERIFY": "off"}):
        build_app_from_ir(example_ir("minimal-blog"), target, author_name="t", author_email="t@example.com",
                          overwrite=True)
    return Path(target)


class TheBundleRunsTheWholeAppAnywhere(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.repo = _repo(cls.tmp.name)
        cls.layout = bundle.read_layout(cls.repo, "Minimal Blog")
        cls.written = bundle.write_bundle(cls.repo, cls.layout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_every_part_is_found(self) -> None:
        self.assertEqual(self.layout.api_kind, "python")
        self.assertEqual(self.layout.web_apps[0], "web")
        self.assertTrue(self.layout.has_admin)

    def test_the_files_land_in_the_project(self) -> None:
        for rel in ("deploy/compose.yaml", "deploy/Caddyfile", "deploy/proxy.Dockerfile", "deploy/README.md",
                    "apps/web/Dockerfile", "apps/admin/Dockerfile", "services/api/Dockerfile", ".dockerignore"):
            with self.subTest(rel=rel):
                self.assertTrue((self.repo / rel).is_file())

    def test_writing_again_changes_nothing(self) -> None:
        self.assertEqual(bundle.write_bundle(self.repo, self.layout), [])

    def test_one_address_for_everything(self) -> None:
        caddy = (self.repo / "deploy" / "Caddyfile").read_text()
        self.assertIn("handle_path /api/*", caddy, "the /api prefix is removed, as the preview proxy does")
        self.assertIn("@admin path /admin /admin/*", caddy)
        self.assertNotIn("redir", caddy, "Next redirects /admin/ to /admin; redirecting back would loop")

    def test_the_admin_console_is_built_under_its_path(self) -> None:
        compose = (self.repo / "deploy" / "compose.yaml").read_text()
        self.assertIn('BASE_PATH: "/admin"', compose)
        self.assertIn("NEXT_PUBLIC_API_URL: /api", compose)

    def test_web_apps_build_from_the_project_root(self) -> None:
        # They import brand.json and brand/ from the root; built from apps/web the build failed live.
        compose = (self.repo / "deploy" / "compose.yaml").read_text()
        self.assertIn("dockerfile: apps/web/Dockerfile", compose)
        self.assertIn("COPY . /repo", (self.repo / "apps" / "web" / "Dockerfile").read_text())

    def test_no_secret_is_written_into_the_project(self) -> None:
        compose = (self.repo / "deploy" / "compose.yaml").read_text()
        self.assertIn("${DB_PASSWORD:?set DB_PASSWORD}", compose)
        self.assertIn("${JWT_SECRET:?set JWT_SECRET}", compose)
        self.assertNotIn("local-dev-secret", compose)

    def test_the_stack_does_not_mount_host_paths(self) -> None:
        # So the same file runs on a remote Docker host (a mount would name a path on that host).
        compose = (self.repo / "deploy" / "compose.yaml").read_text()
        self.assertNotIn("./Caddyfile:", compose)

    def test_a_mobile_app_is_not_a_web_surface(self) -> None:
        # Seen live: an Expo app with app.config.js (no app.json) was built as a Next app and failed.
        mobile = self.repo / "apps" / "customer-app"
        mobile.mkdir(exist_ok=True)
        (mobile / "package.json").write_text(json.dumps({"dependencies": {"expo": "~51.0.0"}}))
        (mobile / "Dockerfile").write_text(bundle.NEXT_DOCKERFILE)
        layout = bundle.read_layout(self.repo, "Minimal Blog")
        self.assertNotIn("customer-app", layout.web_apps)
        self.assertIn("apps/customer-app/Dockerfile", bundle.write_bundle(self.repo, layout))
        self.assertFalse((mobile / "Dockerfile").exists())

    def test_migrations_are_found_for_each_backend(self) -> None:
        self.assertEqual([p.name for p in bundle.migrations(self.repo)][:1], ["0001_init.sql"])


class _FakeDocker:
    """Records docker calls and answers them as a healthy local daemon would."""

    def __init__(self, *, fail_on: str | None = None, seeded_admin: bool = False) -> None:
        self.seeded_admin = seeded_admin
        self.calls: list[list[str]] = []
        self.stdins: list[str | None] = []
        self.fail_on = fail_on

    def __call__(self, argv, input=None, **kwargs):
        self.calls.append(argv)
        self.stdins.append(input)
        joined = " ".join(argv)
        if self.fail_on and self.fail_on in joined:
            return subprocess.CompletedProcess(argv, 1, "", "ERROR: failed to solve: boom")
        out = ""
        if "to_regclass('public.users')" in joined:
            out = "t\n" if self.seeded_admin else "f\n"
        return subprocess.CompletedProcess(argv, 0, out, "")


class ThePublisher(TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = _repo(self.tmp.name)
        self.state = Path(self.tmp.name) / "published"

    def _publisher(self, docker, http_status=200):
        publisher = StackPublisher(self.state, target=Target(), runner=docker, http_get=lambda url: http_status)
        return publisher

    def _publish(self, publisher):
        with mock.patch("omnistackai_agent_engine.publish.stack._post_json",
                        side_effect=[(201, {"access_token": "t"}), (200, {"access_token": "t"})]), \
                mock.patch("omnistackai_agent_engine.publish.stack._http_status", return_value=200):
            return publisher.publish("ws1", str(self.repo), name="Minimal Blog")

    def test_a_publish_goes_live_in_order(self) -> None:
        docker = _FakeDocker()
        result = self._publish(self._publisher(docker))
        self.assertEqual(result["status"], "live")
        self.assertEqual(result["release"], 1)
        self.assertTrue(result["url"].startswith("http://127.0.0.1:"))
        order = [" ".join(c) for c in docker.calls]
        build = next(i for i, c in enumerate(order) if c.endswith(" build"))
        db = next(i for i, c in enumerate(order) if "up -d --wait db" in c)
        up = next(i for i, c in enumerate(order) if "up -d --remove-orphans" in c)
        self.assertLess(build, db)
        self.assertLess(db, up)

    def test_each_migration_runs_once_in_one_transaction(self) -> None:
        docker = _FakeDocker()
        self._publish(self._publisher(docker))
        applied = [s for s in docker.stdins if s and "INSERT INTO _omnistack_migrations" in s
                   and not s.startswith("INSERT INTO _omnistack_migrations")]
        self.assertEqual(len(applied), len(bundle.migrations(self.repo)))
        # PC-049: the schema's version is remembered too, so a changed schema is noticed next time.
        self.assertEqual(len([s for s in docker.stdins if s and s.startswith("INSERT INTO _omnistack_migrations (name) VALUES ('0001_init.sql@")]), 1)
        migration_calls = [c for c, s in zip(docker.calls, docker.stdins)
                           if s and "INSERT INTO _omnistack_migrations" in s
                           and not s.startswith("INSERT INTO _omnistack_migrations")]
        self.assertTrue(migration_calls and all("-1" in c for c in migration_calls))

    def test_secrets_stay_private_and_stable(self) -> None:
        publisher = self._publisher(_FakeDocker())
        self._publish(publisher)
        secrets_file = self.state / "ws1" / "secrets.env"
        first = secrets_file.read_text()
        self.assertEqual(stat.S_IMODE(secrets_file.stat().st_mode), 0o600)
        self._publish(publisher)
        self.assertEqual(secrets_file.read_text(), first, "the database password must survive a republish")
        status = json.dumps(publisher.status("ws1"))
        for line in first.splitlines():
            self.assertNotIn(line.split("=", 1)[1], status)

    def test_a_failed_build_says_where_and_why(self) -> None:
        result = self._publish(self._publisher(_FakeDocker(fail_on=" build")))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["step"], "build")
        self.assertIn("boom", result["error"]["reason"])

    def test_a_failed_check_keeps_the_previous_release_live(self) -> None:
        docker = _FakeDocker()
        publisher = self._publisher(docker)
        self._publish(publisher)
        publisher._http_get = lambda url: 502
        with mock.patch("omnistackai_agent_engine.publish.stack.time.sleep"), \
                mock.patch("omnistackai_agent_engine.publish.stack.time.time", side_effect=[0.0] + [1000.0] * 50):
            result = publisher.publish("ws1", str(self.repo), name="Minimal Blog")
        self.assertEqual(result["status"], "live")
        self.assertIn("Release 1 is still live", result["message"])
        self.assertIn("--no-build", " ".join(docker.calls[-1]))

    def test_rollback_and_unpublish(self) -> None:
        docker = _FakeDocker()
        publisher = self._publisher(docker)
        self._publish(publisher)
        self.assertIn("no earlier release", publisher.rollback("ws1", str(self.repo))["message"])
        self._publish(publisher)
        rolled = publisher.rollback("ws1", str(self.repo))
        self.assertEqual(rolled["release"], 1)
        down = publisher.unpublish("ws1", str(self.repo))
        self.assertEqual(down["status"], "unpublished")
        self.assertNotIn("-v", docker.calls[-1], "the database is kept unless asked")

    def test_deleting_the_data_leaves_nothing_behind(self) -> None:
        # PC-012: a deleted account's app keeps no release history and no secrets on disk.
        docker = _FakeDocker()
        publisher = self._publisher(docker)
        self._publish(publisher)
        self.assertTrue(publisher._dir("ws1").is_dir())
        down = publisher.unpublish("ws1", str(self.repo), delete_data=True)
        down_call = next(c for c in docker.calls if "down" in c)
        self.assertIn("-v", down_call)
        # PC-049: and its images are looked up to be removed.
        self.assertIn(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"], docker.calls)
        self.assertFalse(publisher._dir("ws1").exists())
        self.assertEqual((down["status"], down["admin"]), ("unpublished", None))

    def test_a_domain_goes_through_the_shared_https_proxy(self) -> None:
        docker = _FakeDocker()
        publisher = StackPublisher(self.state, target=Target(domain="apps.example.com"), runner=docker,
                                   http_get=lambda url: 200)
        with mock.patch("omnistackai_agent_engine.publish.stack._post_json",
                        side_effect=[(201, {}), (200, {"access_token": "t"})]), \
                mock.patch("omnistackai_agent_engine.publish.stack._http_status", return_value=200):
            result = publisher.publish("ws1", str(self.repo), name="Minimal Blog")
        self.assertTrue(result["url"].startswith("https://minimal-blog-ws1.apps.example.com"))
        edge_config = next(s for s in docker.stdins if s and "reverse_proxy omni-ws1-proxy-1:80" in s)
        self.assertIn("minimal-blog-ws1.apps.example.com {", edge_config)

    def test_where_it_publishes_comes_from_settings(self) -> None:
        with mock.patch.dict(os.environ, {"OMNISTACKAI_PUBLISH_DOCKER_HOST": "ssh://deploy@server",
                                          "OMNISTACKAI_PUBLISH_DOMAIN": "apps.example.com"}):
            target = target_from_env()
        self.assertEqual((target.docker_host, target.domain), ("ssh://deploy@server", "apps.example.com"))
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(target_from_env(), Target())


class AChildRowDeleteCompiles(TestCase):
    """Found publishing a clinic app: a Service list could not delete Services but could delete their
    Bookings, and `next build` failed — `confirmAsync` was used but only declared when the parent
    itself was deletable."""

    def test_the_confirm_hook_is_declared_wherever_it_is_used(self) -> None:
        import dataclasses

        from omnistackai_agent_engine.application_ir.ir import ApiEndpoint
        from omnistackai_agent_engine.codegen.assembler import assemble_project

        ir = example_ir("minimal-blog")
        ir = dataclasses.replace(ir, apis=ir.apis + (ApiEndpoint(method="DELETE", path="/comments/{commentId}", auth=True),))
        checked = 0
        for f in assemble_project(ir).files():
            if f.path.endswith(".tsx") and "confirm-dialog" not in f.path and "confirmAsync(" in f.content:
                lines = f.content.splitlines()
                declared = [i for i, line in enumerate(lines) if "useConfirm()" in line]
                used = [i for i, line in enumerate(lines) if "confirmAsync(" in line]
                with self.subTest(path=f.path):
                    self.assertTrue(declared and declared[0] < used[0])
                checked += 1
        self.assertGreaterEqual(checked, 2)


class TheFirstRecordSaves(TestCase):
    """Found as a visitor on a published notes app: saving the first note failed with
    `null value in column "created_at"` — repositories leave the timestamps to the database, and a
    model-declared timestamp column had no default."""

    def test_model_declared_timestamps_default_to_now(self) -> None:
        import dataclasses

        from omnistackai_agent_engine.application_ir.ir import Entity, Field, FieldType
        from omnistackai_agent_engine.codegen.schema_sql import render_postgres_schema

        ir = example_ir("minimal-blog")
        note = Entity(name="Note", fields=(
            Field(name="id", type=FieldType.UUID), Field(name="title", type=FieldType.STRING),
            Field(name="created_at", type=FieldType.DATETIME), Field(name="updated_at", type=FieldType.DATETIME),
            Field(name="due_at", type=FieldType.DATETIME)))
        sql = render_postgres_schema(dataclasses.replace(ir, entities=ir.entities + (note,)))
        table = sql.split('CREATE TABLE IF NOT EXISTS "note"')[1].split(");")[0]
        self.assertIn('"created_at" TIMESTAMPTZ NOT NULL DEFAULT now()', table)
        self.assertIn('"updated_at" TIMESTAMPTZ NOT NULL DEFAULT now()', table)
        self.assertNotIn('"due_at" TIMESTAMPTZ NOT NULL DEFAULT', table, "only the managed timestamps")


class APlanCannotShadowTheSignInPage(TestCase):
    """Found publishing a notes app: the plan declared POST /login and POST /signup. The web app got a
    proxy route at app/login/route.ts beside the sign-in page and `next build` refused both."""

    def _plan(self):
        from test_intake_repair import _plan

        data = _plan()
        data["apis"] += [{"method": "POST", "path": "/login", "auth": False},
                         {"method": "POST", "path": "/signup", "auth": False}]
        return data

    def test_intake_removes_duplicates_of_the_account_endpoints(self) -> None:
        from omnistackai_agent_engine.intake.nl_to_ir import parse_ir_response_with_repairs

        ir, repairs = parse_ir_response_with_repairs(json.dumps(self._plan()))
        self.assertNotIn("/login", [a.path for a in ir.apis])
        self.assertIn("POST /login: removed; sign-up and sign-in are built in under /auth", repairs)

    def test_a_page_and_a_route_never_share_a_path(self) -> None:
        import dataclasses

        from omnistackai_agent_engine.application_ir.ir import ApiEndpoint
        from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter

        ir = example_ir("minimal-blog")
        ir = dataclasses.replace(ir, apis=ir.apis + (ApiEndpoint(method="POST", path="/login", auth=False),
                                                     ApiEndpoint(method="GET", path="/me", auth=True)))
        paths = {f.path for f in NextjsWebAdapter().generate(ir).files()}
        pages = {p[: -len("/page.tsx")] for p in paths if p.endswith("/page.tsx")}
        routes = {p[: -len("/route.ts")] for p in paths if p.endswith("/route.ts")}
        self.assertIn("app/login", pages)
        self.assertEqual(pages & routes, set())


class NoPublishedAppAcceptsTheDevelopmentPassword(TestCase):
    """Found on the first live publish: every published app accepted admin@example.local / changeme
    (seeded by the schema for local development) and its sign-in page offered to fill it in."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = _repo(self.tmp.name)
        self.docker = _FakeDocker(seeded_admin=True)
        self.publisher = StackPublisher(Path(self.tmp.name) / "published", target=Target(), runner=self.docker,
                                        http_get=lambda url: 200)
        with mock.patch("omnistackai_agent_engine.publish.stack._post_json",
                        side_effect=[(201, {}), (200, {"access_token": "t"})]), \
                mock.patch("omnistackai_agent_engine.publish.stack._http_status", return_value=200):
            self.status = self.publisher.publish("ws1", str(self.repo), name="Minimal Blog")

    def test_the_seeded_password_is_replaced(self) -> None:
        from omnistackai_agent_engine.codegen.schema_sql import _ADMIN_SEED_HASH

        update = next(s for s in self.docker.stdins if s and s.startswith("UPDATE users SET password_hash"))
        self.assertIn(f"AND password_hash = '{_ADMIN_SEED_HASH}'", update, "only the untouched seed")
        self.assertNotIn(f"SET password_hash = '{_ADMIN_SEED_HASH}'", update)

    def test_the_owner_sees_the_new_password_and_the_log_never_does(self) -> None:
        admin = self.status["admin"]
        self.assertEqual(admin["email"], "admin@example.local")
        self.assertNotEqual(admin["password"], "changeme")
        self.assertNotIn(admin["password"], "\n".join(self.status["log"]))
        self.assertEqual(self.publisher.status("ws1")["admin"]["password"], admin["password"], "stable")

    def test_the_demo_button_is_not_in_production_builds(self) -> None:
        page = (self.repo / "apps" / "web" / "app" / "login" / "page.tsx").read_text()
        button = page.index('id="login-demo-fill"')
        self.assertIn('{process.env.NODE_ENV !== "production" && (', page[button - 300:button])

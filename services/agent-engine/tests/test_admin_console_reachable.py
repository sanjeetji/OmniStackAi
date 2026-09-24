"""R-542: the admin console R-541 assembles is reachable in the Studio.

R-541 assembled `apps/admin` and the run plan started it, but the preview still reported a single
app — so the console ran and landed in the user's repo while being invisible in the product.

A project with a console now reports as a multi-app preview, which the console's existing
`MultiAppPreview` switcher and `/preview/<project>/<app>` proxy already serve. That proxy forwards
the full pathname upstream, so each Next app has to be *served* under its own base path — hence
`BASE_PATH` in the generated `next.config.mjs`, matching what template apps already do.

A project without a console must keep exactly the single-app behaviour it has always had.
"""

import dataclasses
import tempfile
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import AdminStrategy, WebStrategy, example_ir
from omnistackai_agent_engine.codegen import NextjsWebAdapter
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.localrun.plan import build_run_plan
from omnistackai_agent_engine.localrun.run import allocate_preview_ports, allocate_preview_ports3

PUBLIC_BASE = "/preview/proj-1"


def _repo_with(*apps: str) -> str:
    tmp = tempfile.mkdtemp()
    root = Path(tmp)
    for app in apps:
        d = root / "apps" / app
        d.mkdir(parents=True)
        (d / "package.json").write_text('{"name": "x"}', encoding="utf-8")
    return str(root)


def _env_of(plan, needle: str) -> dict:
    step = next(s for s in plan.steps if s.cwd and needle in s.cwd and s.background)
    return dict(step.env)


class TheGeneratedAppCanBeServedUnderABasePath(TestCase):
    def test_next_config_honours_base_path(self) -> None:
        config = NextjsWebAdapter().generate(example_ir("minimal-blog")).get("next.config.mjs").content
        self.assertIn("process.env.BASE_PATH", config)
        self.assertIn("basePath,", config)
        # Unset outside a preview, so `pnpm dev` still serves the app at the root.
        self.assertIn('process.env.BASE_PATH || ""', config)

    def test_both_generated_apps_get_the_same_config(self) -> None:
        ir = example_ir("minimal-blog")
        ir = dataclasses.replace(ir, project_strategy=dataclasses.replace(
            ir.project_strategy, web_strategy=WebStrategy.NEXTJS, admin_strategy=AdminStrategy.NEXTJS))
        project = assemble_project(ir)
        self.assertEqual(
            project.get("apps/web/next.config.mjs").content,
            project.get("apps/admin/next.config.mjs").content,
        )


class AProjectWithAConsoleIsAMultiAppPreview(TestCase):
    def setUp(self) -> None:
        self.plan = build_run_plan(_repo_with("web", "admin"), public_base=PUBLIC_BASE)

    def test_it_reports_both_uis_and_its_api(self) -> None:
        self.assertTrue(self.plan.multi_app)
        apps = self.plan.preview_apps()
        self.assertEqual([a["id"] for a in apps], ["web", "admin"])  # no backend in this fixture
        self.assertEqual([a["kind"] for a in apps], ["web", "admin"])

    def test_each_app_is_served_under_its_own_base_path(self) -> None:
        apps = {a["id"]: a for a in self.plan.preview_apps()}
        self.assertEqual(apps["web"]["path"], f"{PUBLIC_BASE}/web")
        self.assertEqual(apps["admin"]["path"], f"{PUBLIC_BASE}/admin")
        self.assertNotEqual(apps["web"]["url"], apps["admin"]["url"])

    def test_each_app_is_started_with_its_base_path(self) -> None:
        self.assertEqual(_env_of(self.plan, "apps/web")["BASE_PATH"], f"{PUBLIC_BASE}/web")
        self.assertEqual(_env_of(self.plan, "apps/admin")["BASE_PATH"], f"{PUBLIC_BASE}/admin")

    def test_the_api_base_is_relative_so_it_survives_the_proxy(self) -> None:
        """An absolute loopback url would break every call from another device on the LAN."""
        for app in ("apps/web", "apps/admin"):
            with self.subTest(app=app):
                self.assertEqual(_env_of(self.plan, app)["NEXT_PUBLIC_API_URL"], f"{PUBLIC_BASE}/api")

    def test_the_api_is_listed_when_the_project_has_a_backend(self) -> None:
        root = Path(_repo_with("web", "admin"))
        api = root / "services" / "api"
        api.mkdir(parents=True)
        (api / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        plan = build_run_plan(str(root), public_base=PUBLIC_BASE)
        apps = {a["id"]: a for a in plan.preview_apps()}
        self.assertIn("api", apps)
        self.assertEqual(apps["api"]["kind"], "api")
        self.assertEqual(apps["api"]["path"], f"{PUBLIC_BASE}/api")


class AProjectWithoutAConsoleIsUnchanged(TestCase):
    def test_a_single_app_project_is_not_multi(self) -> None:
        plan = build_run_plan(_repo_with("web"), public_base=PUBLIC_BASE)
        self.assertTrue(plan.has_web)
        self.assertFalse(plan.has_admin)
        self.assertFalse(plan.multi_app)
        self.assertEqual(plan.preview_apps(), ())

    def test_a_single_app_project_keeps_serving_at_the_root(self) -> None:
        plan = build_run_plan(_repo_with("web"), public_base=PUBLIC_BASE, api_port=8000)
        env = _env_of(plan, "apps/web")
        self.assertEqual(env["BASE_PATH"], "")
        # And keeps the absolute api url it has always had.
        self.assertEqual(env["NEXT_PUBLIC_API_URL"], "http://127.0.0.1:8000")

    def test_without_a_public_base_nothing_becomes_multi(self) -> None:
        """The CLI paths (`task app:run`) pass no public base and must keep working."""
        plan = build_run_plan(_repo_with("web", "admin"))
        self.assertTrue(plan.has_admin)
        self.assertFalse(plan.multi_app)
        self.assertEqual(_env_of(plan, "apps/admin")["BASE_PATH"], "")


class PortAllocation(TestCase):
    def test_three_distinct_free_ports(self) -> None:
        ports = allocate_preview_ports3()
        self.assertEqual(len(ports), 3)
        self.assertEqual(len(set(ports)), 3, ports)

    def test_the_two_port_allocator_still_works_for_existing_callers(self) -> None:
        api, web = allocate_preview_ports()
        self.assertNotEqual(api, web)

"""R-541: one prompt delivers every app it asked for, and each app looks like itself.

Two defects this locks shut:

1.  `nl_to_ir` has always defaulted `admin_strategy` to "nextjs", so every prompt-built IR asked
    for an admin panel — and `_plan_assembly` recorded it as "not assembled yet" and dropped it,
    because `GenerationTarget.NEXTJS_ADMIN` was declared with no adapter behind it. A request for
    "a website to sell my product with an admin panel" produced one app and no console.

2.  `_overview_page` renders an entity dashboard, and it was the home page of *every* generated
    app. A visitor arriving at a storefront met an internal console.
"""

import dataclasses
import json
import tempfile
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import AdminStrategy, WebStrategy, example_ir
from omnistackai_agent_engine.codegen import NextjsAdminAdapter, NextjsWebAdapter
from omnistackai_agent_engine.codegen.assembler import assemble_project, assembled_targets
from omnistackai_agent_engine.codegen.llm_ui import build_ui_synthesis_prompt, clean_and_validate_jsx
from omnistackai_agent_engine.localrun.plan import build_run_plan

_EXAMPLES = ("minimal-blog", "rideshare-favourites")


def _with_strategy(slug: str, **changes):
    ir = example_ir(slug)
    return dataclasses.replace(ir, project_strategy=dataclasses.replace(ir.project_strategy, **changes))


class EveryRequestedAppIsAssembled(TestCase):
    def test_a_site_with_an_admin_panel_assembles_both_apps_and_the_api(self) -> None:
        ir = _with_strategy("minimal-blog", web_strategy=WebStrategy.NEXTJS, admin_strategy=AdminStrategy.NEXTJS)
        by_dir = {app.directory: app.target for app in assembled_targets(ir)}
        self.assertEqual(
            by_dir,
            {"apps/web": "nextjs-web", "apps/admin": "nextjs-admin", "services/api": "backend-python"},
        )

    def test_nothing_is_recorded_as_skipped_for_an_admin_panel(self) -> None:
        """The README's "not assembled yet" note was the only trace the console ever left."""
        ir = _with_strategy("minimal-blog", web_strategy=WebStrategy.NEXTJS, admin_strategy=AdminStrategy.NEXTJS)
        self.assertNotIn("admin_strategy", assemble_project(ir).get("README.md").content)

    def test_an_admin_only_request_does_not_gain_a_public_website(self) -> None:
        """`nl_to_ir` used to force web_strategy back on so the console could hide in apps/web."""
        ir = _with_strategy("minimal-blog", web_strategy=WebStrategy.NONE, admin_strategy=AdminStrategy.NEXTJS)
        by_dir = {app.directory: app.target for app in assembled_targets(ir)}
        self.assertEqual(by_dir, {"apps/web": "nextjs-admin", "services/api": "backend-python"})

    def test_the_two_apps_can_share_one_workspace(self) -> None:
        """pnpm refuses two workspace packages with the same name."""
        ir = _with_strategy("minimal-blog", web_strategy=WebStrategy.NEXTJS, admin_strategy=AdminStrategy.NEXTJS)
        project = assemble_project(ir)
        web = json.loads(project.get("apps/web/package.json").content)["name"]
        admin = json.loads(project.get("apps/admin/package.json").content)["name"]
        self.assertNotEqual(web, admin)
        self.assertTrue(admin.endswith("-admin"), admin)


class EachAppLooksLikeItself(TestCase):
    def test_the_public_home_is_a_landing_page(self) -> None:
        for slug in _EXAMPLES:
            with self.subTest(slug=slug):
                page = NextjsWebAdapter().generate(example_ir(slug)).get("app/page.tsx").content
                # A landing page names the product and offers a way in...
                self.assertIn(example_ir(slug).name, page)
                self.assertIn("<main", page)
                self.assertIn("<footer", page)
                # ...and is not the staff dashboard: no live count hooks, no client runtime.
                self.assertNotIn("useList", page)
                self.assertNotIn('"use client"', page)

    def test_the_admin_home_is_the_dashboard(self) -> None:
        for slug in _EXAMPLES:
            with self.subTest(slug=slug):
                page = NextjsAdminAdapter().generate(example_ir(slug)).get("app/page.tsx").content
                self.assertTrue(page.startswith('"use client";'))
                self.assertIn("useList", page)

    def test_the_two_homes_are_not_the_same_page(self) -> None:
        ir = example_ir("minimal-blog")
        self.assertNotEqual(
            NextjsWebAdapter().generate(ir).get("app/page.tsx").content,
            NextjsAdminAdapter().generate(ir).get("app/page.tsx").content,
        )

    def test_the_public_home_is_valid_jsx(self) -> None:
        """The same validator the engine applies to model-written pages."""
        for slug in _EXAMPLES:
            with self.subTest(slug=slug):
                page = NextjsWebAdapter().generate(example_ir(slug)).get("app/page.tsx").content
                valid, _cleaned, reason = clean_and_validate_jsx(page)
                self.assertTrue(valid, f"{slug}: {reason}")

    def test_an_ir_with_no_screens_or_entities_still_renders(self) -> None:
        ir = dataclasses.replace(example_ir("minimal-blog"), screens=(), entities=(), apis=())
        page = NextjsWebAdapter().generate(ir).get("app/page.tsx").content
        valid, _cleaned, reason = clean_and_validate_jsx(page)
        self.assertTrue(valid, reason)
        self.assertIn("<main", page)

    def test_the_caller_can_state_the_archetype_instead_of_it_being_guessed(self) -> None:
        """"a website to sell my product" matches none of the website keywords, so inference
        alone classified a storefront as an admin panel."""
        ir = example_ir("minimal-blog")
        prompt = "a website to sell my product"
        inferred = build_ui_synthesis_prompt(ir, prompt)
        as_website = build_ui_synthesis_prompt(ir, prompt, archetype="public_website")
        as_admin = build_ui_synthesis_prompt(ir, prompt, archetype="admin_panel")

        # Inference alone reaches for the console; stating the archetype overrides it.
        self.assertEqual(inferred, as_admin)
        self.assertNotEqual(inferred, as_website)
        # And a prompt that does trip a keyword agrees with the stated form.
        self.assertEqual(
            build_ui_synthesis_prompt(ir, "a marketing website", archetype="public_website"),
            build_ui_synthesis_prompt(ir, "a marketing website"),
        )


class TheOutputStaysReproducible(TestCase):
    def test_the_whole_project_is_byte_stable_across_runs(self) -> None:
        ir = _with_strategy("minimal-blog", web_strategy=WebStrategy.NEXTJS, admin_strategy=AdminStrategy.NEXTJS)
        first = {f.path: f.content for f in assemble_project(ir).files()}
        second = {f.path: f.content for f in assemble_project(ir).files()}
        self.assertEqual(first, second)

    def test_the_admin_dashboard_keeps_its_diff_invariance(self) -> None:
        """Changing only the description must not churn the admin home (R-275's guarantee)."""
        ir = example_ir("minimal-blog")
        other = dataclasses.replace(ir, description="something else entirely")
        self.assertEqual(
            NextjsAdminAdapter().generate(ir).get("app/page.tsx").content,
            NextjsAdminAdapter().generate(other).get("app/page.tsx").content,
        )


class ThePreviewRunsBothApps(TestCase):
    def test_the_run_plan_starts_the_admin_console_on_its_own_port(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for app in ("web", "admin"):
                d = root / "apps" / app
                d.mkdir(parents=True)
                (d / "package.json").write_text('{"name": "x"}', encoding="utf-8")
            plan = build_run_plan(str(root), web_port=3000, admin_port=3100)

            self.assertTrue(plan.has_web)
            self.assertTrue(plan.has_admin)
            self.assertEqual(plan.admin_url, "http://127.0.0.1:3100")
            self.assertNotEqual(plan.web_url, plan.admin_url)

            admin_steps = [s for s in plan.steps if s.cwd and "apps/admin" in s.cwd]
            self.assertEqual(len(admin_steps), 2, "install then start")
            self.assertTrue(any(s.background and "3100" in s.args for s in admin_steps))
            self.assertIn("has_admin", plan.to_dict())

    def test_a_project_without_a_console_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            web = root / "apps" / "web"
            web.mkdir(parents=True)
            (web / "package.json").write_text('{"name": "x"}', encoding="utf-8")
            plan = build_run_plan(str(root))

            self.assertTrue(plan.has_web)
            self.assertFalse(plan.has_admin)
            self.assertEqual(plan.admin_url, "")
            self.assertFalse([s for s in plan.steps if s.cwd and "apps/admin" in s.cwd])

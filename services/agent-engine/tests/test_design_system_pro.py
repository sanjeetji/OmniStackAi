"""PC-050: model-written pages get a professional toolkit - charts, motion, tables, forms, dates,
toasts, a command palette and drawers - pinned for the generated apps' React 18.

The version list and the page writer's import allowlist must agree: a library the writer may use
but the app does not install fails the page's type-check, and one installed but not allowed is
dead weight. The type-check cache follows the list (scripts/omnistack.sh rebuilds it on change).
"""

import json
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.codegen.llm_ui import (
    ALLOWED_EXACT_IMPORTS,
    build_ui_synthesis_prompt,
    clean_and_validate_jsx,
)
from omnistackai_agent_engine.codegen.nextjs import DESIGN_SYSTEM_PRO

_PAGE = '''"use client";
import { ResponsiveContainer, AreaChart, Area } from "recharts";
import { motion } from "framer-motion";
import { useReactTable } from "@tanstack/react-table";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { format } from "date-fns";
import { toast } from "sonner";
import { Command } from "cmdk";
import { Drawer } from "vaul";

export default function Page() {
  return <motion.main>{format(new Date(), "PP")}</motion.main>;
}
'''


class TheToolkitIsInstalledAndAllowed(TestCase):
    def test_every_allowed_library_is_installed_and_every_installed_one_is_allowed(self) -> None:
        packages = {name.split("/zod")[0] for name in ALLOWED_EXACT_IMPORTS}
        for library in DESIGN_SYSTEM_PRO:
            self.assertIn(library, packages)
        for library in ("recharts", "framer-motion", "@tanstack/react-table", "zod", "sonner"):
            self.assertIn(library, DESIGN_SYSTEM_PRO)

    def test_versions_are_pinned_exactly(self) -> None:
        for library, version in DESIGN_SYSTEM_PRO.items():
            self.assertRegex(version, r"^\d+\.\d+\.\d+$", library)

    def test_both_next_apps_install_it(self) -> None:
        project = assemble_project(example_ir("minimal-blog"))
        for app in ("web", "admin"):
            dependencies = json.loads(project.get(f"apps/{app}/package.json").content)["dependencies"]
            self.assertEqual({k: dependencies[k] for k in DESIGN_SYSTEM_PRO}, DESIGN_SYSTEM_PRO)
            self.assertEqual(dependencies["react"], "18.3.1", "the pins are chosen for React 18")

    def test_a_page_using_it_passes_the_import_check(self) -> None:
        ok, _code, reason = clean_and_validate_jsx(_PAGE)
        self.assertTrue(ok, reason)

    def test_anything_else_is_still_refused(self) -> None:
        ok, _code, reason = clean_and_validate_jsx(_PAGE.replace('"cmdk"', '"react-icons/fa"'))
        self.assertFalse(ok)
        self.assertIn("react-icons", reason)


class TheWriterKnowsHowToUseIt(TestCase):
    def test_the_prompt_shows_the_imports_and_warns_against_invented_chart_data(self) -> None:
        prompt = build_ui_synthesis_prompt(example_ir("minimal-blog"), "a blog")
        self.assertIn("'recharts'", prompt)
        self.assertIn("'@hookform/resolvers/zod' { zodResolver }", prompt)
        self.assertIn("chart ONLY real data", prompt)

    def test_the_app_renders_the_toaster_that_toast_needs(self) -> None:
        layout = assemble_project(example_ir("minimal-blog")).get("apps/web/app/layout.tsx").content
        self.assertIn('import { Toaster } from "sonner";', layout)
        self.assertIn("<Toaster", layout)

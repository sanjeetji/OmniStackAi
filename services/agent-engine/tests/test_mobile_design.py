"""PC-129: the phone app's screens are designed by the model too - checked, or put back."""

import asyncio
import json
import os
import tempfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import ApplicationIR, MobileProfile
from omnistackai_agent_engine.studio import mobile_design

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"


def _project(tmp: str) -> Path:
    from omnistackai_agent_engine.intake.build_app import build_app_from_ir

    ir = ApplicationIR.from_dict(json.loads(FIXTURE.read_text()))
    ir = replace(ir, project_strategy=replace(ir.project_strategy, mobile_profile=MobileProfile.REACT_NATIVE))
    with mock.patch.dict(os.environ, {"OMNISTACKAI_BUILD_VERIFY": "off"}):
        return Path(build_app_from_ir(ir, Path(tmp) / "repo", author_name="t", author_email="t@example.com",
                                      prompt="A shop").target_dir)


class _Model:
    """Answers with the template it was sent, restyled - a well-behaved designer."""

    provider_id = "fake"

    def __init__(self, transform=lambda code: code.replace("StyleSheet.create({", "StyleSheet.create({\n  designed: { flex: 1 },", 1)):
        self.transform, self.calls = transform, 0

    async def generate(self, request):
        self.calls += 1
        text = request.messages[-1].content
        code = text.rsplit("```tsx\n", 1)[1].split("```", 1)[0]
        return SimpleNamespace(text="```tsx\n" + self.transform(code) + "```")


def _run(repo: Path, model, runner):
    async def go():
        return [e async for e in mobile_design.design_phone_screens(repo, "A shop", model, model_id="m", runner=runner)]
    return asyncio.run(go())


class TheContract(TestCase):
    TEMPLATE = ("import React from 'react';\nimport { View } from 'react-native';\nimport { useOrders } from '../hooks/useOrder';\n"
                "export const OrderListScreen = () => { const x = useOrders(); return <View />; };\n")

    def test_what_a_redesign_may_and_may_not_do(self) -> None:
        good = self.TEMPLATE.replace("<View />", "<View style={{ padding: 16 }} />").replace(
            "import { View } from 'react-native';", "import { View } from 'react-native';\nimport { Package } from 'lucide-react-native';")
        self.assertEqual(mobile_design.validate(good, self.TEMPLATE, "OrderListScreen"), (True, ""))
        kit = {"../../../design-system/components/Badge"}
        with_kit = self.TEMPLATE + "import { Badge } from '../../../design-system/components/Badge';\n"
        self.assertEqual(mobile_design.validate(with_kit, self.TEMPLATE, "OrderListScreen", kit), (True, ""),
                         "found live: the design system's own components are allowed")
        for bad, why in (
            (self.TEMPLATE.replace("OrderListScreen", "Orders"), "must still export"),
            (self.TEMPLATE + "import axios from 'axios';\n", "'axios'"),
            (self.TEMPLATE + "import { x } from '../api/secret';\n", "did not use"),
            (self.TEMPLATE + "const m = require('fs');\n", "require"),
            (self.TEMPLATE + "{", "truncated"),
        ):
            with self.subTest(why=why):
                ok, reason = mobile_design.validate(bad, self.TEMPLATE, "OrderListScreen")
                self.assertFalse(ok)
                self.assertIn(why, reason)


class DesigningAProject(TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = _project(self.tmp.name)

    def test_the_kit_as_each_screen_imports_it(self) -> None:
        base = self.repo / "apps/mobile"
        self.assertIn("../../design-system/components/Badge", mobile_design.kit_imports(base, "src/app/screens/OverviewScreen.tsx"))
        self.assertIn("../../../design-system/tokens", mobile_design.kit_imports(base, "src/features/order/ui/OrderListScreen.tsx"))

    def test_the_home_screen_first_then_the_lists(self) -> None:
        screens = mobile_design.plan_screens(self.repo)
        self.assertEqual(screens[0].path, "src/app/screens/OverviewScreen.tsx")
        self.assertTrue(all(s.path.endswith("ListScreen.tsx") for s in screens[1:]))
        self.assertIn("OrderListScreen", [s.export for s in screens])

    def test_checked_screens_are_kept(self) -> None:
        events = _run(self.repo, _Model(), runner=lambda argv, cwd: (0, ""))
        self.assertTrue(events and all(e["status"] == "designed" for e in events), events)
        overview = (self.repo / "apps/mobile/src/app/screens/OverviewScreen.tsx").read_text()
        self.assertTrue(overview.startswith(mobile_design.MARKER))
        self.assertEqual(mobile_design.plan_screens(self.repo), [], "designed screens are not redone")

    def test_a_screen_that_does_not_type_check_goes_back(self) -> None:
        overview = self.repo / "apps/mobile/src/app/screens/OverviewScreen.tsx"
        before = overview.read_text()
        calls = []

        def runner(argv, cwd):
            calls.append(1)
            return 2, "src/app/screens/OverviewScreen.tsx(3,1): error TS2304: Cannot find name 'Nope'.\n"

        events = {e["path"]: e for e in _run(self.repo, _Model(), runner)}
        self.assertEqual(events["apps/mobile/src/app/screens/OverviewScreen.tsx"]["status"], "kept_template")
        self.assertEqual(overview.read_text(), before)
        self.assertEqual(len(calls), 2, "checked, repaired once, checked again")

    def test_a_contract_break_is_never_written(self) -> None:
        model = _Model(lambda code: code + "\nimport fetchEverything from 'axios';\n")
        events = _run(self.repo, model, runner=lambda argv, cwd: (0, ""))
        self.assertTrue(all(e["status"] == "kept_template" and "axios" in e["reason"] for e in events))

    def test_through_the_real_compiler(self) -> None:
        cache = Path.home() / ".omnistackai" / "mobile-typecheck" / "node_modules"
        if not (cache / ".bin" / "tsc").exists():
            self.skipTest("no phone type-check cache on this machine")
        with mock.patch.dict(os.environ, {"OMNISTACKAI_MOBILE_NODE_MODULES": str(cache)}):
            events = _run(self.repo, _Model(), runner=None)
        statuses = {e["status"] for e in events}
        self.assertEqual(statuses, {"designed"}, events)
        self.assertFalse((self.repo / "apps/mobile/node_modules").exists(), "the shared cache link is removed")

"""R-545: the generated Expo app actually runs, and a phone can open it.

`codegen/react_native.py` has been emitting a genuine Expo app — design system, navigation, API
client, auth context, per-entity screens, iOS and Android bundle identifiers — and the platform
could do nothing with it. `APP_KINDS` had no mobile kind and `localrun/plan.py` contained zero
references to `apps/mobile`, so a user who asked for a mobile app received working code that was
never installed, started, previewed or offered as a QR.

The two things these tests care about, because they are what make it work on a real device:

* the app is started in LAN mode on its own port, and the preview reports the `exp://` URL that
  Expo Go reads from a QR — a native app cannot be shown in an iframe, so the QR *is* the preview;
* its API base is the machine's LAN address. A phone is a different device: `127.0.0.1` is the
  phone itself, so a loopback base silently fails every request the app makes.

PWA remains the default for generated apps. This runs alongside it and changes nothing about it.
"""

import ipaddress
import tempfile
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.localrun.plan import build_run_plan, lan_address
from omnistackai_agent_engine.localrun.run import (
    _should_skip,
    allocate_preview_ports3,
    allocate_preview_ports4,
)

API_PORT = 8000
MOBILE_PORT = 8081


def _repo(*apps: str, backend: bool = False) -> Path:
    root = Path(tempfile.mkdtemp())
    for app in apps:
        d = root / "apps" / app
        d.mkdir(parents=True)
        (d / "package.json").write_text('{"name": "x"}', encoding="utf-8")
    if backend:
        api = root / "services" / "api"
        api.mkdir(parents=True)
        (api / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    return root


def _mobile_steps(plan):
    return [s for s in plan.steps if s.cwd and s.cwd.endswith("apps/mobile")]


class TheLanAddressIsUsable(TestCase):
    def test_it_is_a_valid_ipv4_address(self) -> None:
        ipaddress.IPv4Address(lan_address())

    def test_it_is_deterministic_within_a_run(self) -> None:
        self.assertEqual(lan_address(), lan_address())

    def test_it_falls_back_rather_than_raising(self) -> None:
        """No network is not an error: the rest of the preview must still work."""
        self.assertTrue(lan_address(fallback="127.0.0.1"))


class TheMobileAppIsStarted(TestCase):
    def setUp(self) -> None:
        self.plan = build_run_plan(
            str(_repo("web", "admin", "mobile", backend=True)),
            public_base="/preview/p1",
            api_port=API_PORT,
            mobile_port=MOBILE_PORT,
        )

    def test_the_plan_knows_about_it(self) -> None:
        self.assertTrue(self.plan.has_mobile)
        self.assertTrue(self.plan.mobile_url.endswith(f":{MOBILE_PORT}"))

    def test_it_is_installed_and_started(self) -> None:
        steps = _mobile_steps(self.plan)
        self.assertEqual(len(steps), 2, [s.label for s in steps])
        self.assertTrue(steps[1].background)
        self.assertIn("expo", steps[1].program)

    def test_expo_runs_in_lan_mode_so_a_phone_can_reach_it(self) -> None:
        start = _mobile_steps(self.plan)[1]
        self.assertIn("--lan", start.args)
        self.assertIn(str(MOBILE_PORT), start.args)

    def test_expo_is_started_non_interactively(self) -> None:
        """Without this it waits on a keypress and the preview hangs forever."""
        env = dict(_mobile_steps(self.plan)[1].env)
        self.assertEqual(env.get("CI"), "1")

    def test_the_api_base_is_the_lan_address_not_loopback(self) -> None:
        """The single defect that would make a scanned app look broken on every screen."""
        env = dict(_mobile_steps(self.plan)[1].env)
        base = env["EXPO_PUBLIC_API_URL"]
        self.assertNotIn("127.0.0.1", base)
        self.assertNotIn("localhost", base)
        self.assertTrue(base.endswith(f":{API_PORT}"), base)


class ThePhoneGetsSomethingToScan(TestCase):
    def test_the_preview_reports_an_expo_url(self) -> None:
        plan = build_run_plan(str(_repo("web", "admin", "mobile")), public_base="/preview/p1")
        mobile = next(a for a in plan.preview_apps() if a["id"] == "mobile")
        self.assertEqual(mobile["kind"], "mobile")
        self.assertTrue(mobile["scan"].startswith("exp://"), mobile["scan"])

    def test_it_is_not_proxied_because_a_native_app_is_not_an_iframe(self) -> None:
        plan = build_run_plan(str(_repo("web", "admin", "mobile")), public_base="/preview/p1")
        mobile = next(a for a in plan.preview_apps() if a["id"] == "mobile")
        self.assertEqual(mobile["path"], "")

    def test_a_mobile_only_project_still_reports_it(self) -> None:
        """`preview_apps()` was empty unless the project was multi-app; mobile needs listing too."""
        plan = build_run_plan(str(_repo("web", "mobile")), public_base="/preview/p1")
        self.assertTrue(any(a["id"] == "mobile" for a in plan.preview_apps()))


class NothingElseChanges(TestCase):
    def test_a_project_without_a_mobile_app_is_untouched(self) -> None:
        plan = build_run_plan(str(_repo("web", "admin")), public_base="/preview/p1")
        self.assertFalse(plan.has_mobile)
        self.assertEqual(plan.mobile_url, "")
        self.assertEqual(plan.expo_url, "")
        self.assertEqual(_mobile_steps(plan), [])

    def test_the_three_port_allocator_still_works(self) -> None:
        ports = allocate_preview_ports3()
        self.assertEqual(len(ports), 3)
        self.assertEqual(len(set(ports)), 3)

    def test_four_distinct_ports_are_available(self) -> None:
        ports = allocate_preview_ports4()
        self.assertEqual(len(ports), 4)
        self.assertEqual(len(set(ports)), 4, ports)


class DependenciesAreNotReinstalledEveryTime(TestCase):
    def test_an_installed_expo_app_skips_its_install(self) -> None:
        root = _repo("mobile")
        plan = build_run_plan(str(root), public_base="/preview/p1")
        install = _mobile_steps(plan)[0]
        self.assertFalse(_should_skip(install))

        binv = root / "apps" / "mobile" / "node_modules" / ".bin"
        binv.mkdir(parents=True)
        (binv / "expo").write_text("#!/bin/sh\n", encoding="utf-8")
        self.assertTrue(_should_skip(install))


class TheGeneratedAppCanActuallyBundle(TestCase):
    """R-545: the Expo adapter had never been run. Two defects meant no generated mobile app has
    ever bundled — it would have failed on a phone at the first import, every time.

    These are static checks on purpose: they catch the same class of defect Metro catches, but
    offline and in milliseconds, so `task verify` can hold the line without a bundler.
    """

    def _files(self) -> dict:
        from omnistackai_agent_engine.application_ir import example_ir
        from omnistackai_agent_engine.codegen import ReactNativeAdapter

        return {f.path: f.content for f in ReactNativeAdapter().generate(example_ir("minimal-blog")).files()}

    def test_every_relative_import_resolves_to_a_generated_file(self) -> None:
        """`src/app/screens/OverviewScreen.tsx` imported `../design-system/...`, which is
        `src/app/design-system` — one level short. Metro could not resolve a single component on
        the app's own home screen."""
        import posixpath
        import re

        files = self._files()
        broken = []
        for path, content in files.items():
            if not path.endswith((".ts", ".tsx")):
                continue
            for imported in re.findall(r"from '(\.[^']+)'", content):
                target = posixpath.normpath(posixpath.join(posixpath.dirname(path), imported))
                if not any(
                    target == f or f.startswith(target + ".") or f.startswith(target + "/") for f in files
                ):
                    broken.append(f"{path} -> {imported}")
        self.assertEqual(broken, [], "unresolvable relative imports")

    def test_the_babel_runtime_helpers_are_declared(self) -> None:
        """babel-preset-expo emits `@babel/runtime/helpers/...` imports. Undeclared, pnpm's strict
        resolution cannot find them and the first bundle fails outright."""
        import json

        deps = json.loads(self._files()["package.json"])["dependencies"]
        self.assertIn("@babel/runtime", deps)

    def test_the_entry_point_matches_the_app_it_registers(self) -> None:
        files = self._files()
        entry = files["index.js"]
        self.assertIn("./src/app/App", entry)
        self.assertIn("src/app/App.tsx", files)

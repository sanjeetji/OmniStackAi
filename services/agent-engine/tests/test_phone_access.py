"""PC-124: scanning the QR opens the generated app on a real phone.

Two causes, both found by the founder's report that the QR did nothing:

* the apps were on Expo SDK 51, and the store's Expo Go opens only the newest SDK ("Project is
  incompatible with this version of Expo Go");
* the QR pointed at this computer's LAN address, which a phone on mobile data, a guest or office
  Wi-Fi with client isolation, or a VPN cannot reach. `OMNISTACKAI_PHONE_ACCESS=anywhere` opens
  public tunnels instead, and then the preview stops letting token-less requests in as an admin.
"""

import io
import json
import re
import tempfile
from pathlib import Path
from unittest import TestCase, mock

from omnistackai_agent_engine.codegen import expo_sdk
from omnistackai_agent_engine.localrun import phone_tunnel
from omnistackai_agent_engine.localrun.plan import build_run_plan

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"


def _repo(*apps: str) -> Path:
    root = Path(tempfile.mkdtemp())
    for app in apps:
        d = root / "apps" / app
        d.mkdir(parents=True)
        (d / "package.json").write_text('{"name": "x"}', encoding="utf-8")
        (d / "app.config.js").write_text("module.exports = {};", encoding="utf-8")
    api = root / "services" / "api"
    api.mkdir(parents=True)
    (api / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    return root


def _env(step) -> dict:
    return dict(step.env)


class TheAppIsOnTheSdkExpoGoOpens(TestCase):
    def test_one_sdk_everywhere(self) -> None:
        from omnistackai_agent_engine.application_ir import ApplicationIR
        from omnistackai_agent_engine.codegen.react_native import ReactNativeAdapter

        files = {f.path: f.content for f in ReactNativeAdapter().generate(ApplicationIR.from_dict(json.loads(FIXTURE.read_text()))).files()}
        manifest = json.loads(files["package.json"])
        self.assertEqual(manifest["dependencies"]["expo"], f"~{expo_sdk.SDK}.0.26")
        for name, version in {**manifest["dependencies"], **expo_sdk.PUSH}.items():
            if name.startswith("expo"):
                with self.subTest(package=name):
                    self.assertEqual(int(re.search(r"\d+", version).group(0)), expo_sdk.SDK, "an Expo module from another SDK")
        self.assertEqual(manifest["dependencies"]["react"], "19.2.3")
        self.assertIn("babel-preset-expo", manifest["devDependencies"], "babel.config.js names it; pnpm does not hoist it")

    def test_the_emulator_installs_the_matching_expo_go(self) -> None:
        from omnistackai_agent_engine.mobile_device import android

        self.assertIn(expo_sdk.SDK, android.EXPO_GO)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(android.expo_sdk_major(Path(tmp)), expo_sdk.SDK, "no package.json: the current SDK")

    def test_push_is_not_loaded_in_expo_go(self) -> None:
        from omnistackai_agent_engine.codegen.push_mobile import PUSH_MODULE

        self.assertNotIn("import * as Notifications from 'expo-notifications'", PUSH_MODULE)
        self.assertIn("require('expo-notifications')", PUSH_MODULE)
        self.assertIn("ExecutionEnvironment.StoreClient", PUSH_MODULE)
        self.assertIn("shouldShowBanner: true", PUSH_MODULE)


class OnTheSameWifi(TestCase):
    def test_the_default_is_the_lan(self) -> None:
        plan = build_run_plan(str(_repo("mobile")), api_port=8000, mobile_port=8081)
        surface = plan.mobile_surfaces[0]
        self.assertTrue(surface["scan"].startswith("exp://") and surface["scan"].endswith(":8081"))
        self.assertEqual(surface["access"], "lan")
        app = next(a for a in plan.preview_apps() if a["kind"] == "mobile")
        self.assertEqual((app["access"], app["sdk"]), ("lan", expo_sdk.SDK))
        expo = next(s for s in plan.steps if s.program.endswith("expo"))
        self.assertNotIn("EXPO_PACKAGER_PROXY_URL", _env(expo))

    def test_nothing_is_opened_unless_asked(self) -> None:
        from omnistackai_agent_engine.localrun.run import _phone_tunnels

        with mock.patch.dict("os.environ", {"OMNISTACKAI_PHONE_ACCESS": ""}), \
                mock.patch.object(phone_tunnel, "open_tunnel") as opened:
            self.assertEqual(_phone_tunnels(_repo("mobile"), 8000, 8081, None, None), ({}, None))
        opened.assert_not_called()


class FromAnywhere(TestCase):
    TUNNELS = {"api": "https://api-one.trycloudflare.com", "mobile": "https://app-two.trycloudflare.com",
               "courier": "https://app-three.trycloudflare.com"}

    def test_the_qr_and_the_app_use_the_tunnels(self) -> None:
        plan = build_run_plan(str(_repo("mobile", "courier")), api_port=8000, mobile_port=8081, phone_tunnels=self.TUNNELS)
        scans = {s["id"]: (s["scan"], s["access"]) for s in plan.mobile_surfaces}
        self.assertEqual(scans, {"mobile": ("exps://app-two.trycloudflare.com", "anywhere"),
                                 "courier": ("exps://app-three.trycloudflare.com", "anywhere")})
        self.assertEqual(plan.expo_url, "exps://app-two.trycloudflare.com")
        for step in (s for s in plan.steps if s.program.endswith("expo")):
            app = Path(step.cwd).name
            with self.subTest(app=app):
                self.assertEqual(_env(step)["EXPO_PACKAGER_PROXY_URL"], self.TUNNELS[app], "the manifest names the tunnel")
                self.assertEqual(_env(step)["EXPO_PUBLIC_API_URL"], self.TUNNELS["api"])

    def test_opening_tunnels_closes_the_dev_admin_door(self) -> None:
        from omnistackai_agent_engine.localrun.run import _phone_tunnels

        opened = []

        def fake_open(port: int):
            opened.append(port)
            return phone_tunnel.Tunnel(f"https://t{port}.trycloudflare.com", mock.Mock())

        with mock.patch.object(phone_tunnel, "open_tunnel", fake_open), \
                mock.patch.object(phone_tunnel, "wait_until_reachable", return_value=True):
            tunnels, secret = _phone_tunnels(_repo("mobile", "courier"), 8000, 8081,
                                             {"OMNISTACKAI_PHONE_ACCESS": "anywhere"}, None)
            self.assertEqual(opened, [8000, 8081, 8082])
            self.assertEqual(set(tunnels), {"api", "courier", "mobile"})
            self.assertTrue(secret.startswith("preview-") and secret not in phone_tunnel.DEV_SECRETS)
            _, kept = _phone_tunnels(_repo("mobile"), 8000, 8081,
                                     {"OMNISTACKAI_PHONE_ACCESS": "anywhere", "JWT_SECRET": "a-real-secret"}, None)
            self.assertEqual(kept, "a-real-secret", "a real secret is not replaced")

    def test_no_cloudflared_falls_back_to_the_lan(self) -> None:
        from omnistackai_agent_engine.localrun.run import _phone_tunnels

        lines = []
        with mock.patch.object(phone_tunnel, "open_tunnel", side_effect=phone_tunnel.TunnelError("needs cloudflared")):
            self.assertEqual(_phone_tunnels(_repo("mobile"), 8000, 8081, {"OMNISTACKAI_PHONE_ACCESS": "anywhere"}, lines.append),
                             ({}, None))
        self.assertIn("this Wi-Fi only", lines[0])


class _Process:
    def __init__(self, stderr: str) -> None:
        self.stderr = io.StringIO(stderr)
        self.terminated = False

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout=None) -> int:
        return 0

    def kill(self) -> None:
        pass


class TheTunnel(TestCase):
    def test_its_address_is_read_from_cloudflared(self) -> None:
        log = ("2026-10-02T10:00:00Z INF Requesting new quick Tunnel on trycloudflare.com...\n"
               "2026-10-02T10:00:02Z INF |  https://brave-otter-smile.trycloudflare.com  |\n")
        calls = []
        tunnel = phone_tunnel.open_tunnel(8081, program="cloudflared",
                                          popen=lambda args, **kw: calls.append(args) or _Process(log))
        self.assertEqual(tunnel.url, "https://brave-otter-smile.trycloudflare.com")
        self.assertEqual(calls[0], ["cloudflared", "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8081"])

    def test_no_address_is_an_error_and_the_process_is_stopped(self) -> None:
        process = _Process("ERR failed to request quick Tunnel\n")
        with self.assertRaises(phone_tunnel.TunnelError):
            phone_tunnel.open_tunnel(8081, program="cloudflared", popen=lambda *a, **k: process, timeout=2)
        self.assertTrue(process.terminated)

    def test_the_setting(self) -> None:
        with mock.patch.dict("os.environ", {"OMNISTACKAI_PHONE_ACCESS": ""}):
            self.assertEqual(phone_tunnel.phone_access(), "lan")
            self.assertEqual(phone_tunnel.phone_access({"OMNISTACKAI_PHONE_ACCESS": "Anywhere"}), "anywhere")
            self.assertEqual(phone_tunnel.phone_access({"OMNISTACKAI_PHONE_ACCESS": "tunnel"}), "anywhere")
            self.assertEqual(phone_tunnel.phone_access({"OMNISTACKAI_PHONE_ACCESS": "yes please"}), "lan")


class TheBundleIsBuiltBeforeTheScan(TestCase):
    """Found live: a cold bundle streamed through a quick tunnel stopped at "Bundling 99%"."""

    def test_each_app_and_platform(self) -> None:
        calls = []

        def fetch(url, headers):
            calls.append((url, headers["expo-platform"]))
            if "index.bundle" in url:
                return b"bundle"
            return json.dumps({"launchAsset": {"url": "https://app-two.trycloudflare.com/index.bundle?platform="
                                               + headers["expo-platform"] + "&dev=true"}}).encode()

        built = phone_tunnel.warm_bundles([8081, 8082], fetch=fetch)
        self.assertEqual(built, ["http://127.0.0.1:8081/index.bundle?platform=android&dev=true",
                                 "http://127.0.0.1:8081/index.bundle?platform=ios&dev=true",
                                 "http://127.0.0.1:8082/index.bundle?platform=android&dev=true",
                                 "http://127.0.0.1:8082/index.bundle?platform=ios&dev=true"])
        self.assertTrue(all(url.startswith("http://127.0.0.1:") for url, _ in calls), "built locally, never through the tunnel")

    def test_a_failure_is_noted_not_raised(self) -> None:
        notes = []
        self.assertEqual(phone_tunnel.warm_bundles([8081], fetch=lambda u, h: (_ for _ in ()).throw(OSError("refused")),
                                                   log=notes.append), [])
        self.assertEqual(len(notes), 2)

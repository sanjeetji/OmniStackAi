"""PC-063: the Android emulator in the Studio, set up and driven without Android Studio.

Every command is checked with a fake runner and a fake downloader: `verify` never downloads the SDK
or boots a device (the live proof does, once, on the founder's Mac).
"""

import hashlib
import io
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from omnistackai_agent_engine.mobile_device import android as a


def _done(stdout="", code=0, stderr=""):
    return subprocess.CompletedProcess([], code, stdout=stdout, stderr=stderr)


class _Fake:
    """Answers adb/sdkmanager/avdmanager the way a running, booted emulator does."""

    def __init__(self, devices=True, booted=True, packages="", opens=True):
        self.calls: list[list[str]] = []
        self.devices, self.booted, self.packages, self.opens = devices, booted, packages, opens
        self.front: str | None = None
        self.prefs = '<?xml version="1.0"?>\n<map>\n    <boolean name="is_onboarding_finished" value="false" />\n</map>\n'


    def __call__(self, cmd, env=None, input=None, timeout=0, text=True):
        self.calls.append(cmd)
        joined = " ".join(cmd)
        if cmd[-1] == "devices":
            return _done(f"List of devices attached\n{a.SERIAL}\tdevice\n" if self.devices else "List of devices attached\n")
        if "sys.boot_completed" in joined:
            return _done("1\n" if self.booted else "\n")
        if "pm list packages" in joined:
            return _done(self.packages)
        if "screencap" in joined:
            return _done(b"\x89PNG\r\n\x1a\nrest")
        if " install -r " in f" {joined} ":
            return _done("Performing Streamed Install\nSuccess\n")
        if "monkey" in cmd:
            self.front = "HomeActivity"
        if "android.intent.action.VIEW" in cmd:
            self.front = "ExperienceActivity" if self.opens else None
        if cmd[-2:] == ["cat", a.EXPO_GO_PREFS]:
            return _done(self.prefs)
        if cmd[-1] == "root":
            return _done("restarting adbd as root\n")
        if "dumpsys" in cmd:
            if not self.front:
                return _done("  topResumedActivity=ActivityRecord{1 u0 com.google.android.apps.nexuslauncher/.NexusLauncherActivity t7}\n")
            return _done(f"  topResumedActivity=ActivityRecord{{2 u0 host.exp.exponent/.experience.{self.front} t9}}\n")
        return _done("Starting: Intent { }\n")


def _sdk(root: Path, *, full: bool) -> a.Sdk:
    sdk = a.Sdk(root)
    for path in (sdk.emulator, sdk.adb):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    if full:
        sdk.sdkmanager.parent.mkdir(parents=True, exist_ok=True)
        sdk.sdkmanager.write_text("")
        image = sdk.image_dir("mac-arm64")
        image.mkdir(parents=True)
        (image / "system.img").write_text("")
    return sdk


class TheStatusSaysWhatIsMissingAndTheNextStep(TestCase):
    def test_a_fresh_sdk_is_not_set_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"ANDROID_AVD_HOME": f"{tmp}/avd"}):
            device = a.AndroidDevice(sdk=_sdk(Path(tmp) / "sdk", full=False), runner=_Fake(), host="mac-arm64")
            status = device.status()
        self.assertEqual(status["state"], "not_set_up")
        self.assertFalse(status["have"]["cmdline_tools"])
        self.assertTrue(status["have"]["emulator"])
        self.assertIn("1.5 GB", status["setup_size"])

    def test_set_up_then_stopped_then_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"ANDROID_AVD_HOME": f"{tmp}/avd"}):
            (Path(tmp) / "avd").mkdir()
            (Path(tmp) / "avd" / f"{a.AVD_NAME}.ini").write_text("")
            sdk = _sdk(Path(tmp) / "sdk", full=True)
            self.assertEqual(a.AndroidDevice(sdk=sdk, runner=_Fake(devices=False), host="mac-arm64").status()["state"], "stopped")
            self.assertEqual(a.AndroidDevice(sdk=sdk, runner=_Fake(booted=False), host="mac-arm64").status()["state"], "booting")
            self.assertEqual(a.AndroidDevice(sdk=sdk, runner=_Fake(), host="mac-arm64").status()["state"], "running")

    def test_the_sdk_is_found_where_android_studio_puts_it(self) -> None:
        self.assertEqual(a.find_sdk({"ANDROID_HOME": "/opt/sdk"}), Path("/opt/sdk"))
        self.assertTrue(str(a.find_sdk({"HOME": "/Users/x"})).startswith("/Users/x/"))

    def test_the_image_matches_the_machine(self) -> None:
        self.assertEqual(a.system_image("mac-arm64"), "system-images;android-34;google_apis;arm64-v8a")
        self.assertEqual(a.system_image("linux-x86_64"), "system-images;android-34;google_apis;x86_64")


class SetupIsVerifiedAndRepeatable(TestCase):
    def _zip(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("cmdline-tools/bin/sdkmanager", "#!/bin/sh\n")
            z.writestr("cmdline-tools/bin/avdmanager", "#!/bin/sh\n")
        return buf.getvalue()

    def test_setup_runs_each_step_in_order(self) -> None:
        payload = self._zip()
        name = a.CMDLINE_TOOLS["mac-arm64"][0]
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"ANDROID_AVD_HOME": f"{tmp}/avd"}), \
                patch.dict(a.CMDLINE_TOOLS, {"mac-arm64": (name, hashlib.sha1(payload).hexdigest())}):
            fetched = []
            fake = _Fake()
            device = a.AndroidDevice(sdk=_sdk(Path(tmp) / "sdk", full=False), cache=Path(tmp) / "cache", runner=fake,
                                     downloader=lambda url, target: (fetched.append(url), target.parent.mkdir(parents=True, exist_ok=True),
                                                                     target.write_bytes(payload)), host="mac-arm64")
            device.setup()
            self.assertEqual(device.error, "")
            self.assertTrue(device.sdk.sdkmanager.exists())
            self.assertTrue(device.sdk.sdkmanager.stat().st_mode & 0o100, "the tools are executable")
        self.assertEqual(fetched, ["https://dl.google.com/android/repository/" + name])
        steps = [c[1:] for c in fake.calls]
        self.assertIn("--licenses", steps[0])
        self.assertEqual(steps[1][1:], ["platform-tools", "emulator", "system-images;android-34;google_apis;arm64-v8a"])
        self.assertEqual(steps[2][:4], ["create", "avd", "--name", a.AVD_NAME])

    def test_a_download_that_does_not_match_the_checksum_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = _Fake()
            device = a.AndroidDevice(sdk=_sdk(Path(tmp) / "sdk", full=False), cache=Path(tmp) / "cache", runner=fake,
                                     downloader=lambda url, target: (target.parent.mkdir(parents=True, exist_ok=True),
                                                                     target.write_bytes(b"not the zip")), host="mac-arm64")
            device.setup()
            self.assertIn("checksum", device.error)
            self.assertFalse(device.sdk.sdkmanager.exists())
        self.assertEqual(fake.calls, [], "nothing runs from an unverified archive")


class TheAppOpensInExpoGoAndTheScreenIsDriven(TestCase):
    def test_expo_go_is_installed_for_the_apps_sdk_then_the_preview_opens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = _Fake(packages="")
            fetched = []
            device = a.AndroidDevice(sdk=_sdk(Path(tmp) / "sdk", full=True), cache=Path(tmp) / "cache", runner=fake,
                                     downloader=lambda url, target: (fetched.append(url), target.parent.mkdir(parents=True, exist_ok=True),
                                                                     target.write_bytes(b"apk")), host="mac-arm64",
                                     sleep=lambda s: None)
            with patch.object(a, "expo_go_url", return_value="https://example.com/Exponent-2.31.2.apk"):
                device.open_expo("exp://192.168.1.20:8081", 51)
            staged = (Path(tmp) / "cache" / f"staged-{a.EXPO_GO_PREFS.rsplit('/', 1)[-1]}").read_text()
            menu = (Path(tmp) / "cache" / "staged-expo.modules.devmenu.sharedpreferences.xml").read_text()
        self.assertIn('<boolean name="is_onboarding_finished" value="true" />', staged)
        for setting in ('"isOnboardingFinished" value="true"', '"showsAtLaunch" value="false"', '"showFab" value="false"', '"tryToLaunchLastBundle" value="false"'):
            self.assertIn(setting, menu, "Expo Go 57: no menu over the app, no Tools button over its header")
        self.assertEqual(fetched, ["https://example.com/Exponent-2.31.2.apk"])
        joined = [" ".join(c) for c in fake.calls]
        install = next(i for i, j in enumerate(joined) if "install -r" in j)
        home = next(i for i, j in enumerate(joined) if "monkey -p host.exp.exponent" in j)
        link = next(i for i, j in enumerate(joined) if "android.intent.action.VIEW -d exp://192.168.1.20:8081 host.exp.exponent" in j)
        self.assertLess(install, home)
        self.assertLess(home, link, "Expo Go's home is up before the link (a cold link crashes Expo Go 2.31)")
        push = next(i for i, j in enumerate(joined) if " push " in f" {j} ")
        self.assertLess(push, link, "the developer-menu introduction is marked seen before the app opens")

    def test_an_app_that_closes_while_opening_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            device = a.AndroidDevice(sdk=_sdk(Path(tmp) / "sdk", full=True), runner=_Fake(packages="package:host.exp.exponent", opens=False),
                                     host="mac-arm64", sleep=lambda s: None)
            with self.assertRaisesRegex(RuntimeError, "closed while opening"):
                device.open_expo("exp://192.168.1.20:8081", 51)

    def test_only_an_exp_url_is_opened(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            device = a.AndroidDevice(sdk=_sdk(Path(tmp) / "sdk", full=True), runner=_Fake(), host="mac-arm64")
            with self.assertRaises(ValueError):
                device.open_expo("https://evil.example/intent", 51)

    def test_expo_go_follows_the_versions_api_and_falls_back_offline(self) -> None:
        api = json.dumps({"data": {"sdkVersions": {"52.0.0": {"androidClientUrl": "https://x/Exponent-52.apk"}}}}).encode()
        self.assertEqual(a.expo_go_url(52, fetch=lambda u: api), "https://x/Exponent-52.apk")
        self.assertEqual(a.expo_go_url(51, fetch=lambda u: (_ for _ in ()).throw(OSError("offline"))), a.EXPO_GO[51])

    def test_the_apps_sdk_is_read_from_its_package_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "package.json").write_text(json.dumps({"dependencies": {"expo": "~51.0.0"}}))
            self.assertEqual(a.expo_sdk_major(Path(tmp)), 51)

    def test_input_is_validated_before_it_reaches_the_device(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = _Fake()
            device = a.AndroidDevice(sdk=_sdk(Path(tmp) / "sdk", full=True), runner=fake, host="mac-arm64")
            device.input({"kind": "tap", "x": 100, "y": 200.7})
            device.input({"kind": "text", "text": "hello world; rm -rf"})
            device.input({"kind": "key", "key": "back"})
            for bad in ({"kind": "tap", "x": "1; reboot", "y": 1}, {"kind": "key", "key": "power"}, {"kind": "shell"}):
                with self.assertRaises(ValueError):
                    device.input(bad)
        inputs = [c[c.index("input") + 1:] for c in fake.calls if "input" in c]
        self.assertEqual(inputs[0], ["tap", "100", "200"])
        self.assertEqual(inputs[1], ["text", "'hello%sworld;%srm%s-rf'"])
        self.assertEqual(inputs[2], ["keyevent", "4"])

    def test_the_screen_is_a_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            device = a.AndroidDevice(sdk=_sdk(Path(tmp) / "sdk", full=True), runner=_Fake(), host="mac-arm64")
            self.assertTrue(device.screen().startswith(b"\x89PNG"))


class TheStudioServesTheDevice(TestCase):
    """The routes the control plane proxies: status, screen (a PNG), actions, input, open."""

    def _server(self, device_fn, workspace_fn=None):
        import threading

        from omnistackai_agent_engine.studio import create_studio_server

        server = create_studio_server(lambda prompt: {}, host="127.0.0.1", port=0,
                                      android_device_fn=device_fn, workspace_device_fn=workspace_fn)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def _call(self, url, body=None):
        import urllib.error
        import urllib.request

        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.headers.get("Content-Type"), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type"), e.read()

    def test_each_route_reaches_its_operation(self) -> None:
        seen = []

        def device(op, body):
            seen.append((op, body))
            if op == "screen":
                return b"\x89PNG-bytes"
            if op == "input" and body.get("kind") == "shell":
                raise ValueError("kind must be tap, swipe, text or key")
            return {"state": "running"}

        def workspace(ws_id, body):
            if ws_id == "missing":
                raise KeyError(ws_id)
            raise RuntimeError("start the emulator first")

        base = self._server(device, workspace)
        self.assertEqual(self._call(base + "/api/device/android")[0], 200)
        status, ctype, body = self._call(base + "/api/device/android/screen")
        self.assertEqual((status, ctype, body), (200, "image/png", b"\x89PNG-bytes"))
        self.assertEqual(self._call(base + "/api/device/android", {"action": "boot"})[0], 200)
        self.assertEqual(self._call(base + "/api/device/android/input", {"kind": "tap", "x": 1, "y": 2})[0], 200)
        self.assertEqual(self._call(base + "/api/device/android/input", {"kind": "shell"})[0], 400)
        self.assertEqual(self._call(base + "/api/workspaces/abc/device", {})[0], 409)
        self.assertEqual(self._call(base + "/api/workspaces/missing/device", {})[0], 404)
        self.assertEqual([op for op, _ in seen], ["status", "screen", "act", "input", "input"])

    def test_without_a_device_the_routes_say_so(self) -> None:
        base = self._server(None)
        self.assertEqual(self._call(base + "/api/device/android")[0], 404)


class TheEmulatorsExpoGoMatchesTheApp(TestCase):
    """PC-124: an emulator set up for SDK 51 kept its Expo Go, which cannot open an SDK 57 app."""

    def _device(self, tmp: str, installed: str):
        class Old(_Fake):
            def __call__(self, cmd, env=None, input=None, timeout=0, text=True):
                if cmd[-3:] == ["dumpsys", "package", a.EXPO_GO_PACKAGE]:
                    self.calls.append(cmd)
                    return _done(f"    versionCode=1 minSdk=24\n    versionName={installed}\n")
                return super().__call__(cmd, env, input, timeout, text)

        fake = Old(packages="package:host.exp.exponent")
        device = a.AndroidDevice(sdk=_sdk(Path(tmp) / "sdk", full=True), cache=Path(tmp) / "cache", runner=fake,
                                 downloader=lambda url, target: (target.parent.mkdir(parents=True, exist_ok=True), target.write_bytes(b"apk")),
                                 host="mac-arm64", sleep=lambda s: None)
        return device, fake

    def test_an_older_expo_go_is_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            device, fake = self._device(tmp, "2.31.2")
            with patch.object(a, "expo_go_url", return_value="https://example.com/Expo-Go-57.0.9.apk"):
                device.open_expo("exps://brave-otter.trycloudflare.com", 57)
        self.assertTrue(any(c[-4:-1] == ["install", "-r", "-d"] for c in fake.calls), "reinstalled, downgrades allowed")
        self.assertTrue(any("android.intent.action.VIEW" in c and "exps://brave-otter.trycloudflare.com" in c for c in fake.calls))

    def test_the_right_one_is_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            device, fake = self._device(tmp, "57.0.9")
            with patch.object(a, "expo_go_url", return_value="https://example.com/Expo-Go-57.0.9.apk"):
                device.open_expo("exp://192.168.1.20:8081", 57)
        self.assertFalse(any("install" in c for c in fake.calls))


class ExpoGosDeveloperMenuIsClosed(TestCase):
    """PC-124, found live: Expo Go 57 opened its developer menu over the app on the first load."""

    def test_it_is_closed_when_it_appears(self) -> None:
        class Menu(_Fake):
            shown = 0

            def __call__(self, cmd, env=None, input=None, timeout=0, text=True):
                if cmd[-2:] == ["cat", "/sdcard/omnistack-ui.xml"]:
                    self.calls.append(cmd)
                    Menu.shown += 1
                    return _done('<node text="SDK version: 57.0.0"/><node text="Toggle performance monitor"/>' if Menu.shown > 2 else "<node/>")
                return super().__call__(cmd, env, input, timeout, text)

        with tempfile.TemporaryDirectory() as tmp:
            fake = Menu()
            fake.front = "ExperienceActivity"
            device = a.AndroidDevice(sdk=_sdk(Path(tmp) / "sdk", full=True), runner=fake, host="mac-arm64", sleep=lambda s: None)
            self.assertTrue(device.dismiss_dev_menu())
        self.assertEqual(fake.calls[-1][-3:], ["input", "keyevent", "4"])

    def test_nothing_is_pressed_when_it_never_appears(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = _Fake()
            fake.front = "ExperienceActivity"
            device = a.AndroidDevice(sdk=_sdk(Path(tmp) / "sdk", full=True), runner=fake, host="mac-arm64", sleep=lambda s: None)
            self.assertFalse(device.dismiss_dev_menu(polls=3))
        self.assertFalse(any("keyevent" in c for c in fake.calls))

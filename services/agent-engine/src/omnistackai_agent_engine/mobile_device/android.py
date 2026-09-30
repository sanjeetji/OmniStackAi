"""PC-063: an Android emulator in the Studio, without Android Studio.

The emulator is a separate Android SDK package driven from the command line, so the Studio can set
one up, boot it with no window, open a project's mobile app on it and show its screen:

    setup   cmdline-tools (checksum-verified) -> licences -> platform-tools, emulator and one
            arm64 (or x86_64) system image -> the `omnistack-phone` virtual device
    boot    `emulator -avd omnistack-phone -no-window ...`, then wait for Android to finish booting
    open    install Expo Go for the app's Expo SDK, then open the preview's exp:// URL in it
    screen  `adb exec-out screencap -p` (a PNG the Studio refreshes)
    input   taps, swipes, text and the back/home keys through `adb shell input`
    stop    `adb emu kill` (the emulator saves a snapshot, so the next boot takes seconds)

Nothing is downloaded unless the owner presses "Set up" (about 1.5 GB); `verify` never touches a
real device - the runner and the downloader are injected. See docs/runbooks/android-emulator.md.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import threading
import time
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

AVD_NAME = "omnistack-phone"
DEVICE_PROFILE = "pixel_6"
CONSOLE_PORT = 5580  # the emulator's serial is emulator-<port>; 5554 stays free for an owner's own
SERIAL = f"emulator-{CONSOLE_PORT}"
API_LEVEL = 34  # Android 14, what Expo SDK 51 targets
# A smaller screen than the phone profile keeps every screenshot small enough to refresh quickly.
SCREEN = {"hw.lcd.width": "720", "hw.lcd.height": "1560", "hw.lcd.density": "320", "hw.keyboard": "yes",
          "hw.ramSize": "2048"}

# cmdline-tools 23.0 (checked in Google's repository2-3.xml on 2026-09-30; sha1 is what it publishes).
_CMDLINE_BASE = "https://dl.google.com/android/repository/"
CMDLINE_TOOLS = {
    "mac-arm64": ("commandlinetools-mac_arm64-16111833_latest.zip", "ad03dc49bfacfd52c110b14104ea548b8a07e830"),
    "mac-x86_64": ("commandlinetools-mac_x86_64-16111833_latest.zip", "112cf9618794a997ff273537d55bee02c22abffe"),
    "linux-x86_64": ("commandlinetools-linux-16111833_latest.zip", "e025545c62a8e64c7559119566a569fb1dec5f60"),
}
# Expo Go per Expo SDK (from https://api.expo.dev/v2/versions/latest), used when that is unreachable.
EXPO_GO = {51: "https://d1ahtucjixef4r.cloudfront.net/Exponent-2.31.2.apk"}
EXPO_GO_PACKAGE = "host.exp.exponent"
EXPO_GO_PREFS = f"/data/data/{EXPO_GO_PACKAGE}/shared_prefs/{EXPO_GO_PACKAGE}.SharedPreferences.xml"
KEYS = {"back": 4, "home": 3, "enter": 66, "delete": 67, "apps": 187}


def _host() -> str:
    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
    return f"{'mac' if platform.system() == 'Darwin' else 'linux'}-{arch}"


def system_image(host: str | None = None) -> str:
    abi = "arm64-v8a" if (host or _host()).endswith("arm64") else "x86_64"
    return f"system-images;android-{API_LEVEL};google_apis;{abi}"


def find_sdk(env: dict[str, str] | None = None) -> Path:
    """The Android SDK: ANDROID_HOME / ANDROID_SDK_ROOT, else where Android Studio would put it."""
    env = os.environ if env is None else env
    for name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        if env.get(name):
            return Path(env[name]).expanduser()
    home = Path(env.get("HOME") or Path.home())
    return home / ("Library/Android/sdk" if platform.system() == "Darwin" else "Android/Sdk")


@dataclass(frozen=True)
class Sdk:
    root: Path

    @property
    def sdkmanager(self) -> Path:
        return self.root / "cmdline-tools/latest/bin/sdkmanager"

    @property
    def avdmanager(self) -> Path:
        return self.root / "cmdline-tools/latest/bin/avdmanager"

    @property
    def emulator(self) -> Path:
        return self.root / "emulator/emulator"

    @property
    def adb(self) -> Path:
        return self.root / "platform-tools/adb"

    def image_dir(self, host: str | None = None) -> Path:
        return self.root.joinpath(*system_image(host).split(";"))

    def env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.update({"ANDROID_HOME": str(self.root), "ANDROID_SDK_ROOT": str(self.root)})
        return env


def avd_home(env: dict[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    if env.get("ANDROID_AVD_HOME"):
        return Path(env["ANDROID_AVD_HOME"]).expanduser()
    return Path(env.get("HOME") or Path.home()) / ".android/avd"


Runner = Callable[..., "subprocess.CompletedProcess"]
Downloader = Callable[[str, Path], None]


def _run(cmd: list[str], *, env: dict[str, str] | None = None, input: str | bytes | None = None,
         timeout: float = 120, text: bool = True) -> "subprocess.CompletedProcess":
    return subprocess.run(cmd, env=env, input=input, capture_output=True, timeout=timeout, text=text, check=False)


def _download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as out:
        shutil.copyfileobj(response, out, 1 << 20)
    partial.replace(target)


def _sha1(path: Path) -> str:
    digest = hashlib.sha1()  # noqa: S324 - Google publishes sha1 for SDK archives
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expo_sdk_major(app_dir: Path) -> int:
    """The Expo SDK a generated app is on ("expo": "~51.0.0" -> 51)."""
    try:
        version = json.loads((app_dir / "package.json").read_text(encoding="utf-8"))["dependencies"]["expo"]
    except (OSError, ValueError, KeyError, TypeError):
        return 51
    match = re.search(r"(\d+)", str(version))
    return int(match.group(1)) if match else 51


def expo_go_url(sdk_major: int, fetch: Callable[[str], bytes] | None = None) -> str:
    """Expo Go supports one SDK per release, so the APK is picked for the app's SDK."""
    try:
        raw = (fetch or (lambda u: urllib.request.urlopen(u, timeout=15).read()))("https://api.expo.dev/v2/versions/latest")
        url = json.loads(raw)["data"]["sdkVersions"][f"{sdk_major}.0.0"]["androidClientUrl"]
        if isinstance(url, str) and url.startswith("https://"):
            return url
    except Exception:  # noqa: BLE001 - offline or a changed API: fall back to the pinned build
        pass
    if sdk_major in EXPO_GO:
        return EXPO_GO[sdk_major]
    raise ValueError(f"no Expo Go build is known for Expo SDK {sdk_major}")


@dataclass
class AndroidDevice:
    """The one emulator this machine runs for the Studio, and what it is doing."""

    sdk: Sdk = field(default_factory=lambda: Sdk(find_sdk()))
    cache: Path = field(default_factory=lambda: Path.home() / ".omnistackai/android")
    runner: Runner = _run
    downloader: Downloader = _download
    popen: Callable[..., "subprocess.Popen"] = subprocess.Popen
    sleep: Callable[[float], None] = time.sleep
    host: str = field(default_factory=_host)
    busy: str = ""
    log: list[str] = field(default_factory=list)
    error: str = ""
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _process: "subprocess.Popen | None" = None

    # -- what is there ---------------------------------------------------------------------------
    def _note(self, line: str) -> None:
        self.log = (self.log + [line])[-30:]

    def _adb(self, *args: str, timeout: float = 30, text: bool = True) -> "subprocess.CompletedProcess":
        return self.runner([str(self.sdk.adb), "-s", SERIAL, *args], env=self.sdk.env(), timeout=timeout, text=text)

    def running(self) -> bool:
        if not self.sdk.adb.exists():
            return False
        try:
            listed = self.runner([str(self.sdk.adb), "devices"], env=self.sdk.env(), timeout=10)
        except (OSError, subprocess.SubprocessError):
            return False
        return any(line.split("\t")[:2] == [SERIAL, "device"] for line in (listed.stdout or "").splitlines())

    def booted(self) -> bool:
        try:
            return self._adb("shell", "getprop", "sys.boot_completed", timeout=10).stdout.strip() == "1"
        except (OSError, subprocess.SubprocessError):
            return False

    def status(self) -> dict:
        """Everything the Studio's device panel shows, and the one next step."""
        have = {
            "cmdline_tools": self.sdk.sdkmanager.exists(),
            "emulator": self.sdk.emulator.exists(),
            "platform_tools": self.sdk.adb.exists(),
            "system_image": (self.sdk.image_dir(self.host) / "system.img").exists(),
            "device": (avd_home() / f"{AVD_NAME}.ini").exists(),
        }
        ready = all(have.values())
        running = ready and self.running()
        booted = running and self.booted()
        if self.busy:
            state = self.busy
        elif not ready:
            state = "not_set_up"
        elif not running:
            state = "stopped"
        else:
            state = "running" if booted else "booting"
        return {"state": state, "have": have, "sdk": str(self.sdk.root), "device": AVD_NAME,
                "system_image": system_image(self.host), "log": self.log[-8:], "error": self.error,
                "setup_size": "about 1.5 GB (downloaded once)" if not ready else ""}

    # -- setting up --------------------------------------------------------------------------------
    def _install_cmdline_tools(self) -> None:
        if self.sdk.sdkmanager.exists():
            return
        if self.host not in CMDLINE_TOOLS:
            raise RuntimeError(f"no Android command-line tools are published for {self.host}")
        name, sha1 = CMDLINE_TOOLS[self.host]
        archive = self.cache / name
        if not archive.exists() or _sha1(archive) != sha1:
            self._note(f"Downloading the Android command-line tools ({name})")
            self.downloader(_CMDLINE_BASE + name, archive)
        if _sha1(archive) != sha1:
            archive.unlink(missing_ok=True)
            raise RuntimeError("the command-line tools download did not match Google's checksum")
        staging = self.cache / "cmdline-tools-unzip"
        shutil.rmtree(staging, ignore_errors=True)
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(staging)
        target = self.sdk.root / "cmdline-tools/latest"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(target, ignore_errors=True)
        shutil.move(str(staging / "cmdline-tools"), str(target))
        shutil.rmtree(staging, ignore_errors=True)
        for tool in (target / "bin").iterdir():
            tool.chmod(0o755)  # zipfile does not keep the executable bit

    def _sdkmanager(self, *args: str, timeout: float = 3600) -> None:
        done = self.runner([str(self.sdk.sdkmanager), f"--sdk_root={self.sdk.root}", *args], env=self.sdk.env(),
                           input="y\n" * 40, timeout=timeout)
        if done.returncode != 0:
            raise RuntimeError(f"sdkmanager {' '.join(args)} failed: {(done.stderr or done.stdout or '')[-400:]}")

    def _create_device(self) -> None:
        if (avd_home() / f"{AVD_NAME}.ini").exists():
            return
        done = self.runner([str(self.sdk.avdmanager), "create", "avd", "--name", AVD_NAME, "--package",
                            system_image(self.host), "--device", DEVICE_PROFILE, "--force"],
                           env=self.sdk.env(), input="no\n", timeout=300)
        if done.returncode != 0:
            raise RuntimeError(f"creating the virtual device failed: {(done.stderr or done.stdout or '')[-400:]}")
        config = avd_home() / f"{AVD_NAME}.avd/config.ini"
        if config.exists():
            lines = [l for l in config.read_text(encoding="utf-8").splitlines() if l.split("=", 1)[0].strip() not in SCREEN]
            config.write_text("\n".join(lines + [f"{k}={v}" for k, v in SCREEN.items()]) + "\n", encoding="utf-8")

    def setup(self) -> None:
        """Everything the emulator needs, once. Safe to run again: each step skips what is there."""
        try:
            self._install_cmdline_tools()
            self._note("Accepting the Android SDK licences")
            self._sdkmanager("--licenses", timeout=300)
            self._note(f"Installing platform-tools, the emulator and {system_image(self.host)} (the long step)")
            self._sdkmanager("platform-tools", "emulator", system_image(self.host))
            self._note(f"Creating the virtual device {AVD_NAME}")
            self._create_device()
            self._note("Set up. Start the emulator to use it.")
            self.error = ""
        except Exception as error:  # noqa: BLE001 - shown in the panel, never raised into the server
            self.error = str(error)
            self._note(f"Setup stopped: {error}")

    # -- running -----------------------------------------------------------------------------------
    def boot(self, wait: float = 240) -> None:
        if self.running():
            return
        self.cache.mkdir(parents=True, exist_ok=True)
        log = (self.cache / "emulator.log").open("ab")
        self._note("Starting the emulator (the first boot takes a minute or two)")
        self._process = self.popen(
            [str(self.sdk.emulator), "-avd", AVD_NAME, "-port", str(CONSOLE_PORT), "-no-window", "-no-audio",
             "-no-boot-anim", "-gpu", "swiftshader_indirect", "-netdelay", "none", "-netspeed", "full"],
            env=self.sdk.env(), stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            start_new_session=True)
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                self.error = f"the emulator exited ({self._process.returncode}); see {self.cache / 'emulator.log'}"
                self._note(self.error)
                return
            if self.running() and self.booted():
                self._adb("shell", "settings", "put", "global", "window_animation_scale", "0")
                self._adb("shell", "settings", "put", "global", "transition_animation_scale", "0")
                self._note("The emulator is running.")
                self.error = ""
                return
            time.sleep(2)
        self.error = "the emulator did not finish booting in time"
        self._note(self.error)

    def stop(self) -> None:
        if self.running():
            self._adb("emu", "kill", timeout=30)
            self._note("The emulator stopped (a snapshot makes the next start quick).")
        self._process = None

    def start(self, action: str) -> dict:
        """setup / boot / stop in the background; the panel polls status()."""
        if action not in ("setup", "boot", "stop"):
            raise ValueError("action must be setup, boot or stop")
        with self._lock:
            if self.busy:
                return self.status()
            self.busy = {"setup": "setting_up", "boot": "booting", "stop": "stopping"}[action]
            self.error = ""

        def work() -> None:
            try:
                getattr(self, action)()
            finally:
                self.busy = ""

        threading.Thread(target=work, name=f"android-{action}", daemon=True).start()
        return self.status()

    # -- the app ---------------------------------------------------------------------------------
    def has_expo_go(self) -> bool:
        return EXPO_GO_PACKAGE in (self._adb("shell", "pm", "list", "packages", EXPO_GO_PACKAGE).stdout or "")

    def open_expo(self, url: str, sdk_major: int = 51) -> dict:
        """Install Expo Go for the app's SDK if needed, then open the preview in it."""
        if not url.startswith("exp://"):
            raise ValueError("an Expo preview URL starts with exp://")
        if not (self.running() and self.booted()):
            raise RuntimeError("start the emulator first")
        if not self.has_expo_go():
            apk_url = expo_go_url(sdk_major)
            apk = self.cache / apk_url.rsplit("/", 1)[-1]
            if not apk.exists():
                self._note(f"Downloading Expo Go for Expo SDK {sdk_major}")
                self.downloader(apk_url, apk)
            self._note("Installing Expo Go on the emulator")
            done = self._adb("install", "-r", str(apk), timeout=300)
            if done.returncode != 0 or "Success" not in (done.stdout or ""):
                raise RuntimeError(f"installing Expo Go failed: {(done.stderr or done.stdout or '')[-300:]}")
        # Found live: a link that cold-starts Expo Go 2.31 crashes it ("Unable to attach a rootView
        # to ReactInstance when UIManager is not properly initialized") - its own home screen has to
        # be up first. So: start Expo Go, wait for its home, then hand it the link.
        self._start_expo_home()
        # Found live: on its first app Expo Go opens its developer-menu introduction, which this
        # headless emulator never draws - the app shows but ignores every touch until Back. The
        # emulator's image is ours (google_apis, rootable), so the introduction is marked as seen.
        if self._finish_expo_onboarding():
            self._start_expo_home()
        done = self._adb("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url, EXPO_GO_PACKAGE)
        if done.returncode != 0 or "Error" in (done.stdout or ""):
            raise RuntimeError(f"opening the app failed: {(done.stderr or done.stdout or '')[-300:]}")
        if not self._wait_for(lambda: self._expo_screen() == "ExperienceActivity", 20):
            raise RuntimeError("Expo Go closed while opening the app - its log is `adb logcat` on the emulator")
        self._note(f"Opened {url} in Expo Go")
        return {"opened": url, "sdk": sdk_major}

    def _start_expo_home(self) -> None:
        if self._expo_screen():
            return
        self._adb("shell", "monkey", "-p", EXPO_GO_PACKAGE, "-c", "android.intent.category.LAUNCHER", "1")
        if not self._wait_for(lambda: self._expo_screen() is not None, 30):
            raise RuntimeError("Expo Go did not start on the emulator")

    def _finish_expo_onboarding(self) -> bool:
        """Mark Expo Go's developer-menu introduction as seen; True when Expo Go had to restart."""
        prefs = EXPO_GO_PREFS
        rooted = self._adb("root", timeout=30)
        if rooted.returncode != 0 or "cannot" in f"{rooted.stdout}{rooted.stderr}".lower():
            return False  # not rootable (a Play Store image): the owner taps Back once
        self._adb("wait-for-device", timeout=60)
        current = self._adb("shell", "cat", prefs).stdout or ""
        if '"is_onboarding_finished" value="true"' in current or "</map>" not in current:
            return False
        if '"is_onboarding_finished"' in current:
            updated = current.replace('"is_onboarding_finished" value="false"', '"is_onboarding_finished" value="true"')
        else:
            updated = current.replace("</map>", '    <boolean name="is_onboarding_finished" value="true" />\n</map>')
        self._adb("shell", "am", "force-stop", EXPO_GO_PACKAGE)
        # Written through the existing file, so it keeps the app as its owner.
        staged = self.cache / "expo-go-prefs.xml"
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text(updated, encoding="utf-8")
        self._adb("push", str(staged), "/data/local/tmp/omnistack-expo-prefs.xml")
        self._adb("shell", f"cat /data/local/tmp/omnistack-expo-prefs.xml > {prefs} && rm /data/local/tmp/omnistack-expo-prefs.xml")
        self._note("Marked Expo Go's developer-menu introduction as seen")
        return True

    def _expo_screen(self) -> str | None:
        """The Expo Go screen in front (HomeActivity, ExperienceActivity, ...), or None."""
        shown = self._adb("shell", "dumpsys", "activity", "activities").stdout or ""
        match = re.search(r"topResumedActivity=.*? " + re.escape(EXPO_GO_PACKAGE) + r"/\S*?\.(\w+Activity)", shown)
        return match.group(1) if match else None

    def _wait_for(self, check: Callable[[], bool], seconds: int) -> bool:
        """Check once a second, ``seconds`` times."""
        for _ in range(seconds):
            if check():
                return True
            self.sleep(1)
        return check()

    def screen(self) -> bytes:
        done = self._adb("exec-out", "screencap", "-p", timeout=15, text=False)
        if done.returncode != 0 or not (done.stdout or b"").startswith(b"\x89PNG"):
            raise RuntimeError("the emulator is not showing a screen yet")
        return done.stdout

    def input(self, body: dict) -> dict:
        """A tap, swipe, text or key from the Studio (coordinates in device pixels)."""
        kind = body.get("kind")

        def coord(name: str) -> str:
            value = body.get(name)
            if not isinstance(value, (int, float)) or not 0 <= value <= 10000:
                raise ValueError(f"{name} must be a pixel position")
            return str(int(value))

        if kind == "tap":
            args = ["tap", coord("x"), coord("y")]
        elif kind == "swipe":
            args = ["swipe", coord("x"), coord("y"), coord("x2"), coord("y2"), "250"]
        elif kind == "text":
            text = str(body.get("text") or "")[:200]
            if not text:
                raise ValueError("text is empty")
            # `input text` takes %s for a space; everything else is passed as one quoted argument.
            args = ["text", "'" + text.replace("'", "").replace(" ", "%s") + "'"]
        elif kind == "key":
            if body.get("key") not in KEYS:
                raise ValueError(f"key must be one of {', '.join(KEYS)}")
            args = ["keyevent", str(KEYS[body["key"]])]
        else:
            raise ValueError("kind must be tap, swipe, text or key")
        done = self._adb("shell", "input", *args)
        if done.returncode != 0:
            raise RuntimeError((done.stderr or "input failed")[-200:])
        return {"ok": True}


def main() -> None:
    """`python -m omnistackai_agent_engine.mobile_device.android [status|setup|boot|stop]`."""
    import sys

    device = AndroidDevice()
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action in ("setup", "boot", "stop"):
        getattr(device, action)()
        for line in device.log:
            print(line)
    status = device.status()
    have = ", ".join(k.replace("_", " ") for k, v in status["have"].items() if not v)
    print(f"android emulator: {status['state']}" + (f" (missing: {have})" if have else "")
          + (f" - {status['error']}" if status["error"] else ""))
    if action != "status" and status["error"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

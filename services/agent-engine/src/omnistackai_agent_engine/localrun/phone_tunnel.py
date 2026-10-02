"""PC-124: the phone reaches the preview from any network.

By default the QR is `exp://<this machine's LAN address>:<port>`, which works only when the phone is
on the same Wi-Fi as this computer and that Wi-Fi lets two devices talk to each other. Many do
not: phones on mobile data, guest and office networks with client isolation, a VPN on either side.

`OMNISTACKAI_PHONE_ACCESS=anywhere` opens a Cloudflare quick tunnel (`cloudflared`, no account) to
the app's dev server and one to its API, and the QR becomes `exps://<name>.trycloudflare.com`. Expo
is told its public address (EXPO_PACKAGER_PROXY_URL), so the manifest and the bundle come through the
tunnel, and the app calls the API through its own tunnel.

A tunnel makes the preview reachable from the internet. The preview API treats a request with no
token as an admin while the JWT secret is the development default, so with a tunnel the preview gets
a random secret of its own: people sign in, exactly as in the published app.
"""

from __future__ import annotations

import os
import re
import secrets
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable, Mapping

LAN = "lan"
ANYWHERE = "anywhere"
_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
#: The JWT secrets under which a generated API lets a request with no token in as a dev admin.
DEV_SECRETS = ("local-dev-secret", "dev-secret", "change-me-in-production")


class TunnelError(RuntimeError):
    pass


def phone_access(env: Mapping[str, str] | None = None) -> str:
    """`anywhere` when asked for, otherwise `lan` (the default: nothing leaves this machine)."""
    value = ((env or {}).get("OMNISTACKAI_PHONE_ACCESS") or os.environ.get("OMNISTACKAI_PHONE_ACCESS", "")).strip().lower()
    return ANYWHERE if value in (ANYWHERE, "tunnel", "internet") else LAN


def cloudflared() -> str | None:
    return shutil.which("cloudflared") or next(
        (p for p in ("/opt/homebrew/bin/cloudflared", "/usr/local/bin/cloudflared") if os.path.exists(p)), None)


@dataclass
class Tunnel:
    url: str
    process: subprocess.Popen

    @property
    def host(self) -> str:
        return self.url.removeprefix("https://")


def open_tunnel(port: int, *, popen: Callable[..., subprocess.Popen] = subprocess.Popen,
                timeout: float = 45.0, program: str | None = None) -> Tunnel:
    """A quick tunnel to 127.0.0.1:`port`; returns once cloudflared has printed its public address."""
    binary = program or cloudflared()
    if not binary:
        raise TunnelError("phone access from anywhere needs cloudflared: brew install cloudflared")
    process = popen([binary, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, bufsize=1, start_new_session=True)
    process.omnistack_group = True  # type: ignore[attr-defined]  - stopped with the preview's other processes
    found: list[str] = []
    ready = threading.Event()

    def _read() -> None:
        for line in iter(process.stderr.readline, ""):  # type: ignore[union-attr]
            if not found:
                match = _URL.search(line)
                if match:
                    found.append(match.group(0))
                    ready.set()
        ready.set()  # cloudflared exited

    threading.Thread(target=_read, daemon=True).start()
    if not ready.wait(timeout) or not found:
        close(process)
        raise TunnelError(f"cloudflared did not open a tunnel to port {port} within {int(timeout)}s")
    return Tunnel(found[0], process)


def close(process: subprocess.Popen) -> None:
    try:
        process.terminate()
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass


def wait_until_reachable(url: str, *, timeout: float = 30.0, fetch: Callable[[str], object] | None = None,
                         sleep: Callable[[float], None] = time.sleep) -> bool:
    """A new quick tunnel takes a few seconds before its name resolves everywhere."""
    import urllib.error
    import urllib.request

    def _default(u: str) -> object:
        try:
            return urllib.request.urlopen(u, timeout=10)  # noqa: S310 - our own tunnel
        except urllib.error.HTTPError as error:  # any HTTP answer means the tunnel is up
            return error

    deadline = time.monotonic() + timeout
    while True:
        try:
            (fetch or _default)(url)
            return True
        except Exception:  # noqa: BLE001 - not resolvable or not routed yet
            if time.monotonic() >= deadline:
                return False
            sleep(1.0)


def preview_secret(current: str) -> str:
    """A development secret is replaced by a random one; a real secret is kept."""
    return f"preview-{secrets.token_urlsafe(24)}" if not current or current in DEV_SECRETS else current


def warm_bundles(ports: list[int], *, fetch: Callable[[str, dict], bytes] | None = None,
                 platforms: tuple[str, ...] = ("android", "ios"), log: Callable[[str], None] | None = None) -> list[str]:
    """Build each app's bundle once, locally, before a phone asks for it.

    Found live: Expo Go streams a cold bundle's build progress and waits on one long response; a
    quick tunnel dropped its end and the app stayed on "Bundling 99%". With the bundle already built
    the phone's download takes seconds - through a tunnel, and on the first LAN scan as well.
    Returns the bundle URLs built (local addresses).
    """
    import json
    import urllib.parse
    import urllib.request

    def _default(url: str, headers: dict) -> bytes:
        return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=600).read()  # noqa: S310 - localhost

    get = fetch or _default
    built: list[str] = []
    for port in ports:
        local = f"http://127.0.0.1:{port}"
        for platform in platforms:
            try:
                raw = get(local, {"expo-platform": platform, "accept": "application/expo+json,application/json"}).decode()
                bundle = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])["launchAsset"]["url"]
                parsed = urllib.parse.urlsplit(bundle)
                url = f"{local}{parsed.path}?{parsed.query}"
                get(url, {"expo-platform": platform})
                built.append(url)
            except Exception as error:  # noqa: BLE001 - a phone can still build it on its first scan
                if log is not None:
                    log(f"!  the {platform} bundle on :{port} was not built ahead ({error})")
    return built

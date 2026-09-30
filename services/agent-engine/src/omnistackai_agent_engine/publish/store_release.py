"""R-574: publish a project's mobile app to Google Play and the App Store from the Studio.

R-546/R-547 made every generated Expo app store-ready (eas.json, icons, version numbers, privacy
manifest). This runs the release itself, with EAS (Expo Application Services), which builds in
Expo's cloud - so an iOS build needs no Mac:

    check   which credentials are set and which are missing, per store (nothing runs)
    build   `eas build --platform <p> --profile production --non-interactive --no-wait`
    submit  `eas submit --platform <p> --profile production --non-interactive --latest --no-wait`

The credentials are the app owner's and come only from the project's secrets (the control plane
passes them per request); none is created, logged or kept. Key files that EAS reads from disk are
written into the app's git-ignored `credentials/` folder for the one command and deleted after it.
The App Store upload uses an App Store Connect API key, the non-interactive way - an Apple ID
password with two-factor codes cannot be typed by a server.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

EAS_CLI = "eas-cli@24.8.0"
PLATFORMS = ("android", "ios")
ACTIONS = ("check", "build", "submit")


@dataclass(frozen=True)
class Credential:
    name: str
    what: str
    where: str
    file: str | None = None  # written to credentials/<file> while a command runs


EXPO_TOKEN = Credential("EXPO_TOKEN", "Expo access token",
                        "expo.dev -> Account settings -> Access tokens -> Create token")
EAS_PROJECT_ID = Credential("EAS_PROJECT_ID", "EAS project ID",
                            "expo.dev -> Projects -> Create a project -> the project's ID")
PLAY_KEY = Credential("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON", "Google Play service account key (JSON)",
                      "Google Cloud console -> IAM -> Service accounts -> Keys -> Add key (JSON); "
                      "then Play Console -> Users and permissions -> invite that account as a release manager",
                      file="play-service-account.json")
ASC_KEY = Credential("ASC_API_KEY_P8", "App Store Connect API key (.p8 contents)",
                     "App Store Connect -> Users and Access -> Integrations -> App Store Connect API -> "
                     "Generate key (App Manager); download the .p8 once", file="asc-api-key.p8")
ASC_KEY_ID = Credential("ASC_API_KEY_ID", "App Store Connect API key ID", "shown beside the key")
ASC_ISSUER = Credential("ASC_API_ISSUER_ID", "App Store Connect issuer ID", "shown above the keys list")
APPLE_TEAM = Credential("APPLE_TEAM_ID", "Apple Developer team ID", "developer.apple.com -> Account -> Membership")
ASC_APP = Credential("ASC_APP_ID", "App Store Connect app ID",
                     "App Store Connect -> Apps -> New app -> App Information -> Apple ID (a number)")

NEEDS: dict[tuple[str, str], tuple[Credential, ...]] = {
    ("android", "build"): (EXPO_TOKEN, EAS_PROJECT_ID),
    ("android", "submit"): (EXPO_TOKEN, EAS_PROJECT_ID, PLAY_KEY),
    # An iOS build signs the app: EAS creates the certificate and profile with the API key.
    ("ios", "build"): (EXPO_TOKEN, EAS_PROJECT_ID, ASC_KEY, ASC_KEY_ID, ASC_ISSUER, APPLE_TEAM),
    ("ios", "submit"): (EXPO_TOKEN, EAS_PROJECT_ID, ASC_KEY, ASC_KEY_ID, ASC_ISSUER, APPLE_TEAM, ASC_APP),
}


@dataclass
class StoreResult:
    platform: str
    action: str
    ok: bool
    missing: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    output: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"platform": self.platform, "action": self.action, "ok": self.ok, "missing": self.missing,
                "warnings": self.warnings, "output": self.output, "details": self.details}


def mobile_apps(repo: Path) -> list[Path]:
    """Every Expo app in the project (apps/<name>/eas.json)."""
    return sorted(p.parent for p in (repo / "apps").glob("*/eas.json")) if (repo / "apps").is_dir() else []


def _warnings(app: Path) -> list[str]:
    """What the stores will refuse that no credential fixes (the generated files say the same)."""
    notes = []
    try:
        identity = json.loads((app.parent.parent / "brand.json").read_text(encoding="utf-8")).get("identity", {})
    except (OSError, ValueError):
        identity = {}
    bundle = identity.get("bundleId") or ""
    if bundle and not identity.get("published"):
        notes.append(f"bundle identifier {bundle}: make sure it is under a domain you own before the first upload - "
                     "the stores tie it to the listing for good (brand.json -> identity.bundleId)")
    try:
        store = json.loads((app / "store.config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        store = {}
    if not (store.get("privacyPolicyUrl") or "").strip():
        notes.append("both stores require a privacy policy URL before review (store.config.json -> privacyPolicyUrl)")
    return notes


def missing_for(platform: str, action: str, secrets: dict[str, str]) -> list[Credential]:
    return [c for c in NEEDS[(platform, "build" if action == "check" else action)] if not (secrets.get(c.name) or "").strip()]


def check(repo: Path, platform: str, secrets: dict[str, str]) -> StoreResult:
    """What a release to ``platform`` still needs: credentials per step, and store warnings."""
    apps = mobile_apps(repo)
    if not apps:
        return StoreResult(platform, "check", False, output="This project has no mobile app to publish.")
    missing = {c.name: c for step in ("build", "submit") for c in missing_for(platform, step, secrets)}
    result = StoreResult(platform, "check", not missing, warnings=_warnings(apps[0]))
    result.missing = [{"name": c.name, "what": c.what, "where": c.where} for c in missing.values()]
    result.details = {"app": str(apps[0].relative_to(repo)),
                      "can_build": not missing_for(platform, "build", secrets),
                      "can_submit": not missing_for(platform, "submit", secrets)}
    return result


def _command(platform: str, action: str) -> list[str]:
    npx = shutil.which("npx") or "npx"
    base = [npx, "--yes", EAS_CLI]
    if action == "build":
        return base + ["build", "--platform", platform, "--profile", "production", "--non-interactive",
                       "--no-wait", "--json"]
    return base + ["submit", "--platform", platform, "--profile", "production", "--non-interactive",
                   "--latest", "--no-wait"]


Runner = Callable[[list[str], Path, dict[str, str]], "subprocess.CompletedProcess[str]"]


def _run(cmd: list[str], cwd: Path, env: dict[str, str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=900, check=False)


def _scrub(text: str, secrets: dict[str, str]) -> str:
    """No secret in the output, and none of npm's deprecation noise from fetching eas-cli."""
    for value in secrets.values():
        if value and len(value) >= 6:
            text = text.replace(value, "[redacted]")
    text = "\n".join(line for line in text.splitlines() if not line.startswith("npm warn")).strip()
    return text[-4000:]


def _hint(output: str) -> str:
    """The next step for the failures an owner can fix, in front of eas-cli's own words."""
    lowered = output.lower()
    if "graphql request failed" in lowered or "unauthorized" in lowered or "not logged in" in lowered:
        return "Expo did not accept EXPO_TOKEN - create a new token on expo.dev and replace the secret.\n"
    if "could not find project" in lowered or "experience with id" in lowered:
        return "Expo has no project with this EAS_PROJECT_ID under the token's account.\n"
    return ""


def release(repo: Path, platform: str, action: str, secrets: dict[str, str], runner: Runner = _run) -> StoreResult:
    """Run ``build`` or ``submit`` for ``platform``; refuses (and lists why) when a credential is missing."""
    if platform not in PLATFORMS or action not in ("build", "submit"):
        raise ValueError("platform must be android or ios, action build or submit")
    apps = mobile_apps(repo)
    if not apps:
        return StoreResult(platform, action, False, output="This project has no mobile app to publish.")
    missing = missing_for(platform, action, secrets)
    if missing:
        return StoreResult(platform, action, False,
                           missing=[{"name": c.name, "what": c.what, "where": c.where} for c in missing],
                           output="Add these to the project's secrets, then try again.")
    app = apps[0]
    creds_dir = app / "credentials"
    creds_dir.mkdir(exist_ok=True)
    written: list[Path] = []
    eas_json = app / "eas.json"
    original_eas = eas_json.read_text(encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OMNISTACKAI_", "EXPO_", "EAS_", "ASC_"))}
    env.update({"EXPO_TOKEN": secrets[EXPO_TOKEN.name], "EAS_PROJECT_ID": secrets[EAS_PROJECT_ID.name],
                "CI": "1", "EAS_NO_VCS": "1", "EAS_BUILD_NO_EXPO_GO_WARNING": "1"})
    try:
        for cred in NEEDS[(platform, action)]:
            if cred.file:
                path = creds_dir / cred.file
                path.write_text(secrets[cred.name], encoding="utf-8")
                path.chmod(0o600)
                written.append(path)
        if platform == "ios":
            # EAS manages the signing certificate and profile with the API key, without a login.
            env.update({"EXPO_ASC_API_KEY_PATH": str(creds_dir / ASC_KEY.file), "EXPO_ASC_KEY_ID": secrets[ASC_KEY_ID.name],
                        "EXPO_ASC_ISSUER_ID": secrets[ASC_ISSUER.name], "EXPO_APPLE_TEAM_ID": secrets[APPLE_TEAM.name],
                        "EXPO_APPLE_TEAM_TYPE": "COMPANY_OR_ORGANIZATION"})
            if action == "submit":
                # eas submit reads these only from the submit profile, never the environment
                # (checked in eas-cli 24.8.0): filled for this one command, restored below.
                config = json.loads(original_eas)
                ios = config.setdefault("submit", {}).setdefault("production", {}).setdefault("ios", {})
                ios.update({"ascApiKeyPath": f"./credentials/{ASC_KEY.file}", "ascApiKeyId": secrets[ASC_KEY_ID.name],
                            "ascApiKeyIssuerId": secrets[ASC_ISSUER.name], "ascAppId": secrets[ASC_APP.name]})
                eas_json.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        done = runner(_command(platform, action), app, env)
    except (OSError, subprocess.SubprocessError) as error:
        return StoreResult(platform, action, False, output=f"{type(error).__name__}: {error}")
    finally:
        for path in written:
            path.unlink(missing_ok=True)
        if eas_json.read_text(encoding="utf-8") != original_eas:
            eas_json.write_text(original_eas, encoding="utf-8")
    output = _scrub((done.stdout or "") + (done.stderr or ""), secrets)
    result = StoreResult(platform, action, done.returncode == 0,
                         output=output if done.returncode == 0 else _hint(output) + output)
    if action == "build" and done.returncode == 0:
        try:
            builds = json.loads(done.stdout)
            first = builds[0] if isinstance(builds, list) and builds else builds
            result.details = {"build_id": first.get("id"), "status": first.get("status"),
                              "url": f"https://expo.dev/accounts/{first.get('accountName', '')}/projects/"
                                     f"{first.get('projectName', '')}/builds/{first.get('id')}"}
        except (ValueError, AttributeError, TypeError):
            pass
    return result

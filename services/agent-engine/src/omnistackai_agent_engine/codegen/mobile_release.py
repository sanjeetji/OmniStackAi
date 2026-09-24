"""Everything a generated Expo app needs to be built and submitted to the stores (R-546).

R-545 made the app run on a phone. It could not be *built* for a store: no `eas.json`, so
`eas build` has nothing to read; no icon, so a listing would carry Expo's default; no
`versionCode`/`buildNumber`, so a second upload to either store is refused outright; no iOS
privacy manifest, which Apple has required since spring 2024; and a bundle identifier under
`com.omnistackai.*` — our domain on someone else's app, which they cannot register.

Everything here is generated offline with the standard library. **No credential, key, certificate
or account is created, used or embedded.** Secrets are referenced by name (`EXPO_TOKEN`, a service
account path) so the founder can paste them in later without a generated file ever holding one.

The PNG encoder exists because `GeneratedFile.content` is text: an icon travels as base64 and is
decoded by the single writer in `git_service/materialize.py`.
"""

from __future__ import annotations

import base64
import binascii  # noqa: F401 - imported for the error type GeneratedFile raises on bad base64
import hashlib
import json
import struct
import zlib

from ..application_ir import ApplicationIR, BrandTokens
from .files import GeneratedFile

# --- a minimal PNG encoder ------------------------------------------------------------------------


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + tag
        + payload
        + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    )


def png_bytes(width: int, height: int, rows: list[bytes]) -> bytes:
    """Encode 8-bit RGB rows as a PNG. `rows` holds `height` entries of `width * 3` bytes."""
    raw = b"".join(b"\x00" + row for row in rows)  # filter type 0 per scanline
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _solid_with_plate(size: int, background: str, plate: str, inset_ratio: float, radius_ratio: float) -> bytes:
    """A solid square with a centred rounded plate — deliberately simple, and recognisably branded.

    Not an attempt at art: it is a real, valid, brand-coloured icon so a first store listing does
    not show Expo's default, and it is trivially replaceable. `assets/README.md` says exactly that.
    """
    bg = _rgb(background)
    fg = _rgb(plate)
    inset = int(size * inset_ratio)
    radius = int(size * radius_ratio)
    left, right = inset, size - inset
    top, bottom = inset, size - inset

    rows: list[bytes] = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            inside = left <= x < right and top <= y < bottom
            if inside and radius > 0:
                # Round the plate's corners so it reads as an icon rather than a flat square.
                for cx, cy in ((left + radius, top + radius), (right - radius - 1, top + radius),
                               (left + radius, bottom - radius - 1), (right - radius - 1, bottom - radius - 1)):
                    if (x < left + radius or x > right - radius - 1) and (y < top + radius or y > bottom - radius - 1):
                        if (x - cx) ** 2 + (y - cy) ** 2 > radius ** 2:
                            inside = False
                        break
            row += bytes(fg if inside else bg)
        rows.append(bytes(row))
    return png_bytes(size, size, rows)


def _png_file(path: str, data: bytes) -> GeneratedFile:
    return GeneratedFile(path, base64.b64encode(data).decode("ascii"), base64_encoded=True)


def _mark_grid(seed: str, cells: int = 5) -> list[list[bool]]:
    """A vertically-mirrored grid of filled cells, derived from the app's name.

    R-547: the first default icon was a flat plate, which reads as unfinished. This is the approach
    GitHub and GitLab use for default avatars, and for the same reason: it is deterministic, unique
    per project, and looks deliberate rather than blank. Mirroring is what makes an arbitrary hash
    look designed — symmetry reads as intent.
    """
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    half = cells // 2 + cells % 2
    grid = [[False] * cells for _ in range(cells)]
    bit = 0
    for row in range(cells):
        for col in range(half):
            filled = bool(digest[bit % len(digest)] & (1 << (bit // len(digest) % 8)))
            bit += 1
            grid[row][col] = filled
            grid[row][cells - 1 - col] = filled
    # A sparse hash renders a thin, weak mark. Raise it to a floor that reads as a shape, adding
    # mirrored pairs in a fixed order so symmetry — and determinism — survive. Filling the centre
    # column alone was not enough: cells already set there left the total short of the floor.
    floor = cells * 2
    for row in range(cells):
        if sum(sum(r) for r in grid) >= floor:
            break
        grid[row][half - 1] = True
    for col in range(half - 1, -1, -1):
        for row in range(cells):
            if sum(sum(r) for r in grid) >= floor:
                break
            if not grid[row][col]:
                grid[row][col] = True
                grid[row][cells - 1 - col] = True
    return grid


def _mark_png(size: int, background: str, ink: str, seed: str, *, cells: int = 5, margin_ratio: float = 0.18) -> bytes:
    """Render the mark: rounded cells in `ink` on a solid `background`."""
    bg = _rgb(background)
    fg = _rgb(ink)
    grid = _mark_grid(seed, cells)

    margin = int(size * margin_ratio)
    span = size - 2 * margin
    cell = span / cells
    # Half a cell makes each mark a circle. At icon scale a dot grid reads as a designed mark;
    # square blocks read as pixels, which is exactly the "unfinished" look this replaces.
    radius = cell * 0.5

    rows: list[bytes] = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            colour = bg
            gx = (x - margin) / cell
            gy = (y - margin) / cell
            if 0 <= gx < cells and 0 <= gy < cells and grid[int(gy)][int(gx)]:
                # Inscribe a circle in the cell (see `radius`).
                fx = (gx - int(gx)) * cell
                fy = (gy - int(gy)) * cell
                cx = radius if fx < radius else (cell - radius if fx > cell - radius else fx)
                cy = radius if fy < radius else (cell - radius if fy > cell - radius else fy)
                if (fx - cx) ** 2 + (fy - cy) ** 2 <= radius ** 2:
                    colour = fg
            row += bytes(colour)
        rows.append(bytes(row))
    return png_bytes(size, size, rows)


def icon_files(brand: BrandTokens, name: str = "") -> list[GeneratedFile]:
    """The icon set Expo references. Sized as Expo documents: 1024 square for the store icon."""
    background = brand.primary_color
    ink = "#ffffff"
    seed = name or "app"
    return [
        _png_file("assets/icon.png", _mark_png(1024, background, ink, seed, margin_ratio=0.18)),
        # Android masks the adaptive foreground to a circle or squircle, so the art has to sit
        # inside the middle ~66%: a wider margin keeps the mark from being clipped.
        _png_file("assets/adaptive-icon.png", _mark_png(1024, background, ink, seed, margin_ratio=0.28)),
        _png_file("assets/splash.png", _mark_png(1024, background, ink, seed, margin_ratio=0.34)),
        _png_file("assets/favicon.png", _mark_png(48, background, ink, seed, margin_ratio=0.16)),
    ]


# --- identifiers ----------------------------------------------------------------------------------


def bundle_identifier(slug: str) -> str:
    """A reverse-DNS identifier derived from the project, not from us.

    It was `com.omnistackai.<slug>` — our domain on a user's app, which they cannot register with
    either store. This is a placeholder the user owns the shape of; `README-RELEASE.md` says in the
    first section to change it to a domain they control before the first submission, because both
    stores bind an identifier permanently to the listing on first upload.
    """
    cleaned = "".join(ch for ch in slug.lower() if ch.isalnum() or ch == "-")
    parts = [p for p in cleaned.split("-") if p] or ["app"]
    if parts[0][0].isdigit():
        parts[0] = f"a{parts[0]}"
    return "com." + ".".join(parts) + ".app" if len(parts) == 1 else "com." + ".".join(parts)


# --- generated configuration ------------------------------------------------------------------------


def eas_json() -> GeneratedFile:
    """Build profiles. `development` for a dev client, `preview` for an installable internal build,
    `production` for the store artefacts (`.aab` for Play, `.ipa` for the App Store)."""
    config = {
        "cli": {"version": ">= 12.0.0", "appVersionSource": "remote"},
        "build": {
            "development": {
                "developmentClient": True,
                "distribution": "internal",
                "env": {"EXPO_PUBLIC_API_URL": "http://127.0.0.1:8000"},
            },
            "preview": {
                "distribution": "internal",
                "android": {"buildType": "apk"},
                "env": {"EXPO_PUBLIC_API_URL": "https://staging.example.com"},
            },
            "production": {
                "autoIncrement": True,
                "android": {"buildType": "app-bundle"},
                "env": {"EXPO_PUBLIC_API_URL": "https://api.example.com"},
            },
        },
        "submit": {
            "production": {
                "android": {
                    # A path, never a key: the file is supplied by the publisher and git-ignored.
                    "serviceAccountKeyPath": "./credentials/play-service-account.json",
                    "track": "internal",
                },
                "ios": {
                    "appleId": "$EXPO_APPLE_ID",
                    "ascAppId": "$EXPO_ASC_APP_ID",
                    "appleTeamId": "$EXPO_APPLE_TEAM_ID",
                },
            }
        },
    }
    return GeneratedFile("eas.json", json.dumps(config, indent=2) + "\n")


def privacy_manifest() -> GeneratedFile:
    """Apple has rejected submissions without a privacy manifest since spring 2024.

    Declares the one reason a generated app actually uses: `UserDefaults`, which React Native's
    AsyncStorage sits on. It declares no tracking and no collected data, which is true of the
    generated app; a publisher adding analytics must extend this, and the release README says so.
    """
    plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>NSPrivacyTracking</key>
  <false/>
  <key>NSPrivacyTrackingDomains</key>
  <array/>
  <key>NSPrivacyCollectedDataTypes</key>
  <array/>
  <key>NSPrivacyAccessedAPITypes</key>
  <array>
    <dict>
      <key>NSPrivacyAccessedAPIType</key>
      <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
      <key>NSPrivacyAccessedAPITypeReasons</key>
      <array>
        <string>CA92.1</string>
      </array>
    </dict>
  </array>
</dict>
</plist>
"""
    return GeneratedFile("assets/PrivacyInfo.xcprivacy", plist)


def store_config(ir: ApplicationIR) -> GeneratedFile:
    """Listing metadata for `eas submit`, with nothing secret in it."""
    config = {
        "name": ir.name,
        "shortDescription": (ir.description or ir.name)[:80],
        "fullDescription": ir.description or ir.name,
        "keywords": [],
        "category": "",
        "privacyPolicyUrl": "",
        "supportUrl": "",
        "_note": (
            "Both stores require a reachable privacy policy URL before review. Fill privacyPolicyUrl "
            "and supportUrl in before the first submission; a listing without them is rejected."
        ),
    }
    return GeneratedFile("store.config.json", json.dumps(config, indent=2) + "\n")


def env_example() -> GeneratedFile:
    """R-547: every variable `eas.json` references, with what to paste and where it comes from.

    R-546 named these and stopped there, which left a founder holding an Apple Team ID with nowhere
    obvious to put it. Values are placeholders shaped like the real thing so a wrong paste is
    obvious; none of them is a credential.
    """
    return GeneratedFile(
        ".env.example",
        """# Copy to .env.local and fill in. .env* is git-ignored — never commit real values.
# Only EXPO_PUBLIC_* reaches the app bundle; everything else is used by eas build/submit.

# ---------------------------------------------------------------------------
# The app itself
# ---------------------------------------------------------------------------

# Where the built app calls your API. Must be a public HTTPS URL for a store build —
# a released app cannot reach localhost. Example: https://api.yourcompany.com
EXPO_PUBLIC_API_URL=https://api.example.com

# ---------------------------------------------------------------------------
# Expo (needed for `eas build`; free account at https://expo.dev)
# ---------------------------------------------------------------------------

# A personal access token. expo.dev -> account settings -> Access tokens -> Create.
# Looks like a long opaque string. Used by CI; locally `eas login` is enough instead.
EXPO_TOKEN=

# ---------------------------------------------------------------------------
# Apple (needed for `eas submit --platform ios`; Apple Developer Program, 99 USD/year)
# ---------------------------------------------------------------------------

# The Apple ID email you sign in to developer.apple.com with. Example: you@yourcompany.com
EXPO_APPLE_ID=

# Your 10-character Team ID. developer.apple.com -> Membership details -> Team ID.
# Ten letters and digits, e.g. A1B2C3D4E5
EXPO_APPLE_TEAM_ID=

# The App Store Connect app ID — the numeric id of the listing, NOT the bundle identifier.
# Create the app in App Store Connect first; the id is in the URL and in App Information.
# All digits, e.g. 6478123456
EXPO_ASC_APP_ID=

# ---------------------------------------------------------------------------
# Google Play (needed for `eas submit --platform android`; Play Console, 25 USD once)
# ---------------------------------------------------------------------------

# No variable to set: the Play service-account JSON is a *file*.
# Put it at credentials/play-service-account.json — see credentials/README.md.
""",
    )


def credentials_readme() -> GeneratedFile:
    """R-547: `eas.json` points at a service-account file; say where it comes from."""
    return GeneratedFile(
        "credentials/README.md",
        """# Credentials

**This directory is git-ignored. Nothing in it should ever be committed.**

## `play-service-account.json`

`eas.json` reads this path when submitting to Google Play. To create it:

1. Google Play Console -> **Setup** -> **API access**.
2. Create or link a Google Cloud project, then **Create new service account**.
3. In Google Cloud, give that account a key: **Keys** -> **Add key** -> **JSON**. The file
   downloads once and cannot be downloaded again.
4. Back in Play Console, grant the account the **Release manager** role (it needs permission to
   upload and to release to a track).
5. Save the downloaded file here as `play-service-account.json`.

It is a JSON object containing `"type": "service_account"`, a `client_email` and a `private_key`.
The private key is a real secret: anyone holding it can publish to your listing.

## Apple

Nothing is stored here. EAS manages iOS signing certificates and provisioning profiles for you the
first time you run `eas build --platform ios`; answer yes when it offers to handle them. Your Apple
identifiers go in `.env.local` — see `.env.example`.

## If a credential leaks

Revoke it before anything else: delete the service-account key in Google Cloud, or revoke the
token at expo.dev. Rotating is cheap; a compromised publishing key is not.
""",
    )


def assets_readme() -> GeneratedFile:
    return GeneratedFile(
        "assets/README.md",
        """# Assets

`icon.png`, `adaptive-icon.png`, `splash.png` and `favicon.png` were generated from the project's
brand colour so the first build is branded rather than carrying Expo's default icon. **Replace
them with your own artwork before you publish** — they are valid placeholders, not a design.

Sizes Expo expects:

| File | Size | Used for |
| --- | --- | --- |
| `icon.png` | 1024x1024 | the store icon and the iOS app icon |
| `adaptive-icon.png` | 1024x1024 | the Android adaptive foreground (keep art inside the middle 66%) |
| `splash.png` | 1024x1024 | the launch screen |
| `favicon.png` | 48x48 | the web build |

`PrivacyInfo.xcprivacy` is Apple's privacy manifest, required for App Store review. It currently
declares no tracking and no collected data, which is true of the generated app. **If you add
analytics, advertising or any SDK that collects data, you must extend it** or review will fail.
""",
    )


def release_readme(ir: ApplicationIR, identifier: str) -> GeneratedFile:
    return GeneratedFile(
        "README-RELEASE.md",
        f"""# Publishing {ir.name} to the App Store and Google Play

Everything in this app is configured for a store build. What is left is the part only you can do:
accounts and credentials. Nothing here needs further coding.

## 1. Change the bundle identifier first

`app.json` currently uses `{identifier}`, derived from the project name. **Change it to a domain
you own** (for example `com.yourcompany.{ir.name.lower().replace(' ', '')}`) *before* your first
upload. Both stores bind an identifier permanently to a listing on first submission — it cannot be
changed afterwards, and it cannot be reused.

Set the same value in three places: `expo.ios.bundleIdentifier`, `expo.android.package`, and your
listing in each store console.

## 2. Accounts you need

| What | Cost | Why |
| --- | --- | --- |
| Apple Developer Program | 99 USD / year | required to submit any iOS app |
| Google Play Developer | 25 USD once | required to submit any Android app |
| Expo account | free tier available | runs `eas build` in the cloud, so no Mac is needed for iOS |

## 3. Credentials, and where they go

**Never commit any of these.** `credentials/` is git-ignored.

| Credential | Where it goes |
| --- | --- |
| Expo access token | the `EXPO_TOKEN` environment variable |
| Google Play service account JSON | `credentials/play-service-account.json` |
| Apple ID | the `EXPO_APPLE_ID` environment variable |
| App Store Connect app ID | the `EXPO_ASC_APP_ID` environment variable |
| Apple Team ID | the `EXPO_APPLE_TEAM_ID` environment variable |

`eas.json` refers to each of these by name. No key is stored in this repository.

## 4. Build and submit

```bash
npm install -g eas-cli
eas login
eas build:configure          # links this app to your Expo project

eas build --platform android --profile production   # produces an .aab for Play
eas build --platform ios --profile production       # produces an .ipa for the App Store

eas submit --platform android --profile production
eas submit --platform ios --profile production
```

`production` sets `autoIncrement`, so the build number rises on every build. A store rejects a
second upload that reuses one.

## 5. Before review

Both stores reject a listing without these, and neither is generated for you:

- a reachable **privacy policy URL** (put it in `store.config.json`)
- store **screenshots** at the sizes each console asks for
- your own **icon and splash** artwork (see `assets/README.md`)

If you add analytics or any data-collecting SDK, extend `assets/PrivacyInfo.xcprivacy` to declare
it, or App Store review will fail.

## 6. Point the app at your real API

`eas.json` has placeholder API URLs per profile (`EXPO_PUBLIC_API_URL`). Set `production` to your
deployed API before building — a store build pointed at `localhost` reaches nothing.
""",
    )


def ci_workflow() -> GeneratedFile:
    return GeneratedFile(
        ".github/workflows/mobile-release.yml",
        """# Builds the mobile app with EAS. Runs only when you ask it to, because a build consumes
# EAS quota. Requires the EXPO_TOKEN secret; without it the job stops with a clear message
# rather than failing halfway through a build.
name: Mobile release

on:
  workflow_dispatch:
    inputs:
      platform:
        description: Platform to build
        required: true
        default: all
        type: choice
        options: [all, android, ios]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - name: Check for the Expo token
        run: |
          if [ -z "${{ secrets.EXPO_TOKEN }}" ]; then
            echo "EXPO_TOKEN is not set. Add it in Settings > Secrets before running this workflow."
            exit 1
          fi
      - run: npm install -g eas-cli
      - working-directory: apps/mobile
        run: npm ci || npm install
      - name: Build
        working-directory: apps/mobile
        env:
          EXPO_TOKEN: ${{ secrets.EXPO_TOKEN }}
        run: eas build --non-interactive --no-wait --platform ${{ inputs.platform }} --profile production
""",
    )


def gitignore() -> GeneratedFile:
    return GeneratedFile(
        ".gitignore",
        "node_modules/\n.expo/\ndist/\n*.tsbuildinfo\n"
        "# Store credentials never belong in a repository.\n"
        "credentials/\n*.keystore\n*.p8\n*.p12\n*.mobileprovision\n"
        ".env\n.env.local\n.env.*.local\n",
    )


def release_files(ir: ApplicationIR, slug: str, identifier: str) -> list[GeneratedFile]:
    """Every file the app needs to be built and submitted, none of them holding a secret."""
    return [
        eas_json(),
        env_example(),
        credentials_readme(),
        privacy_manifest(),
        store_config(ir),
        assets_readme(),
        release_readme(ir, identifier),
        ci_workflow(),
        gitignore(),
        *icon_files(ir.brand, ir.name),
    ]

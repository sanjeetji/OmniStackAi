"""Quality gates that every published template must pass, whichever template it is.

Three templates in a row shipped with apps that rendered invented data instead of calling their
own API, and each needed a follow-up task to become real. These checks apply to the whole
catalogue, so the next template cannot ship the same way.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[3] / "templates" / "catalog"

# Any reference to the template's own API, however its client is shaped: RideNow uses a module
# `api` object, CareClinic a `defaultApiClient`, Bazaar an `api` singleton, and every app may use
# a `useApi` hook or plain fetch.
CLIENT = re.compile(
    r"defaultApiClient\.\w|(?<![\w.])api\.\w+\s*[<(]|useApi|useStream|fetch\s*\("
)

# Pages that legitimately do not call the API: a sign-in screen delegates to a shared form or
# session provider, and a bare redirect has nothing to fetch.
DELEGATES = re.compile(r"signIn\s*\(|AuthForm|router\.replace\(|router\.push\(")


def published_templates() -> list[Path]:
    if not CATALOG.is_dir():
        return []
    return sorted(
        path
        for path in CATALOG.iterdir()
        if path.is_dir() and not path.name.startswith("_") and (path / "template.json").is_file()
    )


def app_pages(app: Path) -> list[tuple[str, Path]]:
    root = app / "app"
    if not root.is_dir():
        return []
    return [
        (page.parent.relative_to(root).as_posix() or "/", page)
        for page in sorted(root.rglob("page.tsx"))
        if "node_modules" not in page.parts and ".next" not in page.parts
    ]


@unittest.skipUnless(published_templates(), "needs at least one published template")
class EveryTemplateTests(unittest.TestCase):
    def test_every_page_reaches_its_api(self) -> None:
        """A page that never calls the API can only be showing invented data."""
        offenders: list[str] = []
        for template in published_templates():
            apps = template / "repo" / "apps"
            if not apps.is_dir():
                continue
            for app in sorted(a for a in apps.iterdir() if a.is_dir()):
                for name, page in app_pages(app):
                    source = page.read_text(encoding="utf-8")
                    if CLIENT.search(source) or DELEGATES.search(source):
                        continue
                    offenders.append(f"{template.name}/{app.name}/{name}")
        self.assertEqual(offenders, [], f"pages that never reach the API: {offenders}")

    def test_no_link_points_at_a_placeholder_id(self) -> None:
        """Links to ids like pat-1 or doc-1 are left over from a mock and 404 for everyone."""
        placeholder = re.compile(r"href=[{\"`]+/[a-z-]+/(?:pat|doc|apt|rx|inv|usr|ord|shp|shop|set)-\d")
        offenders: list[str] = []
        for template in published_templates():
            for source in (template / "repo").rglob("*.tsx"):
                if "node_modules" in source.parts or ".next" in source.parts:
                    continue
                if placeholder.search(source.read_text(encoding="utf-8")):
                    offenders.append(f"{template.name}/{source.relative_to(template / 'repo')}")
        self.assertEqual(offenders, [], f"links to a placeholder id: {offenders}")

    def test_dynamic_segments_are_real_route_folders(self) -> None:
        """A URL-encoded folder ('%5Bid%5D') is a literal path, so the page 404s on a real id."""
        offenders: list[str] = []
        for template in published_templates():
            for path in (template / "repo").rglob("*"):
                if not path.is_dir() or "node_modules" in path.parts or ".next" in path.parts:
                    continue
                if "%5B" in path.name:
                    offenders.append(f"{template.name}/{path.relative_to(template / 'repo')}")
        self.assertEqual(offenders, [], f"URL-encoded dynamic segments: {offenders}")

    def test_no_sign_in_writes_a_fake_token(self) -> None:
        """A sign-in that invents a token never talks to the API, so nothing behind it is real."""
        fake = re.compile(r"""setItem\(\s*["'][\w.]*token["']\s*,\s*["'](?!\$)[\w-]*(mock|demo|fake)""", re.I)
        offenders: list[str] = []
        for template in published_templates():
            for source in (template / "repo").rglob("*.tsx"):
                if "node_modules" in source.parts or ".next" in source.parts:
                    continue
                if fake.search(source.read_text(encoding="utf-8")):
                    offenders.append(f"{template.name}/{source.relative_to(template / 'repo')}")
        self.assertEqual(offenders, [], f"sign-in writes a fabricated token: {offenders}")

    def test_demo_users_can_actually_be_seeded(self) -> None:
        """Every advertised demo login must exist in the template's own seed."""
        offenders: list[str] = []
        for template in published_templates():
            manifest = json.loads((template / "template.json").read_text(encoding="utf-8"))
            seeds = list((template / "repo" / "services" / "api" / "seed").glob("*.sql"))
            if not seeds:
                continue
            seeded = "\n".join(seed.read_text(encoding="utf-8") for seed in seeds)
            for user in manifest.get("demo_users", []):
                if user["email"] not in seeded:
                    offenders.append(f"{template.name}: {user['email']}")
        self.assertEqual(offenders, [], f"advertised demo logins missing from the seed: {offenders}")

    def test_a_one_click_demo_login_uses_a_seeded_account(self) -> None:
        """A login screen pre-filled with an account the seed never creates always fails."""
        offenders: list[str] = []
        # A real address, not a password like "Shopper@2026": the domain must carry a dot and a TLD.
        credential = re.compile(r"""useState\(\s*["']([\w.+-]+@[\w-]+\.[A-Za-z]{2,})["']""")
        for template in published_templates():
            seeds = list((template / "repo" / "services" / "api" / "seed").glob("*.sql"))
            if not seeds:
                continue
            seeded = "\n".join(seed.read_text(encoding="utf-8") for seed in seeds)
            for source in (template / "repo" / "apps").rglob("login/page.tsx"):
                if "node_modules" in source.parts:
                    continue
                for email in credential.findall(source.read_text(encoding="utf-8")):
                    if email not in seeded:
                        offenders.append(f"{template.name}/{source.parent.name}: {email}")
        self.assertEqual(offenders, [], f"demo logins that cannot sign in: {offenders}")

    def test_every_screen_in_the_manifest_has_an_image(self) -> None:
        for template in published_templates():
            manifest = json.loads((template / "template.json").read_text(encoding="utf-8"))
            for screen in manifest.get("screens", []):
                self.assertTrue(
                    (template / screen["image"]).is_file(),
                    f"{template.name}: {screen['image']} is listed but not on disk",
                )
            cover = manifest.get("cover")
            if cover:
                self.assertTrue((template / cover).is_file(), f"{template.name}: cover missing")

    def test_no_dependencies_or_build_output_are_published(self) -> None:
        for template in published_templates():
            for path in (template / "repo").rglob("*"):
                self.assertNotIn(
                    path.name,
                    {"node_modules", ".next", ".turbo"},
                    f"{template.name}: {path} must not be published",
                )


if __name__ == "__main__":
    unittest.main()

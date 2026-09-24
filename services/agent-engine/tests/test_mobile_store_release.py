"""R-546: the generated Expo app can be built and submitted to the stores.

R-545 made it run on a phone. It could not be *built* for a store, and each gap blocks a
submission on its own:

* no `eas.json`, so `eas build` has nothing to read;
* no icon or splash image — only a background colour — so a listing carries Expo's default;
* no `buildNumber`/`versionCode`, so a store refuses a second upload that reuses one;
* no iOS privacy manifest, which Apple has required since spring 2024;
* a bundle identifier under `com.omnistackai.*` — our domain on a user's app, which they cannot
  register, and which both stores bind permanently to a listing on first upload.

Everything is generated offline. The rule these tests hold hardest: **no credential is ever
embedded.** Secrets are referenced by name so the publisher supplies them later.
"""

import base64
import dataclasses
import json
from unittest import TestCase

from omnistackai_agent_engine.application_ir import BrandTokens, example_ir
from omnistackai_agent_engine.codegen import ReactNativeAdapter
from omnistackai_agent_engine.codegen.mobile_release import bundle_identifier, png_bytes

BRAND = "#dc2626"


def _files(brand: str = BRAND) -> dict:
    ir = dataclasses.replace(example_ir("minimal-blog"), brand=BrandTokens(primary_color=brand))
    return {f.path: f for f in ReactNativeAdapter().generate(ir).files()}


class TheBuildConfigurationExists(TestCase):
    def setUp(self) -> None:
        self.files = _files()
        self.eas = json.loads(self.files["eas.json"].content)

    def test_eas_json_is_generated(self) -> None:
        self.assertIn("eas.json", self.files)

    def test_it_has_the_three_profiles_a_publisher_needs(self) -> None:
        self.assertEqual(set(self.eas["build"]), {"development", "preview", "production"})

    def test_production_builds_the_artefacts_each_store_wants(self) -> None:
        """Play takes an app bundle, not an APK; the internal preview profile takes an APK."""
        self.assertEqual(self.eas["build"]["production"]["android"]["buildType"], "app-bundle")
        self.assertEqual(self.eas["build"]["preview"]["android"]["buildType"], "apk")

    def test_production_increments_the_build_number(self) -> None:
        """Without this the second upload to either store is rejected."""
        self.assertTrue(self.eas["build"]["production"]["autoIncrement"])


class NoCredentialIsEverEmbedded(TestCase):
    """The rule that matters most here: a generated repository must never carry a secret."""

    FORBIDDEN = (
        "-----BEGIN",           # any PEM key
        "ghp_", "github_pat_",  # GitHub tokens
        "AIza",                 # Google API keys
        '"private_key"',        # a service-account JSON
    )

    def test_no_generated_file_contains_a_credential(self) -> None:
        for path, generated in _files().items():
            if generated.base64_encoded:
                continue
            for marker in self.FORBIDDEN:
                with self.subTest(path=path, marker=marker):
                    self.assertNotIn(marker, generated.content)

    def test_secrets_are_referenced_by_name_not_value(self) -> None:
        eas = json.loads(_files()["eas.json"].content)
        ios = eas["submit"]["production"]["ios"]
        for value in ios.values():
            self.assertTrue(value.startswith("$"), f"{value} should be an env reference")
        android = eas["submit"]["production"]["android"]
        self.assertTrue(android["serviceAccountKeyPath"].endswith(".json"))
        self.assertIn("credentials/", android["serviceAccountKeyPath"])

    def test_credentials_are_git_ignored(self) -> None:
        ignore = _files()[".gitignore"].content
        for pattern in ("credentials/", "*.keystore", "*.p8", "*.p12", "*.mobileprovision"):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, ignore)


class TheAppIsIdentifiedAsTheUsersOwn(TestCase):
    def test_the_bundle_identifier_is_not_ours(self) -> None:
        """`com.omnistackai.<slug>` put our domain on someone else's app."""
        cfg = json.loads(_files()["app.json"].content)["expo"]
        self.assertNotIn("omnistackai", cfg["ios"]["bundleIdentifier"])
        self.assertNotIn("omnistackai", cfg["android"]["package"])

    def test_ios_and_android_agree(self) -> None:
        cfg = json.loads(_files()["app.json"].content)["expo"]
        self.assertEqual(cfg["ios"]["bundleIdentifier"], cfg["android"]["package"])

    def test_it_is_a_valid_reverse_dns_identifier(self) -> None:
        for slug in ("minimal-blog", "shop", "9lives-app", "a-b-c"):
            with self.subTest(slug=slug):
                identifier = bundle_identifier(slug)
                parts = identifier.split(".")
                self.assertGreaterEqual(len(parts), 2, identifier)
                for part in parts:
                    self.assertTrue(part.isalnum(), identifier)
                    self.assertFalse(part[0].isdigit(), identifier)

    def test_the_release_guide_says_to_change_it_first(self) -> None:
        """Both stores bind an identifier permanently on first upload — this cannot be a footnote."""
        readme = _files()["README-RELEASE.md"].content
        self.assertIn("Change the bundle identifier first", readme)
        # Matched without the line wrap the Markdown introduces.
        self.assertIn("permanently to a listing on first submission", readme)


class TheStoresWillAcceptTheBuild(TestCase):
    def setUp(self) -> None:
        self.files = _files()
        self.cfg = json.loads(self.files["app.json"].content)["expo"]

    def test_a_second_upload_is_possible(self) -> None:
        self.assertIn("buildNumber", self.cfg["ios"])
        self.assertIn("versionCode", self.cfg["android"])

    def test_the_ios_privacy_manifest_exists(self) -> None:
        """Apple has rejected submissions without one since spring 2024."""
        manifest = self.files["assets/PrivacyInfo.xcprivacy"].content
        self.assertIn("NSPrivacyTracking", manifest)
        self.assertIn("NSPrivacyAccessedAPITypes", manifest)

    def test_no_unjustified_permissions_are_requested(self) -> None:
        """Play rejects builds asking for permissions they cannot justify."""
        self.assertEqual(self.cfg["android"]["permissions"], [])

    def test_listing_metadata_is_generated(self) -> None:
        store = json.loads(self.files["store.config.json"].content)
        self.assertEqual(store["name"], example_ir("minimal-blog").name)
        self.assertIn("privacyPolicyUrl", store)

    def test_the_guide_names_what_the_publisher_must_still_supply(self) -> None:
        readme = self.files["README-RELEASE.md"].content
        for needed in ("99 USD", "25 USD", "EXPO_TOKEN", "privacy policy", "screenshots"):
            with self.subTest(needed=needed):
                self.assertIn(needed, readme)


class TheIconsAreRealImages(TestCase):
    def setUp(self) -> None:
        self.files = _files()

    def test_every_icon_expo_references_is_generated(self) -> None:
        cfg = json.loads(self.files["app.json"].content)["expo"]
        referenced = [
            cfg["icon"],
            cfg["splash"]["image"],
            cfg["android"]["adaptiveIcon"]["foregroundImage"],
            cfg["web"]["favicon"],
        ]
        for reference in referenced:
            with self.subTest(reference=reference):
                # A referenced file that does not exist fails the build outright.
                self.assertIn(reference.removeprefix("./"), self.files)

    def test_they_are_valid_pngs_at_the_sizes_expo_expects(self) -> None:
        import struct

        for path, expected in (
            ("assets/icon.png", 1024),
            ("assets/adaptive-icon.png", 1024),
            ("assets/splash.png", 1024),
            ("assets/favicon.png", 48),
        ):
            with self.subTest(path=path):
                data = base64.b64decode(self.files[path].content)
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                width, height = struct.unpack(">II", data[16:24])
                self.assertEqual((width, height), (expected, expected))

    def test_the_icon_carries_the_projects_brand_colour(self) -> None:
        """R-544 extracts the brand from the prompt; the app should be its own colour."""
        red = base64.b64decode(_files("#dc2626")["assets/icon.png"].content)
        green = base64.b64decode(_files("#16a34a")["assets/icon.png"].content)
        self.assertNotEqual(red, green)

    def test_the_splash_background_matches_the_brand(self) -> None:
        cfg = json.loads(self.files["app.json"].content)["expo"]
        self.assertEqual(cfg["splash"]["backgroundColor"], BRAND)

    def test_the_assets_guide_says_they_are_placeholders(self) -> None:
        self.assertIn("Replace", self.files["assets/README.md"].content)

    def test_the_encoder_produces_a_decodable_png(self) -> None:
        data = png_bytes(2, 2, [bytes([255, 0, 0, 0, 255, 0]), bytes([0, 0, 255, 255, 255, 255])])
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertTrue(data.endswith(b"IEND\xae\x42\x60\x82"))


class OutputStaysReproducible(TestCase):
    def test_the_whole_app_is_byte_stable_across_runs(self) -> None:
        first = {p: f.content for p, f in _files().items()}
        second = {p: f.content for p, f in _files().items()}
        self.assertEqual(first, second)


class EveryCredentialHasATemplateEntry(TestCase):
    """R-547: R-546 named the variables and stopped, which left a founder holding an Apple Team ID
    with nowhere obvious to put it and no note on what the value should look like."""

    def setUp(self) -> None:
        self.files = _files()
        self.env = self.files[".env.example"].content

    def test_an_env_template_is_generated(self) -> None:
        self.assertIn(".env.example", self.files)

    def test_every_variable_eas_json_references_is_in_it(self) -> None:
        """A referenced variable with no template entry is one a publisher will not know to set."""
        import re

        eas = self.files["eas.json"].content
        referenced = set(re.findall(r"\$([A-Z][A-Z0-9_]+)", eas))
        self.assertTrue(referenced, "expected eas.json to reference env vars")
        for name in referenced:
            with self.subTest(name=name):
                self.assertIn(name, self.env)

    def test_each_entry_says_where_the_value_comes_from(self) -> None:
        """Naming a variable is not enough — the template has to say where to obtain it."""
        for source in ("expo.dev", "developer.apple.com", "App Store Connect", "Play Console"):
            with self.subTest(source=source):
                self.assertIn(source, self.env + self.files["credentials/README.md"].content)

    def test_the_service_account_file_is_explained(self) -> None:
        guide = self.files["credentials/README.md"].content
        self.assertIn("play-service-account.json", guide)
        self.assertIn("Release manager", guide)
        self.assertIn("git-ignored", guide)

    def test_the_template_holds_no_real_credential(self) -> None:
        """Placeholders are shaped like the real thing; none of them is one."""
        for line in self.env.splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            value = line.split("=", 1)[1].strip()
            with self.subTest(line=line):
                self.assertTrue(value == "" or "example.com" in value, value)

    def test_env_files_are_git_ignored(self) -> None:
        ignore = self.files[".gitignore"].content
        self.assertIn(".env.local", ignore)


class TheDefaultIconLooksDeliberate(TestCase):
    """R-547: a flat coloured plate reads as unfinished. The mark is derived from the app name,
    the way GitHub and GitLab derive default avatars — unique, symmetric, and clearly intentional."""

    def test_two_projects_get_different_marks(self) -> None:
        from omnistackai_agent_engine.codegen.mobile_release import _mark_grid

        self.assertNotEqual(_mark_grid("Minimal Blog"), _mark_grid("Red Bakery Shop"))

    def test_the_same_project_always_gets_the_same_mark(self) -> None:
        from omnistackai_agent_engine.codegen.mobile_release import _mark_grid

        self.assertEqual(_mark_grid("Minimal Blog"), _mark_grid("Minimal Blog"))

    def test_the_mark_is_symmetric(self) -> None:
        """Symmetry is what makes an arbitrary hash read as a design rather than noise."""
        from omnistackai_agent_engine.codegen.mobile_release import _mark_grid

        for name in ("Minimal Blog", "OmniNews", "Salon Booking"):
            with self.subTest(name=name):
                for row in _mark_grid(name):
                    self.assertEqual(row, row[::-1])

    def test_no_mark_is_too_sparse_to_read(self) -> None:
        from omnistackai_agent_engine.codegen.mobile_release import _mark_grid

        for name in ("a", "Minimal Blog", "X", "Zzz", "OmniNews"):
            with self.subTest(name=name):
                grid = _mark_grid(name)
                self.assertGreaterEqual(sum(sum(r) for r in grid), 10, name)

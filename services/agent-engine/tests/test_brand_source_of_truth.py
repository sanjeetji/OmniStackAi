"""R-548: one `brand.json` every generated surface derives from.

Branding was scattered across files that did not know about each other: eleven CSS variables in
`apps/web`, the same eleven again in `apps/admin`, two places in `apps/mobile/app.json`, and the
React Native design tokens — then four PNGs a user could not regenerate at all, because the
generator is Python inside the platform.

The rule this file exists to hold: **the JavaScript derivation and the Python one must agree
exactly.** A project rebranded by its owner has to produce the same palette the platform would
have generated. When first written they differed on five of seven colours, because Python's
`round()` is half-to-even and JavaScript's `Math.round()` is half-up.
"""

import base64
import dataclasses
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase, skipUnless

from omnistackai_agent_engine.application_ir import (
    AdminStrategy,
    BrandTokens,
    MobileProfile,
    example_ir,
)
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.codegen.brand import dark_palette, light_palette, readable_foreground

_NODE = shutil.which("node")
COLOURS = ("#dc2626", "#16a34a", "#0d9488", "#facc15", "#1e3a8a", "#2563eb", "#7c3aed", "#92400e")


def _project(colour: str = "#dc2626") -> dict:
    ir = dataclasses.replace(example_ir("minimal-blog"), brand=BrandTokens(primary_color=colour))
    ir = dataclasses.replace(ir, project_strategy=dataclasses.replace(
        ir.project_strategy, mobile_profile=MobileProfile.REACT_NATIVE, admin_strategy=AdminStrategy.NEXTJS))
    return {f.path: f for f in assemble_project(ir).files()}


class ThereIsOnePlaceToChangeBranding(TestCase):
    def setUp(self) -> None:
        self.files = _project()
        self.brand = json.loads(self.files["brand.json"].content)

    def test_brand_json_is_generated_at_the_repo_root(self) -> None:
        self.assertIn("brand.json", self.files)
        self.assertIn("brand/derive.mjs", self.files)
        self.assertIn("brand/README.md", self.files)

    def test_it_holds_the_inputs_every_surface_needs(self) -> None:
        for field in ("name", "primaryColor", "fontFamily", "borderRadius", "identity"):
            with self.subTest(field=field):
                self.assertIn(field, self.brand)

    def test_it_does_not_store_a_derived_palette(self) -> None:
        """A stored palette goes stale the moment someone edits primaryColor by hand, and a stale
        palette is worse than none because it looks deliberate."""
        serialised = json.dumps(self.brand)
        self.assertNotIn("primary-hover", serialised)
        self.assertNotIn("--color-primary", serialised)

    def test_the_mobile_app_reads_it_rather_than_duplicating_it(self) -> None:
        config = self.files["apps/mobile/app.config.js"].content
        self.assertIn("brand.json", config)
        self.assertIn("name: brand.name", config)
        self.assertIn("backgroundColor: brand.primaryColor", config)

    def test_a_static_app_json_no_longer_competes_with_it(self) -> None:
        """Expo merges app.json and app.config.js with the config winning, so a user editing the
        wrong one sees nothing change and has no way to tell why. Only one is generated."""
        self.assertNotIn("apps/mobile/app.json", self.files)

    def test_the_web_stylesheet_carries_the_colour_brand_json_declares(self) -> None:
        for colour in ("#dc2626", "#16a34a"):
            with self.subTest(colour=colour):
                files = _project(colour)
                brand = json.loads(files["brand.json"].content)
                css = files["apps/web/styles/tokens.css"].content
                self.assertEqual(brand["primaryColor"], colour)
                self.assertIn(colour, css)

    def test_the_admin_console_agrees_with_the_web_app(self) -> None:
        self.assertEqual(
            self.files["apps/web/styles/tokens.css"].content,
            self.files["apps/admin/styles/tokens.css"].content,
        )

    def test_the_identifier_is_marked_permanent(self) -> None:
        """The one irreversible decision in publishing has to be stated where it is made."""
        identity = self.brand["identity"]
        self.assertIn("bundleId", identity)
        self.assertIs(identity["published"], False)
        self.assertIn("PERMANENT", " ".join(identity["$comment"]))


@skipUnless(_NODE, "node is required to run the generated derivation")
class TheTwoDerivationsAgree(TestCase):
    """The gate. Five of seven colours differed when this was first written."""

    def _js_palettes(self, colours: tuple[str, ...]) -> dict:
        files = _project()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "derive.mjs").write_text(files["brand/derive.mjs"].content, encoding="utf-8")
            (root / "check.mjs").write_text(
                "import { lightPalette, darkPalette, readableOn } from './derive.mjs';\n"
                f"const colours = {json.dumps(list(colours))};\n"
                "const out = {};\n"
                "for (const c of colours) out[c] = "
                "{ light: lightPalette(c), dark: darkPalette(c), fg: readableOn(c) };\n"
                "console.log(JSON.stringify(out));\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [_NODE, str(root / "check.mjs")], capture_output=True, text=True, check=True
            )
        return json.loads(result.stdout)

    def test_the_palettes_match_exactly(self) -> None:
        js = self._js_palettes(COLOURS)
        for colour in COLOURS:
            with self.subTest(colour=colour):
                self.assertEqual(js[colour]["light"], light_palette(colour))
                self.assertEqual(js[colour]["dark"], dark_palette(colour))
                self.assertEqual(js[colour]["fg"], readable_foreground(colour))

    def test_a_light_brand_gets_readable_text_in_both(self) -> None:
        """A yellow brand with white button text is an accessibility failure, not a taste call."""
        js = self._js_palettes(("#facc15",))
        self.assertEqual(js["#facc15"]["fg"], "#0f172a")
        self.assertEqual(readable_foreground("#facc15"), "#0f172a")

    def test_the_generated_config_parses_and_uses_brand_json(self) -> None:
        """`app.config.js` is executed by Expo at every start; a syntax error breaks the app."""
        files = _project("#16a34a")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "brand.json").write_text(files["brand.json"].content, encoding="utf-8")
            mobile = root / "apps" / "mobile"
            mobile.mkdir(parents=True)
            (mobile / "app.config.js").write_text(
                files["apps/mobile/app.config.js"].content, encoding="utf-8"
            )
            result = subprocess.run(
                [_NODE, "-e",
                 "const c = require(process.argv[1])(); "
                 "console.log(JSON.stringify(c.expo));",
                 str(mobile / "app.config.js")],
                capture_output=True, text=True, check=True,
            )
        expo = json.loads(result.stdout)
        self.assertEqual(expo["splash"]["backgroundColor"], "#16a34a")
        self.assertEqual(expo["ios"]["bundleIdentifier"], expo["android"]["package"])
        self.assertNotIn("omnistackai", expo["ios"]["bundleIdentifier"])


class TheBrandReachesTheWebApps(TestCase):
    """R-549: CSS cannot read JSON at runtime, so a Next.js app derives the palette at build time.

    Without this, editing brand.json moved the mobile app and left the web app and admin console
    behind — the half-connected state that is worse than not having the feature.
    """

    def setUp(self) -> None:
        self.files = _project("#16a34a")

    def test_both_web_apps_get_the_bridge(self) -> None:
        self.assertIn("apps/web/lib/brand.ts", self.files)
        self.assertIn("apps/admin/lib/brand.ts", self.files)

    def test_the_layout_emits_the_derived_brand(self) -> None:
        for app in ("web", "admin"):
            with self.subTest(app=app):
                layout = self.files[f"apps/{app}/app/layout.tsx"].content
                self.assertIn('from "@/lib/brand"', layout)
                self.assertIn("brandCss()", layout)

    def test_the_bridge_uses_the_same_derivation_as_the_mobile_app(self) -> None:
        """Two derivations would mean the phone and the web app showing different greens."""
        bridge = self.files["apps/web/lib/brand.ts"].content
        self.assertIn("brand/derive.mjs", bridge)
        self.assertIn("brand.json", bridge)

    def test_a_regeneration_script_is_provided_for_what_cannot_be_derived(self) -> None:
        self.assertIn("brand/generate.mjs", self.files)
        scripts = json.loads(self.files["package.json"].content)["scripts"]
        self.assertEqual(scripts["brand"], "node brand/generate.mjs")


class GeneratedIconsAreMarkedAsOurs(TestCase):
    """R-549: `pnpm run brand` must never overwrite artwork a user supplied. Losing somebody's logo
    to a rebuild is a far worse failure than a stale icon."""

    def test_every_generated_icon_carries_the_marker(self) -> None:
        """Without the marker every fresh project's icons look user-supplied, and the regenerator
        silently never updates any of them — which is exactly what happened first time."""
        from omnistackai_agent_engine.codegen.mobile_release import GENERATED_ICON_MARKER

        files = _project()
        for path, generated in files.items():
            if path.endswith(".png"):
                with self.subTest(path=path):
                    data = base64.b64decode(generated.content)
                    self.assertIn(GENERATED_ICON_MARKER.encode(), data)

    def test_the_two_generators_agree_on_the_marker(self) -> None:
        """They are in different languages; a typo in either makes the protection silently inert."""
        from omnistackai_agent_engine.codegen.mobile_release import GENERATED_ICON_MARKER

        script = _project()["brand/generate.mjs"].content
        self.assertIn(f"const MARKER = '{GENERATED_ICON_MARKER}'", script)


class BinaryFilesSurviveAssembly(TestCase):
    def test_an_icon_is_still_binary_after_being_placed_in_the_monorepo(self) -> None:
        """R-549: `_prefixed` rebuilt each file without `base64_encoded`, so every icon became a
        text file the moment it moved into apps/mobile/. The adapter's own tests passed because
        they never went through assembly."""
        files = _project()
        icon = files["apps/mobile/assets/icon.png"]
        self.assertTrue(icon.base64_encoded, "the icon lost its binary flag during assembly")
        self.assertEqual(base64.b64decode(icon.content)[:8], b"\x89PNG\r\n\x1a\n")


class OnlyTheIdentifierIsRefused(TestCase):
    """R-550: the one irreversible decision in publishing, and only that one.

    Apple ties the bundle identifier to the App Store Connect record; Google Play uses it as the
    listing's primary key and never lets one be reused. Changing it after publication does not
    update the app — it makes a different one, with no reviews and no update path for existing
    users. Icon, colours, font and display name can all change in an update, so blocking those
    would be wrong and would teach a user to ignore the tool.
    """

    def setUp(self) -> None:
        self.files = _project()
        self.brand = json.loads(self.files["brand.json"].content)

    def test_the_published_identifier_is_recorded_separately(self) -> None:
        """A lone `published: true` cannot tell anyone whether the identifier beside it still is
        the one the stores know."""
        identity = self.brand["identity"]
        self.assertIn("publishedBundleId", identity)
        self.assertIsNone(identity["publishedBundleId"])

    def test_a_check_script_is_generated_and_wired_in(self) -> None:
        self.assertIn("brand/check.mjs", self.files)
        scripts = json.loads(self.files["package.json"].content)["scripts"]
        self.assertEqual(scripts["brand:check"], "node brand/check.mjs")
        # Regenerating from a brand.json that cannot be shipped helps nobody.
        self.assertIn("check.mjs", self.files["brand/generate.mjs"].content)

    def test_the_refusal_explains_itself(self) -> None:
        check = self.files["brand/check.mjs"].content
        for phrase in ("App Store", "Google Play", "no reviews", "Restore it to"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, check)

    def test_what_is_still_allowed_is_stated_too(self) -> None:
        """Saying what a user *can* still change matters as much as the refusal."""
        check = self.files["brand/check.mjs"].content
        self.assertIn("icon, colours, font or display name is fine", check)
        self.assertIn("buildNumber", check)


class TheChatAgentKnowsWhereBrandingLives(TestCase):
    def test_a_branding_request_selects_brand_json(self) -> None:
        """"make it green" names no file; ranking by word overlap would never find it."""
        from omnistackai_agent_engine.studio.code_edit import pick_files_by_name

        paths = ["brand.json", "apps/web/app/page.tsx", "apps/web/styles/tokens.css"]
        for prompt in ("make it green", "change the logo", "rename the app to Bakery"):
            with self.subTest(prompt=prompt):
                self.assertEqual(pick_files_by_name(prompt, paths)[0], "brand.json")

    def test_an_unrelated_request_does_not(self) -> None:
        from omnistackai_agent_engine.studio.code_edit import pick_files_by_name

        paths = ["brand.json", "apps/web/app/page.tsx"]
        self.assertNotIn("brand.json", pick_files_by_name("add a waitlist to the booking screen", paths))

    def test_the_agent_refuses_to_change_a_published_identifier(self) -> None:
        import tempfile
        from pathlib import Path

        from omnistackai_agent_engine.studio.code_edit import published_identity_violation

        root = Path(tempfile.mkdtemp())
        (root / "brand.json").write_text(json.dumps({
            "identity": {"bundleId": "com.mine.app", "published": True, "publishedBundleId": "com.mine.app"}
        }), encoding="utf-8")
        proposed = json.dumps({
            "identity": {"bundleId": "com.someoneelse.app", "published": True, "publishedBundleId": "com.mine.app"}
        })
        violation = published_identity_violation(root, {"brand.json": proposed})
        self.assertIsNotNone(violation)
        self.assertIn("com.mine.app", violation)
        self.assertIn("no update path", violation)

    def test_it_allows_everything_else(self) -> None:
        import tempfile
        from pathlib import Path

        from omnistackai_agent_engine.studio.code_edit import published_identity_violation

        root = Path(tempfile.mkdtemp())
        (root / "brand.json").write_text(json.dumps({
            "identity": {"bundleId": "com.mine.app", "published": True, "publishedBundleId": "com.mine.app"}
        }), encoding="utf-8")
        recoloured = json.dumps({
            "primaryColor": "#7c3aed", "name": "Renamed",
            "identity": {"bundleId": "com.mine.app", "published": True, "publishedBundleId": "com.mine.app"},
        })
        self.assertIsNone(published_identity_violation(root, {"brand.json": recoloured}))

    def test_an_unpublished_project_may_change_its_identifier(self) -> None:
        import tempfile
        from pathlib import Path

        from omnistackai_agent_engine.studio.code_edit import published_identity_violation

        root = Path(tempfile.mkdtemp())
        (root / "brand.json").write_text(json.dumps({
            "identity": {"bundleId": "com.mine.app", "published": False, "publishedBundleId": None}
        }), encoding="utf-8")
        proposed = json.dumps({"identity": {"bundleId": "com.yourco.app", "published": False}})
        self.assertIsNone(published_identity_violation(root, {"brand.json": proposed}))

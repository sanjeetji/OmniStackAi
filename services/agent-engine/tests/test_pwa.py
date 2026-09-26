"""R-573: every generated web app and admin console is an installable PWA with a QR code.

Proven live on 2026-09-26: a generated app built with `next build`, served with `next start` and
opened in headless Google Chrome reported **no installability errors**, an activated service
worker, the "Get the app" control with its QR code, and the offline page when the network was cut.
"""

import base64
import struct
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ProjectStrategy, WebStrategy, example_ir
from omnistackai_agent_engine.codegen.capabilities import resolve_stack
from omnistackai_agent_engine.codegen.nextjs import NextjsAdminAdapter, NextjsWebAdapter
from omnistackai_agent_engine.codegen.pwa import SERVICE_WORKER

IR = example_ir("minimal-blog")
PROJECT = NextjsWebAdapter().generate(IR)


def _png_size(generated) -> tuple[int, int]:
    data = base64.b64decode(generated.content)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


class TheAppIsInstallable(TestCase):
    def test_a_manifest_with_the_brand_and_png_icons(self) -> None:
        manifest = PROJECT.get("app/manifest.ts").content
        self.assertIn('display: "standalone"', manifest)
        self.assertIn(f'theme_color: "{IR.brand.primary_color}"', manifest)
        for icon in ("icon-192.png", "icon-512.png", "maskable-512.png"):
            self.assertIn(icon, manifest)
        self.assertIn('purpose: "maskable"', manifest)

    def test_icons_are_real_pngs_at_the_sizes_browsers_ask_for(self) -> None:
        self.assertEqual(_png_size(PROJECT.get("public/icons/icon-192.png")), (192, 192))
        self.assertEqual(_png_size(PROJECT.get("public/icons/icon-512.png")), (512, 512))
        self.assertEqual(_png_size(PROJECT.get("public/icons/maskable-512.png")), (512, 512))
        self.assertEqual(_png_size(PROJECT.get("public/icons/apple-touch-icon.png")), (180, 180))

    def test_the_layout_wires_it_in(self) -> None:
        layout = PROJECT.get("app/layout.tsx").content
        self.assertIn("<PwaSupport />", layout)
        self.assertIn("appleWebApp: { capable: true", layout)
        self.assertIn("/icons/apple-touch-icon.png", layout)
        self.assertIn(f'export const viewport = {{ themeColor: "{IR.brand.primary_color}" }};', layout)

    def test_the_admin_console_is_installable_too(self) -> None:
        admin = NextjsAdminAdapter().generate(IR)
        self.assertIn("app/manifest.ts", admin.paths())
        self.assertIn("public/sw.js", admin.paths())


class TheServiceWorkerIsHonest(TestCase):
    def test_it_never_answers_the_api_from_cache(self) -> None:
        self.assertIn("if (url.origin !== self.location.origin) return;", SERVICE_WORKER)
        self.assertIn('if (request.method !== "GET") return;', SERVICE_WORKER)
        # Only the build's static files and icons are cached, never arbitrary same-origin responses.
        self.assertIn('url.pathname.includes("/_next/static/") || url.pathname.includes("/icons/")', SERVICE_WORKER)
        self.assertIn("if (!isStatic) return;", SERVICE_WORKER)

    def test_page_loads_go_to_the_network_first(self) -> None:
        self.assertIn("fetch(request).catch(() => caches.match(OFFLINE))", SERVICE_WORKER)
        self.assertIn("public/offline.html", PROJECT.paths())


class APhoneCanOpenIt(TestCase):
    def test_the_widget_shows_a_qr_of_an_address_a_phone_can_reach(self) -> None:
        widget = PROJECT.get("components/pwa-support.tsx").content
        self.assertIn("<QrCode value={qrValue} size={160} />", widget)
        self.assertIn('url.hostname === "localhost" || url.hostname === "127.0.0.1"', widget)
        self.assertIn("NEXT_PUBLIC_LAN_HOST", widget)
        self.assertIn("Add to Home Screen", widget)
        self.assertIn("components/qr-code.tsx", PROJECT.paths())

    def test_the_run_plan_passes_the_lan_host_to_web_apps(self) -> None:
        import inspect

        from omnistackai_agent_engine.localrun import plan

        self.assertIn('("NEXT_PUBLIC_LAN_HOST", web_lan)', inspect.getsource(plan))


class APwaRequestIsHonoured(TestCase):
    def test_no_substitution_note_any_more(self) -> None:
        from dataclasses import replace

        strategy = replace(IR.project_strategy, web_strategy=WebStrategy.PWA)
        resolved = resolve_stack(strategy)
        self.assertEqual(resolved.substitutions, ())
        self.assertEqual(resolved.strategy.web_strategy, WebStrategy.NEXTJS)

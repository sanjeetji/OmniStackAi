"""PC-107: a preview is reported ready only once every page has been compiled.

PC-106 warmed the pages after the preview was reported ready, so a visitor opening a page in that
first minute could meet a dev-server chunk error while another route compiled. The Studio now
reports the preview as starting ("Preparing pages: n of m") until the warm-up is done, bounded so a
slow app is never held for long.
"""

import threading
import time
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.studio.preview import StudioPreviewManager, WorkspacePreviewSession

_REPO = Path(__file__).resolve().parents[3]


class _Warmer(threading.Thread):
    def __init__(self, seconds: float) -> None:
        super().__init__(daemon=True)
        self.seconds, self.total, self.done = seconds, 4, 0

    def run(self) -> None:
        for _ in range(self.total):
            time.sleep(self.seconds / self.total)
            self.done += 1


class _Session:
    def __init__(self, warmer) -> None:
        self.warming = warmer


def _wait(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline and not predicate():
        time.sleep(0.05)
    return predicate()


class ItIsReadyOnlyOnceThePagesAreCompiled(TestCase):
    def _ready_session(self) -> WorkspacePreviewSession:
        return WorkspacePreviewSession("w1", "/tmp/w1/repo", status="ready", phase="ready",
                                       message="The generated web app and admin console are running locally.")

    def test_it_says_preparing_pages_then_becomes_ready(self) -> None:
        manager, ws, warmer = StudioPreviewManager(), self._ready_session(), _Warmer(0.4)
        warmer.start()
        manager._hold_until_warm(ws, _Session(warmer))
        self.assertEqual((ws.status, ws.phase), ("starting", "warm"))
        self.assertTrue(ws.message.startswith("Preparing pages:"))
        self.assertTrue(_wait(lambda: ws.status == "ready"))
        self.assertEqual(ws.phase, "ready")
        self.assertEqual(ws.message, "The generated web app and admin console are running locally.")

    def test_a_slow_warm_up_is_bounded(self) -> None:
        manager, ws, warmer = StudioPreviewManager(), self._ready_session(), _Warmer(30.0)
        manager.WARM_CAP_SECONDS = 0.3
        warmer.start()
        manager._hold_until_warm(ws, _Session(warmer))
        self.assertTrue(_wait(lambda: ws.status == "ready", timeout=3.0), "ready after the cap, warming or not")

    def test_nothing_to_warm_stays_ready_and_a_replaced_preview_is_left_alone(self) -> None:
        manager, ws = StudioPreviewManager(), self._ready_session()
        manager._hold_until_warm(ws, _Session(None))
        self.assertEqual(ws.status, "ready")
        warmer = _Warmer(0.4)
        warmer.start()
        manager._hold_until_warm(ws, _Session(warmer))
        ws.cancelled = True
        time.sleep(0.8)
        self.assertEqual(ws.status, "starting", "a cancelled session is never flipped to ready")

    def test_the_studio_labels_the_phase(self) -> None:
        studio = (_REPO / "apps/console-web/app/studio/studio-preview-apps.tsx").read_text()
        self.assertIn('warm: "Preparing pages"', studio)


class APageLoadMakesOneLookupNotOnePerFile(TestCase):
    """The real cause of the "dev-server" chunk 404s: the console's preview proxy asked the control
    plane (and so the Studio) for the preview on every file of a page; a page's parallel requests
    ran some lookups past the control plane's deadline, and each failure answered 404. Proved live:
    16 parallel asset requests through the console, 2 of 366 failed before, 0 of 610 after."""

    def test_the_proxy_reuses_one_lookup_and_never_turns_an_outage_into_a_404(self) -> None:
        route = (_REPO / "apps/console-web/app/preview/[projectId]/[[...path]]/route.ts").read_text()
        self.assertIn("const PREVIEW_FRESH_MS = 3_000;", route)
        self.assertIn("if (entry?.pending) return entry.pending;", route, "concurrent requests share one lookup")
        self.assertIn("preview = await resolvePreview(token, projectId);", route)
        self.assertIn('{ error: "preview status unavailable, try again" }', route)

    def test_the_control_plane_keeps_connections_to_the_studio_and_its_token(self) -> None:
        auth = (_REPO / "services/control-plane/internal/studioauth/studioauth.go").read_text()
        self.assertIn("base.MaxIdleConnsPerHost = 64", auth)
        self.assertLess(auth.index("base.MaxIdleConnsPerHost = 64"), auth.index("http.DefaultTransport = Wrap("))

    def test_the_dev_server_keeps_every_page_compiled(self) -> None:
        from omnistackai_agent_engine.codegen.nextjs import _NEXT_CONFIG

        self.assertIn("onDemandEntries: { maxInactiveAge: 60 * 60 * 1000, pagesBufferLength: 200 }", _NEXT_CONFIG)

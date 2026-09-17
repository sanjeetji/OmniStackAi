"""Tests for Studio Ecosystem Pack Discovery and Multi-Surface Building (R-445).

Deterministic and offline: tests Studio endpoints for ecosystem packs, recommendation,
multi-surface building, history recording, and UI self-containment with 0 model calls
and 0 network calls.
"""

from __future__ import annotations

import json
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from omnistackai_agent_engine.studio import STUDIO_HTML, create_studio_server
from omnistackai_agent_engine.studio.history import StudioBuildHistory
from omnistackai_agent_engine.studio.live_serve import _build

_VALID_PAGE = '''"use client";
import { useListPosts } from "@/lib/hooks";

export default function Page() {
  const { items, loading } = useListPosts();
  return <main>{loading ? "..." : items.length}</main>;
}
'''


class _StubProvider:
    """Always-succeeding in-memory ModelProvider (R-467: proves hybrid_ui threading with 0 real calls)."""

    provider_id = "stub"

    async def generate(self, request):  # noqa: ANN001
        from types import SimpleNamespace

        return SimpleNamespace(text=_VALID_PAGE)


@contextmanager
def running_server(build_fn, **control_kwargs):
    server = create_studio_server(build_fn, host="127.0.0.1", port=0, **control_kwargs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class TestStudioEcosystem(unittest.TestCase):
    def test_get_ecosystem_packs_endpoint(self) -> None:
        def stub_build(prompt: str, **kwargs) -> dict:
            return {"name": "Test", "prompt": prompt}

        with running_server(stub_build) as base_url:
            req = urllib.request.Request(f"{base_url}/api/ecosystem-packs")
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertIn("ecosystems", data)
                self.assertGreaterEqual(len(data["ecosystems"]), 2)
                eco_ids = [e["ecosystem_id"] for e in data["ecosystems"]]
                self.assertIn("minimal-blog-ecosystem", eco_ids)
                self.assertIn("rideshare-favourites-ecosystem", eco_ids)

    def test_post_ecosystem_packs_recommend_endpoint(self) -> None:
        def stub_build(prompt: str, **kwargs) -> dict:
            return {"name": "Test", "prompt": prompt}

        with running_server(stub_build) as base_url:
            # 1. Recommend by exact domain
            body = json.dumps({"domain": "blog-cms"}).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/ecosystem-packs/recommend",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data["domain"], "blog-cms")
                self.assertEqual(data["recommendation"]["status"], "selected")
                self.assertEqual(data["recommendation"]["ecosystem"]["ecosystem_id"], "minimal-blog-ecosystem")

            # 2. Recommend by prompt classification
            body = json.dumps({"prompt": "Build a rideshare app where passengers book drivers"}).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/ecosystem-packs/recommend",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data["domain"], "rideshare")
                self.assertEqual(data["recommendation"]["status"], "selected")
                self.assertEqual(data["recommendation"]["ecosystem"]["ecosystem_id"], "rideshare-favourites-ecosystem")

            # 3. No match domain
            body = json.dumps({"domain": "unknown-domain"}).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/ecosystem-packs/recommend",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data["recommendation"]["status"], "no-exact-match")

    def test_post_build_with_ecosystem_parameters(self) -> None:
        received_options = {}

        def recording_build(prompt: str, **options) -> dict:
            received_options.update(options)
            return {
                "name": "Ecosystem Surface App",
                "prompt": prompt,
                "ecosystem_id": options.get("ecosystem_id"),
                "surface_slug": options.get("surface_slug"),
            }

        with running_server(recording_build) as base_url:
            body = json.dumps({
                "prompt": "Publish blog articles",
                "ecosystem_id": "minimal-blog-ecosystem",
                "ecosystem_version": "1.0.0",
                "surface_slug": "author-studio",
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/build",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data["ecosystem_id"], "minimal-blog-ecosystem")
                self.assertEqual(data["surface_slug"], "author-studio")

            self.assertEqual(received_options["ecosystem_id"], "minimal-blog-ecosystem")
            self.assertEqual(received_options["ecosystem_version"], "1.0.0")
            self.assertEqual(received_options["surface_slug"], "author-studio")

    def test_live_serve_build_single_surface_from_ecosystem(self) -> None:
        history = StudioBuildHistory()
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            old_out = os.environ.get("OMNISTACKAI_APP_OUT_DIR")
            os.environ["OMNISTACKAI_APP_OUT_DIR"] = tmpdir
            try:
                # R-467: resolve_generation_provider_from_env is real and env-sensitive (it loads .env
                # and can resolve a live cloud provider); mock it so this suite's "0 model calls, 0
                # network calls" claim holds by construction, not by accident of the local environment.
                with patch(
                    "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                    return_value=(None, "stub-model", 4096, 5.0),
                ):
                    payload = _build(
                        "Publish blog articles",
                        ecosystem_id="minimal-blog-ecosystem",
                        ecosystem_version="1.0.0",
                        surface_slug="author-studio",
                        history=history,
                    )
            finally:
                if old_out is None:
                    os.environ.pop("OMNISTACKAI_APP_OUT_DIR", None)
                else:
                    os.environ["OMNISTACKAI_APP_OUT_DIR"] = old_out

            self.assertFalse(payload.get("is_ecosystem"))
            self.assertEqual(payload["ecosystem_id"], "minimal-blog-ecosystem")
            self.assertEqual(payload["surface_slug"], "author-studio")
            self.assertEqual(payload["surface_kind"], "provider_portal")
            self.assertGreater(payload["file_count"], 100)
            self.assertTrue(os.path.isdir(payload["target_dir"]))

            # Verify history was recorded
            recent = history.list()
            self.assertEqual(len(recent["builds"]), 1)
            entry = recent["builds"][0]
            self.assertEqual(entry["ecosystem_id"], "minimal-blog-ecosystem")
            self.assertEqual(entry["surface_slug"], "author-studio")
            self.assertEqual(entry["surface_kind"], "provider_portal")

    def test_live_serve_build_all_surfaces_ecosystem(self) -> None:
        history = StudioBuildHistory()
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            old_out = os.environ.get("OMNISTACKAI_APP_OUT_DIR")
            os.environ["OMNISTACKAI_APP_OUT_DIR"] = tmpdir
            try:
                with patch(
                    "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                    return_value=(None, "stub-model", 4096, 5.0),
                ):
                    payload = _build(
                        "Launch minimal blog platform",
                        ecosystem_id="minimal-blog-ecosystem",
                        ecosystem_version="1.0.0",
                        surface_slug="all",
                        history=history,
                    )
            finally:
                if old_out is None:
                    os.environ.pop("OMNISTACKAI_APP_OUT_DIR", None)
                else:
                    os.environ["OMNISTACKAI_APP_OUT_DIR"] = old_out

            self.assertTrue(payload.get("is_ecosystem"))
            self.assertEqual(payload["ecosystem_id"], "minimal-blog-ecosystem")
            self.assertEqual(payload["surface_count"], 3)
            self.assertEqual(len(payload["surfaces"]), 3)
            self.assertGreater(payload["file_count"], 400)

            # Verify history was recorded
            recent = history.list()
            self.assertEqual(len(recent["builds"]), 1)
            entry = recent["builds"][0]
            self.assertEqual(entry["ecosystem_id"], "minimal-blog-ecosystem")
            self.assertTrue(entry.get("is_ecosystem"))
            self.assertEqual(entry["surface_count"], 3)

    def test_hybrid_ui_threads_synthesize_screens_through_ecosystem_build(self) -> None:
        history = StudioBuildHistory()
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            old_out = os.environ.get("OMNISTACKAI_APP_OUT_DIR")
            os.environ["OMNISTACKAI_APP_OUT_DIR"] = tmpdir
            try:
                with patch(
                    "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                    return_value=(_StubProvider(), "stub-model", 4096, 5.0),
                ):
                    payload = _build(
                        "Publish blog articles",
                        ecosystem_id="minimal-blog-ecosystem",
                        ecosystem_version="1.0.0",
                        surface_slug="author-studio",
                        hybrid_ui=True,
                        history=history,
                    )
            finally:
                if old_out is None:
                    os.environ.pop("OMNISTACKAI_APP_OUT_DIR", None)
                else:
                    os.environ["OMNISTACKAI_APP_OUT_DIR"] = old_out

            self.assertTrue(payload["hybrid_ui_requested"])
            self.assertTrue(payload["hybrid_ui_active"])
            outcomes = payload["ui_outcomes"]
            self.assertTrue(outcomes)
            page_outcome = next(o for o in outcomes if o["path"] == "app/page.tsx")
            self.assertEqual(page_outcome["mode"], "llm")
            page_file = Path(payload["target_dir"]) / "apps" / "web" / "app" / "page.tsx"
            self.assertIn("LLM-Synthesized", page_file.read_text(encoding="utf-8"))
            # It round-trips into history too.
            entry = history.list()["builds"][0]
            self.assertTrue(entry["hybrid_ui_active"])
            self.assertTrue(entry["ui_outcomes"])

    def test_hybrid_ui_without_a_provider_is_reported_as_inactive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            old_out = os.environ.get("OMNISTACKAI_APP_OUT_DIR")
            os.environ["OMNISTACKAI_APP_OUT_DIR"] = tmpdir
            try:
                with patch(
                    "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                    return_value=(None, "stub-model", 4096, 5.0),
                ):
                    payload = _build(
                        "Publish blog articles",
                        ecosystem_id="minimal-blog-ecosystem",
                        ecosystem_version="1.0.0",
                        surface_slug="author-studio",
                        hybrid_ui=True,
                    )
            finally:
                if old_out is None:
                    os.environ.pop("OMNISTACKAI_APP_OUT_DIR", None)
                else:
                    os.environ["OMNISTACKAI_APP_OUT_DIR"] = old_out

            self.assertTrue(payload["hybrid_ui_requested"])
            self.assertFalse(payload["hybrid_ui_active"])
            self.assertNotIn("ui_outcomes", payload)

    def test_solution_pack_build_reports_hybrid_ui_inactive_honestly(self) -> None:
        from omnistackai_agent_engine.studio.live_serve import _target_dir_for  # noqa: F401 (documents intent)

        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "omnistackai_agent_engine.studio.live_serve._target_dir_for",
                return_value=str(Path(tmp) / "blog_app"),
            ), patch(
                "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                return_value=(_StubProvider(), "stub-model", 4096, 5.0),
            ):
                payload = _build("A tech blog", pack_id="minimal-blog", hybrid_ui=True)
            # build_solution_pack_project has no synthesize_screens/ui_outcomes parameter -- the request
            # is reported back honestly as inactive, never silently ignored or guessed at.
            self.assertTrue(payload["hybrid_ui_requested"])
            self.assertFalse(payload["hybrid_ui_active"])
            self.assertNotIn("ui_outcomes", payload)

    def test_studio_html_has_ecosystem_ui_and_zero_external_assets(self) -> None:
        html = STUDIO_HTML
        self.assertIn('id="eco-select"', html)
        self.assertIn('id="surface-select"', html)
        self.assertIn('id="tab-single"', html)
        self.assertIn('id="tab-ecosystem"', html)
        self.assertIn('id="surface-cards"', html)

        # Strictly check for zero external dependencies
        self.assertNotIn('<link rel="stylesheet"', html)
        self.assertNotIn('<script src="http', html)
        self.assertNotIn('<script src="//', html)
        self.assertNotIn('fonts.googleapis.com', html)

        # Check for remote URLs in src or href
        remote_srcs = re.findall(r'src=["\'](https?://[^"\']+)["\']', html)
        self.assertEqual(remote_srcs, [], f"Found external src attributes: {remote_srcs}")
        remote_hrefs = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
        self.assertEqual(remote_hrefs, [], f"Found external href attributes: {remote_hrefs}")


if __name__ == "__main__":
    unittest.main()

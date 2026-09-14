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

from omnistackai_agent_engine.studio import STUDIO_HTML, create_studio_server
from omnistackai_agent_engine.studio.history import StudioBuildHistory
from omnistackai_agent_engine.studio.live_serve import _build


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

"""End-to-end tests for the Studio's follow-up edit loop (studio/live_serve.py::_edit, R-468).

Build -> edit -> a real second git commit on a real temp repo, extending test_edit_loop.py's proven
CommitEditTests pattern. Stub providers throughout; every resolve_generation_provider_from_env call site is
mocked from the start (closing the exact class of live-network gap found in R-467).
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.studio.files import BuildNotFoundError
from omnistackai_agent_engine.studio.history import StudioBuildHistory
from omnistackai_agent_engine.studio.live_serve import _build, _edit
from omnistackai_agent_engine.studio.session import EditNotSupportedError, StudioSessionStore

_VALID_DELTA = json.dumps({
    "entities": [
        {
            "name": "Favorite",
            "fields": [
                {"name": "id", "type": "uuid", "required": True},
                {"name": "post_id", "type": "uuid", "required": True},
            ],
        }
    ],
    "apis": [{"method": "POST", "path": "/favorites", "auth": True}],
    "screens": [{"id": "favorites_list", "role": "reader"}],
    "rationale": "Adds a favorites feature.",
})


class StubProvider:
    """Returns each queued response in order, then repeats the last one (never raises IndexError).

    A build's provider serves two purposes -- the IR JSON for `generate_ir`, then (independently of
    `hybrid_ui`) an always-attempted overview-page synthesis call per R-462 -- so a fixed-size queue would
    make the second call `IndexError`. Repeating the last response keeps that harmless: it isn't valid JSX,
    the validator rejects it, and the page falls back to the deterministic template, same as a real bare
    Ollama account would do without a chat-formatted response.
    """

    provider_id = "stub"

    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self.requests: list = []

    async def generate(self, request):  # noqa: ANN001
        self.requests.append(request)
        if len(self._responses) > 1:
            return SimpleNamespace(text=self._responses.pop(0))
        return SimpleNamespace(text=self._responses[0])


def _git_log_oneline(repo_dir: str) -> list[str]:
    log = subprocess.run(
        ["git", "-C", repo_dir, "log", "--oneline"], capture_output=True, text=True, check=True
    )
    return log.stdout.strip().splitlines()


def _no_provider():
    return patch(
        "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
        return_value=(None, "stub-model", 4096, 5.0),
    )


class EditEndToEndTests(unittest.TestCase):
    def _build_plain_prompt(self, tmp: str, *, history: StudioBuildHistory, session_store: StudioSessionStore) -> dict:
        provider = StubProvider([json.dumps(example_ir("minimal-blog").to_dict())])
        with patch(
            "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
            return_value=(provider, "stub-model", 4096, 5.0),
        ):
            return _build(
                "A tech blog", target_dir=str(Path(tmp) / "blog"), history=history, session_store=session_store
            )

    def test_edit_records_a_second_commit_with_the_new_entitys_files(self) -> None:
        history = StudioBuildHistory()
        session_store = StudioSessionStore()
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._build_plain_prompt(tmp, history=history, session_store=session_store)
            build_id = payload["id"]
            repo_dir = payload["target_dir"]
            self.assertEqual(len(_git_log_oneline(repo_dir)), 1)

            with patch(
                "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                return_value=(StubProvider([_VALID_DELTA]), "stub-model", 4096, 5.0),
            ):
                result = asyncio.run(
                    _edit(build_id, "add a favorites feature", history=history, session_store=session_store)
                )

            self.assertIn("Favorite", result["entities"])
            self.assertGreater(len(result["diff"]["added"]), 0)
            self.assertEqual(result["rationale"], "Adds a favorites feature.")

            # A real second commit landed on the real repo.
            log = _git_log_oneline(repo_dir)
            self.assertEqual(len(log), 2)
            self.assertIn("edit: add a favorites feature", log[0])

            # The working tree actually contains the new entity's files (not just the diff record).
            web_dir = Path(repo_dir) / "apps" / "web"
            self.assertTrue((web_dir / "app" / "favorites_list" / "page.tsx").is_file())
            self.assertTrue((web_dir / "app" / "favorites" / "route.ts").is_file())

            # StudioBuildHistory's entry was updated in place, not appended as a new entry.
            self.assertEqual(len(history.list()["builds"]), 1)
            entry = history.get(build_id)
            self.assertIn("Favorite", entry["entities"])
            self.assertEqual(entry["commit_sha"], result["commit_sha"])
            self.assertGreater(entry["file_count"], payload["file_count"])

            # Turns were recorded: a user turn and an assistant summary turn.
            self.assertEqual([t["role"] for t in result["turns"]], ["user", "assistant"])
            self.assertEqual(result["turns"][0]["text"], "add a favorites feature")

    def test_second_edit_stacks_on_the_first(self) -> None:
        history = StudioBuildHistory()
        session_store = StudioSessionStore()
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._build_plain_prompt(tmp, history=history, session_store=session_store)
            build_id, repo_dir = payload["id"], payload["target_dir"]

            with patch(
                "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                return_value=(StubProvider([_VALID_DELTA]), "stub-model", 4096, 5.0),
            ):
                asyncio.run(_edit(build_id, "add a favorites feature", history=history, session_store=session_store))

            second_delta = json.dumps({
                "entities": [], "screens": [],
                "apis": [{"method": "GET", "path": "/health", "auth": False}],
                "rationale": "Adds a health check.",
            })
            with patch(
                "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                return_value=(StubProvider([second_delta]), "stub-model", 4096, 5.0),
            ):
                result = asyncio.run(_edit(build_id, "add a health check", history=history, session_store=session_store))

            self.assertEqual(len(_git_log_oneline(repo_dir)), 3)
            self.assertEqual(len(result["turns"]), 4)  # 2 user + 2 assistant turns across both edits
            self.assertIn("Favorite", result["entities"])  # the first edit's entity is still present

    def test_empty_delta_produces_no_commit(self) -> None:
        history = StudioBuildHistory()
        session_store = StudioSessionStore()
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._build_plain_prompt(tmp, history=history, session_store=session_store)
            build_id, repo_dir = payload["id"], payload["target_dir"]
            empty_delta = json.dumps({"entities": [], "apis": [], "screens": [], "rationale": "Nothing to add."})
            with patch(
                "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                return_value=(StubProvider([empty_delta]), "stub-model", 4096, 5.0),
            ):
                result = asyncio.run(_edit(build_id, "do nothing", history=history, session_store=session_store))
            self.assertEqual(len(_git_log_oneline(repo_dir)), 1)  # still just the initial commit
            self.assertEqual(result["diff"]["added"], [])
            self.assertEqual(result["file_count"], payload["file_count"])

    def test_colliding_entity_name_is_rejected_and_makes_no_commit(self) -> None:
        history = StudioBuildHistory()
        session_store = StudioSessionStore()
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._build_plain_prompt(tmp, history=history, session_store=session_store)
            build_id, repo_dir = payload["id"], payload["target_dir"]
            colliding_name = payload["entities"][0]
            colliding_delta = json.dumps({
                "entities": [{
                    "name": colliding_name,
                    "fields": [{"name": "id", "type": "uuid", "required": True}],
                }],
                "apis": [], "screens": [], "rationale": "",
            })
            with patch(
                "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                return_value=(StubProvider([colliding_delta]), "stub-model", 4096, 5.0),
            ):
                with self.assertRaises(Exception):
                    asyncio.run(_edit(build_id, "add a duplicate entity", history=history, session_store=session_store))
            self.assertEqual(len(_git_log_oneline(repo_dir)), 1)  # rejected before any commit
            # The recorded build's entities are exactly what they were before the rejected edit.
            self.assertEqual(history.get(build_id)["entities"], payload["entities"])
            self.assertEqual(
                {e.name for e in session_store.get(build_id).ir.entities},
                {e.name for e in example_ir("minimal-blog").entities},
            )

    def test_unknown_build_id_raises_build_not_found(self) -> None:
        history = StudioBuildHistory()
        session_store = StudioSessionStore()
        with self.assertRaises(BuildNotFoundError):
            asyncio.run(_edit("does-not-exist", "add x", history=history, session_store=session_store))

    def test_solution_pack_build_is_honestly_not_supported(self) -> None:
        history = StudioBuildHistory()
        session_store = StudioSessionStore()
        build_id = history.record({
            "prompt": "a blog", "name": "Blog", "entities": ["Post"], "file_count": 150,
            "target_dir": "/tmp/x", "commit_sha": "a" * 40, "pack_id": "minimal-blog",
        })
        with self.assertRaises(EditNotSupportedError):
            asyncio.run(_edit(build_id, "add x", history=history, session_store=session_store))

    def test_all_surfaces_ecosystem_build_is_honestly_not_supported(self) -> None:
        history = StudioBuildHistory()
        session_store = StudioSessionStore()
        build_id = history.record({
            "prompt": "a platform", "name": "Platform", "entities": ["Post"], "file_count": 400,
            "target_dir": "/tmp/x", "commit_sha": "a" * 40, "is_ecosystem": True, "surface_count": 3,
        })
        with self.assertRaises(EditNotSupportedError):
            asyncio.run(_edit(build_id, "add x", history=history, session_store=session_store))

    def test_single_surface_ecosystem_build_is_editable(self) -> None:
        history = StudioBuildHistory()
        session_store = StudioSessionStore()
        with tempfile.TemporaryDirectory() as tmpdir:
            import os

            old_out = os.environ.get("OMNISTACKAI_APP_OUT_DIR")
            os.environ["OMNISTACKAI_APP_OUT_DIR"] = tmpdir
            try:
                with _no_provider():
                    payload = _build(
                        "Publish blog articles",
                        ecosystem_id="minimal-blog-ecosystem",
                        ecosystem_version="1.0.0",
                        surface_slug="author-studio",
                        history=history,
                        session_store=session_store,
                    )
            finally:
                if old_out is None:
                    os.environ.pop("OMNISTACKAI_APP_OUT_DIR", None)
                else:
                    os.environ["OMNISTACKAI_APP_OUT_DIR"] = old_out

            build_id, repo_dir = payload["id"], payload["target_dir"]
            self.assertIsNotNone(session_store.get(build_id))
            # The "author-studio" surface only declares an "author" role (unlike minimal-blog's
            # author+reader), so this delta uses that role rather than the shared _VALID_DELTA fixture.
            author_role_delta = json.dumps({
                "entities": [{
                    "name": "Favorite",
                    "fields": [
                        {"name": "id", "type": "uuid", "required": True},
                        {"name": "post_id", "type": "uuid", "required": True},
                    ],
                }],
                "apis": [{"method": "POST", "path": "/favorites", "auth": True}],
                "screens": [{"id": "favorites_list", "role": "author"}],
                "rationale": "Adds a favorites feature.",
            })
            with patch(
                "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                return_value=(StubProvider([author_role_delta]), "stub-model", 4096, 5.0),
            ):
                result = asyncio.run(
                    _edit(build_id, "add a favorites feature", history=history, session_store=session_store)
                )
            self.assertIn("Favorite", result["entities"])
            self.assertEqual(len(_git_log_oneline(repo_dir)), 2)

    def test_provider_exception_during_edit_is_never_retried_and_makes_no_commit(self) -> None:
        history = StudioBuildHistory()
        session_store = StudioSessionStore()

        class FailingProvider:
            provider_id = "stub"

            def __init__(self) -> None:
                self.calls = 0

            async def generate(self, request):  # noqa: ANN001
                self.calls += 1
                raise RuntimeError("provider unavailable")

        with tempfile.TemporaryDirectory() as tmp:
            payload = self._build_plain_prompt(tmp, history=history, session_store=session_store)
            build_id, repo_dir = payload["id"], payload["target_dir"]
            failing = FailingProvider()
            with patch(
                "omnistackai_agent_engine.studio.live_serve.resolve_generation_provider_from_env",
                return_value=(failing, "stub-model", 4096, 5.0),
            ):
                with self.assertRaises(RuntimeError):
                    asyncio.run(_edit(build_id, "add x", history=history, session_store=session_store))
            self.assertEqual(failing.calls, 1)
            self.assertEqual(len(_git_log_oneline(repo_dir)), 1)


if __name__ == "__main__":
    unittest.main()

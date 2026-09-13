"""Tests for the Studio build history store (studio/history.py, R-423).

Pure, deterministic, offline: no generated code, Docker, database, package manager, model, or network.
"""

from __future__ import annotations

import json
import unittest

from omnistackai_agent_engine.studio import StudioBuildHistory


def _build(name: str, **extra) -> dict:
    payload = {
        "prompt": f"Build {name}",
        "name": name,
        "entities": ["A", "B"],
        "file_count": 152,
        "target_dir": f"/tmp/{name}",
        "commit_sha": "abc123def4567890",
    }
    payload.update(extra)
    return payload


class TestStudioBuildHistory(unittest.TestCase):
    def test_record_returns_id_and_appears_in_list(self) -> None:
        history = StudioBuildHistory()
        build_id = history.record(_build("Blog"))
        self.assertTrue(build_id)
        builds = history.list()["builds"]
        self.assertEqual(len(builds), 1)
        self.assertEqual(builds[0]["id"], build_id)
        self.assertEqual(builds[0]["name"], "Blog")

    def test_list_is_newest_first(self) -> None:
        history = StudioBuildHistory()
        history.record(_build("One"))
        history.record(_build("Two"))
        history.record(_build("Three"))
        names = [b["name"] for b in history.list()["builds"]]
        self.assertEqual(names, ["Three", "Two", "One"])

    def test_history_is_bounded_to_limit(self) -> None:
        history = StudioBuildHistory(limit=3)
        ids = [history.record(_build(f"App{i}")) for i in range(6)]
        builds = history.list()["builds"]
        self.assertEqual(len(builds), 3)
        # Oldest evicted; newest retained.
        self.assertEqual([b["name"] for b in builds], ["App5", "App4", "App3"])
        self.assertIsNone(history.get(ids[0]))
        self.assertIsNotNone(history.get(ids[5]))

    def test_get_by_id(self) -> None:
        history = StudioBuildHistory()
        build_id = history.record(_build("Bookstore"))
        entry = history.get(build_id)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["target_dir"], "/tmp/Bookstore")
        self.assertIsNone(history.get("does-not-exist"))

    def test_created_at_uses_injected_clock(self) -> None:
        history = StudioBuildHistory(clock=lambda: 1234.5)
        history.record(_build("Blog"))
        self.assertEqual(history.list()["builds"][0]["created_at"], 1234.5)

    def test_entries_are_bounded_and_secret_free(self) -> None:
        history = StudioBuildHistory()
        history.record(
            _build(
                "Blog",
                prompt="x" * 5000,
                db_password="SUPER-SECRET-PW",
                extra_field={"nested": "SUPER-SECRET-PW"},
            )
        )
        text = json.dumps(history.list())
        self.assertNotIn("SUPER-SECRET-PW", text)
        entry = history.list()["builds"][0]
        self.assertLessEqual(len(entry["prompt"]), 400)
        # Only the known bounded fields are exposed.
        self.assertEqual(
            set(entry),
            {"id", "prompt", "name", "entities", "file_count", "target_dir", "commit_sha", "created_at"},
        )

    def test_list_is_json_serializable(self) -> None:
        history = StudioBuildHistory()
        history.record(_build("Blog"))
        json.dumps(history.list())

    def test_remove_drops_entry_by_id(self) -> None:
        history = StudioBuildHistory()
        keep = history.record(_build("Blog"))
        drop = history.record(_build("Shop"))
        self.assertTrue(history.remove(drop))
        names = [b["name"] for b in history.list()["builds"]]
        self.assertEqual(names, ["Blog"])
        self.assertIsNone(history.get(drop))
        self.assertIsNotNone(history.get(keep))

    def test_remove_unknown_id_is_false_noop(self) -> None:
        history = StudioBuildHistory()
        history.record(_build("Blog"))
        self.assertFalse(history.remove("does-not-exist"))
        self.assertEqual(len(history.list()["builds"]), 1)


if __name__ == "__main__":
    unittest.main()

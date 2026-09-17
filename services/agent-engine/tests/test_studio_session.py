"""Tests for the Studio in-memory edit-session store (studio/session.py, R-468).

Pure, deterministic, offline. The ApplicationIR is server-only state and must never appear in the
JSON-safe views this store exposes.
"""

from __future__ import annotations

import json
import unittest

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.studio.session import StudioSessionStore


class StudioSessionStoreTests(unittest.TestCase):
    def test_begin_then_get_round_trips_the_ir_and_target_dir(self) -> None:
        store = StudioSessionStore()
        ir = example_ir("minimal-blog")
        store.begin("1", ir, "/tmp/app-1")
        entry = store.get("1")
        self.assertIsNotNone(entry)
        self.assertIs(entry.ir, ir)
        self.assertEqual(entry.target_dir, "/tmp/app-1")

    def test_get_unknown_id_is_none(self) -> None:
        store = StudioSessionStore()
        self.assertIsNone(store.get("does-not-exist"))

    def test_advance_replaces_the_current_ir(self) -> None:
        store = StudioSessionStore()
        ir = example_ir("minimal-blog")
        store.begin("1", ir, "/tmp/app-1")
        new_ir = example_ir("rideshare-favourites")
        store.advance("1", new_ir)
        entry = store.get("1")
        self.assertIs(entry.ir, new_ir)
        self.assertEqual(entry.target_dir, "/tmp/app-1")  # unchanged

    def test_advance_unknown_id_is_a_noop(self) -> None:
        store = StudioSessionStore()
        store.advance("does-not-exist", example_ir("minimal-blog"))  # must not raise
        self.assertIsNone(store.get("does-not-exist"))

    def test_record_turn_and_turns_view_are_ordered_and_json_safe(self) -> None:
        store = StudioSessionStore()
        store.begin("1", example_ir("minimal-blog"), "/tmp/app-1")
        store.record_turn("1", "user", "add a favorites feature")
        store.record_turn("1", "assistant", "2 added, 1 modified, 0 deleted, 40 unchanged")
        view = store.turns_view("1")
        json.dumps(view)  # must not raise
        self.assertEqual([t["role"] for t in view["turns"]], ["user", "assistant"])
        self.assertEqual(view["turns"][0]["text"], "add a favorites feature")
        self.assertIn("created_at", view["turns"][0])

    def test_turns_view_never_leaks_the_ir(self) -> None:
        store = StudioSessionStore()
        store.begin("1", example_ir("minimal-blog"), "/tmp/app-1")
        store.record_turn("1", "user", "add a favorites feature")
        text = json.dumps(store.turns_view("1"))
        self.assertNotIn("Application", text)  # no repr of the IR class ever leaks
        self.assertNotIn("/tmp/app-1", text)  # target_dir is server-only too

    def test_turns_view_for_unknown_id_is_an_empty_list_not_an_error(self) -> None:
        store = StudioSessionStore()
        self.assertEqual(store.turns_view("does-not-exist"), {"turns": []})

    def test_record_turn_is_bounded(self) -> None:
        store = StudioSessionStore(max_turns=5)
        store.begin("1", example_ir("minimal-blog"), "/tmp/app-1")
        for i in range(10):
            store.record_turn("1", "user", f"turn {i}")
        view = store.turns_view("1")
        self.assertEqual(len(view["turns"]), 5)
        # Oldest turns evicted; newest kept, in order.
        self.assertEqual([t["text"] for t in view["turns"]], [f"turn {i}" for i in range(5, 10)])

    def test_record_turn_rejects_an_unknown_role(self) -> None:
        store = StudioSessionStore()
        store.begin("1", example_ir("minimal-blog"), "/tmp/app-1")
        with self.assertRaises(ValueError):
            store.record_turn("1", "system-admin", "nope")

    def test_record_turn_on_unknown_id_is_a_noop(self) -> None:
        store = StudioSessionStore()
        store.record_turn("does-not-exist", "user", "hello")  # must not raise
        self.assertEqual(store.turns_view("does-not-exist"), {"turns": []})

    def test_store_is_bounded_and_evicts_the_oldest_touched_session(self) -> None:
        store = StudioSessionStore(limit=3)
        ir = example_ir("minimal-blog")
        for i in range(3):
            store.begin(str(i), ir, f"/tmp/app-{i}")
        store.begin("3", ir, "/tmp/app-3")  # evicts "0", the oldest
        self.assertIsNone(store.get("0"))
        for i in (1, 2, 3):
            self.assertIsNotNone(store.get(str(i)))

    def test_touching_a_session_keeps_it_from_being_evicted(self) -> None:
        store = StudioSessionStore(limit=3)
        ir = example_ir("minimal-blog")
        store.begin("0", ir, "/tmp/app-0")
        store.begin("1", ir, "/tmp/app-1")
        store.begin("2", ir, "/tmp/app-2")
        store.advance("0", ir)  # touches "0" -> now most-recently-used
        store.begin("3", ir, "/tmp/app-3")  # evicts "1", the actual oldest-touched
        self.assertIsNotNone(store.get("0"))
        self.assertIsNone(store.get("1"))
        self.assertIsNotNone(store.get("2"))
        self.assertIsNotNone(store.get("3"))

    def test_begin_on_an_existing_id_replaces_its_session(self) -> None:
        store = StudioSessionStore()
        ir = example_ir("minimal-blog")
        store.begin("1", ir, "/tmp/app-1")
        store.record_turn("1", "user", "first")
        new_ir = example_ir("rideshare-favourites")
        store.begin("1", new_ir, "/tmp/app-1-v2")
        entry = store.get("1")
        self.assertIs(entry.ir, new_ir)
        self.assertEqual(entry.target_dir, "/tmp/app-1-v2")
        self.assertEqual(store.turns_view("1"), {"turns": []})  # a fresh session, not appended history


if __name__ == "__main__":
    unittest.main()

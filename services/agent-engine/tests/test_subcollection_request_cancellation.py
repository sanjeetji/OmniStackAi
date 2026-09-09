"""R-286: generated LIST_BY hooks cancel superseded subcollection requests."""

from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import render_hooks

from test_subcollection_field_filter_wiring import _ir as filterable_subcollection_ir


def _hook_section(hooks: str, name: str) -> str:
    return hooks.split(f"export function {name}(", 1)[1].split("\n}\n", 1)[0]


class SubcollectionCancellationTests(TestCase):
    def test_nonfilterable_hook_aborts_before_empty_parent_reset(self) -> None:
        hook = _hook_section(render_hooks(example_ir("minimal-blog")), "useListCommentsByPost")
        abort_index = hook.index("abortRef.current?.abort();")
        empty_parent_index = hook.index("if (!postId) {")
        controller_index = hook.index("const controller = new AbortController();")

        self.assertIn("const abortRef = useRef<AbortController | null>(null);", hook)
        self.assertLess(abort_index, empty_parent_index)
        self.assertLess(empty_parent_index, controller_index)

    def test_nonfilterable_request_uses_non_overridable_internal_signal(self) -> None:
        hook = _hook_section(render_hooks(example_ir("minimal-blog")), "useListCommentsByPost")
        self.assertIn(
            "api.listCommentsByPostWithCount(postId, { params, ...options, signal: controller.signal });",
            hook,
        )

    def test_filterable_request_preserves_flattened_params_and_internal_signal(self) -> None:
        hook = _hook_section(render_hooks(filterable_subcollection_ir()), "useListTasksByProject")
        self.assertIn("const requestParams = { ...baseParams, ...(filters ?? {}) };", hook)
        self.assertIn(
            "api.listTasksByProjectWithCount(projectId, { params: requestParams, ...options, signal: controller.signal });",
            hook,
        )

    def test_aborted_completion_cannot_mutate_current_state(self) -> None:
        hook = _hook_section(render_hooks(example_ir("minimal-blog")), "useListCommentsByPost")
        success_guard = hook.index("if (controller.signal.aborted) return;")
        self.assertLess(success_guard, hook.index("setData(res.data);"))
        self.assertLess(success_guard, hook.index("setTotal(res.total);"))
        self.assertIn(
            'if (controller.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) return;',
            hook,
        )
        self.assertIn("if (!controller.signal.aborted) setLoading(false);", hook)

    def test_effect_cleanup_aborts_current_request(self) -> None:
        hook = _hook_section(render_hooks(example_ir("minimal-blog")), "useListCommentsByPost")
        self.assertIn("return () => abortRef.current?.abort();", hook)

    def test_description_only_changes_are_byte_stable(self) -> None:
        first = filterable_subcollection_ir("First")
        second = filterable_subcollection_ir("Second")
        self.assertEqual(render_hooks(first), render_hooks(second))


if __name__ == "__main__":
    import unittest

    unittest.main()

"""Generated Next.js TSX must use valid JSX inline styles (R-427).

A JSX inline style is `style={{ ... }}` (double braces: the JSX expression container plus the object
literal). A single-brace `style={ ... }` is a syntax error that makes the generated app fail to compile
(HTTP 500). Several f-string templates in codegen/nextjs.py previously collapsed `{{ }}` to `{ }`.
This deterministic test generates real projects and forbids any single-brace inline style in the output.
"""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import NextjsWebAdapter

# The bug: a bare object literal in a single brace -> `style={ key: ... }` (JSX needs `style={{ ... }}`).
# A single-brace expression style like `style={someVar}` or `style={cond ? a : b}` is valid and NOT matched.
_SINGLE_BRACE_STYLE = re.compile(r"style=\{ [A-Za-z_$][\w$]*\s*:")


class TestGeneratedScreenStyles(unittest.TestCase):
    def _generated_tsx(self, example: str) -> dict[str, str]:
        project = NextjsWebAdapter().generate(example_ir(example))
        return {f.path: f.content for f in project.files() if f.path.endswith(".tsx")}

    def _assert_no_single_brace_styles(self, example: str) -> None:
        offenders: list[str] = []
        for path, content in self._generated_tsx(example).items():
            for match in _SINGLE_BRACE_STYLE.finditer(content):
                line = content[: match.start()].count("\n") + 1
                offenders.append(f"{path}:{line}")
        self.assertEqual(offenders, [], f"single-brace JSX styles in {example}: {offenders[:12]}")

    def test_minimal_blog_has_valid_inline_styles(self) -> None:
        self._assert_no_single_brace_styles("minimal-blog")

    def test_rideshare_favourites_has_valid_inline_styles(self) -> None:
        self._assert_no_single_brace_styles("rideshare-favourites")

    def test_screen_files_are_actually_generated(self) -> None:
        # Guard: the check above is only meaningful if screen pages exist in the output.
        tsx = self._generated_tsx("minimal-blog")
        self.assertTrue(any("/page.tsx" in path for path in tsx))


if __name__ == "__main__":
    unittest.main()

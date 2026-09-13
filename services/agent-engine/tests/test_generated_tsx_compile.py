"""Generated Next.js TSX must be free of the compile-breaking bugs R-428 fixed.

`task verify` never compiles the generated TSX, so these deterministic pattern checks guard the
run-blocking classes found by running a generated app through `tsc`/`next dev`:
  * over-braced arrow bodies in event handlers (`=> {{`), which are a JSX syntax error;
  * component/lib imports written as depth-relative `../components/` / `../lib/` (they break in nested
    screen pages) instead of the depth-independent `@/` path alias;
  * a literal backslash-n leaking into code from a raw-string join.
The opt-in `task agent-engine:web-typecheck` gate runs the real compiler for full coverage.
"""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import NextjsWebAdapter

_OVER_BRACED_HANDLER = re.compile(r"=>\s*\{\{")  # arrow body must open with a single brace
_RELATIVE_APP_IMPORT = re.compile(r'from\s+["\']\.\./(components|lib)/')  # must be `@/...` instead
_LITERAL_BACKSLASH_N = re.compile(r"\);\\n")  # `);\n` (literal) from a raw-string join bug

_EXAMPLES = ("minimal-blog", "rideshare-favourites")


class TestGeneratedTsxCompile(unittest.TestCase):
    def _tsx(self, example: str) -> dict[str, str]:
        project = NextjsWebAdapter().generate(example_ir(example))
        return {f.path: f.content for f in project.files() if f.path.endswith((".tsx", ".ts"))}

    def _assert_none(self, pattern: re.Pattern, label: str) -> None:
        offenders: list[str] = []
        for example in _EXAMPLES:
            for path, content in self._tsx(example).items():
                for match in pattern.finditer(content):
                    line = content[: match.start()].count("\n") + 1
                    offenders.append(f"{example}:{path}:{line}")
        self.assertEqual(offenders, [], f"{label}: {offenders[:12]}")

    def test_no_over_braced_event_handlers(self) -> None:
        self._assert_none(_OVER_BRACED_HANDLER, "over-braced arrow handler (=> {{)")

    def test_screens_use_path_alias_not_relative_imports(self) -> None:
        self._assert_none(_RELATIVE_APP_IMPORT, "depth-relative ../components|../lib import (use @/)")

    def test_no_literal_backslash_n_in_code(self) -> None:
        self._assert_none(_LITERAL_BACKSLASH_N, "literal backslash-n from a raw-string join")


if __name__ == "__main__":
    unittest.main()

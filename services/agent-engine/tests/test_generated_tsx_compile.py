"""Generated Next.js output must be free of the compile-breaking bugs R-428/R-429 fixed.

`task verify` never compiles the generated TSX, so these deterministic pattern checks guard the
strict-type and run-blocking classes found by running a generated app through `tsc`/`next dev`.

R-428 (run-blocking):
  * over-braced arrow bodies in event handlers (`=> {{`), which are a JSX syntax error;
  * component/lib imports written as depth-relative `../components/` / `../lib/` (they break in nested
    screen pages) instead of the depth-independent `@/` path alias;
  * a literal backslash-n leaking into code from a raw-string join.

R-429 (strict-type cleanup, so a generated app passes `tsc --noEmit`):
  * generated `tsconfig.json` must set `skipLibCheck` (Next.js's own default);
  * no name may be both `export const/function X` AND re-listed in an `export { X }` block (TS2323/2484);
  * DOM/SVG element ref annotations must be `React.RefObject<T>`, never `<T | null>` (TS2322 vs `ref=`);
  * every `api.<method>(` a generated hook calls must exist on the exported `api` object (TS2339/2551).

The opt-in `task agent-engine:web-typecheck` gate runs the real compiler for full coverage.
"""

from __future__ import annotations

import json
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import NextjsWebAdapter

_OVER_BRACED_HANDLER = re.compile(r"=>\s*\{\{")  # arrow body must open with a single brace
_RELATIVE_APP_IMPORT = re.compile(r'from\s+["\']\.\./(components|lib)/')  # must be `@/...` instead
_LITERAL_BACKSLASH_N = re.compile(r"\);\\n")  # `);\n` (literal) from a raw-string join bug
# R-429: element ref annotations must not carry `| null` (breaks assignment to a JSX `ref=`).
_NULLABLE_ELEMENT_REF = re.compile(r"React\.RefObject<(?:HTML|SVG)[A-Za-z]+ \| null>")
_EXPORT_BLOCK = re.compile(r"export\s*\{([^}]*)\}")  # `export { A, B, ... }`
_API_CALL = re.compile(r"\bapi\.([A-Za-z_$][\w$]*)\s*\(")  # `api.listPostsWithCount(`

_EXAMPLES = ("minimal-blog", "rideshare-favourites")


class TestGeneratedTsxCompile(unittest.TestCase):
    def _project_files(self, example: str) -> dict[str, str]:
        project = NextjsWebAdapter().generate(example_ir(example))
        return {f.path: f.content for f in project.files()}

    def _tsx(self, example: str) -> dict[str, str]:
        return {p: c for p, c in self._project_files(example).items() if p.endswith((".tsx", ".ts"))}

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

    def test_no_nullable_element_ref_annotations(self) -> None:
        # R-429 (G5): React.RefObject<HTMLxxx | null> is not assignable to a JSX `ref=`.
        self._assert_none(_NULLABLE_ELEMENT_REF, "nullable element ref annotation (drop `| null`)")

    def test_tsconfig_sets_skip_lib_check(self) -> None:
        # R-429 (G0): without skipLibCheck, dependency .d.ts type errors fail `tsc --noEmit`.
        for example in _EXAMPLES:
            tsconfig = self._project_files(example)["tsconfig.json"]
            self.assertIs(
                json.loads(tsconfig)["compilerOptions"].get("skipLibCheck"),
                True,
                f"{example}: tsconfig must set skipLibCheck: true",
            )

    def test_no_duplicate_exports(self) -> None:
        # R-429 (G1): a name declared `export const/function/class X` must NOT also appear in a
        # trailing `export { X }` block (TS2323 "cannot redeclare" / TS2484 "conflicts").
        offenders: list[str] = []
        for example in _EXAMPLES:
            for path, content in self._tsx(example).items():
                declared = set(re.findall(r"export\s+(?:const|function|class)\s+([A-Za-z_$][\w$]*)", content))
                for block in _EXPORT_BLOCK.findall(content):
                    for raw in block.split(","):
                        entry = raw.strip()
                        # `export { X as Y }` re-exports the binding under a new name Y and is valid
                        # even when X is already exported; only a bare re-export of an already-exported
                        # name (`export { X }`) is the TS2323/2484 duplicate.
                        if not entry or " as " in entry:
                            continue
                        if entry in declared:
                            offenders.append(f"{example}:{path}:{entry}")
        self.assertEqual(offenders, [], f"double-exported names (declared + re-listed): {offenders[:12]}")

    def test_hooks_only_call_defined_api_methods(self) -> None:
        # R-429 (G8): every api.<method>() a hook calls must be a key on the exported `api` object.
        for example in _EXAMPLES:
            files = self._project_files(example)
            api_src = files.get("lib/api.ts", "")
            hooks_src = files.get("lib/hooks.ts", "")
            if not api_src or not hooks_src:
                continue
            block = re.search(r"export const api = \{([^}]*)\}", api_src)
            self.assertIsNotNone(block, f"{example}: lib/api.ts must export an `api` object")
            defined = {ln.strip().rstrip(",").split(":")[0].strip() for ln in block.group(1).splitlines() if ln.strip()}
            called = set(_API_CALL.findall(hooks_src))
            missing = sorted(called - defined)
            self.assertEqual(missing, [], f"{example}: hooks call api methods not on the api object: {missing}")


if __name__ == "__main__":
    unittest.main()

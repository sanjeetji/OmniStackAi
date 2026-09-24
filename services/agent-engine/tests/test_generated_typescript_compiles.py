"""R-558: the TypeScript we generate is compiled, not just read.

R-549 shipped `lib/brand.ts` with two `@ts-expect-error` directives over imports that TypeScript
resolves perfectly well. An *unused* suppression is itself an error, so `next build` failed on
every generated web app from that day until this one. Nothing caught it: the tests of that change
asserted on the file's text, and text was exactly what was wrong with it.

That is the third time this pattern has bitten in one sitting -- `_prefixed` dropping
`base64_encoded` (adapter tests skip assembly), the ecosystem branch wired only into the
non-streaming twin the console never calls, and now this. Reading generated source proves it says
what we meant. Only a compiler proves it means anything.

`lib/brand.ts` is checkable without installing a thing: it imports the generated `brand.json` and
the generated `brand/derive.mjs` and nothing else, so `tsc` alone can compile it offline, in about
a second, with no `node_modules` in the generated tree. So it runs in `task verify` rather than in
a lane someone has to remember to run.

The compiler options come from the *generated* `tsconfig.json`, not from a copy pasted here. A
gate that checks different settings than the real build is a gate that passes while the build
breaks -- which is the failure being fixed, wearing a different hat.
"""

import base64
import dataclasses
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase, skipUnless

from omnistackai_agent_engine.application_ir import (
    AdminStrategy,
    BrandTokens,
    example_ir,
)
from omnistackai_agent_engine.codegen.assembler import assemble_project

#: Repo-local, so this stays offline. `None` when the console's dependencies are not installed,
#: which skips the compile half of this file rather than failing it.
_REPO = Path(__file__).resolve().parents[3]
_TSC = _REPO / "apps" / "console-web" / "node_modules" / ".bin" / "tsc"
_HAVE_TSC = _TSC.is_file() and shutil.which("node") is not None


def _project() -> dict:
    ir = dataclasses.replace(
        example_ir("minimal-blog"),
        name="Bakery Shop",
        brand=BrandTokens(primary_color="#dc2626"),
    )
    ir = dataclasses.replace(
        ir,
        project_strategy=dataclasses.replace(
            ir.project_strategy, admin_strategy=AdminStrategy.NEXTJS
        ),
    )
    return {f.path: f for f in assemble_project(ir, prompt="an online store for bread").files()}


def _write(files: dict, root: Path, wanted: tuple[str, ...]) -> None:
    for path in wanted:
        generated = files[path]
        out = root / path
        out.parent.mkdir(parents=True, exist_ok=True)
        if generated.base64_encoded:
            out.write_bytes(base64.b64decode(generated.content))
        else:
            out.write_text(generated.content, encoding="utf-8")


@skipUnless(_HAVE_TSC, "needs the console's local tsc; run `task console:install`")
class GeneratedBrandModuleCompiles(TestCase):
    """The file R-549 broke, compiled with the settings the real build uses."""

    def _typecheck(self, app: str) -> subprocess.CompletedProcess:
        files = _project()
        entry = f"apps/{app}/lib/brand.ts"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(files, root, ("brand.json", "brand/derive.mjs", entry))

            # The real options, minus the two things that need an install: the `next` plugin and
            # `incremental`, which wants a writable build directory.
            config = json.loads(files[f"apps/{app}/tsconfig.json"].content)
            options = {
                k: v
                for k, v in config["compilerOptions"].items()
                if k not in {"plugins", "incremental"}
            }
            options["noEmit"] = True
            (root / "tsconfig.json").write_text(
                json.dumps({"compilerOptions": options, "include": [entry]}), encoding="utf-8"
            )
            return subprocess.run(
                [str(_TSC), "-p", "tsconfig.json"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=180,
            )

    def test_web_brand_module_typechecks(self) -> None:
        result = self._typecheck("web")
        self.assertEqual(result.returncode, 0, f"tsc rejected the generated web brand module:\n{result.stdout}")

    def test_admin_brand_module_typechecks(self) -> None:
        result = self._typecheck("admin")
        self.assertEqual(result.returncode, 0, f"tsc rejected the generated admin brand module:\n{result.stdout}")


class GeneratedTypeScriptCarriesNoSuppressions(TestCase):
    """The cheap half: no `@ts-expect-error` anywhere we generate TypeScript.

    This holds even for the files the compile test above cannot reach, because they import React
    and would need an install. The rule is worth having on its own terms: a suppression in
    generated code is either unnecessary -- in which case it is a hard error, which is precisely
    how this broke -- or it is hiding a type error we should fix rather than silence. A user who
    opens their own generated repo should not find us papering over the compiler in it.
    """

    def test_no_ts_expect_error_in_generated_typescript(self) -> None:
        offenders = [
            path
            for path, f in _project().items()
            if path.endswith((".ts", ".tsx")) and "@ts-expect-error" in f.content
        ]
        self.assertEqual(
            offenders,
            [],
            "generated TypeScript must not suppress the compiler; an unused directive is itself "
            f"a build failure (R-549): {offenders}",
        )

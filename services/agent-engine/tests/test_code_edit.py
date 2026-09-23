"""R-525 (Phase T, T-4): the code-edit agent for template projects.

Scripted stub providers stand in for the model (0 model/network calls). Projects are real git
repos made from the corner-shop fixture template, so applying, verifying, rolling back and
committing are exercised for real.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from omnistackai_agent_engine.studio.code_edit import (
    pick_files_by_name,
)
from omnistackai_agent_engine.studio.code_edit import (
    CodeEditError,
    EditOp,
    Verification,
    compute_changes,
    parse_edit_reply,
    project_file_index,
    run_code_edit,
    verify_changes,
)
from omnistackai_agent_engine.studio.templates import TemplateCatalog, instantiate_template
from omnistackai_agent_engine.studio.workspace import StudioWorkspaceStore

FIXTURES = Path(__file__).parent / "fixtures" / "templates"
WS = "5e1f0c2a-0000-4000-8000-00000000c0de"

ABOUT_PAGE = 'export default function About() {\n  return <main>About Corner Shop</main>;\n}\n'


def _select(*files: str, plan: str = "1. add about page") -> str:
    return json.dumps({"plan": plan, "files": list(files)})


GOOD_EDIT = f"""@@@ SUMMARY
Added an About page and removed the live product count.
@@@ WRITE apps/web/app/about/page.jsx
{ABOUT_PAGE.rstrip()}
@@@ REPLACE apps/web/app/page.jsx
@@@ FIND
      <LiveCount />
@@@ WITH
      <a href="about">About us</a>
@@@ DELETE apps/web/app/live-count.jsx
@@@ END
"""


class ScriptedProvider:
    provider_id = "stub"

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.requests: list = []

    async def generate(self, request):  # noqa: ANN001
        self.requests.append(request)
        if not self.replies:
            raise AssertionError("the agent asked the model more times than scripted")
        return SimpleNamespace(text=self.replies.pop(0))


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


def _tree_digest(repo: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts):
        digest.update(path.relative_to(repo).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class _ProjectCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        store = StudioWorkspaceStore(root / "workspaces")
        instantiate_template(TemplateCatalog(FIXTURES), store, WS, "corner-shop")
        self.repo = store.repo_path(WS)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_edit(self, provider: ScriptedProvider, **kwargs) -> dict:
        return asyncio.run(run_code_edit(self.repo, "Add an about page", provider, **kwargs))


class ParseTests(unittest.TestCase):
    def test_parses_all_operation_kinds(self) -> None:
        reply = parse_edit_reply(GOOD_EDIT)
        self.assertEqual(reply.summary, "Added an About page and removed the live product count.")
        self.assertEqual([op.kind for op in reply.ops], ["write", "replace", "delete"])
        self.assertEqual(reply.ops[0].content, ABOUT_PAGE)
        self.assertEqual(reply.ops[1].find, "      <LiveCount />")
        self.assertEqual(reply.ops[1].replacement, '      <a href="about">About us</a>')

    def test_tolerates_a_markdown_fence(self) -> None:
        self.assertEqual(len(parse_edit_reply("```\n" + GOOD_EDIT + "```\n").ops), 3)

    def test_tolerates_what_small_models_add(self) -> None:
        """R-530: a local model nearly always writes a sentence first, and sometimes forgets the
        summary. Neither is a reason to throw away operations that parsed."""
        preamble = parse_edit_reply("Sure! Here you go:\n\n" + GOOD_EDIT)
        self.assertEqual([op.kind for op in preamble.ops], ["write", "replace", "delete"])
        self.assertEqual(preamble.summary, "Added an About page and removed the live product count.")

        no_summary = parse_edit_reply("@@@ SUMMARY\n\n@@@ DELETE a.js\n@@@ END\n")
        self.assertEqual([op.kind for op in no_summary.ops], ["delete"])
        self.assertIn("a.js", no_summary.summary)

    def test_rejections(self) -> None:
        cases = {
            "cut off": GOOD_EDIT.replace("@@@ END\n", ""),
            "FIND must follow": "@@@ SUMMARY\nx\n@@@ FIND\na\n@@@ END\n",
            "WITH must follow": "@@@ SUMMARY\nx\n@@@ REPLACE a.js\n@@@ WITH\nb\n@@@ END\n",
            "no WRITE": "@@@ SUMMARY\nnothing\n@@@ END\n",
            "needs a file path": "@@@ SUMMARY\nx\n@@@ WRITE\ny\n@@@ END\n",
        }
        for needle, text in cases.items():
            with self.subTest(case=needle):
                with self.assertRaises(CodeEditError) as error:
                    parse_edit_reply(text)
                self.assertIn(needle, str(error.exception))


class PickFilesByNameTests(unittest.TestCase):
    """R-530: when the model names files that do not exist, the editor must still see real code."""

    PATHS = [
        "apps/rider/app/(app)/ride/page.tsx",
        "apps/rider/app/(app)/promos/page.tsx",
        "apps/driver/app/trip/page.tsx",
        "apps/admin/app/pricing/page.tsx",
        "services/api/src/routes/rider.ts",
        "services/api/src/services/trips.ts",
        "README.md",
    ]

    def test_ranks_paths_by_the_words_in_the_request(self) -> None:
        picked = pick_files_by_name("Add a women-only rides toggle to the booking screen in the rider app", self.PATHS)
        self.assertIn("apps/rider/app/(app)/ride/page.tsx", picked[:3])
        self.assertNotIn("README.md", picked)

        pin = pick_files_by_name("Change the driver trip start PIN to 6 digits", self.PATHS)
        self.assertEqual(pin[0], "apps/driver/app/trip/page.tsx")

    def test_a_request_with_no_useful_words_selects_nothing(self) -> None:
        self.assertEqual(pick_files_by_name("please make it better", self.PATHS), [])


class ComputeChangesTests(_ProjectCase):
    def test_path_and_content_rules(self) -> None:
        bad = {
            "not a relative path inside": EditOp("write", "../escape.js", content="x"),
            "not a relative path": EditOp("write", "/etc/passwd", content="x"),
            "generated or tool directory": EditOp("write", "apps/web/node_modules/x.js", content="x"),
            "real .env files": EditOp("write", "services/api/.env", content="SECRET=1"),
            "lockfiles": EditOp("write", "pnpm-lock.yaml", content="x"),
            "does not exist (use WRITE": EditOp("replace", "apps/web/app/nope.jsx", find="a", replacement="b"),
            "occurs 0 times": EditOp("replace", "apps/web/app/page.jsx", find="NOT IN FILE", replacement="b"),
            "DELETE apps/web/app/gone.jsx": EditOp("delete", "apps/web/app/gone.jsx"),
        }
        for needle, op in bad.items():
            with self.subTest(case=needle):
                with self.assertRaises(CodeEditError) as error:
                    compute_changes(self.repo, (op,))
                self.assertIn(needle, str(error.exception))

    def test_replace_must_be_unique(self) -> None:
        (self.repo / "dup.js").write_text("a\na\n", encoding="utf-8")
        with self.assertRaises(CodeEditError) as error:
            compute_changes(self.repo, (EditOp("replace", "dup.js", find="a", replacement="b"),))
        self.assertIn("occurs 2 times", str(error.exception))

    def test_write_refused_on_a_truncated_file(self) -> None:
        with self.assertRaises(CodeEditError):
            compute_changes(self.repo, (EditOp("write", "README.md", content="x"),), truncated=frozenset({"README.md"}))

    def test_env_example_and_sequential_ops_are_fine(self) -> None:
        changes = compute_changes(
            self.repo,
            (
                EditOp("write", "./.env.example", content="A=1\n"),
                EditOp("write", "notes.md", content="one\n"),
                EditOp("replace", "notes.md", find="one", replacement="two"),
            ),
        )
        self.assertEqual(changes, {".env.example": "A=1\n", "notes.md": "two\n"})

    def test_index_skips_tool_dirs_secrets_and_lockfiles(self) -> None:
        (self.repo / "apps" / "web" / "node_modules").mkdir()
        (self.repo / "apps" / "web" / "node_modules" / "x.js").write_text("x", encoding="utf-8")
        (self.repo / "services" / "api" / ".env").write_text("SECRET=1", encoding="utf-8")
        (self.repo / "pnpm-lock.yaml").write_text("lock", encoding="utf-8")
        paths = [p for p, _ in project_file_index(self.repo)]
        self.assertIn("apps/web/app/page.jsx", paths)
        self.assertIn("omnistack.json", paths)
        self.assertFalse(any("node_modules" in p or p.endswith(".env") or p == "pnpm-lock.yaml" for p in paths))


class RunCodeEditTests(_ProjectCase):
    def test_add_modify_delete_then_commit_only_touched_paths(self) -> None:
        # A preview leaves untracked node_modules; they must never be committed.
        (self.repo / "apps" / "web" / "node_modules" / "next").mkdir(parents=True)
        (self.repo / "apps" / "web" / "node_modules" / "next" / "index.js").write_text("x", encoding="utf-8")
        head_before = _git(self.repo, "rev-parse", "HEAD")
        provider = ScriptedProvider([_select("apps/web/app/page.jsx", "apps/web/app/live-count.jsx", "nope.js"), GOOD_EDIT])

        result = self.run_edit(provider)

        self.assertEqual(result["added"], ["apps/web/app/about/page.jsx"])
        self.assertEqual(result["modified"], ["apps/web/app/page.jsx"])
        self.assertEqual(result["deleted"], ["apps/web/app/live-count.jsx"])
        self.assertEqual(result["summary"], "Added an About page and removed the live product count.")
        self.assertFalse(result["repaired"])
        self.assertTrue(result["verification"]["passed"])
        self.assertTrue(result["verification"]["not_checked"])  # .jsx cannot be checked without a toolchain

        self.assertNotEqual(result["commit_sha"], head_before)
        self.assertEqual(_git(self.repo, "log", "-1", "--format=%s"), "edit: Add an about page")
        committed = set(_git(self.repo, "show", "--name-only", "--format=", "HEAD").splitlines())
        self.assertEqual(
            committed,
            {"apps/web/app/about/page.jsx", "apps/web/app/page.jsx", "apps/web/app/live-count.jsx"},
        )
        self.assertIn("?? apps/web/node_modules/", _git(self.repo, "status", "--porcelain"))
        self.assertEqual((self.repo / "apps/web/app/about/page.jsx").read_text(encoding="utf-8"), ABOUT_PAGE)
        self.assertFalse((self.repo / "apps/web/app/live-count.jsx").exists())

        # The model only ever saw real files: the unknown path was dropped from what it read.
        edit_prompt = provider.requests[1].messages[1].content
        self.assertIn("=== FILE apps/web/app/page.jsx", edit_prompt)
        self.assertNotIn("=== FILE nope.js", edit_prompt)
        self.assertEqual(provider.requests[0].max_output_tokens, 8_192)

    def test_cut_off_reply_is_retried_once(self) -> None:
        provider = ScriptedProvider([_select("apps/web/app/page.jsx"), GOOD_EDIT.replace("@@@ END\n", ""), GOOD_EDIT])
        result = self.run_edit(provider)
        self.assertEqual(len(provider.requests), 3)
        self.assertIn("rejected", provider.requests[2].messages[-1].content)
        self.assertEqual(result["added"], ["apps/web/app/about/page.jsx"])

    def test_two_bad_replies_fail_without_touching_anything(self) -> None:
        before = _tree_digest(self.repo)
        head = _git(self.repo, "rev-parse", "HEAD")
        bad = "@@@ SUMMARY\nx\n@@@ REPLACE apps/web/app/page.jsx\n@@@ FIND\nNOPE\n@@@ WITH\ny\n@@@ END\n"
        with self.assertRaises(CodeEditError):
            self.run_edit(ScriptedProvider([_select("apps/web/app/page.jsx"), bad, bad]))
        self.assertEqual(_tree_digest(self.repo), before)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD"), head)

    def test_failed_check_is_repaired_once(self) -> None:
        broken = GOOD_EDIT.replace("About Corner Shop", "BROKEN")
        fix = (
            "@@@ SUMMARY\nFixed the about page.\n@@@ REPLACE apps/web/app/about/page.jsx\n@@@ FIND\n"
            "BROKEN\n@@@ WITH\nAbout Corner Shop\n@@@ END\n"
        )

        def verifier(repo, manifest, changes):  # noqa: ANN001
            text = (Path(repo) / "apps/web/app/about/page.jsx").read_text(encoding="utf-8")
            return Verification(errors=["web: about page is broken"] if "BROKEN" in text else [], checked=["web (fake)"])

        provider = ScriptedProvider([_select("apps/web/app/page.jsx"), broken, fix])
        result = self.run_edit(provider, verifier=verifier)
        self.assertTrue(result["repaired"])
        self.assertTrue(result["verification"]["passed"])
        self.assertIn("about page is broken", provider.requests[2].messages[-1].content)
        self.assertIn("About Corner Shop", (self.repo / "apps/web/app/about/page.jsx").read_text(encoding="utf-8"))

    def test_still_failing_after_repair_rolls_everything_back(self) -> None:
        (self.repo / "apps" / "web" / "node_modules").mkdir()
        before = _tree_digest(self.repo)
        head = _git(self.repo, "rev-parse", "HEAD")
        fix = "@@@ SUMMARY\nTried.\n@@@ WRITE apps/web/app/extra.jsx\nexport default 1;\n@@@ END\n"
        provider = ScriptedProvider([_select("apps/web/app/page.jsx"), GOOD_EDIT, fix])

        with self.assertRaises(CodeEditError) as error:
            self.run_edit(provider, verifier=lambda *a, **k: Verification(errors=["still broken"]))

        self.assertIn("nothing was saved", str(error.exception))
        self.assertEqual(_tree_digest(self.repo), before)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD"), head)
        self.assertFalse((self.repo / "apps/web/app/about").exists())

    def test_real_node_check_catches_broken_javascript_and_repair_fixes_it(self) -> None:
        broken = (
            "@@@ SUMMARY\nAdded a version route.\n@@@ REPLACE services/api/src/index.js\n@@@ FIND\n"
            '    if (url.pathname === "/health") {\n@@@ WITH\n'
            '    if (url.pathname === "/version") { return send(res, 200, { version: "1.1" }\n'
            '    if (url.pathname === "/health") {\n@@@ END\n'
        )
        fix = (
            "@@@ SUMMARY\nClosed the brace.\n@@@ REPLACE services/api/src/index.js\n@@@ FIND\n"
            '{ version: "1.1" }\n@@@ WITH\n{ version: "1.1" }); }\n@@@ END\n'
        )
        provider = ScriptedProvider([_select("services/api/src/index.js"), broken, fix])
        result = self.run_edit(provider)
        self.assertTrue(result["repaired"])
        self.assertIn("services/api/src/index.js", result["verification"]["checked"])
        self.assertIn("index.js", provider.requests[2].messages[-1].content)

    def test_manifest_edits_are_validated(self) -> None:
        manifest = json.loads((self.repo / "omnistack.json").read_text(encoding="utf-8"))
        manifest["apps"][0]["path"] = "apps/missing"
        verification = verify_changes(
            self.repo, manifest, {"omnistack.json": json.dumps(manifest)}
        ) if (self.repo / "omnistack.json").write_text(json.dumps(manifest), encoding="utf-8") else None
        self.assertIsNotNone(verification)
        self.assertTrue(any("omnistack.json" in e for e in verification.errors))

    def test_context_and_plan_reach_the_edit_prompt(self) -> None:
        provider = ScriptedProvider([_select("apps/web/app/page.jsx", plan="PLAN-XYZ"), GOOD_EDIT])
        self.run_edit(provider, context_text="Brand colour is teal")
        self.assertIn("Brand colour is teal", provider.requests[0].messages[1].content)
        self.assertIn("PLAN-XYZ", provider.requests[1].messages[1].content)


class BasePathLintTests(_ProjectCase):
    """R-525 live finding: the model linked with <a href="/about">. Template UI apps run under a base
    path, so a raw root-relative anchor leaves the app. The check turns that into an error the repair
    round must fix."""

    def _verify(self, rel: str, content: str):
        manifest = json.loads((self.repo / "omnistack.json").read_text(encoding="utf-8"))
        (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / rel).write_text(content, encoding="utf-8")
        return verify_changes(self.repo, manifest, {rel: content})

    def test_root_relative_anchor_in_a_ui_app_is_an_error(self) -> None:
        result = self._verify("apps/web/app/page.jsx", '<main><a href="/about">About</a></main>\n')
        self.assertTrue(any("next/link" in error for error in result.errors), result.errors)

    def test_link_component_external_and_relative_anchors_pass(self) -> None:
        ok = (
            'import Link from "next/link";\n'
            '<Link href="/about">About</Link>\n<a href="https://example.com">x</a>\n'
            '<a href="#top">top</a>\n<a href="mailto:hi@example.com">mail</a>\n<a href="about">rel</a>\n'
        )
        self.assertEqual(self._verify("apps/web/app/page.jsx", ok).errors, [])

    def test_api_app_is_not_linted_for_anchors(self) -> None:
        self.assertEqual(self._verify("services/api/src/page.html", '<a href="/x">x</a>\n').errors, [])


class DuplicateStructureTests(_ProjectCase):
    """R-525 live finding: a model pasted a whole new file into a REPLACE's WITH block, leaving the
    original top of the file plus a second complete copy. The page could not compile, and .jsx
    cannot be type-checked before dependencies are installed. Duplicate imports, a second default
    export or a repeated top-level declaration are never valid, so they are always errors."""

    def _errors(self, rel: str, content: str) -> list[str]:
        manifest = json.loads((self.repo / "omnistack.json").read_text(encoding="utf-8"))
        (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / rel).write_text(content, encoding="utf-8")
        return verify_changes(self.repo, manifest, {rel: content}).errors

    def test_the_real_duplicated_file_from_the_live_run_is_caught(self) -> None:
        content = (Path(__file__).parent / "fixtures" / "code_edit_duplicated_page.jsx").read_text(encoding="utf-8")
        errors = self._errors("apps/web/app/page.jsx", content)
        self.assertTrue(any("default export" in e for e in errors), errors)
        self.assertTrue(any("imported twice" in e for e in errors), errors)
        self.assertTrue(any("declared twice" in e for e in errors), errors)

    def test_valid_files_pass(self) -> None:
        content = (
            'import Link from "next/link";\nimport { a } from "./a";\n\nexport const dynamic = "force-dynamic";\n'
            "function helper() {\n  function inner() {}\n  return inner;\n}\n"
            "export default function Home() {\n  const x = 1;\n  return x;\n}\n"
        )
        self.assertEqual(self._errors("apps/web/app/page.jsx", content), [])

    def test_applies_to_api_javascript_too(self) -> None:
        content = "const a = 1;\nconst a = 2;\n"
        self.assertTrue(any("declared twice" in e for e in self._errors("services/api/src/extra.js", content)))


if __name__ == "__main__":
    unittest.main()

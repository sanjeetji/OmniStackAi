"""R-560: the build path compiles what it generated.

The compile-verify-repair loop has worked since R-466. Its only caller was an opt-in CLI, so a user
building through the console reached none of it — and R-549's `lib/brand.ts` shipped with two
unnecessary `@ts-expect-error` directives, which are themselves a compile error, breaking
`next build` for **every generated web app across nine tasks**. Every test of that change read the
generated source and agreed it was correct. None compiled it.

These tests are offline and make no model calls: they exercise the decision and reporting layer,
which is where this task's own mistakes would live. The compiler itself is covered by R-466's tests
with injected fake runners, and the loop was verified against a real `tsc` by reintroducing R-549's
defect and watching it come back as `generator_failures: ["lib/brand.ts"]`.

The distinction that matters most here is **whose fault a failure is**. The repair loop only rewrites
files a model wrote. A deterministic file that does not compile is our bug in every project built
from that template, so it is reported separately and said first — a user cannot fix it and should
not be left thinking they can.
"""

import os
import tempfile
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.intake import build_verify
from omnistackai_agent_engine.intake.build_app import app_build_result_to_dict, build_app_from_ir


class _Provider:
    """Stands in for a model. Consulting it in these tests is itself the failure."""

    def __getattr__(self, name):
        raise AssertionError(f"the model was consulted ({name}); these tests are offline")


def _build(tmp: str, **kwargs):
    return build_app_from_ir(
        example_ir("minimal-blog"),
        tmp,
        author_name="t",
        author_email="t@t.t",
        prompt="a blog",
        **kwargs,
    )


class ABuildIsNeverFailedByVerification(TestCase):
    """Refusing to hand over a repository because we could not type-check it trades a real
    deliverable for a diagnostic."""

    def test_a_build_without_a_provider_still_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = _build(tmp)
            self.assertTrue(result.commit_sha)
            self.assertGreater(result.file_count, 0)

    def test_it_says_why_rather_than_saying_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = _build(tmp).verification
        self.assertEqual(record["status"], "skipped")
        self.assertIn("without a model provider", record["reason"])

    def test_the_reason_reaches_the_console_payload(self) -> None:
        # Silence would read as "checked and fine", which is the impression that let a
        # non-compiling app ship for nine tasks.
        with tempfile.TemporaryDirectory() as tmp:
            payload = app_build_result_to_dict(_build(tmp))
        self.assertEqual(payload["verification"]["status"], "skipped")

    def test_turning_it_off_is_itself_reported(self) -> None:
        with mock.patch.dict(os.environ, {build_verify.MODE_ENV: "off"}):
            record = build_verify.verify_and_repair_build(
                target_dir="/nonexistent", ir=None, prompt="", provider=_Provider(),
                author_name="t", author_email="t@t.t",
            )
        self.assertEqual(record["status"], "skipped")
        self.assertIn("turned off", record["reason"])

    def test_missing_dependencies_name_the_way_out(self) -> None:
        # A reason a person cannot act on is barely better than silence.
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ, {build_verify.MODE_ENV: "auto"}, clear=False
        ):
            os.environ.pop(build_verify.NODE_MODULES_ENV, None)
            record = _build(tmp, provider=_Provider()).verification
        self.assertEqual(record["status"], "skipped")
        self.assertIn(build_verify.NODE_MODULES_ENV, record["reason"])
        self.assertIn(build_verify.MODE_ENV, record["reason"])

    def test_a_misnamed_cache_is_refused_rather_than_trusted(self) -> None:
        """The subtlest defect this task produced, and the most dangerous.

        TypeScript resolves through a symlink's real path, and nested lookups only recognise a
        directory literally named `node_modules`. Pointed at a cache called anything else, `next`'s
        own types become unresolvable and tsc reports implicit-any errors in code that compiles
        perfectly. An A/B of two byte-identical caches -- one named `node_modules`, one not -- was
        the only way to see it. Inventing errors in correct code is worse than checking nothing, so
        this refuses.
        """
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ, {build_verify.NODE_MODULES_ENV: f"{tmp}/warm-cache", build_verify.MODE_ENV: "auto"}
        ):
            record = _build(tmp, provider=_Provider()).verification
        self.assertEqual(record["status"], "skipped")
        self.assertIn("named 'node_modules'", record["reason"])

    def test_a_project_with_no_web_app_is_not_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = build_verify.verify_and_repair_build(
                target_dir=tmp, ir=None, prompt="", provider=_Provider(),
                author_name="t", author_email="t@t.t",
            )
        self.assertEqual(record["status"], "skipped")
        self.assertIn("no web app", record["reason"])


class WhoseFaultItIsComesFirst(TestCase):
    """A fault in a file we generate is our bug in every project built from that template."""

    def test_a_generator_failure_is_named_as_ours(self) -> None:
        summary = build_verify._summary(
            {"status": "failing", "repaired": [], "reverted": [], "generator_failures": ["lib/brand.ts"]}
        )
        self.assertIn("generates itself", summary)
        self.assertIn("not in your project", summary)

    def test_a_generator_failure_outranks_repair_counts(self) -> None:
        # Leading with "3 pages repaired" would bury the part that is actually our fault.
        summary = build_verify._summary(
            {"status": "failing", "repaired": ["a.tsx", "b.tsx", "c.tsx"], "reverted": [],
             "generator_failures": ["lib/brand.ts"]}
        )
        self.assertNotIn("3 pages", summary)

    def test_a_clean_build_says_so_plainly(self) -> None:
        summary = build_verify._summary(
            {"status": "clean", "repaired": [], "reverted": [], "generator_failures": []}
        )
        self.assertIn("compiled cleanly", summary)

    def test_reverted_pages_are_described_in_user_terms(self) -> None:
        summary = build_verify._summary(
            {"status": "clean", "repaired": [], "reverted": ["app/page.tsx"], "generator_failures": []}
        )
        self.assertIn("built-in template", summary)
        self.assertNotIn("deterministic", summary)  # our word, not theirs


class BothBuildTwinsGoThroughOneSeam(TestCase):
    """R-555 was wired into the twin the console does not call, and looked fine until a live run.

    `build_app_from_ir` is the single function every path reaches — the streaming build the console
    uses, its non-streaming sibling, and the ecosystem builder. Verifying there rather than at three
    call sites is what stops them from disagreeing.
    """

    def test_every_build_entry_point_is_verified(self) -> None:
        """Written before the code, and it found one immediately: `build_ecosystem_from_plan`
        assembles and commits by itself rather than going through `build_app_from_ir`, so every
        multi-app project would have been built unverified."""
        import inspect

        from omnistackai_agent_engine.intake import build_app

        for name in ("build_app_from_prompt", "build_app_from_prompt_stream", "build_ecosystem_from_plan"):
            with self.subTest(entry=name):
                source = inspect.getsource(getattr(build_app, name))
                reached = "build_app_from_ir" in source or "verify_and_repair_build" in source
                self.assertTrue(
                    reached,
                    f"{name} must reach verification, either through the shared seam or by calling it",
                )

    def test_verification_is_called_from_the_seam(self) -> None:
        import inspect

        from omnistackai_agent_engine.intake import build_app

        self.assertIn("verify_and_repair_build", inspect.getsource(build_app.build_app_from_ir))

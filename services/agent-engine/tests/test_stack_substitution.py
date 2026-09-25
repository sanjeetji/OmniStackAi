"""R-559: ask for something we cannot build and get the nearest thing we can, plus a reason.

Before this, a prompt for a Flutter app, native iOS/Android apps, or a React-Native-for-Web site
produced a Next.js website and an admin panel with no error and nothing saying why. Only
`react_native` ever emitted `apps/mobile`; `flutter`, `native` and `auto` were dropped in silence.
`nl_to_ir` meanwhile told the model to choose `flutter`, so the likeliest path through the product
was a guaranteed silent drop.

Two invariants here are worth more than the rest of the file:

* **Supported means it actually assembles.** The first draft of `capabilities.py` mapped `rn_web`
  to the React Native target, which *is* registered — so react-native-web reported as supported,
  no substitution fired, and `_plan_assembly` (which only lays out Next.js) produced a project
  with **zero apps**. A table of what we support is worthless unless something checks it against
  what is actually built.
* **Registering an adapter must be the only change needed.** If making Flutter real requires
  editing an intake prompt, a planner, or a list of excuses somewhere, this was built wrong — the
  point of deriving support from the registry is that a future stack plugs in at one seam.
"""

import dataclasses
from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    MobileProfile,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen.adapter import GenerationTarget
from omnistackai_agent_engine.codegen.assembler import assemble_project, default_registry
from omnistackai_agent_engine.codegen.capabilities import (
    MOBILE_FALLBACK,
    WEB_FALLBACK,
    offerable_mobile_profiles,
    resolve_stack,
    supported_mobile_profiles,
    supported_web_strategies,
)
from omnistackai_agent_engine.codegen.files import GeneratedFile, GeneratedProject


def _ir(**strategy):
    base = example_ir("minimal-blog")
    return dataclasses.replace(
        base, project_strategy=dataclasses.replace(base.project_strategy, **strategy)
    )


def _apps(ir) -> list[str]:
    return sorted({f.path.split("/")[1] for f in assemble_project(ir).files() if f.path.startswith("apps/")})


class AnAppRequestIsAnsweredWithAnApp(TestCase):
    """The defect that opened this task: three of four mobile profiles produced no app at all."""

    def test_every_mobile_profile_that_wants_an_app_builds_one(self) -> None:
        for profile in (MobileProfile.REACT_NATIVE, MobileProfile.FLUTTER, MobileProfile.NATIVE, MobileProfile.AUTO):
            with self.subTest(profile=profile):
                self.assertIn(
                    "mobile",
                    _apps(_ir(mobile_profile=profile)),
                    f"{profile.value} produced no app; a request for an app must return an app",
                )

    def test_asking_for_no_app_still_builds_none(self) -> None:
        self.assertNotIn("mobile", _apps(_ir(mobile_profile=MobileProfile.NONE)))

    def test_every_web_strategy_that_wants_a_site_builds_one(self) -> None:
        for strategy in (WebStrategy.NEXTJS, WebStrategy.FLUTTER_WEB, WebStrategy.RN_WEB, WebStrategy.PWA):
            with self.subTest(strategy=strategy):
                self.assertIn(
                    "web",
                    _apps(_ir(web_strategy=strategy)),
                    f"{strategy.value} produced no web app",
                )


class SupportedMeansItActuallyAssembles(TestCase):
    """The invariant that catches the class of bug this file's docstring describes.

    Whatever `capabilities` reports as supported has to survive a real assembly. Mapping a strategy
    onto a registered-but-unrelated adapter passes any test that only reads the table.
    """

    def test_supported_mobile_profiles_all_assemble(self) -> None:
        for profile in supported_mobile_profiles(default_registry()):
            with self.subTest(profile=profile):
                self.assertIn("mobile", _apps(_ir(mobile_profile=profile)))

    def test_supported_web_strategies_all_assemble(self) -> None:
        for strategy in supported_web_strategies(default_registry()):
            with self.subTest(strategy=strategy):
                self.assertIn("web", _apps(_ir(web_strategy=strategy)))

    def test_unsupported_strategies_are_substituted_not_dropped(self) -> None:
        registry = default_registry()
        for profile in MobileProfile:
            if profile in (MobileProfile.NONE,) or profile in supported_mobile_profiles(registry):
                continue
            with self.subTest(profile=profile):
                plan = resolve_stack(_ir(mobile_profile=profile).project_strategy)
                self.assertEqual(plan.strategy.mobile_profile, MOBILE_FALLBACK)
                self.assertTrue(plan.substitutions, "a substitution must be recorded, not silent")


class EverySubstitutionSaysWhy(TestCase):
    def test_a_reason_names_what_was_asked_and_what_was_built(self) -> None:
        plan = resolve_stack(_ir(mobile_profile=MobileProfile.FLUTTER).project_strategy)
        (sub,) = plan.substitutions
        self.assertEqual((sub.layer, sub.asked, sub.built), ("mobile", "flutter", "react_native"))
        self.assertIn("Flutter", sub.reason)
        self.assertIn("React Native", sub.reason)
        # The part that decides whether the substitution is acceptable to the person asking.
        self.assertIn("App Store", sub.reason)

    def test_native_is_named_in_the_words_a_user_used(self) -> None:
        plan = resolve_stack(_ir(mobile_profile=MobileProfile.NATIVE).project_strategy)
        (sub,) = plan.substitutions
        self.assertIn("native iOS and Android", sub.reason)
        self.assertIn("Swift or Kotlin", sub.reason)

    def test_auto_states_a_choice_rather_than_an_apology(self) -> None:
        plan = resolve_stack(_ir(mobile_profile=MobileProfile.AUTO).project_strategy)
        (sub,) = plan.substitutions
        self.assertNotIn("does not generate", sub.reason)

    def test_a_supported_stack_produces_no_note(self) -> None:
        plan = resolve_stack(_ir(mobile_profile=MobileProfile.REACT_NATIVE, web_strategy=WebStrategy.NEXTJS).project_strategy)
        self.assertEqual(plan.substitutions, ())

    def test_the_reason_reaches_the_generated_readme(self) -> None:
        files = {f.path: f for f in assemble_project(_ir(mobile_profile=MobileProfile.FLUTTER)).files()}
        self.assertIn("does not generate Flutter yet", files["README.md"].content)

    def test_reasons_carry_no_markup(self) -> None:
        # Generated copy is rendered as text in the console; it has no reason to contain markup.
        for profile in (MobileProfile.FLUTTER, MobileProfile.NATIVE, MobileProfile.AUTO):
            for sub in resolve_stack(_ir(mobile_profile=profile).project_strategy).substitutions:
                self.assertNotIn("<", sub.reason)
                self.assertNotIn(">", sub.reason)


class _FlutterAdapter:
    """A stand-in for the adapter R-559 does not write, used to prove the seam works."""

    target = GenerationTarget.FLUTTER

    def generate(self, ir) -> GeneratedProject:
        return GeneratedProject(self.target.value, [GeneratedFile("apps/flutter/main.dart", "void main() {}\n")])


class RegisteringAnAdapterIsTheOnlyChangeNeeded(TestCase):
    """The roadmap's expandability requirement, enforced rather than hoped for.

    If this test ever needs an intake prompt edited or a hardcoded exception removed to pass, the
    substitution was not derived from the registry and the next stack will cost a rewrite.
    """

    def test_flutter_stops_being_substituted_once_an_adapter_exists(self) -> None:
        registry = default_registry()
        before = resolve_stack(_ir(mobile_profile=MobileProfile.FLUTTER).project_strategy, registry)
        self.assertTrue(before.substitutions, "precondition: Flutter is substituted today")

        registry.register(_FlutterAdapter())
        after = resolve_stack(_ir(mobile_profile=MobileProfile.FLUTTER).project_strategy, registry)

        self.assertEqual(after.substitutions, (), "registering the adapter must end the substitution")
        self.assertEqual(after.strategy.mobile_profile, MobileProfile.FLUTTER, "the request must be honoured as asked")

    def test_intake_offers_flutter_once_an_adapter_exists(self) -> None:
        registry = default_registry()
        self.assertNotIn("flutter", offerable_mobile_profiles(registry))
        registry.register(_FlutterAdapter())
        self.assertIn("flutter", offerable_mobile_profiles(registry))


class TheRequestIsNeverRewritten(TestCase):
    """Substituting must not destroy what the user asked for."""

    def test_the_ir_still_records_the_original_request(self) -> None:
        ir = _ir(mobile_profile=MobileProfile.FLUTTER)
        assemble_project(ir)
        self.assertEqual(
            ir.project_strategy.mobile_profile,
            MobileProfile.FLUTTER,
            "the IR must keep the request so we can find these projects when Flutter ships",
        )

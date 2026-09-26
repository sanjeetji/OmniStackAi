"""PC-003: a stack the user names but we do not build is answered with a reason, never silently.

R-559 made this true for the stacks the IR can record (Flutter, native, React Native for Web).
It was still false one level up: the IR has no value for React.js, Vue, Angular, Spring, Laravel,
MySQL or MongoDB, so the model wrote the nearest value the schema allows — Next.js, Python,
PostgreSQL — and the user who asked for Vue got React with nothing anywhere saying so.

The patterns are narrow on purpose. "A spring sale store for ruby jewellery in Maui" names no
stack, and telling that user "you asked for Java" would be worse than silence.
"""

from dataclasses import replace
from unittest import TestCase

from omnistackai_agent_engine.application_ir import MobileProfile, WebStrategy, example_ir
from omnistackai_agent_engine.codegen.capabilities import named_stack_substitutions
from omnistackai_agent_engine.intake.build_app import _substitutions_for

STRATEGY = example_ir("minimal-blog").project_strategy


def _asked(prompt: str, strategy=STRATEGY) -> list[tuple[str, str]]:
    return [(s.layer, s.asked) for s in named_stack_substitutions(prompt, strategy)]


class NamedStacksAreAnswered(TestCase):
    def test_each_unsupported_stack_is_named_with_what_was_built(self) -> None:
        cases = {
            "Build it in React.js": ("web", "React.js"),
            "a Vue dashboard": ("web", "Vue"),
            "an Angular admin": ("web", "Angular"),
            "made with SvelteKit": ("web", "Svelte"),
            "Spring Boot backend": ("backend", "Java / Spring"),
            "a Laravel API": ("backend", "PHP / Laravel"),
            "Ruby on Rails please": ("backend", "Ruby on Rails"),
            "ASP.NET core api": ("backend", ".NET / C#"),
            "a Django backend": ("backend", "Django / Flask"),
            "store it in MySQL": ("database", "MySQL"),
            "use MongoDB": ("database", "MongoDB"),
            "Firebase for data": ("database", "Firebase / Supabase"),
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                self.assertIn(expected, _asked(prompt))

    def test_the_reason_says_what_was_built(self) -> None:
        by_layer = {s.layer: s for s in named_stack_substitutions(
            "React.js front end, Spring Boot backend, MySQL database", STRATEGY)}
        self.assertIn("Next.js", by_layer["web"].reason)
        self.assertIn("Python", by_layer["backend"].reason)
        self.assertIn("PostgreSQL", by_layer["database"].reason)

    def test_the_backend_note_names_the_backend_that_was_chosen(self) -> None:
        go = replace(STRATEGY, backend_strategy="go")
        (note,) = named_stack_substitutions("a Laravel API", go)
        self.assertEqual(note.built, "go")
        self.assertIn("Go", note.reason)


class OrdinaryWordsAreNotStacks(TestCase):
    def test_no_false_alarms(self) -> None:
        for prompt in (
            "A spring sale store for ruby jewellery in Maui",
            "An electronics shop selling capacitors",
            "A javascript quiz app",
            "Track reactions to posts",
            "",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(_asked(prompt), [])

    def test_react_native_is_something_we_build(self) -> None:
        self.assertEqual(_asked("A React Native delivery app"), [])
        self.assertEqual(_asked("a react-native app"), [])
        self.assertEqual(_asked("a react-native app plus a React.js site"), [("web", "React.js")])


class NotesOnlyForLayersThatExist(TestCase):
    def test_no_mobile_note_when_no_app_is_built(self) -> None:
        strategy = replace(STRATEGY, mobile_profile=MobileProfile.NONE)
        self.assertEqual(_asked("an Ionic app", strategy), [])

    def test_a_mobile_note_when_an_app_is_built(self) -> None:
        strategy = replace(STRATEGY, mobile_profile=MobileProfile.REACT_NATIVE)
        self.assertEqual(_asked("an Ionic app", strategy), [("mobile", "Ionic / Capacitor")])


class TheNotesReachTheBuildResult(TestCase):
    def test_prompt_notes_join_the_strategy_notes(self) -> None:
        ir = example_ir("minimal-blog")
        notes = _substitutions_for(ir, "a Vue site with a Laravel API")
        self.assertEqual({(n["layer"], n["asked"]) for n in notes},
                         {("web", "Vue"), ("backend", "PHP / Laravel")})

    def test_a_layer_already_explained_is_not_explained_twice(self) -> None:
        # The IR recorded Flutter; resolve_stack already explains the mobile layer.
        ir = example_ir("minimal-blog")
        ir = replace(ir, project_strategy=replace(ir.project_strategy, mobile_profile=MobileProfile.FLUTTER,
                                                  web_strategy=WebStrategy.NEXTJS))
        notes = _substitutions_for(ir, "a Flutter app, or Ionic if not")
        self.assertEqual([n["layer"] for n in notes].count("mobile"), 1)

    def test_no_prompt_means_no_new_notes(self) -> None:
        self.assertEqual(_substitutions_for(example_ir("minimal-blog")), ())

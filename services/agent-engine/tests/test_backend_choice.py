"""R-565: an ecosystem is built with the backend the user asked for.

`surface_to_ir` hardcoded `BackendStrategy.PYTHON` for every surface, so "a logistics platform with
drivers and dispatchers and the backend should be in Go language" produced a Python backend and
said nothing. The single-app path honoured the request, so the same sentence got a different answer
depending on how many apps the prompt happened to imply — which is worse than either answer alone,
because nothing on screen explained the difference.

The matching is narrow on purpose, and the test that matters most is the one that asserts a
*non*-match: "go" is an ordinary verb and "node" is a thing in a graph, so a bare mention must not
change anybody's backend. Being eager here would mean a delivery platform whose customers "go to
collect their order" silently becomes a Go project.
"""

from unittest import TestCase

from omnistackai_agent_engine.application_ir import BackendStrategy
from omnistackai_agent_engine.codegen.ecosystem_assembler import assemble_ecosystem, union_ir
from omnistackai_agent_engine.intake.backend_choice import DEFAULT_BACKEND, backend_for_prompt
from omnistackai_agent_engine.intake.ecosystem import plan_ecosystem_from_prompt

_ROLES = " with drivers and dispatchers"


def _ecosystem_backend(prompt: str) -> str:
    return union_ir(plan_ecosystem_from_prompt(prompt, "complete")).project_strategy.backend_strategy.value


class TheRequestedLanguageIsUsed(TestCase):
    def test_go_is_honoured_in_an_ecosystem(self) -> None:
        self.assertEqual(
            _ecosystem_backend("Create a logistics platform" + _ROLES + " and the backend should be in Go language"),
            "go",
        )

    def test_node_is_honoured(self) -> None:
        self.assertEqual(_ecosystem_backend("a delivery platform" + _ROLES + ", backend in Node.js"), "node")

    def test_python_remains_the_default(self) -> None:
        self.assertEqual(_ecosystem_backend("a delivery platform" + _ROLES), "python")
        self.assertEqual(DEFAULT_BACKEND, BackendStrategy.PYTHON)

    def test_the_choice_reaches_the_generated_repository(self) -> None:
        plan = plan_ecosystem_from_prompt(
            "Create a logistics platform" + _ROLES + " and the backend should be in Go language", "complete"
        )
        paths = {f.path for f in assemble_ecosystem(plan).files()}
        self.assertIn("services/api/go.mod", paths)
        self.assertFalse(
            any(p.endswith("requirements.txt") for p in paths), "a Python backend was generated too"
        )

    def test_there_is_still_exactly_one_backend(self) -> None:
        plan = plan_ecosystem_from_prompt("a delivery platform" + _ROLES + ", API written in golang", "complete")
        paths = {f.path for f in assemble_ecosystem(plan).files()}
        self.assertEqual({p.split("/")[1] for p in paths if p.startswith("services/")}, {"api"})


class APassingMentionIsNotARequest(TestCase):
    """The eager reading of this would be worse than not reading it at all."""

    def test_go_as_a_verb_changes_nothing(self) -> None:
        self.assertEqual(
            backend_for_prompt("a delivery platform where customers go to collect their orders"),
            BackendStrategy.PYTHON,
        )

    def test_node_as_a_graph_term_changes_nothing(self) -> None:
        self.assertEqual(
            backend_for_prompt("a logistics platform that routes between each node on the map"),
            BackendStrategy.PYTHON,
        )

    def test_the_language_still_counts_when_it_names_the_stack(self) -> None:
        for prompt in (
            "build the backend in go",
            "the API should be written in go",
            "use node for the server",
            "golang backend please",
        ):
            with self.subTest(prompt=prompt):
                self.assertNotEqual(backend_for_prompt(prompt), BackendStrategy.PYTHON)


class TheChoiceIsDeterministic(TestCase):
    def test_the_same_prompt_answers_the_same_twice(self) -> None:
        prompt = "a platform" + _ROLES + " with a go backend and a node dashboard"
        self.assertEqual(backend_for_prompt(prompt), backend_for_prompt(prompt))

    def test_an_empty_prompt_takes_the_default(self) -> None:
        self.assertEqual(backend_for_prompt(""), DEFAULT_BACKEND)
        self.assertEqual(backend_for_prompt("   "), DEFAULT_BACKEND)


class TheSingleAppPathIsUnchanged(TestCase):
    def test_the_intake_prompt_still_tells_the_model_about_go(self) -> None:
        # The single-app path honours the request through the model, and this task did not touch it.
        from omnistackai_agent_engine.intake.nl_to_ir import _system_instruction

        self.assertIn("choose 'go' if the user requested Go/golang", _system_instruction("minimal-blog"))

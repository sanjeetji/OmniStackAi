"""PC-014: local models as a first-class path.

Found in PC-084: `.env` named qwen2.5-coder:14b while only the 7b was installed, and every local call
failed with "model is not configured for this provider". The platform now asks Ollama what is
installed, recommends a model from the machine's memory, and - with OMNISTACKAI_PREFER_LOCAL - keeps
every model call of a build on this machine, page design included.
"""

import os
from unittest import TestCase, mock

from omnistackai_agent_engine.model_gateway import local_models as lm
from omnistackai_agent_engine.model_gateway.local_models import InstalledModel, choose, recommend


class ItRecommendsAModelForTheMachine(TestCase):
    def test_by_memory(self) -> None:
        self.assertEqual(recommend(8)[0], "qwen2.5-coder:7b")
        self.assertEqual(recommend(16)[0], "qwen2.5-coder:14b")
        self.assertEqual(recommend(64)[0], "qwen2.5-coder:32b")
        self.assertEqual(recommend(4)[0], "qwen2.5-coder:3b")


class ItRunsWhatIsInstalled(TestCase):
    INSTALLED = (InstalledModel("qwen2.5-coder:14b", 8.4, 14.8), InstalledModel("llama3.2:3b", 2.0, 3.2))

    def test_the_configured_model_when_it_is_installed(self) -> None:
        self.assertEqual(choose("qwen2.5-coder:14b", self.INSTALLED, 16).model, "qwen2.5-coder:14b")

    def test_the_best_installed_one_that_fits_when_it_is_not(self) -> None:
        choice = choose("qwen2.5-coder:7b", self.INSTALLED, 16)
        self.assertEqual(choice.model, "qwen2.5-coder:14b")
        self.assertIn("qwen2.5-coder:7b is not installed", choice.reason)

    def test_a_model_too_large_for_the_machine_is_passed_over(self) -> None:
        installed = (InstalledModel("qwen2.5-coder:32b", 19.9, 32.8), InstalledModel("qwen2.5-coder:7b", 4.7, 7.6))
        self.assertEqual(choose("qwen2.5-coder:14b", installed, 16).model, "qwen2.5-coder:7b")

    def test_with_nothing_installed_it_says_what_to_pull_and_downloads_nothing(self) -> None:
        choice = choose("qwen2.5-coder:14b", (), 16)
        self.assertIsNone(choice.model)
        self.assertIn("ollama pull qwen2.5-coder:14b", choice.reason)

    def test_without_ollama_the_setting_stands(self) -> None:
        self.assertEqual(choose("qwen2.5-coder:14b", None, 16).model, "qwen2.5-coder:14b")

    def test_the_studio_applies_it_once_at_start(self) -> None:
        with mock.patch.object(lm, "installed_models", return_value=self.INSTALLED), \
             mock.patch.object(lm, "machine_memory_gb", return_value=16.0), \
             mock.patch.dict(os.environ, {"OMNISTACKAI_OLLAMA_MODEL": "qwen2.5-coder:7b"}):
            lm.apply_installed_local_model()
            self.assertEqual(os.environ["OMNISTACKAI_OLLAMA_MODEL"], "qwen2.5-coder:14b")
        from pathlib import Path

        serve = Path(lm.__file__).parents[1].joinpath("studio/live_serve.py").read_text()
        self.assertIn("apply_installed_local_model(log=", serve)


class LocalMeansEveryCallStaysLocal(TestCase):
    def test_page_design_uses_the_local_model_when_local_is_preferred(self) -> None:
        from omnistackai_agent_engine.intake import provider_resolution as pr

        with mock.patch.dict(os.environ, {"OMNISTACKAI_PREFER_LOCAL": "1", "OMNISTACKAI_GEMINI_API_KEY": "x",
                                          "OMNISTACKAI_GOOGLE_API_KEY": "x"}), \
             mock.patch.object(pr, "is_ollama_ready", return_value=True), \
             mock.patch.object(pr, "_load_dotenv_if_needed"):
            chain = pr.resolve_page_providers_from_env()
            self.assertEqual([p[0].provider_id for p in chain], ["ollama-local"])
            self.assertIsNone(pr.page_provider_choice())
            self.assertEqual(pr.page_provider_choice("groq"), "groq", "a project's own provider is kept")


class PagesAskForTheModelTheProviderHas(TestCase):
    """Found live: a local-only build's ecosystem pages asked Ollama for "default" (the recorder
    wrapper has no profiles()) and every page fell back to its template (UnknownModelError)."""

    def test_the_model_is_found_through_the_recorder(self) -> None:
        from omnistackai_agent_engine.codegen.llm_ui import _default_model_id
        from omnistackai_agent_engine.intake._ollama import build_ollama_provider_from_env
        from omnistackai_agent_engine.model_gateway.accounting import UsageLedger
        from omnistackai_agent_engine.model_gateway.recording import RecordingProvider

        with mock.patch.dict(os.environ, {"OMNISTACKAI_OLLAMA_MODEL": "qwen2.5-coder:14b"}):
            provider, _, _, _ = build_ollama_provider_from_env()
        self.assertEqual(_default_model_id(RecordingProvider(provider, UsageLedger())), "qwen2.5-coder:14b")


class AFieldNamedAuthorIsNotASecondKindOfUser(TestCase):
    """Found in the PC-014 live build: "books with a title, author, a short note and a read/unread
    status" was read as naming authors, and a reading list became a three-app publishing platform."""

    def test_actor_words_in_a_list_of_fields_are_fields(self) -> None:
        from omnistackai_agent_engine.intake.ecosystem_intent import detect_ecosystem_intent as detect

        self.assertFalse(detect("A simple reading list: books with a title, author, a short note and a read/unread status").build_ecosystem)
        self.assertFalse(detect("Orders with a customer, a date, a status and a driver").build_ecosystem)
        self.assertTrue(detect("A blog where authors write articles and readers comment").build_ecosystem)
        self.assertTrue(detect("A food delivery app: restaurants with menus, customers place orders, couriers deliver").build_ecosystem)


class ALocalModelsPageIsReadAsWritten(TestCase):
    """Found in the PC-014 live build: every page the local model wrote was rejected as
    "truncated" - it put a sentence before its code block or a note after it."""

    def test_the_page_is_taken_from_its_code_block(self) -> None:
        from omnistackai_agent_engine.codegen.llm_ui import clean_and_validate_jsx

        page = '"use client";\nexport default function P() { return <main>Hi</main>; }'
        for raw in (f"Here is the page:\n```tsx\n{page}\n```\nIt shows a greeting.", f"```tsx\n{page}\n```\nNotes: Tailwind."):
            valid, cleaned, reason = clean_and_validate_jsx(raw)
            self.assertTrue(valid, reason)
            self.assertTrue(cleaned.rstrip().endswith("}"))
        self.assertFalse(clean_and_validate_jsx('```tsx\n"use client";\nexport default function P() { return <main>')[0],
                         "a page that really stops half-way is still refused")


class LocalPreferredIsPatient(TestCase):
    def test_a_slow_first_answer_does_not_send_the_work_to_the_cloud(self) -> None:
        from omnistackai_agent_engine.intake import provider_resolution as pr

        answers = iter([False, True])
        with mock.patch.object(pr, "is_ollama_ready", side_effect=lambda **_: next(answers)), \
             mock.patch("time.sleep"):
            self.assertTrue(pr.ollama_ready_patiently())

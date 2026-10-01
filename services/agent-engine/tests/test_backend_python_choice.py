"""Found during R-570 (2026-10-01): Homebrew's python@3.13 and python@3.14 were built against a newer
libexpat than macOS 26.1 ships, so `python3 -m venv` failed and every new preview with a Python API
stopped at "create backend virtualenv". The runner now uses the first interpreter that works.
"""

from unittest import TestCase
from unittest.mock import patch

from omnistackai_agent_engine.localrun import api_env, run
from omnistackai_agent_engine.localrun.plan import RunStep


class TheFirstWorkingInterpreterIsUsed(TestCase):
    def setUp(self) -> None:
        api_env._CHOSEN.clear()
        self.addCleanup(api_env._CHOSEN.clear)

    def _choose(self, working: set[str], override: str = "") -> str | None:
        which = {"python3": "/opt/brew/python3", "python3.13": "/opt/brew/python3.13"}
        with patch.dict("os.environ", {api_env.PYTHON_ENV: override}), \
                patch.object(api_env.shutil, "which", side_effect=lambda n: which.get(n)), \
                patch.object(api_env.os.path, "realpath", side_effect=lambda p: p), \
                patch.object(api_env, "_uv_pythons", return_value=["/uv/python3.13"]), \
                patch.object(api_env, "_works", side_effect=lambda p: p in working):
            return api_env.backend_python()

    def test_a_broken_python3_is_passed_over(self) -> None:
        self.assertEqual(self._choose({"/uv/python3.13"}), "/uv/python3.13")

    def test_python3_when_it_works(self) -> None:
        self.assertEqual(self._choose({"/opt/brew/python3", "/uv/python3.13"}), "/opt/brew/python3")

    def test_an_explicit_choice_wins(self) -> None:
        self.assertEqual(self._choose({"/opt/brew/python3", "/my/python"}, override="/my/python"), "/my/python")

    def test_the_virtualenv_step_runs_on_it(self) -> None:
        step = RunStep(label="create backend virtualenv", program="python3", args=("-m", "venv", ".venv"))
        with patch.object(api_env, "backend_python", return_value="/uv/python3.13"):
            self.assertEqual(run._program(step), "/uv/python3.13")
        self.assertEqual(run._program(RunStep(label="x", program="go")), "go")

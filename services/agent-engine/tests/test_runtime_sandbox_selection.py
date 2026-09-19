"""Tests for the sandbox provider-selection surface (runtime/sandbox_selection.py, R-490).

Fully offline: every test injects fake providers via the `providers` override - 0 real network/
Docker calls under `task verify`. This is the missing piece making R-486..R-489's four real
SandboxLifecycleProvider drivers genuinely pluggable/switchable via configuration.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from omnistackai_agent_engine.runtime.errors import SandboxSelectionError
from omnistackai_agent_engine.runtime.sandbox_selection import SandboxSetup, build_sandbox_from_env


class _FakeProvider:
    def __init__(self, provider_id: str, active: bool) -> None:
        self._id = provider_id
        self._active = active

    @property
    def id(self) -> str:
        return self._id

    @property
    def active(self) -> bool:
        return self._active


def _fake_registry(**active_by_name: bool) -> dict:
    return {name: _FakeProvider(name, active) for name, active in active_by_name.items()}


class TestBuildSandboxFromEnvDefaults(unittest.TestCase):
    def test_defaults_to_disabled_when_env_var_is_unset(self) -> None:
        providers = _fake_registry(gvisor=True, e2b=False, **{"vercel-sandbox": False}, daytona=False)
        with patch.dict("os.environ", {}, clear=True):
            setup = build_sandbox_from_env(providers=providers)
        self.assertIsInstance(setup, SandboxSetup)
        self.assertIsNone(setup.selected)
        self.assertIsNone(setup.provider)
        self.assertEqual(setup.active, ("gvisor",))

    def test_env_var_none_is_equivalent_to_unset(self) -> None:
        providers = _fake_registry(gvisor=True, e2b=False, **{"vercel-sandbox": False}, daytona=False)
        with patch.dict("os.environ", {"OMNISTACKAI_SANDBOX_PROVIDER": "none"}, clear=True):
            setup = build_sandbox_from_env(providers=providers)
        self.assertIsNone(setup.selected)
        self.assertIsNone(setup.provider)

    def test_active_reports_every_provider_whose_active_is_true(self) -> None:
        providers = _fake_registry(gvisor=True, e2b=True, **{"vercel-sandbox": False}, daytona=False)
        with patch.dict("os.environ", {}, clear=True):
            setup = build_sandbox_from_env(providers=providers)
        self.assertEqual(setup.active, ("e2b", "gvisor"))  # sorted


class TestBuildSandboxFromEnvSelection(unittest.TestCase):
    def test_selecting_an_active_provider_via_env_var(self) -> None:
        providers = _fake_registry(gvisor=True, e2b=False, **{"vercel-sandbox": False}, daytona=False)
        with patch.dict("os.environ", {"OMNISTACKAI_SANDBOX_PROVIDER": "gvisor"}, clear=True):
            setup = build_sandbox_from_env(providers=providers)
        self.assertEqual(setup.selected, "gvisor")
        self.assertIs(setup.provider, providers["gvisor"])

    def test_explicit_selection_parameter_overrides_the_env_var(self) -> None:
        """The concrete "switch per user base" mechanism: a caller passes selection explicitly,
        e.g. computed from a user's plan, without touching the global env var at all."""
        providers = _fake_registry(gvisor=True, e2b=True, **{"vercel-sandbox": False}, daytona=False)
        with patch.dict("os.environ", {"OMNISTACKAI_SANDBOX_PROVIDER": "gvisor"}, clear=True):
            setup = build_sandbox_from_env("e2b", providers=providers)
        self.assertEqual(setup.selected, "e2b")
        self.assertIs(setup.provider, providers["e2b"])

    def test_selection_is_case_insensitive_and_trims_whitespace(self) -> None:
        providers = _fake_registry(gvisor=True, e2b=False, **{"vercel-sandbox": False}, daytona=False)
        setup = build_sandbox_from_env("  GVisor  ", providers=providers)
        self.assertEqual(setup.selected, "gvisor")

    def test_selecting_an_inactive_provider_raises(self) -> None:
        providers = _fake_registry(gvisor=False, e2b=False, **{"vercel-sandbox": False}, daytona=False)
        with self.assertRaises(SandboxSelectionError):
            build_sandbox_from_env("gvisor", providers=providers)

    def test_selecting_an_unknown_name_raises_and_lists_real_names(self) -> None:
        providers = _fake_registry(gvisor=True, e2b=False, **{"vercel-sandbox": False}, daytona=False)
        with self.assertRaises(SandboxSelectionError) as ctx:
            build_sandbox_from_env("openai-sandbox", providers=providers)
        message = str(ctx.exception)
        self.assertIn("daytona", message)
        self.assertIn("e2b", message)
        self.assertIn("gvisor", message)
        self.assertIn("vercel-sandbox", message)


class TestRealRegistryWiring(unittest.TestCase):
    """Confirms the real registry names the correct real driver classes, without ever
    instantiating or calling `.active` on a real one - `GVisorSandboxProvider.active` makes a real
    local Docker socket connection attempt, which no automated test in this suite may do."""

    def test_registry_maps_every_name_to_the_correct_real_driver_class(self) -> None:
        from omnistackai_agent_engine.runtime.daytona import DaytonaSandboxProvider
        from omnistackai_agent_engine.runtime.e2b import E2BSandboxProvider
        from omnistackai_agent_engine.runtime.gvisor import GVisorSandboxProvider
        from omnistackai_agent_engine.runtime.sandbox_selection import _SANDBOX_LIFECYCLE_PROVIDERS
        from omnistackai_agent_engine.runtime.vercel_sandbox import VercelSandboxProvider

        self.assertEqual(
            set(_SANDBOX_LIFECYCLE_PROVIDERS), {"gvisor", "e2b", "vercel-sandbox", "daytona"}
        )
        self.assertIs(_SANDBOX_LIFECYCLE_PROVIDERS["gvisor"], GVisorSandboxProvider)
        self.assertIs(_SANDBOX_LIFECYCLE_PROVIDERS["e2b"], E2BSandboxProvider)
        self.assertIs(_SANDBOX_LIFECYCLE_PROVIDERS["vercel-sandbox"], VercelSandboxProvider)
        self.assertIs(_SANDBOX_LIFECYCLE_PROVIDERS["daytona"], DaytonaSandboxProvider)


if __name__ == "__main__":
    unittest.main()

"""Cloud provider drivers: deploy hosts and run sandboxes.

Each driver produces a *plan* — the provider's official-CLI command sequence — activated by the
provider's key env var. The key value is read by the CLI from the environment at execution time and
is NEVER placed into a command or shown in a plan. `run_deploy` executes a plan (opt-in; needs the
provider CLI + key on a network machine). Nothing is run or deployed by importing this module.
"""

from __future__ import annotations

import os
import subprocess

from .contracts import Command, DeployPlan, PreviewPlan, PreviewStep
from .local import LocalRuntimeProvider
from .providers import DEPLOY_SPECS, RUNTIME_SPECS, ProviderSpec

# Deploy provider -> ordered (label, program, args) using the provider's official CLI. No secrets:
# the CLI reads its token from the environment (the key_env in providers.py).
_DEPLOY_RECIPES: dict[str, tuple[tuple[str, str, tuple[str, ...]], ...]] = {
    "vercel": (("deploy", "vercel", ("deploy", "--prod", "--yes")),),
    "netlify": (("deploy", "netlify", ("deploy", "--build", "--prod")),),
    "render": (("deploy", "render", ("deploys", "create", "--wait", "--confirm")),),
    "fly": (("launch", "fly", ("launch", "--now", "--copy-config", "--yes")),
            ("deploy", "fly", ("deploy", "--remote-only"))),
}

# Sandbox provider -> the https URL pattern where the running app is reached (placeholder host).
_SANDBOX_URLS: dict[str, str] = {
    "e2b": "https://<id>.e2b.dev",
    "daytona": "https://<workspace>.daytona.io",
    "fly-machines": "https://<app>.fly.dev",
}


class CloudDeployProvider:
    """Deploys a generated app to a hosting provider via its official CLI."""

    def __init__(self, spec: ProviderSpec, recipe: tuple[tuple[str, str, tuple[str, ...]], ...]) -> None:
        self._spec = spec
        self._recipe = recipe

    @property
    def id(self) -> str:
        return self._spec.name

    @property
    def active(self) -> bool:
        return bool(os.environ.get(self._spec.key_env, "").strip())

    def deploy_plan(self, app_dir: str, target: str) -> DeployPlan:
        steps = tuple(PreviewStep(label, Command(program, args)) for label, program, args in self._recipe)
        return DeployPlan(provider_id=self.id, target=target, app_dir=app_dir, steps=steps)


class CloudSandboxProvider:
    """Runs a generated app in a cloud sandbox. Reuses the target's local run commands; provisioning
    (creating the sandbox and syncing files) is performed by the provider CLI/SDK at execution time."""

    def __init__(self, spec: ProviderSpec, url: str) -> None:
        self._spec = spec
        self._url = url

    @property
    def id(self) -> str:
        return self._spec.name

    @property
    def active(self) -> bool:
        return bool(os.environ.get(self._spec.key_env, "").strip())

    def preview_plan(self, app_dir: str, target: str) -> PreviewPlan:
        local_plan = LocalRuntimeProvider().preview_plan(app_dir, target)
        return PreviewPlan(
            provider_id=self.id,
            target=target,
            app_dir=app_dir,
            steps=local_plan.steps,
            url=self._url,
        )


def deploy_driver(name: str) -> CloudDeployProvider:
    return CloudDeployProvider(DEPLOY_SPECS[name], _DEPLOY_RECIPES[name])


def sandbox_driver(name: str) -> CloudSandboxProvider:
    return CloudSandboxProvider(RUNTIME_SPECS[name], _SANDBOX_URLS[name])


def run_deploy(plan: DeployPlan) -> None:
    """Execute a deploy plan (opt-in). Requires the provider CLI + key on a network machine. Never
    called by tests or `task verify`."""

    for step in plan.steps:
        subprocess.run([step.command.program, *step.command.args], cwd=plan.app_dir, check=True)

"""Local runtime provider (Tier 0/1): run a generated app on this machine and preview it locally.

`LocalRuntimeProvider.preview_plan` is pure — it returns the install/run commands and the local URL.
`run_preview` is the opt-in executor that actually runs the plan (needs the toolchain + network on a
Tier-0 machine); it is never called by tests or `task verify`.
"""

from __future__ import annotations

import subprocess

from .contracts import Command, PreviewPlan, PreviewStep
from .errors import UnsupportedRuntimeTargetError

LOCAL_PROVIDER_ID = "local"

# target -> (local port, (label, program, args) steps)
_PLANS: dict[str, tuple[int, tuple[tuple[str, str, tuple[str, ...]], ...]]] = {
    "nextjs-web": (3000, (("install", "pnpm", ("install",)), ("dev", "pnpm", ("dev",)))),
    "nextjs-admin": (3001, (("install", "pnpm", ("install",)), ("dev", "pnpm", ("dev", "--port", "3001")))),
    "backend-python": (8000, (
        ("install", "pip", ("install", "-r", "requirements.txt")),
        ("serve", "uvicorn", ("app.main:app", "--port", "8000", "--reload")),
    )),
    "backend-go": (8080, (("run", "go", ("run", ".")),)),
}


class LocalRuntimeProvider:
    """Produces preview plans that run a generated app locally at a loopback URL."""

    @property
    def id(self) -> str:
        return LOCAL_PROVIDER_ID

    def supports(self, target: str) -> bool:
        return target in _PLANS

    def preview_plan(self, app_dir: str, target: str) -> PreviewPlan:
        try:
            port, raw_steps = _PLANS[target]
        except KeyError as error:
            raise UnsupportedRuntimeTargetError(
                f"local runtime has no plan for target {target!r}; known: {', '.join(sorted(_PLANS))}"
            ) from error
        steps = tuple(PreviewStep(label, Command(program, args)) for label, program, args in raw_steps)
        return PreviewPlan(
            provider_id=self.id,
            target=target,
            app_dir=app_dir,
            steps=steps,
            url=f"http://127.0.0.1:{port}",
        )


def run_preview(plan: PreviewPlan) -> None:
    """Execute a preview plan on this machine (Tier 0/1). Requires the toolchain and network.

    Runs each step in the plan's app_dir; the final run/serve step blocks until interrupted. Never
    called by tests or `task verify`.
    """

    for step in plan.steps:
        subprocess.run([step.command.program, *step.command.args], cwd=plan.app_dir, check=True)

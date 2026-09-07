"""Combined per-app project plan: how to preview, verify, and (optionally) deploy each generated app.

Composes the assembler's app layout (R-232 `assembled_targets`), the runtime preview plans
(R-233 `LocalRuntimeProvider`), the verifiable-engineering verify plans (R-235 `verify_plan`), and —
only when a key-activated `DeploymentProvider` is supplied — the deploy plans (R-234) into one
structured, JSON-serializable view a console/CLI can render. Pure and deterministic: it only *builds*
plans; nothing is installed, run, verified, or deployed here, and no key value is ever included.
"""

from __future__ import annotations

from dataclasses import dataclass

from .application_ir import ApplicationIR
from .codegen import assembled_targets
from .runtime import DeploymentProvider, DeployPlan, LocalRuntimeProvider, PreviewPlan
from .verify import VerifyPlan, supported_targets, verify_plan


@dataclass(frozen=True, slots=True)
class AppPlan:
    """One assembled app plus its preview / verify / deploy plans (any of which may be absent)."""

    label: str
    app_dir: str
    target: str
    preview: PreviewPlan | None
    verify: VerifyPlan | None
    deploy: DeployPlan | None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"label": self.label, "appDir": self.app_dir, "target": self.target}
        data["preview"] = (
            None
            if self.preview is None
            else {"url": self.preview.url, "steps": [step.command.display() for step in self.preview.steps]}
        )
        data["verify"] = (
            None
            if self.verify is None
            else {
                "gates": [kind.value for kind in self.verify.gates()],
                "steps": [
                    {"kind": step.kind.value, "command": step.command.display()} for step in self.verify.steps
                ],
            }
        )
        data["deploy"] = (
            None
            if self.deploy is None
            else {
                "provider": self.deploy.provider_id,
                "steps": [step.command.display() for step in self.deploy.steps],
            }
        )
        return data


@dataclass(frozen=True, slots=True)
class ProjectPlan:
    """The combined plan for every app an Application IR assembles."""

    app_name: str
    apps: tuple[AppPlan, ...]

    def to_dict(self) -> dict[str, object]:
        return {"appName": self.app_name, "apps": [app.to_dict() for app in self.apps]}

    def render(self) -> str:
        lines = [f"Project plan for '{self.app_name}':"]
        for app in self.apps:
            lines.append("")
            lines.append(f"- {app.label}  [{app.target}]  ({app.app_dir})")
            if app.preview is not None:
                lines.append(f"    preview -> {app.preview.url}")
                for step in app.preview.steps:
                    lines.append(f"      run: {step.command.display()}")
            if app.verify is not None:
                lines.append(f"    verify gates: {', '.join(kind.value for kind in app.verify.gates())}")
            if app.deploy is not None:
                lines.append(f"    deploy ({app.deploy.provider_id}):")
                for step in app.deploy.steps:
                    lines.append(f"      {step.command.display()}")
        return "\n".join(lines)


def build_project_plan(ir: ApplicationIR, *, deploy: DeploymentProvider | None = None) -> ProjectPlan:
    """Build the combined preview/verify/(deploy) plan for every app the IR assembles."""

    if not isinstance(ir, ApplicationIR):
        raise TypeError("build_project_plan expects an ApplicationIR")

    runtime = LocalRuntimeProvider()
    verify_supported = set(supported_targets())
    apps: list[AppPlan] = []
    for app in assembled_targets(ir):
        preview = runtime.preview_plan(app.directory, app.target) if runtime.supports(app.target) else None
        verify = verify_plan(app.target, app.directory) if app.target in verify_supported else None
        deploy_plan = deploy.deploy_plan(app.directory, app.target) if deploy is not None else None
        apps.append(AppPlan(app.label, app.directory, app.target, preview, verify, deploy_plan))
    return ProjectPlan(ir.name, tuple(apps))

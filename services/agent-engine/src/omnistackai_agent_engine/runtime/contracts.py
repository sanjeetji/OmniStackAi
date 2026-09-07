"""Vendor-neutral runtime (preview/sandbox) and deployment provider contracts (Brief 51, 75).

Providers produce *plans* (validated command descriptions + a URL), not side effects. Executing a plan
is a separate opt-in step (`local.run_preview`) that runs on a network-capable machine (Tier 0/1) or,
for cloud tiers, is carried out by a key-activated provider. Keeping planning pure makes the whole
layer deterministic and offline-testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from .errors import RuntimeProviderError

_ID = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _text(value: str, name: str, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value or _CONTROL.search(value) or len(value) > maximum:
        raise RuntimeProviderError(f"{name} must be a non-empty control-free string within the limit")
    return value


@dataclass(frozen=True, slots=True)
class Command:
    """A command to run, described (not executed) here."""

    program: str
    args: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.program, "command program", 128)
        if not isinstance(self.args, tuple) or any(not isinstance(a, str) or _CONTROL.search(a) for a in self.args):
            raise RuntimeProviderError("command args must be control-free strings")

    def display(self) -> str:
        return " ".join([self.program, *self.args])


@dataclass(frozen=True, slots=True)
class PreviewStep:
    label: str
    command: Command

    def __post_init__(self) -> None:
        _text(self.label, "step label", 128)
        if not isinstance(self.command, Command):
            raise RuntimeProviderError("step command must be a Command")


@dataclass(frozen=True, slots=True)
class PreviewPlan:
    """How to install and run one app locally, and where to view it."""

    provider_id: str
    target: str
    app_dir: str
    steps: tuple[PreviewStep, ...]
    url: str

    def __post_init__(self) -> None:
        _text(self.provider_id, "provider_id", 64)
        _text(self.target, "target", 64)
        _text(self.app_dir, "app_dir", 400)
        if not isinstance(self.steps, tuple) or not self.steps or any(not isinstance(s, PreviewStep) for s in self.steps):
            raise RuntimeProviderError("steps must be a non-empty tuple of PreviewStep")
        if not self.url.startswith(("http://127.0.0.1", "http://localhost", "https://")):
            raise RuntimeProviderError("url must be a loopback or https URL")


@dataclass(frozen=True, slots=True)
class DeployPlan:
    provider_id: str
    target: str
    app_dir: str
    steps: tuple[PreviewStep, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _text(self.provider_id, "provider_id", 64)
        _text(self.target, "target", 64)
        _text(self.app_dir, "app_dir", 400)
        if not isinstance(self.steps, tuple) or any(not isinstance(s, PreviewStep) for s in self.steps):
            raise RuntimeProviderError("steps must be a tuple of PreviewStep")


@runtime_checkable
class RuntimeProvider(Protocol):
    """Produces a PreviewPlan for a generated app target."""

    @property
    def id(self) -> str: ...

    def preview_plan(self, app_dir: str, target: str) -> PreviewPlan: ...


@runtime_checkable
class DeploymentProvider(Protocol):
    """Produces a DeployPlan for a generated app target; `active` reflects key presence."""

    @property
    def id(self) -> str: ...

    @property
    def active(self) -> bool: ...

    def deploy_plan(self, app_dir: str, target: str) -> DeployPlan: ...

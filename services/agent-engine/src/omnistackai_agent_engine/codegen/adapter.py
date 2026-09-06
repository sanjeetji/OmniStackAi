"""Framework adapter contract and registry.

A `FrameworkAdapter` turns an Application IR into a `GeneratedProject` for one `GenerationTarget`.
Product/agent code selects an adapter only through the `AdapterRegistry`, never a concrete class, so
new targets plug in without touching callers.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from ..application_ir import ApplicationIR
from .errors import DuplicateAdapterError, UnsupportedTargetError
from .files import GeneratedProject


class GenerationTarget(StrEnum):
    NEXTJS_WEB = "nextjs-web"
    NEXTJS_ADMIN = "nextjs-admin"
    BACKEND_GO = "backend-go"
    BACKEND_PYTHON = "backend-python"
    BACKEND_NODE = "backend-node"
    FLUTTER = "flutter"
    REACT_NATIVE = "react-native"
    NATIVE_ANDROID = "native-android"
    NATIVE_IOS = "native-ios"


@runtime_checkable
class FrameworkAdapter(Protocol):
    """Port implemented by every framework code generator."""

    @property
    def target(self) -> GenerationTarget: ...

    def generate(self, ir: ApplicationIR) -> GeneratedProject: ...


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[GenerationTarget, FrameworkAdapter] = {}

    def register(self, adapter: object) -> None:
        if not isinstance(adapter, FrameworkAdapter):
            raise UnsupportedTargetError("adapter does not implement the FrameworkAdapter contract")
        target = adapter.target
        if not isinstance(target, GenerationTarget):
            raise UnsupportedTargetError("adapter target must be a GenerationTarget")
        if target in self._adapters:
            raise DuplicateAdapterError(f"adapter already registered for target: {target.value}")
        self._adapters[target] = adapter

    def get(self, target: GenerationTarget | str) -> FrameworkAdapter:
        try:
            resolved = target if isinstance(target, GenerationTarget) else GenerationTarget(target)
        except ValueError as error:
            raise UnsupportedTargetError(f"unknown generation target: {target!r}") from error
        try:
            return self._adapters[resolved]
        except KeyError as error:
            raise UnsupportedTargetError(f"no adapter registered for target: {resolved.value}") from error

    def targets(self) -> tuple[GenerationTarget, ...]:
        return tuple(sorted(self._adapters, key=lambda member: member.value))

    def __len__(self) -> int:
        return len(self._adapters)

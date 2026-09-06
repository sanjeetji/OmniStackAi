"""Code-generation boundary: generated file-set model, adapter contract, and registry."""

from .adapter import AdapterRegistry, FrameworkAdapter, GenerationTarget
from .errors import (
    CodegenError,
    DuplicateAdapterError,
    DuplicateFileError,
    GenerationError,
    InvalidGeneratedFileError,
    UnsupportedTargetError,
)
from .files import GeneratedFile, GeneratedProject

__all__ = [
    "AdapterRegistry",
    "CodegenError",
    "DuplicateAdapterError",
    "DuplicateFileError",
    "FrameworkAdapter",
    "GeneratedFile",
    "GeneratedProject",
    "GenerationError",
    "GenerationTarget",
    "InvalidGeneratedFileError",
    "UnsupportedTargetError",
]

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
from .backend_go import GoBackendAdapter
from .backend_python import PythonBackendAdapter
from .files import GeneratedFile, GeneratedProject
from .nextjs import NextjsWebAdapter

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
    "GoBackendAdapter",
    "InvalidGeneratedFileError",
    "NextjsWebAdapter",
    "PythonBackendAdapter",
    "UnsupportedTargetError",
]

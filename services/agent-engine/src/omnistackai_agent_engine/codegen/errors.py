"""Stable, boundary-safe errors for code generation."""


class CodegenError(Exception):
    """Base error for the code-generation boundary."""

    code = "codegen_error"


class InvalidGeneratedFileError(CodegenError):
    code = "invalid_generated_file"


class DuplicateFileError(CodegenError):
    code = "duplicate_file"


class UnsupportedTargetError(CodegenError):
    code = "unsupported_target"


class DuplicateAdapterError(CodegenError):
    code = "duplicate_adapter"


class GenerationError(CodegenError):
    code = "generation_error"

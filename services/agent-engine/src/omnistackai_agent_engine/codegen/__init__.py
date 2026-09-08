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
from .assembler import (
    MONOREPO_TARGET,
    AssembledApp,
    assemble_project,
    assembled_targets,
    default_registry,
)
from .backend_go import GoBackendAdapter
from .backend_python import PythonBackendAdapter
from .data_access import go_data_access_files, python_data_access_files
from .field_validation import (
    VALIDATOR_REQUIRE,
    FieldRules,
    go_validate_file,
    parse_field_rules,
)
from .files import GeneratedFile, GeneratedProject
from .nextjs import (
    NextjsWebAdapter,
    render_hooks,
    render_screen_page,
    render_toast_component,
)
from .openapi import render_openapi, render_openapi_json
from .schema_sql import render_postgres_schema, table_name
from .seed_sql import render_postgres_seed

__all__ = [
    "AdapterRegistry",
    "AssembledApp",
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
    "MONOREPO_TARGET",
    "NextjsWebAdapter",
    "PythonBackendAdapter",
    "UnsupportedTargetError",
    "FieldRules",
    "VALIDATOR_REQUIRE",
    "assemble_project",
    "assembled_targets",
    "default_registry",
    "go_validate_file",
    "parse_field_rules",
    "go_data_access_files",
    "python_data_access_files",
    "render_hooks",
    "render_screen_page",
    "render_toast_component",
    "render_postgres_schema",
    "render_postgres_seed",
    "render_openapi",
    "render_openapi_json",
    "table_name",
]

"""Arkais Academic Visual Assets & Scientific Table Registry.

Provides schema validation, local catalog management, and stylometric weaving
integration for publication-grade scientific figures and tables.
"""

from arkais.templates.catalog import (
    DEFAULT_REGISTRY_URL,
    SyncResult,
    TemplateCatalog,
    TemplateNotFoundError,
    get_default_catalog,
)
from arkais.templates.compiler import (
    CompilationError,
    RenderFormat,
    RenderOutput,
    TemplateCompiler,
    render_template,
)
from arkais.templates.models import (
    AssetCategory,
    Discipline,
    EngineType,
    ParameterDefinition,
    ParameterType,
    SignatureIntegration,
    TemplateEnvelope,
    WeavingArchetype,
)
from arkais.templates.validator import (
    TemplateValidationError,
    benchmark_validation_speed,
    get_json_schema,
    validate_against_json_schema,
    validate_template_dict,
    validate_template_file,
    validate_template_json,
)
from arkais.templates.weaver import (
    RhetoricalWeaver,
    WeavingResult,
    weave_template_prose,
)

__all__ = [
    # Enums & Models
    "AssetCategory",
    "Discipline",
    "EngineType",
    "ParameterDefinition",
    "ParameterType",
    "SignatureIntegration",
    "TemplateEnvelope",
    "WeavingArchetype",
    # Validation
    "TemplateValidationError",
    "benchmark_validation_speed",
    "get_json_schema",
    "validate_against_json_schema",
    "validate_template_dict",
    "validate_template_file",
    "validate_template_json",
    # Catalog & Storage
    "DEFAULT_REGISTRY_URL",
    "SyncResult",
    "TemplateCatalog",
    "TemplateNotFoundError",
    "get_default_catalog",
    # Compiler & Vector Rendering
    "CompilationError",
    "RenderFormat",
    "RenderOutput",
    "TemplateCompiler",
    "render_template",
    # In-Prose Rhetorical Weaving (GATE-07/GATE-08)
    "RhetoricalWeaver",
    "WeavingResult",
    "weave_template_prose",
]

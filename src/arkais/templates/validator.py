"""Fast validation routines for Arkais Visual Asset Envelopes.

Provides both sub-millisecond Pydantic v2 runtime validation and draft-07
JSON Schema conformance checking for cross-platform integration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import time

import jsonschema
from pydantic import ValidationError

from arkais.templates.models import TemplateEnvelope

# Path to the canonical JSON Schema draft
_SCHEMA_PATH = Path(__file__).parent / "schema" / "arkais-template-schema.v1.json"
_CACHED_SCHEMA: Optional[Dict[str, Any]] = None


class TemplateValidationError(Exception):
    """Raised when an asset template fails schema or semantic validation."""

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.message = message
        self.errors = errors or []

    def __str__(self) -> str:
        if not self.errors:
            return self.message
        error_details = "\n  • ".join(self.errors)
        return f"{self.message}\nValidation Details:\n  • {error_details}"


def get_json_schema() -> Dict[str, Any]:
    """Load and cache the canonical JSON schema."""
    global _CACHED_SCHEMA
    if _CACHED_SCHEMA is None:
        if not _SCHEMA_PATH.exists():
            raise FileNotFoundError(f"Schema file not found at: {_SCHEMA_PATH}")
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            _CACHED_SCHEMA = json.load(f)
    return _CACHED_SCHEMA


def validate_template_dict(data: Dict[str, Any]) -> TemplateEnvelope:
    """Validate a template dictionary against Pydantic models with sub-millisecond performance.

    Args:
        data: Raw template dictionary.

    Returns:
        Validated TemplateEnvelope instance.

    Raises:
        TemplateValidationError: If validation fails.
    """
    try:
        return TemplateEnvelope.from_dict(data)
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc = " -> ".join(str(p) for p in err["loc"])
            errors.append(f"{loc}: {err['msg']}")
        raise TemplateValidationError(
            f"Template validation failed for ID '{data.get('id', 'UNKNOWN')}':",
            errors=errors
        ) from e
    except Exception as e:
        raise TemplateValidationError(f"Invalid template format: {str(e)}") from e


def validate_template_json(json_str: str) -> TemplateEnvelope:
    """Validate a raw JSON string template.

    Args:
        json_str: JSON formatted string.

    Returns:
        Validated TemplateEnvelope instance.

    Raises:
        TemplateValidationError: If parsing or validation fails.
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise TemplateValidationError(f"JSON parsing error: {e.msg} at line {e.lineno}, col {e.colno}") from e

    if not isinstance(data, dict):
        raise TemplateValidationError(f"Expected top-level JSON object, got {type(data).__name__}")

    return validate_template_dict(data)


def validate_template_file(path: Union[str, Path]) -> TemplateEnvelope:
    """Validate a template JSON file from disk.

    Args:
        path: Path to the .json template file.

    Returns:
        Validated TemplateEnvelope instance.

    Raises:
        TemplateValidationError: If file does not exist or content is invalid.
    """
    p = Path(path)
    if not p.is_file():
        raise TemplateValidationError(f"Template file not found: {p}")
    try:
        content = p.read_text(encoding="utf-8")
        return validate_template_json(content)
    except Exception as e:
        if isinstance(e, TemplateValidationError):
            raise
        raise TemplateValidationError(f"Failed to read template '{p}': {str(e)}") from e


def validate_against_json_schema(data: Dict[str, Any]) -> List[str]:
    """Validate data against canonical JSON Schema v1 via jsonschema validator.

    Args:
        data: Dictionary to check against the schema.

    Returns:
        List of error strings (empty if completely valid).
    """
    schema = get_json_schema()
    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for error in validator.iter_errors(data):
        path = " -> ".join(str(p) for p in error.path) or "root"
        errors.append(f"[{path}] {error.message}")
    return errors


def benchmark_validation_speed(data: Dict[str, Any], iterations: int = 500) -> float:
    """Measure average validation time in microseconds per call.

    Args:
        data: Sample template payload.
        iterations: Number of test iterations.

    Returns:
        Average time in microseconds (µs).
    """
    # Warmup
    for _ in range(10):
        validate_template_dict(data)

    start = time.perf_counter()
    for _ in range(iterations):
        validate_template_dict(data)
    elapsed = time.perf_counter() - start

    avg_microseconds = (elapsed / iterations) * 1_000_000.0
    return avg_microseconds

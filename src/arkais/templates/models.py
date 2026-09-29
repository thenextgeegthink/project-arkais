"""Arkais Visual Asset & Scientific Table Envelope Models.

Defines the Pydantic v2 schemas and validation contracts for publication-grade
templates used across Project Arkais CLI, SDK, and Manuscript compilers.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AssetCategory(str, Enum):
    """Broad asset classification."""
    FIGURES = "figures"
    TABLES = "tables"


class Discipline(str, Enum):
    """Target academic discipline."""
    PHYSICS = "physics"
    COMPUTER_SCIENCE = "computer_science"
    MEDICINE = "medicine"
    ECONOMICS = "economics"
    ENGINEERING = "engineering"
    GENERAL = "general"


class EngineType(str, Enum):
    """Declarative visual rendering engine."""
    VEGA_LITE = "vega-lite"
    LATEX_BOOKTABS = "latex-booktabs"
    MATPLOTLIB = "matplotlib"
    MERMAID = "mermaid"
    SVG_CUSTOM = "svg-custom"


class WeavingArchetype(str, Enum):
    """Scholarly in-prose rhetorical integration pattern."""
    PARENTHETICAL_GROUNDING = "parenthetical_grounding"
    LEAD_IN_ASSERTION = "lead_in_assertion"
    COMPARATIVE_DELTA = "comparative_delta"
    METHODOLOGICAL_PROTOCOL = "methodological_protocol"
    TABULAR_BASELINE = "tabular_baseline"


class ParameterType(str, Enum):
    """Supported parameter types."""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    COLOR = "color"


class SignatureIntegration(BaseModel):
    """Arkais stylometric audit and in-prose rhetorical integration config."""
    model_config = ConfigDict(extra="forbid")

    recommended_gate: str = Field(
        default="GATE-07",
        pattern=r"^GATE-[0-9]{2}$",
        description="Arkais audit gate enforcing this asset (GATE-07 or GATE-08)."
    )
    weaving_archetype: WeavingArchetype = Field(
        description="Rhetorical archetype governing scholarly text integration."
    )
    in_prose_blueprint: str = Field(
        min_length=10,
        description="Format string for parenthetical or lead-in in-prose weaving."
    )
    required_metrics: List[str] = Field(
        default_factory=list,
        description="List of metric slots required by the blueprint (e.g. p_value, sample_size)."
    )
    unit_discipline: Optional[str] = Field(
        default="GATE-08",
        description="Physical unit standard adhering to GATE-08."
    )
    grounding_rules: List[str] = Field(
        default_factory=list,
        description="Stylometric assertions preventing hallucinated visual references."
    )

    @field_validator("in_prose_blueprint")
    @classmethod
    def validate_no_detached_pointers(cls, v: str) -> str:
        """Reject conversational detached pointer anti-patterns like 'Figure 1 shows'."""
        detached_patterns = [
            r"(?:Figure|Table|Fig\.)\s+[0-9a-zA-Z\.\{\}_]+\s+(?:shows|illustrates|depicts|presents|demonstrates)"
        ]
        for pat in detached_patterns:
            if re.search(pat, v, re.IGNORECASE):
                raise ValueError(
                    f"Blueprint violates GATE-07: Detached phrasing detected ('{v}'). "
                    "Use integrated parenthetical grounding (e.g., '...reaches a minimum ({fig_ref})...')."
                )
        return v


class ParameterDefinition(BaseModel):
    """Specification for a configurable parameter inside a template."""
    model_config = ConfigDict(extra="forbid")

    type: ParameterType
    description: str
    default: Optional[Any] = None
    choices: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class TemplateEnvelope(BaseModel):
    """Complete declarative asset envelope for scientific figures and tables."""
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    schema_uri: Optional[str] = Field(
        default="https://arkais.geegthink.com/schemas/v1/template.json",
        alias="$schema",
        description="Optional schema URI."
    )
    id: str = Field(
        pattern=r"^(fig|tbl)\.[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+\.v[0-9]+$",
        description="Canonical identifier: {type}.{discipline}.{archetype}.{name}.v{version}."
    )
    version: str = Field(
        pattern=r"^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$",
        description="Semantic version string."
    )
    name: str = Field(
        min_length=3,
        max_length=160,
        description="Human-readable title for catalog indexing."
    )
    description: Optional[str] = Field(
        default=None,
        description="Scholarly description and visual encoding summary."
    )
    category: AssetCategory = Field(
        description="Category: figures or tables."
    )
    discipline: Discipline = Field(
        description="Scientific discipline domain."
    )
    tags: List[str] = Field(
        min_length=1,
        description="Taxonomy tags for semantic search."
    )
    engine: EngineType = Field(
        description="Target rendering engine (vega-lite, latex-booktabs, etc.)."
    )
    min_engine_version: Optional[str] = Field(
        default=None,
        description="Minimum engine version requirement."
    )
    author: str = Field(
        default="The Next Geek Think (NGT)",
        description="Author or maintainer organization."
    )
    license: str = Field(
        default="Apache-2.0",
        description="SPDX license string."
    )
    provenance_ark: Optional[str] = Field(
        default=None,
        pattern=r"^ARK-[0-9]{3,5}$",
        description="Historical corpus accession ID motivating this archetype."
    )
    signature_integration: SignatureIntegration = Field(
        description="Stylometric weaving blueprint and audit parameters."
    )
    caption_blueprint: Optional[str] = Field(
        default=None,
        description="Academic caption format string."
    )
    notes: Optional[str] = Field(
        default=None,
        description="Footnotes, significance levels, or methodology annotations."
    )
    parameters: Optional[Dict[str, ParameterDefinition]] = Field(
        default=None,
        description="Configurable template parameters."
    )
    spec: Union[Dict[str, Any], str] = Field(
        description="Engine-specific specification (Vega-Lite JSON or LaTeX code)."
    )
    sample_data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = Field(
        default=None,
        description="Out-of-the-box sample dataset."
    )

    @model_validator(mode="after")
    def validate_category_prefix_alignment(self) -> "TemplateEnvelope":
        """Verify that 'fig' ID prefix matches 'figures' and 'tbl' matches 'tables'."""
        prefix = self.id.split(".")[0]
        if prefix == "fig" and self.category != AssetCategory.FIGURES:
            raise ValueError(f"Template ID '{self.id}' has 'fig' prefix but category is '{self.category}'.")
        if prefix == "tbl" and self.category != AssetCategory.TABLES:
            raise ValueError(f"Template ID '{self.id}' has 'tbl' prefix but category is '{self.category}'.")
        return self

    @property
    def title(self) -> str:
        """Alias for name to support title/name polymorphism."""
        return self.name

    def render_prose(self, label: str = "Figure 1", **kwargs: Any) -> str:
        """Render the in-prose rhetorical blueprint with supplied variables."""
        context = {
            "fig_ref": label,
            "tbl_ref": label,
            "label": label,
            **kwargs
        }
        # Validate that all required metrics are provided
        for req in self.signature_integration.required_metrics:
            if req not in kwargs:
                raise KeyError(
                    f"Missing required metric '{req}' to render prose for template '{self.id}'. "
                    f"Required slots: {self.signature_integration.required_metrics}"
                )

        result = self.signature_integration.in_prose_blueprint
        for k, v in context.items():
            result = result.replace(f"{{{k}}}", str(v))
        return result

    def render_caption(self, number: int = 1, title: Optional[str] = None, **kwargs: Any) -> str:
        """Render an academic figure or table caption."""
        prefix = "Figure" if self.category == AssetCategory.FIGURES else "Table"
        actual_title = title or self.name
        if self.caption_blueprint:
            context = {
                "num": number,
                "prefix": prefix,
                "title": actual_title,
                **kwargs
            }
            result = self.caption_blueprint
            for k, v in context.items():
                result = result.replace(f"{{{k}}}", str(v))
            return result
        return f"{prefix} {number}: {actual_title}."

    def to_dict(self) -> Dict[str, Any]:
        """Export envelope to dictionary matching JSON Schema."""
        return self.model_dump(by_alias=True, exclude_none=True)

    def to_json(self, indent: int = 2) -> str:
        """Serialize envelope to JSON formatted string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateEnvelope":
        """Construct and validate TemplateEnvelope from dictionary."""
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, json_str: str) -> "TemplateEnvelope":
        """Construct and validate TemplateEnvelope from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "TemplateEnvelope":
        """Load and validate TemplateEnvelope from file path."""
        p = Path(path)
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

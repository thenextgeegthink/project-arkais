"""Unit tests for Arkais Visual Asset & Scientific Table Envelope models and validator."""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from arkais.templates.models import (
    AssetCategory,
    Discipline,
    EngineType,
    SignatureIntegration,
    TemplateEnvelope,
    WeavingArchetype,
)
from arkais.templates.validator import (
    TemplateValidationError,
    benchmark_validation_speed,
    validate_against_json_schema,
    validate_template_dict,
    validate_template_file,
    validate_template_json,
)


@pytest.fixture
def sample_figure_data() -> dict:
    """Canonical Vega-Lite Pareto Frontier figure template payload."""
    return {
        "$schema": "https://arkais.geegthink.com/schemas/v1/template.json",
        "id": "fig.physics.scatter.pareto_frontier.v1",
        "version": "1.0.0",
        "name": "Bi-Objective Pareto Frontier with 95% Confidence Ellipses",
        "description": "Pareto frontier scatter plot with uncertainty bounds across frequency regimes.",
        "category": "figures",
        "discipline": "physics",
        "tags": ["pareto", "optimization", "confidence-interval", "scatter"],
        "engine": "vega-lite",
        "min_engine_version": ">=2.0.0",
        "author": "The Next Geek Think (NGT)",
        "license": "Apache-2.0",
        "provenance_ark": "ARK-010",
        "signature_integration": {
            "recommended_gate": "GATE-07",
            "weaving_archetype": "parenthetical_grounding",
            "in_prose_blueprint": "Across drive frequencies from {x_min} to {x_max}, magnetic dissipation reaches a global minimum of {y_min} {units} ({fig_ref}), confirming the predicted lattice constraint.",
            "required_metrics": ["x_min", "x_max", "y_min", "units"],
            "unit_discipline": "GATE-08",
            "grounding_rules": ["assert_sub_zero_error", "require_uncertainty_bounds"]
        },
        "caption_blueprint": "{prefix} {num}: {title}. Shaded regions represent 95% bootstrap confidence ellipses.",
        "parameters": {
            "point_size": {
                "type": "integer",
                "description": "Scatter mark radius in points",
                "default": 60,
                "min_value": 10,
                "max_value": 200
            }
        },
        "spec": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": {"type": "point", "filled": True, "size": 60},
            "encoding": {
                "x": {"field": "frequency_mhz", "type": "quantitative", "title": "Frequency (MHz)"},
                "y": {"field": "dissipation_ratio", "type": "quantitative", "title": "Dissipation (10⁻³)"},
                "color": {"field": "regime", "type": "nominal"}
            }
        },
        "sample_data": [
            {"frequency_mhz": 12.5, "dissipation_ratio": 4.12, "regime": "Linear"},
            {"frequency_mhz": 25.0, "dissipation_ratio": 2.85, "regime": "Linear"},
            {"frequency_mhz": 50.0, "dissipation_ratio": 1.15, "regime": "Optimal"},
            {"frequency_mhz": 100.0, "dissipation_ratio": 1.95, "regime": "Turbulent"}
        ]
    }


@pytest.fixture
def sample_table_data() -> dict:
    """Canonical LaTeX Booktabs table template payload."""
    return {
        "$schema": "https://arkais.geegthink.com/schemas/v1/template.json",
        "id": "tbl.cs.benchmarks.model_comparison.v1",
        "version": "1.0.0",
        "name": "Transformer Architecture Latency and Throughput Matrix",
        "description": "Publication-grade booktabs comparison table with parameter counts and FLOPS.",
        "category": "tables",
        "discipline": "computer_science",
        "tags": ["benchmarks", "llm", "latency", "throughput", "booktabs"],
        "engine": "latex-booktabs",
        "author": "The Next Geek Think (NGT)",
        "license": "Apache-2.0",
        "provenance_ark": "ARK-105",
        "signature_integration": {
            "recommended_gate": "GATE-07",
            "weaving_archetype": "tabular_baseline",
            "in_prose_blueprint": "Under equivalent batch constraints, the quantized variant reduces inference latency from {baseline_ms} ms to {optimized_ms} ms ({tbl_ref}) without measurable perplexity degradation.",
            "required_metrics": ["baseline_ms", "optimized_ms"],
            "unit_discipline": "GATE-08"
        },
        "caption_blueprint": "{prefix} {num}: {title}. Evaluation conducted across 1,000 warm-start queries on NVIDIA A100.",
        "notes": "* p < 0.05 against baseline architecture via Welch's two-tailed t-test.",
        "spec": "\\begin{table}[t]\n\\centering\n\\begin{tabular}{lcccc}\n\\toprule\nModel & Params & P50 (ms) & P99 (ms) & Tokens/s \\\\\n\\midrule\nDense-7B & 7.1B & 18.2 & 34.5 & 124.2 \\\\\nMoE-8x7B & 46.7B & 12.4 & 22.1 & 188.6 \\\\\n\\bottomrule\n\\end{tabular}\n\\end{table}",
        "sample_data": [
            {"model": "Dense-7B", "params": "7.1B", "p50_ms": 18.2, "p99_ms": 34.5, "tokens_sec": 124.2},
            {"model": "MoE-8x7B", "params": "46.7B", "p50_ms": 12.4, "p99_ms": 22.1, "tokens_sec": 188.6}
        ]
    }


def test_valid_figure_template(sample_figure_data):
    """Verify clean instantiation and roundtrip serialization of figure envelopes."""
    envelope = validate_template_dict(sample_figure_data)
    assert envelope.id == "fig.physics.scatter.pareto_frontier.v1"
    assert envelope.category == AssetCategory.FIGURES
    assert envelope.discipline == Discipline.PHYSICS
    assert envelope.engine == EngineType.VEGA_LITE
    assert envelope.author == "The Next Geek Think (NGT)"
    assert envelope.parameters["point_size"].type.value == "integer"

    # Round trip JSON test
    json_str = envelope.to_json()
    reloaded = validate_template_json(json_str)
    assert reloaded.id == envelope.id
    assert reloaded.spec == envelope.spec


def test_valid_table_template(sample_table_data):
    """Verify clean instantiation of LaTeX booktabs table envelopes."""
    envelope = validate_template_dict(sample_table_data)
    assert envelope.id == "tbl.cs.benchmarks.model_comparison.v1"
    assert envelope.category == AssetCategory.TABLES
    assert envelope.discipline == Discipline.COMPUTER_SCIENCE
    assert envelope.engine == EngineType.LATEX_BOOKTABS
    assert "\\begin{table}" in envelope.spec


def test_invalid_id_patterns(sample_figure_data):
    """Verify rejection of invalid ID formats and category mismatches."""
    # Bad prefix (not fig or tbl)
    bad_id = sample_figure_data.copy()
    bad_id["id"] = "chart.physics.scatter.pareto.v1"
    with pytest.raises(TemplateValidationError) as exc:
        validate_template_dict(bad_id)
    assert "String should match pattern" in str(exc.value) or "pattern" in str(exc.value).lower()

    # Category mismatch: tbl prefix with figures category
    mismatch = sample_figure_data.copy()
    mismatch["id"] = "tbl.physics.scatter.pareto.v1"
    with pytest.raises(TemplateValidationError) as exc:
        validate_template_dict(mismatch)
    assert "category is 'AssetCategory.figures'" in str(exc.value) or "tbl" in str(exc.value)

    # Missing version component
    no_ver = sample_figure_data.copy()
    no_ver["id"] = "fig.physics.scatter.pareto"
    with pytest.raises(TemplateValidationError):
        validate_template_dict(no_ver)


def test_gate_07_detached_pointer_detection(sample_figure_data):
    """Verify that templates violating GATE-07 with conversational detached pointers are rejected."""
    bad_blueprint = sample_figure_data.copy()
    bad_blueprint["signature_integration"] = dict(sample_figure_data["signature_integration"])
    bad_blueprint["signature_integration"]["in_prose_blueprint"] = "Figure 1 shows that dissipation increases rapidly with frequency."

    with pytest.raises(TemplateValidationError) as exc:
        validate_template_dict(bad_blueprint)
    assert "violates GATE-07" in str(exc.value)
    assert "Detached phrasing detected" in str(exc.value)


def test_prose_rendering(sample_figure_data):
    """Verify in-prose synthesis with supplied quantitative values."""
    envelope = validate_template_dict(sample_figure_data)
    rendered = envelope.render_prose(
        label="(Figure 3)",
        x_min="10 MHz",
        x_max="120 MHz",
        y_min="1.15",
        units="10⁻³"
    )
    assert "Across drive frequencies from 10 MHz to 120 MHz" in rendered
    assert "minimum of 1.15 10⁻³ ((Figure 3))" in rendered

    # Missing metric should raise KeyError
    with pytest.raises(KeyError) as exc:
        envelope.render_prose(label="(Figure 3)", x_min="10 MHz")
    assert "Missing required metric" in str(exc.value)


def test_caption_rendering(sample_figure_data, sample_table_data):
    """Verify academic caption formatting for figures and tables."""
    fig_envelope = validate_template_dict(sample_figure_data)
    fig_caption = fig_envelope.render_caption(number=2)
    assert fig_caption.startswith("Figure 2:")
    assert "Bi-Objective Pareto Frontier" in fig_caption
    assert "bootstrap confidence ellipses" in fig_caption

    tbl_envelope = validate_template_dict(sample_table_data)
    tbl_caption = tbl_envelope.render_caption(number=1)
    assert tbl_caption.startswith("Table 1:")
    assert "Transformer Architecture" in tbl_caption


def test_json_schema_conformance(sample_figure_data, sample_table_data):
    """Verify strict compliance with draft-07 JSON Schema."""
    fig_errors = validate_against_json_schema(sample_figure_data)
    assert fig_errors == [], f"Figure schema errors: {fig_errors}"

    tbl_errors = validate_against_json_schema(sample_table_data)
    assert tbl_errors == [], f"Table schema errors: {tbl_errors}"

    # Verify that illegal properties are rejected by schema additionalProperties=false
    illegal = sample_figure_data.copy()
    illegal["unauthorized_field"] = "malicious_payload"
    illegal_errors = validate_against_json_schema(illegal)
    assert len(illegal_errors) > 0
    assert any("unauthorized_field" in err for err in illegal_errors)


def test_validation_speed_sub_millisecond(sample_figure_data):
    """Verify that validation speed is well under 1,000 microseconds (1 millisecond)."""
    avg_us = benchmark_validation_speed(sample_figure_data, iterations=1000)
    # Validation should comfortably execute under 100 microseconds on modern CPUs (spec requirement is < 1,000 µs)
    assert avg_us < 1000.0, f"Validation took {avg_us:.2f} µs, exceeding 1ms requirement!"


def test_file_validation(sample_figure_data, tmp_path):
    """Verify reading and validating template files directly from disk."""
    file_path = tmp_path / "test_template.json"
    file_path.write_text(json.dumps(sample_figure_data), encoding="utf-8")

    envelope = validate_template_file(file_path)
    assert envelope.id == sample_figure_data["id"]

    # Test non-existent file
    with pytest.raises(TemplateValidationError) as exc:
        validate_template_file(tmp_path / "missing.json")
    assert "not found" in str(exc.value).lower()

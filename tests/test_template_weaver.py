"""Unit tests for Arkais In-Prose Rhetorical Weaving Generator and GATE-07/08 compliance."""

import pytest

from arkais.audit.engine import StylometricAuditEngine
from arkais.templates.catalog import get_default_catalog
from arkais.templates.models import WeavingArchetype
from arkais.templates.weaver import (
    RhetoricalWeaver,
    WeavingResult,
    weave_template_prose,
)


@pytest.fixture
def catalog():
    return get_default_catalog()


@pytest.fixture
def weaver():
    return RhetoricalWeaver()


@pytest.fixture
def audit_engine():
    return StylometricAuditEngine()


def test_weave_figure_prose_gate_07_pass(weaver, catalog):
    """Verify figure weaving generates integrated parenthetical prose that passes GATE-07."""
    envelope = catalog.get("fig.physics.scatter.pareto_frontier.v1")
    result = weaver.weave(
        envelope,
        number=2,
        metrics={"x_min": "10.0 MHz", "x_max": "100.0 MHz", "y_min": "1.15", "units": "10⁻³"}
    )

    assert isinstance(result, WeavingResult)
    assert result.label == "Figure 2"
    assert "(Figure 2)" in result.prose
    assert "Figure 2 shows" not in result.prose
    assert result.gate_07_pass is True
    assert "Across drive frequencies from 10.0 MHz to 100.0 MHz" in result.prose


def test_weave_table_prose_gate_07_pass(weaver, catalog):
    """Verify table weaving generates integrated parenthetical prose that passes GATE-07."""
    envelope = catalog.get("tbl.cs.benchmarks.model_comparison.v1")
    result = weaver.weave(
        envelope,
        number=1,
        metrics={"baseline_ms": "18.2", "optimized_ms": "11.5"}
    )

    assert result.label == "Table 1"
    assert "(Table 1)" in result.prose
    assert "Table 1 shows" not in result.prose
    assert result.gate_07_pass is True
    assert "reduces inference latency from 18.2 ms to 11.5 ms (Table 1)" in result.prose


def test_audit_engine_10_gates_evaluation(weaver, catalog, audit_engine):
    """Audit woven manuscript prose through the StylometricAuditEngine."""
    envelope = catalog.get("fig.cs.convergence.loss_curve.v1")
    result = weaver.weave(
        envelope,
        number=3,
        metrics={"final_loss": "0.18", "optimal_epoch": "20"}
    )

    report = audit_engine(result.prose)
    g7 = next(g for g in report.gate_results if g.gate_id == "GATE-07")
    g8 = next(g for g in report.gate_results if g.gate_id == "GATE-08")

    assert g7.passed is True
    assert g7.score == 1.0
    assert g8.passed is True
    assert g7.details["detached"] == 0
    assert g7.details["parenthetical"] >= 1


def test_weave_manuscript_section(weaver, catalog):
    """Verify synthesizing a publication-grade section block."""
    envelope = catalog.get("tbl.medicine.clinical.demographics_table1.v1")
    section_md = weaver.weave_manuscript_section(
        envelope,
        number=1,
        heading="Baseline Cohort Demographics"
    )

    assert "### Baseline Cohort Demographics" in section_md
    assert "(Table 1)" in section_md
    assert "*Table 1:" in section_md


def test_all_50_templates_weave_successfully(weaver, catalog):
    """Verify all 50 foundational templates weave valid GATE-07 compliant prose."""
    templates = catalog.list()
    assert len(templates) == 50

    for envelope in templates:
        result = weaver.weave(envelope, number=1)
        assert result.gate_07_pass is True, f"Template '{envelope.id}' failed GATE-07!"
        import re
        assert re.search(r"\([^)]*\b(?:Figure|Table|Fig\.)\s+1\b[^)]*\)", result.prose), (
            f"Template '{envelope.id}' missing parenthetical anchor in: '{result.prose}'"
        )




def test_convenience_helper(catalog):
    """Verify top-level weave_template_prose helper."""
    envelope = catalog.get("fig.engineering.controls.bode_frequency_plot.v1")
    res = weave_template_prose(envelope, number=4)
    assert res.label == "Figure 4"
    assert "(Figure 4)" in res.prose

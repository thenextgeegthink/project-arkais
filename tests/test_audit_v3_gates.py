"""Test suite for upgraded v3.0 StylometricAuditEngine gates (Phase 4).

Tests:
1. Broadened GATE-02 (single sentence, pair, em-dash, not merely).
2. Conditional GATE-08 (no manifest returns 'na', manifest verified / fabricated).
3. Coupled GATE-10 (REF-001 phantom citation failure, verified pass).
"""

import pytest
from arkais.audit.engine import StylometricAuditEngine
from arkais.reference.resolver import ReferenceResolver
from arkais.reference.models import ReferenceItem, ResolutionResult


@pytest.fixture
def engine():
    return StylometricAuditEngine()


def test_gate_02_synthetic_contrast_broadened(engine):
    # Single sentence A is not B, but C
    report1 = engine("Direct air capture is not an engineering choice, but rather an imperative.")
    g2_1 = next(g for g in report1.gate_results if g.gate_id == "GATE-02")
    assert g2_1.passed is False
    assert g2_1.status == "fail"

    # Single sentence A is not B, it is C
    report2 = engine("The model is not a database, it is an intelligent cognitive engine.")
    g2_2 = next(g for g in report2.gate_results if g.gate_id == "GATE-02")
    assert g2_2.passed is False

    # Multi-sentence pair
    report3 = engine("The system is not static. This is an adaptive cognitive architecture.")
    g2_3 = next(g for g in report3.gate_results if g.gate_id == "GATE-02")
    assert g2_3.passed is False

    # Em-dash dichotomy
    report4 = engine("It is not a dashboard — it is a mission control center.")
    g2_4 = next(g for g in report4.gate_results if g.gate_id == "GATE-02")
    assert g2_4.passed is False

    # Legitimate scientific negation must pass
    report5 = engine("The observed variance was not statistically significant at p < 0.05.")
    g2_5 = next(g for g in report5.gate_results if g.gate_id == "GATE-02")
    assert g2_5.passed is True
    assert g2_5.status == "pass"


def test_gate_08_conditional_data_manifest(engine):
    prose = "The reactor yielded 45.2 kg at 350 K with 12.5% efficiency."

    # Without manifest -> status == "na", passed == True
    report_no_manifest = engine(prose, manifest=None)
    g8_none = next(g for g in report_no_manifest.gate_results if g.gate_id == "GATE-08")
    assert g8_none.passed is True
    assert g8_none.status == "na"
    assert "returns na without rewarding mere presence of numbers" in g8_none.message

    # With matching manifest -> status == "pass"
    manifest = [
        {"value": 45.2, "unit": "kg", "tolerance_pct": 1.0},
        {"value": 350, "unit": "K", "tolerance_pct": 1.0},
        {"value": 12.5, "unit": "%", "tolerance_pct": 1.0}
    ]
    report_matched = engine(prose, manifest=manifest)
    g8_matched = next(g for g in report_matched.gate_results if g.gate_id == "GATE-08")
    assert g8_matched.passed is True
    assert g8_matched.status == "pass"

    # With missing/unmanifested quantity -> status == "fail"
    partial_manifest = [
        {"value": 45.2, "unit": "kg", "tolerance_pct": 1.0}
    ]
    report_untraced = engine(prose, manifest=partial_manifest)
    g8_untraced = next(g for g in report_untraced.gate_results if g.gate_id == "GATE-08")
    assert g8_untraced.passed is False
    assert g8_untraced.status == "fail"


def test_gate_10_coupled_offline_resolver(engine, monkeypatch):
    prose = "Previous studies demonstrated catalytic conversion at scale (PhantomAuthor, 2024)."

    class MockResolver:
        def verify_citation(self, title, author, year):
            if "Phantom" in author:
                return ResolutionResult(
                    verified=False,
                    confidence=0.1,
                    canonical_doi=None,
                    matched_item=None,
                    status_code="UNVERIFIED_PHANTOM",
                    message="REF-001: Unverified Citation Phantom."
                )
            return ResolutionResult(
                verified=True,
                confidence=1.0,
                canonical_doi="10.1000/182",
                matched_item=None,
                status_code="VERIFIED",
                message="Verified citation."
            )

    resolver = MockResolver()
    report = engine(prose, reference_resolver=resolver)
    g10 = next(g for g in report.gate_results if g.gate_id == "GATE-10")
    assert g10.passed is False
    assert g10.details["phantom_citations"] >= 1
    assert "REF-001" in report.defect_summary[0]

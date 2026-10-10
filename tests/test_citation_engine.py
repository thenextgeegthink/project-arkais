"""Unit tests for CitationFormatter and RhetoricalWeaver (THE-22)."""

import pytest
from pathlib import Path
import sys

# Ensure SDK src is in path for tests
SDK_SRC = Path(__file__).resolve().parent.parent / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from arkais import (
    ArkaisClient,
    ReferenceItem,
    CslCitationFormatter,
    RhetoricalWeaver,
    CitationStyle,
    RhetoricalRole
)


@pytest.fixture
def sample_references():
    keith = ReferenceItem(
        doi="10.1016/j.joule.2018.05.006",
        title="A Process for Capturing CO2 from the Atmosphere",
        authors=["Keith, David W.", "Holmes, Geoffrey", "St. Angelo, David", "Heidel, Kenton"],
        year=2018,
        venue="Joule",
        volume="2",
        issue="8",
        pages="1573-1594"
    )
    lackner = ReferenceItem(
        doi="10.1016/s0040-6031(99)00078-4",
        title="Carbon dioxide extraction from air",
        authors=["Lackner, Klaus S."],
        year=1999,
        venue="Thermochimica Acta",
        volume="335",
        issue="1",
        pages="3-11"
    )
    billet = ReferenceItem(
        doi="10.1016/0009-2509(94)00215-m",
        title="Mass transfer and pressure drop in structured packings",
        authors=["Billet, Reinhard", "Schultes, Michael"],
        year=1994,
        venue="Chemical Engineering Science",
        volume="49",
        issue="15",
        pages="2389-2400"
    )
    return keith, lackner, billet


def test_rhetorical_weaving(sample_references):
    keith, lackner, billet = sample_references
    weaver = RhetoricalWeaver()

    # 1. Integral Subject
    s1 = weaver.weave(
        keith,
        role=RhetoricalRole.INTEGRAL_SUBJECT,
        verb="demonstrated",
        claim_context="packing density dictates mass transfer efficiency."
    )
    assert s1 == "Keith and colleagues (2018) demonstrated that packing density dictates mass transfer efficiency."

    # 2. Integral Passive
    s2 = weaver.weave(
        billet,
        role=RhetoricalRole.INTEGRAL_PASSIVE,
        verb="formulated",
        claim_context="gas-liquid contact dynamics follow two-phase hydraulic equilibria."
    )
    assert s2 == "As formulated by Billet and Schultes (1994), gas-liquid contact dynamics follow two-phase hydraulic equilibria."

    # 3. Contrastive Tension
    s3 = weaver.weave(
        lackner,
        role=RhetoricalRole.CONTRASTIVE_TENSION,
        claim_context="regeneration requires an asymptotic thermodynamic threshold of 1.4 GJ/t."
    )
    assert s3 == "While Lackner (1999) posited that regeneration requires an asymptotic thermodynamic threshold of 1.4 GJ/t."

    # 4. Methodological Anchor
    s4 = weaver.weave(
        keith,
        role=RhetoricalRole.METHODOLOGICAL
    )
    assert s4 == "following the protocol described in (Keith et al., 2018)"

    # 5. Consensus Cluster
    cluster = weaver.weave_cluster([lackner, keith])
    assert cluster == "(Lackner, 1999; Keith et al., 2018)"


def test_client_citation_integration(sample_references):
    keith, lackner, billet = sample_references
    # D-1 / THE-75: the client refuses to build without a contact identity rather than falling
    # back to a hardcoded address. RFC 2606 reserved, deliberately non-routable — the same
    # constant test_reference_resolver.py uses.
    client = ArkaisClient(contact_email="arkais-tests@example.com")

    # Client convenience formatters
    in_text = client.format_citation(keith, style=CitationStyle.APA_7TH)
    assert in_text == "(Keith et al., 2018)"

    bib = client.format_bibliography([keith, lackner, billet], style=CitationStyle.APA_7TH)
    assert len(bib) == 3
    # Every requested source renders exactly once: no entry dropped, none duplicated. The
    # *order* is the style's business, not the caller's — IEEE and Nature are numeric styles
    # that must stay in citation order, so asserting APA-alphabetical here would encode a
    # rule that is wrong for the rest of CitationStyle.
    joined = "\n".join(bib)
    for ref in (keith, lackner, billet):
        assert joined.count(ref.doi) == 1, f"{ref.doi} missing or duplicated in the bibliography"
    assert "Billet" in joined and "Keith" in joined and "Lackner" in joined

    weaved = client.weave_citation(keith, role=RhetoricalRole.INTEGRAL_SUBJECT, verb="confirmed", claim_context="regeneration costs scale non-linearly.")
    assert "Keith and colleagues (2018) confirmed that" in weaved

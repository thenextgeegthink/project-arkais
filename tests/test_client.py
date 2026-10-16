"""Unit tests for ArkaisClient and Core SDK functionality."""

import pytest
from pathlib import Path
import sys

# Ensure SDK src is in path for tests
SDK_SRC = Path(__file__).resolve().parent.parent / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from arkais import (
    ArkaisClient,
    ArkaisConfig,
    SignatureProfile,
    AuditReport,
    RedactedSecret,
    CredentialSecurityError
)

#: D-1 / THE-75 made a contact identity mandatory rather than falling back to a hardcoded
#: address. RFC 2606 reserved, deliberately non-routable.
TEST_CONTACT_EMAIL = "arkais-tests@example.com"



def test_client_initialization():
    client = ArkaisClient(contact_email=TEST_CONTACT_EMAIL)
    assert client is not None
    assert client.config.default_signature == "ARKAIS-v3.0"


def test_signature_management():
    client = ArkaisClient(contact_email=TEST_CONTACT_EMAIL)
    signatures = client.signatures.list()
    assert "ARKAIS-v3.0" in signatures
    assert "ARKAIS-v2.1" in signatures
    assert "ARKAIS-001-v1.1" in signatures
    assert "ARKAIS-001-v2.0" in signatures

    # Canonical v3.0 signature (Default)
    sig_v30 = client.signatures.get("ARKAIS-v3.0")
    assert isinstance(sig_v30, SignatureProfile)
    assert sig_v30.identifier == "ARKAIS-v3.0"
    assert "10,000 Landmark Corpus Papers" in sig_v30.corpus_size

    # Active baseline v2.1 signature
    sig_v21 = client.signatures.get("ARKAIS-v2.1")
    assert isinstance(sig_v21, SignatureProfile)
    assert sig_v21.identifier == "ARKAIS-v2.1"
    assert "5,000 Calibrated Authentic Papers" in sig_v21.corpus_size

    # Historical v1.1 signature
    sig = client.signatures.get("ARKAIS-001-v1.1")
    assert isinstance(sig, SignatureProfile)
    assert sig.identifier == "ARKAIS-001-v1.1"
    assert "100 Landmark Papers" in sig.corpus_size
    assert len(sig.raw_markdown) > 500

    # Backward-compatible alias lookup
    sig2 = client.signatures.get("ARKAIS-001-v2.0")
    assert isinstance(sig2, SignatureProfile)
    assert "5,000 Calibrated Authentic Papers" in sig2.corpus_size


def test_audit_clean_prose():
    client = ArkaisClient(contact_email=TEST_CONTACT_EMAIL)
    clean_academic_text = """
    Direct air capture configurations operating under high thermodynamic irreversibility 
    exhibit non-linear capital scaling as regeneration temperatures increase (Figure 2b). 
    Early empirical pilots demonstrated that structured packings achieve surface wetting 
    densities exceeding 450 m2/m3 without solvent degradation (Keith et al., 2018). 
    Independent thermodynamic measurements indicate asymptotic heat recovery boundaries 
    at 1.4 GJ/t under ambient conditions (Lackner, 1999).
    """

    report = client.evaluate_draft(clean_academic_text)
    assert isinstance(report, AuditReport)
    assert report.total_words > 40
    assert report.passed_qc is True
    assert report.gates_passed == 10
    assert report.composite_score >= 8.0
    assert len(report.defect_summary) == 0


def test_audit_slop_detection():
    client = ArkaisClient(contact_email=TEST_CONTACT_EMAIL)
    slop_text = """
    In recent years, the rapid development of artificial intelligence has revolutionized research.
    Carbon capture is not a mere engineering exercise, but rather a fundamental ecological necessity.
    Imagine a library where books represent molecules in a delicate dance of chemistry.
    - Point 1: Symmetrical bullet list
    - Point 2: Symmetrical bullet list
    - Point 3: Symmetrical bullet list
    """

    report = client.evaluate_draft(slop_text)
    assert isinstance(report, AuditReport)
    assert report.passed_qc is False
    assert len(report.defect_summary) >= 3

    # Check specific gate defects
    gate_ids = {g.gate_id for g in report.gate_results if not g.passed}
    assert "GATE-01" in gate_ids  # Banned opener ("In recent years")
    assert "GATE-02" in gate_ids  # "A is not B, but C"
    assert "GATE-03" in gate_ids  # "imagine a library" & "delicate dance"


def test_byok_security_integration(monkeypatch):
    client = ArkaisClient(explicit_api_key="sk-ant-testclientkey12345678901234567890",
                          contact_email=TEST_CONTACT_EMAIL)
    secret = client.get_provider_key("anthropic")
    assert isinstance(secret, RedactedSecret)
    assert "sk-ant" in str(secret)
    assert "****..." in str(secret)

    # Zero telemetry assertion
    client.security.assert_zero_telemetry("anthropic", "https://api.anthropic.com/v1/messages")

    with pytest.raises(CredentialSecurityError):
        client.security.assert_zero_telemetry("anthropic", "https://tracking.thirdparty.com/api")

"""Unit tests for Arkais CLI commands (THE-23)."""

import pytest
import json
from pathlib import Path
import sys

# Ensure SDK src is in path for tests
SDK_SRC = Path(__file__).resolve().parent.parent / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from arkais.cli import main




#: D-1 / THE-75: the client refuses to build without a contact identity. The CLI constructs the
#: client internally, so the identity is supplied through the environment the resolver reads.
#: RFC 2606 reserved, deliberately non-routable.
TEST_CONTACT_EMAIL = "arkais-tests@example.com"


@pytest.fixture(autouse=True)
def _contact_identity(monkeypatch):
    monkeypatch.setenv("ARKAIS_CONTACT_EMAIL", TEST_CONTACT_EMAIL)

@pytest.fixture
def sample_files(tmp_path):
    clean_file = tmp_path / "clean_paper.md"
    clean_file.write_text(
        "Direct air capture configurations operating under high thermodynamic irreversibility "
        "exhibit non-linear capital scaling as regeneration temperatures increase (Figure 2b). "
        "Early empirical pilots demonstrated that structured packings achieve surface wetting "
        "densities exceeding 450 m2/m3 without solvent degradation (Keith et al., 2018). "
        "Independent thermodynamic measurements indicate asymptotic heat recovery boundaries "
        "at 1.4 GJ/t under ambient conditions (Lackner, 1999).\n",
        encoding="utf-8"
    )

    slop_file = tmp_path / "slop_paper.md"
    slop_file.write_text(
        "In recent years, the rapid development of artificial intelligence has revolutionized research.\n"
        "Carbon capture is not a mere engineering exercise, but rather a fundamental ecological necessity.\n"
        "Imagine a library where books represent molecules in a delicate dance of chemistry.\n",
        encoding="utf-8"
    )

    return clean_file, slop_file


def test_cli_version(capsys):
    ret = main(["version"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Project Arkais Engine" in captured.out


def test_cli_signatures(capsys):
    ret = main(["signatures"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "ARKAIS-001-v1.1" in captured.out


def test_cli_audit_clean_file(sample_files, capsys):
    clean_file, _ = sample_files
    ret = main(["audit", str(clean_file)])
    assert ret == 0
    captured = capsys.readouterr()
    assert "PASSED (10/10 GATES)" in captured.out
    assert "GATE-01" in captured.out


def test_cli_audit_slop_file(sample_files, capsys):
    _, slop_file = sample_files
    ret = main(["audit", str(slop_file)])
    assert ret == 1
    captured = capsys.readouterr()
    assert "FAILED (DEFECTS DETECTED)" in captured.out
    assert "Defect Summary" in captured.out


def test_cli_audit_json_output(sample_files, capsys):
    clean_file, _ = sample_files
    ret = main(["audit", str(clean_file), "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["passed_qc"] is True
    assert data["composite_score"] >= 8.0
    assert data["gates_passed"] == 10


def test_cli_audit_nonexistent_file(capsys):
    ret = main(["audit", "non_existent_file_xyz.md"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "Error: File not found" in captured.err


def test_cli_verify_citation_mock(monkeypatch, capsys):
    # Mock verify_citation on ArkaisClient
    from arkais.reference.models import ResolutionResult

    def mock_verify(self, title, author=None, proposed_doi=None):
        if "Real Paper" in title:
            return ResolutionResult(
                verified=True,
                confidence=0.95,
                canonical_doi="10.1016/j.joule.2018.05.006",
                status_code="VERIFIED",
                message="Verified"
            )
        return ResolutionResult(
            verified=False,
            confidence=0.1,
            status_code="UNVERIFIED_PHANTOM",
            message="REF-001: Unverified Citation Phantom."
        )

    from arkais import ArkaisClient
    monkeypatch.setattr(ArkaisClient, "verify_citation", mock_verify)

    # Success case
    ret_pass = main(["verify-citation", "--title", "Real Paper Title"])
    assert ret_pass == 0
    captured = capsys.readouterr()
    assert "CITATION VERIFIED" in captured.out

    # Phantom case
    ret_fail = main(["verify-citation", "--title", "Fake Fabricated Paper"])
    assert ret_fail == 1
    captured = capsys.readouterr()
    assert "CITATION REJECTED" in captured.out


def test_cli_templates_list(capsys):
    ret = main(["templates", "list", "--discipline", "physics"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "fig.physics.scatter.pareto_frontier.v1" in captured.out
    assert "Total: 50 templates" in captured.out


def test_cli_templates_list_json(capsys):
    ret = main(["templates", "list", "--category", "figures", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) == 25
    assert all(item["category"] == "figures" for item in data)


def test_cli_templates_render(tmp_path, capsys):
    out_file = tmp_path / "test_fig.pdf"
    ret = main(["templates", "render", "fig.physics.scatter.pareto_frontier.v1", "--format", "pdf", "--out", str(out_file)])
    assert ret == 0
    assert out_file.is_file()
    assert out_file.read_bytes().startswith(b"%PDF")
    captured = capsys.readouterr()
    assert "Successfully compiled" in captured.out


def test_cli_templates_info(capsys):
    ret = main(["templates", "info", "fig.physics.scatter.pareto_frontier.v1"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Bi-Objective Pareto Frontier" in captured.out
    assert "GATE-07" in captured.out


def test_cli_templates_embed(tmp_path, capsys):
    ret = main(["templates", "embed", "tbl.cs.benchmarks.model_comparison.v1", "--project", str(tmp_path)])
    assert ret == 0
    dest = tmp_path / "assets" / "templates" / "tbl.cs.benchmarks.model_comparison.v1.json"
    assert dest.is_file()
    captured = capsys.readouterr()
    assert "Embedded frozen template" in captured.out


def test_cli_templates_weave(capsys):
    ret = main(["templates", "weave", "tbl.cs.benchmarks.model_comparison.v1", "--number", "2"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Woven Scholarly Prose" in captured.out
    assert "(Table 2)" in captured.out
    assert "GATE-07 Passed: True" in captured.out


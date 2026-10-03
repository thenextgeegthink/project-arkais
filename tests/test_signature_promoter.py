"""Tests for Project Arkais Signature v3.0 Promoter Engine and CLI."""

import json
from pathlib import Path
import sys
import pytest

SDK_SRC = Path(__file__).resolve().parent.parent / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TOOLS_DIR = REPO_ROOT / "06_TOOLS" / "signatures"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from arkais.cli import main as cli_main
from arkais.signature.promoter import (
    PromotionError,
    PromotionValidationError,
    compute_catalog_digest,
    promote_candidate_to_active,
    validate_candidate_catalog,
)
import promote_v3


@pytest.fixture
def repo_candidate_dir():
    return REPO_ROOT / "04_SIGNATURES" / "candidate"


def test_validate_candidate_catalog_real(repo_candidate_dir):
    is_valid, errors, meta = validate_candidate_catalog(repo_candidate_dir)
    assert is_valid is True, f"Candidate validation failed: {errors}"
    assert meta["modules_count"] >= 20
    assert len(meta["layers_present"]) >= 9
    assert len(meta["catalog_digest"]) == 64


def test_validate_candidate_catalog_missing_dir(tmp_path):
    non_existent = tmp_path / "does_not_exist"
    is_valid, errors, _ = validate_candidate_catalog(non_existent)
    assert is_valid is False
    assert any("does not exist" in e for e in errors)


def test_validate_candidate_catalog_cycle_detection(tmp_path):
    mod_dir = tmp_path / "v3.0"
    mod_dir.mkdir(parents=True)

    # Create cycle: mod_a -> mod_b -> mod_a
    (mod_dir / "mod_a.md").write_text(
        "---\n"
        "id: mod_a\n"
        "layer: contract\n"
        "name: Module A\n"
        "token_cost: 100\n"
        "domain: [all]\n"
        "section: [all]\n"
        "competencies: [epistemic_rigor]\n"
        "dependencies: [mod_b]\n"
        "---\n"
        "### 1. Constitutional Directives\nContent A\n"
        "### 2. Structural Invariants\nInvariants A\n"
        "### 3. Operational Guidance\nGuidance A\n",
        encoding="utf-8"
    )

    (mod_dir / "mod_b.md").write_text(
        "---\n"
        "id: mod_b\n"
        "layer: reasoning\n"
        "name: Module B\n"
        "token_cost: 100\n"
        "domain: [all]\n"
        "section: [all]\n"
        "competencies: [epistemic_rigor]\n"
        "dependencies: [mod_a]\n"
        "---\n"
        "### 1. Constitutional Directives\nContent B\n"
        "### 2. Structural Invariants\nInvariants B\n"
        "### 3. Operational Guidance\nGuidance B\n",
        encoding="utf-8"
    )

    is_valid, errors, _ = validate_candidate_catalog(tmp_path, min_modules=2)
    assert is_valid is False
    assert any("Dependency cycle detected" in e for e in errors)


def test_promote_candidate_dry_run(repo_candidate_dir, tmp_path):
    mock_active = tmp_path / "active"
    mock_sdk = tmp_path / "sdk_profiles"

    report = promote_candidate_to_active(
        candidate_dir=repo_candidate_dir,
        active_dir=mock_active,
        sdk_profiles_dir=mock_sdk,
        dry_run=True,
    )

    assert report.status == "DRY_RUN_PASSED"
    assert report.dry_run is True
    assert report.modules_count >= 20
    assert len(report.compiled_bundles) >= 5
    assert "ARKAIS-v3.0.system.md" in report.compiled_bundles
    assert "ARKAIS-v3.0-stem.system.md" in report.compiled_bundles

    # Ensure dry run did not write files to active or sdk directories
    assert not mock_active.exists()
    assert not mock_sdk.exists()


def test_promote_candidate_atomic_live(repo_candidate_dir, tmp_path):
    mock_active = tmp_path / "active"
    mock_sdk = tmp_path / "sdk_profiles"
    mock_sdk.mkdir(parents=True)

    report = promote_candidate_to_active(
        candidate_dir=repo_candidate_dir,
        active_dir=mock_active,
        sdk_profiles_dir=mock_sdk,
        dry_run=False,
    )

    assert report.status == "PROMOTED_SUCCESS"
    assert report.dry_run is False

    # Check active directory contents
    assert (mock_active / "v3.0").is_dir()
    assert (mock_active / "promotion_manifest.json").is_file()
    assert (mock_active / "ARKAIS-v3.0.system.md").is_file()
    assert (mock_active / "ARKAIS-v3.0-stem.system.md").is_file()
    assert (mock_active / "ARKAIS-v3.0-social.system.md").is_file()
    assert (mock_active / "ARKAIS-v3.0-humanities.system.md").is_file()
    assert (mock_active / "ARKAIS-v3.0-biomed.system.md").is_file()
    assert (mock_active / "ARKAIS-v3.0.json").is_file()

    # Check that staging directory was cleaned up
    assert not (mock_active / ".staging_promotion_v3").exists()

    # Check that SDK profiles received synced bundles
    assert (mock_sdk / "ARKAIS-v3.0.system.md").is_file()
    assert (mock_sdk / "ARKAIS-v3.0-stem.system.md").is_file()

    # Verify promotion manifest contents
    manifest = json.loads((mock_active / "promotion_manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "3.0"
    assert manifest["modules_count"] == report.modules_count
    assert "ARKAIS-v3.0.system.md" in manifest["bundles"]


def test_cli_promote_signature_dry_run(capsys):
    ret = cli_main(["promote-signature", "--dry-run"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "ARKAIS SIGNATURE v3.0 PROMOTION REPORT" in captured.out
    assert "DRY-RUN SIMULATION" in captured.out
    assert "Status:          DRY_RUN_PASSED" in captured.out


def test_cli_promote_signature_json(capsys):
    ret = cli_main(["promote-signature", "--dry-run", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "DRY_RUN_PASSED"
    assert data["dry_run"] is True
    assert "compiled_bundles" in data


def test_standalone_promote_script_dry_run(capsys):
    ret = promote_v3.main(["--dry-run"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "ARKAIS SIGNATURE v3.0 PROMOTION REPORT" in captured.out
    assert "DRY-RUN SIMULATION" in captured.out

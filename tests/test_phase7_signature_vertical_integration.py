"""Vertical integration tests for Phase 7 Signature Compiler (SDK + CLI).

Verifies that the golden canonical request compiles to identical manifests and
prompt digests across Python SDK and CLI.
"""

import json
from pathlib import Path
import sys
import pytest

SDK_SRC = Path(__file__).resolve().parent.parent / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from arkais import ArkaisClient, SignatureCompiler
from arkais.signature.compiler import CompileRequest, CompilationResult
from arkais.cli import main

GOLDEN_DIGEST = "71f722fef4bea6a5390b6e0747c7fb025bab243af15305aa3f5b0b6a933c5745"
GOLDEN_MODULES = [
    "arkais.contract.system_directive",
    "arkais.reasoning.causal_reasoning",
    "arkais.domain.cs_systems",
    "arkais.section.methodology",
    "arkais.citation.citation_integrity",
]


def test_sdk_compile_signature_golden():
    """SDK client compile_signature matches canonical golden digest and manifest."""
    client = ArkaisClient()
    result = client.compile_signature(
        domain="stem",
        section="methodology",
        token_budget=2500,
        citation_style="all",
        task="general"
    )

    assert isinstance(result, CompilationResult)
    assert result.prompt_digest == GOLDEN_DIGEST
    assert result.selected_module_ids == GOLDEN_MODULES
    assert result.layers_present == ["contract", "reasoning", "domain", "section", "citation"]
    assert result.declared_tokens == 2510
    assert result.measured_tokens == 4309

    # Manifest and omission diagnostics
    manifest = result.manifest
    assert manifest.domain == "stem"
    assert manifest.section == "methodology"
    assert manifest.token_budget == 2500
    assert len(result.omitted_modules) > 0
    assert result.omitted_modules.get("arkais.audit.gate") == "evaluation_layer_decoupled"
    assert result.omitted_modules.get("arkais.style.anti_slop") == "budget_exceeded"


def test_sdk_compiler_direct_instance():
    """SignatureCompiler directly creates valid CompilationResult."""
    compiler = SignatureCompiler()
    result = compiler.compile(
        domain="stem",
        section="methodology",
        token_budget=2500,
        citation_style="all",
        task="general"
    )
    assert result.prompt_digest == GOLDEN_DIGEST
    assert result.selected_module_ids == GOLDEN_MODULES


def test_cli_compile_signature_manifest(capsys):
    """CLI compile-signature command outputs golden manifest and digest."""
    ret = main([
        "compile-signature",
        "-d", "stem",
        "-s", "methodology",
        "-b", "2500",
        "-t", "general",
        "--citation-style", "all",
        "--manifest"
    ])
    assert ret == 0
    captured = capsys.readouterr()
    assert GOLDEN_DIGEST in captured.out
    for mod in GOLDEN_MODULES:
        assert mod in captured.out
    assert "Omitted Modules" in captured.out
    assert "evaluation_layer_decoupled" in captured.out


def test_cli_compile_signature_json(capsys):
    """CLI compile-signature with --json produces valid parseable JSON."""
    ret = main([
        "compile-signature",
        "-d", "stem",
        "-s", "methodology",
        "-b", "2500",
        "-t", "general",
        "--citation-style", "all",
        "--json"
    ])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["prompt_digest"] == GOLDEN_DIGEST
    assert data["selected_module_ids"] == GOLDEN_MODULES
    assert data["declared_tokens"] == 2510
    assert "omitted_modules" in data

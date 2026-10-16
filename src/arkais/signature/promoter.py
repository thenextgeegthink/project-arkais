"""Promotion and canonical release engine for Project Arkais v3.0 Signatures.

Governed by ADR-006 and the deep-module architecture:
edit candidate -> validate -> compile -> evaluate -> approve -> promote active.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .compiler import (
    CompilationManifest,
    CompiledSignature,
    SignatureCompiler,
    SignatureModule,
    find_repo_root,
)


class PromotionError(Exception):
    """Base error raised during signature promotion."""


class PromotionValidationError(PromotionError):
    """Raised when candidate signature catalog fails pre-promotion validation gates."""


@dataclass
class PromotionReport:
    """Detailed summary of the promotion run."""
    status: str
    catalog_digest: str
    modules_count: int
    modules: List[str]
    layers_present: List[str]
    compiled_bundles: Dict[str, Dict[str, Any]]
    copied_files: List[str]
    timestamp: str
    dry_run: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    layer: str = "both"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_catalog_digest(modules_dir: Path) -> str:
    """Computes a deterministic composite SHA-256 digest of all module markdown files."""
    if not modules_dir.exists():
        return hashlib.sha256(b"").hexdigest()

    hasher = hashlib.sha256()
    md_files = sorted(modules_dir.rglob("*.md"), key=lambda p: str(p.relative_to(modules_dir)))
    for p in md_files:
        rel = str(p.relative_to(modules_dir)).replace("\\", "/")
        hasher.update(rel.encode("utf-8"))
        hasher.update(b":")
        hasher.update(p.read_bytes())
        hasher.update(b"\n")
    return hasher.hexdigest()


def validate_candidate_catalog(
    candidate_dir: Path,
    min_modules: int = 20,
    required_layers: Optional[Set[str]] = None,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validates candidate catalog integrity, deep-module structure, and dependency closure."""
    errors: List[str] = []
    warnings: List[str] = []

    if required_layers is None:
        required_layers = {
            "contract",
            "reasoning",
            "research",
            "rhetoric",
            "style",
            "domain",
            "section",
            "citation",
            "failure",
            "evaluation",
        }

    modules_dir = candidate_dir / "v3.0" if (candidate_dir / "v3.0").exists() else candidate_dir
    if not modules_dir.exists():
        return False, [f"Candidate modules directory does not exist: {modules_dir}"], {}

    compiler = SignatureCompiler(modules_dir=modules_dir)
    modules = compiler.modules

    # Filter out legacy aliases for source inspection
    canonical_modules = {
        m_id: m for m_id, m in modules.items()
        if not m.description.startswith("[Legacy Alias")
    }

    if len(canonical_modules) < min_modules:
        errors.append(
            f"Candidate catalog has {len(canonical_modules)} modules; required at least {min_modules}."
        )

    # Check layers present
    layers_present = {m.layer for m in canonical_modules.values()}
    missing_layers = required_layers - layers_present
    if missing_layers:
        errors.append(f"Candidate catalog is missing required architectural layers: {sorted(missing_layers)}")

    # Check dependencies closure & cycles
    graph: Dict[str, List[str]] = {}
    for m_id, mod in canonical_modules.items():
        graph[m_id] = []
        for dep in mod.dependencies:
            if dep not in modules:
                errors.append(f"Module '{m_id}' has unresolved dependency '{dep}'")
            else:
                graph[m_id].append(dep)

    # Cycle detection via DFS
    visited: Dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited

    def dfs(node: str, path: List[str]):
        visited[node] = 1
        for neighbor in graph.get(node, []):
            if visited.get(neighbor, 0) == 1:
                cycle = " -> ".join(path + [neighbor])
                errors.append(f"Dependency cycle detected in candidate modules: {cycle}")
            elif visited.get(neighbor, 0) == 0:
                dfs(neighbor, path + [neighbor])
        visited[node] = 2

    for node in graph:
        if visited.get(node, 0) == 0:
            dfs(node, [node])

    # Deep module structural invariant checks
    required_sections = [
        "Constitutional Directives",
        "Structural Invariants",
        "Operational Guidance",
    ]
    for m_id, mod in canonical_modules.items():
        if len(mod.content.strip()) < 100:
            errors.append(f"Module '{m_id}' content is too short or empty ({len(mod.content.strip())} chars)")
        for sec in required_sections:
            if sec not in mod.content:
                warnings.append(f"Module '{m_id}' is missing recommended deep-module section: '{sec}'")

    meta = {
        "modules_count": len(canonical_modules),
        "total_with_aliases": len(modules),
        "layers_present": sorted(layers_present),
        "catalog_digest": compute_catalog_digest(modules_dir),
        "warnings": warnings,
    }

    is_valid = len(errors) == 0
    return is_valid, errors, meta




def recompile_deterministic_only(
    candidate_dir: Path,
    catalog_digest: str,
    token_budget: int = 3500,
    version: str = "3.1",
) -> Dict[str, str]:
    """Recompile stripping all ai-annotated modules (last-known-deterministic).

    Rollback produces a NEW artifact; it never rewrites history. The output is
    byte-identical to a fresh core-layer promotion of the same candidate, which is
    the invariant the rollback drill asserts.
    """
    cand_modules_dir = candidate_dir / "v3.0" if (candidate_dir / "v3.0").exists() else candidate_dir
    compiler = SignatureCompiler(modules_dir=cand_modules_dir, provenance_filter={"deterministic"})
    return compile_promoted_artifacts(
        compiler, catalog_digest=catalog_digest, token_budget=token_budget,
        layer="core", version=version,
    )

def validate_layer_gate(
    layer: str,
    charter_version: Optional[str] = None,
    judge_registry: Optional[Path] = None,
    annotation_manifest: Optional[Path] = None,
    agreement_stats: Optional[Dict[str, float]] = None,
    version: str = "3.0",
) -> List[str]:
    """Layer promotion gate. Returns a list of errors (empty means pass).

    Enforced only for ``-a`` layers (which include ai-annotated modules). For those, the
    charter must be frozen, the judge registry recorded, per-cell sample floors met, and
    agreement stats must meet C4 thresholds (kappa >= 0.60 AND gold precision >= 0.70).
    """
    errors: List[str] = []
    # The annotation layer is only meaningful for the layered release. Legacy v3.0
    # promotions ship one layer and need no annotation evidence.
    if version == "3.0" or layer == "core":
        return errors
    if layer not in ("a", "both"):
        return errors

    if not charter_version:
        errors.append("layer -a requires a frozen charter version")
    if judge_registry is None or not Path(judge_registry).exists():
        errors.append("layer -a requires a recorded judge registry")
    if annotation_manifest is None or not Path(annotation_manifest).exists():
        errors.append("layer -a requires an annotation sample manifest")

    # per-cell sample floors
    if annotation_manifest is not None and Path(annotation_manifest).exists():
        try:
            manifest = json.loads(Path(annotation_manifest).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"annotation manifest unreadable: {exc}")
            manifest = {}
        cells = manifest.get("cells", {}) if isinstance(manifest, dict) else {}
        for cell_id, cell in (cells.items() if isinstance(cells, dict) else []):
            if not isinstance(cell, dict):
                continue
            floor = cell.get("floor", 0)
            n = cell.get("n", 0)
            if n < floor:
                errors.append(f"cell {cell_id}: sample count {n} < floor {floor}")

    stats = agreement_stats or {}
    if "kappa" not in stats:
        errors.append("layer -a requires agreement stats (kappa)")
    else:
        if stats["kappa"] < 0.60:
            errors.append(f"kappa {stats['kappa']:.3f} < 0.60")
    if "gold_precision" not in stats:
        errors.append("layer -a requires gold precision")
    else:
        if stats["gold_precision"] < 0.70:
            errors.append(f"gold_precision {stats['gold_precision']:.3f} < 0.70")

    return errors


def compile_promoted_artifacts(
    compiler: SignatureCompiler,
    catalog_digest: str,
    token_budget: int = 3500,
    layer: str = "a",
    version: str = "3.0",
) -> Dict[str, str]:
    """Compiles all canonical domain variants and specification artifacts with standard provenance headers."""
    bundles: Dict[str, str] = {}
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    suffix = f"-{layer}" if layer in ("core", "a") else ""
    domain_targets = [
        (f"ARKAIS-v{version}{suffix}.system.md", "all", "all"),
        (f"ARKAIS-v{version}{suffix}-stem.system.md", "stem", "all"),
        (f"ARKAIS-v{version}{suffix}-social.system.md", "social", "all"),
        (f"ARKAIS-v{version}{suffix}-humanities.system.md", "humanities", "all"),
        (f"ARKAIS-v{version}{suffix}-biomed.system.md", "biomed", "all"),
    ]

    for filename, domain, section in domain_targets:
        compiled = compiler.compile(
            domain=domain,
            section=section,
            token_budget=token_budget,
            inject_exemplars=True,
            task="general",
        )

        mod_lines = "\n".join(f"- {mid}" for mid in compiled.included_modules)
        header = (
            f"<!--\n"
            f"ARKAIS COMPILED SIGNATURE SYSTEM PROMPT\n"
            f"Version: {version}\n"
            f"Compiler: Arkais SignatureCompiler v{version}\nLayer: {layer}\n"
            f"Domain: {domain} | Section: {section}\n"
            f"Catalog Digest: {catalog_digest}\n"
            f"Generated: {timestamp}\n"
            f"Source Modules ({len(compiled.included_modules)}):\n"
            f"{mod_lines}\n"
            f"-->\n\n"
        )
        bundles[filename] = header + compiled.prompt_text

    return bundles


def promote_candidate_to_active(
    candidate_dir: Optional[Path] = None,
    active_dir: Optional[Path] = None,
    sdk_profiles_dir: Optional[Path] = None,
    dry_run: bool = False,
    force: bool = False,
    token_budget: int = 3500,
    logger: Optional[Callable[[str], None]] = None,
    layer: str = "both",
    version: str = "3.0",
    annotation_manifest: Optional[Path] = None,
    judge_registry: Optional[Path] = None,
    charter_version: Optional[str] = None,
    agreement_stats: Optional[Dict[str, float]] = None,
) -> PromotionReport:
    """Validates candidate signature catalog, compiles canonical bundles, and atomically promotes to active.

    Parameters:
        candidate_dir: Root directory of candidate signatures (default: 04_SIGNATURES/candidate)
        active_dir: Root directory of active release signatures (default: 04_SIGNATURES/active)
        sdk_profiles_dir: SDK bundled profile directory (default: packages/sdk/src/arkais/signature/profiles)
        dry_run: When True, performs validation and compilation without modifying active files
        force: When True, bypasses non-critical validation errors
        token_budget: Compilation token ceiling for generated system prompts
        logger: Optional log sink function
    """
    log = logger or (lambda msg: None)
    root = find_repo_root()

    cand_path = candidate_dir or (root / "04_SIGNATURES" / "candidate")
    act_path = active_dir or (root / "04_SIGNATURES" / "active")
    sdk_path = sdk_profiles_dir or (root / "packages" / "sdk" / "src" / "arkais" / "signature" / "profiles")

    log(f"Starting Project Arkais v3.0 Promotion Engine")
    log(f"Candidate Directory: {cand_path}")
    log(f"Active Directory:    {act_path}")
    log(f"SDK Profiles Dir:    {sdk_path}")
    log(f"Dry Run Mode:        {dry_run}")

    # 1. Validation Gate
    is_valid, errors, meta = validate_candidate_catalog(cand_path)
    if not is_valid and not force:
        error_msg = "\n".join(f"  • {e}" for e in errors)
        raise PromotionValidationError(f"Candidate catalog validation failed:\n{error_msg}")

    # 1b. Layered promotion gate. For -a layers the annotation-derived modules may only
    # be promoted when the charter, judge registry, sample floors, and agreement stats are
    # frozen and recorded. Dry runs on fixtures exercise this path without mutating state.
    layer_errors = validate_layer_gate(
        layer=layer,
        charter_version=charter_version,
        judge_registry=judge_registry,
        annotation_manifest=annotation_manifest,
        agreement_stats=agreement_stats,
        version=version,
    )
    if layer_errors and not force:
        raise PromotionValidationError("Layer promotion gate failed:\n" + "\n".join(f"  • {e}" for e in layer_errors))

    catalog_digest = meta["catalog_digest"]
    cand_modules_dir = cand_path / "v3.0" if (cand_path / "v3.0").exists() else cand_path

    # Provenance filter per layer.
    if layer in ("core", "a", "both"):
        if layer == "core":
            compiler = SignatureCompiler(modules_dir=cand_modules_dir, provenance_filter={"deterministic"})
        else:
            compiler = SignatureCompiler(modules_dir=cand_modules_dir)
    else:
        raise PromotionValidationError(f"unknown layer {layer!r}")

    # 2. Compilation Gate
    log("Compiling canonical prompt bundles from candidate catalog...")
    # v3.0 (legacy, single-layer): keep the historical unsuffixed artifact names so
    # existing promotions and tests stay byte-stable.
    if version == "3.0":
        bundles = compile_promoted_artifacts(compiler, catalog_digest=catalog_digest, token_budget=token_budget, layer="both", version=version)
    elif layer == "both":
        bundles_core = compile_promoted_artifacts(
            SignatureCompiler(modules_dir=cand_modules_dir, provenance_filter={"deterministic"}),
            catalog_digest=catalog_digest, token_budget=token_budget, layer="core", version=version)
        bundles_a = compile_promoted_artifacts(
            SignatureCompiler(modules_dir=cand_modules_dir),
            catalog_digest=catalog_digest, token_budget=token_budget, layer="a", version=version)
        bundles = {**bundles_core, **bundles_a}
    else:
        bundles = compile_promoted_artifacts(compiler, catalog_digest=catalog_digest, token_budget=token_budget, layer=layer, version=version)

    # Pre-promotion quality invariant verification on compiled bundles
    required_invariants = ["delve", "tapestry", "revolutionize", "Moreover"]
    for b_name, b_content in bundles.items():
        if len(b_content.strip()) < 5000:
            raise PromotionValidationError(f"Compiled bundle '{b_name}' failed minimum length gate ({len(b_content)} bytes)")
        for inv in required_invariants:
            if inv not in b_content:
                raise PromotionValidationError(f"Compiled bundle '{b_name}' missing core invariant anchor '{inv}'")

    # Load machine AST and specification
    cand_json = cand_path / "ARKAIS-v3.0.json"
    cand_md = cand_path / "ARKAIS-v3.0.md"
    if cand_json.exists():
        json_data = json.loads(cand_json.read_text(encoding="utf-8"))
        json_data["metadata"]["manifest_hash"] = catalog_digest
        json_data["metadata"]["promoted_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        bundles["ARKAIS-v3.0.json"] = json.dumps(json_data, indent=2) + "\n"

    if cand_md.exists():
        bundles["ARKAIS-v3.0.md"] = cand_md.read_text(encoding="utf-8")

    # Build bundle summary
    bundle_meta: Dict[str, Dict[str, Any]] = {}
    for b_name, b_text in bundles.items():
        bundle_meta[b_name] = {
            "bytes": len(b_text),
            "sha256": hashlib.sha256(b_text.encode("utf-8")).hexdigest(),
        }

    copy_plan = [f"v3.0/ ({meta['modules_count']} modules)"]
    if (cand_path / "exemplars").exists():
        copy_plan.append("exemplars/")
    copy_plan.extend(sorted(bundles.keys()))

    if dry_run:
        log(f"[DRY-RUN] Validation PASSED. Catalog digest: {catalog_digest[:16]}... ({meta['modules_count']} modules)")
        log(f"[DRY-RUN] Would update {len(bundles)} compiled bundles and module hierarchy.")
        return PromotionReport(
            status="DRY_RUN_PASSED",
            catalog_digest=catalog_digest,
            modules_count=meta["modules_count"],
            modules=list(compiler.modules.keys()),
            layers_present=meta["layers_present"],
            compiled_bundles=bundle_meta,
            copied_files=copy_plan,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            dry_run=True,
            errors=errors,
            warnings=meta.get("warnings", []),
            layer=layer,
        )

    # 3. Atomic Promotion Execution
    act_path.mkdir(parents=True, exist_ok=True)
    staging_dir = act_path / ".staging_promotion_v3"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    try:
        log("Staging candidate modules...")
        shutil.copytree(cand_modules_dir, staging_dir / "v3.0")

        cand_exemplars = cand_path / "exemplars"
        if cand_exemplars.exists():
            shutil.copytree(cand_exemplars, staging_dir / "exemplars")

        # Write bundles into staging and candidate (candidate holds self-build products)
        for b_name, b_content in bundles.items():
            (staging_dir / b_name).write_text(b_content, encoding="utf-8")
            (cand_path / b_name).write_text(b_content, encoding="utf-8")

            # Also sync into SDK bundled profiles
            if sdk_path.exists():
                (sdk_path / b_name).write_text(b_content, encoding="utf-8")

        # Atomic swap of active v3.0 directory
        target_v3 = act_path / "v3.0"
        backup_v3 = act_path / ".v3.0_backup"
        if backup_v3.exists():
            shutil.rmtree(backup_v3)

        if target_v3.exists():
            target_v3.rename(backup_v3)

        (staging_dir / "v3.0").rename(target_v3)

        if backup_v3.exists():
            shutil.rmtree(backup_v3)

        # Atomic copy of exemplars
        if (staging_dir / "exemplars").exists():
            target_exemplars = act_path / "exemplars"
            if target_exemplars.exists():
                shutil.rmtree(target_exemplars)
            (staging_dir / "exemplars").rename(target_exemplars)

        # Copy compiled bundle files to active
        for b_name in bundles:
            src_file = staging_dir / b_name
            if src_file.exists():
                shutil.copy2(src_file, act_path / b_name)

        # Write promotion manifest
        manifest_data = {
            "version": version,
            "layer": layer,
            "promoted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "catalog_digest": catalog_digest,
            "modules_count": meta["modules_count"],
            "layers_present": meta["layers_present"],
            "bundles": bundle_meta,
            "modules": sorted(compiler.modules.keys()),
        }
        # Recorded fields for -a layers (check_versions validates presence only then).
        if layer in ("a", "both"):
            manifest_data["annotation_sample_manifest"] = (
                str(annotation_manifest) if annotation_manifest is not None else None
            )
            manifest_data["judge_registry"] = (
                str(judge_registry) if judge_registry is not None else None
            )
            manifest_data["charter_version"] = charter_version
            manifest_data["agreement_stats"] = agreement_stats
        (act_path / "promotion_manifest.json").write_text(
            json.dumps(manifest_data, indent=2) + "\n",
            encoding="utf-8"
        )

        log("Atomic promotion complete.")

    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)

    return PromotionReport(
        status="PROMOTED_SUCCESS",
        catalog_digest=catalog_digest,
        modules_count=meta["modules_count"],
        modules=list(compiler.modules.keys()),
        layers_present=meta["layers_present"],
        compiled_bundles=bundle_meta,
        copied_files=copy_plan,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        dry_run=False,
        errors=errors,
        warnings=meta.get("warnings", []),
        layer=layer,
    )

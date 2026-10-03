"""Command-Line Interface (CLI) for Project Arkais (THE-23)."""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List

from .client import ArkaisClient
from .config import ArkaisConfig
from .citation.models import CitationStyle
from .signature.compiler import SignatureCompiler
from .signature.loader import SignatureManager
from .signature.promoter import (
    PromotionError,
    PromotionValidationError,
    promote_candidate_to_active,
)
from .verification.factored import FactoredVerifier
from .verification.interrogator import ArgumentInterrogator, ToulminChain

# ANSI Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[90m"
RESET = "\033[0m"


def format_status(passed: bool) -> str:
    return f"{GREEN}[PASS]{RESET}" if passed else f"{RED}[FAIL]{RESET}"


def cmd_audit(client: ArkaisClient, args: argparse.Namespace) -> int:
    target_path = Path(args.file)
    if not target_path.exists():
        print(f"{RED}Error: File not found: {target_path}{RESET}", file=sys.stderr)
        return 1

    text = target_path.read_text(encoding="utf-8")
    report = client.evaluate_draft(text)

    if args.json:
        payload = {
            "file": str(target_path),
            "passed_qc": report.passed_qc,
            "composite_score": report.composite_score,
            "total_words": report.total_words,
            "gates_passed": report.gates_passed,
            "gates_total": report.gates_total,
            "defect_summary": report.defect_summary,
            "gate_results": [
                {
                    "gate_id": g.gate_id,
                    "name": g.name,
                    "passed": g.passed,
                    "score": g.score,
                    "message": g.message
                }
                for g in report.gate_results
            ]
        }
        print(json.dumps(payload, indent=2))
        return 0 if report.passed_qc else 1

    print("=" * 70)
    print(f"{BOLD}ARKAIS ACADEMIC PROSE AUDIT REPORT{RESET}")
    print("=" * 70)
    print(f"Target File:      {target_path.name}")
    print(f"Word Count:       {report.total_words} words ({report.total_sentences} sentences)")
    print(f"Active Signature: {client.config.default_signature}")
    print(f"Overall Status:   {GREEN + 'PASSED (10/10 GATES)' + RESET if report.passed_qc else RED + 'FAILED (DEFECTS DETECTED)' + RESET}")
    print(f"Composite Score:  {BOLD}{report.composite_score} / 10.0{RESET}")
    print("-" * 70)

    for g in report.gate_results:
        print(f"{format_status(g.passed)} {BOLD}{g.gate_id}{RESET} {g.name:<34} {g.message}")

    if report.defect_summary:
        print("-" * 70)
        print(f"{RED}{BOLD}Defect Summary:{RESET}")
        for d in report.defect_summary:
            print(f"  ❌ {d}")

    print("=" * 70)
    return 0 if report.passed_qc else 1


def cmd_verify_doi(client: ArkaisClient, args: argparse.Namespace) -> int:
    doi = args.doi.strip()
    print(f"Resolving DOI: {CYAN}{doi}{RESET} via scholarly polite pool...")
    item = client.resolve_doi(doi)

    if not item:
        print(f"{RED}Error: DOI not found in registered scholarly registries.{RESET}", file=sys.stderr)
        return 1

    print(f"\n{GREEN}✅ Registered Academic Work Verified{RESET}")
    print(f"  Title:    {BOLD}{item.title}{RESET}")
    print(f"  Authors:  {', '.join(item.authors) if item.authors else 'Anon'}")
    print(f"  Venue:    {item.venue or 'N/A'} ({item.year or 'n.d.'})")
    print(f"  Registry: {item.source_registry.upper()}")
    print(f"  DOI Link: {item.url or f'https://doi.org/{item.doi}'}")
    return 0


def cmd_verify_citation(client: ArkaisClient, args: argparse.Namespace) -> int:
    title = args.title.strip()
    author = args.author.strip() if args.author else None
    proposed_doi = args.doi.strip() if args.doi else None

    print(f"Verifying citation authenticity: \"{title}\"...")
    res = client.verify_citation(title=title, author=author, proposed_doi=proposed_doi)

    if res.verified:
        print(f"\n{GREEN}✅ CITATION VERIFIED (Confidence: {res.confidence*100:.1f}%){RESET}")
        print(f"  Canonical DOI: {res.canonical_doi}")
        print(f"  Message:       {res.message}")
        return 0
    else:
        print(f"\n{RED}❌ CITATION REJECTED: {res.status_code}{RESET}")
        print(f"  {res.message}")
        return 1


def cmd_signatures(client: ArkaisClient, args: argparse.Namespace) -> int:
    sigs = client.signatures.list()
    print("=" * 60)
    print(f"{BOLD}AVAILABLE ARKAIS ACADEMIC SIGNATURES{RESET}")
    print("=" * 60)
    for s_id in sigs:
        sig = client.signatures.get(s_id)
        is_active = (s_id == client.config.default_signature)
        active_tag = f"{GREEN}[ACTIVE]{RESET}" if is_active else "[AVAILABLE]"
        print(f"{active_tag} {BOLD}{sig.identifier}{RESET} (v{sig.version})")
        print(f"  Corpus:      {sig.corpus_size}")
        print(f"  Calibrated:  {sig.calibration_date}")
        print(f"  Description: {sig.description}")
        print("-" * 60)
    return 0


def cmd_templates(args: argparse.Namespace) -> int:
    """Handle all 'arkais templates' subcommands."""
    from .templates import (
        CompilationError,
        RenderFormat,
        TemplateCompiler,
        TemplateNotFoundError,
        get_default_catalog,
        weave_template_prose,
    )

    catalog = get_default_catalog()

    if not args.template_action or args.template_action == "list":
        cat_filter = getattr(args, "category", None)
        disc_filter = getattr(args, "discipline", None)
        eng_filter = getattr(args, "engine", None)
        search_filter = getattr(args, "search", None)

        templates = catalog.list(
            category=cat_filter,
            discipline=disc_filter,
            engine=eng_filter,
            search=search_filter,
        )
        if getattr(args, "json", False):
            print(json.dumps([t.to_dict() for t in templates], indent=2))
            return 0

        stats = catalog.stats()
        print(f"\n{BOLD}Arkais Academic Visual Assets & Scientific Table Registry{RESET}")
        print(
            f"{DIM}Total: {stats['total']} templates "
            f"({stats['by_category'].get('figures', 0)} figures, "
            f"{stats['by_category'].get('tables', 0)} tables) | "
            f"Cache: {stats['cached']} cached{RESET}\n"
        )

        print(f"{BOLD}{'ID':<48} {'NAME':<42} {'ENGINE':<16} {'DISCIPLINE'}{RESET}")
        print("─" * 122)
        for t in templates:
            print(f"{CYAN}{t.id:<48}{RESET} {t.name[:40]:<42} {DIM}{t.engine.value:<16}{RESET} {t.discipline.value}")
        print("─" * 122)
        print(f"{DIM}Render using: arkais templates render <id> --format pdf --out <path>{RESET}\n")
        return 0

    elif args.template_action == "render":
        t_id = args.id
        try:
            envelope = catalog.get(t_id)
        except TemplateNotFoundError:
            print(f"{RED}Error: Template '{t_id}' not found in catalog.{RESET}", file=sys.stderr)
            return 1

        compiler = TemplateCompiler(catalog=catalog)
        fmt = getattr(args, "format", None) or ("svg" if envelope.category.value == "figures" else "latex")
        out_path = getattr(args, "out", None)

        try:
            rendered = compiler.compile(envelope, format=fmt, output_path=out_path)
            if out_path:
                print(f"{GREEN}✓ Successfully compiled '{t_id}' to {out_path} ({rendered.mime_type}){RESET}")
            else:
                if isinstance(rendered.content, bytes):
                    sys.stdout.buffer.write(rendered.content)
                else:
                    print(rendered.content)
            return 0
        except Exception as e:
            print(f"{RED}Compilation failed: {str(e)}{RESET}", file=sys.stderr)
            return 1

    elif args.template_action == "info":
        t_id = args.id
        try:
            envelope = catalog.get(t_id)
        except TemplateNotFoundError:
            print(f"{RED}Error: Template '{t_id}' not found.{RESET}", file=sys.stderr)
            return 1

        if getattr(args, "json", False):
            print(envelope.to_json(indent=2))
            return 0

        print(f"\n{BOLD}{envelope.name}{RESET}")
        print(f"{CYAN}ID:{RESET}           {envelope.id} (v{envelope.version})")
        print(f"{CYAN}Category:{RESET}     {envelope.category.value.capitalize()}")
        print(f"{CYAN}Discipline:{RESET}   {envelope.discipline.value}")
        print(f"{CYAN}Engine:{RESET}       {envelope.engine.value}")
        print(f"{CYAN}Tags:{RESET}         {', '.join(envelope.tags)}")
        print(f"{CYAN}Description:{RESET}  {envelope.description or 'N/A'}")
        print(f"\n{BOLD}Stylometric Signature Integration (GATE-07/GATE-08):{RESET}")
        print(f"  Gate:       {envelope.signature_integration.recommended_gate}")
        print(f"  Archetype:  {envelope.signature_integration.weaving_archetype.value}")
        print(f"  Blueprint:  {envelope.signature_integration.in_prose_blueprint}")
        print(f"  Metrics:    {', '.join(envelope.signature_integration.required_metrics)}")
        if envelope.caption_blueprint:
            print(f"  Caption:    {envelope.caption_blueprint}")
        if envelope.notes:
            print(f"  Notes:      {envelope.notes}")
        print()
        return 0

    elif args.template_action == "embed":
        t_id = args.id
        proj = getattr(args, "project", ".")
        try:
            dest = catalog.embed_in_project(t_id, project_dir=proj)
            print(f"{GREEN}✓ Embedded frozen template into: {dest}{RESET}")
            return 0
        except Exception as e:
            print(f"{RED}Embedding failed: {str(e)}{RESET}", file=sys.stderr)
            return 1

    elif args.template_action == "weave":
        t_id = args.id
        try:
            envelope = catalog.get(t_id)
        except TemplateNotFoundError:
            print(f"{RED}Error: Template '{t_id}' not found.{RESET}", file=sys.stderr)
            return 1

        metrics = {}
        if getattr(args, "metrics", None):
            try:
                metrics = json.loads(args.metrics)
            except Exception:
                pass

        number = getattr(args, "number", 1)
        res = weave_template_prose(envelope, number=number, metrics=metrics)
        print(f"\n{BOLD}Woven Scholarly Prose:{RESET}")
        print(f"{res.prose}\n")
        print(f"{BOLD}Caption:{RESET}")
        print(f"*{res.caption}*\n")
        print(f"{DIM}GATE-07 Passed: {res.gate_07_pass} | GATE-08 Passed: {res.gate_08_pass}{RESET}\n")
        return 0

    elif args.template_action == "sync":
        print(f"{CYAN}Synchronizing templates with remote repository...{RESET}")
        res = catalog.sync(remote_base_url=getattr(args, "url", None), force=getattr(args, "force", False))
        if res.is_success:
            print(f"{GREEN}✓ Sync completed: {res.synced} new, {res.updated} updated, {res.skipped} up-to-date.{RESET}")
            return 0
        else:
            print(f"{YELLOW}Sync completed with warnings: {', '.join(res.errors)}{RESET}")
            return 1

    return 0


def cmd_version() -> int:
    from . import __version__
    print(f"Project Arkais Engine v{__version__} (NGT / Dreadnought Studio)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arkais",
        description="Deterministic academic prose signature engine, stylometric audit suite, and template registry."
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # audit
    p_audit = subparsers.add_parser("audit", help="Audit manuscript text against the 10 deterministic QC gates.")
    p_audit.add_argument("file", type=str, help="Path to manuscript file (.md, .tex, .txt)")
    p_audit.add_argument("--json", action="store_true", help="Output audit report as structured JSON")

    # verify-doi
    p_vdoi = subparsers.add_parser("verify-doi", help="Resolve metadata for a registered DOI via scholarly polite pool.")
    p_vdoi.add_argument("doi", type=str, help="DOI string (e.g. 10.1016/j.joule.2018.05.006)")

    # verify-citation
    p_vcite = subparsers.add_parser("verify-citation", help="Verify authenticity of an academic paper title to eliminate phantoms.")
    p_vcite.add_argument("--title", required=True, type=str, help="Title of the paper")
    p_vcite.add_argument("--author", type=str, help="Author last name")
    p_vcite.add_argument("--doi", type=str, help="Proposed DOI if known")

    # signatures
    subparsers.add_parser("signatures", help="List available academic signatures.")

    # templates
    p_templates = subparsers.add_parser("templates", help="Manage, search, render, and embed scientific figure & table templates.")
    t_subparsers = p_templates.add_subparsers(dest="template_action", help="Template subactions")

    # templates list
    p_tlist = t_subparsers.add_parser("list", help="List and search available templates.")
    p_tlist.add_argument("-c", "--category", choices=["figures", "tables"], help="Filter by category")
    p_tlist.add_argument("-d", "--discipline", choices=["physics", "computer_science", "medicine", "economics", "engineering"], help="Filter by discipline")
    p_tlist.add_argument("-e", "--engine", help="Filter by engine")
    p_tlist.add_argument("-s", "--search", help="Search keyword")
    p_tlist.add_argument("--json", action="store_true", help="Output as JSON")

    # templates render
    p_trender = t_subparsers.add_parser("render", help="Render template to vector PDF, SVG, PNG, HTML, LaTeX, or Markdown.")
    p_trender.add_argument("id", type=str, help="Template canonical ID")
    p_trender.add_argument("-f", "--format", choices=["svg", "pdf", "png", "html", "latex", "markdown"], help="Output format")
    p_trender.add_argument("-o", "--out", type=str, help="Output destination file path")

    # templates info
    p_tinfo = t_subparsers.add_parser("info", help="Show full metadata and signature integration for a template.")
    p_tinfo.add_argument("id", type=str, help="Template canonical ID")
    p_tinfo.add_argument("--json", action="store_true", help="Output as JSON")

    # templates embed
    p_tembed = t_subparsers.add_parser("embed", help="Embed a frozen template spec into manuscript project assets.")
    p_tembed.add_argument("id", type=str, help="Template canonical ID")
    p_tembed.add_argument("-p", "--project", default=".", help="Project directory path (default: .)")

    # templates weave
    p_tweave = t_subparsers.add_parser("weave", help="Synthesize grounded in-prose citations and caption.")
    p_tweave.add_argument("id", type=str, help="Template canonical ID")
    p_tweave.add_argument("-n", "--number", type=int, default=1, help="Figure or table number (default: 1)")
    p_tweave.add_argument("-m", "--metrics", type=str, help="JSON string of quantitative metrics")

    # templates sync
    p_tsync = t_subparsers.add_parser("sync", help="Synchronize local cache with remote GitHub registry.")
    p_tsync.add_argument("--url", type=str, help="Remote registry base URL override")
    p_tsync.add_argument("--force", action="store_true", help="Force redownload without ETag check")

    # compile-signature
    p_compile = subparsers.add_parser("compile-signature", help="Dynamically compile modular signature prompts.")
    p_compile.add_argument("-d", "--domain", default="all", choices=["all", "stem", "social", "humanities", "biomed"], help="Target academic domain")
    p_compile.add_argument("-s", "--section", default="all", choices=["all", "abstract", "introduction", "literature_review", "methodology", "results", "discussion", "conclusion"], help="Target paper section")
    p_compile.add_argument("-b", "--budget", type=int, default=2500, help="Target token budget ceiling (default: 2500)")
    p_compile.add_argument("-t", "--task", default="general", help="Target task type (default: general)")
    p_compile.add_argument("--citation-style", choices=["all", "apa", "chicago", "mla", "ieee"], default="all", help="Target citation style archetype")
    p_compile.add_argument("-o", "--out", type=str, help="Destination output file path")
    p_compile.add_argument("--no-exemplars", action="store_true", help="Exclude authentic mined corpus exemplars")
    p_compile.add_argument("-m", "--manifest", action="store_true", help="Display full compilation manifest with module breakdown and omission reasons")
    p_compile.add_argument("--json", action="store_true", help="Output compilation metadata as JSON")

    # interrogate
    p_interrogate = subparsers.add_parser("interrogate", help="Run Toulmin 9-test argument interrogation on claim chains.")
    p_interrogate.add_argument("-f", "--file", type=str, help="Path to text or markdown claim chain file")
    p_interrogate.add_argument("-c", "--claim", type=str, help="Primary claim statement")
    p_interrogate.add_argument("-g", "--grounds", type=str, help="Empirical grounds statement")
    p_interrogate.add_argument("-w", "--warrant", type=str, help="Theoretical warrant")
    p_interrogate.add_argument("-q", "--qualifier", type=str, help="Scope / validity boundary qualifier")
    p_interrogate.add_argument("-r", "--rebuttal", type=str, help="Refutation condition")

    # verify-factored
    p_vfact = subparsers.add_parser("verify-factored", help="Run Chain of Verification (CoVe Factor + Revise) on manuscript drafts.")
    p_vfact.add_argument("file", type=str, help="Path to manuscript draft file")
    p_vfact.add_argument("--revise", action="store_true", help="Replace unverified assertions with structured [AUTHOR: ...] / [CITE: ...] gap tags")
    p_vfact.add_argument("-o", "--out", type=str, help="Destination file for revised draft")
    p_vfact.add_argument("--json", action="store_true", help="Output verification results as JSON")

    # benchmark-ladder
    p_ladder = subparsers.add_parser("benchmark-ladder", help="Run Claude's Empirical Evaluation Ladder (L0 to L5) benchmark.")
    p_ladder.add_argument("--brief", choices=["all", "brief_01_cs_systems", "brief_02_econometrics", "brief_03_biomedical"], default="all")
    p_ladder.add_argument("--levels", type=str, default="0,1,2,3,4,5", help="Comma-separated levels to evaluate")
    p_ladder.add_argument("--json", action="store_true", help="Output benchmark data as JSON")

    # promote-signature
    p_promote = subparsers.add_parser("promote-signature", help="Promote candidate signature catalog to active release state atomically.")
    p_promote.add_argument("--dry-run", action="store_true", help="Simulate validation and compilation without modifying active signatures.")
    p_promote.add_argument("--candidate-dir", type=str, default=None, help="Path to candidate signatures root")
    p_promote.add_argument("--active-dir", type=str, default=None, help="Path to active signatures root")
    p_promote.add_argument("--sdk-dir", type=str, default=None, help="Path to SDK signature profiles")
    p_promote.add_argument("--force", action="store_true", help="Bypass non-critical validation warnings")
    p_promote.add_argument("--budget", type=int, default=3500, help="Compilation token ceiling (default: 3500)")
    p_promote.add_argument("--json", action="store_true", help="Output promotion report as structured JSON")

    # version
    subparsers.add_parser("version", help="Display Arkais package version.")

    return parser


def cmd_promote_signature(args: argparse.Namespace) -> int:
    def log(msg: str):
        if not getattr(args, "json", False):
            print(f"{CYAN}[PROMOTE]{RESET} {msg}")

    try:
        report = promote_candidate_to_active(
            candidate_dir=Path(args.candidate_dir) if args.candidate_dir else None,
            active_dir=Path(args.active_dir) if args.active_dir else None,
            sdk_profiles_dir=Path(args.sdk_dir) if args.sdk_dir else None,
            dry_run=getattr(args, "dry_run", False),
            force=getattr(args, "force", False),
            token_budget=getattr(args, "budget", 3500),
            logger=log,
        )

        if getattr(args, "json", False):
            print(json.dumps(report.to_dict(), indent=2))
            return 0

        print("\n" + "=" * 70)
        mode_label = f"{YELLOW}[DRY-RUN SIMULATION]{RESET}" if args.dry_run else f"{GREEN}[LIVE PROMOTION SUCCESS]{RESET}"
        print(f"{BOLD}ARKAIS SIGNATURE v3.0 PROMOTION REPORT — {mode_label}")
        print("=" * 70)
        print(f"Status:          {report.status}")
        print(f"Catalog Digest:  {report.catalog_digest}")
        print(f"Modules Count:   {report.modules_count}")
        print(f"Layers Present:  {', '.join(report.layers_present)}")
        print(f"Timestamp:       {report.timestamp}")
        print("-" * 70)
        print(f"{BOLD}Compiled Bundles ({len(report.compiled_bundles)}):{RESET}")
        for b_name, b_info in sorted(report.compiled_bundles.items()):
            print(f"  • {b_name:<34} ({b_info.get('bytes', 0):>6} bytes, sha: {b_info.get('sha256', '')[:12]}...)")
        print("-" * 70)
        print(f"{BOLD}Files Staged & Promoted:{RESET}")
        for f in report.copied_files:
            print(f"  ✓ {f}")

        if report.warnings:
            print("-" * 70)
            print(f"{YELLOW}{BOLD}Warnings ({len(report.warnings)}):{RESET}")
            for w in report.warnings[:10]:
                print(f"  ⚠ {w}")
            if len(report.warnings) > 10:
                print(f"  ... and {len(report.warnings) - 10} more.")

        print("=" * 70)
        if args.dry_run:
            print(f"{YELLOW}Simulation complete. No active files modified. Run without --dry-run to commit promotion.{RESET}\n")
        else:
            print(f"{GREEN}✓ Promotion successfully committed to 04_SIGNATURES/active/ and SDK profiles.{RESET}\n")
        return 0

    except PromotionValidationError as e:
        if getattr(args, "json", False):
            print(json.dumps({"status": "VALIDATION_FAILED", "error": str(e)}, indent=2))
        else:
            print(f"\n{RED}{BOLD}[VALIDATION FAILED]{RESET}\n{e}\n", file=sys.stderr)
        return 1
    except PromotionError as e:
        if getattr(args, "json", False):
            print(json.dumps({"status": "PROMOTION_ERROR", "error": str(e)}, indent=2))
        else:
            print(f"\n{RED}{BOLD}[PROMOTION ERROR]{RESET}\n{e}\n", file=sys.stderr)
        return 1
    except Exception as e:
        if getattr(args, "json", False):
            print(json.dumps({"status": "UNEXPECTED_ERROR", "error": str(e)}, indent=2))
        else:
            print(f"\n{RED}{BOLD}[UNEXPECTED ERROR]{RESET}\n{e}\n", file=sys.stderr)
        return 1


def cmd_compile_signature(args: argparse.Namespace) -> int:
    manager = SignatureManager()
    inject_exemplars = not getattr(args, "no_exemplars", False)
    compiled = manager.compile(
        domain=args.domain,
        section=args.section,
        token_budget=args.budget,
        inject_exemplars=inject_exemplars,
        citation_style=getattr(args, "citation_style", "all"),
        task=getattr(args, "task", "general"),
        slots={}
    )

    if getattr(args, "json", False):
        manifest_dict = compiled.manifest.to_dict() if compiled.manifest else None
        selected = compiled.manifest.selected_module_ids if compiled.manifest else compiled.included_modules
        omissions = compiled.manifest.omitted_modules if compiled.manifest else {}
        measured = compiled.manifest.measured_tokens if compiled.manifest else round(len(compiled.prompt_text.split()) * 1.33)
        payload = {
            "domain": compiled.domain,
            "section": compiled.section,
            "total_tokens": compiled.total_tokens,
            "declared_tokens": compiled.total_tokens,
            "measured_tokens": measured,
            "prompt_digest": compiled.prompt_digest,
            "selected_modules": selected,
            "selected_module_ids": selected,
            "omissions": omissions,
            "omitted_modules": omissions,
            "included_modules": compiled.included_modules,
            "exemplar_count": compiled.exemplar_count,
            "validation_status": compiled.validation_status,
            "manifest": manifest_dict,
            "prompt_text": compiled.prompt_text
        }
        print(json.dumps(payload, indent=2))
        return 0

    if getattr(args, "manifest", False):
        print("=" * 70)
        print(f"{BOLD}ARKAIS SIGNATURE COMPILATION MANIFEST{RESET}")
        print("=" * 70)
        print(f"Domain:          {compiled.domain}")
        print(f"Section:         {compiled.section}")
        print(f"Token Budget:    {compiled.manifest.token_budget if compiled.manifest else 'N/A'}")
        print(f"Declared Tokens: {compiled.total_tokens}")
        print(f"Measured Tokens: {compiled.manifest.measured_tokens if compiled.manifest else 'N/A'}")
        print(f"Prompt SHA-256:  {compiled.prompt_digest}")
        if compiled.manifest:
            print(f"Layers Present:  {', '.join(compiled.manifest.layers_present)}")
        print("-" * 70)
        selected = compiled.manifest.selected_module_ids if compiled.manifest else compiled.included_modules
        print(f"{GREEN}{BOLD}Selected Modules ({len(selected)}):{RESET}")
        for mid in selected:
            print(f"  ✓ {mid}")
        if compiled.manifest and compiled.manifest.omitted_modules:
            print(f"\n{YELLOW}{BOLD}Omitted Modules ({len(compiled.manifest.omitted_modules)}):{RESET}")
            for mid, reason in sorted(compiled.manifest.omitted_modules.items()):
                print(f"  • {mid:<40} [{reason}]")
        print("=" * 70)

    if args.out:
        out_p = Path(args.out)
        out_p.write_text(compiled.prompt_text, encoding="utf-8")
        print(f"{GREEN}[SUCCESS] Compiled signature prompt saved to {out_p} ({compiled.total_tokens} tokens, {len(compiled.included_modules)} modules){RESET}")
        return 0

    if not getattr(args, "manifest", False):
        print(compiled.prompt_text)
    return 0


def cmd_interrogate(args: argparse.Namespace) -> int:
    interrogator = ArgumentInterrogator()
    if args.file:
        p = Path(args.file)
        if not p.exists():
            print(f"{RED}Error: File not found: {p}{RESET}", file=sys.stderr)
            return 1
        content = p.read_text(encoding="utf-8")
        chain = interrogator.intake(content)
    else:
        chain = ToulminChain(
            claim=args.claim or "",
            grounds=args.grounds or "none supplied",
            warrant=args.warrant,
            qualifier=args.qualifier,
            rebuttal=args.rebuttal
        )

    questions = interrogator.interrogate(chain)
    report = interrogator.format_report(chain, questions)
    print(report)
    return 0


def cmd_verify_factored(args: argparse.Namespace) -> int:
    target_path = Path(args.file)
    if not target_path.exists():
        print(f"{RED}Error: File not found: {target_path}{RESET}", file=sys.stderr)
        return 1

    text = target_path.read_text(encoding="utf-8")
    verifier = FactoredVerifier()
    claims = verifier.extract_claims(text)

    for c in claims:
        verifier.verify_isolated(c)

    consistency = verifier.check_consistency(claims)

    if args.json:
        payload = {
            "file": str(target_path),
            "status": consistency["status"],
            "total_claims": consistency["total_claims"],
            "supported": consistency["supported"],
            "unverified": consistency["unverified"],
            "pass_rate": consistency["pass_rate"],
            "claims": [
                {
                    "id": c.id,
                    "type": c.claim_type,
                    "text": c.original_text,
                    "question": c.verification_question,
                    "status": c.consistency_status
                }
                for c in claims
            ]
        }
        print(json.dumps(payload, indent=2))
        return 0 if consistency["status"] == "APPROVED" else 1

    print("=" * 70)
    print(f"{BOLD}ARKAIS FACTORED VERIFICATION REPORT (CoVe Factor + Revise){RESET}")
    print("=" * 70)
    print(f"Target File:   {target_path.name}")
    print(f"Total Claims:  {consistency['total_claims']}")
    print(f"Supported:     {GREEN}{consistency['supported']}{RESET}")
    print(f"Unverified:    {YELLOW}{consistency['unverified']}{RESET}")
    print(f"Pass Rate:     {consistency['pass_rate'] * 100:.1f}%")
    print(f"Status:        {GREEN + 'APPROVED' + RESET if consistency['status'] == 'APPROVED' else YELLOW + 'NEEDS REVISION (GAPS DETECTED)' + RESET}")
    print("-" * 70)

    for c in claims:
        status_label = GREEN + "[SUPPORTED]" + RESET if c.consistency_status == "SUPPORTED" else YELLOW + "[UNVERIFIED]" + RESET
        print(f"{status_label} ({c.claim_type}) {c.original_text}")
        print(f"   ↳ Q: {DIM}{c.verification_question}{RESET}")

    if args.revise:
        revised_text = verifier.revise_with_gap_tags(text, claims)
        if args.out:
            Path(args.out).write_text(revised_text, encoding="utf-8")
            print(f"\n{GREEN}[+] Revised draft with gap tags written to {args.out}{RESET}")
        else:
            print("\n" + "=" * 70)
            print(f"{BOLD}REVISED DRAFT (WITH STRUCTURED GAP TAGS){RESET}")
            print("=" * 70)
            print(revised_text)

    return 0 if consistency["status"] == "APPROVED" else 1


def cmd_benchmark_ladder(args: argparse.Namespace) -> int:
    from arkais.signature.benchmark_ladder import BenchmarkLadderRunner


    runner = BenchmarkLadderRunner()
    levels = [int(x.strip()) for x in args.levels.split(",") if x.strip().isdigit()]
    results = runner.run_all(levels=levels)

    if args.brief != "all":
        results = [r for r in results if r.brief_id == args.brief]

    if getattr(args, "json", False):
        from dataclasses import asdict
        print(json.dumps([asdict(r) for r in results], indent=2))
        return 0

    print("=" * 90)
    print(f"{BOLD}ARKAIS EMPIRICAL EVALUATION LADDER BENCHMARK (L0 to L5){RESET}")
    print("=" * 90)
    print(f"{'Brief':<22} | {'Level':<5} | {'Gates':<6} | {'Score':<6} | {'Burst':<6} | {'Contrasts':<9} | {'Toulmin':<8}")
    print("-" * 90)
    for r in results:
        status_color = GREEN if r.gates_passed == r.gates_total else YELLOW
        print(f"{r.brief_id:<22} | L{r.level:<4} | {status_color}{r.gates_passed:>2}/{r.gates_total:<2}{RESET} | {r.composite_score:>5.1f} | {r.burstiness:>5.3f} | {r.synthetic_contrasts:>9} | {r.toulmin_completeness*100:>6.0f}%")
    print("=" * 90)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand or args.subcommand == "version":
        return cmd_version()

    if args.subcommand == "templates":
        return cmd_templates(args)
    elif args.subcommand == "compile-signature":
        return cmd_compile_signature(args)
    elif args.subcommand == "interrogate":
        return cmd_interrogate(args)
    elif args.subcommand == "verify-factored":
        return cmd_verify_factored(args)
    elif args.subcommand == "benchmark-ladder":
        return cmd_benchmark_ladder(args)
    elif args.subcommand == "promote-signature":
        return cmd_promote_signature(args)


    client = ArkaisClient()

    if args.subcommand == "audit":
        return cmd_audit(client, args)
    elif args.subcommand == "verify-doi":
        return cmd_verify_doi(client, args)
    elif args.subcommand == "verify-citation":
        return cmd_verify_citation(client, args)
    elif args.subcommand == "signatures":
        return cmd_signatures(client, args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())



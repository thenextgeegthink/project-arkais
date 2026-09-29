"""Command-Line Interface (CLI) for Project Arkais (THE-23)."""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List

from .client import ArkaisClient
from .config import ArkaisConfig
from .citation.models import CitationStyle

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

    # version
    subparsers.add_parser("version", help="Display Arkais package version.")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand or args.subcommand == "version":
        return cmd_version()

    if args.subcommand == "templates":
        return cmd_templates(args)

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


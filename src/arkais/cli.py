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


def cmd_version() -> int:
    from . import __version__
    print(f"Project Arkais Engine v{__version__} (NGT / Dreadnought Studio)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arkais",
        description="Deterministic academic prose signature engine and stylometric audit suite."
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

    # version
    subparsers.add_parser("version", help="Display Arkais package version.")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand or args.subcommand == "version":
        return cmd_version()

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

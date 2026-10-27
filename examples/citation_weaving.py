#!/usr/bin/env python3
"""
Project Arkais — Multi-Style Citation Formatting & Rhetorical Weaving Example
=============================================================================
Demonstrates formatting citations across APA, IEEE, Nature, Harvard, Chicago,
and BibTeX standards, and weaving citations dynamically into human narrative prose.
"""

import sys
from pathlib import Path

# Support direct execution from repo root or package root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "sdk" / "src"))

from arkais import ArkaisClient, ReferenceItem, CitationStyle, RhetoricalRole

def main():
    client = ArkaisClient()

    # Create reference items
    ref1 = ReferenceItem(
        doi="10.1016/j.joule.2018.05.006",
        title="A Process for Capturing CO2 from the Atmosphere",
        authors=["David Keith", "Geoffrey Holmes", "David St. Angelo", "Kent Heidel"],
        year=2018,
        venue="Joule",
        volume="2",
        issue="8",
        pages="1573-1594",
    )

    ref2 = ReferenceItem(
        doi="10.1126/science.286.5442.1105",
        title="Capture of Carbon Dioxide Directly from the Atmosphere",
        authors=["Klaus S. Lackner"],
        year=1999,
        venue="Science",
        volume="286",
        pages="1105-1105",
    )

    print("=" * 65)
    print("1. MULTI-STYLE IN-TEXT CITATION FORMATTING")
    print("=" * 65)
    print(f"APA 7th:  {client.format_citation(ref1, style=CitationStyle.APA_7TH)}")
    print(f"IEEE:     {client.format_citation(ref1, style=CitationStyle.IEEE, index=1)}")
    print(f"Nature:   {client.format_citation(ref1, style=CitationStyle.NATURE, index=1)}")
    print(f"Harvard:  {client.format_citation(ref1, style=CitationStyle.HARVARD)}")
    print(f"Chicago:  {client.format_citation(ref1, style=CitationStyle.CHICAGO)}")

    print("\n" + "=" * 65)
    print("2. RHETORICAL WEAVING (ELIMINATING MONOTONE AI PARENTHETICALS)")
    print("=" * 65)
    
    # 1. Integral Subject
    s1 = client.weave_citation(
        ref1,
        role=RhetoricalRole.INTEGRAL_SUBJECT,
        verb="demonstrated",
        claim_context="liquid-gas contact dynamics depend on structured packing geometries."
    )
    print(f"[Integral Subject]:\n  {s1}\n")

    # 2. Integral Passive
    s2 = client.weave_citation(
        ref1,
        role=RhetoricalRole.INTEGRAL_PASSIVE,
        verb="established",
        claim_context="contactor scaling relationships were empirically derived."
    )
    print(f"[Integral Passive]:\n  {s2}\n")

    # 3. Contrastive Tension
    s3 = client.weave_citation(
        ref2,
        role=RhetoricalRole.CONTRASTIVE_TENSION,
        verb="argued",
        claim_context="calcination energy remained an unyielding boundary condition."
    )
    print(f"[Contrastive Tension]:\n  {s3}\n")

    # 4. Methodological Anchor
    s4 = client.weave_citation(
        ref1,
        role=RhetoricalRole.METHODOLOGICAL,
        claim_context="we scaled the draft velocity to 1.5 m/s."
    )
    print(f"[Methodological]:\n  {s4}\n")

    # 5. Parenthetical Consensus
    s5 = client.weave_citation(
        ref2,
        role=RhetoricalRole.PARENTHETICAL_CONSENSUS,
        claim_context="Mass transfer kinetics exhibit non-linear boundary constraints."
    )
    print(f"[Parenthetical Consensus]:\n  {s5}\n")

    print("=" * 65)
    print("3. BIBTEX EXPORT")
    print("=" * 65)
    for ref in [ref1, ref2]:
        print(client.citations.format_bibtex(ref))
        print()

if __name__ == "__main__":
    main()

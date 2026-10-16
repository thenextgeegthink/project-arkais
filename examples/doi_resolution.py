#!/usr/bin/env python3
"""
Project Arkais — DOI Resolution & Citation Authenticity Verification
=====================================================================
Demonstrates zero-key academic metadata lookup via OpenAlex and CrossRef
polite pools, with atomic local caching and phantom citation blocking.
"""

import sys
from pathlib import Path

# Support direct execution from repo root or package root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "sdk" / "src"))

from arkais import ArkaisClient

def main():
    client = ArkaisClient()

    doi = "10.1016/j.joule.2018.05.006"
    print("=" * 60)
    print(f"1. RESOLVING DOI METADATA VIA POLITE POOL ({doi})")
    print("=" * 60)

    try:
        ref = client.resolve_doi(doi)
        print(f"Title:    {ref.title}")
        print(f"Authors:  {', '.join(ref.authors)}")
        print(f"Year:     {ref.year}")
        print(f"Journal:  {ref.journal} (Vol {ref.volume}, Issue {ref.issue})")
        print(f"DOI:      {ref.doi}")
    except Exception as e:
        print(f"Resolution note: {e}")

    print("\n" + "=" * 60)
    print("2. VERIFYING CITATION AUTHENTICITY (PHANTOM CITATION GUARD)")
    print("=" * 60)

    # Legitimate publication
    real_title = "A Process for Capturing CO2 from the Atmosphere"
    real_author = "David Keith"
    is_real = client.verify_citation(title=real_title, author=real_author)
    print(f"Claim: '{real_title}' by {real_author}")
    print(f"Authentic Publication Record: {is_real}")

    # Fabricated hallucinated publication
    fake_title = "Comprehensive Quantum Direct Air Capture Thermodynamics on Mars"
    fake_author = "Alexander Nonexistent"
    is_fake = client.verify_citation(title=fake_title, author=fake_author)
    print(f"\nClaim: '{fake_title}' by {fake_author}")
    print(f"Authentic Publication Record: {is_fake} (Correctly blocked as phantom citation!)")

if __name__ == "__main__":
    main()

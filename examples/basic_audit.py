#!/usr/bin/env python3
"""
Project Arkais — Basic Stylometric Audit Example
================================================
Demonstrates evaluating academic text drafts against empirical
pre-LLM 1990s stylometric signatures.
"""

import sys
from pathlib import Path

# Support direct execution from repo root or package root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "sdk" / "src"))

from arkais import ArkaisClient

def main():
    client = ArkaisClient()

    # Sample 1: Authentic, rigorous academic prose
    authentic_text = """
    The regeneration of potassium hydroxide solutions in atmospheric contactors
    presents a substantial thermodynamic challenge. Early models proposed by Lackner (1999)
    suggested that calcination requires significant energetic input, potentially exceeding
    350 kJ per mole of captured carbon dioxide. However, empirical measurements obtained
    from pilot packing columns indicate that mass transfer rates are governed primarily
    by liquid-side boundary layers rather than gas-phase diffusion constraints.
    """

    print("=" * 60)
    print("AUDITING AUTHENTIC ACADEMIC TEXT")
    print("=" * 60)
    scorecard = client.audit(authentic_text)
    print(f"Audit Passed:    {scorecard.passed_qc}")
    print(f"Composite Score: {scorecard.composite_score:.1f}/10")
    print(f"Gates Passed:    {scorecard.gates_passed}/{scorecard.gates_total}")
    print("\nGate Details:")
    for gate in scorecard.gate_results:
        status = "PASS" if gate.passed else "FAIL"
        print(f"  [{status}] {gate.name:32s}: {gate.message}")

    # Sample 2: Synthetic AI slop with typical buzzwords and monotonic cadence
    synthetic_text = """
    In this modern era, it is crucial to delve into the transformative landscape of carbon capture.
    This study serves as a testament to the pivotal role of sustainable innovation.
    Furthermore, we explore the vibrant realm of environmental technologies to unlock groundbreaking solutions.
    """

    print("\n" + "=" * 60)
    print("AUDITING SYNTHETIC AI SLOP")
    print("=" * 60)
    scorecard_slop = client.audit(synthetic_text)
    print(f"Audit Passed:    {scorecard_slop.passed_qc}")
    print(f"Composite Score: {scorecard_slop.composite_score:.1f}/10")
    print(f"Gates Passed:    {scorecard_slop.gates_passed}/{scorecard_slop.gates_total}")
    print("\nGate Details:")
    for gate in scorecard_slop.gate_results:
        status = "PASS" if gate.passed else "FAIL"
        print(f"  [{status}] {gate.name:32s}: {gate.message}")

if __name__ == "__main__":
    main()

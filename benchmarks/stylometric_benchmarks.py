#!/usr/bin/env python3
"""
Project Arkais — Public Stylometric Benchmarks
==============================================
Runs deterministic stylometric evaluations contrasting pre-LLM 1990s
academic literature benchmarks against contemporary synthetic AI generation.
"""

import sys
from pathlib import Path

# Support direct execution from repo root or package root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "sdk" / "src"))

from arkais import ArkaisClient

PRE_LLM_HUMAN_CORPUS_EXCERPT = """
The determination of mass transfer coefficients in structured packing columns has historically
relied upon empirical correlations developed under idealized hydraulic regimes. As demonstrated
by Billet and Schultes (1994), liquid holdup and interfacial area exhibit non-linear dependence
on packing void fraction. While Lackner (1999) argued that energetic requirements for calcination
impose an asymptotic lower bound on direct atmospheric extraction, subsequent pilot measurements
suggest that pressure drop penalties can be mitigated through staggered corrugated geometries.
Nevertheless, substantial uncertainties persist regarding long-term scaling in reactive media.
"""

SYNTHETIC_AI_SLOP_EXCERPT = """
In today's fast-paced world, it is crucial to delve into the transformative power of direct air capture.
This innovative methodology stands as a testament to human ingenuity, offering a pivotal pathway
towards a greener and more sustainable future. Furthermore, by harnessing cutting-edge carbon sequestration,
researchers are unlocking a vibrant tapestry of eco-friendly solutions that truly revolutionize our planet.
Moreover, it is important to note that these groundbreaking advancements pave the way for unparalleled progress.
"""

def run_benchmark():
    client = ArkaisClient()

    print("=" * 70)
    print("PROJECT ARKAIS: DETERMINISTIC STYLOMETRIC BENCHMARK")
    print("Ground Truth 1990s Empirical Baseline vs. Synthetic AI Output")
    print("=" * 70)

    # Human benchmark
    human_res = client.audit(PRE_LLM_HUMAN_CORPUS_EXCERPT)
    ai_res = client.audit(SYNTHETIC_AI_SLOP_EXCERPT)

    print(f"\n{'Metric / Gate':<30} | {'Human Academic':<18} | {'Synthetic AI':<18}")
    print("-" * 70)

    h_gates = {g.gate_id: g for g in human_res.gate_results}
    a_gates = {g.gate_id: g for g in ai_res.gate_results}
    all_gate_ids = sorted(set(list(h_gates.keys()) + list(a_gates.keys())))

    for gid in all_gate_ids:
        hg = h_gates.get(gid)
        ag = a_gates.get(gid)
        name = hg.name if hg else (ag.name if ag else gid)
        h_str = f"{'PASS' if hg.passed else 'FAIL'} ({hg.score:.0f})" if hg else "N/A"
        a_str = f"{'PASS' if ag.passed else 'FAIL'} ({ag.score:.0f})" if ag else "N/A"
        print(f"{name[:28]:<30} | {h_str:<18} | {a_str:<18}")

    print("-" * 70)
    print(f"{'Composite Score':<30} | {human_res.composite_score:<18.1f} | {ai_res.composite_score:<18.1f}")
    print(f"{'Passed QC Gate':<30} | {'YES' if human_res.passed_qc else 'NO':<18} | {'YES' if ai_res.passed_qc else 'NO':<18}")
    print("=" * 70)

if __name__ == "__main__":
    run_benchmark()

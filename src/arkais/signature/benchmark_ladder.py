"""
ARKAIS v3.0 Empirical Evaluation Ladder Benchmark Runner.

Implements Claude's 6-level Empirical Evaluation Ladder (L0 to L5):
- L0: Baseline 17-line negative prompt (legacy negative constraints only)
- L1: Core authoring contract (00_contract + 01_reasoning)
- L2: L1 + authentic mined exemplars (02_research + pre-2000 corpus exemplars)
- L3: L2 + section blueprint (06_sections + 03_rhetoric)
- L4: L3 + domain scaffold (05_domains + 04_style)
- L5: L4 + citation archetypes & factored verification (07_citations + CoVe)
"""

import sys
from pathlib import Path

# Forward to the canonical benchmark ladder implementation
TOOLS_LADDER = Path(__file__).resolve().parents[5] / "06_TOOLS" / "signatures"
if str(TOOLS_LADDER) not in sys.path:
    sys.path.insert(0, str(TOOLS_LADDER))

from benchmark_ladder import (
    BENCHMARK_BRIEFS,
    LadderLevelEvaluation,
    BenchmarkLadderRunner,
    main
)

__all__ = [
    "BENCHMARK_BRIEFS",
    "LadderLevelEvaluation",
    "BenchmarkLadderRunner",
    "main"
]

if __name__ == "__main__":
    sys.exit(main())

# ARKAIS-v2.1: Canonical Specification for Pre-2000 Academic Prose
**Calibrated Empirical Signature for Scientific & Technical Manuscript Generation**  
*Project Arkais — The Next Geek Think | Governed by The Architrave & Codex Architecture*

## 1. Specification Overview
- **Signature Identifier**: `ARKAIS-v2.1`
- **Corpus Baseline**: Authentic peer-reviewed journal papers (1980–1999) from Scopus/arXiv/Crossref.
- **Empirical Sample**: 50 papers (617,204 words, 28,789 sentences).
- **Architecture**: Multi-tier distillation (Empirical Metrics $\rightarrow$ Operational Directives $\rightarrow$ AST Linter Schema $\rightarrow$ Few-Shot Exemplars).

---

## 2. Statistical Distributions & Dimensional Bounds

### S-1: Syntax & Elasticity
- **Mean Sentence Length**: **21.23 words** (Std Dev: **16.44**)
- **Percentiles**:
  - `p10`: **4.0 words** (Short punchy thesis/state statements)
  - `p25`: **9.0 words**
  - `p50 (Median)`: **18.0 words**
  - `p75`: **28.0 words**
  - `p90`: **40.0 words** (Multi-clause evidence synthesis)
  - `p99`: **81.0 words**
- **Elasticity Ratio ($p_{90} / p_{10}$)**: **10.00x** (High rhythmic burstiness).
- **Hypotactic Subordination**: **10.0%** of sentences contain subordinate conjunctions.
- **Suspended Opening Conditions**: **3.0%** of sentences open with situational or conditional clauses preceding the subject.

### D-1: Diction & Lexical Density
- **Nominalization Density**: **5.37%** of running tokens.
- **Explicit Transition Word Density**: **0.31%** (Restrained logical signaling).
- **AI Buzzword Leakage**: **59 hits** (Zero-tolerance gate).

### E-1: Epistemic Stance & Modality
- **Hedge-to-Certainty Ratio**: **1.55:1** (Hedging strictly outnumbers dogmatic assertions).
- **Mid-Sentence Transition Placement**: **14.5%** of causal markers are placed medially (parenthetical commas).

### M-1: Paragraph Opening Architecture (Archetypes)
Every paragraph must belong to one of the five canonical opening archetypes:
1. **ARCH-01 (Empirical Condition Prepend)**: Contextual boundary or thermodynamic state parameter.
2. **ARCH-02 (Direct Observation Anchor)**: Measured value, empirical phenomenon, or direct figure reference.
3. **ARCH-03 (Methodological Action)**: Purposeful laboratory, procedural, or computational execution.
4. **ARCH-04 (Dialectical Friction)**: Tension against previous findings or counter-evidence.
5. **ARCH-05 (Operational Definition)**: Axiomatic grounding or mathematical constraint.

---

## 3. Disciplinary Calibration Matrix
| Discipline | Paper Count | Analyzed Words | Mean Sentence Length | Nominalization % | Epistemic Ratio |
|---|---|---|---|---|---|
| Computer Science | 10 | 94,298 | 23.7 | 5.29% | 1.58:1 |
| Astrophysics | 7 | 94,440 | 33.4 | 4.23% | 1.79:1 |
| Political Science | 6 | 56,689 | 25.3 | 5.81% | 1.73:1 |
| Humanities | 6 | 66,702 | 30.0 | 5.44% | 2.52:1 |
| Economics | 5 | 132,329 | 22.2 | 5.7% | 1.06:1 |
| Sociology | 5 | 71,381 | 19.7 | 6.32% | 2.04:1 |
| Physics | 3 | 28,266 | 23.3 | 4.34% | 0.57:1 |
| Psychology | 3 | 33,550 | 21.0 | 5.86% | 3.09:1 |
| Environmental Studies | 2 | 10,477 | 20.9 | 5.56% | 1.77:1 |
| Education | 1 | 10,840 | 28.7 | 3.57% | 4.3:1 |
| Law | 1 | 6,481 | 30.2 | 4.74% | 0.95:1 |

---

## 4. Verification & Linter Directives
Any manuscript generated under `ARKAIS-v2.1` must pass the validation harness:
1. Zero AI Buzzwords.
2. Zero Banned Paragraph Openers.
3. Zero False Dichotomy Rhetorical Patterns.
4. Zero Pedagogical Dictionaries Glosses.
5. Mean sentence length within [22.0, 28.0] words with burstiness elasticity $\ge 2.2$.

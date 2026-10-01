# ARKAIS-v3.0: Canonical Specification for Pre-2000 Academic Prose
**10,000-Paper Landmark Calibrated Signature for Scholarly Manuscript Generation**  
*Project Arkais — The Next Geek Think | Governed by The Architrave & Codex Architecture*

## 1. Specification Overview
- **Signature Identifier**: `ARKAIS-v3.0`
- **Corpus Baseline**: 10,000 authentic peer-reviewed journal papers (1980–1999) across STEM, Social Sciences, and Humanities (`ARK-001` through `ARK-10000`).
- **Empirical Calibration Sample**: 8,998 training papers, 117,083 600-word windows (98,538 STEM, 18,392 Social Sciences, 153 Humanities).
- **Holdout Validation Split**: 1,000 stratified papers isolated under read-only POSIX `0444` (zero test leakage certified).
- **Composite Discrimination AUROC**: **`0.7747`** against 500-draft synthetic defect benchmark.
- **Architecture**: Multi-tier distillation (Empirical Bootstrap Metrics $\rightarrow$ Operational Directives $\rightarrow$ 10 Deterministic Invariant Gates $\rightarrow$ Stratified Exemplars).

---

## 2. Statistical Distributions & Dimensional Bounds (Core Bands)

### S-1: Syntax & Sentence Cadence
- **Target Mean Sentence Length**: **20.5 – 44.1 words**
- **Cadence Standard Deviation ($\sigma$)**:
  - `P5 [95% CI]`: **8.5 [8.3, 8.6]**
  - `P25 (Target Q1)`: **11.8**
  - `P50 (Target Median)`: **16.1**
  - `P75 (Target Q3)`: **24.7**
  - `P95 [95% CI]`: **55.6 [52.5, 58.3]**
- **Elasticity Ratio ($p_{90} / p_{10}$)**: $\ge$ **2.20x** (High rhythmic modulation, interspersing short declarative anchors with layered compound-complex periods).

### D-1: Diction & Lexical Packaging
- **Nominalization Density**:
  - `P5 [95% CI]`: **0.8% [0.6%, 1.0%]**
  - `P25 (Target Q1)`: **3.8%**
  - `P50 (Target Median)`: **5.1%**
  - `P75 (Target Q3)`: **6.5%**
  - `P95 [95% CI]`: **8.7% [8.6%, 8.8%]**
- **AI Buzzword Leakage**: **0 Tolerance** across 18 canonical tripwires (delve, tapestry, revolutionize, testament, multifaceted, pivotal, game-changing, paramount, beacon, plethora, interplay, cornerstone, synergy, orchestrate, foster, seamlessly, holistic, cutting-edge).
- **Banned Rhetorical Openers**: **0 Tolerance** across robotic transition families (Moreover, Furthermore, Additionally, In conclusion, Firstly, Secondly).

### E-1: Epistemic Stance & Modality
- **Hedge-to-Certainty Ratio (H:C)**:
  - `Floor (P5)`: **0.00:1**
  - `Target Median (P50)`: **2.00:1**
  - `Target IQR`: **[1.00:1, 4.00:1]**
- **Epistemic Modesty**: Explicit qualification of unproven mechanisms and clear articulation of thermodynamic, methodological, or boundary conditions.

### M-1: Paragraph Opening Architecture (Archetypes)
Every paragraph must belong to one of the five canonical opening archetypes:
1. **ARCH-01 (Problem Confrontation & Direct Empirical Thesis)**: Immediate thesis grounding, empirical problem framing, or primary observation.
2. **ARCH-02 (Methodological Apparatus & Physical Friction)**: Apparatus specifications, operational parameter states, or laboratory execution.
3. **ARCH-03 (Epistemic Modesty & Boundary Delineation)**: Cautious qualification, experimental uncertainty bounds, or tentative interpretation.
4. **ARCH-04 (Structural Pivot & Synthesis)**: Dialectical friction against prior models or synthesis across observations.
5. **ARCH-05 (Suspended Subordination & Hypotaxis)**: Prepending conditional or situational clauses before the main verb.

---

## 3. Disciplinary Stratification Matrix
| Discipline Stratum | Calibrated Papers | 600-Word Windows | Median Cadence ($\sigma$) | Median Nominals (%) | Epistemic Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **STEM** | 7,764 | 98,538 | 14.7 | 4.7% | 2.00:1 |
| **Social Sciences** | 1,222 | 18,392 | 15.2 | 5.2% | 2.00:1 |
| **Humanities** | 12 | 153 | 22.1 | 5.4% | 2.00:1 |
| **Core (Equal 1/3 Mixture)** | — | 6,000 | 16.1 | 5.1% | 2.00:1 |

---

## 4. Verification & 10 Deterministic Quality Gates
Any manuscript evaluated under `ARKAIS-v3.0` is assessed against the 10 orthogonal deterministic gates:
1. **GATE-01 (Banned Paragraph Openers)**: Rejects robotic transition openers (`Moreover,`, `Furthermore,`, etc.).
2. **GATE-02 (Synthetic Contrast Elimination)**: Rejects synthetic false-dichotomy tropes across 4 pattern families (`is not X, it is Y`, `not X, but Y`, `X, not Y`, `not merely X but Y`).
3. **GATE-03 (No Patronizing Analogies)**: Rejects pedagogical conversational glosses (`Think of it as...`, `Imagine a...`).
4. **GATE-04 (Sentence Cadence & Length Variance)**: Enforces $\sigma \in [8.5, 55.6]$ and mean sentence length $\in [20.5, 44.1]$ words.
5. **GATE-05 (Nominal Packaging Density)**: Enforces nominalization token percentage $\in [0.8\%, 8.7\%]$.
6. **GATE-06 (Epistemic Calibration)**: Enforces empirical hedge-to-certainty ratio $\ge 0.0:1$ (Target 2.0:1).
7. **GATE-07 (Parenthetical Visual Anchoring)**: Validates disciplined parenthetical figure/table citations `(Figure 1)`.
8. **GATE-08 (Numerical Unit Discipline)**: Validates SI units and quantitative measurements attached to numbers.
9. **GATE-09 (Connected Prose / Anti-Bulleting)**: Rejects bullet points, numbered lists, and fragmentary summaries.
10. **GATE-10 (Citation Weaving & Density)**: Validates bibliographic reference integration and density bounds.

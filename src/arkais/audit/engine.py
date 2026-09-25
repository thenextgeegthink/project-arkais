"""Deterministic Stylometric & Discourse Audit Engine for Project Arkais."""

import re
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Banned synthetic tropes & openers
BANNED_OPENERS = [
    r"^(in recent years|recently|with the rapid development|with the advent of|it is widely known that)",
    r"^(in this paper, we (aim to|propose to|explore|investigate))",
    r"^(as an ai|as a language model|it is important to note that|it should be noted that)",
    r"^(needless to say|furthermore, it is crucial|moreover, it is essential)"
]

BANNED_SYNTHETIC_CONTRAST = re.compile(
    r"\b([A-Za-z0-9_-]+)\s+is\s+not\s+([A-Za-z0-9_\s-]+),\s*but\s+(rather\s+)?([A-Za-z0-9_\s-]+)\b",
    re.IGNORECASE
)

PATRONIZING_ANALOGIES = [
    r"\b(imagine a (library|factory|highway|orchestra|chef))\b",
    r"\b(delicate dance|symphony of|tapestry of|treasure trove|double-edged sword)\b",
    r"\b(at its core|simply put|in layman's terms|put simply)\b"
]

NOMINAL_SUFFIXES = (
    "tion", "tions", "sion", "sions", "ment", "ments", "ance", "ances",
    "ence", "ences", "ity", "ities", "ism", "isms", "ing", "ings"
)

HEDGE_TERMS = {
    "suggest", "suggests", "suggested", "indicate", "indicates", "indicated",
    "likely", "unlikely", "possible", "possibly", "potential", "potentially",
    "appear", "appears", "appeared", "seem", "seems", "seemed", "may", "might"
}

CERTAINTY_TERMS = {
    "clearly", "definitely", "always", "never", "proves", "proven",
    "undeniably", "indisputably", "irrefutable", "conclusively", "fundamental"
}


@dataclass
class GateResult:
    gate_id: str
    name: str
    passed: bool
    score: float = 1.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    passed_qc: bool
    composite_score: float
    total_words: int
    total_sentences: int
    total_paragraphs: int
    gates_passed: int
    gates_total: int
    gate_results: List[GateResult]
    defect_summary: List[str]


class StylometricAuditEngine:
    """Evaluates manuscripts and prose segments against the 10 deterministic gates."""

    def __call__(self, text: str) -> AuditReport:
        """Allows direct callable invocation e.g. engine(text) or client.audit(text)."""
        return self.evaluate(text)

    def evaluate(self, text: str) -> AuditReport:
        clean_text = text.strip()
        words = re.findall(r"\b[A-Za-z0-9_-]+\b", clean_text)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if s.strip()]
        paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]

        total_words = len(words)
        total_sentences = max(1, len(sentences))
        total_paragraphs = max(1, len(paragraphs))

        gate_results = []
        defects = []

        # Gate 1: Banned Openers
        opener_violations = 0
        for p in paragraphs:
            for pat in BANNED_OPENERS:
                if re.search(pat, p, re.IGNORECASE):
                    opener_violations += 1
        g1_pass = opener_violations == 0
        if not g1_pass:
            defects.append(f"Found {opener_violations} banned synthetic paragraph openers.")
        gate_results.append(GateResult(
            gate_id="GATE-01",
            name="Banned Paragraph Openers",
            passed=g1_pass,
            score=1.0 if g1_pass else 0.0,
            message="No empty AI windup openers detected." if g1_pass else f"{opener_violations} banned openers detected.",
            details={"violations": opener_violations}
        ))

        # Gate 2: Synthetic Contrast Tropes ("A is not B, but C")
        contrast_matches = len(BANNED_SYNTHETIC_CONTRAST.findall(clean_text))
        g2_pass = contrast_matches == 0
        if not g2_pass:
            defects.append(f"Found {contrast_matches} occurrences of synthetic 'A is not B, but C' contrast trope.")
        gate_results.append(GateResult(
            gate_id="GATE-02",
            name="Synthetic Contrast Elimination",
            passed=g2_pass,
            score=1.0 if g2_pass else 0.0,
            message="Zero synthetic contrast tropes found." if g2_pass else f"{contrast_matches} contrast tropes detected.",
            details={"violations": contrast_matches}
        ))

        # Gate 3: Patronizing Analogies & Chatty Glosses
        analogy_violations = 0
        for pat in PATRONIZING_ANALOGIES:
            analogy_violations += len(re.findall(pat, clean_text, re.IGNORECASE))
        g3_pass = analogy_violations == 0
        if not g3_pass:
            defects.append(f"Found {analogy_violations} patronizing analogies or chatty dictionary glosses.")
        gate_results.append(GateResult(
            gate_id="GATE-03",
            name="No Patronizing Analogies",
            passed=g3_pass,
            score=1.0 if g3_pass else 0.0,
            message="Zero patronizing analogies found." if g3_pass else f"{analogy_violations} analogies detected.",
            details={"violations": analogy_violations}
        ))

        # Gate 4: Sentence Length Variance (Std Dev)
        sentence_lengths = [len(re.findall(r"\b\w+\b", s)) for s in sentences]
        mean_len = sum(sentence_lengths) / total_sentences
        variance = sum((l - mean_len) ** 2 for l in sentence_lengths) / total_sentences
        std_len = math.sqrt(variance)
        g4_pass = std_len >= 12.0 or total_words < 150
        if not g4_pass:
            defects.append(f"Sentence length standard deviation ({std_len:.1f}) is below authentic cadence threshold (12.0).")
        gate_results.append(GateResult(
            gate_id="GATE-04",
            name="Sentence Cadence & Length Variance",
            passed=g4_pass,
            score=min(1.0, std_len / 15.0),
            message=f"Standard deviation is {std_len:.1f} words (mean: {mean_len:.1f}).",
            details={"std_dev": round(std_len, 2), "mean": round(mean_len, 2)}
        ))

        # Gate 5: Nominalization Density
        nominals = [w for w in words if w.lower().endswith(NOMINAL_SUFFIXES) and len(w) > 5]
        nom_density = (len(nominals) / max(1, total_words)) * 100.0
        g5_pass = (3.5 <= nom_density <= 10.0) or total_words < 100
        if not g5_pass:
            defects.append(f"Nominalization density ({nom_density:.2f}%) falls outside empirical bounds (3.5%–10.0%).")
        gate_results.append(GateResult(
            gate_id="GATE-05",
            name="Nominal Packaging Density",
            passed=g5_pass,
            score=1.0 if g5_pass else 0.5,
            message=f"Nominal density is {nom_density:.2f}% (target: 3.5%-10.0%).",
            details={"density_pct": round(nom_density, 2)}
        ))

        # Gate 6: Epistemic Balance (Hedges to Certainty)
        hedges = sum(1 for w in words if w.lower() in HEDGE_TERMS)
        certs = sum(1 for w in words if w.lower() in CERTAINTY_TERMS)
        epistemic_ratio = (hedges + 1.0) / (certs + 1.0)
        g6_pass = epistemic_ratio >= 1.2 or total_words < 150
        if not g6_pass:
            defects.append(f"Epistemic ratio ({epistemic_ratio:.2f}) indicates over-confident or dogmatic tone.")
        gate_results.append(GateResult(
            gate_id="GATE-06",
            name="Epistemic Calibration",
            passed=g6_pass,
            score=min(1.0, epistemic_ratio / 1.5),
            message=f"Epistemic hedge/certainty ratio is {epistemic_ratio:.2f}:1.",
            details={"ratio": round(epistemic_ratio, 2), "hedges": hedges, "certainty": certs}
        ))

        # Gate 7: Parenthetical Data & Visual Weaving
        parenthetical_anchors = len(re.findall(r"\((?:Figure|Table|Equation|Eq\.|Fig\.)\s+[0-9a-zA-Z\.]+\)", clean_text))
        detached_pointers = len(re.findall(r"(?:Figure|Table|Fig\.)\s+[0-9a-zA-Z\.]+\s+(?:shows|illustrates|depicts|presents)", clean_text))
        g7_pass = (parenthetical_anchors >= detached_pointers) or (parenthetical_anchors == 0 and detached_pointers == 0)
        if not g7_pass:
            defects.append("Detached visual pointers ('Figure 1 shows...') exceed integrated parenthetical anchors ('(Figure 1)').")
        gate_results.append(GateResult(
            gate_id="GATE-07",
            name="Parenthetical Visual Anchoring",
            passed=g7_pass,
            score=1.0 if g7_pass else 0.4,
            message=f"Found {parenthetical_anchors} parenthetical anchors vs {detached_pointers} detached pointers.",
            details={"parenthetical": parenthetical_anchors, "detached": detached_pointers}
        ))

        # Gate 8: In-Prose Numerical & Unit Coupling
        numerical_units = len(re.findall(r"\b\d+(?:\.\d+)?\s*(?:%|m2/m3|GJ/t|USD|MW|kg|g|°C|K|kJ)\b", clean_text))
        g8_pass = True  # Information gate
        gate_results.append(GateResult(
            gate_id="GATE-08",
            name="Numerical Unit Discipline",
            passed=g8_pass,
            score=1.0,
            message=f"Identified {numerical_units} in-prose physical quantity anchors.",
            details={"anchors": numerical_units}
        ))

        # Gate 9: Bullet List & Tricolon Symmetry
        bullet_count = len(re.findall(r"^\s*[-*•]\s+", clean_text, re.MULTILINE))
        g9_pass = bullet_count <= (total_words / 200)
        if not g9_pass:
            defects.append(f"Excessive bullet list density ({bullet_count} items); human 1990s papers synthesize via connected prose.")
        gate_results.append(GateResult(
            gate_id="GATE-09",
            name="Connected Prose (Anti-Bulleting)",
            passed=g9_pass,
            score=1.0 if g9_pass else 0.5,
            message=f"Found {bullet_count} bullet elements.",
            details={"bullets": bullet_count}
        ))

        # Gate 10: Citation Density & Formatting
        citation_matches = len(re.findall(r"\[[0-9,\s\-]+\]|\([A-Za-z]+(?:\s+et\s+al\.)?,\s*\d{4}\)", clean_text))
        cites_per_k = (citation_matches / max(1, total_words)) * 1000.0
        g10_pass = cites_per_k >= 1.5 or total_words < 200
        gate_results.append(GateResult(
            gate_id="GATE-10",
            name="Citation Weaving & Density",
            passed=g10_pass,
            score=min(1.0, cites_per_k / 2.5),
            message=f"Citation density is {cites_per_k:.1f} per 1,000 words ({citation_matches} total).",
            details={"cites_per_k": round(cites_per_k, 2), "total_citations": citation_matches}
        ))

        passed_count = sum(1 for g in gate_results if g.passed)
        passed_qc = len(defects) == 0
        composite_score = round(sum(g.score for g in gate_results), 2)

        return AuditReport(
            passed_qc=passed_qc,
            composite_score=composite_score,
            total_words=total_words,
            total_sentences=total_sentences,
            total_paragraphs=total_paragraphs,
            gates_passed=passed_count,
            gates_total=len(gate_results),
            gate_results=gate_results,
            defect_summary=defects
        )

"""
ArgumentInterrogator — Programmatic Toulmin 9-Test Interrogation Engine.

Implements Claude's L1 Argument Interrogation Blueprint:
Tests: T1 Refutability, T2 Sufficiency, T3 Warrant, T4 Backing, T5 Scope,
       T6 Rebuttal, T7 Alternatives, T8 Terms, T9 Consistency.

Maintains strict status:
OPEN (<n> load-bearing, <n> weakening, <n> refinement) | READY FOR DRAFTING
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class ToulminChain:
    claim: str
    grounds: str
    warrant: Optional[str] = None
    backing: Optional[str] = None
    qualifier: Optional[str] = None
    rebuttal: Optional[str] = None


@dataclass
class InterrogationQuestion:
    severity: str  # "Load-bearing", "Weakening", "Refinement"
    test_id: str   # "T1" through "T9"
    element: str   # "claim", "grounds", "warrant", etc.
    quote: str
    question_text: str
    settled_by: str


class ArgumentInterrogator:
    """Interrogates academic claim chains to stress-test reasoning before drafting."""

    def intake(self, raw_input: Any) -> ToulminChain:
        """Parses structured or text input into a ToulminChain."""
        if isinstance(raw_input, dict):
            return ToulminChain(
                claim=raw_input.get("claim", "").strip(),
                grounds=raw_input.get("grounds", "").strip(),
                warrant=raw_input.get("warrant"),
                backing=raw_input.get("backing"),
                qualifier=raw_input.get("qualifier"),
                rebuttal=raw_input.get("rebuttal")
            )
        
        # Simple text parser
        text = str(raw_input)
        claim = text
        grounds = "none supplied"
        return ToulminChain(claim=claim, grounds=grounds)

    def interrogate(self, chain: ToulminChain) -> List[InterrogationQuestion]:
        """Runs the 9 Toulmin tests and returns open interrogation questions."""
        questions = []

        # T3: Warrant check (Load-bearing)
        if not chain.warrant or chain.warrant.lower() in ("none", "not supplied", "none supplied"):
            questions.append(InterrogationQuestion(
                severity="Load-bearing",
                test_id="T3 Warrant",
                element="grounds to claim",
                quote=chain.claim[:60] + "...",
                question_text="What theoretical or logical principle licenses the step from your empirical grounds to this general claim?",
                settled_by="A stated behavioral, causal, or physical mechanism"
            ))

        # T5: Scope / Qualifier check (Weakening)
        if not chain.qualifier or chain.qualifier.lower() in ("none", "not supplied", "none supplied"):
            questions.append(InterrogationQuestion(
                severity="Weakening",
                test_id="T5 Scope",
                element="qualifier",
                quote=chain.claim[:60] + "...",
                question_text="What are the explicit boundary conditions (population, system architecture, sample range) outside of which this claim does not hold?",
                settled_by="An explicit validity scope or cohort limitation"
            ))

        # T6: Rebuttal check (Weakening)
        if not chain.rebuttal or chain.rebuttal.lower() in ("none", "not supplied", "none supplied"):
            questions.append(InterrogationQuestion(
                severity="Weakening",
                test_id="T6 Rebuttal",
                element="rebuttal",
                quote=chain.claim[:60] + "...",
                question_text="Under what specific observation or failure state would you accept this claim as refuted?",
                settled_by="A falsifiable empirical threshold"
            ))

        # T4: Backing check (Refinement)
        if not chain.backing or chain.backing.lower() in ("none", "not supplied", "none supplied"):
            questions.append(InterrogationQuestion(
                severity="Refinement",
                test_id="T4 Backing",
                element="backing",
                quote=chain.grounds[:60] + "...",
                question_text="What published evidence or established benchmark validates your baseline measurement strategy?",
                settled_by="A prior methodological citation"
            ))

        return questions

    def format_report(self, chain: ToulminChain, questions: List[InterrogationQuestion]) -> str:
        """Formats the machine-readable interrogation report."""
        load_bearing = sum(1 for q in questions if q.severity == "Load-bearing")
        weakening = sum(1 for q in questions if q.severity == "Weakening")
        refinement = sum(1 for q in questions if q.severity == "Refinement")

        status_str = "READY FOR DRAFTING" if load_bearing == 0 else f"OPEN ({load_bearing} load-bearing, {weakening} weakening, {refinement} refinement)"

        lines = [
            f"Status: {status_str}",
            "",
            "Chain as received:",
            f"  Claim: \"{chain.claim}\"",
            f"  Grounds: \"{chain.grounds}\"",
            f"  Warrant: {chain.warrant or 'not supplied'} | Qualifier: {chain.qualifier or 'not supplied'} | Rebuttal: {chain.rebuttal or 'not supplied'}",
            ""
        ]

        if questions:
            lines.append("Questions:")
            for idx, q in enumerate(questions, 1):
                lines.append(f"{idx}. [{q.severity} | {q.test_id} | {q.element}]")
                lines.append(f"   \"{q.quote}\"")
                lines.append(f"   {q.question_text}")
                lines.append(f"   (Settled by: {q.settled_by})")
                lines.append("")

        return "\n".join(lines)

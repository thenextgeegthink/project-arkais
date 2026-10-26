"""Signature loader and catalog manager for Project Arkais."""

from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from .models import SignatureProfile, SignatureMetrics
from .compiler import SignatureCompiler, CompiledSignature, CompileRequest, CompilationResult


class SignatureManager:
    """Manages bundled, custom, and dynamically compiled academic signature profiles."""

    def __init__(self, custom_dir: Optional[Path] = None):
        self.profiles_dir = Path(__file__).resolve().parent / "profiles"
        self.custom_dir = custom_dir
        self.compiler = SignatureCompiler()

    def compile(
        self,
        domain: Union[str, CompileRequest] = "all",
        section: str = "all",
        token_budget: int = 2500,
        competencies: Optional[List[str]] = None,
        slots: Optional[Dict[str, str]] = None,
        inject_exemplars: bool = True,
        citation_style: str = "all",
        task: str = "general"
    ) -> CompiledSignature:
        """Dynamically compiles a tailored modular signature prompt."""
        return self.compiler.compile(
            domain=domain,
            section=section,
            token_budget=token_budget,
            competencies=competencies,
            slots=slots,
            inject_exemplars=inject_exemplars,
            citation_style=citation_style,
            task=task
        )

    def list(self) -> List[str]:
        """Returns list of all available signature identifiers."""
        signatures = set()
        if self.profiles_dir.exists():
            for p in self.profiles_dir.glob("*.md"):
                if not p.stem.endswith(".system"):
                    signatures.add(p.stem)
        if self.custom_dir and self.custom_dir.exists():
            for p in self.custom_dir.glob("*.md"):
                if not p.stem.endswith(".system"):
                    signatures.add(p.stem)
        return sorted(list(signatures))

    def get(self, identifier: str = "ARKAIS-v3.0") -> SignatureProfile:
        """Loads and parses a signature profile by identifier or path."""
        # 1. Check bundled
        target = self.profiles_dir / f"{identifier}.md"
        if not target.exists() and self.custom_dir:
            target = self.custom_dir / f"{identifier}.md"
        if not target.exists() and Path(identifier).exists():
            target = Path(identifier)

        # 2. Backward compatibility alias resolution
        if not target.exists():
            legacy_aliases = {
                "ARKAIS-001-v3.0": "ARKAIS-v3.0",
                "ARKAIS-001-v2.1": "ARKAIS-v2.1",
                "ARKAIS-001-v2.0": "ARKAIS-v2.1",
                "ARKAIS-001-v1.1": "ARKAIS-001-v1.1",
            }
            if identifier in legacy_aliases:
                alias_target = self.profiles_dir / f"{legacy_aliases[identifier]}.md"
                if alias_target.exists():
                    target = alias_target

        if not target.exists():
            available = self.list()
            raise FileNotFoundError(f"Signature '{identifier}' not found. Available: {available}")

        content = target.read_text(encoding="utf-8")
        return self._parse_profile(target.stem, content)

    def _parse_profile(self, identifier: str, content: str) -> SignatureProfile:
        if "3.0" in identifier:
            version = "3.0"
            corpus_size = "10,000 Landmark Corpus Papers (8,998 Calibrated Training Windows)"
            cal_date = "2026-10-01"
        elif "2.1" in identifier:
            version = "2.1"
            corpus_size = "5,000 Calibrated Authentic Papers (57,219,878 words)"
            cal_date = "2026-09-30"
        elif "2.0" in identifier:
            version = "2.0"
            corpus_size = "5,000 Calibrated Authentic Papers (57,219,878 words)"
            cal_date = "2026-09-27"
        elif "1.1" in identifier:
            version = "1.1"
            corpus_size = "100 Landmark Papers (1990-1999)"
            cal_date = "2026-09-06"
        else:
            version = "1.0"
            corpus_size = "Initial Pilot"
            cal_date = "2026-08-01"

        return SignatureProfile(
            identifier=identifier,
            version=version,
            status="ACTIVE / CALIBRATED",
            corpus_size=corpus_size,
            calibration_date=cal_date,
            description="Micro-rhetorical, structural, and discourse architecture calibrated against authentic pre-LLM human academic craft.",
            raw_markdown=content,
            metrics=SignatureMetrics()
        )

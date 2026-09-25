"""Signature loader and catalog manager for Project Arkais."""

from pathlib import Path
from typing import List, Dict, Optional
from .models import SignatureProfile, SignatureMetrics


class SignatureManager:
    """Manages bundled and custom academic signature profiles."""

    def __init__(self, custom_dir: Optional[Path] = None):
        self.profiles_dir = Path(__file__).resolve().parent / "profiles"
        self.custom_dir = custom_dir

    def list(self) -> List[str]:
        """Returns list of all available signature identifiers."""
        signatures = set()
        if self.profiles_dir.exists():
            for p in self.profiles_dir.glob("*.md"):
                signatures.add(p.stem)
        if self.custom_dir and self.custom_dir.exists():
            for p in self.custom_dir.glob("*.md"):
                signatures.add(p.stem)
        return sorted(list(signatures))

    def get(self, identifier: str = "ARKAIS-001-v2.0") -> SignatureProfile:
        """Loads and parses a signature profile by identifier or path."""
        # 1. Check bundled
        target = self.profiles_dir / f"{identifier}.md"
        if not target.exists() and self.custom_dir:
            target = self.custom_dir / f"{identifier}.md"
        if not target.exists() and Path(identifier).exists():
            target = Path(identifier)

        if not target.exists():
            available = self.list()
            raise FileNotFoundError(f"Signature '{identifier}' not found. Available: {available}")

        content = target.read_text(encoding="utf-8")
        return self._parse_profile(target.stem, content)

    def _parse_profile(self, identifier: str, content: str) -> SignatureProfile:
        if "2.0" in identifier:
            version = "2.0"
            corpus_size = "1,500 Calibrated Authentic Papers (16,853,926 words)"
            cal_date = "2026-09-24"
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

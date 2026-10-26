"""Versioned keyness table loader from signature bundle (METH-05 / THE-174).

Replaces unconditional zero-tolerance buzzword bans with an evidence-grounded,
corpus-relative keyness engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

SUPPORTED_KEYNESS_SCHEMA = "arkais.keyness.table.v1"
WORKSPACE_ROOT = Path(__file__).resolve().parents[5]
SIGNATURES_DIR = WORKSPACE_ROOT / "04_SIGNATURES" / "active"


class KeynessTableError(ValueError):
    """Raised when a keyness table is missing, invalid, or uncalibrated."""


@dataclass(frozen=True)
class KeynessEntry:
    word: str
    target_count: int
    reference_count: int
    target_rate_per_1k: float
    reference_rate_per_1k: float
    relative_rate: Optional[float]
    keyness: float


class KeynessTable:
    """Read-only queryable keyness table for vocabulary overuse scoring."""

    def __init__(
        self,
        schema_version: str,
        signature_id: str,
        consensus_floor: int,
        threshold: Optional[float],
        words: Mapping[str, Dict[str, Any]],
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.schema_version = schema_version
        self.signature_id = signature_id
        self.consensus_floor = consensus_floor
        self.threshold = threshold
        self.meta = meta or {}
        self._entries: Dict[str, KeynessEntry] = {}

        for w, v in words.items():
            self._entries[w.lower()] = KeynessEntry(
                word=w.lower(),
                target_count=v.get("target_count", 0),
                reference_count=v.get("reference_count", 0),
                target_rate_per_1k=v.get("target_rate_per_1k", 0.0),
                reference_rate_per_1k=v.get("reference_rate_per_1k", 0.0),
                relative_rate=v.get("relative_rate"),
                keyness=v.get("keyness", 0.0),
            )

    def __contains__(self, word: str) -> bool:
        return word.lower() in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, word: str) -> Optional[KeynessEntry]:
        return self._entries.get(word.lower())

    def score(self, word: str) -> Optional[float]:
        entry = self.get(word)
        return entry.keyness if entry else None

    def relative_rate(self, word: str) -> Optional[float]:
        entry = self.get(word)
        return entry.relative_rate if entry else None

    def is_overused(self, word: str) -> bool:
        """Evaluate if word exceeds keyness cut-off.

        Refuses if threshold is unset (C5 ruling: threshold must be calibrated against
        ablation, not hardcoded in advance).
        """
        if self.threshold is None:
            raise KeynessTableError(
                f"Cannot evaluate overrepresentation for {word!r}: keyness threshold is "
                f"deliberately unset in {self.signature_id} per operator ruling C5 until "
                f"gate ablation is executed."
            )
        entry = self.get(word)
        if not entry:
            return False
        return entry.keyness >= self.threshold


def load_keyness_table(
    source: Optional[Union[Path, str, Dict[str, Any]]] = None,
    signature_id: str = "ARKAIS-v3.0",
) -> KeynessTable:
    """Load and validate keyness baseline table.

    Fails loudly with an actionable message if the table is absent or empty.
    """
    payload: Dict[str, Any]

    if isinstance(source, dict):
        payload = source
    else:
        sig_path: Path
        if source is not None:
            sig_path = Path(source)
        else:
            sig_path = SIGNATURES_DIR / f"{signature_id}.json"

        if not sig_path.exists():
            raise KeynessTableError(
                f"Signature file {sig_path} not found; cannot load keyness table for {signature_id}."
            )

        try:
            data = json.loads(sig_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise KeynessTableError(f"Failed to read signature JSON from {sig_path}: {e}") from e

        # If source file is already a keyness table JSON
        if data.get("kind") == SUPPORTED_KEYNESS_SCHEMA:
            payload = data
        elif "keyness_table" in data and isinstance(data["keyness_table"], dict):
            payload = data["keyness_table"]
        else:
            raise KeynessTableError(
                f"Keyness table absent from signature bundle '{signature_id}'; "
                f"cannot evaluate FRR-budgeted keyness without a calibrated baseline table. "
                f"Operator must build period-matched reference corpus via METH-15 / keyness_table.py."
            )

    # Validate schema
    kind = payload.get("kind", SUPPORTED_KEYNESS_SCHEMA)
    if kind != SUPPORTED_KEYNESS_SCHEMA:
        raise KeynessTableError(
            f"Unsupported keyness table schema {kind!r}; expected {SUPPORTED_KEYNESS_SCHEMA!r}."
        )

    words_data = payload.get("words", [])
    if not words_data:
        raise KeynessTableError(
            f"Keyness table for '{signature_id}' is empty (0 words); "
            f"cannot score vocabulary without calibrated reference counts."
        )

    words_map: Dict[str, Dict[str, Any]] = {}
    if isinstance(words_data, list):
        for item in words_data:
            if "word" in item:
                words_map[item["word"]] = item
    elif isinstance(words_data, dict):
        words_map = words_data

    return KeynessTable(
        schema_version=kind,
        signature_id=payload.get("signature_id", signature_id),
        consensus_floor=payload.get("consensus_floor", 5),
        threshold=payload.get("threshold"),
        words=words_map,
        meta=payload.get("meta"),
    )

"""Shared sentence segmentation & tokenization contract.

This module is the single source of truth for how Project Arkais breaks text into
sentences and counts words. It exists because the calibration pipeline and the
production audit engine previously disagreed: calibration used an
abbreviation-protected splitter, the audit engine used a naive
``(?<=[.!?])\\s+`` split. The same paragraph therefore produced different
sentence boundaries -- and therefore different cadence statistics -- depending on
which side measured it.

Owning this in the SDK (rather than in ``06_TOOLS``) is deliberate: the SDK is the
published, dependency-free consumer, and the calibration pipeline already imports
the SDK. See ``.scratch/agi-consult/reconciled-decisions.md`` F1/F6.

Contract rules:
  * Both sides MUST call :func:`split_into_sentences` for sentence boundaries.
  * Both sides MUST call :func:`count_words` / :func:`sentence_word_lengths`
    for every length-derived statistic. Never re-derive a word count inline.
  * Changing anything here changes :data:`SPLITTER_VERSION`, which is recorded in
    calibration and audit reports. Recalibration is a separate, operator-run
    ceremony; this module never triggers one.
"""

from __future__ import annotations

import hashlib
import inspect
import re
from typing import List

__all__ = [
    "SPLITTER_VERSION",
    "SPLITTER_SHA256",
    "TOKENIZER_VERSION",
    "ABBREVIATIONS",
    "WORD_PATTERN",
    "split_into_sentences",
    "split_into_paragraphs",
    "count_words",
    "word_tokens",
    "sentence_word_lengths",
]

# Bumped when the segmentation *logic* changes. The prior value was
# "v3.0.0-academic", owned by 06_TOOLS/analysis/core/text_parser.py.
SPLITTER_VERSION = "v3.1.0-shared-academic"

# Bumped when the tokenizer changes. Prior behaviour was inconsistent across
# three sites (see the module docstring); this records the unified contract.
TOKENIZER_VERSION = "v3.1.0-unicode-word"

# Abbreviations protected during sentence splitting. Previously duplicated as
# ABBREVIATIONS in 06_TOOLS/analysis/core/text_parser.py.
ABBREVIATIONS = (
    "fig", "figs", "al", "dr", "prof", "eq", "eqs", "ref", "refs",
    "vs", "cf", "etc", "vol", "no", "pp", "approx",
    "sec", "ch", "ca", "univ", "dept", "ed", "eds",
)

_DOT_SENTINEL = "@@DOT@@"

# One token unit for every length-derived statistic.
#
# A word is a run of word characters, optionally joined by internal apostrophes or
# hyphens ("don't", "state-of-the-art", "J_c" are each one token). Unicode-aware:
# the previous calibration pattern was ASCII-only, so an accented token such as
# "naive" (or "café") matched *nothing at all* and silently vanished from every
# word count. For pure-ASCII text this pattern reproduces the old calibration
# behaviour exactly, so unifying the contract does not by itself move any number.
WORD_PATTERN = re.compile(r"\b\w+(?:['’\-]\w+)*\b", re.UNICODE)

_PARAGRAPH_SPLIT = "\n\n"


def split_into_sentences(text: str) -> List[str]:
    """Split ``text`` into sentences, protecting academic abbreviations.

    Handles decimals (3.1415), author initials (J. R. Smith), multi-dot Latin
    abbreviations (i.e., e.g.), "et al.", the ABBREVIATIONS table, and numbered
    list markers. Extracted verbatim from the calibration splitter so that the
    audit engine stops disagreeing with it.
    """
    clean_text = re.sub(r"[ \t]+", " ", text.strip())
    if not clean_text:
        return []

    protected = clean_text

    # Decimals like 3.1415 or 1990.5
    protected = re.sub(r"(?<=\d)\.(?=\d)", _DOT_SENTINEL, protected)

    # Multi-dot Latin abbreviations (e.g. i.e.)
    protected = re.sub(r"\b([eE])\.([gG])\.",
                       lambda m: f"{m.group(1)}{_DOT_SENTINEL}{m.group(2)}{_DOT_SENTINEL}", protected)
    protected = re.sub(r"\b([iI])\.([eE])\.",
                       lambda m: f"{m.group(1)}{_DOT_SENTINEL}{m.group(2)}{_DOT_SENTINEL}", protected)
    protected = re.sub(r"\b([eE])\.([gG])\b",
                       lambda m: f"{m.group(1)}{_DOT_SENTINEL}{m.group(2)}", protected)
    protected = re.sub(r"\b([iI])\.([eE])\b",
                       lambda m: f"{m.group(1)}{_DOT_SENTINEL}{m.group(2)}", protected)

    # "et al."
    protected = re.sub(r"\b([eE]t\s+al)\.", lambda m: f"{m.group(1)}{_DOT_SENTINEL}", protected)

    # Author initials e.g. J. R. Smith or A. B. Johnson (excluding units after
    # digits e.g. 4.2 K.)
    protected = re.sub(r"(?<!\d\s)\b([A-Z])\.(?=\s+[A-Z]\b)", rf"\1{_DOT_SENTINEL}", protected)
    protected = re.sub(r"(?<!\d\s)\b([A-Z])\.(?=\s+[A-Z][a-z])", rf"\1{_DOT_SENTINEL}", protected)

    # Standard single-word abbreviations, case-insensitively.
    for abbr in ABBREVIATIONS:
        protected = re.compile(rf"\b{abbr}\.", re.IGNORECASE).sub(
            lambda m: m.group(0)[:-1] + _DOT_SENTINEL, protected)

    # Numbered list markers at start of text or after punctuation, e.g. "1. "
    protected = re.sub(r"(?:^|(?<=[.!?]\s))(\d+)\.(?=\s+[A-Z])", rf"\1{_DOT_SENTINEL}", protected)

    raw_sents = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'‘“])", protected)

    sentences: List[str] = []
    for s in raw_sents:
        restored = s.replace(_DOT_SENTINEL, ".").strip()
        if not restored:
            continue
        # Keep any fragment carrying at least one letter; drop pure debris.
        if len(word_tokens(restored)) >= 2 or re.search(r"[a-zA-Z]", restored):
            sentences.append(restored)
    return sentences


def split_into_paragraphs(text: str) -> List[str]:
    """Split ``text`` into non-empty paragraphs on a blank line.

    Deliberately preserves the pre-existing ``text.split("\\n\\n")`` semantics
    exactly. Paragraph segmentation was NOT one of the inconsistencies this
    refactor set out to fix, so tightening it here would silently move gate
    results without a measurement behind it.
    """
    return [p.strip() for p in text.split(_PARAGRAPH_SPLIT) if p.strip()]


def word_tokens(text: str) -> List[str]:
    """Return the word tokens of ``text`` under :data:`WORD_PATTERN`."""
    return WORD_PATTERN.findall(text)


def count_words(text: str) -> int:
    """Total word count. The single permitted way to size a document or window."""
    return len(WORD_PATTERN.findall(text))


def sentence_word_lengths(sentences: List[str]) -> List[int]:
    """Per-sentence word counts under the same tokenizer as :func:`count_words`."""
    return [len(WORD_PATTERN.findall(s)) for s in sentences]


def _sha256_of_logic() -> str:
    """Hash of the segmentation logic itself, so any edit changes the fingerprint."""
    try:
        src = inspect.getsource(split_into_sentences)
    except (OSError, TypeError):  # pragma: no cover - source unavailable
        src = SPLITTER_VERSION
    return hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]


SPLITTER_SHA256 = _sha256_of_logic()
"""Shared text segmentation primitives for Project Arkais.

Import from here rather than from :mod:`arkais.text.segmentation` directly so the
contract has one stable public surface.
"""

from .segmentation import (
    ABBREVIATIONS,
    SPLITTER_SHA256,
    SPLITTER_VERSION,
    TOKENIZER_VERSION,
    WORD_PATTERN,
    count_words,
    sentence_word_lengths,
    split_into_paragraphs,
    split_into_sentences,
    word_tokens,
)

__all__ = [
    "ABBREVIATIONS",
    "SPLITTER_SHA256",
    "SPLITTER_VERSION",
    "TOKENIZER_VERSION",
    "WORD_PATTERN",
    "count_words",
    "sentence_word_lengths",
    "split_into_paragraphs",
    "split_into_sentences",
    "word_tokens",
]
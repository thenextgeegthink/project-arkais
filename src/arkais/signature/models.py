"""Signature profile models and representations for Project Arkais."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class SignatureMetrics:
    sentence_length_mean: float = 21.46
    sentence_length_std: float = 16.55
    nominalization_density_min: float = 4.6
    nominalization_density_max: float = 9.0
    epistemic_ratio_min: float = 1.32
    citation_density_min: float = 2.0


@dataclass
class SignatureProfile:
    identifier: str
    version: str
    status: str
    corpus_size: str
    calibration_date: str
    description: str
    raw_markdown: str
    metrics: SignatureMetrics = field(default_factory=SignatureMetrics)

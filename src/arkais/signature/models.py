"""Signature profile models and representations for Project Arkais."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class SignatureMetrics:
    sentence_length_mean: float = 21.1
    sentence_length_std: float = 19.7
    nominalization_density_min: float = 4.2
    nominalization_density_max: float = 8.5
    epistemic_ratio_min: float = 1.4
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

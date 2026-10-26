"""Signature specification and catalog module for Project Arkais."""

from .models import SignatureProfile, SignatureMetrics
from .loader import SignatureManager
from .compiler import SignatureCompiler, CompiledSignature, CompileRequest, CompilationManifest, CompilationResult
from .promoter import (
    PromotionError,
    PromotionValidationError,
    PromotionReport,
    validate_candidate_catalog,
    promote_candidate_to_active,
)

__all__ = [
    "SignatureProfile",
    "SignatureMetrics",
    "SignatureManager",
    "SignatureCompiler",
    "CompiledSignature",
    "CompileRequest",
    "CompilationManifest",
    "CompilationResult",
    "PromotionError",
    "PromotionValidationError",
    "PromotionReport",
    "validate_candidate_catalog",
    "promote_candidate_to_active",
]

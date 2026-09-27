"""Project Arkais Client SDK (`project-arkais`).

Deterministic academic prose signature engine and stylometric audit suite.
"""

from .client import ArkaisClient
from .config import ArkaisConfig
from .signature import SignatureProfile, SignatureManager, SignatureMetrics
from .audit import StylometricAuditEngine, AuditReport, GateResult
from .security import ByokKeyManager, RedactedSecret, CredentialSecurityError
from .reference import ReferenceResolver, ReferenceCache, ReferenceItem, ResolutionResult
from .citation import CitationFormatter, RhetoricalWeaver, CitationStyle, RhetoricalRole, FormattedCitation

from .__version__ import __version__, SCHEMA_VERSION, CORPUS_FORMAT, STUDIO_COMPATIBILITY

__all__ = [
    "ArkaisClient",
    "ArkaisConfig",
    "SignatureProfile",
    "SignatureManager",
    "SignatureMetrics",
    "StylometricAuditEngine",
    "AuditReport",
    "GateResult",
    "ByokKeyManager",
    "RedactedSecret",
    "CredentialSecurityError",
    "ReferenceResolver",
    "ReferenceCache",
    "ReferenceItem",
    "ResolutionResult",
    "CitationFormatter",
    "RhetoricalWeaver",
    "CitationStyle",
    "RhetoricalRole",
    "FormattedCitation",
]

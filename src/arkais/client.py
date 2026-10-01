"""Top-level client entrypoint for Project Arkais Python SDK."""

from pathlib import Path
from typing import Optional, Union, Dict, Any, List

from .config import ArkaisConfig
from .security import ByokKeyManager, RedactedSecret
from .signature import SignatureManager, SignatureProfile
from .audit import StylometricAuditEngine, AuditReport
from .reference import ReferenceResolver, ReferenceCache, ReferenceItem, ResolutionResult
from .citation import CitationFormatter, RhetoricalWeaver, CitationStyle, RhetoricalRole


class ArkaisClient:
    """The central interface for Project Arkais programmatic operations.
    
    Provides:
    - Zero-telemetry BYOK credential discovery and management.
    - Calibrated academic signatures inspection and loading.
    - 10-gate deterministic stylometric prose auditing.
    - Zero-key polite-pool scholarly reference resolution and caching.
    - Multi-style academic citation formatting and rhetorical prose weaving.
    """

    def __init__(self, config: Optional[ArkaisConfig] = None, **kwargs):
        self.config = config or ArkaisConfig(**kwargs)

        # 1. Initialize Security Sandbox & BYOK Manager
        self.security = ByokKeyManager(
            project_root=self.config.project_root
        )

        # 2. Initialize Signature Catalog Manager
        self.signatures = SignatureManager(
            custom_dir=self.config.custom_signature_dir
        )

        # 3. Initialize Stylometric Audit Engine
        self.audit = StylometricAuditEngine()

        # 4. Initialize Reference Cache & Resolver
        cache_path = self.config.references_cache_file or (self.config.project_root / "05_ASSETS" / "references_cache.json")
        self.reference_cache = ReferenceCache(cache_file=cache_path)
        self.references = ReferenceResolver(
            cache=self.reference_cache,
            contact_email=self.config.contact_email
        )

        # 5. Initialize Citation Formatter & Rhetorical Weaver
        self.citations = CitationFormatter()
        self.weaver = RhetoricalWeaver()

    @property
    def active_signature(self) -> SignatureProfile:
        """Returns currently configured default signature profile."""
        return self.signatures.get(self.config.default_signature)

    def get_provider_key(self, provider: Optional[str] = None) -> Optional[RedactedSecret]:
        """Retrieves credential for requested or configured provider via multi-tier BYOK."""
        prov = provider or self.config.provider
        return self.security.get_key(prov, explicit_key=self.config.explicit_api_key)

    def evaluate_draft(self, manuscript_text: str) -> AuditReport:
        """Convenience method to evaluate prose against the 10 stylometric gates."""
        return self.audit.evaluate(manuscript_text)

    def resolve_doi(self, doi: str) -> Optional[ReferenceItem]:
        """Resolves metadata for a DOI via polite pool or local cache."""
        return self.references.resolve_doi(doi)

    def verify_citation(self, title: str, author: Optional[str] = None, proposed_doi: Optional[str] = None) -> ResolutionResult:
        """Verifies if an academic citation corresponds to an authentic registered work."""
        return self.references.verify_citation(title=title, author=author, proposed_doi=proposed_doi)

    def format_citation(self, item: ReferenceItem, style: CitationStyle = CitationStyle.APA_7TH, index: Optional[int] = None) -> str:
        """Convenience method to format in-text citation."""
        return self.citations.format_in_text(item, style=style, index=index)

    def format_bibliography(self, items: List[ReferenceItem], style: CitationStyle = CitationStyle.APA_7TH) -> List[str]:
        """Convenience method to format a sorted bibliography."""
        return self.citations.format_bibliography(items, style=style)

    def weave_citation(
        self,
        item: ReferenceItem,
        role: RhetoricalRole = RhetoricalRole.INTEGRAL_SUBJECT,
        verb: str = "demonstrated",
        claim_context: str = ""
    ) -> str:
        """Weaves a reference into authentic academic syntax avoiding AI parenthetical slop."""
        return self.weaver.weave(item, role=role, verb=verb, claim_context=claim_context)

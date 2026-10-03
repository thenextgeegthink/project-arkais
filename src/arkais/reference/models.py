"""Reference models and data representations for Project Arkais."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ReferenceItem:
    """Canonical representation of an academic work."""
    doi: str
    title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    citation_count: Optional[int] = None
    url: Optional[str] = None
    source_registry: str = "local"
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def journal(self) -> Optional[str]:
        """Convenience alias for venue."""
        return self.venue

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doi": self.doi,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "citation_count": self.citation_count,
            "url": self.url,
            "source_registry": self.source_registry
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReferenceItem":
        return cls(
            doi=data.get("doi", ""),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            year=data.get("year"),
            venue=data.get("venue"),
            volume=data.get("volume"),
            issue=data.get("issue"),
            pages=data.get("pages"),
            citation_count=data.get("citation_count"),
            url=data.get("url"),
            source_registry=data.get("source_registry", "local"),
            raw_metadata=data.get("raw_metadata", {})
        )


@dataclass
class ResolutionResult:
    """Result of attempting to resolve and verify an academic reference."""
    verified: bool
    confidence: float
    canonical_doi: Optional[str] = None
    matched_item: Optional[ReferenceItem] = None
    status_code: str = "VERIFIED"  # VERIFIED | UNVERIFIED_PHANTOM | PARTIAL_MATCH
    message: str = ""

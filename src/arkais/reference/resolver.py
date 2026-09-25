"""Scholarly Reference Resolver using OpenAlex and CrossRef Polite Pools."""

import re
import json
import urllib.request
import urllib.parse
import urllib.error
from difflib import SequenceMatcher
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from .models import ReferenceItem, ResolutionResult
from .cache import ReferenceCache, normalize_doi, normalize_title

POLITE_USER_AGENT = "Arkais/1.0 (mailto:engineering@geegthink.com; +https://geegthink.com/project-arkais)"
CROSSREF_BASE = "https://api.crossref.org/works"
OPENALEX_BASE = "https://api.openalex.org/works"

ALLOWED_DOMAINS = ["api.crossref.org", "api.openalex.org"]


def _calculate_similarity(a: str, b: str) -> float:
    """Calculates Levenshtein-like string similarity between 0.0 and 1.0."""
    norm_a = normalize_title(a)
    norm_b = normalize_title(b)
    if not norm_a or not norm_b:
        return 0.0
    return SequenceMatcher(None, norm_a, norm_b).ratio()


class ReferenceResolver:
    """Zero-key, polite-pool scholarly reference resolver with local caching."""

    def __init__(self, cache: Optional[ReferenceCache] = None, contact_email: str = "engineering@geegthink.com"):
        self.cache = cache or ReferenceCache()
        self.contact_email = contact_email
        self.headers = {
            "User-Agent": f"Arkais/1.0 (mailto:{self.contact_email}; +https://geegthink.com/project-arkais)",
            "Accept": "application/json"
        }

    def resolve_doi(self, doi: str) -> Optional[ReferenceItem]:
        """Resolves metadata for a specific DOI, consulting local cache first."""
        norm = normalize_doi(doi)
        if not norm:
            return None

        # 1. Check Cache
        cached = self.cache.get_by_doi(norm)
        if cached:
            return cached

        # 2. Query CrossRef
        item = self._fetch_crossref_doi(norm)
        if not item:
            # 3. Fallback to OpenAlex
            item = self._fetch_openalex_doi(norm)

        if item:
            self.cache.put(item)
            return item

        return None

    def verify_citation(
        self,
        title: str,
        author: Optional[str] = None,
        year: Optional[int] = None,
        proposed_doi: Optional[str] = None
    ) -> ResolutionResult:
        """Verifies whether an academic citation corresponds to a real published work."""
        # 1. If DOI is proposed, verify DOI directly
        if proposed_doi:
            item = self.resolve_doi(proposed_doi)
            if item:
                sim = _calculate_similarity(title, item.title)
                if sim >= 0.75:
                    return ResolutionResult(
                        verified=True,
                        confidence=round(sim, 3),
                        canonical_doi=item.doi,
                        matched_item=item,
                        status_code="VERIFIED",
                        message=f"Verified against registered DOI: {item.doi}"
                    )
                else:
                    return ResolutionResult(
                        verified=False,
                        confidence=round(sim, 3),
                        canonical_doi=item.doi,
                        matched_item=item,
                        status_code="PARTIAL_MATCH",
                        message=f"Proposed DOI exists, but title differs ('{item.title}' vs '{title}')"
                    )

        # 2. Check title in local cache
        cached_item = self.cache.get_by_title(title)
        if cached_item:
            return ResolutionResult(
                verified=True,
                confidence=1.0,
                canonical_doi=cached_item.doi,
                matched_item=cached_item,
                status_code="VERIFIED",
                message="Verified from local project reference cache."
            )

        # 3. Search CrossRef Polite Pool
        search_query = f"{title} {author or ''}".strip()
        candidates = self.search_works(search_query, limit=3)

        best_match: Optional[ReferenceItem] = None
        best_sim = 0.0

        for candidate in candidates:
            sim = _calculate_similarity(title, candidate.title)
            if sim > best_sim:
                best_sim = sim
                best_match = candidate

        if best_match and best_sim >= 0.80:
            self.cache.put(best_match)
            return ResolutionResult(
                verified=True,
                confidence=round(best_sim, 3),
                canonical_doi=best_match.doi,
                matched_item=best_match,
                status_code="VERIFIED",
                message=f"Verified through CrossRef search (Title Match: {best_sim*100:.1f}%)"
            )

        return ResolutionResult(
            verified=False,
            confidence=round(best_sim, 3),
            canonical_doi=None,
            matched_item=None,
            status_code="UNVERIFIED_PHANTOM",
            message=f"REF-001: Unverified Citation Phantom. No matching scholarly record found (best match: {best_sim*100:.1f}%)."
        )

    def search_works(self, query: str, limit: int = 5) -> List[ReferenceItem]:
        """Searches CrossRef for scholarly works matching free-text query."""
        encoded_query = urllib.parse.quote_plus(query)
        url = f"{CROSSREF_BASE}?query={encoded_query}&rows={limit}&select=DOI,title,author,published,container-title,volume,issue,page,is-referenced-by-count,URL"
        
        data = self._http_get(url)
        if not data or "message" not in data or "items" not in data["message"]:
            return []

        results = []
        for raw in data["message"]["items"]:
            item = self._parse_crossref_item(raw)
            if item:
                results.append(item)
        return results

    def _fetch_crossref_doi(self, doi: str) -> Optional[ReferenceItem]:
        encoded_doi = urllib.parse.quote(doi)
        url = f"{CROSSREF_BASE}/{encoded_doi}"
        data = self._http_get(url)
        if data and "message" in data:
            return self._parse_crossref_item(data["message"])
        return None

    def _fetch_openalex_doi(self, doi: str) -> Optional[ReferenceItem]:
        url = f"{OPENALEX_BASE}/doi:{urllib.parse.quote(doi)}"
        data = self._http_get(url)
        if data and "id" in data:
            return self._parse_openalex_item(data)
        return None

    def _http_get(self, url: str) -> Optional[Dict[str, Any]]:
        # Security domain check
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.netloc not in ALLOWED_DOMAINS:
            raise ValueError(f"Security violation: Unauthorized outbound endpoint {url}")

        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            return None

    def _parse_crossref_item(self, raw: Dict[str, Any]) -> Optional[ReferenceItem]:
        doi = raw.get("DOI")
        if not doi:
            return None

        # Title
        titles = raw.get("title", [])
        title = titles[0] if isinstance(titles, list) and titles else str(titles)

        # Authors
        authors = []
        for a in raw.get("author", []):
            family = a.get("family", "")
            given = a.get("given", "")
            if family and given:
                authors.append(f"{family}, {given}")
            elif family:
                authors.append(family)

        # Year
        year = None
        date_parts = raw.get("published", {}).get("date-parts", []) or raw.get("created", {}).get("date-parts", [])
        if date_parts and isinstance(date_parts[0], list) and date_parts[0]:
            year = date_parts[0][0]

        # Venue
        venues = raw.get("container-title", [])
        venue = venues[0] if isinstance(venues, list) and venues else str(venues)

        return ReferenceItem(
            doi=normalize_doi(doi),
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            volume=raw.get("volume"),
            issue=raw.get("issue"),
            pages=raw.get("page"),
            citation_count=raw.get("is-referenced-by-count"),
            url=raw.get("URL", f"https://doi.org/{doi}"),
            source_registry="crossref",
            raw_metadata=raw
        )

    def _parse_openalex_item(self, raw: Dict[str, Any]) -> Optional[ReferenceItem]:
        doi = raw.get("doi")
        if not doi:
            return None

        title = raw.get("title") or ""
        authors = [a.get("author", {}).get("display_name", "") for a in raw.get("authorships", [])]
        year = raw.get("publication_year")
        venue = raw.get("primary_location", {}).get("source", {}).get("display_name")

        return ReferenceItem(
            doi=normalize_doi(doi),
            title=title,
            authors=[a for a in authors if a],
            year=year,
            venue=venue,
            citation_count=raw.get("cited_by_count"),
            url=doi,
            source_registry="openalex",
            raw_metadata=raw
        )

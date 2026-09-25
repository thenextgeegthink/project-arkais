"""Reference resolution and local caching module for Project Arkais."""

from .models import ReferenceItem, ResolutionResult
from .cache import ReferenceCache, normalize_doi, normalize_title
from .resolver import ReferenceResolver

__all__ = [
    "ReferenceItem",
    "ResolutionResult",
    "ReferenceCache",
    "normalize_doi",
    "normalize_title",
    "ReferenceResolver",
]

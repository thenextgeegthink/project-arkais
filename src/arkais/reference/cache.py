"""Persistent local reference cache for Project Arkais."""

import json
import re
from pathlib import Path
from typing import Dict, Optional, List, Any
from .models import ReferenceItem


def normalize_doi(doi: str) -> str:
    """Normalizes DOI strings to canonical lowercase format without URL prefixes."""
    clean = doi.strip().lower()
    clean = re.sub(r"^https?://(dx\.)?doi\.org/", "", clean)
    return clean.strip()


def normalize_title(title: str) -> str:
    """Normalizes titles for fuzzy lookup by stripping punctuation and whitespace."""
    return re.sub(r"[^a-z0-9]", "", title.lower())


class ReferenceCache:
    """Zero-telemetry local reference storage and cache."""

    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file or (Path.cwd() / "05_ASSETS" / "references_cache.json")
        self._by_doi: Dict[str, ReferenceItem] = {}
        self._by_title_key: Dict[str, ReferenceItem] = {}
        self._load()

    def get_by_doi(self, doi: str) -> Optional[ReferenceItem]:
        norm = normalize_doi(doi)
        return self._by_doi.get(norm)

    def get_by_title(self, title: str) -> Optional[ReferenceItem]:
        key = normalize_title(title)
        if not key:
            return None
        return self._by_title_key.get(key)

    def put(self, item: ReferenceItem, persist: bool = True):
        norm_doi = normalize_doi(item.doi)
        title_key = normalize_title(item.title)

        self._by_doi[norm_doi] = item
        if title_key:
            self._by_title_key[title_key] = item

        if persist:
            self.save()

    def count(self) -> int:
        return len(self._by_doi)

    def all(self) -> List[ReferenceItem]:
        return list(self._by_doi.values())

    def save(self):
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {doi: item.to_dict() for doi, item in self._by_doi.items()}
        temp_file = self.cache_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp_file.replace(self.cache_file)

    def _load(self):
        if not self.cache_file.exists():
            return
        try:
            data = json.loads(self.cache_file.read_text(encoding="utf-8"))
            for doi, raw in data.items():
                item = ReferenceItem.from_dict(raw)
                norm_doi = normalize_doi(item.doi)
                title_key = normalize_title(item.title)
                self._by_doi[norm_doi] = item
                if title_key:
                    self._by_title_key[title_key] = item
        except Exception:
            # Fall back gracefully if corrupted
            pass

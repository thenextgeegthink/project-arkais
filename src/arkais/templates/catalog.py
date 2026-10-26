"""Local-first offline seed catalog and cache manager for Project Arkais templates.

Provides local-first retrieval, per-project freezing, and GitHub CDN sync with ETag caching.
"""

from __future__ import annotations

import json
import os
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from arkais.templates.models import (
    AssetCategory,
    Discipline,
    EngineType,
    TemplateEnvelope,
)
from arkais.templates.validator import (
    TemplateValidationError,
    validate_template_dict,
    validate_template_file,
)

DEFAULT_REGISTRY_URL = "https://raw.githubusercontent.com/thenextgeegthink/project-arkais/main/templates"


class TemplateNotFoundError(KeyError):
    """Raised when a requested template ID is not found in the catalog."""
    def __init__(self, template_id: str):
        super().__init__(f"Template '{template_id}' was not found in the Arkais catalog.")
        self.template_id = template_id


@dataclass
class SyncResult:
    """Outcome report from synchronizing with remote registry."""
    synced: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    manifest_version: Optional[str] = None
    cached_manifest: bool = False
    errors: List[str] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        return self.failed == 0 and len(self.errors) == 0


class TemplateCatalog:
    """Catalog managing bundled offline templates and cached remote drops."""

    def __init__(
        self,
        cache_dir: Optional[Union[str, Path]] = None,
        bundled_dir: Optional[Union[str, Path]] = None,
        remote_url: Optional[str] = None,
    ):
        if cache_dir is not None:
            self.cache_dir = Path(cache_dir).expanduser().resolve()
        else:
            env_cache = os.environ.get("ARKAIS_TEMPLATE_CACHE_DIR")
            self.cache_dir = Path(env_cache).expanduser().resolve() if env_cache else Path.home() / ".cache" / "arkais" / "templates"

        if bundled_dir is not None:
            self.bundled_dir = Path(bundled_dir).resolve()
        else:
            self.bundled_dir = Path(__file__).parent / "bundled"

        self.remote_url = (remote_url or os.environ.get("ARKAIS_TEMPLATE_REGISTRY_URL") or DEFAULT_REGISTRY_URL).rstrip("/")

        self._templates: Dict[str, TemplateEnvelope] = {}
        self._sources: Dict[str, Path] = {}
        self._is_loaded: bool = False

    def _ensure_loaded(self) -> None:
        """Lazily load catalog on first access."""
        if not self._is_loaded:
            self.reload()

    def reload(self) -> None:
        """Scan bundled and cached directories to reconstruct template index."""
        self._templates.clear()
        self._sources.clear()

        # 1. Load bundled templates (built-in offline baseline)
        if self.bundled_dir.is_dir():
            for p in self.bundled_dir.rglob("*.json"):
                if p.name in ("registry.json", "manifest.json"):
                    continue
                try:
                    envelope = validate_template_file(p)
                    self._templates[envelope.id] = envelope
                    self._sources[envelope.id] = p
                except (TemplateValidationError, Exception):
                    # Skip non-template JSON files silently
                    continue

        # 2. Overlay cached templates (from local cache or downloaded drops)
        if self.cache_dir.is_dir():
            for p in self.cache_dir.rglob("*.json"):
                if p.name in ("registry.json", "manifest.json"):
                    continue
                try:
                    envelope = validate_template_file(p)
                    # Cache overrides bundled if present
                    self._templates[envelope.id] = envelope
                    self._sources[envelope.id] = p
                except (TemplateValidationError, Exception):
                    continue

        self._is_loaded = True

    def get(self, template_id: str) -> TemplateEnvelope:
        """Retrieve a template envelope by its canonical ID.

        Raises:
            TemplateNotFoundError: If the ID does not exist in the catalog.
        """
        self._ensure_loaded()
        if template_id not in self._templates:
            raise TemplateNotFoundError(template_id)
        return self._templates[template_id]

    def get_or_none(self, template_id: str) -> Optional[TemplateEnvelope]:
        """Retrieve a template envelope or return None if not present."""
        self._ensure_loaded()
        return self._templates.get(template_id)

    def contains(self, template_id: str) -> bool:
        """Check if a template exists in the catalog."""
        self._ensure_loaded()
        return template_id in self._templates

    def list(
        self,
        category: Optional[Union[str, AssetCategory]] = None,
        discipline: Optional[Union[str, Discipline]] = None,
        engine: Optional[Union[str, EngineType]] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[TemplateEnvelope]:
        """Search and filter templates within the catalog."""
        self._ensure_loaded()
        results: List[TemplateEnvelope] = []

        cat_val = category.value if isinstance(category, AssetCategory) else category
        disc_val = discipline.value if isinstance(discipline, Discipline) else discipline
        eng_val = engine.value if isinstance(engine, EngineType) else engine
        tag_val = tag.lower() if tag else None
        search_val = search.lower() if search else None

        for item in self._templates.values():
            if cat_val and item.category.value != cat_val:
                continue
            if disc_val and item.discipline.value != disc_val:
                continue
            if eng_val and item.engine.value != eng_val:
                continue
            if tag_val and not any(tag_val in t.lower() for t in item.tags):
                continue
            if search_val:
                aliases_map = {
                    "computer_science": "tech technology computing ai ml software code algorithm",
                    "engineering": "tech technology hardware systems controls mechanical electrical",
                    "physics": "physical science materials energy kinetics thermodynamics",
                    "medicine": "medical clinical health pharma biology bio genomics trial patient",
                    "economics": "econ finance econometrics policy social business market",
                }
                disc_aliases = aliases_map.get(item.discipline.value, "")
                searchable_text = f"{item.id} {item.name} {item.discipline.value} {disc_aliases} {item.category.value} {item.description or ''} {' '.join(item.tags)}".lower()
                query_tokens = search_val.split()
                if not any(token in searchable_text for token in query_tokens):
                    continue
            results.append(item)

        results.sort(key=lambda x: x.id)
        return results

    def count(self) -> int:
        """Total number of indexed templates."""
        self._ensure_loaded()
        return len(self._templates)

    def stats(self) -> Dict[str, Any]:
        """Aggregate breakdown of the catalog."""
        self._ensure_loaded()
        by_category: Dict[str, int] = {}
        by_discipline: Dict[str, int] = {}
        by_engine: Dict[str, int] = {}

        bundled_count = 0
        cached_count = 0

        for t_id, item in self._templates.items():
            by_category[item.category.value] = by_category.get(item.category.value, 0) + 1
            by_discipline[item.discipline.value] = by_discipline.get(item.discipline.value, 0) + 1
            by_engine[item.engine.value] = by_engine.get(item.engine.value, 0) + 1

            source_path = self._sources.get(t_id)
            if source_path and self.cache_dir in source_path.parents:
                cached_count += 1
            else:
                bundled_count += 1

        return {
            "total": len(self._templates),
            "bundled": bundled_count,
            "cached": cached_count,
            "by_category": by_category,
            "by_discipline": by_discipline,
            "by_engine": by_engine,
        }

    def embed_in_project(self, template_id: str, project_dir: Union[str, Path] = ".") -> Path:
        """Embed a frozen copy of the template into the paper's project directory.

        Saves to: <project_dir>/assets/templates/<template_id>.json

        Returns:
            The destination Path of the frozen spec.
        """
        envelope = self.get(template_id)
        proj_path = Path(project_dir).resolve()
        dest_dir = proj_path / "assets" / "templates"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / f"{template_id}.json"

        dest_file.write_text(envelope.to_json(indent=2), encoding="utf-8")
        return dest_file

    def sync(
        self,
        remote_base_url: Optional[str] = None,
        timeout: float = 6.0,
        force: bool = False,
    ) -> SyncResult:
        """Synchronize the local cache with the public GitHub repository catalog.

        Employs HTTP ETag headers to minimize data transfer. Never overwrites with corrupted data.
        Gracefully handles offline environments.
        """
        base_url = (remote_base_url or self.remote_url).rstrip("/")
        registry_url = f"{base_url}/registry.json"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        etag_file = self.cache_dir / ".registry_etag"
        manifest_file = self.cache_dir / "registry.json"
        saved_etag = etag_file.read_text(encoding="utf-8").strip() if etag_file.is_file() else None

        req = urllib.request.Request(
            registry_url,
            headers={
                "User-Agent": "Arkais-SDK/2.0.0 (Local-First Template Engine)",
                "Accept": "application/json",
            }
        )
        if saved_etag and not force:
            req.add_header("If-None-Match", saved_etag)

        result = SyncResult()

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                new_etag = resp.headers.get("ETag")
                raw_bytes = resp.read()
                manifest_data = json.loads(raw_bytes.decode("utf-8"))

                # Save new manifest and ETag
                manifest_file.write_bytes(raw_bytes)
                if new_etag:
                    etag_file.write_text(new_etag.strip(), encoding="utf-8")

                result.manifest_version = manifest_data.get("manifest_version", "unknown")

        except urllib.error.HTTPError as e:
            if e.code == 304:  # Not Modified
                result.cached_manifest = True
                if manifest_file.is_file():
                    try:
                        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                        result.manifest_version = manifest_data.get("manifest_version", "cached")
                    except Exception:
                        manifest_data = {"templates": []}
                else:
                    manifest_data = {"templates": []}
            else:
                result.errors.append(f"HTTP {e.code} while fetching registry manifest: {e.reason}")
                return result
        except Exception as e:
            result.errors.append(f"Network error syncing template registry: {str(e)}")
            return result

        # Process each remote template entry
        templates = manifest_data.get("templates", [])
        for entry in templates:
            t_id = entry.get("id")
            rel_path = entry.get("relative_path")
            if not t_id or not rel_path:
                continue

            target_file = self.cache_dir / rel_path
            # Check if already present and up-to-date
            if target_file.is_file() and not force:
                existing = self._templates.get(t_id)
                if existing and existing.version == entry.get("version"):
                    result.skipped += 1
                    continue

            # Fetch individual template spec
            template_item_url = f"{base_url}/{rel_path}"
            item_req = urllib.request.Request(
                template_item_url,
                headers={"User-Agent": "Arkais-SDK/2.0.0"}
            )
            try:
                with urllib.request.urlopen(item_req, timeout=timeout) as item_resp:
                    item_bytes = item_resp.read()
                    # Validate content before writing to disk
                    item_dict = json.loads(item_bytes.decode("utf-8"))
                    validate_template_dict(item_dict)

                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    target_file.write_bytes(item_bytes)

                    if t_id in self._templates:
                        result.updated += 1
                    else:
                        result.synced += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(f"Failed to download template '{t_id}': {str(e)}")

        # Reload the catalog index
        self.reload()
        return result

    def clear_cache(self) -> int:
        """Clear local downloaded templates from cache_dir, preserving bundled templates."""
        if not self.cache_dir.exists():
            return 0
        count = 0
        for p in list(self.cache_dir.glob("*")):
            if p.is_file():
                p.unlink()
                count += 1
            elif p.is_dir():
                shutil.rmtree(p)
                count += 1
        self.reload()
        return count


_DEFAULT_CATALOG: Optional[TemplateCatalog] = None


def get_default_catalog() -> TemplateCatalog:
    """Get or instantiate the default singleton TemplateCatalog."""
    global _DEFAULT_CATALOG
    if _DEFAULT_CATALOG is None:
        _DEFAULT_CATALOG = TemplateCatalog()
    return _DEFAULT_CATALOG

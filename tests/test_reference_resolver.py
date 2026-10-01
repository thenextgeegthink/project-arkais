"""Unit tests for ReferenceResolver and ReferenceCache (THE-21)."""

import pytest
import json
from pathlib import Path
import sys

# Ensure SDK src is in path for tests
SDK_SRC = Path(__file__).resolve().parent.parent / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from arkais import (
    ArkaisClient,
    ReferenceItem,
    ResolutionResult,
    ReferenceCache,
    ReferenceResolver
)
from arkais.reference.cache import normalize_doi, normalize_title


@pytest.fixture
def temp_cache_dir(tmp_path):
    cache_file = tmp_path / "references_cache.json"
    return cache_file


def test_doi_and_title_normalization():
    assert normalize_doi("https://doi.org/10.1016/j.joule.2018.05.006") == "10.1016/j.joule.2018.05.006"
    assert normalize_doi("http://dx.doi.org/10.1016/j.joule.2018.05.006 ") == "10.1016/j.joule.2018.05.006"
    assert normalize_doi("10.1016/J.JOULE.2018.05.006") == "10.1016/j.joule.2018.05.006"

    assert normalize_title("A Process for Capturing CO2 from Atmosphere!") == "aprocessforcapturingco2fromatmosphere"


def test_cache_storage_and_reload(temp_cache_dir):
    cache = ReferenceCache(cache_file=temp_cache_dir)
    assert cache.count() == 0

    item = ReferenceItem(
        doi="10.1016/j.joule.2018.05.006",
        title="A Process for Capturing CO2 from the Atmosphere",
        authors=["Keith, David W.", "Holmes, Geoffrey"],
        year=2018,
        venue="Joule"
    )

    cache.put(item)
    assert cache.count() == 1
    assert temp_cache_dir.exists()

    # Query from same instance
    assert cache.get_by_doi("10.1016/j.joule.2018.05.006") is not None
    assert cache.get_by_title("A Process for Capturing CO2 from the Atmosphere") is not None

    # Reload into new instance from disk
    new_cache = ReferenceCache(cache_file=temp_cache_dir)
    assert new_cache.count() == 1
    loaded = new_cache.get_by_doi("https://doi.org/10.1016/J.JOULE.2018.05.006")
    assert loaded is not None
    assert loaded.title == "A Process for Capturing CO2 from the Atmosphere"
    assert loaded.authors == ["Keith, David W.", "Holmes, Geoffrey"]


def test_cached_resolution(temp_cache_dir):
    cache = ReferenceCache(cache_file=temp_cache_dir)
    resolver = ReferenceResolver(cache=cache)

    item = ReferenceItem(
        doi="10.1038/s41558-019-0438-6",
        title="Evaluating the direct air capture of carbon dioxide",
        authors=["Lackner, Klaus S."],
        year=2019,
        venue="Nature Climate Change"
    )
    cache.put(item)

    # Resolving known DOI hits cache
    resolved = resolver.resolve_doi("10.1038/s41558-019-0438-6")
    assert resolved is not None
    assert resolved.title == "Evaluating the direct air capture of carbon dioxide"

    # Verifying known citation hits cache
    res = resolver.verify_citation(title="Evaluating the direct air capture of carbon dioxide")
    assert res.verified is True
    assert res.status_code == "VERIFIED"
    assert res.canonical_doi == "10.1038/s41558-019-0438-6"


def test_phantom_citation_detection(temp_cache_dir, monkeypatch):
    cache = ReferenceCache(cache_file=temp_cache_dir)
    resolver = ReferenceResolver(cache=cache)

    # Mock search_works returning empty
    monkeypatch.setattr(resolver, "search_works", lambda query, limit=5: [])

    # Fabricated hallucinated paper
    res = resolver.verify_citation(
        title="Revolutionary Quantum Carbon Storage Mechanisms in Subterranean Basalts",
        author="Fictional, Alexander"
    )

    assert res.verified is False
    assert res.status_code == "UNVERIFIED_PHANTOM"
    assert "REF-001" in res.message


def test_security_domain_restriction(temp_cache_dir):
    resolver = ReferenceResolver(cache=ReferenceCache(cache_file=temp_cache_dir))

    # Unauthorized domain raises ValueError
    with pytest.raises(ValueError) as exc:
        resolver._http_get("https://malicious-telemetry-server.com/api/steal")
    assert "Security violation" in str(exc.value)


def test_client_reference_integration(temp_cache_dir):
    client = ArkaisClient(references_cache_file=temp_cache_dir)
    assert client.references is not None

    item = ReferenceItem(
        doi="10.1016/0009-2509(94)00215-m",
        title="Mass transfer and pressure drop in structured packings",
        authors=["Billet, Reinhard"],
        year=1994,
        venue="Chemical Engineering Science"
    )
    client.reference_cache.put(item)

    # Direct client convenience methods
    resolved = client.resolve_doi("10.1016/0009-2509(94)00215-m")
    assert resolved is not None
    assert resolved.title == item.title

    verification = client.verify_citation(title="Mass transfer and pressure drop in structured packings")
    assert verification.verified is True
    assert verification.canonical_doi == item.doi

"""Unit tests for Arkais Template Catalog and Local-First Cache Manager."""

import json
from pathlib import Path
import pytest

from arkais.templates.catalog import (
    SyncResult,
    TemplateCatalog,
    TemplateNotFoundError,
    get_default_catalog,
)
from arkais.templates.models import (
    AssetCategory,
    Discipline,
    EngineType,
    TemplateEnvelope,
)
from arkais.templates.validator import validate_template_file


@pytest.fixture
def clean_catalog(tmp_path) -> TemplateCatalog:
    """Instantiate a TemplateCatalog with an isolated temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True)
    return TemplateCatalog(cache_dir=cache_dir)


def test_catalog_initialization(clean_catalog):
    """Verify catalog indexes built-in bundled seed templates."""
    assert clean_catalog.count() == 50
    assert clean_catalog.contains("fig.physics.scatter.pareto_frontier.v1")
    assert clean_catalog.contains("tbl.cs.benchmarks.model_comparison.v1")


def test_bundled_drop1_catalog_distribution(clean_catalog):
    """Verify the 50 foundational scientific templates across disciplines and categories."""
    stats = clean_catalog.stats()
    assert stats["total"] == 50
    assert stats["bundled"] == 50
    assert stats["by_category"]["figures"] == 25
    assert stats["by_category"]["tables"] == 25

    # Exactly 10 per discipline (5 figures + 5 tables each)
    expected_disciplines = ["computer_science", "physics", "medicine", "economics", "engineering"]
    for disc in expected_disciplines:
        assert stats["by_discipline"][disc] == 10, f"Discipline {disc} has {stats['by_discipline'][disc]} != 10"



def test_catalog_get_and_not_found(clean_catalog):
    """Verify template retrieval by ID and exception handling."""
    fig = clean_catalog.get("fig.physics.scatter.pareto_frontier.v1")
    assert isinstance(fig, TemplateEnvelope)
    assert fig.id == "fig.physics.scatter.pareto_frontier.v1"
    assert fig.engine == EngineType.VEGA_LITE

    # Non-existent ID raises TemplateNotFoundError
    with pytest.raises(TemplateNotFoundError) as exc:
        clean_catalog.get("fig.nonexistent.template.v1")
    assert "fig.nonexistent.template.v1" in str(exc.value)

    # get_or_none returns None
    assert clean_catalog.get_or_none("fig.nonexistent.template.v1") is None


def test_catalog_filtering(clean_catalog):
    """Verify search and multifaceted filtering across category, discipline, and text."""
    # Filter figures
    figures = clean_catalog.list(category=AssetCategory.FIGURES)
    assert all(f.category == AssetCategory.FIGURES for f in figures)
    assert any(f.id == "fig.physics.scatter.pareto_frontier.v1" for f in figures)

    # Filter tables
    tables = clean_catalog.list(category=AssetCategory.TABLES)
    assert all(t.category == AssetCategory.TABLES for t in tables)
    assert any(t.id == "tbl.cs.benchmarks.model_comparison.v1" for t in tables)

    # Filter by discipline
    physics_templates = clean_catalog.list(discipline=Discipline.PHYSICS)
    assert len(physics_templates) >= 1
    assert physics_templates[0].discipline == Discipline.PHYSICS

    # Filter by engine
    latex_templates = clean_catalog.list(engine=EngineType.LATEX_BOOKTABS)
    assert len(latex_templates) >= 1
    assert latex_templates[0].engine == EngineType.LATEX_BOOKTABS

    # Filter by tag
    tagged = clean_catalog.list(tag="pareto")
    assert len(tagged) >= 1
    assert "pareto" in tagged[0].tags

    # Text search
    searched = clean_catalog.list(search="Transformer")
    assert len(searched) >= 1
    assert "Transformer" in searched[0].name


def test_catalog_stats(clean_catalog):
    """Verify aggregation metrics reported by stats()."""
    stats = clean_catalog.stats()
    assert stats["total"] >= 2
    assert stats["bundled"] >= 2
    assert stats["cached"] == 0
    assert "figures" in stats["by_category"]
    assert "tables" in stats["by_category"]
    assert "physics" in stats["by_discipline"]


def test_embed_in_project(clean_catalog, tmp_path):
    """Verify embedding frozen template spec into project directory (Decision Q2)."""
    project_dir = tmp_path / "my_paper"
    embedded_path = clean_catalog.embed_in_project(
        template_id="fig.physics.scatter.pareto_frontier.v1",
        project_dir=project_dir,
    )

    expected_path = project_dir / "assets" / "templates" / "fig.physics.scatter.pareto_frontier.v1.json"
    assert embedded_path == expected_path
    assert expected_path.is_file()

    # Verify that the embedded file is a 100% valid TemplateEnvelope
    loaded = validate_template_file(expected_path)
    assert loaded.id == "fig.physics.scatter.pareto_frontier.v1"
    assert loaded.name == clean_catalog.get("fig.physics.scatter.pareto_frontier.v1").name


def test_cache_overlay_and_clear(clean_catalog):
    """Verify that cached templates overlay bundled ones and can be cleared."""
    cache_dir = clean_catalog.cache_dir
    custom_fig = {
        "$schema": "https://arkais.geegthink.com/schemas/v1/template.json",
        "id": "fig.economics.scatter.gini_lorenz.v1",
        "version": "1.0.0",
        "name": "Empirical Lorenz Curve with Gini Coefficient",
        "category": "figures",
        "discipline": "economics",
        "tags": ["economics", "lorenz", "gini", "inequality"],
        "engine": "vega-lite",
        "author": "The Next Geek Think (NGT)",
        "license": "Apache-2.0",
        "signature_integration": {
            "recommended_gate": "GATE-07",
            "weaving_archetype": "parenthetical_grounding",
            "in_prose_blueprint": "The observed distribution yields a Gini index of {gini_coeff} ({fig_ref}), confirming progressive redistribution.",
            "required_metrics": ["gini_coeff"],
            "unit_discipline": "GATE-08"
        },
        "spec": {
            "mark": "line",
            "encoding": {"x": {"field": "pop_pct"}, "y": {"field": "income_pct"}}
        }
    }
    custom_file = cache_dir / "fig.economics.scatter.gini_lorenz.v1.json"
    custom_file.write_text(json.dumps(custom_fig), encoding="utf-8")

    clean_catalog.reload()
    assert clean_catalog.contains("fig.economics.scatter.gini_lorenz.v1")
    stats = clean_catalog.stats()
    assert stats["cached"] == 1

    # Clear cache
    removed = clean_catalog.clear_cache()
    assert removed >= 1
    assert not clean_catalog.contains("fig.economics.scatter.gini_lorenz.v1")
    assert clean_catalog.contains("fig.physics.scatter.pareto_frontier.v1")  # Bundled remains intact


def test_sync_offline_resilience(clean_catalog):
    """Verify that sync failures on invalid/unreachable endpoints fail gracefully without corrupting local index."""
    initial_count = clean_catalog.count()
    result = clean_catalog.sync(remote_base_url="https://invalid.domain.never.exists.ngt/templates", timeout=1.0)
    assert not result.is_success
    assert len(result.errors) > 0
    # Catalog is unchanged and healthy
    assert clean_catalog.count() == initial_count


def test_default_singleton_catalog():
    """Verify global singleton accessor."""
    cat1 = get_default_catalog()
    cat2 = get_default_catalog()
    assert cat1 is cat2
    assert cat1.count() >= 2

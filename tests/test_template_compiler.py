"""Unit tests for Arkais Rust-powered zero-node vector rendering and table compilation engine."""

from pathlib import Path
import pytest

from arkais.templates.catalog import get_default_catalog
from arkais.templates.compiler import (
    CompilationError,
    RenderFormat,
    RenderOutput,
    TemplateCompiler,
    render_template,
)


@pytest.fixture
def compiler() -> TemplateCompiler:
    return TemplateCompiler()


@pytest.fixture
def catalog():
    return get_default_catalog()


def test_compile_figure_svg(compiler, catalog):
    """Verify rendering Vega-Lite figure to vector SVG."""
    envelope = catalog.get("fig.physics.scatter.pareto_frontier.v1")
    out = compiler.compile_figure(envelope, format=RenderFormat.SVG)

    assert out.format == RenderFormat.SVG
    assert out.mime_type == "image/svg+xml"
    assert out.file_extension == "svg"
    assert isinstance(out.content, str)
    assert "<svg" in out.content
    assert "</svg>" in out.content
    assert "Frequency (MHz)" in out.content


def test_compile_figure_pdf(compiler, catalog):
    """Verify headless rendering of Vega-Lite to crisp vector PDF."""
    envelope = catalog.get("fig.physics.scatter.pareto_frontier.v1")
    out = compiler.compile_figure(envelope, format=RenderFormat.PDF)

    assert out.format == RenderFormat.PDF
    assert out.mime_type == "application/pdf"
    assert out.file_extension == "pdf"
    assert isinstance(out.content, bytes)
    assert out.content.startswith(b"%PDF")
    assert len(out.content) > 5000  # High-quality vector PDF payload


def test_compile_figure_png(compiler, catalog):
    """Verify rasterizing Vega-Lite to high-resolution PNG."""
    envelope = catalog.get("fig.physics.scatter.pareto_frontier.v1")
    out = compiler.compile_figure(envelope, format=RenderFormat.PNG, scale=2.0)

    assert out.format == RenderFormat.PNG
    assert out.mime_type == "image/png"
    assert isinstance(out.content, bytes)
    assert out.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_compile_figure_html(compiler, catalog):
    """Verify standalone interactive HTML export."""
    envelope = catalog.get("fig.physics.scatter.pareto_frontier.v1")
    out = compiler.compile_figure(envelope, format=RenderFormat.HTML)

    assert out.format == RenderFormat.HTML
    assert out.mime_type == "text/html"
    assert isinstance(out.content, str)
    assert "vegaEmbed('#vis'" in out.content
    assert "Bi-Objective Pareto Frontier" in out.content


def test_compile_figure_with_custom_data(compiler, catalog):
    """Verify rendering figure with user-supplied runtime data."""
    envelope = catalog.get("fig.physics.scatter.pareto_frontier.v1")
    custom_points = [
        {"frequency_mhz": 5.0, "dissipation_ratio": 9.8, "regime": "Sub-Harmonic"},
        {"frequency_mhz": 15.0, "dissipation_ratio": 3.2, "regime": "Optimal"}
    ]
    out = compiler.compile_figure(envelope, data=custom_points, format=RenderFormat.SVG)
    assert "Sub-Harmonic" in out.content


def test_compile_table_latex(compiler, catalog):
    """Verify formatting scientific table to LaTeX booktabs source."""
    envelope = catalog.get("tbl.cs.benchmarks.model_comparison.v1")
    out = compiler.compile_table(envelope, format=RenderFormat.LATEX)

    assert out.format == RenderFormat.LATEX
    assert out.mime_type == "application/x-latex"
    assert isinstance(out.content, str)
    assert "\\begin{table}" in out.content
    assert "\\caption{" in out.content
    assert "\\toprule" in out.content
    assert "\\bottomrule" in out.content


def test_compile_table_html(compiler, catalog):
    """Verify formatting scientific table to clean academic HTML."""
    envelope = catalog.get("tbl.cs.benchmarks.model_comparison.v1")
    out = compiler.compile_table(envelope, format=RenderFormat.HTML)

    assert out.format == RenderFormat.HTML
    assert "<table" in out.content
    assert "<thead>" in out.content
    assert "<strong>Model Architecture</strong>" in out.content
    assert "Dense-7B" in out.content


def test_compile_table_markdown(compiler, catalog):
    """Verify formatting scientific table to Markdown format."""
    envelope = catalog.get("tbl.cs.benchmarks.model_comparison.v1")
    out = compiler.compile_table(envelope, format=RenderFormat.MARKDOWN)

    assert out.format == RenderFormat.MARKDOWN
    assert "| **Model Architecture** | **Active Params** |" in out.content
    assert "| --- | --- |" in out.content


def test_render_output_save(compiler, catalog, tmp_path):
    """Verify saving rendered artifacts to disk."""
    envelope = catalog.get("fig.physics.scatter.pareto_frontier.v1")
    out_pdf = compiler.compile_figure(envelope, format=RenderFormat.PDF)
    pdf_file = tmp_path / "exports" / "test_pareto.pdf"
    saved_pdf = out_pdf.save(pdf_file)

    assert saved_pdf == pdf_file
    assert pdf_file.is_file()
    assert pdf_file.read_bytes().startswith(b"%PDF")

    tbl_envelope = catalog.get("tbl.cs.benchmarks.model_comparison.v1")
    out_tex = compiler.compile_table(tbl_envelope, format=RenderFormat.LATEX)
    tex_file = tmp_path / "exports" / "test_table.tex"
    saved_tex = out_tex.save(tex_file)

    assert saved_tex == tex_file
    assert tex_file.is_file()
    assert "\\begin{table}" in tex_file.read_text(encoding="utf-8")


def test_render_template_convenience_function(tmp_path):
    """Verify top-level render_template dispatcher."""
    svg_out = render_template("fig.physics.scatter.pareto_frontier.v1", format="svg")
    assert svg_out.format == RenderFormat.SVG
    assert "<svg" in svg_out.content

    dest_file = tmp_path / "quick_table.md"
    md_out = render_template("tbl.cs.benchmarks.model_comparison.v1", format="markdown", output_path=dest_file)
    assert md_out.format == RenderFormat.MARKDOWN
    assert dest_file.is_file()
    assert "| **Model Architecture** |" in dest_file.read_text()

"""Rust-powered zero-node vector rendering and table compilation engine for Arkais templates.

Converts declarative Vega-Lite specifications into publication-grade vector PDF and clean SVG,
and transforms LaTeX booktabs tables into LaTeX source, clean HTML previews, and Markdown tables.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from arkais.templates.catalog import TemplateCatalog, get_default_catalog
from arkais.templates.models import AssetCategory, EngineType, TemplateEnvelope

try:
    import vl_convert as _vlc
    _VL_CONVERT_AVAILABLE = True
except ImportError:
    _vlc = None
    _VL_CONVERT_AVAILABLE = False


class RenderFormat(str, Enum):
    """Output formats supported by Arkais compilers."""
    SVG = "svg"
    PDF = "pdf"
    PNG = "png"
    HTML = "html"
    LATEX = "latex"
    MARKDOWN = "markdown"


class CompilationError(Exception):
    """Raised when compilation or rendering of a template fails."""
    pass


@dataclass
class RenderOutput:
    """Artifact resulting from rendering a template."""
    format: RenderFormat
    content: Union[str, bytes]
    mime_type: str
    file_extension: str

    def save(self, path: Union[str, Path]) -> Path:
        """Write rendered output to disk."""
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(self.content, bytes):
            target.write_bytes(self.content)
        else:
            target.write_text(self.content, encoding="utf-8")
        return target

    def to_string(self) -> str:
        """Decode content to string if text or base64 representation."""
        if isinstance(self.content, str):
            return self.content
        return self.content.decode("utf-8", errors="replace")


class TemplateCompiler:
    """Headless compilation engine for scientific figures and tables."""

    def __init__(self, catalog: Optional[TemplateCatalog] = None):
        self.catalog = catalog or get_default_catalog()

    def compile(
        self,
        envelope: TemplateEnvelope,
        data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
        format: Optional[Union[str, RenderFormat]] = None,
        output_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> RenderOutput:
        """Universal compilation dispatcher for figures and tables.

        Args:
            envelope: The TemplateEnvelope to compile.
            data: Optional data payload to inject. Falls back to envelope.sample_data.
            format: Target format (svg, pdf, png, html, latex, markdown).
            output_path: Optional path to save rendered asset.

        Returns:
            RenderOutput containing the compiled content.
        """
        # Determine default format based on asset category
        if format is None:
            target_format = RenderFormat.SVG if envelope.category == AssetCategory.FIGURES else RenderFormat.LATEX
        elif isinstance(format, str):
            target_format = RenderFormat(format.lower())
        else:
            target_format = format

        if envelope.category == AssetCategory.FIGURES:
            out = self.compile_figure(envelope, data=data, format=target_format, **kwargs)
        else:
            out = self.compile_table(envelope, data=data, format=target_format, **kwargs)

        if output_path is not None:
            out.save(output_path)

        return out

    def compile_figure(
        self,
        envelope: TemplateEnvelope,
        data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
        format: RenderFormat = RenderFormat.SVG,
        scale: float = 2.0,
        **kwargs: Any,
    ) -> RenderOutput:
        """Compile a figure template to vector SVG, PDF, or raster PNG.

        Args:
            envelope: Figure template envelope.
            data: Data points to inject into the Vega-Lite specification.
            format: Target RenderFormat (SVG, PDF, PNG, HTML).
            scale: Pixel density scale for raster exports (default: 2.0 for Retina/Print).

        Returns:
            RenderOutput instance.
        """
        if envelope.engine == EngineType.VEGA_LITE:
            return self._compile_vegalite(envelope, data=data, format=format, scale=scale, **kwargs)
        elif envelope.engine == EngineType.SVG_CUSTOM:
            return self._compile_custom_svg(envelope, format=format)
        else:
            raise CompilationError(
                f"Unsupported figure engine '{envelope.engine.value}' for template '{envelope.id}'. "
                "Supported figure engines: vega-lite, svg-custom."
            )

    def _compile_vegalite(
        self,
        envelope: TemplateEnvelope,
        data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
        format: RenderFormat = RenderFormat.SVG,
        scale: float = 2.0,
        **kwargs: Any,
    ) -> RenderOutput:
        """Process Vega-Lite spec using Rust-based vl-convert."""
        if not _VL_CONVERT_AVAILABLE:
            raise CompilationError(
                "vl-convert-python is not installed. Install via 'uv pip install vl-convert-python'."
            )

        if not isinstance(envelope.spec, dict):
            raise CompilationError(f"Vega-Lite template '{envelope.id}' must provide a dictionary spec.")

        # Deep copy spec and inject data
        spec = copy.deepcopy(envelope.spec)
        active_data = data if data is not None else envelope.sample_data

        if active_data is not None:
            if isinstance(active_data, list):
                spec["data"] = {"values": active_data}
            elif isinstance(active_data, dict):
                if "values" in active_data:
                    spec["data"] = active_data
                else:
                    spec["data"] = {"values": active_data}

        # Ensure title if not set in spec
        if "title" not in spec:
            spec["title"] = {
                "text": envelope.name,
                "fontSize": 13,
                "fontWeight": 600,
                "anchor": "start",
                "color": "#18181b",
            }

        try:
            if format == RenderFormat.SVG:
                svg_str = _vlc.vegalite_to_svg(spec)
                return RenderOutput(
                    format=RenderFormat.SVG,
                    content=svg_str,
                    mime_type="image/svg+xml",
                    file_extension="svg",
                )

            elif format == RenderFormat.PDF:
                pdf_bytes = _vlc.vegalite_to_pdf(spec)
                return RenderOutput(
                    format=RenderFormat.PDF,
                    content=pdf_bytes,
                    mime_type="application/pdf",
                    file_extension="pdf",
                )

            elif format == RenderFormat.PNG:
                png_bytes = _vlc.vegalite_to_png(spec, scale=scale)
                return RenderOutput(
                    format=RenderFormat.PNG,
                    content=png_bytes,
                    mime_type="image/png",
                    file_extension="png",
                )

            elif format == RenderFormat.HTML:
                html_str = self._render_vegalite_html(envelope, spec)
                return RenderOutput(
                    format=RenderFormat.HTML,
                    content=html_str,
                    mime_type="text/html",
                    file_extension="html",
                )

            else:
                raise CompilationError(
                    f"Format '{format.value}' is not supported for Vega-Lite figures. "
                    "Use 'svg', 'pdf', 'png', or 'html'."
                )

        except Exception as e:
            if isinstance(e, CompilationError):
                raise
            raise CompilationError(f"Vega-Lite rendering failed for '{envelope.id}': {str(e)}") from e

    def _render_vegalite_html(self, envelope: TemplateEnvelope, spec: Dict[str, Any]) -> str:
        """Generate standalone HTML document embedding Vega-Lite spec."""
        spec_json = json.dumps(spec)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{envelope.name} - Arkais</title>
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 2rem;
      background: #fafafa;
      color: #18181b;
    }}
    .container {{
      max-width: 900px;
      margin: 0 auto;
      background: #ffffff;
      padding: 2rem;
      border: 1px solid #e4e4e7;
      border-radius: 8px;
    }}
    .caption {{
      margin-top: 1.5rem;
      font-size: 0.9rem;
      color: #52525b;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div id="vis"></div>
    <div class="caption">
      <strong>{envelope.render_caption(1)}</strong>
    </div>
  </div>
  <script>
    const spec = {spec_json};
    vegaEmbed('#vis', spec, {{ actions: true, renderer: 'svg' }});
  </script>
</body>
</html>"""

    def _compile_custom_svg(self, envelope: TemplateEnvelope, format: RenderFormat) -> RenderOutput:
        """Handle raw SVG spec."""
        if isinstance(envelope.spec, str):
            svg_content = envelope.spec
        elif isinstance(envelope.spec, dict) and "svg" in envelope.spec:
            svg_content = str(envelope.spec["svg"])
        else:
            raise CompilationError(f"Template '{envelope.id}' does not provide valid SVG source.")

        if format == RenderFormat.SVG:
            return RenderOutput(
                format=RenderFormat.SVG,
                content=svg_content,
                mime_type="image/svg+xml",
                file_extension="svg",
            )
        elif format == RenderFormat.PDF and _VL_CONVERT_AVAILABLE:
            pdf_bytes = _vlc.svg_to_pdf(svg_content)
            return RenderOutput(
                format=RenderFormat.PDF,
                content=pdf_bytes,
                mime_type="application/pdf",
                file_extension="pdf",
            )
        else:
            raise CompilationError(f"Format '{format.value}' not supported for custom SVG template.")

    def compile_table(
        self,
        envelope: TemplateEnvelope,
        data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
        format: RenderFormat = RenderFormat.LATEX,
        label: Optional[str] = None,
        caption: Optional[str] = None,
        **kwargs: Any,
    ) -> RenderOutput:
        """Compile a scientific table template to LaTeX booktabs, clean HTML, or Markdown.

        Args:
            envelope: Table template envelope.
            data: Data payload to substitute into tabular rows.
            format: Target RenderFormat (LATEX, HTML, MARKDOWN).
            label: LaTeX label (e.g. 'tab:baseline_params').
            caption: Table caption override.

        Returns:
            RenderOutput instance.
        """
        raw_spec = envelope.spec
        if not isinstance(raw_spec, str):
            if isinstance(raw_spec, dict) and "latex" in raw_spec:
                raw_spec = str(raw_spec["latex"])
            else:
                raw_spec = str(raw_spec)

        active_caption = caption or envelope.render_caption(1)
        active_label = label or f"tab:{envelope.id.replace('.', '_')}"

        if format == RenderFormat.LATEX:
            latex_code = self._format_latex_booktabs(raw_spec, caption=active_caption, label=active_label)
            return RenderOutput(
                format=RenderFormat.LATEX,
                content=latex_code,
                mime_type="application/x-latex",
                file_extension="tex",
            )

        elif format == RenderFormat.HTML:
            html_table = self._convert_latex_to_html(raw_spec, caption=active_caption, notes=envelope.notes)
            return RenderOutput(
                format=RenderFormat.HTML,
                content=html_table,
                mime_type="text/html",
                file_extension="html",
            )

        elif format == RenderFormat.MARKDOWN:
            md_table = self._convert_latex_to_markdown(raw_spec, caption=active_caption)
            return RenderOutput(
                format=RenderFormat.MARKDOWN,
                content=md_table,
                mime_type="text/markdown",
                file_extension="md",
            )

        else:
            raise CompilationError(
                f"Format '{format.value}' is not supported for tables. "
                "Supported table formats: latex, html, markdown."
            )

    def _format_latex_booktabs(self, latex_str: str, caption: str, label: str) -> str:
        """Inject proper academic caption and label into LaTeX table environment."""
        clean = latex_str.strip()
        # If already wrapped in table environment, inject or replace caption/label
        if "\\begin{table}" in clean:
            if "\\caption{" not in clean:
                clean = clean.replace(
                    "\\begin{table}[t]\n\\centering",
                    f"\\begin{{table}}[t]\n\\centering\n\\caption{{{caption}}}\n\\label{{{label}}}"
                )
            return clean

        # Wrap raw tabular in table environment
        return f"""\\begin{{table}}[t]
\\centering
\\caption{{{caption}}}
\\label{{{label}}}
{clean}
\\end{{table}}"""

    def _convert_latex_to_html(self, latex_str: str, caption: str, notes: Optional[str] = None) -> str:
        """Convert a LaTeX booktabs tabular snippet to a clean academic HTML table."""
        # Extract rows inside tabular
        tabular_match = re.search(r"\\begin\{tabular\}\{[^}]+\}(.*?)\\end\{tabular\}", latex_str, re.DOTALL)
        if not tabular_match:
            body = latex_str
        else:
            body = tabular_match.group(1)

        # Remove toprule, midrule, bottomrule
        cleaned_body = re.sub(r"\\(?:toprule|midrule|bottomrule|hline)", "", body)
        raw_rows = [r.strip() for r in cleaned_body.split("\\\\") if r.strip()]

        html_rows = []
        is_header = True

        for row in raw_rows:
            # Clean LaTeX commands: \textbf{}, \textit{}, \small, etc.
            clean_row = re.sub(r"\\textbf\{([^}]+)\}", r"<strong>\1</strong>", row)
            clean_row = re.sub(r"\\textit\{([^}]+)\}", r"<em>\1</em>", clean_row)
            clean_row = re.sub(r"\\[a-zA-Z]+", "", clean_row)

            cells = [c.strip() for c in clean_row.split("&")]
            if is_header:
                th_cells = "".join(f"    <th style='padding: 6px 12px; text-align: left; border-bottom: 2px solid #18181b;'>{c}</th>\n" for c in cells)
                html_rows.append(f"  <thead>\n  <tr>\n{th_cells}  </tr>\n  </thead>\n  <tbody>")
                is_header = False
            else:
                td_cells = "".join(f"    <td style='padding: 6px 12px; border-bottom: 1px solid #e4e4e7;'>{c}</td>\n" for c in cells)
                html_rows.append(f"  <tr>\n{td_cells}  </tr>")

        table_body = "\n".join(html_rows) + "\n  </tbody>"
        notes_html = f"<p style='font-size: 0.8rem; color: #71717a; margin-top: 6px;'>{notes}</p>" if notes else ""

        return f"""<div style="font-family: 'Times New Roman', Times, serif; margin: 1.5rem 0;">
  <p style="font-size: 0.95rem; font-weight: bold; margin-bottom: 8px;">{caption}</p>
  <table style="border-collapse: collapse; width: 100%; border-top: 2px solid #18181b; border-bottom: 2px solid #18181b; font-size: 0.9rem;">
{table_body}
  </table>
  {notes_html}
</div>"""

    def _convert_latex_to_markdown(self, latex_str: str, caption: str) -> str:
        """Convert a LaTeX booktabs tabular snippet to GFM Markdown table."""
        tabular_match = re.search(r"\\begin\{tabular\}\{[^}]+\}(.*?)\\end\{tabular\}", latex_str, re.DOTALL)
        body = tabular_match.group(1) if tabular_match else latex_str

        cleaned_body = re.sub(r"\\(?:toprule|midrule|bottomrule|hline)", "", body)
        raw_rows = [r.strip() for r in cleaned_body.split("\\\\") if r.strip()]

        md_lines = [f"**{caption}**\n"]
        header_parsed = False

        for row in raw_rows:
            clean_row = re.sub(r"\\textbf\{([^}]+)\}", r"**\1**", row)
            clean_row = re.sub(r"\\textit\{([^}]+)\}", r"*\1*", clean_row)
            clean_row = re.sub(r"\\[a-zA-Z]+", "", clean_row)

            cells = [c.strip() for c in clean_row.split("&")]
            row_str = "| " + " | ".join(cells) + " |"
            md_lines.append(row_str)

            if not header_parsed:
                separator = "| " + " | ".join(["---"] * len(cells)) + " |"
                md_lines.append(separator)
                header_parsed = True

        return "\n".join(md_lines)


def render_template(
    template_id_or_envelope: Union[str, TemplateEnvelope],
    format: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
    data: Optional[Any] = None,
    catalog: Optional[TemplateCatalog] = None,
    **kwargs: Any,
) -> RenderOutput:
    """High-level function to render any template by ID or envelope instance."""
    cat = catalog or get_default_catalog()
    if isinstance(template_id_or_envelope, str):
        envelope = cat.get(template_id_or_envelope)
    else:
        envelope = template_id_or_envelope

    compiler = TemplateCompiler(catalog=cat)
    return compiler.compile(envelope, data=data, format=format, output_path=output_path, **kwargs)

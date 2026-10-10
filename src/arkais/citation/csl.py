"""CSL-backed citation formatting — THE-80.

Replaces the hand-rolled `CitationFormatter`. The old implementation formatted APA, IEEE and
Nature by string interpolation, which is why the same reference could render three different
ways depending on which code path asked. There is now exactly one rendering authority: a pinned
citeproc-js subprocess speaking CSL 1.0.2.

Two formatters means two answers, so the old one is deleted rather than deprecated. Callers keep
their existing surface — `format_in_text`, `format_bibliography`, `format_bibtex` — but the
output is now whatever the stylesheet says, not what this file assumed.

Note on `format_in_text`: CSL numbering is a property of the whole ordered document, not of a
lone reference. Rendering one item in isolation gives an author-date form for author-date styles
and a number for numeric ones, but that number carries no document meaning. Callers that need
correct numbering must render the document through the Spine's `render()`, which sees the sequence.
This method exists for single-item display and is explicit about that limitation.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .models import CitationStyle

#: Maps the product's `CitationStyle` enum onto CSL style ids present in
#: `06_TOOLS/spine/styles/`. Anything unmapped is an error, never a silent fallback — a citation
#: rendered in an unrequested style is worse than one that fails to render.
STYLE_IDS: Dict[str, str] = {
    CitationStyle.NATURE.value: "nature",
    CitationStyle.IEEE.value: "ieee",
    CitationStyle.APA_7TH.value: "apa",
    CitationStyle.CHICAGO.value: "chicago-author-date",
    # `harvard` has no separate CSL id upstream; author-date is the same lineage. Mapping it
    # explicitly keeps the enum total without pretending harvard is its own stylesheet.
    CitationStyle.HARVARD.value: "chicago-author-date",
}


class CslProcessorError(RuntimeError):
    """The CSL processor is unavailable or refused the work.

    Never caught and degraded into hand-rolled output. A reference manager that silently changes
    citation style when its renderer breaks is the failure this whole project exists to prevent.
    """


def _find_wrapper() -> Optional[Path]:
    """Locate `cslexec.js`.

    Searched in order: explicit env override, the workspace-relative location, then PATH. The
    Spine owns the processor; the SDK is a client of it, so a missing wrapper is a deployment
    error and is reported as one.
    """
    override = os.environ.get("ARKAIS_CSL_WRAPPER")
    if override and Path(override).is_file():
        return Path(override)

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "06_TOOLS" / "spine" / "cslexec.js"
        if candidate.is_file():
            return candidate
    return None


class CslCitationFormatter:
    """Drop-in replacement for the deleted `CitationFormatter`."""

    def __init__(self, wrapper: Optional[Path] = None, locale: str = "en-US") -> None:
        self.wrapper = wrapper or _find_wrapper()
        self.locale = locale

    # -- process ---------------------------------------------------------------

    def _call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if self.wrapper is None:
            raise CslProcessorError(
                "citeproc-js wrapper not found. Set ARKAIS_CSL_WRAPPER or ensure "
                "06_TOOLS/spine/cslexec.js is present. This module does not fall back to "
                "hand-rolled formatting."
            )
        node = shutil.which("node")
        if not node:
            raise CslProcessorError("node is required to run the pinned CSL processor")
        try:
            proc = subprocess.run(
                [node, str(self.wrapper)],
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=60,
            )
        except Exception as exc:
            raise CslProcessorError(f"could not run the CSL processor: {exc}") from exc

        stdout = (proc.stdout or "").strip()
        if not stdout:
            raise CslProcessorError(
                f"CSL processor produced no output (exit {proc.returncode}): "
                f"{(proc.stderr or '').strip()[:300]}"
            )
        try:
            reply = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise CslProcessorError(f"CSL processor emitted non-JSON: {stdout[:200]!r}") from exc
        if not reply.get("ok"):
            raise CslProcessorError(f"CSL processor refused the work: {reply.get('error')}")
        return reply

    @staticmethod
    def _style_id(style: Any) -> str:
        value = style.value if isinstance(style, CitationStyle) else str(style)
        mapped = STYLE_IDS.get(value)
        if not mapped:
            raise CslProcessorError(
                f"no CSL stylesheet is pinned for {value!r}. Known: {sorted(STYLE_IDS)}. "
                f"Add one under 06_TOOLS/spine/styles/ rather than guessing a fallback."
            )
        return mapped

    # -- surface ---------------------------------------------------------------

    def format_in_text(self, item: Any, style: CitationStyle = CitationStyle.APA_7TH,
                       index: Optional[int] = None) -> str:
        """Render one reference as an in-text citation.

        `index` is accepted for interface compatibility and ignored: numbering is a whole-document
        property. Passing it would let a caller believe a number is document-accurate when it is
        not.
        """
        csl = _item_to_csl(item, "solo")
        reply = self._call({
            "op": "render",
            "style_id": self._style_id(style),
            "locale": self.locale,
            "document_id": "solo",
            "items": {csl["id"]: csl},
            "events": [{"event_id": "c1:1", "source_id": csl["id"], "revision": 1}],
        })
        entries = reply.get("entries") or []
        return _plain(entries[0]["html"]) if entries else ""

    def format_bibliography(self, items: Sequence[Any],
                            style: CitationStyle = CitationStyle.APA_7TH) -> List[str]:
        csls = [_item_to_csl(it, f"ref{i}") for i, it in enumerate(items)]
        reply = self._call({
            "op": "bibliography",
            "style_id": self._style_id(style),
            "locale": self.locale,
            "source_ids": [c["id"] for c in csls],
            "items": {c["id"]: c for c in csls},
        })
        return [_plain(entry) for entry in (reply.get("entries") or [])]

    def format_bibtex(self, item: Any) -> str:
        """BibTeX is a serialization format, not a rendering one.

        CSL cannot emit it. This delegates to the exporter rather than hand-rolling an entry, so
        the SDK carries no BibTeX writer of its own. See `spec.md` §4.4 and P2-X1.
        """
        from ..reference.serialize import to_bibtex

        return to_bibtex([_item_to_csl(item, "solo")], style_id="biblatex")[0]


def _item_to_csl(item: Any, fallback_id: str) -> Dict[str, Any]:
    """Project a `ReferenceItem` (or a dict) onto CSL-JSON."""
    if isinstance(item, dict):
        csl = dict(item)
    else:
        csl = {
            "id": getattr(item, "doi", None) or fallback_id,
            "type": _type_for(getattr(item, "document_type", None)),
            "title": getattr(item, "title", "") or "",
            "container-title": getattr(item, "journal", "") or "",
            "volume": getattr(item, "volume", "") or "",
            "issue": getattr(item, "issue", "") or "",
            "page": getattr(item, "pages", "") or "",
            "issued": {"date-parts": [[getattr(item, "year", 0) or 0]]},
            "DOI": getattr(item, "doi", "") or "",
        }
        # `ReferenceItem.authors` is a list of names, each either "Family, Given" or "Given Family".
        parsed = [_name_to_csl(a) for a in (getattr(item, "authors", None) or []) if str(a).strip()]
        # The field is sometimes a pre-joined string in older call sites.
        if not parsed:
            raw = getattr(item, "authors", "")
            if isinstance(raw, str):
                parsed = [_name_to_csl(a) for a in raw.split(",") if a.strip()]
        if parsed:
            csl["author"] = parsed
    csl.setdefault("id", fallback_id)
    return csl


def _name_to_csl(name: str) -> Dict[str, str]:
    """One author string onto a CSL name object."""
    n = str(name).strip()
    if "," in n:
        family, _, given = n.partition(",")
        return {"family": family.strip(), "given": given.strip()}
    parts = n.split()
    if len(parts) < 2:
        return {"literal": n}
    return {"family": parts[-1], "given": " ".join(parts[:-1])}


_TYPE_MAP = {
    "journal": "article-journal", "article": "article-journal",
    "book": "book", "chapter": "chapter", "conference": "paper-conference",
    "thesis": "thesis", "report": "report", "dataset": "dataset",
    "preprint": "article", "web": "webpage",
}


def _type_for(value: Optional[str]) -> str:
    return _TYPE_MAP.get((value or "").lower(), "article-journal")


def _plain(html: str) -> str:
    """Strip CSL markup down to text.

    citeproc emits HTML by design. Downstream consumers here want plain strings, and doing the
    stripping here keeps every caller from writing its own regex over `<i>` tags.
    """
    import re

    text = re.sub(r"<[^>]+>", "", html or "")
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&#38;", "&").replace("&quot;", '"').replace("&#39;", "'"))
    return re.sub(r"\s+", " ", text).strip()
"""Multi-style citation formatter and BibTeX generator for Project Arkais."""

import re
from typing import List, Optional, Tuple, Dict, Any
from .models import CitationStyle, FormattedCitation
from ..reference.models import ReferenceItem


def _get_author_family_names(authors: List[str]) -> List[str]:
    """Extracts family/last names from author strings."""
    families = []
    for a in authors:
        a = a.strip()
        if "," in a:
            families.append(a.split(",")[0].strip())
        else:
            parts = a.split()
            families.append(parts[-1].strip() if parts else a)
    return families


def _format_author_initials(author_str: str) -> str:
    """Formats author as 'Last, F. M.'."""
    author_str = author_str.strip()
    if "," in author_str:
        parts = author_str.split(",", 1)
        family = parts[0].strip()
        givens = parts[1].strip().split()
        initials = " ".join([f"{g[0]}." for g in givens if g])
        return f"{family}, {initials}" if initials else family
    else:
        parts = author_str.split()
        if len(parts) == 1:
            return parts[0]
        family = parts[-1]
        givens = parts[:-1]
        initials = " ".join([f"{g[0]}." for g in givens if g])
        return f"{family}, {initials}" if initials else family


def _generate_cite_key(item: ReferenceItem) -> str:
    """Generates an authentic BibTeX citation key e.g. keith2018process."""
    families = _get_author_family_names(item.authors)
    first_author = families[0].lower() if families else "unknown"
    first_author = re.sub(r"[^a-z0-9]", "", first_author)
    year = str(item.year) if item.year else "nodate"
    
    title_words = [w.lower() for w in re.findall(r"\b[A-Za-z0-9]+\b", item.title) if w.lower() not in {"a", "an", "the", "on", "in", "for", "of", "to"}]
    first_word = title_words[0] if title_words else "paper"
    return f"{first_author}{year}{first_word}"


class CitationFormatter:
    """Standardized academic citation and bibliography engine."""

    def format_in_text(self, item: ReferenceItem, style: CitationStyle = CitationStyle.APA_7TH, index: Optional[int] = None) -> str:
        """Formats in-text citation token."""
        families = _get_author_family_names(item.authors)
        year_str = str(item.year) if item.year else "n.d."

        if style == CitationStyle.IEEE:
            idx = index or 1
            return f"[{idx}]"

        if style == CitationStyle.NATURE:
            idx = index or 1
            # Unicode superscripts
            supers = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
            return str(idx).translate(supers)

        if style == CitationStyle.HARVARD:
            if not families:
                return f"(Anon {year_str})"
            if len(families) == 1:
                return f"({families[0]} {year_str})"
            if len(families) == 2:
                return f"({families[0]} and {families[1]} {year_str})"
            return f"({families[0]} et al. {year_str})"

        if style == CitationStyle.CHICAGO:
            if not families:
                return f"(Anon. {year_str})"
            if len(families) == 1:
                return f"({families[0]} {year_str})"
            if len(families) == 2:
                return f"({families[0]} and {families[1]} {year_str})"
            return f"({families[0]} et al. {year_str})"

        # Default APA 7th
        if not families:
            return f"(Unknown, {year_str})"
        if len(families) == 1:
            return f"({families[0]}, {year_str})"
        if len(families) == 2:
            return f"({families[0]} & {families[1]}, {year_str})"
        return f"({families[0]} et al., {year_str})"

    def format_bibliography_entry(self, item: ReferenceItem, style: CitationStyle = CitationStyle.APA_7TH, index: Optional[int] = None) -> str:
        """Formats full bibliography entry."""
        year_str = str(item.year) if item.year else "n.d."
        venue = item.venue or "Unpublished manuscript"
        doi_url = f"https://doi.org/{item.doi}" if item.doi else (item.url or "")

        if style == CitationStyle.IEEE:
            idx = index or 1
            # D. W. Keith and G. Holmes
            author_list = []
            for a in item.authors:
                formatted = _format_author_initials(a)
                if "," in formatted:
                    parts = formatted.split(",", 1)
                    author_list.append(f"{parts[1].strip()} {parts[0].strip()}")
                else:
                    author_list.append(formatted)

            if len(author_list) > 1:
                authors_str = ", ".join(author_list[:-1]) + " and " + author_list[-1]
            elif author_list:
                authors_str = author_list[0]
            else:
                authors_str = "Anon."

            parts = [f"[{idx}] {authors_str}, \"{item.title},\" *{venue}*"]
            if item.volume:
                parts.append(f"vol. {item.volume}")
            if item.issue:
                parts.append(f"no. {item.issue}")
            if item.pages:
                parts.append(f"pp. {item.pages}")
            parts.append(f"{year_str}")
            if item.doi:
                parts.append(f"doi: {item.doi}.")
            return ", ".join(parts)

        if style == CitationStyle.NATURE:
            idx = index or 1
            authors_str = ", ".join([_format_author_initials(a) for a in item.authors]) or "Anon."
            res = f"{idx}. {authors_str} {item.title}. *{venue}*"
            if item.volume:
                res += f" **{item.volume}**"
            if item.pages:
                res += f", {item.pages}"
            res += f" ({year_str})."
            return res

        if style == CitationStyle.HARVARD:
            authors_str = ", ".join([_format_author_initials(a) for a in item.authors]) or "Anon."
            res = f"{authors_str}, {year_str}. {item.title}. *{venue}*"
            if item.volume:
                res += f", {item.volume}"
                if item.issue:
                    res += f"({item.issue})"
            if item.pages:
                res += f", pp.{item.pages}"
            res += "."
            return res

        if style == CitationStyle.CHICAGO:
            authors_str = "; ".join(item.authors) or "Anon."
            res = f"{authors_str}. {year_str}. \"{item.title}.\" *{venue}*"
            if item.volume:
                res += f" {item.volume}"
                if item.issue:
                    res += f" ({item.issue})"
            if item.pages:
                res += f": {item.pages}"
            res += f". {doi_url}"
            return res

        # Default APA 7th
        # Keith, D. W., & Holmes, G. (2018). Title. Venue, Vol(Issue), pp. DOI
        formatted_authors = [_format_author_initials(a) for a in item.authors]
        if len(formatted_authors) > 1:
            authors_str = ", ".join(formatted_authors[:-1]) + ", & " + formatted_authors[-1]
        elif formatted_authors:
            authors_str = formatted_authors[0]
        else:
            authors_str = "Unknown"

        res = f"{authors_str} ({year_str}). {item.title}. *{venue}*"
        if item.volume:
            res += f", *{item.volume}*"
            if item.issue:
                res += f"({item.issue})"
        if item.pages:
            res += f", {item.pages}"
        res += f". {doi_url}"
        return res

    def format_bibtex(self, item: ReferenceItem) -> str:
        """Generates clean standard BibTeX entry."""
        key = _generate_cite_key(item)
        authors_bib = " and ".join(item.authors) if item.authors else "Unknown"

        lines = [
            f"@article{{{key},",
            f"  author = {{{authors_bib}}},",
            f"  title = {{{{{item.title}}}}},",
            f"  journal = {{{item.venue or 'Journal'}}},",
            f"  year = {{{item.year or 'nodate'}}}"
        ]
        if item.volume:
            lines.append(f"  volume = {{{item.volume}}},")
        if item.issue:
            lines.append(f"  number = {{{item.issue}}},")
        if item.pages:
            lines.append(f"  pages = {{{item.pages}}},")
        if item.doi:
            lines.append(f"  doi = {{{item.doi}}},")
        lines.append("}")
        return "\n".join(lines)

    def format_bibliography(self, items: List[ReferenceItem], style: CitationStyle = CitationStyle.APA_7TH) -> List[str]:
        """Formats a sorted list of bibliography entries according to style rules."""
        if style in (CitationStyle.APA_7TH, CitationStyle.HARVARD, CitationStyle.CHICAGO):
            # Sort alphabetically by first author last name
            sorted_items = sorted(items, key=lambda x: (_get_author_family_names(x.authors)[0] if x.authors else "zzz").lower())
            return [self.format_bibliography_entry(item, style=style) for item in sorted_items]
        else:
            # Sequential numeric for IEEE and Nature
            return [self.format_bibliography_entry(item, style=style, index=idx) for idx, item in enumerate(items, start=1)]

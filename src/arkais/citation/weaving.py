"""Rhetorical in-text citation weaving engine for Project Arkais."""

from typing import List, Optional
from .models import RhetoricalRole, CitationStyle
from .formatter import _get_author_family_names
from ..reference.models import ReferenceItem


class RhetoricalWeaver:
    """Weaves academic citations into authentic human discourse frames.
    
    Eliminates synthetic AI parenthetical slop by diversifying syntactic roles:
    - Integral subjects ("Keith and colleagues (2018) demonstrated...")
    - Passive agent frames ("As demonstrated by Keith et al. (2018)...")
    - Clustered consensus parentheticals ("(Lackner, 1999; Keith et al., 2018)")
    - Contrastive dialectical tension ("While early models posited bounds (Lackner, 1999)...")
    - Methodological references ("...using the configuration described in (Keith et al., 2018)")
    """

    def weave(
        self,
        item: ReferenceItem,
        role: RhetoricalRole = RhetoricalRole.INTEGRAL_SUBJECT,
        verb: str = "demonstrated",
        claim_context: str = "",
        style: CitationStyle = CitationStyle.APA_7TH
    ) -> str:
        """Generates an authentic in-prose sentence lead or clause integrating the citation."""
        families = _get_author_family_names(item.authors)
        year_str = str(item.year) if item.year else "n.d."

        # Compute author textual phrase
        if not families:
            author_phrase = "Earlier investigations"
            author_et_al = "Earlier studies"
        elif len(families) == 1:
            author_phrase = families[0]
            author_et_al = families[0]
        elif len(families) == 2:
            author_phrase = f"{families[0]} and {families[1]}"
            author_et_al = f"{families[0]} and {families[1]}"
        else:
            author_phrase = f"{families[0]} and colleagues"
            author_et_al = f"{families[0]} et al."

        if role == RhetoricalRole.INTEGRAL_SUBJECT:
            return f"{author_phrase} ({year_str}) {verb} that {claim_context}".strip()

        if role == RhetoricalRole.INTEGRAL_PASSIVE:
            return f"As {verb} by {author_et_al} ({year_str}), {claim_context}".strip()

        if role == RhetoricalRole.CONTRASTIVE_TENSION:
            return f"While {author_phrase} ({year_str}) posited that {claim_context}".strip()

        if role == RhetoricalRole.METHODOLOGICAL:
            return f"following the protocol described in ({author_et_al}, {year_str})".strip()

        # Default PARENTHETICAL_CONSENSUS
        if claim_context:
            return f"{claim_context} ({author_et_al}, {year_str})".strip()
        return f"({author_et_al}, {year_str})"

    def weave_cluster(self, items: List[ReferenceItem], style: CitationStyle = CitationStyle.APA_7TH) -> str:
        """Weaves multiple references into an authentic parenthetical consensus cluster."""
        if not items:
            return ""

        parts = []
        for item in items:
            families = _get_author_family_names(item.authors)
            year_str = str(item.year) if item.year else "n.d."
            if not families:
                author_tag = "Unknown"
            elif len(families) == 1:
                author_tag = families[0]
            elif len(families) == 2:
                author_tag = f"{families[0]} & {families[1]}"
            else:
                author_tag = f"{families[0]} et al."
            parts.append(f"{author_tag}, {year_str}")

        return f"({'; '.join(parts)})"

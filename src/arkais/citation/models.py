"""Citation data structures and stylistic enumerations for Project Arkais."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class CitationStyle(str, Enum):
    """Supported academic citation standards."""
    APA_7TH = "apa_7th"
    IEEE = "ieee"
    NATURE = "nature"
    HARVARD = "harvard"
    CHICAGO = "chicago"


class RhetoricalRole(str, Enum):
    """Authentic academic rhetorical in-text citation placement patterns."""
    INTEGRAL_SUBJECT = "integral_subject"              # "Keith and colleagues (2018) demonstrated..."
    INTEGRAL_PASSIVE = "integral_passive"              # "As demonstrated by Keith et al. (2018), ..."
    PARENTHETICAL_CONSENSUS = "parenthetical_consensus"# "...exhibits quadratic scaling (Keith et al., 2018)."
    CONTRASTIVE_TENSION = "contrastive_tension"        # "While earlier models assumed asymptotic bounds (Lackner, 1999), ..."
    METHODOLOGICAL = "methodological"                  # "...using the contactor configuration described in (Keith et al., 2018)."


@dataclass
class FormattedCitation:
    """Formatted in-text token, bibliography entry, and BibTeX representation."""
    in_text: str
    bibliography_entry: str
    style: CitationStyle
    doi: str
    bibtex: str

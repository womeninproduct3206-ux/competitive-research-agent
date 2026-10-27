"""The building blocks of a research run, shared by every part of the app."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class ResearchCategory(str, Enum):
    FEATURES = "Product features"
    PRICING = "Pricing"
    POSITIONING = "Positioning"
    LAUNCHES = "Recent launches"
    REVIEWS = "Customer reviews"
    GAPS = "Product gaps"


class EvidenceType(str, Enum):
    """How confident a statement is. Every claim in a report carries one of these."""

    FACT = "Verified fact"      # directly supported by a quoted source
    INFERENCE = "Inference"     # reasoned from one or more facts
    HYPOTHESIS = "Hypothesis"   # an idea worth testing, not yet supported


@dataclass
class Competitor:
    name: str
    urls: List[str] = field(default_factory=list)


@dataclass
class ResearchRequest:
    product_name: str
    product_description: str
    industry: str
    target_customer: str
    competitors: List[Competitor]
    objectives: str
    categories: List[ResearchCategory]


@dataclass
class Source:
    """A public web page the app read, and when it read it."""

    title: str
    url: str
    accessed_at: str  # ISO date-time, e.g. "2026-10-27T15:40:00Z"
    excerpt: str = ""


@dataclass
class Claim:
    """One statement in the report, tied to the sources that support it."""

    competitor: str
    category: ResearchCategory
    statement: str
    evidence_type: EvidenceType
    source_urls: List[str] = field(default_factory=list)
    quote: str = ""

    def is_supported(self) -> bool:
        """A verified fact must point at a source and carry a supporting quote."""
        if self.evidence_type is EvidenceType.FACT:
            return bool(self.source_urls) and bool(self.quote.strip())
        return True

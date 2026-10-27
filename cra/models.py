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
    excerpt: str = ""  # short summary of what the page says, shown in the report
    text: str = ""     # full extracted page text, used by the fact-checker


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


@dataclass
class FeatureEntry:
    """One cell of the feature comparison matrix."""

    competitor: str
    feature: str
    status: str  # "Yes", "No" or "Not found" (not mentioned in any source)
    source_url: str = ""
    quote: str = ""


@dataclass
class PriceEntry:
    """A price exactly as published on a source page."""

    competitor: str
    plan: str
    price: str    # as written on the page, e.g. "$12" or "Contact sales"
    billing: str  # e.g. "per user / month"
    source_url: str
    notes: str = ""
    quote: str = ""


class InsightKind(str, Enum):
    NEED = "Underserved customer need"
    STRENGTH = "Competitor strength"
    WEAKNESS = "Competitor weakness"
    OPPORTUNITY = "Product opportunity"


@dataclass
class Insight:
    kind: InsightKind
    title: str
    reasoning: str  # why we believe this, in plain English
    evidence_type: EvidenceType
    source_urls: List[str] = field(default_factory=list)


@dataclass
class SkippedPage:
    """A page we did not use, and the plain-English reason why."""

    competitor: str
    url: str
    reason: str


@dataclass
class Report:
    request: ResearchRequest
    sources: List[Source]
    claims: List[Claim]
    features: List[FeatureEntry]
    prices: List[PriceEntry]
    insights: List[Insight]
    generated_at: str
    is_demo: bool
    rejected_claims: List[Claim] = field(default_factory=list)  # failed the fact-check
    notes: List[str] = field(default_factory=list)  # general messages shown at the top
    analyzed_by: str = ""  # which AI service produced the findings, if any
    skipped_pages: List[SkippedPage] = field(default_factory=list)

    def claims_for(self, category: ResearchCategory) -> List[Claim]:
        return [c for c in self.claims if c.category is category]

"""Asks the AI to extract findings from the collected pages, then checks every answer.

The AI only sees pages the fetcher actually read. It must cite pages by number and quote them
word for word. Plain code then verifies each quote; anything that fails is removed and listed
in the report's Fact-check tab.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from cra.llm import LLMClient
from cra.models import (
    Claim,
    EvidenceType,
    FeatureEntry,
    Insight,
    InsightKind,
    PriceEntry,
    ResearchCategory,
    ResearchRequest,
    Source,
)
from cra.verification import quote_in_sources, verify_claims

MAX_TOTAL_CHARS = 150_000   # all page text sent to the AI, roughly 40,000 tokens
MAX_CHARS_PER_PAGE = 15_000

SYSTEM_PROMPT = """You are a careful competitive-research analyst helping a Product Manager.

Rules you must follow:
- Use ONLY the numbered sources provided. Never use outside knowledge about these companies.
- Every finding must cite source numbers. A "Verified fact" must include a quote copied
  word for word from ONE cited source (5 to 30 words, no edits, no ellipses).
- Never invent facts, prices, dates, launches, customer quotes or features. If the sources
  don't cover something, leave it out. Empty lists are fine.
- Prices: copy the price text exactly as written on the page (e.g. "Rs 299", "$12"), and only
  when the page clearly states it. The quote must contain that price.
- Customer complaints must come from customer reviews or comments shown on the pages,
  not from marketing copy.
- Label each finding honestly: "Verified fact" (directly stated in the quote),
  "Inference" (your reasoning from cited facts), or "Hypothesis" (an idea worth testing).
- Insights must explain the reasoning and evidence in plain English, for a non-technical reader.
- Use the competitor names exactly as given."""


def _schema() -> Dict[str, Any]:
    def obj(props: Dict[str, Any]) -> Dict[str, Any]:
        return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}

    text = {"type": "string"}
    numbers = {"type": "array", "items": {"type": "integer"}}
    evidence = {"type": "string", "enum": [e.value for e in EvidenceType]}
    return obj({
        "findings": {"type": "array", "items": obj({
            "competitor": text,
            "category": {"type": "string", "enum": [c.value for c in ResearchCategory]},
            "statement": text,
            "evidence_type": evidence,
            "source_numbers": numbers,
            "quote": text,
        })},
        "features": {"type": "array", "items": obj({
            "competitor": text,
            "feature": text,
            "status": {"type": "string", "enum": ["Yes", "No"]},
            "source_number": {"type": "integer"},
            "quote": text,
        })},
        "prices": {"type": "array", "items": obj({
            "competitor": text,
            "plan": text,
            "price": text,
            "billing": text,
            "notes": text,
            "source_number": {"type": "integer"},
            "quote": text,
        })},
        "insights": {"type": "array", "items": obj({
            "kind": {"type": "string", "enum": [k.value for k in InsightKind]},
            "title": text,
            "reasoning": text,
            "evidence_type": evidence,
            "source_numbers": numbers,
        })},
    })


@dataclass
class Analysis:
    claims: List[Claim] = field(default_factory=list)
    features: List[FeatureEntry] = field(default_factory=list)
    prices: List[PriceEntry] = field(default_factory=list)
    insights: List[Insight] = field(default_factory=list)
    rejected: List[Claim] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def build_prompt(request: ResearchRequest, sources: List[Source], competitor_of: Dict[str, str]) -> Tuple[str, bool]:
    """The research brief plus numbered page texts. Returns (prompt, was_any_page_shortened)."""
    per_page = min(MAX_CHARS_PER_PAGE, MAX_TOTAL_CHARS // max(len(sources), 1))
    shortened = False
    parts = [
        "RESEARCH BRIEF",
        f"Our product: {request.product_name} - {request.product_description}",
        f"Industry: {request.industry}",
        f"Target customer: {request.target_customer}",
        f"Research objectives: {request.objectives}",
        f"Competitors: {', '.join(c.name for c in request.competitors)}",
        f"Categories to cover: {', '.join(c.value for c in request.categories)}",
        "",
        "SOURCES",
    ]
    for i, source in enumerate(sources, start=1):
        text = source.text
        if len(text) > per_page:
            text, shortened = text[:per_page], True
        parts += [f"=== [{i}] {source.title} | {source.url} | competitor: {competitor_of.get(source.url, '?')} ===",
                  text, ""]
    parts.append("Extract findings, a feature list, published prices and insights following the rules.")
    return "\n".join(parts), shortened


def _canonical_name(name: str, competitors: List[str]) -> str:
    for known in competitors:
        if name.strip().lower() == known.lower():
            return known
    return name.strip()


def _enum(enum_cls, value: str, default):
    for member in enum_cls:
        if member.value == value:
            return member
    return default


def _numbers(text: str) -> List[str]:
    """All numbers in a text, with thousands separators removed: "Rs 1,099.00" -> ["1099.00"]."""
    return [n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)]


def _price_in_quote(price: str, quote: str) -> bool:
    """Every number in the price must appear as a whole number in the quote."""
    price_numbers = _numbers(price)
    if not price_numbers:  # e.g. "Contact sales" - must appear in the quote as words
        return bool(price.strip()) and price.strip().lower() in quote.lower()
    quote_numbers = set(_numbers(quote))
    return all(n in quote_numbers for n in price_numbers)


def interpret(raw: Dict[str, Any], request: ResearchRequest, sources: List[Source]) -> Analysis:
    """Turn the AI's JSON into report items, verifying every one against the sources."""
    names = [c.name for c in request.competitors]
    selected = set(request.categories)
    by_number = {i: s for i, s in enumerate(sources, start=1)}
    by_url = {s.url: s for s in sources}
    result = Analysis()

    def urls(numbers) -> List[str]:
        return [by_number[n].url for n in numbers or [] if isinstance(n, int) and n in by_number]

    claims = []
    for item in raw.get("findings", []):
        category = _enum(ResearchCategory, item.get("category"), None)
        if category is None or category not in selected:
            continue
        cited = urls(item.get("source_numbers"))
        claim = Claim(_canonical_name(item.get("competitor", ""), names), category, item.get("statement", "").strip(),
                      _enum(EvidenceType, item.get("evidence_type"), EvidenceType.HYPOTHESIS),
                      cited, item.get("quote", "").strip())
        if len(cited) != len(item.get("source_numbers") or []):
            result.rejected.append(claim)  # cited a page number that doesn't exist
        else:
            claims.append(claim)
    kept, rejected = verify_claims(claims, sources)
    result.claims, result.rejected = kept, result.rejected + rejected

    if ResearchCategory.FEATURES in selected:
        found: Dict[Tuple[str, str], FeatureEntry] = {}
        for item in raw.get("features", []):
            cited = urls([item.get("source_number")])
            competitor = _canonical_name(item.get("competitor", ""), names)
            feature = item.get("feature", "").strip()
            quote = item.get("quote", "").strip()
            if cited and quote and quote_in_sources(quote, cited, by_url):
                found[(feature, competitor)] = FeatureEntry(competitor, feature, item.get("status", "Yes"), cited[0], quote)
            else:
                result.rejected.append(Claim(competitor, ResearchCategory.FEATURES,
                                             f"Feature '{feature}': {item.get('status')}", EvidenceType.FACT, cited, quote))
        features = sorted({f for f, _ in found})
        competitors = names + sorted({c for _, c in found} - set(names))
        result.features = [found.get((f, c), FeatureEntry(c, f, "Not found")) for f in features for c in competitors]

    if ResearchCategory.PRICING in selected:
        for item in raw.get("prices", []):
            cited = urls([item.get("source_number")])
            competitor = _canonical_name(item.get("competitor", ""), names)
            quote, price = item.get("quote", "").strip(), item.get("price", "").strip()
            if cited and quote and quote_in_sources(quote, cited, by_url) and _price_in_quote(price, quote):
                result.prices.append(PriceEntry(competitor, item.get("plan", "").strip(), price,
                                                item.get("billing", "").strip(), cited[0],
                                                item.get("notes", "").strip(), quote))
            else:
                result.rejected.append(Claim(competitor, ResearchCategory.PRICING,
                                             f"{item.get('plan', '')}: {price}", EvidenceType.FACT, cited, quote))

    for item in raw.get("insights", []):
        cited = urls(item.get("source_numbers"))
        evidence = _enum(EvidenceType, item.get("evidence_type"), EvidenceType.HYPOTHESIS)
        if evidence is EvidenceType.FACT and not cited:
            evidence = EvidenceType.INFERENCE  # a "fact" with no source can't be called verified
        result.insights.append(Insight(_enum(InsightKind, item.get("kind"), InsightKind.OPPORTUNITY),
                                       item.get("title", "").strip(), item.get("reasoning", "").strip(),
                                       evidence, cited))
    return result


def analyze(request: ResearchRequest, sources: List[Source], competitor_of: Dict[str, str],
            client: LLMClient) -> Analysis:
    prompt, shortened = build_prompt(request, sources, competitor_of)
    raw = client.generate_json(SYSTEM_PROMPT, prompt, _schema())
    analysis = interpret(raw, request, sources)
    if shortened:
        analysis.notes.append("Some long pages were shortened before analysis, so details near the "
                              "end of those pages may be missing.")
    return analysis

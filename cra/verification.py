"""The fact-checker: plain code (no AI) that checks every "verified fact" against its sources.

A fact survives only if its quote really appears in the text of one of the pages it cites.
Everything else is removed from the report and listed separately, so nothing is hidden.
"""

import re
from typing import Dict, List, Tuple

from cra.models import Claim, EvidenceType, Source


def _normalize(text: str) -> str:
    text = text.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip()


def quote_in_sources(quote: str, urls: List[str], sources_by_url: Dict[str, Source]) -> bool:
    needle = _normalize(quote)
    if not needle:
        return False
    for url in urls:
        source = sources_by_url.get(url)
        if source and needle in _normalize(source.text or source.excerpt):
            return True
    return False


def verify_claims(claims: List[Claim], sources: List[Source]) -> Tuple[List[Claim], List[Claim]]:
    """Split claims into (kept, rejected)."""
    sources_by_url = {s.url: s for s in sources}
    kept: List[Claim] = []
    rejected: List[Claim] = []
    for claim in claims:
        unknown_source = any(url not in sources_by_url for url in claim.source_urls)
        if unknown_source:
            rejected.append(claim)  # cites a page we never read
        elif claim.evidence_type is EvidenceType.FACT and not (
            claim.is_supported() and quote_in_sources(claim.quote, claim.source_urls, sources_by_url)
        ):
            rejected.append(claim)
        else:
            kept.append(claim)
    return kept, rejected

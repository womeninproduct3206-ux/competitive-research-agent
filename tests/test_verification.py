from cra.models import Claim, EvidenceType, ResearchCategory, Source
from cra.verification import verify_claims

URL = "https://example.com/pricing"
SOURCES = [Source("Pricing", URL, "2026-01-01T00:00:00Z", text="Team plan: $12 per user / month.")]


def claim(quote, evidence=EvidenceType.FACT, urls=(URL,)):
    return Claim("X", ResearchCategory.PRICING, "statement", evidence, list(urls), quote)


def test_fact_with_matching_quote_is_kept():
    kept, rejected = verify_claims([claim("team plan:  $12 PER user")], SOURCES)
    assert len(kept) == 1 and rejected == []


def test_fact_with_invented_quote_is_rejected():
    kept, rejected = verify_claims([claim("$10 per user")], SOURCES)
    assert kept == [] and len(rejected) == 1


def test_fact_without_quote_is_rejected():
    _, rejected = verify_claims([claim("")], SOURCES)
    assert len(rejected) == 1


def test_claim_citing_unknown_page_is_rejected_even_if_inference():
    _, rejected = verify_claims([claim("", EvidenceType.INFERENCE, ["https://never-read.example.com"])], SOURCES)
    assert len(rejected) == 1


def test_hypothesis_without_sources_is_kept():
    kept, _ = verify_claims([claim("", EvidenceType.HYPOTHESIS, [])], SOURCES)
    assert len(kept) == 1

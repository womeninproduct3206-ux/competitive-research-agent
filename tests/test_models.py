from cra.models import Claim, EvidenceType, ResearchCategory


def make_claim(evidence_type, urls=(), quote=""):
    return Claim(
        competitor="Demo Brand A",
        category=ResearchCategory.PRICING,
        statement="Sample statement",
        evidence_type=evidence_type,
        source_urls=list(urls),
        quote=quote,
    )


def test_fact_needs_source_and_quote():
    assert not make_claim(EvidenceType.FACT).is_supported()
    assert not make_claim(EvidenceType.FACT, urls=["https://example.com"]).is_supported()
    assert make_claim(EvidenceType.FACT, ["https://example.com"], "quoted text").is_supported()


def test_hypothesis_does_not_need_a_source():
    assert make_claim(EvidenceType.HYPOTHESIS).is_supported()

from cra.analyzer import _schema, analyze, build_prompt, interpret
from cra.fetcher import Fetcher
from cra.llm import LLMError
from cra.models import Competitor, EvidenceType, ResearchCategory as Cat, Source
from cra.pipeline import run_research
from tests.helpers import sample_request
from tests.test_fetcher import PAGE, make_fetcher

AMUL = "https://amul.test/ice-cream"
GAW = "https://getaway.test/"
SOURCES = [
    Source("Amul Ice Creams", AMUL, "2026-10-27T00:00:00Z",
           text="Amul Protein Ice Cream 125 ml: Rs 50. Now available in Mango. Launched in June 2026."),
    Source("Get Away Desserts", GAW, "2026-10-27T00:00:00Z",
           text="Guilt-free desserts with 0 added sugar. Pint Tub: Rs 325. "
                "Customer review: 'Tastes great but melts too quickly in delivery.'"),
]


def request():
    req = sample_request()
    req.competitors = [Competitor("Amul", [AMUL]), Competitor("Get-A-Whey", [GAW])]
    return req


GOOD_ANSWER = {
    "findings": [
        {"competitor": "amul", "category": "Recent launches", "statement": "Launched a mango flavour.",
         "evidence_type": "Verified fact", "source_numbers": [1], "quote": "Now available in Mango"},
        {"competitor": "Get-A-Whey", "category": "Customer reviews", "statement": "Melting during delivery.",
         "evidence_type": "Verified fact", "source_numbers": [2], "quote": "melts too quickly in delivery"},
        {"competitor": "Get-A-Whey", "category": "Positioning", "statement": "Invented claim.",
         "evidence_type": "Verified fact", "source_numbers": [2], "quote": "India's number one dessert"},
        {"competitor": "Amul", "category": "Positioning", "statement": "Cites a page that doesn't exist.",
         "evidence_type": "Inference", "source_numbers": [7], "quote": ""},
    ],
    "features": [
        {"competitor": "Get-A-Whey", "feature": "No added sugar", "status": "Yes", "source_number": 2,
         "quote": "0 added sugar"},
        {"competitor": "Amul", "feature": "No added sugar", "status": "Yes", "source_number": 1,
         "quote": "zero sugar range"},
    ],
    "prices": [
        {"competitor": "Amul", "plan": "Protein 125 ml", "price": "Rs 50", "billing": "per cup", "notes": "",
         "source_number": 1, "quote": "Amul Protein Ice Cream 125 ml: Rs 50"},
        {"competitor": "Get-A-Whey", "plan": "Pint", "price": "Rs 299", "billing": "per tub", "notes": "",
         "source_number": 2, "quote": "Pint Tub: Rs 325"},
    ],
    "insights": [
        {"kind": "Underserved customer need", "title": "Delivery-proof packaging",
         "reasoning": "Reviewers mention melting.", "evidence_type": "Inference", "source_numbers": [2]},
        {"kind": "Competitor strength", "title": "Unsourced fact",
         "reasoning": "No source given.", "evidence_type": "Verified fact", "source_numbers": []},
    ],
}


class FakeAI:
    label = "Fake AI"

    def __init__(self, answer=None, error=None):
        self.answer, self.error, self.calls = answer, error, []

    def generate_json(self, system, prompt, schema):
        self.calls.append((system, prompt, schema))
        if self.error:
            raise self.error
        return self.answer


def test_true_findings_are_kept_and_invented_ones_removed():
    result = interpret(GOOD_ANSWER, request(), SOURCES)
    statements = [c.statement for c in result.claims]
    assert "Launched a mango flavour." in statements
    assert result.claims[0].competitor == "Amul"  # name normalised to the user's spelling
    rejected = [c.statement for c in result.rejected]
    assert "Invented claim." in rejected
    assert "Cites a page that doesn't exist." in rejected


def test_feature_matrix_keeps_verified_cells_and_fills_not_found():
    result = interpret(GOOD_ANSWER, request(), SOURCES)
    cells = {(f.feature, f.competitor): f.status for f in result.features}
    assert cells[("No added sugar", "Get-A-Whey")] == "Yes"
    assert cells[("No added sugar", "Amul")] == "Not found"  # its quote wasn't on the page
    assert any("No added sugar" in c.statement for c in result.rejected)


def test_price_must_appear_in_its_quote():
    result = interpret(GOOD_ANSWER, request(), SOURCES)
    assert [(p.competitor, p.price) for p in result.prices] == [("Amul", "Rs 50")]
    assert any("Rs 299" in c.statement for c in result.rejected)


def test_unsourced_fact_insight_is_relabelled_as_inference():
    result = interpret(GOOD_ANSWER, request(), SOURCES)
    insight = next(i for i in result.insights if i.title == "Unsourced fact")
    assert insight.evidence_type is EvidenceType.INFERENCE


def test_unselected_categories_are_dropped():
    req = request()
    req.categories = [Cat.REVIEWS]
    result = interpret(GOOD_ANSWER, req, SOURCES)
    assert {c.category for c in result.claims} == {Cat.REVIEWS}
    assert result.features == [] and result.prices == []


def test_prompt_contains_numbered_sources_and_long_pages_are_shortened():
    long_source = Source("Long", "https://long.test/", "2026-10-27T00:00:00Z", text="x" * 50_000)
    prompt, shortened = build_prompt(request(), SOURCES + [long_source], {AMUL: "Amul"})
    assert "[1] Amul Ice Creams | https://amul.test/ice-cream | competitor: Amul" in prompt
    assert "[3] Long" in prompt and shortened
    assert "x" * 15_001 not in prompt


def test_schema_requires_every_field():
    item = _schema()["properties"]["findings"]["items"]
    assert set(item["required"]) == set(item["properties"]) and item["additionalProperties"] is False


def test_analyze_adds_note_when_pages_shortened():
    long_source = Source("Long", "https://long.test/", "2026-10-27T00:00:00Z", text="y" * 50_000)
    result = analyze(request(), [long_source], {}, FakeAI({"findings": [], "features": [], "prices": [], "insights": []}))
    assert any("shortened" in n for n in result.notes)


def live_request():
    req = sample_request()
    req.competitors = [Competitor("Acme", ["https://acme.test/pricing"])]
    return req


def test_live_pipeline_with_ai_produces_fact_checked_report():
    fetcher, _, _ = make_fetcher({"https://acme.test/pricing": (200, {}, PAGE)}, min_delay=0)
    answer = {"findings": [{"competitor": "Acme", "category": "Pricing", "statement": "Team plan is $12.",
                            "evidence_type": "Verified fact", "source_numbers": [1],
                            "quote": "Our Team plan costs $12 per user per month"}],
              "features": [], "prices": [{"competitor": "Acme", "plan": "Team", "price": "$12",
                                          "billing": "per user / month", "notes": "", "source_number": 1,
                                          "quote": "Team plan costs $12 per user per month"}],
              "insights": []}
    ai = FakeAI(answer)
    report = run_research(live_request(), live=True, fetcher=fetcher, client=ai)
    assert report.analyzed_by == "Fake AI"
    assert len(report.claims) == 1 and report.prices[0].price == "$12"
    assert "acme.test/pricing" in ai.calls[0][1]  # the AI saw the page we read


def test_ai_failure_keeps_sources_and_explains():
    fetcher, _, _ = make_fetcher({"https://acme.test/pricing": (200, {}, PAGE)}, min_delay=0)
    ai = FakeAI(error=LLMError("Google Gemini says we've hit the free tier's daily limit."))
    report = run_research(live_request(), live=True, fetcher=fetcher, client=ai)
    assert len(report.sources) == 1 and report.claims == []
    assert any("AI analysis failed" in n and "daily limit" in n for n in report.notes)


def test_ai_is_not_called_when_no_pages_were_read():
    fetcher, _, _ = make_fetcher({}, min_delay=0)
    ai = FakeAI({})
    run_research(live_request(), live=True, fetcher=fetcher, client=ai)
    assert ai.calls == []


def test_price_check_needs_exact_numbers():
    from cra.analyzer import _price_in_quote
    assert _price_in_quote("Rs 50", "Protein Cup 125 ml: Rs 50")
    assert not _price_in_quote("Rs 25", "Protein Cup 125 ml: Rs 50")  # 25 is only part of 125
    assert _price_in_quote("Rs 1,099", "Family Pack: Rs 1,099")
    assert _price_in_quote("Rs 1099", "Family Pack: Rs 1,099")
    assert _price_in_quote("Contact sales", "Enterprise: contact sales")
    assert not _price_in_quote("", "anything")

import csv
import io

from cra.demo import DEMO_LABEL
from cra.models import EvidenceType, ResearchCategory
from cra.pipeline import run_research
from cra.report import claims_csv, features_csv, pricing_csv, to_markdown
from tests.helpers import sample_request


def test_demo_report_is_labeled_and_fact_checked():
    steps = []
    report = run_research(sample_request(), progress=lambda f, m: steps.append(f))
    assert report.is_demo
    assert steps[-1] == 1.0
    # The deliberately invented nonprofit discount must be caught.
    assert any("nonprofit" in c.statement for c in report.rejected_claims)
    assert not any("nonprofit" in c.statement for c in report.claims)


def test_every_source_url_in_report_was_actually_read():
    report = run_research(sample_request())
    read = {s.url for s in report.sources}
    cited = {u for c in report.claims for u in c.source_urls}
    cited |= {f.source_url for f in report.features if f.source_url}
    cited |= {p.source_url for p in report.prices}
    cited |= {u for i in report.insights for u in i.source_urls}
    assert cited <= read


def test_markdown_has_demo_banner_sources_and_labels():
    md = to_markdown(run_research(sample_request()))
    assert DEMO_LABEL in md
    assert "## Sources" in md and "accessed 2026-01-15" in md
    assert EvidenceType.HYPOTHESIS.value in md
    assert "## Removed by fact-check" in md


def test_markdown_only_includes_selected_categories():
    md = to_markdown(run_research(sample_request([ResearchCategory.PRICING])))
    assert "## Pricing comparison" in md
    assert "## Feature comparison" not in md
    assert "## Recent launches" not in md


def test_every_csv_row_is_labeled_demo():
    report = run_research(sample_request())
    for text in (claims_csv(report), features_csv(report), pricing_csv(report)):
        rows = list(csv.DictReader(io.StringIO(text)))
        assert rows and all(r["data_status"] == DEMO_LABEL for r in rows)


def test_insight_headings_are_spelled_correctly():
    md = to_markdown(run_research(sample_request()))
    assert "### Competitor weaknesses" in md and "### Product opportunities" in md
    assert "weaknesss" not in md and "opportunitys" not in md

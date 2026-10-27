"""Runs a research job from start to finish and reports progress along the way."""

from datetime import datetime, timezone
from typing import Callable, List, Optional

from cra import demo
from cra.analyzer import Analysis, analyze
from cra.fetcher import Fetcher
from cra.llm import LLMClient, LLMError
from cra.models import Report, ResearchRequest, SkippedPage, Source
from cra.verification import verify_claims

ProgressCallback = Callable[[float, str], None]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_research(
    request: ResearchRequest,
    progress: Optional[ProgressCallback] = None,
    live: bool = False,
    fetcher: Optional[Fetcher] = None,
    client: Optional[LLMClient] = None,
) -> Report:
    """Produce a report for the request.

    live=False: the labeled sample report (no internet needed).
    live=True:  reads the real public pages listed in the request, then (if an AI client is
                given) extracts fact-checked findings from them. Without a client the report
                lists the collected sources only.
    """
    def step(fraction: float, message: str) -> None:
        if progress:
            progress(fraction, message)

    if live:
        return _run_live(request, step, fetcher or Fetcher(), client)
    return _run_demo(request, step)


def _run_demo(request: ResearchRequest, step: Callable[[float, str], None]) -> Report:
    step(0.1, "Loading sample sources (demo mode)...")
    sources = demo.demo_sources()
    step(0.4, "Loading sample findings...")
    claims = demo.demo_claims()
    step(0.6, "Fact-checking every claim against its sources...")
    kept, rejected = verify_claims(claims, sources)
    step(0.8, "Building comparisons and insights...")
    report = Report(
        request=request,
        sources=sources,
        claims=kept,
        features=demo.demo_features(),
        prices=demo.demo_prices(),
        insights=demo.demo_insights(),
        generated_at=_now(),
        is_demo=True,
        rejected_claims=rejected,
        notes=["This is a sample report with invented brands. It does not describe your competitors."],
    )
    step(1.0, "Report ready.")
    return report


def _run_live(request: ResearchRequest, step: Callable[[float, str], None], fetcher: Fetcher,
              client: Optional[LLMClient]) -> Report:
    pages = [(c.name, url) for c in request.competitors for url in c.urls]
    reading_share = 0.6 if client else 0.9
    sources: List[Source] = []
    competitor_of = {}
    skipped: List[SkippedPage] = []
    for i, (competitor, url) in enumerate(pages):
        step(0.05 + reading_share * i / len(pages), f"Reading page {i + 1} of {len(pages)} ({competitor}): {url}")
        result = fetcher.fetch(url)
        if result.ok:
            sources.append(result.source)
            competitor_of[result.source.url] = competitor
        else:
            skipped.append(SkippedPage(competitor, url, result.skipped_reason))

    notes = [f"Read {len(sources)} of {len(pages)} pages."]
    analysis = Analysis()
    analyzed_by = ""
    if not sources:
        notes.append("No pages could be read, so there is nothing to analyse. "
                     "See 'Pages we could not use' in the Sources tab for the reasons.")
    elif client is None:
        notes.append("No AI service is set up, so this report lists the collected sources only. "
                     "Add an API key to get findings, comparisons and insights.")
    else:
        step(0.7, f"Analysing {len(sources)} pages with {client.label}... (this can take a minute)")
        try:
            analysis = analyze(request, sources, competitor_of, client)
            analyzed_by = client.label
            step(0.95, "Fact-checking every finding against its source...")
        except LLMError as exc:
            notes.append(f"⚠️ AI analysis failed: {exc} The pages that were read are listed below.")
        notes += analysis.notes

    step(1.0, "Report ready.")
    return Report(
        request=request,
        sources=sources,
        claims=analysis.claims,
        features=analysis.features,
        prices=analysis.prices,
        insights=analysis.insights,
        generated_at=_now(),
        is_demo=False,
        rejected_claims=analysis.rejected,
        notes=notes,
        skipped_pages=skipped,
        analyzed_by=analyzed_by,
    )

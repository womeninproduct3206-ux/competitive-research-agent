"""Runs a research job from start to finish and reports progress along the way."""

from datetime import datetime, timezone
from typing import Callable, List, Optional

from cra import demo
from cra.fetcher import Fetcher
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
) -> Report:
    """Produce a report for the request.

    live=False: the labeled sample report (no internet needed).
    live=True:  reads the real public pages listed in the request. AI analysis of those pages
                arrives in Milestone 4, so for now the report lists the collected sources only.
    """
    def step(fraction: float, message: str) -> None:
        if progress:
            progress(fraction, message)

    if live:
        return _run_live(request, step, fetcher or Fetcher())
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


def _run_live(request: ResearchRequest, step: Callable[[float, str], None], fetcher: Fetcher) -> Report:
    pages = [(c.name, url) for c in request.competitors for url in c.urls]
    sources: List[Source] = []
    skipped: List[SkippedPage] = []
    for i, (competitor, url) in enumerate(pages):
        step(0.05 + 0.85 * i / len(pages), f"Reading page {i + 1} of {len(pages)} ({competitor}): {url}")
        result = fetcher.fetch(url)
        if result.ok:
            sources.append(result.source)
        else:
            skipped.append(SkippedPage(competitor, url, result.skipped_reason))

    notes = [f"Read {len(sources)} of {len(pages)} pages. "
             "AI analysis of these pages arrives in Milestone 4, so this report lists sources only."]
    if not sources:
        notes.append("No pages could be read. See 'Pages we could not use' for the reasons.")
    step(1.0, "Sources collected.")
    return Report(
        request=request,
        sources=sources,
        claims=[],
        features=[],
        prices=[],
        insights=[],
        generated_at=_now(),
        is_demo=False,
        notes=notes,
        skipped_pages=skipped,
    )

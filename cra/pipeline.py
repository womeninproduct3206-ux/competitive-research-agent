"""Runs a research job from start to finish and reports progress along the way."""

from datetime import datetime, timezone
from typing import Callable, Optional

from cra import demo
from cra.models import Report, ResearchRequest
from cra.verification import verify_claims

ProgressCallback = Callable[[float, str], None]


def run_research(request: ResearchRequest, progress: Optional[ProgressCallback] = None) -> Report:
    """Produce a report for the request.

    Until live research is built (Milestones 3-4), this always returns the labeled sample report.
    """
    def step(fraction: float, message: str) -> None:
        if progress:
            progress(fraction, message)

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
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        is_demo=True,
        rejected_claims=rejected,
        notes=["This is a sample report with invented brands. It does not describe your competitors."],
    )
    step(1.0, "Report ready.")
    return report

"""Turns a Report into downloadable Markdown and CSV, with sources beside every claim."""

import csv
import io
from typing import Dict, List

from cra.demo import DEMO_LABEL
from cra.models import Claim, EvidenceType, InsightKind, Report, ResearchCategory as Cat, Source

EVIDENCE_ICONS = {
    EvidenceType.FACT: "✅",
    EvidenceType.INFERENCE: "🔍",
    EvidenceType.HYPOTHESIS: "💡",
}

INSIGHT_HEADINGS = {
    InsightKind.NEED: "Underserved customer needs",
    InsightKind.STRENGTH: "Competitor strengths",
    InsightKind.WEAKNESS: "Competitor weaknesses",
    InsightKind.OPPORTUNITY: "Product opportunities",
}

# Report sections that list claims, and the category each one needs.
CLAIM_SECTIONS = [
    (Cat.POSITIONING, "Positioning"),
    (Cat.FEATURES, "Feature observations"),
    (Cat.LAUNCHES, "Recent launches"),
    (Cat.REVIEWS, "Customer complaints and feedback"),
    (Cat.GAPS, "Product gaps"),
    (Cat.PRICING, "Pricing observations"),
]


def evidence_label(evidence_type: EvidenceType) -> str:
    return f"{EVIDENCE_ICONS[evidence_type]} {evidence_type.value}"


def access_date(source: Source) -> str:
    return source.accessed_at[:10]


def competitor_names(report: Report) -> List[str]:
    names: List[str] = []
    for item in [*report.features, *report.prices, *report.claims]:
        if item.competitor not in names:
            names.append(item.competitor)
    return names


def feature_matrix(report: Report) -> List[Dict[str, str]]:
    """One row per feature, one column per competitor."""
    rows: Dict[str, Dict[str, str]] = {}
    for entry in report.features:
        rows.setdefault(entry.feature, {"Feature": entry.feature})[entry.competitor] = entry.status
    return list(rows.values())


class Citations:
    """Numbers each source in the order it was read, e.g. [1], [2]."""

    def __init__(self, sources: List[Source]):
        self.by_url = {s.url: s for s in sources}
        self.numbers = {s.url: i + 1 for i, s in enumerate(sources)}

    def cite(self, urls: List[str]) -> str:
        parts = []
        for url in urls:
            source = self.by_url.get(url)
            if source:
                parts.append(f"[[{self.numbers[url]}]]({url} \"{source.title}, accessed {access_date(source)}\")")
        return " ".join(parts)


def claim_line(claim: Claim, cites: Citations) -> str:
    line = f"- **{evidence_label(claim.evidence_type)}:** {claim.statement}"
    if claim.quote:
        line += f" — *\"{claim.quote}\"*"
    return f"{line} {cites.cite(claim.source_urls)}".rstrip()


# Each *_md function returns one report section as Markdown lines (empty if nothing to show).
# The web page and the Markdown download both use them, so they always match.

def feature_table_md(report: Report, cites: Citations) -> List[str]:
    if not report.features:
        return []
    names = competitor_names(report)
    cells_by_key = {(f.feature, f.competitor): f for f in report.features}
    out = ["| Feature | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for row in feature_matrix(report):
        cells = []
        for name in names:
            entry = cells_by_key.get((row["Feature"], name))
            if entry is None:
                cells.append("-")
            else:
                cells.append(f"{entry.status} {cites.cite([entry.source_url]) if entry.source_url else ''}".strip())
        out.append(f"| {row['Feature']} | " + " | ".join(cells) + " |")
    out += ["", "*\"Not found\" means the feature was not mentioned in the sources we read, "
            "not that it doesn't exist.*"]
    return out


def pricing_table_md(report: Report, cites: Citations) -> List[str]:
    if not report.prices:
        return []
    out = ["| Competitor | Plan | Price | Billing | Notes | Source |", "|---|---|---|---|---|---|"]
    for p in report.prices:
        out.append(f"| {p.competitor} | {p.plan} | {p.price} | {p.billing} | {p.notes} | {cites.cite([p.source_url])} |")
    out += ["", "*Prices are copied exactly as published on the source page on the date accessed.*"]
    return out


def claims_md(report: Report, category: Cat, cites: Citations) -> List[str]:
    claims = report.claims_for(category)
    out: List[str] = []
    for name in competitor_names(report):
        mine = [c for c in claims if c.competitor == name]
        if mine:
            out += [f"### {name}", *[claim_line(c, cites) for c in mine], ""]
    return out


def insights_md(report: Report, cites: Citations) -> List[str]:
    out: List[str] = []
    for kind in InsightKind:
        items = [i for i in report.insights if i.kind is kind]
        if not items:
            continue
        out += [f"### {INSIGHT_HEADINGS[kind]}", ""]
        for item in items:
            out.append(f"- **{item.title}** ({evidence_label(item.evidence_type)}) {cites.cite(item.source_urls)}".rstrip())
            out.append(f"  - *Why:* {item.reasoning}")
        out.append("")
    return out


def sources_md(report: Report) -> List[str]:
    return [f"{i}. [{s.title}]({s.url}) - accessed {access_date(s)}" for i, s in enumerate(report.sources, start=1)]


def skipped_md(report: Report) -> List[str]:
    return [f"- {p.competitor}: {p.url} - {p.reason}" for p in report.skipped_pages]


def rejected_md(report: Report) -> List[str]:
    if not report.rejected_claims:
        return []
    return ["These statements were dropped because their quote could not be found on the cited page:", "",
            *[f"- {c.competitor}: {c.statement}" for c in report.rejected_claims]]


LEGEND = ("**How to read this report:** " + " · ".join(evidence_label(e) for e in EvidenceType)
          + ". Verified facts are quoted from the cited source. Inferences are our reasoning from facts. "
          "Hypotheses are ideas to test.")


def to_markdown(report: Report) -> str:
    req = report.request
    cites = Citations(report.sources)
    selected = set(req.categories)
    out: List[str] = [f"# Competitive Research Report: {req.product_name}", ""]

    if report.is_demo:
        out += [f"> **⚠️ {DEMO_LABEL}.** Every brand, price, quote and source in this report is "
                "invented to show what a report looks like.", ""]
    out += [f"Generated: {report.generated_at}", ""]

    out += ["## Research setup", "",
            f"- **Product:** {req.product_name} - {req.product_description}",
            f"- **Industry:** {req.industry}",
            f"- **Target customer:** {req.target_customer}",
            f"- **Objectives:** {req.objectives}",
            f"- **Competitors requested:** {', '.join(c.name for c in req.competitors)}",
            f"- **Categories:** {', '.join(c.value for c in req.categories)}", ""]
    out += [f"> {note}" for note in report.notes]
    out += ["", LEGEND, ""]

    def section(heading: str, lines: List[str]) -> None:
        if lines:
            out.extend([f"## {heading}", "", *lines, ""])

    if Cat.FEATURES in selected:
        section("Feature comparison", feature_table_md(report, cites))
    if Cat.PRICING in selected:
        section("Pricing comparison", pricing_table_md(report, cites))
    for category, heading in CLAIM_SECTIONS:
        if category in selected:
            section(heading, claims_md(report, category, cites))
    section("Insights", insights_md(report, cites))
    section("Sources", sources_md(report))
    section("Pages we could not use", skipped_md(report))
    section("Removed by fact-check", rejected_md(report))
    return "\n".join(out)


def _csv(header: List[str], rows: List[List[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def _status(report: Report) -> str:
    return DEMO_LABEL if report.is_demo else "Live research"


def claims_csv(report: Report) -> str:
    by_url = {s.url: s for s in report.sources}
    rows = []
    for c in report.claims:
        sources = [by_url[u] for u in c.source_urls if u in by_url]
        rows.append([_status(report), c.competitor, c.category.value, c.evidence_type.value, c.statement, c.quote,
                     " | ".join(s.title for s in sources), " | ".join(s.url for s in sources),
                     " | ".join(access_date(s) for s in sources)])
    return _csv(["data_status", "competitor", "category", "evidence_type", "statement", "quote",
                 "source_titles", "source_urls", "accessed_dates"], rows)


def features_csv(report: Report) -> str:
    names = competitor_names(report)
    rows = [[_status(report), row["Feature"], *[row.get(n, "") for n in names]] for row in feature_matrix(report)]
    return _csv(["data_status", "feature", *names], rows)


def pricing_csv(report: Report) -> str:
    by_url = {s.url: s for s in report.sources}
    rows = [[_status(report), p.competitor, p.plan, p.price, p.billing, p.notes, p.source_url,
             access_date(by_url[p.source_url]) if p.source_url in by_url else ""] for p in report.prices]
    return _csv(["data_status", "competitor", "plan", "price", "billing", "notes", "source_url", "accessed_date"], rows)

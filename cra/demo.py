"""Clearly labeled SAMPLE data, used until live research is configured.

Every brand, web page, price and quote below is invented. The web addresses use the
reserved "example.com" domain, so they can never be mistaken for real companies.
"""

from typing import List

from cra.models import (
    Claim,
    EvidenceType,
    FeatureEntry,
    Insight,
    InsightKind,
    PriceEntry,
    ResearchCategory as Cat,
    Source,
)

DEMO_LABEL = "DEMO DATA - NOT REAL RESEARCH"
DEMO_ACCESSED_AT = "2026-01-15T09:00:00Z"

A, B, C = "Demo Brand A", "Demo Brand B", "Demo Brand C"

_A_HOME = "https://demo-brand-a.example.com/"
_A_PRICING = "https://demo-brand-a.example.com/pricing"
_A_CHANGELOG = "https://demo-brand-a.example.com/changelog"
_B_HOME = "https://demo-brand-b.example.com/"
_B_PRICING = "https://demo-brand-b.example.com/pricing"
_B_REVIEWS = "https://reviews.example.com/demo-brand-b"
_C_HOME = "https://demo-brand-c.example.com/"
_C_BLOG = "https://demo-brand-c.example.com/blog/launch"
_C_REVIEWS = "https://reviews.example.com/demo-brand-c"


def _source(title: str, url: str, text: str) -> Source:
    return Source(title=f"[SAMPLE] {title}", url=url, accessed_at=DEMO_ACCESSED_AT,
                  excerpt=text[:200], text=text)


def demo_sources() -> List[Source]:
    return [
        _source("Demo Brand A - Home", _A_HOME,
                "Demo Brand A is the all-in-one workspace for fast-growing teams. "
                "Plan projects, track work and report to leadership in one place. "
                "Connect 200+ apps from our integrations marketplace."),
        _source("Demo Brand A - Pricing", _A_PRICING,
                "Starter: $0 for up to 5 users. Team: $12 per user / month, billed annually. "
                "Enterprise: contact sales. Single sign-on (SSO) is available on Enterprise only."),
        _source("Demo Brand A - Changelog", _A_CHANGELOG,
                "September 2025: we launched AI Summaries, which turns long project threads "
                "into a short status update. August 2025: new mobile app for Android."),
        _source("Demo Brand B - Home", _B_HOME,
                "Demo Brand B: project tracking built for regulated industries. "
                "SOC 2 Type II certified. SSO included on every plan. Open REST API."),
        _source("Demo Brand B - Pricing", _B_PRICING,
                "Business: $25 per user / month. Minimum 10 seats. All plans include SSO."),
        _source("Review site - Demo Brand B reviews", _B_REVIEWS,
                "\"Setup took our admin two weeks and we needed their support team.\" "
                "\"Very secure, but the interface feels dated.\" "
                "\"Reporting is powerful once configured.\""),
        _source("Demo Brand C - Home", _C_HOME,
                "Demo Brand C is the simplest task board for small teams. "
                "Free forever for teams of any size. Upgrade to Plus for automations."),
        _source("Demo Brand C - Launch blog post", _C_BLOG,
                "Today we are launching Plus, our first paid plan, at $6 per user / month. "
                "Plus adds automations and a mobile app."),
        _source("Review site - Demo Brand C reviews", _C_REVIEWS,
                "\"Great for small teams, but it gets slow with more than 1,000 tasks.\" "
                "\"No way to report progress to my manager without exporting to a spreadsheet.\" "
                "\"Love how easy it is to start.\""),
    ]


def demo_claims() -> List[Claim]:
    fact, inference = EvidenceType.FACT, EvidenceType.INFERENCE
    return [
        Claim(A, Cat.POSITIONING, "Positions itself as an all-in-one workspace for fast-growing teams.",
              fact, [_A_HOME], "the all-in-one workspace for fast-growing teams"),
        Claim(B, Cat.POSITIONING, "Positions itself around security and regulated industries.",
              fact, [_B_HOME], "project tracking built for regulated industries"),
        Claim(C, Cat.POSITIONING, "Positions itself as the simplest option for small teams.",
              fact, [_C_HOME], "the simplest task board for small teams"),
        Claim(A, Cat.LAUNCHES, "Launched AI Summaries (September 2025).",
              fact, [_A_CHANGELOG], "September 2025: we launched AI Summaries"),
        Claim(A, Cat.LAUNCHES, "Launched an Android mobile app (August 2025).",
              fact, [_A_CHANGELOG], "August 2025: new mobile app for Android"),
        Claim(C, Cat.LAUNCHES, "Launched Plus, its first paid plan, at $6 per user / month.",
              fact, [_C_BLOG], "launching Plus, our first paid plan, at $6 per user / month"),
        Claim(B, Cat.REVIEWS, "Reviewers report a slow, support-heavy setup.",
              fact, [_B_REVIEWS], "Setup took our admin two weeks and we needed their support team"),
        Claim(B, Cat.REVIEWS, "Reviewers describe the interface as dated.",
              fact, [_B_REVIEWS], "the interface feels dated"),
        Claim(C, Cat.REVIEWS, "Reviewers report slowdowns on large boards.",
              fact, [_C_REVIEWS], "it gets slow with more than 1,000 tasks"),
        Claim(C, Cat.REVIEWS, "Reviewers want built-in reporting for managers.",
              fact, [_C_REVIEWS], "No way to report progress to my manager"),
        Claim(A, Cat.FEATURES, "Integrations marketplace appears to be a key selling point.",
              inference, [_A_HOME]),
        Claim(B, Cat.GAPS, "Onboarding is likely Demo Brand B's biggest barrier for smaller customers.",
              inference, [_B_REVIEWS, _B_PRICING]),
        # Deliberately unsupported: the quote is NOT on the cited page, so the fact-checker removes it.
        Claim(A, Cat.PRICING, "Offers a 50% discount for nonprofits.",
              fact, [_A_PRICING], "50% off for nonprofits"),
    ]


def demo_features() -> List[FeatureEntry]:
    rows = [
        ("Single sign-on (SSO)", {A: ("Yes", _A_PRICING), B: ("Yes", _B_HOME), C: ("Not found", "")}),
        ("AI summaries", {A: ("Yes", _A_CHANGELOG), B: ("Not found", ""), C: ("Not found", "")}),
        ("Mobile app", {A: ("Yes", _A_CHANGELOG), B: ("Not found", ""), C: ("Yes", _C_BLOG)}),
        ("Public API", {A: ("Not found", ""), B: ("Yes", _B_HOME), C: ("Not found", "")}),
        ("Automations", {A: ("Not found", ""), B: ("Not found", ""), C: ("Yes", _C_BLOG)}),
        ("Integrations marketplace", {A: ("Yes", _A_HOME), B: ("Not found", ""), C: ("Not found", "")}),
    ]
    return [FeatureEntry(comp, feature, status, url)
            for feature, cells in rows for comp, (status, url) in cells.items()]


def demo_prices() -> List[PriceEntry]:
    return [
        PriceEntry(A, "Starter", "$0", "up to 5 users", _A_PRICING),
        PriceEntry(A, "Team", "$12", "per user / month", _A_PRICING, "Billed annually"),
        PriceEntry(A, "Enterprise", "Contact sales", "-", _A_PRICING, "Only plan with SSO"),
        PriceEntry(B, "Business", "$25", "per user / month", _B_PRICING, "Minimum 10 seats"),
        PriceEntry(C, "Free", "$0", "any team size", _C_HOME),
        PriceEntry(C, "Plus", "$6", "per user / month", _C_BLOG),
    ]


def demo_insights() -> List[Insight]:
    return [
        Insight(InsightKind.NEED, "Simple reporting for managers",
                "Demo Brand C reviewers ask for a way to report progress without spreadsheets, and "
                "Demo Brand B reviewers say its powerful reporting is hard to set up. Neither offers "
                "easy reporting for small teams.",
                EvidenceType.INFERENCE, [_C_REVIEWS, _B_REVIEWS]),
        Insight(InsightKind.STRENGTH, "Demo Brand B owns the security story",
                "It is the only sample competitor that states SOC 2 certification and includes SSO on every plan.",
                EvidenceType.FACT, [_B_HOME, _B_PRICING]),
        Insight(InsightKind.WEAKNESS, "Demo Brand A gates SSO behind Enterprise pricing",
                "SSO is listed as Enterprise-only, which may push security-conscious mid-size teams elsewhere.",
                EvidenceType.INFERENCE, [_A_PRICING]),
        Insight(InsightKind.WEAKNESS, "Demo Brand C struggles at scale",
                "Reviewers report slowdowns above 1,000 tasks, suggesting it may lose teams as they grow.",
                EvidenceType.INFERENCE, [_C_REVIEWS]),
        Insight(InsightKind.OPPORTUNITY, "A simple tool with built-in manager reporting and SSO included",
                "Combining Demo Brand C's ease of use with reporting and SSO could win growing teams that "
                "outgrow C but find A and B too expensive or complex. Test this with customer interviews "
                "before building.",
                EvidenceType.HYPOTHESIS, []),
    ]

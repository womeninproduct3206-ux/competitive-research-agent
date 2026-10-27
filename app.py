"""Competitive Research Agent - Streamlit web app.

Run locally with:  streamlit run app.py
"""

import hmac

import streamlit as st
from dotenv import load_dotenv

from cra.config import Settings, load_settings
from cra import report as rpt
from cra.demo import DEMO_LABEL
from cra.models import Report, ResearchCategory as Cat, ResearchRequest
from cra.pipeline import run_research
from cra.validation import MAX_COMPETITORS, CompetitorInput, FormInput, validate_form

st.set_page_config(page_title="Competitive Research Agent", page_icon="🔎", layout="wide")


def get_settings() -> Settings:
    load_dotenv()
    try:
        secrets = dict(st.secrets)
    except Exception:  # no secrets file - normal when running locally
        secrets = {}
    if secrets:
        return load_settings(secrets)
    return load_settings()


def check_password(settings: Settings) -> bool:
    """Show a password box when APP_PASSWORD is set. Returns True once unlocked."""
    if not settings.password_required or st.session_state.get("unlocked"):
        return True
    st.title("🔎 Competitive Research Agent")
    entered = st.text_input("Password", type="password")
    if entered:
        if hmac.compare_digest(entered, settings.app_password):
            st.session_state["unlocked"] = True
            st.rerun()
        st.error("That password is not correct. Please try again.")
    return False


EXAMPLE = {
    "product_name": "Example: My high-protein ice cream",
    "product_description": "Example: a low-sugar, high-protein ice cream sold online and in stores.",
    "industry": "Packaged foods / frozen desserts",
    "target_customer": "Health-conscious adults in Indian cities",
    "objectives": "How do these brands price and position their products? "
    "What do customers complain about? Where are the gaps we could fill?",
    "categories": list(Cat),
    "n_competitors": 3,
    "comp_name_0": "Get-A-Whey",
    "comp_name_1": "Go Zero",
    "comp_name_2": "Amul",
}


def load_example() -> None:
    for i in range(MAX_COMPETITORS):
        st.session_state[f"comp_urls_{i}"] = ""
        st.session_state[f"comp_name_{i}"] = ""
    st.session_state.update(EXAMPLE)


def setup_form() -> None:
    """The research setup form. Saves a valid ResearchRequest in the session."""
    st.session_state.setdefault("n_competitors", 2)
    st.session_state.setdefault("categories", list(Cat))
    st.subheader("1. Research setup")
    left, right = st.columns([3, 1])
    left.write("Tell us about your product, your competitors, and what you want to learn.")
    right.button("Fill in example", on_click=load_example, use_container_width=True,
                 help="Pre-fills the ice cream test case. Competitor web addresses are left for you to paste.")

    n = st.number_input("How many competitors?", min_value=1, max_value=MAX_COMPETITORS,
                        key="n_competitors")

    with st.form("setup"):
        st.markdown("**Your product**")
        c1, c2 = st.columns(2)
        c1.text_input("Product name", key="product_name")
        c2.text_input("Industry", key="industry", placeholder="e.g. B2B SaaS, HR software")
        st.text_area("Product description", key="product_description", height=80,
                     placeholder="What does your product do, and for whom?")
        st.text_input("Target customer", key="target_customer",
                      placeholder="e.g. Product teams at mid-size software companies")

        st.markdown("**Competitors**")
        st.caption(
            "Paste publicly accessible pages, one per line: home page, pricing, docs, changelog, blog, "
            "public review pages. Pages behind a login or paywall will be skipped."
        )
        for i in range(int(n)):
            a, b = st.columns([1, 2])
            a.text_input(f"Competitor {i + 1} name", key=f"comp_name_{i}")
            b.text_area(f"Competitor {i + 1} web pages", key=f"comp_urls_{i}", height=90,
                        placeholder="https://competitor.com\nhttps://competitor.com/pricing")

        st.markdown("**What do you want to learn?**")
        st.text_area("Research objectives", key="objectives", height=80,
                     placeholder="e.g. Why are we losing deals to Competitor X?")
        st.multiselect("Research categories", options=list(Cat),
                       format_func=lambda c: c.value, key="categories")
        submitted = st.form_submit_button("Save research setup", type="primary")

    if submitted:
        state = st.session_state
        form = FormInput(
            product_name=state.product_name,
            product_description=state.product_description,
            industry=state.industry,
            target_customer=state.target_customer,
            competitors=[CompetitorInput(state.get(f"comp_name_{i}", ""), state.get(f"comp_urls_{i}", ""))
                         for i in range(int(n))],
            objectives=state.objectives,
            categories=state.categories,
        )
        request, errors = validate_form(form)
        if errors:
            st.session_state.pop("request", None)
            st.error("A few things need fixing before research can start:\n\n"
                     + "\n".join(f"- {e}" for e in errors))
        else:
            st.session_state["request"] = request
            st.session_state.pop("report", None)  # an old report no longer matches the new setup


def show_request(request: ResearchRequest) -> None:
    st.success("Research setup saved.")
    with st.expander("Review your setup", expanded="report" not in st.session_state):
        st.markdown(f"**{request.product_name}** · {request.industry} · for {request.target_customer}")
        st.markdown(f"**Objectives:** {request.objectives}")
        st.markdown("**Categories:** " + ", ".join(c.value for c in request.categories))
        for comp in request.competitors:
            st.markdown(f"**{comp.name}** ({len(comp.urls)} page{'s' if len(comp.urls) != 1 else ''})")
            st.markdown("\n".join(f"- {u}" for u in comp.urls))


def run_and_store(request: ResearchRequest, live: bool) -> None:
    """Run research with a live progress bar, keeping any error readable."""
    bar = st.progress(0.0, text="Starting research...")
    try:
        report = run_research(request, progress=lambda f, msg: bar.progress(f, text=msg), live=live)
    except Exception as exc:  # show a helpful message instead of a crash screen
        bar.empty()
        st.error(f"Research could not be completed: {exc}\n\nYour setup is saved. "
                 "Please try **Run research** again in a minute.")
        return
    bar.empty()
    st.session_state["report"] = report


LIVE = "Live research"
SAMPLE = "Sample report (demo data)"


def research_step(request: ResearchRequest) -> None:
    st.subheader("2. Run research")
    mode = st.radio(
        "What kind of research?",
        [LIVE, SAMPLE],
        captions=[
            "Reads the public pages you listed. Free. Takes a few seconds per page because we "
            "wait politely between visits to the same website.",
            "Shows a made-up example report so you can see what the output looks like. No internet needed.",
        ],
        key="mode",
    )
    if mode == LIVE:
        pages = sum(len(c.urls) for c in request.competitors)
        st.caption(f"{pages} page{'s' if pages != 1 else ''} to read. AI analysis of the pages "
                   "arrives in Milestone 4, so for now a live report lists the sources collected.")
    label = "Rerun research" if "report" in st.session_state else "Run research"
    if st.button(label, type="primary", help="Collects sources, fact-checks findings and builds the report."):
        run_and_store(request, live=(mode == LIVE))


def show_md(lines: list, empty_message: str) -> None:
    if lines:
        st.markdown("\n".join(lines))
    else:
        st.info(empty_message)


def show_sources(report: Report) -> None:
    if not report.sources:
        st.info("No sources were collected.")
    for i, source in enumerate(report.sources, start=1):
        with st.expander(f"[{i}] {source.title} - accessed {rpt.access_date(source)}"):
            st.markdown(f"[{source.url}]({source.url})")
            st.caption(f"{len(source.text):,} characters of readable text collected. Preview:")
            st.text(source.excerpt)
    if report.skipped_pages:
        st.markdown("**Pages we could not use**")
        st.markdown("\n".join(rpt.skipped_md(report)))
        st.caption("We never get around logins, paywalls, CAPTCHAs or robots.txt rules. "
                   "If a page you need was skipped, try a different public page with the same information.")


def show_report(report: Report) -> None:
    st.subheader("3. Report")
    if report.is_demo:
        st.error(f"**⚠️ {DEMO_LABEL}.** This sample report uses invented brands, prices, quotes and "
                 "sources to show what a report looks like. It does not describe your competitors.")
    st.caption(f"Generated {report.generated_at} · {len(report.sources)} sources · "
               f"{len(report.skipped_pages)} pages skipped · "
               f"{len(report.claims)} findings kept · {len(report.rejected_claims)} removed by fact-check")
    for note in report.notes:
        st.info(note)
    st.markdown(rpt.LEGEND)

    slug = "demo-" if report.is_demo else ""
    d1, d2, d3, d4 = st.columns(4)
    d1.download_button("⬇️ Full report (Markdown)", rpt.to_markdown(report),
                       file_name=f"{slug}competitive-report.md", mime="text/markdown", use_container_width=True)
    d2.download_button("⬇️ Findings (CSV)", rpt.claims_csv(report),
                       file_name=f"{slug}findings.csv", mime="text/csv", use_container_width=True)
    d3.download_button("⬇️ Feature matrix (CSV)", rpt.features_csv(report),
                       file_name=f"{slug}feature-matrix.csv", mime="text/csv", use_container_width=True)
    d4.download_button("⬇️ Pricing (CSV)", rpt.pricing_csv(report),
                       file_name=f"{slug}pricing.csv", mime="text/csv", use_container_width=True)

    cites = rpt.Citations(report.sources)
    selected = set(report.request.categories)
    not_selected = "You didn't select this category in your research setup."
    tabs = st.tabs(["Insights", "Features", "Pricing", "Positioning", "Launches",
                    "Complaints", "Gaps", "Sources", "Fact-check"])
    with tabs[0]:
        show_md(rpt.insights_md(report, cites), "No insights could be supported by the sources.")
    with tabs[1]:
        if Cat.FEATURES in selected:
            show_md(rpt.feature_table_md(report, cites) + [""] + rpt.claims_md(report, Cat.FEATURES, cites),
                    "No feature information was found in the sources.")
        else:
            st.info(not_selected)
    with tabs[2]:
        if Cat.PRICING in selected:
            show_md(rpt.pricing_table_md(report, cites) + [""] + rpt.claims_md(report, Cat.PRICING, cites),
                    "No reliable pricing was published on the pages we read.")
        else:
            st.info(not_selected)
    for tab, category, empty in [
        (tabs[3], Cat.POSITIONING, "No positioning statements were found."),
        (tabs[4], Cat.LAUNCHES, "No recent launches were found in the sources."),
        (tabs[5], Cat.REVIEWS, "No customer complaints were found in publicly accessible sources."),
        (tabs[6], Cat.GAPS, "No product gaps were identified from the sources."),
    ]:
        with tab:
            if category in selected:
                show_md(rpt.claims_md(report, category, cites), empty)
            else:
                st.info(not_selected)
    with tabs[7]:
        show_sources(report)
    with tabs[8]:
        st.markdown("Every **verified fact** must quote text that really appears on the page it cites. "
                    "Anything that fails is removed and listed here, so nothing is hidden.")
        show_md(rpt.rejected_md(report), "All findings passed the fact-check.")


def main() -> None:
    settings = get_settings()
    if not check_password(settings):
        return

    st.title("🔎 Competitive Research Agent")
    st.caption("Evidence-backed competitive research for Product Managers.")

    if settings.live_mode:
        st.info(f"API key detected (model: `{settings.claude_model}`). Live research arrives in "
                "Milestones 3-4; until then reports use labeled sample data.")
    else:
        st.warning(
            "**Demo mode.** No API key is configured, so the app will only show clearly "
            "labeled sample data. Sample data is not real research."
        )

    setup_form()
    if "request" in st.session_state:
        show_request(st.session_state["request"])
        research_step(st.session_state["request"])
    if "report" in st.session_state:
        show_report(st.session_state["report"])


main()

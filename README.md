# Competitive Research Agent

An AI-assisted competitive research tool for Product Managers. You enter your product,
your competitors and their public web pages, and your research questions. The app
produces a structured report in which every claim links to the public source that
supports it.

> **Status: Milestone 3 (live page reading).** Choose **Live research** to read the real public
> pages you list (free, no API key). The report shows every page read, with its access date and a
> text preview, plus every page skipped and why. AI analysis of those pages arrives in Milestone 4.
> Choose **Sample report** to see a full example report built from clearly labeled invented data.

## Demo mode vs. live mode

| Mode | When | What you see |
|---|---|---|
| **Demo** | No `ANTHROPIC_API_KEY` set | Clearly labeled **sample data**. Not real research. |
| **Live** | `ANTHROPIC_API_KEY` set | Real analysis of the public pages you provide. |

## Run it on your computer

1. Install [Python 3.10+](https://www.python.org/downloads/).
2. Open a terminal in this folder and run:
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env             # then edit .env if you have an API key
   streamlit run app.py
   ```
3. Your browser opens at http://localhost:8501.

## Settings (secrets)

Settings are read from environment variables. **Never put keys in the code.**

| Name | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Turns on live AI analysis. Pay-as-you-go, billed separately from Claude Pro. |
| `CLAUDE_MODEL` | Model used for analysis (default `claude-opus-5-5`). |
| `APP_PASSWORD` | If set, users must enter this password to use the app. |

Locally they go in `.env`, which git ignores. On Streamlit Community Cloud they go in
the app's **Settings → Secrets**.

## Run the tests

```bash
pytest
```

## Project layout

```
app.py            Web interface (Streamlit)
cra/config.py     Reads settings and secrets
cra/models.py     Shared data shapes: requests, sources, claims
cra/validation.py Checks the setup form and explains problems in plain English
cra/pipeline.py   Runs a research job step by step, reporting progress
cra/fetcher.py    Reads public pages politely: robots.txt, rate limits, no logins/paywalls/CAPTCHAs
cra/demo.py       Clearly labeled sample data (invented brands on example.com)
cra/verification.py  Fact-checker: drops "facts" whose quote isn't on the cited page
cra/report.py     Builds the report sections, Markdown and CSV downloads
tests/            Automated tests
```

## Research principles

- Only publicly accessible pages are used. Logins, paywalls and CAPTCHAs are never bypassed.
- robots.txt is checked before every page (including after redirects), and pages it disallows
  are never downloaded.
- At least 2 seconds between requests to the same website, or longer if its robots.txt asks.
- The app identifies itself honestly (User-Agent `CompetitiveResearchAgent/0.1`).
- Private/internal network addresses are refused, so a hosted copy can't be used to probe them.
- A "verified fact" must quote text that really appears on the page it cites. Plain code (not AI)
  checks this, and anything that fails is removed and listed in the report's Fact-check tab.
- Facts, pricing, dates and quotes are never invented. Every claim is labeled
  **Verified fact**, **Inference** or **Hypothesis**.

# Competitive Research Agent

An AI-assisted competitive research tool for Product Managers. You enter your product,
your competitors and their public web pages, and your research questions. The app
produces a structured report in which every claim links to the public source that
supports it.

> **Status: Milestone 4 (AI analysis).** Live research reads the public pages you list, an AI
> service extracts findings, features, prices and insights, and plain code fact-checks every one
> against the page it cites before it reaches the report.

## Modes

| Mode | When | What you get |
|---|---|---|
| **Sample report** | Any time | A full example report built from clearly labeled **invented** brands. Not real research. |
| **Live research, no AI key** | No key configured | The public pages read (with access dates) and the pages skipped, with reasons. No findings. |
| **Live research with AI** | `GEMINI_API_KEY` (free) or `ANTHROPIC_API_KEY` (paid) set | Full fact-checked report from the real pages. |

## Choosing an AI service

| Service | Cost | Notes |
|---|---|---|
| **Google Gemini** (default) | Free tier available | Get a key at https://aistudio.google.com/apikey. On the free tier Google may use what you send (your product description and the page text) to improve its products, and daily limits are low. Don't enter confidential details. |
| **Anthropic Claude** | Pay as you go, roughly $1 per run on Opus 5.5 | Key from https://console.anthropic.com. Billed separately from a Claude Pro subscription. Set a monthly spend limit in the console. |

Switch with the `AI_PROVIDER` setting (`gemini` or `claude`). No code changes needed.

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
| `AI_PROVIDER` | `gemini` (default) or `claude` |
| `GEMINI_API_KEY` | Google Gemini key (free tier available) |
| `GEMINI_MODEL` | Gemini model (default `gemini-flash-latest`) |
| `ANTHROPIC_API_KEY` | Anthropic Claude key (paid) |
| `CLAUDE_MODEL` | Claude model (default `claude-opus-5-5`) |
| `APP_PASSWORD` | If set, users must enter this password to use the app |

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
cra/llm.py        Connects to Gemini or Claude behind one interface; plain-English errors
cra/analyzer.py   Asks the AI for findings in a strict format, then verifies quotes and prices
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
- The AI only sees pages the app actually read, must cite them by number, and must quote them
  word for word. Prices must appear in the quote with the exact same numbers.
- Facts, pricing, dates and quotes are never invented. Every claim is labeled
  **Verified fact**, **Inference** or **Hypothesis**.

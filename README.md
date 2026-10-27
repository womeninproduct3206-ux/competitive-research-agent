# Competitive Research Agent

An AI-assisted competitive research tool for Product Managers. You enter your product,
your competitors and their public web pages, and your research questions. The app
produces a structured report in which every claim links to the public source that
supports it.

> **Status: Milestone 1 (research setup form).** You can enter your product, competitors,
> their public web pages, objectives and categories. The form checks your input and
> explains anything that needs fixing. Running research arrives in Milestone 2.

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
tests/            Automated tests
```

## Research principles

- Only publicly accessible pages are used. Logins, paywalls and CAPTCHAs are never bypassed.
- robots.txt and rate limits are respected.
- Facts, pricing, dates and quotes are never invented. Every claim is labeled
  **Verified fact**, **Inference** or **Hypothesis**.

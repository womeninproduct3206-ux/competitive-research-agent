"""Competitive Research Agent - Streamlit web app.

Run locally with:  streamlit run app.py
"""

import hmac

import streamlit as st
from dotenv import load_dotenv

from cra.config import Settings, load_settings

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


def main() -> None:
    settings = get_settings()
    if not check_password(settings):
        return

    st.title("🔎 Competitive Research Agent")
    st.caption("Evidence-backed competitive research for Product Managers.")

    if settings.live_mode:
        st.success(f"Live mode: AI analysis is configured (model: `{settings.claude_model}`).")
    else:
        st.warning(
            "**Demo mode.** No API key is configured, so the app will only show clearly "
            "labeled sample data. Sample data is not real research."
        )

    st.info("The research setup form arrives in Milestone 1.")


main()

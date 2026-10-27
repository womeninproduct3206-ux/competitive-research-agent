"""App settings, read from environment variables (or Streamlit secrets when hosted).

Secrets are never written in the code. Locally they come from a `.env` file;
on Streamlit Community Cloud they come from the app's "Secrets" settings.
"""

import os
from dataclasses import dataclass
from typing import Mapping, Optional

DEFAULT_PROVIDER = "gemini"
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"
DEFAULT_MODEL = "claude-opus-5-5"
PROVIDERS = ("gemini", "claude")


@dataclass(frozen=True)
class Settings:
    ai_provider: str = DEFAULT_PROVIDER
    gemini_api_key: str = ""
    gemini_model: str = DEFAULT_GEMINI_MODEL
    anthropic_api_key: str = ""
    claude_model: str = DEFAULT_MODEL
    app_password: str = ""

    @property
    def live_mode(self) -> bool:
        """True when the chosen AI provider has a key, so real AI analysis can run."""
        if self.ai_provider == "claude":
            return bool(self.anthropic_api_key)
        return bool(self.gemini_api_key)

    @property
    def ai_label(self) -> str:
        if self.ai_provider == "claude":
            return f"Anthropic Claude ({self.claude_model})"
        return f"Google Gemini free tier ({self.gemini_model})"

    @property
    def password_required(self) -> bool:
        return bool(self.app_password)


def load_settings(source: Optional[Mapping[str, str]] = None) -> Settings:
    """Build Settings from a mapping of values (defaults to environment variables)."""
    if source is None:
        source = os.environ

    def get(name: str, default: str = "") -> str:
        return str(source.get(name, default) or default).strip()

    provider = get("AI_PROVIDER", DEFAULT_PROVIDER).lower()
    if provider not in PROVIDERS:
        provider = DEFAULT_PROVIDER
    return Settings(
        ai_provider=provider,
        gemini_api_key=get("GEMINI_API_KEY"),
        gemini_model=get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        anthropic_api_key=get("ANTHROPIC_API_KEY"),
        claude_model=get("CLAUDE_MODEL", DEFAULT_MODEL),
        app_password=get("APP_PASSWORD"),
    )

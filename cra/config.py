"""App settings, read from environment variables (or Streamlit secrets when hosted).

Secrets are never written in the code. Locally they come from a `.env` file;
on Streamlit Community Cloud they come from the app's "Secrets" settings.
"""

import os
from dataclasses import dataclass
from typing import Mapping, Optional

DEFAULT_MODEL = "claude-opus-5-5"


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str = ""
    claude_model: str = DEFAULT_MODEL
    app_password: str = ""

    @property
    def live_mode(self) -> bool:
        """True when an API key is configured, so real AI analysis can run."""
        return bool(self.anthropic_api_key)

    @property
    def password_required(self) -> bool:
        return bool(self.app_password)


def load_settings(source: Optional[Mapping[str, str]] = None) -> Settings:
    """Build Settings from a mapping of values (defaults to environment variables)."""
    if source is None:
        source = os.environ

    def get(name: str, default: str = "") -> str:
        return str(source.get(name, default) or default).strip()

    return Settings(
        anthropic_api_key=get("ANTHROPIC_API_KEY"),
        claude_model=get("CLAUDE_MODEL", DEFAULT_MODEL),
        app_password=get("APP_PASSWORD"),
    )

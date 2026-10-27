"""Connects to an AI service (Google Gemini or Anthropic Claude) behind one simple interface.

The rest of the app only calls `generate_json(system, prompt, schema)`, so switching providers
is a settings change, not a code change.
"""

import json
from typing import Any, Dict, Optional, Protocol

from cra.config import Settings

MAX_OUTPUT_TOKENS = 16000


class LLMError(Exception):
    """A problem talking to the AI service, with a message written for the user."""


class LLMClient(Protocol):
    label: str  # e.g. "Google Gemini (gemini-flash-latest)"

    def generate_json(self, system: str, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        ...


def _parse_json(text: str, service: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LLMError(f"{service} returned an answer we couldn't read. Please run the research again.") from exc


def _status_message(service: str, status: Optional[int], free_tier: bool = False) -> str:
    if status in (401, 403):
        return f"{service} rejected the API key. Please check the key in your settings or secrets."
    if status == 404:
        return f"{service} doesn't recognise the model name in your settings. Please check it."
    if status == 429:
        limit = "the free tier's daily or per-minute limit" if free_tier else "the account's rate or spend limit"
        return f"{service} says we've hit {limit}. Please wait and try again later."
    if status == 400:
        return f"{service} couldn't process the request (it may be too large). Try fewer pages."
    return f"{service} is temporarily unavailable. Please try again in a few minutes."


class GeminiClient:
    def __init__(self, api_key: str, model: str, client: Any = None):
        from google import genai

        self.model = model
        self.label = f"Google Gemini ({model})"
        self._client = client or genai.Client(api_key=api_key)

    def generate_json(self, system: str, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        from google.genai import errors, types

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_json_schema=schema,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                ),
            )
        except errors.APIError as exc:
            raise LLMError(_status_message("Google Gemini", exc.code, free_tier=True)) from exc
        except Exception as exc:  # network problems and similar
            raise LLMError("We couldn't reach Google Gemini. Please check the internet connection.") from exc
        return _parse_json(response.text, "Google Gemini")


class ClaudeClient:
    def __init__(self, api_key: str, model: str, client: Any = None):
        import anthropic

        self.model = model
        self.label = f"Anthropic Claude ({model})"
        self._client = client or anthropic.Anthropic(api_key=api_key)

    def generate_json(self, system: str, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        import anthropic

        try:
            response = self._client.beta.messages.create(
                model=self.model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
                # If a safety check declines the request, Anthropic retries it on a suitable model.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.APIStatusError as exc:
            raise LLMError(_status_message("Anthropic Claude", exc.status_code)) from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("We couldn't reach Anthropic Claude. Please check the internet connection.") from exc

        if response.stop_reason == "refusal":
            raise LLMError("Claude declined to analyse these pages. Try removing unusual pages and run again.")
        if response.stop_reason == "max_tokens":
            raise LLMError("Claude's answer was too long and got cut off. Try fewer pages or competitors.")
        text = next((b.text for b in response.content if b.type == "text"), "")
        return _parse_json(text, "Anthropic Claude")


def make_client(settings: Settings) -> Optional[LLMClient]:
    """The AI client for the configured provider, or None if no key is set."""
    if settings.ai_provider == "claude" and settings.anthropic_api_key:
        return ClaudeClient(settings.anthropic_api_key, settings.claude_model)
    if settings.ai_provider == "gemini" and settings.gemini_api_key:
        return GeminiClient(settings.gemini_api_key, settings.gemini_model)
    return None

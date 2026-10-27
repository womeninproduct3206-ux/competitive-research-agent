from types import SimpleNamespace

import anthropic
import httpx2
import pytest
from google.genai import errors as genai_errors

from cra.config import load_settings
from cra.llm import ClaudeClient, GeminiClient, LLMError, make_client


class FakeGeminiModels:
    def __init__(self, text=None, error=None):
        self.text, self.error, self.kwargs = text, error, None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.text)


def gemini(text=None, error=None):
    models = FakeGeminiModels(text, error)
    return GeminiClient("key", "gemini-test", client=SimpleNamespace(models=models)), models


def test_gemini_requests_json_with_schema():
    client, models = gemini('{"findings": []}')
    assert client.generate_json("sys", "prompt", {"type": "object"}) == {"findings": []}
    config = models.kwargs["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == {"type": "object"}
    assert config.system_instruction == "sys"


@pytest.mark.parametrize("code, words", [(429, "free tier"), (403, "API key"), (404, "model name"), (503, "temporarily")])
def test_gemini_errors_become_plain_english(code, words):
    client, _ = gemini(error=genai_errors.APIError(code, {"error": {"message": "x"}}))
    with pytest.raises(LLMError, match=words):
        client.generate_json("s", "p", {})


def test_unreadable_answer_is_explained():
    client, _ = gemini("not json")
    with pytest.raises(LLMError, match="couldn't read"):
        client.generate_json("s", "p", {})


class FakeClaudeMessages:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.kwargs = response, error, None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


def claude(response=None, error=None):
    messages = FakeClaudeMessages(response, error)
    fake = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return ClaudeClient("key", "claude-opus-5-5", client=fake), messages


def test_claude_uses_structured_output_and_fallbacks():
    response = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text='{"a": 1}')])
    client, messages = claude(response)
    assert client.generate_json("sys", "prompt", {"type": "object"}) == {"a": 1}
    assert messages.kwargs["output_config"]["format"] == {"type": "json_schema", "schema": {"type": "object"}}
    assert messages.kwargs["fallbacks"] == "default"
    assert messages.kwargs["model"] == "claude-opus-5-5"


@pytest.mark.parametrize("stop, words", [("refusal", "declined"), ("max_tokens", "too long")])
def test_claude_stop_reasons_are_explained(stop, words):
    client, _ = claude(SimpleNamespace(stop_reason=stop, content=[]))
    with pytest.raises(LLMError, match=words):
        client.generate_json("s", "p", {})


def test_claude_rate_limit_is_explained():
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    error = anthropic.RateLimitError("slow down", response=httpx2.Response(429, request=request), body=None)
    client, _ = claude(error=error)
    with pytest.raises(LLMError, match="rate or spend limit"):
        client.generate_json("s", "p", {})


def test_make_client_picks_provider_from_settings():
    assert make_client(load_settings({})) is None
    assert isinstance(make_client(load_settings({"GEMINI_API_KEY": "g"})), GeminiClient)
    assert isinstance(make_client(load_settings({"AI_PROVIDER": "claude", "ANTHROPIC_API_KEY": "a"})), ClaudeClient)

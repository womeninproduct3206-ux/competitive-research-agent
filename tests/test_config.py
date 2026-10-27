from cra.config import DEFAULT_GEMINI_MODEL, DEFAULT_MODEL, load_settings


def test_demo_mode_when_no_api_key():
    settings = load_settings({})
    assert settings.live_mode is False
    assert settings.ai_provider == "gemini"
    assert settings.gemini_model == DEFAULT_GEMINI_MODEL
    assert settings.claude_model == DEFAULT_MODEL
    assert settings.password_required is False


def test_gemini_is_default_provider():
    settings = load_settings({"GEMINI_API_KEY": " g-key ", "APP_PASSWORD": "pw"})
    assert settings.live_mode is True
    assert settings.gemini_api_key == "g-key"
    assert "Gemini" in settings.ai_label
    assert settings.password_required is True


def test_claude_needs_its_own_key():
    assert load_settings({"AI_PROVIDER": "claude", "GEMINI_API_KEY": "g"}).live_mode is False
    settings = load_settings({"AI_PROVIDER": "Claude", "ANTHROPIC_API_KEY": "sk"})
    assert settings.live_mode is True and "Claude" in settings.ai_label


def test_unknown_provider_and_blank_model_fall_back_to_defaults():
    settings = load_settings({"AI_PROVIDER": "other", "CLAUDE_MODEL": ""})
    assert settings.ai_provider == "gemini"
    assert settings.claude_model == DEFAULT_MODEL

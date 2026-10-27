from cra.config import DEFAULT_MODEL, load_settings


def test_demo_mode_when_no_api_key():
    settings = load_settings({})
    assert settings.live_mode is False
    assert settings.claude_model == DEFAULT_MODEL
    assert settings.password_required is False


def test_live_mode_and_password_when_configured():
    settings = load_settings({"ANTHROPIC_API_KEY": " sk-test ", "APP_PASSWORD": "pw"})
    assert settings.live_mode is True
    assert settings.anthropic_api_key == "sk-test"
    assert settings.password_required is True


def test_blank_model_falls_back_to_default():
    assert load_settings({"CLAUDE_MODEL": ""}).claude_model == DEFAULT_MODEL

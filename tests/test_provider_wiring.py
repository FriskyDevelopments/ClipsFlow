from config.settings import Settings
from main import build_registry


def test_unknown_provider_config_fails_fast(monkeypatch):
    monkeypatch.setenv("CLIP_PROVIDER", "unknown")
    settings = Settings()
    try:
        build_registry(settings)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Unknown provider" in str(exc)


def test_clip_provider_is_used(monkeypatch):
    monkeypatch.setenv("CLIP_PROVIDER", "youtube")
    settings = Settings()
    registry = build_registry(settings)
    assert registry.enabled_provider_names == ["youtube"]


def test_disabled_provider_is_not_used(monkeypatch):
    monkeypatch.setenv("CLIP_PROVIDER", "youtube")
    settings = Settings()
    registry = build_registry(settings)
    assert registry.find("https://x.com/a/status/1") is None
    _, result = registry.validate_url("https://x.com/a/status/1")
    assert result is not None
    assert "disabled" in result.rejection_message.lower() or "unsupported" in result.rejection_message.lower()

"""
tests.test_settings – Unit tests for the Settings class.

Covers the changes introduced in this PR:
- clip_provider field (replaces enabled_providers)
- simplified validate() that checks TELEGRAM_BOT_TOKEN and youtube key
- removed required_secrets / enabled_providers fields
- simplified app_env handling (no dev/prod aliases)
"""

from __future__ import annotations

import os

import pytest

from config.settings import Settings, get_settings

@pytest.fixture(autouse=True)
def _set_pyrogram_env_vars(monkeypatch):
    """Automatically set Pyrogram API ID and Hash for all tests to pass base validation."""
    monkeypatch.setenv("TELEGRAM_API_ID", "123456")
    monkeypatch.setenv("TELEGRAM_API_HASH", "mocked_hash")


class TestSettingsDefaults:
    """Settings loaded without any env overrides should use documented defaults."""

    def test_clip_provider_defaults_to_mock(self, monkeypatch):
        monkeypatch.delenv("CLIP_PROVIDER", raising=False)
        s = Settings()
        assert s.clip_provider == "mock"

    def test_clip_provider_lowercased(self, monkeypatch):
        monkeypatch.setenv("CLIP_PROVIDER", "MOCK")
        s = Settings()
        assert s.clip_provider == "mock"

    def test_youtube_api_key_defaults_to_empty(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        s = Settings()
        assert s.youtube_api_key == ""

    def test_app_env_defaults_to_development(self, monkeypatch):
        monkeypatch.delenv("APP_ENV", raising=False)
        s = Settings()
        assert s.app_env == "development"

    def test_log_level_defaults_to_info(self, monkeypatch):
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        s = Settings()
        assert s.log_level == "INFO"

    def test_telegram_bot_token_defaults_to_empty(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        s = Settings()
        assert s.telegram_bot_token == ""

    def test_clip_allowed_media_types_defaults_to_video(self, monkeypatch):
        monkeypatch.delenv("CLIP_ALLOWED_MEDIA_TYPES", raising=False)
        s = Settings()
        assert s.clip_allowed_media_types == ["video"]


class TestSettingsClipProvider:
    """clip_provider env var is read and stored correctly."""

    def test_clip_provider_youtube(self, monkeypatch):
        monkeypatch.setenv("CLIP_PROVIDER", "youtube")
        s = Settings()
        assert s.clip_provider == "youtube"

    def test_clip_provider_youtube_uppercase_normalized(self, monkeypatch):
        monkeypatch.setenv("CLIP_PROVIDER", "YouTube")
        s = Settings()
        assert s.clip_provider == "youtube"

    def test_clip_provider_mock_explicit(self, monkeypatch):
        monkeypatch.setenv("CLIP_PROVIDER", "mock")
        s = Settings()
        assert s.clip_provider == "mock"


class TestSettingsAllowedMediaTypes:
    """CLIP_ALLOWED_MEDIA_TYPES is parsed as a comma-separated list."""

    def test_single_type(self, monkeypatch):
        monkeypatch.setenv("CLIP_ALLOWED_MEDIA_TYPES", "video")
        s = Settings()
        assert s.clip_allowed_media_types == ["video"]

    def test_multiple_types(self, monkeypatch):
        monkeypatch.setenv("CLIP_ALLOWED_MEDIA_TYPES", "video,audio")
        s = Settings()
        assert s.clip_allowed_media_types == ["video", "audio"]

    def test_whitespace_stripped(self, monkeypatch):
        monkeypatch.setenv("CLIP_ALLOWED_MEDIA_TYPES", " video , audio ")
        s = Settings()
        assert s.clip_allowed_media_types == ["video", "audio"]

    def test_empty_items_excluded(self, monkeypatch):
        monkeypatch.setenv("CLIP_ALLOWED_MEDIA_TYPES", "video,,audio")
        s = Settings()
        assert s.clip_allowed_media_types == ["video", "audio"]


class TestSettingsAppEnv:
    """APP_ENV is stored as-is (lowercased), no dev/prod alias expansion."""

    def test_production(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        s = Settings()
        assert s.app_env == "production"

    def test_development(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "development")
        s = Settings()
        assert s.app_env == "development"

    def test_app_env_lowercased(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "DEVELOPMENT")
        s = Settings()
        assert s.app_env == "development"

    def test_dev_alias_not_expanded(self, monkeypatch):
        """'dev' is NOT an alias for 'development' in the new simplified version."""
        monkeypatch.setenv("APP_ENV", "dev")
        s = Settings()
        # Stored as-is (lowercased); no expansion to 'development'
        assert s.app_env == "dev"

    def test_prod_alias_not_expanded(self, monkeypatch):
        """'prod' is NOT an alias for 'production' in the new simplified version."""
        monkeypatch.setenv("APP_ENV", "prod")
        s = Settings()
        # Stored as-is (lowercased); no expansion to 'production'
        assert s.app_env == "prod"


class TestSettingsIsEnvironmentProperties:
    """is_development and is_production properties reflect app_env."""

    def test_is_development_when_development(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "development")
        s = Settings()
        assert s.is_development is True
        assert s.is_production is False

    def test_is_production_when_production(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        s = Settings()
        assert s.is_production is True
        assert s.is_development is False

    def test_neither_for_unknown_env(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "staging")
        s = Settings()
        assert s.is_development is False
        assert s.is_production is False


class TestSettingsValidate:
    """validate() enforces only the new simplified rules."""

    def test_raises_when_telegram_bot_token_missing(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        s = Settings()
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            s.validate()

    def test_raises_when_telegram_bot_token_empty_string(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
        s = Settings()
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            s.validate()

    def test_passes_when_telegram_bot_token_set_with_mock_provider(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-abc")
        monkeypatch.setenv("CLIP_PROVIDER", "mock")
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        s = Settings()
        s.validate()  # must not raise

    def test_raises_when_youtube_provider_without_api_key(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-abc")
        monkeypatch.setenv("CLIP_PROVIDER", "youtube")
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        s = Settings()
        s.validate()  # must not raise

    def test_raises_when_youtube_provider_with_empty_api_key(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-abc")
        monkeypatch.setenv("CLIP_PROVIDER", "youtube")
        monkeypatch.setenv("YOUTUBE_API_KEY", "")
        s = Settings()
        s.validate()  # must not raise

    def test_passes_when_youtube_provider_with_api_key(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-abc")
        monkeypatch.setenv("CLIP_PROVIDER", "youtube")
        monkeypatch.setenv("YOUTUBE_API_KEY", "fake-yt-api-key")
        s = Settings()
        s.validate()  # must not raise

    def test_youtube_key_not_required_for_mock_provider(self, monkeypatch):
        """YOUTUBE_API_KEY should be irrelevant when CLIP_PROVIDER=mock."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-abc")
        monkeypatch.setenv("CLIP_PROVIDER", "mock")
        monkeypatch.setenv("YOUTUBE_API_KEY", "")
        s = Settings()
        s.validate()  # must not raise

    def test_validate_error_message_mentions_env_example(self, monkeypatch):
        """Error message for missing token should guide user to .env.example."""
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        s = Settings()
        with pytest.raises(ValueError, match=".env.example"):
            s.validate()

    def test_validate_error_message_mentions_clip_provider(self, monkeypatch):
        """Error message for missing YouTube key should mention CLIP_PROVIDER."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-abc")
        monkeypatch.setenv("CLIP_PROVIDER", "youtube")
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        s = Settings()
        s.validate()  # must not raise


class TestSettingsRemovedFields:
    """Fields removed in this PR must not be present on the Settings object."""

    def test_no_enabled_providers_attribute(self, monkeypatch):
        s = Settings()
        assert not hasattr(s, "enabled_providers"), (
            "enabled_providers was removed in this PR and must not be on Settings"
        )

    def test_no_required_secrets_attribute(self, monkeypatch):
        s = Settings()
        assert not hasattr(s, "required_secrets"), (
            "required_secrets was removed in this PR and must not be on Settings"
        )


class TestGetSettingsCache:
    """get_settings() returns a cached singleton; cache_clear() resets it."""

    def test_same_instance_returned_twice(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
        get_settings.cache_clear()
        a = get_settings()
        b = get_settings()
        assert a is b

    def test_cache_clear_returns_fresh_instance(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok1")
        get_settings.cache_clear()
        a = get_settings()
        get_settings.cache_clear()
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok2")
        b = get_settings()
        assert a is not b
        assert b.telegram_bot_token == "tok2"
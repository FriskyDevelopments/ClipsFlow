import pytest

from providers.direct import DirectProvider
from providers.instagram import InstagramProvider
from providers.registry import ProviderRegistry
from providers.tiktok import TikTokProvider
from providers.x_provider import XProvider
from providers.youtube import YouTubeProvider


@pytest.fixture
def full_registry():
    return ProviderRegistry([
        DirectProvider(),
        YouTubeProvider(),
        TikTokProvider(),
        InstagramProvider(),
        XProvider(),
    ])


def test_direct_url_routes_to_direct(full_registry):
    provider = full_registry.find("https://cdn.example.com/clip.mp4")
    assert provider is not None
    assert provider.name == "direct"


def test_youtube_shorts_routes_to_youtube(full_registry):
    provider = full_registry.find("https://www.youtube.com/shorts/abc123xyz09")
    assert provider is not None
    assert provider.name == "youtube"


def test_tiktok_routes_to_tiktok(full_registry):
    provider = full_registry.find("https://www.tiktok.com/@foo/video/123")
    assert provider is not None
    assert provider.name == "tiktok"


def test_instagram_reels_route_to_instagram(full_registry):
    provider = full_registry.find("https://www.instagram.com/reel/C0deABC/")
    assert provider is not None
    assert provider.name == "instagram"


def test_x_and_twitter_route_to_x(full_registry):
    p1 = full_registry.find("https://x.com/user/status/12")
    p2 = full_registry.find("https://twitter.com/user/status/12")
    assert p1 and p1.name == "x"
    assert p2 and p2.name == "x"


def test_validate_url_disabled_provider_message():
    registry = ProviderRegistry([YouTubeProvider()])
    _, result = registry.validate_url("https://www.tiktok.com/@foo/video/123")
    assert result is not None
    assert "disabled" in result.rejection_message.lower()
    assert "tiktok" in result.rejection_message.lower()


def test_validate_url_unsupported_source_message_lists_enabled():
    registry = ProviderRegistry([YouTubeProvider()])
    _, result = registry.validate_url("https://vimeo.com/123")
    assert result is not None
    assert "enabled providers: youtube" in result.rejection_message.lower()


def test_validate_url_normalizes_schemaless_input():
    registry = ProviderRegistry([YouTubeProvider()])
    normalized_url, result = registry.validate_url("youtube.com/watch?v=abc123")
    assert result is None
    assert normalized_url == "https://youtube.com/watch?v=abc123"


def test_validate_url_invalid_message_is_user_friendly():
    registry = ProviderRegistry([YouTubeProvider()])
    normalized_url, result = registry.validate_url("not a url")
    assert normalized_url == "not a url"
    assert result is not None
    assert "provide a valid video url" in result.rejection_message.lower()

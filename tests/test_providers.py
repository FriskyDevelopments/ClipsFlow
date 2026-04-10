import pytest

from providers.base import is_valid_url
from providers.direct import DirectProvider
from providers.instagram import InstagramProvider
from providers.tiktok import TikTokProvider
from providers.x_provider import XProvider
from providers.youtube import YouTubeProvider


def test_valid_url_accepts_optional_scheme():
    assert is_valid_url("https://example.com/a.mp4")
    assert is_valid_url("example.com/a.mp4")
    assert not is_valid_url("notaurl")


def test_direct_provider_can_handle_media_extensions():
    p = DirectProvider()
    assert p.can_handle("https://cdn.example.com/a.mp4")
    assert not p.can_handle("https://example.com/watch/123")


@pytest.mark.parametrize(
    "provider,url",
    [
        (YouTubeProvider(), "https://youtube.com/watch?v=abc"),
        (YouTubeProvider(), "https://youtu.be/abc"),
        (TikTokProvider(), "https://www.tiktok.com/@a/video/1"),
        (InstagramProvider(), "https://www.instagram.com/reel/ABC/"),
        (XProvider(), "https://x.com/user/status/1"),
        (XProvider(), "https://twitter.com/user/status/1"),
    ],
)
def test_provider_can_handle_domains(provider, url):
    assert provider.can_handle(url)

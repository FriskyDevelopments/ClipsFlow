import pytest

from core.media_normalization import (
    normalize_media_extension,
    normalized_media_descriptor,
    resolve_video_mime,
)
from providers.direct import DirectProvider
from providers.instagram import InstagramProvider
from providers.tiktok import TikTokProvider
from providers.youtube import YouTubeProvider


@pytest.mark.parametrize(
    "raw,expected",
    [
        (".WEBM", ".webm"),
        (".WebM", ".webm"),
        (" Mp4 ", ".mp4"),
        ("", ".mp4"),
    ],
)
def test_normalize_media_extension_common_cases(raw, expected):
    assert normalize_media_extension(raw) == expected


def test_resolve_video_mime_is_canonical():
    assert resolve_video_mime(".WEBM") == "video/webm"
    assert resolve_video_mime("video/x-m4v") == "video/mp4"
    assert resolve_video_mime("unknown") == "video/mp4"


async def test_direct_provider_missing_extension_falls_back_to_mp4():
    candidate = await DirectProvider().resolve("https://cdn.example.com/media")
    assert candidate.media_type == "video/mp4"
    assert candidate.extra["normalized_extension"] == ".mp4"


@pytest.mark.parametrize(
    "provider,url,expected_subtype",
    [
        (YouTubeProvider(), "https://youtube.com/shorts/abc", "short"),
        (TikTokProvider(), "https://www.tiktok.com/@foo/video/123", "short"),
        (InstagramProvider(), "https://www.instagram.com/reel/abc/", "reel"),
    ],
)
async def test_ytdlp_providers_normalize_ext_and_mime_consistently(monkeypatch, provider, url, expected_subtype):
    class _FakeYDL:
        def __init__(self, _opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url, download=False):
            assert download is False
            return {
                "id": "abc123",
                "url": "https://media.example.com/clip.WEBM",
                "ext": " WEBM ",
                "webpage_url": _url,
                "title": "Clip",
                "extractor": "test",
            }

    monkeypatch.setattr("providers.ytdlp_generic.YoutubeDL", _FakeYDL)

    candidate = await provider.resolve(url)
    assert candidate is not None
    assert candidate.extra.get("subtype", "post") == expected_subtype
    assert candidate.media_type == "video/webm"
    assert candidate.extra["normalized_extension"] == ".webm"
    assert candidate.extra["stable_name"].endswith(".webm")


async def test_ytdlp_direct_metadata_media_type_matches_ext_fallback(monkeypatch):
    class _FakeYDL:
        payload = {
            "id": "same",
            "url": "https://media.example.com/clip",
            "ext": " WEBM ",
            "title": "Clip",
            "extractor": "test",
        }

        def __init__(self, _opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url, download=False):
            assert download is False
            return self.payload

    monkeypatch.setattr("providers.ytdlp_generic.YoutubeDL", _FakeYDL)
    provider = YouTubeProvider()

    ext_candidate = await provider.resolve("https://youtube.com/watch?v=one")

    _FakeYDL.payload = {
        "id": "same",
        "url": "https://media.example.com/clip",
        "media_type": " video/webm ",
        "title": "Clip",
        "extractor": "test",
    }
    mime_candidate = await provider.resolve("https://youtube.com/watch?v=two")

    assert ext_candidate.media_type == mime_candidate.media_type == "video/webm"
    assert ext_candidate.extra["normalized_extension"] == mime_candidate.extra["normalized_extension"] == ".webm"


def test_stable_descriptor_does_not_drift_by_case():
    upper = normalized_media_descriptor(ext=".WEBM")
    lower = normalized_media_descriptor(ext=".webm")
    assert upper == lower

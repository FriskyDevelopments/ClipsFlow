import base64
import os

import pytest
from yt_dlp.utils import DownloadError, YoutubeDLError

from core.media_normalization import (
    normalize_media_extension,
    normalized_media_descriptor,
    resolve_video_mime,
)
from providers.base import ProviderError
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


async def test_ytdlp_provider_uses_configured_cookiefile(monkeypatch, tmp_path):
    cookiefile = tmp_path / "youtube-cookies.txt"
    cookiefile.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    seen_opts = {}

    class _FakeYDL:
        def __init__(self, opts):
            seen_opts.update(opts)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url, download=False):
            assert download is False
            return {
                "id": "cookie",
                "url": "https://media.example.com/clip.mp4",
                "ext": "mp4",
                "title": "Cookie Clip",
            }

    monkeypatch.setenv("YTDLP_COOKIE_FILE", str(cookiefile))
    monkeypatch.setattr("providers.ytdlp_generic.YoutubeDL", _FakeYDL)

    await YouTubeProvider().resolve("https://youtube.com/watch?v=cookie")

    assert seen_opts["cookiefile"] == str(cookiefile)


async def test_ytdlp_provider_writes_base64_cookies_to_private_file(monkeypatch, tmp_path):
    cookie_data = b"# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tFALSE\t0\tSID\tabc\n"
    seen_opts = {}

    class _FakeYDL:
        def __init__(self, opts):
            seen_opts.update(opts)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url, download=False):
            assert download is False
            return {
                "id": "b64",
                "url": "https://media.example.com/clip.mp4",
                "ext": "mp4",
                "title": "Cookie Clip",
            }

    monkeypatch.setenv("DOWNLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("YTDLP_COOKIES_B64", base64.b64encode(cookie_data).decode("ascii"))
    monkeypatch.setattr("providers.ytdlp_generic.YoutubeDL", _FakeYDL)

    await YouTubeProvider().resolve("https://youtube.com/watch?v=b64")

    cookiefile = seen_opts["cookiefile"]
    assert os.path.dirname(cookiefile) == str(tmp_path)
    assert os.stat(cookiefile).st_mode & 0o777 == 0o600
    assert open(cookiefile, "rb").read() == cookie_data


async def test_ytdlp_bot_check_is_retryable_before_generic_sign_in(monkeypatch):
    class _FakeYDL:
        def __init__(self, _opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url, download=False):
            raise DownloadError("Sign in to confirm you're not a bot")

    monkeypatch.setattr("providers.ytdlp_generic.YoutubeDL", _FakeYDL)

    with pytest.raises(ProviderError) as exc_info:
        await YouTubeProvider().resolve("https://youtube.com/watch?v=botcheck")

    assert exc_info.value.retryable is True
    assert "bot-protection" in str(exc_info.value)


async def test_ytdlp_unsupported_impersonation_falls_back(monkeypatch):
    seen_opts = []

    class _FakeYDL:
        def __init__(self, opts):
            seen_opts.append(dict(opts))
            if opts.get("impersonate"):
                raise YoutubeDLError('Impersonate target "chrome" is not available')

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url, download=False):
            assert download is False
            return {
                "id": "fallback",
                "url": "https://media.example.com/clip.mp4",
                "ext": "mp4",
                "title": "Fallback Clip",
            }

    monkeypatch.setenv("YTDLP_IMPERSONATE", "chrome")
    monkeypatch.setattr("providers.ytdlp_generic.YoutubeDL", _FakeYDL)

    candidate = await YouTubeProvider().resolve("https://youtube.com/watch?v=fallback")

    assert candidate.title == "Fallback Clip"
    assert seen_opts[0]["impersonate"] == "chrome"
    assert "impersonate" not in seen_opts[1]


def test_stable_descriptor_does_not_drift_by_case():
    upper = normalized_media_descriptor(ext=".WEBM")
    lower = normalized_media_descriptor(ext=".webm")
    assert upper == lower

import pytest
from core.source_routing import (
    classify_url,
    provider_candidates_for_url,
    is_direct_media_url,
    parse_domain,
    RouteDecision
)

def test_parse_domain():
    assert parse_domain("https://example.com/path?q=1") == "example.com"
    assert parse_domain("http://WWW.EXAMPLE.COM/") == "www.example.com"
    assert parse_domain("example.com") == "example.com"
    assert parse_domain("https://youtube.com/watch?v=123") == "youtube.com"

def test_is_direct_media_url():
    assert is_direct_media_url("https://example.com/video.mp4") is True
    assert is_direct_media_url("http://example.com/audio.mp3") is True
    assert is_direct_media_url("https://example.com/movie.MOV") is True  # Should ignore case internally
    assert is_direct_media_url("https://example.com/page.html") is False
    assert is_direct_media_url("https://example.com/video.mp4?test=1") is True
    assert is_direct_media_url("ftp://example.com/video.mp4") is False

def test_provider_candidates_for_url():
    assert provider_candidates_for_url("https://youtube.com/watch?v=123") == ["youtube"]
    assert provider_candidates_for_url("https://tiktok.com/@user/video/123") == ["tiktok"]
    assert provider_candidates_for_url("https://instagram.com/p/123") == ["instagram"]
    assert provider_candidates_for_url("https://x.com/user/status/123") == ["x"]
    assert provider_candidates_for_url("https://example.com/video.mp4") == ["direct"]
    assert provider_candidates_for_url("https://youtube.com/video.mp4") == ["youtube", "direct"]
    assert provider_candidates_for_url("https://example.com/page.html") == []

def test_classify_url_unsupported():
    res = classify_url("https://example.com/page.html", ["youtube"])
    assert res.provider is None
    assert res.reason == "unsupported_source"
    assert res.candidates == []
    assert res.domain == "example.com"

def test_classify_url_matched():
    res = classify_url("https://youtube.com/watch?v=123", ["youtube", "tiktok"])
    assert res.provider == "youtube"
    assert res.reason == "matched"
    assert res.candidates == ["youtube"]
    assert res.domain == "youtube.com"

def test_classify_url_supported_but_disabled():
    res = classify_url("https://tiktok.com/@user/video/123", ["youtube"])
    assert res.provider is None
    assert res.reason == "supported_but_disabled"
    assert res.candidates == ["tiktok"]
    assert res.domain == "tiktok.com"

def test_classify_url_multiple_candidates_priority():
    url = "https://youtube.com/video.mp4"
    candidates = provider_candidates_for_url(url)
    assert candidates == ["youtube", "direct"]

    # If direct is checked first in enabled_providers
    res1 = classify_url(url, ["direct", "youtube"])
    assert res1.provider == "direct"
    assert res1.reason == "matched"

    # If youtube is checked first
    res2 = classify_url(url, ["youtube", "direct"])
    assert res2.provider == "youtube"
    assert res2.reason == "matched"

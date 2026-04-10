from core.url_safety import normalize_url, redact_url


def test_normalize_url_adds_https_for_schemaless_input():
    assert normalize_url("example.com/path") == "https://example.com/path"


def test_normalize_url_keeps_existing_scheme():
    assert normalize_url("http://example.com/path") == "http://example.com/path"


def test_normalize_url_empty_or_none():
    assert normalize_url("") == ""
    assert normalize_url(None) == ""
    assert normalize_url("   ") == ""


def test_redact_url_strips_query_and_fragment():
    result = redact_url("https://example.com/path/file.mp4?token=abc#frag")
    assert result == "https://example.com/path/file.mp4"


def test_redact_url_keeps_non_url_text_unchanged():
    assert redact_url("not-a-url") == "not-a-url"

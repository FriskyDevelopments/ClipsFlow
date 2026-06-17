"""
Utilities for safe URL logging.
"""

from __future__ import annotations

from urllib.parse import ParseResult, urlparse


def _safe_urlparse(url: str) -> ParseResult | None:
    """Parse a URL without leaking ValueError for malformed IPv6/host segments."""
    try:
        return urlparse(url)
    except ValueError:
        return None


def normalize_url(url: str) -> str:
    """
    Normalize user input URL for validation/routing by adding ``https://``
    when a scheme is omitted.
    """
    cleaned = (url or "").strip()
    if not cleaned:
        return cleaned

    parsed = _safe_urlparse(cleaned)
    if parsed is None:
        return cleaned

    if parsed.scheme:
        return cleaned

    return f"https://{cleaned}"


def redact_url(url: str) -> str:
    """
    Return a URL safe for logs by stripping query, fragment, and credentials.
    """
    cleaned = (url or "").strip()
    parsed = _safe_urlparse(cleaned)
    if parsed is None:
        return cleaned
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    normalized = normalize_url(cleaned)
    if normalized == cleaned:
        return cleaned

    parsed_normalized = _safe_urlparse(normalized)
    if parsed_normalized is None:
        return cleaned
    if parsed_normalized.netloc and "." in parsed_normalized.netloc:
        return f"{parsed_normalized.scheme}://{parsed_normalized.netloc}{parsed_normalized.path}"

    return cleaned


def is_valid_http_url(url: str) -> bool:
    """Return True when the value can be treated as a simple HTTP/HTTPS URL."""
    parsed = _safe_urlparse((url or "").strip())
    if parsed is None:
        return False
    if not parsed.scheme:
        parsed = _safe_urlparse(f"https://{url.strip()}")
    if parsed is None:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False

    return "." in parsed.netloc and " " not in parsed.netloc and bool(parsed.netloc.strip())

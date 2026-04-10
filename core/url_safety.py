"""
Utilities for safe URL logging.
"""

from __future__ import annotations

from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    """
    Normalize user input URL for validation/routing by adding ``https://``
    when a scheme is omitted.
    """
    cleaned = (url or "").strip()
    if not cleaned:
        return cleaned

    parsed = urlparse(cleaned)
    if parsed.scheme:
        return cleaned

    return f"https://{cleaned}"


def redact_url(url: str) -> str:
    """
    Return a URL safe for logs by stripping query, fragment, and credentials.
    """
    cleaned = (url or "").strip()
    parsed = urlparse(cleaned)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    normalized = normalize_url(cleaned)
    parsed_normalized = urlparse(normalized)
    if parsed_normalized.netloc and "." in parsed_normalized.netloc:
        return f"{parsed_normalized.scheme}://{parsed_normalized.netloc}{parsed_normalized.path}"

    return cleaned

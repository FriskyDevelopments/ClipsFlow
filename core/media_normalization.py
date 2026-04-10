"""Shared extension + MIME normalization helpers for media ingestion providers."""

from __future__ import annotations

from collections.abc import Mapping

DEFAULT_VIDEO_EXTENSION = ".mp4"
DEFAULT_AUDIO_EXTENSION = ".mp3"

_CANONICAL_VIDEO_MIME_BY_EXTENSION: Mapping[str, str] = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
}

_CANONICAL_AUDIO_MIME_BY_EXTENSION: Mapping[str, str] = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
}

_CANONICAL_VIDEO_MIME_ALIASES: Mapping[str, str] = {
    "video/x-m4v": "video/mp4",
    "video/m4v": "video/mp4",
    "video/x-matroska": "video/x-matroska",
    "video/quicktime": "video/quicktime",
    "video/webm": "video/webm",
    "video/mp4": "video/mp4",
}

_CANONICAL_AUDIO_MIME_ALIASES: Mapping[str, str] = {
    "audio/mp3": "audio/mpeg",
    "audio/mpeg": "audio/mpeg",
    "audio/x-m4a": "audio/mp4",
    "audio/m4a": "audio/mp4",
    "audio/mp4": "audio/mp4",
    "audio/aac": "audio/aac",
    "audio/wav": "audio/wav",
    "audio/x-wav": "audio/wav",
    "audio/ogg": "audio/ogg",
}


def _split_media_type(value: str) -> tuple[str, str] | None:
    normalized = (value or "").strip().lower()
    if "/" not in normalized:
        return None
    kind, subtype = normalized.split("/", 1)
    kind = kind.strip()
    subtype = subtype.strip()
    if not kind or not subtype:
        return None
    return kind, subtype


def normalize_media_extension(ext: str, default_ext: str = DEFAULT_VIDEO_EXTENSION) -> str:
    """Normalize extension string to lowercase, single-dot form."""
    normalized_default = normalize_media_extension(default_ext, DEFAULT_VIDEO_EXTENSION) if default_ext != DEFAULT_VIDEO_EXTENSION else DEFAULT_VIDEO_EXTENSION

    value = (ext or "").strip().lower()
    if not value:
        return normalized_default

    if "/" in value:
        split = _split_media_type(value)
        if split is None:
            return normalized_default
        _, subtype = split
        value = subtype

    value = value.removeprefix(".")
    if not value:
        return normalized_default

    return f".{value}"


def resolve_video_mime(ext_or_media_type: str) -> str:
    """Resolve a canonical video MIME from extension or MIME-like input."""
    split = _split_media_type(ext_or_media_type)
    if split is not None:
        kind, subtype = split
        if kind == "audio":
            return resolve_audio_mime(f"audio/{subtype}")
        if kind == "video":
            return _CANONICAL_VIDEO_MIME_ALIASES.get(f"video/{subtype}", "video/mp4")

    ext = normalize_media_extension(ext_or_media_type, DEFAULT_VIDEO_EXTENSION)
    if ext in _CANONICAL_AUDIO_MIME_BY_EXTENSION:
        return _CANONICAL_AUDIO_MIME_BY_EXTENSION[ext]
    return _CANONICAL_VIDEO_MIME_BY_EXTENSION.get(ext, "video/mp4")


def resolve_audio_mime(ext_or_media_type: str) -> str:
    """Resolve a canonical audio MIME from extension or MIME-like input."""
    split = _split_media_type(ext_or_media_type)
    if split is not None:
        kind, subtype = split
        if kind == "audio":
            return _CANONICAL_AUDIO_MIME_ALIASES.get(f"audio/{subtype}", "audio/mpeg")
        if kind == "video":
            return resolve_video_mime(f"video/{subtype}")

    ext = normalize_media_extension(ext_or_media_type, DEFAULT_AUDIO_EXTENSION)
    if ext in _CANONICAL_VIDEO_MIME_BY_EXTENSION:
        return _CANONICAL_VIDEO_MIME_BY_EXTENSION[ext]
    return _CANONICAL_AUDIO_MIME_BY_EXTENSION.get(ext, "audio/mpeg")


def normalized_media_descriptor(
    *,
    ext: str | None = None,
    media_type: str | None = None,
    default_ext: str = DEFAULT_VIDEO_EXTENSION,
) -> tuple[str, str]:
    """Return normalized extension and canonical MIME for provider outputs."""
    normalized_ext = normalize_media_extension(ext or media_type or "", default_ext=default_ext)
    canonical_mime = resolve_video_mime(media_type or normalized_ext)
    return normalized_ext, canonical_mime

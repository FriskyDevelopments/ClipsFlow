"""
core.models - Typed data models for the ClipsFlow pipeline.

These are the canonical data structures that flow through the system.
Providers, validators, and services all speak in terms of these models.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


def _escape_html(text: str) -> str:
    """Escape HTML special characters in user-controlled text."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class ClipStatus(str, Enum):
    """Lifecycle state of a clip as it moves through the pipeline."""

    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    PROVIDER_ERROR = "provider_error"
    PROCESSING_ERROR = "processing_error"


class RejectionReason(str, Enum):
    """Reason a clip was rejected during validation."""

    TOO_LONG = "too_long"
    FILE_TOO_LARGE = "file_too_large"
    UNSUPPORTED_TYPE = "unsupported_type"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED_PROVIDER = "unsupported_provider"
    INVALID_LINK = "invalid_link"
    PROVIDER_ERROR = "provider_error"
    PROCESSING_ERROR = "processing_error"
    UNKNOWN = "unknown"


@dataclass
class MediaCandidate:
    """
    Raw media information resolved by a provider.

    A provider's resolve() method returns one or more of these.
    The pipeline then validates and processes the best candidate.
    """

    url: str
    title: str = ""
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    media_type: str = "video"  # e.g. "video", "video/mp4"
    source: str = ""           # backward-compatible provider alias
    direct_url: Optional[str] = None  # direct media file URL if available
    local_path: Optional[str] = None  # downloaded file path if available
    thumbnail_url: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def file_size_mb(self) -> Optional[float]:
        if self.file_size_bytes is None:
            return None
        return self.file_size_bytes / (1024 * 1024)


@dataclass
class ProcessedMedia:
    """
    Normalised media output produced by MediaProcessor.
    """

    file_path: Optional[str] = None # Optional because if it's cached, there is no file
    duration: Optional[float] = None
    size_bytes: Optional[int] = None
    mime_type: str = "video/mp4"
    telegram_file_id: Optional[str] = None # Added for Ghost Protocol


@dataclass
class ClipResult:
    """
    The outcome of processing a clip request.

    Carries everything the bot layer needs to reply to the user.
    """

    status: ClipStatus
    original_url: str
    candidate: Optional[MediaCandidate] = None
    rejection_reason: Optional[RejectionReason] = None
    rejection_message: str = ""
    processing_notes: list[str] = field(default_factory=list)
    processed_media: Optional[ProcessedMedia] = None

    @property
    def is_ready(self) -> bool:
        return self.status == ClipStatus.SUCCESS and self.processed_media is not None

    @property
    def is_rejected(self) -> bool:
        return self.status == ClipStatus.VALIDATION_ERROR

    @property
    def is_failed(self) -> bool:
        return self.status in {ClipStatus.PROVIDER_ERROR, ClipStatus.PROCESSING_ERROR}

    def user_message(self) -> str:
        """Return a short, human-friendly result message for the bot."""
        if self.is_ready and self.candidate:
            c = self.candidate
            duration_value = (
                self.processed_media.duration
                if self.processed_media and self.processed_media.duration is not None
                else c.duration_seconds
            )
            duration_str = ""
            if duration_value is not None:
                mins, secs = divmod(int(duration_value), 60)
                duration_str = f" ({mins}m{secs:02d}s)"
            size_value = (
                self.processed_media.size_bytes if self.processed_media else c.file_size_bytes
            )
            size_str = ""
            if size_value is not None:
                size_str = f" · {size_value / (1024 * 1024):.1f} MB"

            escaped_title = _escape_html(c.title or "Untitled Asset")

            return (
                f"█▀▀▀▀▀▀ ◈ ▀▀▀▀▀▀█\n"
                f"<b>ASSET REFINED</b>\n\n"
                f"📹 {escaped_title}{duration_str}{size_str}\n"
                f"<i>Delivered via secure channel.</i>"
            )

        if self.is_rejected:
            return f"█▀▀▀ ◈ ▀▀▀█\n<b>VERIFICATION FAILED</b>\n<i>{self.rejection_message or 'Asset does not meet elite standards.'}</i>"

        if self.is_failed:
            return f"█▀▀▀ ◈ ▀▀▀█\n<b>SYSTEM DISRUPTION</b>\n<i>{self.rejection_message or 'The request could not be fulfilled.'}</i>"

        return "◈ Refinement in progress..."

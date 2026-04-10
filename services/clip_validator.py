"""
services.clip_validator – Validates a MediaCandidate against configured limits.

This is pure business logic: no I/O, no bot coupling.
"""

from __future__ import annotations

import logging
from typing import Optional

from config.settings import Settings
from core.models import ClipResult, ClipStatus, MediaCandidate, RejectionReason

logger = logging.getLogger(__name__)


class ClipValidator:
    """
    Validates a resolved MediaCandidate against the configured clip constraints.

    Returns a ClipResult with status SUCCESS or VALIDATION_ERROR.
    Callers must proceed only when status is SUCCESS.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def validate(self, candidate: MediaCandidate, original_url: str) -> ClipResult:
        """
        Run all validation checks against *candidate*.

        Returns a ClipResult. The pipeline should stop and surface the result
        immediately if the status is not SUCCESS.
        """
        # Run duration, file size, and media type checks sequentially.
        for check in (self._check_duration, self._check_file_size, self._check_media_type):
            rejection = check(candidate)
            if rejection:
                reason, message = rejection
                return self._reject(original_url, candidate, reason, message)

        logger.info(
            "Clip validated OK: title=%r duration=%s source=%s",
            candidate.title,
            candidate.duration_seconds,
            candidate.source,
        )
        return ClipResult(
            status=ClipStatus.SUCCESS,
            original_url=original_url,
            candidate=candidate,
        )

    # ── Internal checks ───────────────────────────────────────────────────

    def _check_duration(
        self, candidate: MediaCandidate
    ) -> Optional[tuple[RejectionReason, str]]:
        if candidate.duration_seconds is None:
            return None  # unknown duration – allow through, warn downstream
        max_dur = self._settings.clip_max_duration_seconds
        if candidate.duration_seconds > max_dur:
            # Format limit: show seconds for sub-minute, minutes otherwise
            if max_dur < 60:
                limit_str = f"{max_dur}-second"
            else:
                mins = max_dur // 60
                limit_str = f"{mins}-minute"

            actual_mins = int(candidate.duration_seconds) // 60
            actual_secs = int(candidate.duration_seconds) % 60
            return (
                RejectionReason.TOO_LONG,
                (
                    f"This clip is {actual_mins}m{actual_secs:02d}s long, "
                    f"which exceeds the {limit_str} limit. "
                    "Please share a shorter clip."
                ),
            )
        return None

    def _check_file_size(
        self, candidate: MediaCandidate
    ) -> Optional[tuple[RejectionReason, str]]:
        if candidate.file_size_mb is None:
            return None  # unknown size – allow through
        max_mb = self._settings.clip_max_file_size_mb
        if candidate.file_size_mb > max_mb:
            return (
                RejectionReason.FILE_TOO_LARGE,
                (
                    f"File is {candidate.file_size_mb:.1f} MB, "
                    f"which exceeds the {max_mb} MB limit."
                ),
            )
        return None

    def _check_media_type(
        self, candidate: MediaCandidate
    ) -> Optional[tuple[RejectionReason, str]]:
        allowed = self._settings.clip_allowed_media_types
        if not any(candidate.media_type.startswith(t) for t in allowed):
            return (
                RejectionReason.UNSUPPORTED_TYPE,
                (
                    f"Media type '{candidate.media_type}' is not supported. "
                    f"Allowed types: {', '.join(allowed)}."
                ),
            )
        return None

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _reject(
        original_url: str,
        candidate: MediaCandidate,
        reason: RejectionReason,
        message: str,
    ) -> ClipResult:
        logger.warning("Clip rejected: reason=%s message=%r", reason, message)
        return ClipResult(
            status=ClipStatus.VALIDATION_ERROR,
            original_url=original_url,
            candidate=candidate,
            rejection_reason=reason,
            rejection_message=message,
        )

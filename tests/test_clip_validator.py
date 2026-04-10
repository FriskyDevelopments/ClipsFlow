"""
tests.test_clip_validator – Unit tests for ClipValidator.
"""

import pytest

from core.models import ClipStatus, RejectionReason
from services.clip_validator import ClipValidator


class TestClipValidatorDuration:
    def test_passes_within_limit(self, make_settings, make_candidate):
        validator = ClipValidator(make_settings(clip_max_duration_seconds=300))
        result = validator.validate(make_candidate(duration_seconds=120.0), "https://x.com")
        assert result.status == ClipStatus.SUCCESS

    def test_rejects_over_limit(self, make_settings, make_candidate):
        validator = ClipValidator(make_settings(clip_max_duration_seconds=60))
        result = validator.validate(make_candidate(duration_seconds=120.0), "https://x.com")
        assert result.status == ClipStatus.VALIDATION_ERROR
        assert result.rejection_reason == RejectionReason.TOO_LONG

    def test_passes_exactly_at_limit(self, make_settings, make_candidate):
        validator = ClipValidator(make_settings(clip_max_duration_seconds=90))
        result = validator.validate(make_candidate(duration_seconds=90.0), "https://x.com")
        assert result.status == ClipStatus.SUCCESS

    def test_passes_when_duration_unknown(self, make_settings, make_candidate):
        validator = ClipValidator(make_settings(clip_max_duration_seconds=60))
        result = validator.validate(make_candidate(duration_seconds=None), "https://x.com")
        assert result.status == ClipStatus.SUCCESS


class TestClipValidatorFileSize:
    def test_passes_within_limit(self, make_settings, make_candidate):
        validator = ClipValidator(make_settings(clip_max_file_size_mb=50))
        # 10 MB < 50 MB
        result = validator.validate(make_candidate(file_size_bytes=10 * 1024 * 1024), "https://x.com")
        assert result.status == ClipStatus.SUCCESS

    def test_rejects_over_limit(self, make_settings, make_candidate):
        validator = ClipValidator(make_settings(clip_max_file_size_mb=5))
        # 10 MB > 5 MB
        result = validator.validate(make_candidate(file_size_bytes=10 * 1024 * 1024), "https://x.com")
        assert result.status == ClipStatus.VALIDATION_ERROR
        assert result.rejection_reason == RejectionReason.FILE_TOO_LARGE

    def test_passes_when_size_unknown(self, make_settings, make_candidate):
        validator = ClipValidator(make_settings(clip_max_file_size_mb=5))
        result = validator.validate(make_candidate(file_size_bytes=None), "https://x.com")
        assert result.status == ClipStatus.SUCCESS


class TestClipValidatorMediaType:
    def test_passes_allowed_type(self, make_settings, make_candidate):
        validator = ClipValidator(make_settings(clip_allowed_media_types=["video"]))
        result = validator.validate(make_candidate(media_type="video/mp4"), "https://x.com")
        assert result.status == ClipStatus.SUCCESS

    def test_rejects_disallowed_type(self, make_settings, make_candidate):
        validator = ClipValidator(make_settings(clip_allowed_media_types=["video"]))
        result = validator.validate(make_candidate(media_type="audio/mpeg"), "https://x.com")
        assert result.status == ClipStatus.VALIDATION_ERROR
        assert result.rejection_reason == RejectionReason.UNSUPPORTED_TYPE

    def test_passes_exact_prefix_match(self, make_settings, make_candidate):
        validator = ClipValidator(make_settings(clip_allowed_media_types=["video/mp4"]))
        result = validator.validate(make_candidate(media_type="video/mp4"), "https://x.com")
        assert result.status == ClipStatus.SUCCESS


class TestClipValidatorRejectionMessage:
    def test_rejection_message_too_long(self, make_settings, make_candidate):
        validator = ClipValidator(make_settings(clip_max_duration_seconds=60))
        result = validator.validate(make_candidate(duration_seconds=200.0), "https://x.com")
        assert "limit" in result.rejection_message.lower()

    def test_rejection_message_file_too_large(self, make_settings, make_candidate):
        validator = ClipValidator(make_settings(clip_max_file_size_mb=1))
        result = validator.validate(make_candidate(file_size_bytes=50 * 1024 * 1024), "https://x.com")
        assert "MB" in result.rejection_message

    def test_candidate_present_on_rejection(self, make_settings, make_candidate):
        """Rejected results should still carry the candidate for context."""
        validator = ClipValidator(make_settings(clip_max_duration_seconds=1))
        candidate = make_candidate(duration_seconds=999.0)
        result = validator.validate(candidate, "https://x.com")
        assert result.candidate is candidate

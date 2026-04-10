"""
tests.test_models – Unit tests for core data models.
"""

import pytest

from core.models import (
    ClipResult,
    ClipStatus,
    MediaCandidate,
    RejectionReason,
)


class TestMediaCandidate:
    def test_file_size_mb_conversion(self):
        c = MediaCandidate(url="https://example.com", file_size_bytes=10 * 1024 * 1024)
        assert c.file_size_mb == pytest.approx(10.0)

    def test_file_size_mb_none_when_unknown(self):
        c = MediaCandidate(url="https://example.com")
        assert c.file_size_mb is None

    def test_defaults(self):
        c = MediaCandidate(url="https://example.com/clip.mp4")
        assert c.media_type == "video"
        assert c.title == ""
        assert c.source == ""
        assert c.direct_url is None


class TestClipResult:
    def test_is_ready(self):
        from core.models import ProcessedMedia
        pm = ProcessedMedia(file_path="/tmp/out.mp4", duration=30.0, size_bytes=1024)
        r = ClipResult(status=ClipStatus.SUCCESS, original_url="https://example.com", processed_media=pm)
        assert r.is_ready
        assert not r.is_rejected
        assert not r.is_failed

    def test_is_rejected(self):
        r = ClipResult(
            status=ClipStatus.VALIDATION_ERROR,
            original_url="https://example.com",
            rejection_reason=RejectionReason.TOO_LONG,
            rejection_message="Too long",
        )
        assert r.is_rejected
        assert not r.is_ready

    def test_is_failed(self):
        r = ClipResult(status=ClipStatus.PROVIDER_ERROR, original_url="https://example.com")
        assert r.is_failed

    def test_user_message_ready(self):
        from core.models import ProcessedMedia
        candidate = MediaCandidate(
            url="https://example.com",
            title="Test Clip",
            duration_seconds=90.0,
            file_size_bytes=5 * 1024 * 1024,
            direct_url="https://cdn.example.com/clip.mp4",
        )
        pm = ProcessedMedia(
            file_path="/tmp/out.mp4",
            duration=90.0,
            size_bytes=5 * 1024 * 1024,
        )
        r = ClipResult(
            status=ClipStatus.SUCCESS,
            original_url="https://example.com",
            candidate=candidate,
            processed_media=pm,
        )
        msg = r.user_message()
        assert "Test Clip" in msg
        assert "1m30s" in msg
        assert "5.0 MB" in msg
        assert "ASSET REFINED" in msg

    def test_user_message_rejected(self):
        r = ClipResult(
            status=ClipStatus.VALIDATION_ERROR,
            original_url="https://example.com",
            rejection_message="Too long",
        )
        msg = r.user_message()
        assert "VERIFICATION FAILED" in msg
        assert "Too long" in msg

    def test_user_message_failed(self):
        r = ClipResult(
            status=ClipStatus.PROCESSING_ERROR,
            original_url="https://example.com",
            rejection_message="Oops",
        )
        msg = r.user_message()
        assert "SYSTEM DISRUPTION" in msg
        assert "Oops" in msg


class TestMediaCandidateSimplifiedFields:
    """Fields removed from MediaCandidate in this PR must not be present."""

    def test_no_subtype_field(self):
        c = MediaCandidate(url="https://example.com/clip")
        assert not hasattr(c, "subtype"), "subtype was removed from MediaCandidate"

    def test_no_canonical_url_field(self):
        c = MediaCandidate(url="https://example.com/clip")
        assert not hasattr(c, "canonical_url"), "canonical_url was removed from MediaCandidate"

    def test_no_author_field(self):
        c = MediaCandidate(url="https://example.com/clip")
        assert not hasattr(c, "author"), "author was removed from MediaCandidate"

    def test_no_provider_metadata_field(self):
        c = MediaCandidate(url="https://example.com/clip")
        assert not hasattr(c, "provider_metadata"), (
            "provider_metadata was removed from MediaCandidate"
        )

    def test_no_provider_field(self):
        """provider field was merged into source; must not have a separate provider field."""
        c = MediaCandidate(url="https://example.com/clip")
        assert not hasattr(c, "provider"), "provider was removed from MediaCandidate"

    def test_source_field_retained(self):
        """source is the remaining provider identifier field."""
        c = MediaCandidate(url="https://example.com/clip", source="youtube")
        assert c.source == "youtube"

    def test_extra_field_retained(self):
        """extra dict is still available for ad-hoc metadata."""
        c = MediaCandidate(url="https://example.com/clip", extra={"foo": "bar"})
        assert c.extra == {"foo": "bar"}

    def test_no_post_init_sync_source_to_provider(self):
        """__post_init__ no longer exists; source is not copied to a provider field."""
        c = MediaCandidate(url="https://example.com/clip", source="youtube")
        # With __post_init__ gone, there is no provider field to sync to
        assert not hasattr(c, "provider")

    def test_no_post_init_sync_provider_to_source(self):
        """__post_init__ was removed; creating a candidate with source set is fine."""
        c = MediaCandidate(url="https://example.com/clip", source="mock")
        assert c.source == "mock"

    def test_url_field_not_duplicated_to_canonical_url(self):
        """canonical_url was removed; url stays only in .url."""
        c = MediaCandidate(url="https://example.com/clip")
        assert not hasattr(c, "canonical_url")
        assert c.url == "https://example.com/clip"


class TestProcessedMediaSimplifiedFields:
    """Fields removed from ProcessedMedia in this PR must not be present."""

    from core.models import ProcessedMedia

    def test_no_media_kind_field(self):
        from core.models import ProcessedMedia
        pm = ProcessedMedia(file_path="/tmp/out.mp4", duration=30.0, size_bytes=1024)
        assert not hasattr(pm, "media_kind"), "media_kind was removed from ProcessedMedia"

    def test_no_title_field(self):
        from core.models import ProcessedMedia
        pm = ProcessedMedia(file_path="/tmp/out.mp4", duration=30.0, size_bytes=1024)
        assert not hasattr(pm, "title"), "title was removed from ProcessedMedia"

    def test_no_thumbnail_url_field(self):
        from core.models import ProcessedMedia
        pm = ProcessedMedia(file_path="/tmp/out.mp4", duration=30.0, size_bytes=1024)
        assert not hasattr(pm, "thumbnail_url"), "thumbnail_url was removed from ProcessedMedia"

    def test_no_source_url_field(self):
        from core.models import ProcessedMedia
        pm = ProcessedMedia(file_path="/tmp/out.mp4", duration=30.0, size_bytes=1024)
        assert not hasattr(pm, "source_url"), "source_url was removed from ProcessedMedia"

    def test_required_fields_retained(self):
        """Core fields (file_path, duration, size_bytes, mime_type) must still be present."""
        from core.models import ProcessedMedia
        pm = ProcessedMedia(
            file_path="/tmp/out.mp4",
            duration=45.0,
            size_bytes=2048,
            mime_type="video/webm",
        )
        assert pm.file_path == "/tmp/out.mp4"
        assert pm.duration == pytest.approx(45.0)
        assert pm.size_bytes == 2048
        assert pm.mime_type == "video/webm"

    def test_mime_type_defaults_to_mp4(self):
        from core.models import ProcessedMedia
        pm = ProcessedMedia(file_path="/tmp/out.mp4", duration=None, size_bytes=0)
        assert pm.mime_type == "video/mp4"

    def test_creating_with_removed_field_raises_type_error(self):
        """Passing a removed field like media_kind must raise TypeError."""
        from core.models import ProcessedMedia
        with pytest.raises(TypeError):
            ProcessedMedia(
                file_path="/tmp/out.mp4",
                duration=30.0,
                size_bytes=1024,
                media_kind="video",  # removed field
            )
"""
tests.test_pipeline – Integration tests for the ClipPipeline.

Uses MockProvider and a real ClipValidator so we test the full flow
end-to-end without any network I/O.
"""

import pytest

from core.models import ClipStatus, ProcessedMedia, RejectionReason
from core.pipeline import ClipPipeline
from providers.mock import MockProvider
from providers.registry import ProviderRegistry
from services.clip_validator import ClipValidator
from services.media_processor import MediaProcessingError


@pytest.fixture
def make_pipeline(make_settings):
    """Construct a pipeline with the mock provider and custom settings."""

    def _make_pipeline(processor=None, **settings_overrides):
        s = make_settings(**settings_overrides)

        registry = ProviderRegistry()
        registry = ProviderRegistry([MockProvider()])

        validator = ClipValidator(s)

        class _DummyProcessor:
            def __init__(self, fail: bool = False):
                self.fail = fail

            async def process_media(self, candidate):
                if self.fail:
                    raise MediaProcessingError("processing error")
                return ProcessedMedia(
                    file_path="/tmp/processed.mp4",
                    duration=candidate.duration_seconds,
                    size_bytes=1024,
                    mime_type="video/mp4",
                )

        processor = processor or _DummyProcessor()
        return ClipPipeline(registry, validator, processor)

    return _make_pipeline


class TestPipelineHappyPath:
    async def test_valid_mock_link_returns_ready(self, make_pipeline):
        pipeline = make_pipeline()
        result = await pipeline.process("https://mock.example.com/clip")
        assert result.status == ClipStatus.SUCCESS
        assert result.candidate is not None
        assert result.processed_media is not None

    async def test_result_carries_candidate_metadata(self, make_pipeline):
        pipeline = make_pipeline()
        result = await pipeline.process("https://mock.example.com/clip?duration=60")
        assert result.candidate.duration_seconds == 60.0
        assert result.candidate.source == "mock"

    async def test_whitespace_around_url_is_trimmed(self, make_pipeline):
        pipeline = make_pipeline()
        result = await pipeline.process("  https://mock.example.com/clip  ")
        assert result.status == ClipStatus.SUCCESS


class TestPipelineRejections:
    async def test_invalid_url_is_rejected(self, make_pipeline):
        pipeline = make_pipeline()
        result = await pipeline.process("not-a-url-at-all")
        assert result.status == ClipStatus.VALIDATION_ERROR
        assert result.rejection_reason == RejectionReason.INVALID_LINK

    async def test_unsupported_provider_is_rejected(self, make_pipeline):
        pipeline = make_pipeline()
        result = await pipeline.process("https://unsupportedsite.com/video")
        assert result.status == ClipStatus.VALIDATION_ERROR
        assert result.rejection_reason == RejectionReason.UNSUPPORTED_PROVIDER

    async def test_clip_too_long_is_rejected(self, make_pipeline):
        pipeline = make_pipeline(clip_max_duration_seconds=60)
        result = await pipeline.process("https://mock.example.com/clip?duration=120")
        assert result.status == ClipStatus.VALIDATION_ERROR
        assert result.rejection_reason == RejectionReason.TOO_LONG

    async def test_file_too_large_is_rejected(self, make_pipeline):
        pipeline = make_pipeline(clip_max_file_size_mb=1)
        # Default mock size is 10 MB > 1 MB limit
        result = await pipeline.process("https://mock.example.com/clip")
        assert result.status == ClipStatus.VALIDATION_ERROR
        assert result.rejection_reason == RejectionReason.FILE_TOO_LARGE

    async def test_unavailable_clip_is_rejected(self, make_pipeline):
        pipeline = make_pipeline()
        result = await pipeline.process("https://mock.example.com/clip?unavailable=1")
        assert result.status == ClipStatus.PROVIDER_ERROR
        assert result.rejection_reason == RejectionReason.UNAVAILABLE


class TestPipelineFailures:
    async def test_provider_failure_returns_provider_error(self, make_pipeline):
        pipeline = make_pipeline()
        result = await pipeline.process("https://mock.example.com/clip?fail=1")
        assert result.status == ClipStatus.PROVIDER_ERROR
        assert result.rejection_reason == RejectionReason.PROVIDER_ERROR

    async def test_processing_failure_returns_processing_error(self, make_pipeline):
        class _FailProcessor:
            async def process_media(self, candidate):
                raise MediaProcessingError("boom")

        pipeline = make_pipeline(processor=_FailProcessor())
        result = await pipeline.process("https://mock.example.com/clip")
        assert result.status == ClipStatus.PROCESSING_ERROR
        assert result.rejection_reason == RejectionReason.PROCESSING_ERROR

    async def test_unexpected_processing_exception_returns_result(self, make_pipeline, caplog):
        class _ExplodingProcessor:
            async def process_media(self, candidate):
                raise OSError("disk gone")

        pipeline = make_pipeline(processor=_ExplodingProcessor())
        with caplog.at_level("ERROR"):
            result = await pipeline.process("https://mock.example.com/clip")

        assert result.status == ClipStatus.PROCESSING_ERROR
        assert result.rejection_reason == RejectionReason.PROCESSING_ERROR
        # Unexpected errors should not leak raw exception messages to users
        assert "disk gone" not in result.rejection_message
        # Logger should have captured an exception traceback
        assert any(rec.exc_info for rec in caplog.records)


class TestPipelineUserMessages:
    async def test_ready_message_contains_title(self, make_pipeline):
        pipeline = make_pipeline()
        result = await pipeline.process("https://mock.example.com/clip")
        msg = result.user_message()
        assert "Mock Clip" in msg

    async def test_rejected_message_is_friendly(self, make_pipeline):
        pipeline = make_pipeline(clip_max_duration_seconds=1)
        result = await pipeline.process("https://mock.example.com/clip?duration=999")
        msg = result.user_message()
        assert "VERIFICATION FAILED" in msg


class TestPipelineUrlHandling:
    """Tests for the URL handling changes in this PR: stripping and direct use."""

    @pytest.mark.anyio
    async def test_original_url_in_result_is_stripped(self, make_pipeline):
        """original_url in ClipResult must be the stripped URL."""
        pipeline = make_pipeline()
        result = await pipeline.process("  https://mock.example.com/clip  ")
        assert result.original_url == "https://mock.example.com/clip"

    @pytest.mark.anyio
    async def test_original_url_not_modified_otherwise(self, make_pipeline):
        """URL is used as-is (after strip), not normalized with https:// prefix."""
        pipeline = make_pipeline()
        url = "https://mock.example.com/clip?duration=30"
        result = await pipeline.process(url)
        assert result.original_url == url

    @pytest.mark.anyio
    async def test_url_stripped_before_validation(self, make_pipeline):
        """Stripping happens before validate_url, so padded valid URLs are accepted."""
        pipeline = make_pipeline()
        result = await pipeline.process("\thttps://mock.example.com/clip\t")
        assert result.status == ClipStatus.SUCCESS

    @pytest.mark.anyio
    async def test_invalid_url_original_url_is_stripped(self, make_pipeline):
        """Even for invalid URLs the original_url should be the stripped version."""
        pipeline = make_pipeline()
        result = await pipeline.process("  not-a-url  ")
        assert result.original_url == "not-a-url"

    @pytest.mark.anyio
    async def test_candidate_url_matches_processed_url(self, make_pipeline):
        """The candidate returned by the provider must reference the same URL."""
        pipeline = make_pipeline()
        url = "https://mock.example.com/clip?duration=45"
        result = await pipeline.process(url)
        assert result.status == ClipStatus.SUCCESS
        assert result.candidate is not None
        assert result.candidate.url == url


class TestPipelineLogging:
    """Tests to verify clean logging after rune/redact_url removal."""

    @pytest.mark.anyio
    async def test_no_rune_glyphs_in_info_logs(self, make_pipeline, caplog):
        """Log messages no longer contain runic glyphs like [⟪], [→], [Λ], [◫], [✕]."""
        rune_glyphs = {"⟪", "→", "Λ", "◫", "✕", "⟐", "⫶"}
        pipeline = make_pipeline()
        with caplog.at_level("INFO"):
            await pipeline.process("https://mock.example.com/clip")
        for record in caplog.records:
            for glyph in rune_glyphs:
                assert glyph not in record.message, (
                    f"Rune glyph {glyph!r} should not appear in log: {record.message!r}"
                )

    @pytest.mark.anyio
    async def test_pipeline_start_logged(self, make_pipeline, caplog):
        """Pipeline start is logged at INFO level."""
        pipeline = make_pipeline()
        with caplog.at_level("INFO"):
            await pipeline.process("https://mock.example.com/clip")
        messages = [r.message for r in caplog.records]
        assert any("Pipeline" in m and "starting" in m for m in messages)

    @pytest.mark.anyio
    async def test_pipeline_success_logged(self, make_pipeline, caplog):
        """Successful pipeline run is logged at INFO level."""
        pipeline = make_pipeline()
        with caplog.at_level("INFO"):
            await pipeline.process("https://mock.example.com/clip")
        messages = [r.message for r in caplog.records]
        assert any("finished" in m or "success" in m for m in messages)

    @pytest.mark.anyio
    async def test_provider_error_logged_without_runes(self, make_pipeline, caplog):
        """Provider errors are logged without rune markers."""
        rune_glyphs = {"⟪", "→", "Λ", "◫", "✕", "⟐", "⫶"}
        pipeline = make_pipeline()
        with caplog.at_level("ERROR"):
            await pipeline.process("https://mock.example.com/clip?fail=1")
        for record in caplog.records:
            for glyph in rune_glyphs:
                assert glyph not in record.message
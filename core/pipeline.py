"""
core.pipeline – The central ClipsFlow processing pipeline.

The pipeline is the heart of ClipsFlow.  It orchestrates:
  1. URL validation
  2. Provider selection and resolution
  3. Clip validation
  4. (Future) processing / normalisation steps

The pipeline is async, stateless, and has no knowledge of Telegram or
any other transport layer.  It accepts a URL string and returns a
ClipResult.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from itertools import cycle
from config.settings import get_settings

from core.models import ClipResult, ClipStatus, MediaCandidate, ProcessedMedia, RejectionReason
from core.url_safety import redact_url
from providers.base import ProviderError
from providers.registry import ProviderRegistry
from services.clip_validator import ClipValidator
from services.media_processor import MediaProcessingError, MediaProcessor

logger = logging.getLogger(__name__)


class ClipPipeline:
    """
    Processes a clip request end-to-end.

    Usage::

        pipeline = ClipPipeline(registry, validator, media_processor)
        result = await pipeline.process("https://youtu.be/...")
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        validator: ClipValidator,
        media_processor: MediaProcessor,
    ) -> None:
        self._registry = registry
        self._validator = validator
        self._media_processor = media_processor

    async def process(self, url: str) -> ClipResult:
        """
        Run the full clip pipeline for *url*.

        Always returns a ClipResult – exceptions are caught internally
        so the bot layer never needs to handle raw exceptions from here.
        """
        # Strip whitespace from incoming url before any processing
        url = url.strip()

        logger.info("Pipeline starting for url=%s", redact_url(url))

        # ── Step 1: URL validation ─────────────────────────────────────
        normalized_url, early_rejection = self._registry.validate_url(url)
        if early_rejection is not None:
            return early_rejection

        # ── Step 2: Provider resolution ───────────────────────────────
        provider = self._registry.find(normalized_url)
        # validate_url already ensures a provider exists, but guard anyway
        if provider is None:
            return ClipResult(
                status=ClipStatus.VALIDATION_ERROR,
                original_url=normalized_url,
                rejection_reason=RejectionReason.UNSUPPORTED_PROVIDER,
                rejection_message="No provider available for this link.",
            )

        candidate = None
        max_retries = 3
        attempt = 0
        settings = get_settings()
        proxy_iter = cycle(settings.proxy_pool) if settings.proxy_pool else None
        
        provider_started_at = time.perf_counter()
        while attempt <= max_retries:
            try:
                proxy = next(proxy_iter) if proxy_iter else None
                if proxy:
                    logger.debug("Attempt %d - using proxy: %s", attempt, getattr(proxy, '__getitem__', lambda x: "")(slice(0, 20)) + "...")
                candidate = await provider.resolve(normalized_url, proxy=proxy)
                break
            except ProviderError as exc:
                if exc.retryable and attempt < max_retries:
                    attempt += 1
                    delay = (2 ** attempt) + random.uniform(0.1, 1.0)
                    logger.warning("Provider error (retryable). Retrying %d/%d for %s in %.2fs", attempt, max_retries, provider.name, delay)
                    await asyncio.sleep(delay)
                    continue
                
                logger.error("Provider error: provider=%r retryable=%s error=%s", provider.name, exc.retryable, exc)
                retry_hint = " Please retry shortly." if exc.retryable else ""
                return ClipResult(
                    status=ClipStatus.PROVIDER_ERROR,
                    original_url=normalized_url,
                    rejection_reason=RejectionReason.PROVIDER_ERROR,
                    rejection_message=f"Provider error: {exc}{retry_hint}",
                )
            except Exception:  # noqa: BLE001
                logger.exception("Unexpected provider error: provider=%r", provider.name)
                return ClipResult(
                    status=ClipStatus.PROVIDER_ERROR,
                    original_url=normalized_url,
                    rejection_reason=RejectionReason.UNKNOWN,
                    rejection_message="An unexpected error occurred. Please try again.",
                )

        if candidate is None:
            return ClipResult(
                status=ClipStatus.PROVIDER_ERROR,
                original_url=normalized_url,
                rejection_reason=RejectionReason.UNAVAILABLE,
                rejection_message="The media could not be retrieved. It may be private or unavailable.",
            )
        logger.info(
            "[TIMING] provider_resolve provider=%s seconds=%.3f size_bytes=%s duration=%s",
            provider.name,
            time.perf_counter() - provider_started_at,
            candidate.file_size_bytes,
            candidate.duration_seconds,
        )

        # ── Step 3: Clip validation ───────────────────────────────────
        validation = self._validator.validate(candidate, normalized_url)
        if validation.status != ClipStatus.SUCCESS:
            return validation

        # ── Step 4: Media processing ─────────────────────────────────
        safe_url = redact_url(normalized_url)
        try:
            processing_started_at = time.perf_counter()
            processed: ProcessedMedia = await self._media_processor.process_media(candidate)
            logger.info(
                "[TIMING] media_processing seconds=%.3f output_bytes=%s mime=%s",
                time.perf_counter() - processing_started_at,
                processed.size_bytes,
                processed.mime_type,
            )
        except MediaProcessingError as exc:
            logger.error("Processing error: url=%s reason=%s", safe_url, exc)
            return ClipResult(
                status=ClipStatus.PROCESSING_ERROR,
                original_url=normalized_url,
                candidate=candidate,
                rejection_reason=RejectionReason.PROCESSING_ERROR,
                rejection_message=str(exc),
            )
        except Exception:
            logger.exception("Unexpected processing error: url=%s", safe_url)
            return ClipResult(
                status=ClipStatus.PROCESSING_ERROR,
                original_url=normalized_url,
                candidate=candidate,
                rejection_reason=RejectionReason.PROCESSING_ERROR,
                rejection_message="An unexpected processing error occurred. Please try again.",
            )

        logger.info("Pipeline finished successfully: url=%s", safe_url)
        return ClipResult(
            status=ClipStatus.SUCCESS,
            original_url=normalized_url,
            candidate=candidate,
            processed_media=processed,
        )

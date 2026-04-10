"""Provider discovery and routing."""

from __future__ import annotations

import logging
from typing import Optional

from config.settings import get_settings
from core.models import ClipResult, ClipStatus, RejectionReason
from core.source_routing import classify_url
from core.url_safety import normalize_url, redact_url
from providers.base import BaseProvider, is_valid_url

logger = logging.getLogger(__name__)


def _get_provider_by_name(name: str) -> Optional[BaseProvider]:
    from providers.mock import MockProvider
    from providers.youtube import YouTubeProvider
    if name == "mock":
        return MockProvider()
    if name == "youtube":
        return YouTubeProvider()
    return None


class ProviderRegistry:
    def __init__(self, providers: list[BaseProvider] | None = None) -> None:
        if providers is None:
            settings = get_settings()
            provider = _get_provider_by_name(settings.clip_provider)
            self._providers = [provider] if provider else []
        else:
            self._providers = providers
        self._provider_by_name = {p.name: p for p in self._providers}

    @property
    def enabled_provider_names(self) -> list[str]:
        return [p.name for p in self._providers]

    def find(self, url: str) -> Optional[BaseProvider]:
        normalized_url = normalize_url(url)
        decision = classify_url(normalized_url, self.enabled_provider_names)
        if decision.provider:
            provider = self._provider_by_name.get(decision.provider)
            if provider and provider.can_handle(normalized_url):
                logger.info(
                    "provider.route matched provider=%s candidates=%s url=%s",
                    provider.name,
                    decision.candidates,
                    redact_url(normalized_url),
                )
                return provider

        # fallback to explicit can_handle in enabled order for deterministic behavior
        for provider in self._providers:
            if provider.can_handle(normalized_url):
                logger.info("provider.route fallback provider=%s url=%s", provider.name, redact_url(normalized_url))
                return provider
        return None

    def validate_url(self, url: str) -> tuple[str, Optional[ClipResult]]:
        """
        Validate a user-supplied URL and return its normalized value.

        The URL scheme is optional in user input. If omitted, ``https://`` is
        prepended before validation and routing. The return value is a tuple
        ``(normalized_url, rejection_or_none)``.
        """
        normalized_url = normalize_url(url)
        if not normalized_url or not is_valid_url(normalized_url):
            return url, ClipResult(  # return original URL instead of normalized_url if invalid
                status=ClipStatus.VALIDATION_ERROR,
                original_url=url,
                rejection_reason=RejectionReason.INVALID_LINK,
                rejection_message="Provide a valid video URL (for example: youtube.com/watch?v=abc123).",
            )

        decision = classify_url(normalized_url, self.enabled_provider_names)
        if decision.reason == "matched":
            return normalized_url, None

        enabled = ", ".join(self.enabled_provider_names) if self._providers else "none"
        if decision.reason == "supported_but_disabled":
            return normalized_url, ClipResult(
                status=ClipStatus.VALIDATION_ERROR,
                original_url=normalized_url,
                rejection_reason=RejectionReason.UNSUPPORTED_PROVIDER,
                rejection_message=(
                    f"This source is supported by ClipsFlow but disabled right now. "
                    f"Route candidates: {', '.join(decision.candidates)}. Enabled providers: {enabled}."
                ),
            )

        # Allow fallback provider logic here! The original code only allowed matched URLs to pass.
        for provider in self._providers:
            if provider.can_handle(normalized_url):
                return normalized_url, None

        return normalized_url, ClipResult(
            status=ClipStatus.VALIDATION_ERROR,
            original_url=normalized_url,
            rejection_reason=RejectionReason.UNSUPPORTED_PROVIDER,
            rejection_message=(
                f"Unsupported source domain. Enabled providers: {enabled}. "
                "Supported sources include direct media URLs plus youtube.com/youtu.be, tiktok.com, "
                "instagram.com, x.com, and twitter.com."
            ),
        )

    def __len__(self) -> int:
        return len(self._providers)

    def __repr__(self) -> str:
        return f"<ProviderRegistry providers={self.enabled_provider_names}>"

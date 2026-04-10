from __future__ import annotations

from providers.base import BaseProvider
from providers.direct import DirectProvider
from providers.instagram import InstagramProvider
from providers.tiktok import TikTokProvider
from providers.x_provider import XProvider
from providers.youtube import YouTubeProvider
from providers.mock import MockProvider


def create_provider(name: str) -> BaseProvider:
    mapping = {
        "direct": DirectProvider,
        "youtube": YouTubeProvider,
        "tiktok": TikTokProvider,
        "instagram": InstagramProvider,
        "x": XProvider,
        "mock": MockProvider,
    }
    if name not in mapping:
        raise ValueError(f"Unknown provider: {name}")
    provider_cls = mapping[name]
    return provider_cls() if name != "youtube" else provider_cls(api_key="")

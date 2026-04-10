"""Central source/provider URL routing rules for ClipsFlow."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from core.url_safety import normalize_url

ALL_PROVIDERS: tuple[str, ...] = ("direct", "youtube", "tiktok", "instagram", "x")

_PROVIDER_DOMAINS: dict[str, tuple[str, ...]] = {
    "youtube": ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "thisvid.com", "www.thisvid.com"),
    "tiktok": ("tiktok.com", "www.tiktok.com", "m.tiktok.com"),
    "instagram": ("instagram.com", "www.instagram.com"),
    "x": ("x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"),
}

_DIRECT_EXTENSIONS = {
    ".mp4", ".mov", ".m4v", ".webm", ".mkv", ".mp3", ".m4a", ".wav", ".aac", ".ogg"
}


@dataclass(frozen=True)
class RouteDecision:
    provider: str | None
    candidates: list[str]
    reason: str
    domain: str



def parse_domain(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    return parsed.netloc.lower()


def is_direct_media_url(url: str) -> bool:
    parsed = urlparse(normalize_url(url))
    if parsed.scheme not in {"http", "https"}:
        return False
    path = (parsed.path or "").lower()
    return any(path.endswith(ext) for ext in _DIRECT_EXTENSIONS)


def provider_candidates_for_url(url: str) -> list[str]:
    domain = parse_domain(url)
    candidates: list[str] = []

    for provider, domains in _PROVIDER_DOMAINS.items():
        if domain in domains or any(domain.endswith(f".{d}") for d in domains):
            candidates.append(provider)

    if is_direct_media_url(url):
        candidates.append("direct")

    # de-dup while preserving order
    return list(dict.fromkeys(candidates))


def classify_url(url: str, enabled_providers: list[str]) -> RouteDecision:
    candidates = provider_candidates_for_url(url)
    domain = parse_domain(url)

    if not candidates:
        return RouteDecision(
            provider=None,
            candidates=[],
            reason="unsupported_source",
            domain=domain,
        )

    for name in enabled_providers:
        if name in candidates:
            return RouteDecision(
                provider=name,
                candidates=candidates,
                reason="matched",
                domain=domain,
            )

    return RouteDecision(
        provider=None,
        candidates=candidates,
        reason="supported_but_disabled",
        domain=domain,
    )


def provider_domains(provider_name: str) -> tuple[str, ...]:
    return _PROVIDER_DOMAINS.get(provider_name, tuple())

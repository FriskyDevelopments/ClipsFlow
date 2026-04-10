"""Generic yt-dlp backed provider for social platforms."""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Optional

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

from core.media_normalization import normalized_media_descriptor
from core.models import MediaCandidate
from providers.base import BaseProvider, ProviderError

logger = logging.getLogger(__name__)


class YtDlpProvider(BaseProvider):
    def __init__(self, name: str, domains: tuple[str, ...], subtype_rules: dict[str, str] | None = None) -> None:
        self.name = name
        self._domains = domains
        self._subtype_rules = subtype_rules or {}

    def can_handle(self, url: str) -> bool:
        lowered = (url or "").lower()
        return any(d in lowered for d in self._domains)

    async def resolve(self, url: str, proxy: Optional[str] = None) -> Optional[MediaCandidate]:
        ydl_opts = {
            "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "socket_timeout": 15,
            "extractor_retries": 3,
            "noplaylist": True,
            
            # --- YOUTUBE BYPASS PROTOCOL (per current yt-dlp guidance) ---
            
            # 1. Prefer safer clients; explicitly avoid tv to prevent DRM/format issues
            "extractor_args": {
                "youtube": {
                    "player_client": ["default", "-tv", "web_safari", "web_embedded"],
                }
            },
            
            # 2. Dynamic impersonation: uses curl-cffi Chrome TLS fingerprinting if available
            #    (wrapped in try/export to keep yt-dlp[default] installs working)
            **(
                {"impersonate": "chrome"}
                if "curl_cffi" in sys.modules
                else {}
            ),
            
            # 3. Light rate-limiting for batch stability (not primary bypass)
            "sleep_requests": 1.5,
            
            # 4. (Optional) Cookie authentication for age/sign-in/CAPTCHA walls
            # "cookiefile": "/path/to/your/youtube_cookies.txt",
            
            # 5. Optional IPv4 binding if you're seeing IPv6-specific bans
            # "source_address": "0.0.0.0",
        }

        if proxy:
            ydl_opts["proxy"] = proxy

        def _extract() -> dict:
            with YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await asyncio.to_thread(_extract)
        except (DownloadError, ExtractorError, OSError) as exc:
            error_str = str(exc).lower()
            if any(kw in error_str for kw in ['private', 'unavailable', 'no video', 'deleted']):
                raise ProviderError("🔒 Video is private, deleted, or unavailable. Please choose another.", retryable=False) from exc
            elif any(kw in error_str for kw in ['age', 'restricted', 'members only', 'login required', 'sign in']):
                raise ProviderError("👨🚫 Age-restricted or login-required content.", retryable=False) from exc
            elif any(kw in error_str for kw in ['region', 'geo']):
                raise ProviderError("🌍 Video is region-blocked.", retryable=False) from exc
            elif any(kw in error_str for kw in ['bot', '403 forbidden']):
                raise ProviderError("🤖 YouTube bot-protection active. Retrying shortly.", retryable=True) from exc
            
            raise ProviderError(f"Failed to resolve {self.name} media", retryable=True) from exc

        if not info:
            return None

        direct_url = info.get("url")
        normalized_ext, media_type = normalized_media_descriptor(
            ext=str(info.get("ext") or ""),
            media_type=str(info.get("media_type") or ""),
        )
        subtype = self._infer_subtype(url)
        duration = info.get("duration")
        provider_id = info.get("id")

        return MediaCandidate(
            url=url,
            source=self.name,
            title=info.get("title") or f"{self.name.title()} clip",
            duration_seconds=float(duration) if duration is not None else None,
            file_size_bytes=info.get("filesize") or info.get("filesize_approx"),
            media_type=media_type,
            direct_url=direct_url,
            thumbnail_url=info.get("thumbnail"),
            extra={
                "id": provider_id,
                "stable_name": f"{self.name}-{provider_id or 'unknown'}{normalized_ext}",
                "subtype": subtype,
                "normalized_extension": normalized_ext,
                "http_headers": info.get("http_headers", {}),
            },
        )

    def _infer_subtype(self, url: str) -> str:
        lowered = (url or "").lower()
        for marker, subtype in self._subtype_rules.items():
            if marker in lowered:
                return subtype
        return "post"

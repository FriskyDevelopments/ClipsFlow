"""Generic yt-dlp backed provider for social platforms."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import importlib.util
import logging
import os
from typing import Optional

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError, YoutubeDLError

from config.settings import get_settings
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
        settings = get_settings()
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
            #    (wrapped in feature detection to keep yt-dlp[default] installs working)
            **(
                {"impersonate": settings.ytdlp_impersonate}
                if settings.ytdlp_impersonate and importlib.util.find_spec("curl_cffi")
                else {}
            ),
            
            # 3. Light rate-limiting for batch stability (not primary bypass)
            "sleep_requests": 1.5,
            
            # 4. (Optional) Cookie authentication for age/sign-in/CAPTCHA walls
            # "cookiefile": "/path/to/your/youtube_cookies.txt",
            
            # 5. Optional IPv4 binding if you're seeing IPv6-specific bans
            # "source_address": "0.0.0.0",
        }

        cookiefile = self._cookiefile_from_settings(settings)
        if cookiefile:
            ydl_opts["cookiefile"] = cookiefile

        if proxy:
            ydl_opts["proxy"] = proxy

        def _extract(options: dict) -> dict:
            with YoutubeDL(options) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await asyncio.to_thread(_extract, ydl_opts)
        except YoutubeDLError as exc:
            if ydl_opts.get("impersonate") and "impersonate target" in str(exc).lower():
                logger.warning(
                    "yt-dlp impersonation target unavailable; retrying without impersonation: %s",
                    ydl_opts["impersonate"],
                )
                fallback_opts = {key: value for key, value in ydl_opts.items() if key != "impersonate"}
                try:
                    info = await asyncio.to_thread(_extract, fallback_opts)
                except (DownloadError, ExtractorError, OSError) as fallback_exc:
                    raise self._provider_error_from_exception(fallback_exc) from fallback_exc
            else:
                raise self._provider_error_from_exception(exc) from exc
        except (DownloadError, ExtractorError, OSError) as exc:
            raise self._provider_error_from_exception(exc) from exc

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

    def _provider_error_from_exception(self, exc: Exception) -> ProviderError:
        error_str = str(exc).lower()
        if any(
            kw in error_str
            for kw in [
                "confirm you're not a bot",
                "confirm you are not a bot",
                "not a bot",
                "bot",
                "403 forbidden",
                "too many requests",
                "429",
            ]
        ):
            return ProviderError("🤖 YouTube bot-protection active. Retrying shortly.", retryable=True)
        if any(kw in error_str for kw in ["private", "unavailable", "no video", "deleted"]):
            return ProviderError("🔒 Video is private, deleted, or unavailable. Please choose another.", retryable=False)
        if any(kw in error_str for kw in ["age", "restricted", "members only", "login required", "sign in"]):
            return ProviderError("👨🚫 Age-restricted or login-required content.", retryable=False)
        if any(kw in error_str for kw in ["region", "geo"]):
            return ProviderError("🌍 Video is region-blocked.", retryable=False)

        return ProviderError(f"Failed to resolve {self.name} media", retryable=True)

    def _cookiefile_from_settings(self, settings) -> str | None:
        if settings.ytdlp_cookie_file:
            return settings.ytdlp_cookie_file
        if not settings.ytdlp_cookies_b64:
            return None

        try:
            cookie_bytes = base64.b64decode(settings.ytdlp_cookies_b64, validate=True)
        except ValueError as exc:
            raise ProviderError("Provider cookie configuration is invalid.", retryable=False) from exc

        os.makedirs(settings.download_dir, exist_ok=True)
        digest = hashlib.sha256(cookie_bytes).hexdigest()[:16]
        cookie_path = os.path.join(settings.download_dir, f"ytdlp-cookies-{digest}.txt")
        if not os.path.exists(cookie_path):
            fd = os.open(cookie_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as fh:
                fh.write(cookie_bytes)
        return cookie_path

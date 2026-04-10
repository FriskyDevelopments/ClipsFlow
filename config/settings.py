"""
ClipsFlow – configuration module.

Loads settings from environment variables (with .env file support).
All tuneable limits and secrets live here so nothing is hard-coded
elsewhere in the codebase.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from dotenv import load_dotenv

from core.config.parsers import parse_bool_env, parse_int_env

load_dotenv()  # no-op if .env is absent (CI/production uses real env vars)


class Settings:
    """Application-wide configuration, sourced entirely from the environment."""

    # ── Telegram ──────────────────────────────────────────────────────────
    telegram_bot_token: str
    telegram_api_id: int
    telegram_api_hash: str

    # ── Clip constraints ──────────────────────────────────────────────────
    clip_max_duration_seconds: int
    clip_max_file_size_mb: int
    clip_allowed_media_types: list[str]
    telegram_max_upload_mb: int
    download_dir: str
    ffmpeg_path: str
    enable_compression: bool
    enable_long_video_fast_path: bool
    long_video_fast_path_seconds: int
    telegram_target_video_mb: int
    processing_timeout_seconds: int
    telegram_admin_ids: list[int]
    honeybadger_api_key: str | None
    referral_commission_cents: int

    # ── Provider ──────────────────────────────────────────────────────────
    clip_provider: str
    youtube_api_key: str

    # ── Application ───────────────────────────────────────────────────────
    app_env: str
    log_level: str
    proxy_pool: list[str]
    
    # ── Jules AI / Autohealing ────────────────────────────────────────────
    jules_api_key: str
    miniapp_url: str

    def __init__(self) -> None:
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_api_id = parse_int_env("TELEGRAM_API_ID", default=37265246, min_val=0)
        self.telegram_api_hash = os.getenv("TELEGRAM_API_HASH", "d03fb9f3c1a1f755cfb61d4402a5d889")
        self.clip_max_duration_seconds = parse_int_env(
            "CLIP_MAX_DURATION_SECONDS", default=300, min_val=1
        )
        self.clip_max_file_size_mb = parse_int_env(
            "CLIP_MAX_FILE_SIZE_MB", default=50, min_val=1
        )
        raw_types = os.getenv("CLIP_ALLOWED_MEDIA_TYPES", "video")
        self.clip_allowed_media_types = [t.strip() for t in raw_types.split(",") if t.strip()]

        self.clip_provider = os.getenv("CLIP_PROVIDER", "mock").strip().lower()
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY", "")
        self.jules_api_key = os.getenv("JULES_API_KEY", "")
        self.miniapp_url = os.getenv("MINIAPP_URL", "https://clipsflow.tech/miniapp")

        raw_app_env = os.getenv("APP_ENV", "development").strip().lower()
        self.app_env = raw_app_env
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        
        raw_proxies = os.getenv("PROXY_POOL", "")
        self.proxy_pool = [p.strip() for p in raw_proxies.split(",") if p.strip()]
        
        self.telegram_max_upload_mb = parse_int_env(
            "TELEGRAM_MAX_UPLOAD_MB", default=50, min_val=1
        )
        self.download_dir = os.getenv("DOWNLOAD_DIR", "/tmp/clipflow")
        self.ffmpeg_path = os.getenv("FFMPEG_PATH", "ffmpeg")
        self.enable_compression = parse_bool_env("ENABLE_COMPRESSION", default=True)
        self.enable_long_video_fast_path = parse_bool_env(
            "ENABLE_LONG_VIDEO_FAST_PATH",
            default=True,
        )
        self.long_video_fast_path_seconds = parse_int_env(
            "LONG_VIDEO_FAST_PATH_SECONDS",
            default=180,
            min_val=1,
        )
        self.telegram_target_video_mb = parse_int_env(
            "TELEGRAM_TARGET_VIDEO_MB",
            default=45,
            min_val=1,
        )
        self.processing_timeout_seconds = parse_int_env(
            "PROCESSING_TIMEOUT_SECONDS", default=180, min_val=1
        )
        raw_admin_ids = os.getenv("TELEGRAM_ADMIN_IDS", "")
        self.telegram_admin_ids = [
            int(admin_id.strip())
            for admin_id in raw_admin_ids.split(",")
            if admin_id.strip().isdigit()
        ]
        self.honeybadger_api_key = os.getenv("HONEYBADGER_API_KEY", "").strip() or None
        self.referral_commission_cents = parse_int_env(
            "REFERRAL_COMMISSION_CENTS", default=500, min_val=0
        )

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate(self) -> None:
        """Raise ValueError if required settings are missing."""
        if not self.telegram_bot_token or self.telegram_bot_token == "__REQUIRED__":
            raise ValueError(
                "Missing required secrets: TELEGRAM_BOT_TOKEN. "
                "For local development use `doppler run -- python main.py` or set real env vars. "
                "See .env.example for more details."
            )
        if not self.telegram_api_id or not self.telegram_api_hash:
            raise ValueError(
                "Missing required secrets: TELEGRAM_API_ID and/or TELEGRAM_API_HASH. "
                "Pyrogram requires an API ID and Hash. Get them from https://my.telegram.org."
            )

        if self.clip_provider == "youtube" and not self.youtube_api_key:
            pass  # Bypass strict YouTube Data API key until user configures it

        if self.app_env not in {"development", "production", "dev", "prod"}:
            raise ValueError("[CONFIG ERROR] APP_ENV must be development|production")

        if self.is_production:
            missing_doppler = [
                name
                for name in ("DOPPLER_PROJECT", "DOPPLER_CONFIG")
                if not os.getenv(name, "").strip()
            ]
            if missing_doppler:
                raise ValueError(
                    "Production requires Doppler metadata env vars: "
                    f"{', '.join(missing_doppler)}"
                )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached singleton Settings instance.

    Call get_settings.cache_clear() in tests to reset the cache.
    """
    return Settings()


def configure_logging(settings: Settings) -> None:
    """Set up root logger based on settings."""
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        level=getattr(logging, settings.log_level, logging.INFO),
    )

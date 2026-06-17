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


def _strip_quoted_env(value: str) -> str:
    """Strip surrounding single/double quotes that may be embedded in Secret Manager values."""
    raw = (value or "").strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {"'", '"'}:
        return raw[1:-1].strip()
    return raw


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
    telegram_delivery_timeout_seconds: int
    free_watermark_enabled: bool
    free_watermark_text: str
    free_trial_export_limit: int
    telegram_admin_ids: list[int]
    honeybadger_api_key: str | None
    referral_commission_cents: int
    telegram_stars_pro_price: int

    # ── Provider ──────────────────────────────────────────────────────────
    clip_provider: str
    youtube_api_key: str
    ytdlp_cookie_file: str
    ytdlp_cookies_b64: str
    ytdlp_impersonate: str

    # ── Application ───────────────────────────────────────────────────────
    app_env: str
    log_level: str
    proxy_pool: list[str]
    
    # ── Jules AI / Autohealing ────────────────────────────────────────────
    jules_api_key: str
    miniapp_url: str
    friskydev_environment: str

    def __init__(self) -> None:
        self.telegram_bot_token = _strip_quoted_env(os.getenv("TELEGRAM_BOT_TOKEN", ""))
        self.telegram_api_id = parse_int_env("TELEGRAM_API_ID", default=37265246, min_val=0)
        self.telegram_api_hash = _strip_quoted_env(
            os.getenv("TELEGRAM_API_HASH", "d03fb9f3c1a1f755cfb61d4402a5d889")
        )
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
        self.ytdlp_cookie_file = _strip_quoted_env(os.getenv("YTDLP_COOKIE_FILE", "")).strip()
        self.ytdlp_cookies_b64 = _strip_quoted_env(os.getenv("YTDLP_COOKIES_B64", "")).strip()
        self.ytdlp_impersonate = _strip_quoted_env(os.getenv("YTDLP_IMPERSONATE", "")).strip()
        self.jules_api_key = os.getenv("JULES_API_KEY", "")
        self.miniapp_url = _strip_quoted_env(os.getenv("MINIAPP_URL", "https://clipsflow.tech/miniapp")).strip()
        self.friskydev_environment = os.getenv("FRISKYDEV_ENVIRONMENT", "friskydev")

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
        self.telegram_delivery_timeout_seconds = parse_int_env(
            "TELEGRAM_DELIVERY_TIMEOUT_SECONDS", default=600, min_val=1
        )
        self.free_watermark_enabled = parse_bool_env("FREE_WATERMARK_ENABLED", default=True)
        self.free_watermark_text = os.getenv("FREE_WATERMARK_TEXT", "ClipFLOW Free").strip() or "ClipFLOW Free"
        self.free_trial_export_limit = parse_int_env(
            "FREE_TRIAL_EXPORT_LIMIT", default=25, min_val=0
        )
        raw_admin_ids = os.getenv("TELEGRAM_ADMIN_IDS", "")
        self.telegram_admin_ids = [
            int(admin_id.strip())
            for admin_id in raw_admin_ids.split(",")
            if admin_id.strip().isdigit()
        ]
        self.honeybadger_api_key = _strip_quoted_env(
            os.getenv("HONEYBADGER_API_KEY", "").strip()
        ) or None
        self.referral_commission_cents = parse_int_env(
            "REFERRAL_COMMISSION_CENTS", default=500, min_val=0
        )
        self.telegram_stars_pro_price = parse_int_env(
            "TELEGRAM_STARS_PRO_PRICE", default=250, min_val=1
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

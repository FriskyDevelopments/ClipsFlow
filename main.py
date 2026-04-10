"""
main.py – The ClipsFlow Bot Entrypoint.
"""
import logging
import sys

from pyrogram import Client

from config.settings import Settings, configure_logging, get_settings
from core.pipeline import ClipPipeline
from providers.registry import ProviderRegistry
from providers.factory import create_provider
from services.clip_validator import ClipValidator
from services.db import init_db
from services.media_processor import MediaProcessor
from bot.handlers import setup_handlers

logger = logging.getLogger(__name__)


def build_registry(settings: Settings) -> ProviderRegistry:
    """Build the provider registry from the configured CLIP_PROVIDER."""
    # Split CLIP_PROVIDER into a list of names, filtering out empty ones
    provider_names = [p.strip() for p in settings.clip_provider.split(",") if p.strip()]
    if not provider_names:
        raise ValueError("CLIP_PROVIDER must be set (e.g., 'direct,youtube,mock')")

    providers = []
    for name in provider_names:
        providers.append(create_provider(name))
    return ProviderRegistry(providers)


def create_app(settings: Settings):
    """Initialise and return the Telegram Pyrogram Client and its dependencies."""
    # 1. Setup core services
    registry = build_registry(settings)
    init_db()
    validator = ClipValidator(settings)
    media_processor = MediaProcessor(settings)

    # 2. Build pipeline
    pipeline = ClipPipeline(registry, validator, media_processor)

    # 3. Create Pyrogram Client
    app = Client(
        "clipflow_bot",
        bot_token=settings.telegram_bot_token,
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
        in_memory=True, # Prevent it from writing a .session file locally
    )

    # 4. Attach handlers
    setup_handlers(app, pipeline, media_processor, settings)

    return app


def main() -> None:
    """
    Main entrypoint. Fails fast if configuration is missing,
    then runs the bot until interrupted.
    """
    settings = get_settings()

    def _sanitize(msg: str) -> str:
        """Strip raw secrets from log messages if they accidentally leak into an error."""
        res = msg
        for secret in [settings.telegram_bot_token, settings.telegram_api_hash]:
            if secret and len(secret) > 8:
                res = res.replace(secret, "[REDACTED]")
        return res

    try:
        settings.validate()
        configure_logging(settings)
        
        # Add basic redaction to the root logger to catch any accidental leakage
        class RedactionFilter(logging.Filter):
            def filter(self, record):
                try:
                    if record.msg and isinstance(record.msg, str):
                        record.msg = _sanitize(record.msg)
                    if record.args:
                        if isinstance(record.args, dict):
                            record.args = {k: _sanitize(v) if isinstance(v, str) else v for k, v in record.args.items()}
                        else:
                            new_args = []
                            for arg in record.args:
                                if isinstance(arg, str):
                                    new_args.append(_sanitize(arg))
                                else:
                                    new_args.append(arg)
                            record.args = tuple(new_args)
                    
                    # Also null out exc_info/exc_text if either secret string appears in the exception representation.
                    if record.exc_info or record.exc_text:
                        import traceback
                        exc_str = record.exc_text or "".join(traceback.format_exception(*record.exc_info)) if record.exc_info else ""
                        for secret in [settings.telegram_bot_token, settings.telegram_api_hash]:
                            if secret and len(secret) > 8 and secret in exc_str:
                                record.exc_info = None
                                record.exc_text = None
                                record.msg = f"{record.msg} [REDACTED EXCEPTION DATA]"
                                break
                except Exception:
                    pass
                return True

        logging.getLogger().addFilter(RedactionFilter())

        if settings.honeybadger_api_key:
            try:
                import honeybadger
                honeybadger.configure(api_key=settings.honeybadger_api_key, env=settings.app_env)
                logger.info("Honeybadger initialized for APM and Error Tracking.")
            except ImportError:
                logger.warning("honeybadger package not installed – APM disabled.")

    except ValueError as e:
        # Fails fast on invalid environment config – sanitized to prevent secret leakage
        print(f"[ERROR] Configuration invalid: {_sanitize(str(e))}", file=sys.stderr)
        sys.exit(1)

    try:
        app = create_app(settings)
    except Exception:
        logger.exception("Failed to create application – check secrets and connectivity")
        sys.exit(1)

    logger.info("ClipsFlow starting via Pyrogram...")
    app.run()


if __name__ == "__main__":
    main()

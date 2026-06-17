"""
bot.handlers – Telegram bot command and message handlers.

Responsibilities:
  - Receive updates from Telegram (commands + messages).
  - Delegate all business logic to the pipeline.
  - Return user-friendly replies.

The bot layer is intentionally thin.  If you find yourself adding
business logic here, move it to core/ or services/ instead.
"""

from __future__ import annotations

import logging
import asyncio
import json
import os
import random
import time
import contextlib
from collections import defaultdict

# Global YouTube throttling (shared across all users)
YOUTUBE_RATE_LIMITER = asyncio.Semaphore(3)  # Max 3 concurrent YouTube requests
YOUTUBE_RECENT_REQUESTS = defaultdict(list)  # Per-domain burst protection

async def is_youtube_safe(domain: str) -> bool:
    """Check if we can safely make a YouTube request (burst + concurrency protection)"""
    now = time.time()
    # Burst limit: max 10 requests per minute per domain
    recent = YOUTUBE_RECENT_REQUESTS[domain]
    recent = [t for t in recent if now - t < 60]  # Last 60s
    if len(recent) >= 10:
        return False
    recent.append(now)
    YOUTUBE_RECENT_REQUESTS[domain] = recent
    await YOUTUBE_RATE_LIMITER.acquire()
    return True

async def release_youtube_slot():
    """Release YouTube semaphore after request completes"""
    YOUTUBE_RATE_LIMITER.release()

from services.ghost_protocol import get_cached_ghost_pointer, store_ghost_pointer

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    CallbackQuery,
)
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified, RPCError
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.handlers import RawUpdateHandler
from pyrogram.raw import functions, types

from bot.ascii_art import ASCII_CONCEPTUAL_LOADERS
from config.settings import Settings
from core.models import ClipResult, ClipStatus, MediaCandidate, ProcessedMedia
from core.pipeline import ClipPipeline
from core.url_safety import is_valid_http_url, normalize_url, redact_url
from services.db import (
    ensure_user,
    ensure_friskydev_account,
    get_free_trial_state,
    get_user,
    mark_telegram_stars_payment,
    mark_keyboard_installed,
    record_free_export,
)
from services.media_processor import MediaProcessor
from services.stars import parse_pro_stars_payload, send_pro_stars_invoice

logger = logging.getLogger(__name__)

# ── Aesthetic Loaders ─────────────────────────────────────────────────────

def _escape_html(text: str) -> str:
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def glitch_string(text: str, intensity: float = 0.01) -> str:
    """Randomly inserts Zalgo/glitch characters into a string based on intensity."""
    glitch_chars = [chr(i) for i in range(0x0300, 0x036F)]
    out = ""
    for char in text:
        out += char
        if char != "\n" and random.random() < intensity:
            out += random.choice(glitch_chars) * random.randint(1, 3)
    return out


# ── Message templates ─────────────────────────────────────────────────────

_START_TEXT = (
    "<b>Welcome to ClipFLOW.</b>\n\n"
    "Paste any video link. Your clip arrives in seconds.\n\n"
    "<i>YouTube · TikTok · Twitter / X · Instagram · and more</i>\n\n"
    "/help · /miniapp"
)

_HELP_TEXT = (
    "<b>ClipFLOW</b>\n\n"
    "Paste any supported video URL. ClipFLOW resolves, validates, "
    "and delivers the clip directly to you.\n\n"
    "<b>Commands</b>\n"
    "/start    — Welcome\n"
    "/help     — This message\n"
    "/miniapp  — Open the web app"
)

_UNKNOWN_COMMAND_TEXT = "Unrecognised command.  Try /help."


def _is_web_app_data(_, __, message: Message) -> bool:
    return bool(getattr(message, "web_app_data", None))


web_app_data_filter = filters.create(_is_web_app_data)


# ── Handler factory ───────────────────────────────────────────────────────

class BotHandlers:
    """
    Encapsulates the Telegram handlers with their required dependencies.
    """
    def __init__(self, app: Client, pipeline: ClipPipeline, media_processor: MediaProcessor, settings: Settings):
        self.pipeline = pipeline
        self.media_processor = media_processor
        self.settings = settings
        self._me_username: str | None = None
        self._rate_limits: dict[int, float] = {}
        self._invalid_link_prompts: dict[int, float] = {}
        
        self.inline_menu = self._build_inline_menu(include_miniapp_button=True)
        self.frisky_signal_menu = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ Transmit Frisky Signal", callback_data="menu:frisky_signal_confirm")],
                [InlineKeyboardButton("❌ Abort", callback_data="menu:back_to_main")],
            ]
        )
        self.pro_approval_menu = self._build_pro_menu(include_miniapp_button=True)

    @staticmethod
    def _is_valid_miniapp_url(url: str) -> bool:
        return is_valid_http_url(url)

    @staticmethod
    def _supports_inline_miniapp(chat_type: object | None) -> bool:
        normalized = getattr(chat_type, "value", chat_type)
        if not isinstance(normalized, str):
            return False
        return normalized.lower() == "private"

    def _menu_for_chat(self, chat) -> InlineKeyboardMarkup:
        include_miniapp = self._supports_inline_miniapp(getattr(chat, "type", None))
        return self._build_inline_menu(include_miniapp_button=include_miniapp)

    def _pro_menu_for_chat(self, chat) -> InlineKeyboardMarkup:
        include_miniapp = self._supports_inline_miniapp(getattr(chat, "type", None))
        return self._build_pro_menu(include_miniapp_button=include_miniapp)

    def _normalize_miniapp_url(self, base_url: str, query: str | None = None) -> str | None:
        cleaned = (base_url or "").strip()
        if not self._is_valid_miniapp_url(cleaned):
            logger.warning("Invalid MINIAPP_URL for Telegram Web App button: %r", cleaned)
            return None

        if not query:
            return cleaned

        suffix = query.lstrip("?")
        joiner = "&" if "?" in cleaned else "?"
        return f"{cleaned}{joiner}{suffix}"

    def _build_inline_menu(self, include_miniapp_button: bool = False) -> InlineKeyboardMarkup:
        rows: list[list[InlineKeyboardButton]] = []

        if include_miniapp_button:
            miniapp_url = self._normalize_miniapp_url(self.settings.miniapp_url)
            if miniapp_url:
                rows.append([InlineKeyboardButton("🚀 Launch Elite Portal", web_app=WebAppInfo(url=miniapp_url))])

        rows.append([
            InlineKeyboardButton("⚙️ Admin Controls", callback_data="menu:admin_controls"),
            InlineKeyboardButton("🚨 Frisky Signal", callback_data="menu:frisky_signal"),
        ])

        return InlineKeyboardMarkup(rows)

    def _build_pro_menu(self, include_miniapp_button: bool = False) -> InlineKeyboardMarkup:
        rows: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton("✅ Create FriskyDev Account", callback_data="pro:create_account")],
            [InlineKeyboardButton(f"⭐ Pay {self.settings.telegram_stars_pro_price} Stars", callback_data="pro:pay_stars")],
            [InlineKeyboardButton("❌ Not now", callback_data="menu:back_to_main")],
        ]

        if include_miniapp_button:
            miniapp_url = self._normalize_miniapp_url(self.settings.miniapp_url, "intent=pro")
            if miniapp_url:
                rows.insert(2, [InlineKeyboardButton("✨ Open Pro Mini App", web_app=WebAppInfo(url=miniapp_url))])

        return InlineKeyboardMarkup(rows)

    async def _ensure_user(self, message: Message) -> dict | None:
        user = message.from_user
        if not user:
            return None

        return await asyncio.to_thread(ensure_user, "telegram", str(user.id), user.username)

    async def _ensure_friskydev_account_for_user(self, user) -> dict | None:
        if not user:
            return None

        return await asyncio.to_thread(
            ensure_friskydev_account,
            "telegram",
            str(user.id),
            user.username,
            self.settings.friskydev_environment,
        )

    async def start(self, client: Client, message: Message) -> None:
        await self._ensure_user(message)

        args = message.command[1:] if message.command else []
        if args and args[0].strip().lower() in {"pro", "upgrade"}:
            await self.pro_command(client, message)
            return
        
        video_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "welcome_videos")
        
        def _get_videos():
            if os.path.exists(video_dir):
                return [f for f in os.listdir(video_dir) if f.lower().endswith(('.mp4', '.mov', '.gif'))]
            return []
            
        videos = await asyncio.to_thread(_get_videos)
        
        user = message.from_user
        safe_user_name = _escape_html(user.username or user.first_name) if user else "there"
        start_msg = _START_TEXT.replace("<b>Welcome to ClipFLOW.</b>", f"<b>Welcome, {safe_user_name}.</b>")
        markup = self._menu_for_chat(message.chat)

        if videos:
            vid = random.choice(videos)
            vid_path = os.path.join(video_dir, vid)
            try:
                await client.send_animation(
                    chat_id=message.chat.id,
                    animation=vid_path,
                    caption=start_msg,
                    parse_mode=ParseMode.HTML,
                    reply_markup=markup
                )
                return
            except Exception as e:
                logger.error("Failed to send welcome video: %s", e)
        
        await message.reply_text(start_msg, parse_mode=ParseMode.HTML, reply_markup=markup)

    async def help_command(self, client: Client, message: Message) -> None:
        await message.reply_text(_HELP_TEXT, parse_mode=ParseMode.HTML)

    async def pro_command(self, client: Client, message: Message) -> None:
        await self._ensure_user(message)

        user = message.from_user
        safe_user_name = _escape_html(user.username or user.first_name) if user else "there"

        await message.reply_text(
            "✨ <b>Upgrade to Pro</b>\n\n"
            f"{safe_user_name}, approve the account link below and I’ll create your "
            f"<b>FriskyDev</b> account in <code>{_escape_html(self.settings.friskydev_environment)}</code>.\n\n"
            f"Then pay <b>{self.settings.telegram_stars_pro_price} Telegram Stars</b> to unlock Pro while Stripe is on pause.",
            parse_mode=ParseMode.HTML,
            reply_markup=self._pro_menu_for_chat(message.chat),
        )

    async def _get_bot_username(self, client: Client) -> str:
        if self._me_username is None:
            me = await client.get_me()
            self._me_username = me.username
        return self._me_username

    async def miniapp_command(self, client: Client, message: Message) -> None:
        await self._ensure_user(message)
        username = await self._get_bot_username(client)
        app_link = f"https://t.me/{username}/miniapp"
        
        await message.reply_text(
            f"<b>ClipFLOW</b>\n\n<a href=\"{app_link}\">Open the web app →</a>",
            parse_mode=ParseMode.HTML,
            reply_markup=self._menu_for_chat(message.chat)
        )

    async def _loader_task(self, client: Client, message: Message, base_text: str, reply_markup: InlineKeyboardMarkup | None, art: str):
        """Asynchronously update the processing message with truthful live state."""
        start_time = time.time()

        stages = [
            (0,  "Opening a clean workspace"),
            (3,  "Reading the source"),
            (8,  "Retrieving media"),
            (16, "Refining the export"),
            (28, "Checking delivery format"),
        ]
        pulse = ("soft", "steady", "focused", "almost ready")

        while True:
            try:
                elapsed = time.time() - start_time
                stage_text = stages[0][1]
                for threshold, label in stages:
                    if elapsed >= threshold:
                        stage_text = label

                status = pulse[int(elapsed / 4) % len(pulse)]
                elapsed_label = f"{int(elapsed)}s"

                loader_text = (
                    f"<b>{stage_text}</b>\n"
                    f"<code>live system · {status} · {elapsed_label}</code>\n\n"
                    f"{base_text}"
                )

                await message.edit_text(  # pyright: ignore[reportUnusedCallResult]
                    loader_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
            except asyncio.CancelledError:
                break
            except MessageNotModified:
                pass
            except Exception as e:
                logger.debug("Loader tick error: %s", e)
            await asyncio.sleep(1.5)

    async def handle_link(self, client: Client, message: Message) -> None:
        """Handle plain text only when it looks like a clip link."""
        text = (message.text or "").strip()
        clean_url = normalize_url(text)
        if not is_valid_http_url(clean_url):
            user_id = (
                message.from_user.id
                if message.from_user
                else message.chat.id
                if message.chat
                else 0
            )
            now = time.time()
            last_prompt = self._invalid_link_prompts.get(user_id, 0)
            if now - last_prompt >= 30:
                self._invalid_link_prompts[user_id] = now
                await message.reply_text("Send a video link when you're ready. Example: https://...")
            return

        await self._process_url_message(client, message, clean_url)

    async def handle_web_app_data(self, client: Client, message: Message) -> None:
        """Handle payloads submitted by the Telegram Mini App."""
        await self._ensure_user(message)

        payload_text = message.web_app_data.data if message.web_app_data else ""
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError:
            await message.reply_text("Mini app sent an unreadable request. Please reopen it and try again.")
            return

        if payload.get("action") != "process_clip":
            await message.reply_text("Mini app action is not supported yet.")
            return

        url = str(payload.get("url") or "").strip()
        if not url:
            await message.reply_text("Paste a video URL in the mini app first.")
            return

        await self._process_url_message(client, message, url)

    async def _send_with_delivery_timeout(
        self,
        send_call,
        processing_msg: Message | None = None,
        msg_text: str | None = None,
        markup: InlineKeyboardMarkup | None = None,
        progress_state: dict | None = None,
    ):
        heartbeat_task = None
        if processing_msg is not None and msg_text is not None:
            state = progress_state if progress_state is not None else {}
            state.setdefault("upload_started_at", time.time())
            heartbeat_task = asyncio.create_task(
                self._upload_progress_heartbeat(processing_msg, msg_text, markup, state)
            )
        try:
            return await asyncio.wait_for(
                send_call,
                timeout=self.settings.telegram_delivery_timeout_seconds,
            )
        finally:
            if heartbeat_task is not None:
                if progress_state is not None:
                    progress_state["completed"] = True
                heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await heartbeat_task

    async def _upload_progress_heartbeat(
        self,
        processing_msg: Message,
        msg_text: str,
        markup: InlineKeyboardMarkup | None,
        state: dict,
    ) -> None:
        """Emit progress heartbeats when callback updates stall near the end."""
        while True:
            await asyncio.sleep(8.0)
            if state.get("completed"):
                return

            now = time.time()
            last_edit = state.get("last_edit", 0.0)
            if now - last_edit < 8.0:
                continue

            percent = min(int(state.get("last_percent", 0) or 0), 95)
            phase = state.get("phase", "uploading")
            elapsed_seconds = int(now - state.get("upload_started_at", now))
            finalizing_started = state.get("finalizing_started_at", now)

            if phase == "finalizing":
                finalizing_seconds = int(now - finalizing_started)
                if finalizing_seconds >= 120:
                    status = (
                        "Telegram has the full upload. Delivery confirmation is taking longer than usual."
                        f"\nFinalization time: {finalizing_seconds}s."
                    )
                else:
                    status = f"Telegram has the full upload. Waiting for delivery confirmation. ({elapsed_seconds}s)"
            elif percent >= 95:
                status = f"Uploading to Telegram · final handoff window · {elapsed_seconds}s"
            else:
                status = f"Uploading to Telegram · {percent}% · {elapsed_seconds}s"

            state["last_edit"] = now
            with contextlib.suppress(MessageNotModified, RPCError):
                await processing_msg.edit_text(
                    f"<b>Delivery check</b>\n"
                    f"<code>{status}</code>\n\n"
                    f"{msg_text}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=markup,
                )

    async def _telegram_upload_progress(
        self,
        current: int,
        total: int,
        processing_msg: Message,
        msg_text: str,
        markup: InlineKeyboardMarkup | None,
        state: dict,
    ) -> None:
        """Surface real Telegram upload progress without editing on every chunk."""
        now = time.time()
        raw_percent = min(int((current / total) * 100), 100) if total else 0
        display_percent = min(raw_percent, 95)
        last_edit = state.get("last_edit", 0.0)
        last_percent = state.get("last_percent", -1)
        phase = state.get("phase", "uploading")
        is_finalizing = total and current >= total

        if is_finalizing:
            state["phase"] = "finalizing"
            state.setdefault("finalizing_started_at", now)
            phase = "finalizing"

        if not is_finalizing and phase == "uploading" and display_percent < last_percent + 5:
            # If upload bytes plateau, still emit an occasional heartbeat.
            if now - last_edit < 8.0:
                return
        elif phase == "finalizing" and now - last_edit < 1.0:
            return

        state["last_edit"] = now
        state["last_percent"] = display_percent
        if phase == "finalizing":
            status = "Telegram has the full upload. Waiting for delivery confirmation."
        elif raw_percent >= 95:
            status = "Uploading to Telegram · final handoff window"
        else:
            status = f"Uploading to Telegram · {display_percent}%"

        with contextlib.suppress(MessageNotModified, RPCError):
            await processing_msg.edit_text(
                f"<b>Delivery check</b>\n"
                f"<code>{status}</code>\n\n"
                f"{msg_text}",
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )

    @staticmethod
    def _video_delivery_kwargs(media: ProcessedMedia) -> dict:
        kwargs = {"supports_streaming": True}
        if media.duration:
            kwargs["duration"] = int(media.duration)
        return kwargs

    async def _process_url_message(self, client: Client, message: Message, url: str) -> None:
        """Process a URL from either chat text or Telegram Mini App data."""
        await self._ensure_user(message)

        clean_url = normalize_url(url)
        if not is_valid_http_url(clean_url):
            await message.reply_text("Paste a valid video link (for example, https://...) and I’ll start processing.")
            return
        
        # ── Rate Limiting ──────────────────────────────────────────────────
        user_id = message.from_user.id if message.from_user else 0
        now = time.time()
        if user_id in self._rate_limits:
            elapsed = now - self._rate_limits[user_id]
            if elapsed < 2.0: # 2 seconds cooldown
                await message.reply_text("Please wait a moment before sending another link.")
                return
        self._rate_limits[user_id] = now
        # ───────────────────────────────────────────────────────────────────

        safe_url = redact_url(clean_url)
        user = message.from_user
        safe_user_name = _escape_html(user.username or user.first_name) if user else "unknown"
        safe_user_id = user.id if user else None
        logger.info(
            "Received link from user=%s id=%s: %s",
            safe_user_name,
            safe_user_id,
            safe_url,
        )

        user_record = await asyncio.to_thread(get_user, "telegram", str(safe_user_id)) if safe_user_id else None
        is_pro = user_record.get("is_pro") if user_record else False
        free_trial_state = None
        if safe_user_id and not is_pro:
            free_trial_state = await asyncio.to_thread(
                get_free_trial_state,
                "telegram",
                str(safe_user_id),
                self.settings.free_trial_export_limit,
            )
            if free_trial_state["exhausted"]:
                await message.reply_text(
                    "Your ClipsFlow trial runway is complete. Clean Pro access is the next step once billing opens.",
                )
                return
        
        if is_pro:
            msg_text = f"<b>On it, {safe_user_name}.</b>\n<i>Priority pipeline — moving fast.</i>"
        else:
            remaining = free_trial_state["remaining"] if free_trial_state else self.settings.free_trial_export_limit
            trial_note = (
                f"Watermarked trial export. {remaining} trial runs remain."
                if self.settings.free_trial_export_limit > 0
                else "Watermarked trial export."
            )
            msg_text = (
                f"<b>Processing your link, {safe_user_name}.</b>\n"
                f"<i>{trial_note}</i>"
            )

        markup = self._menu_for_chat(message.chat)

        art = random.choice(ASCII_CONCEPTUAL_LOADERS)

        initial_loader = (
            f"<b>Opening a clean workspace</b>\n"
            f"<code>live system · soft · 0s</code>\n\n"
            f"{msg_text}"
        )
        
        processing_msg = await message.reply_text(
            initial_loader, 
            parse_mode=ParseMode.HTML,
            reply_markup=markup
        )

        loader_task = asyncio.create_task(self._loader_task(client, processing_msg, msg_text, markup, art))

        try:
            # ── GHOST PROTOCOL (CACHE CHECK) ──
            cached = await get_cached_ghost_pointer(clean_url)
            if is_pro and cached and cached.get("file_id"):
                logger.info(f"Ghost cache hit! Bypassing pipeline for {safe_url}")
                result = ClipResult(
                    status=ClipStatus.SUCCESS,
                    original_url=clean_url,
                    candidate=MediaCandidate(url=clean_url, title="Cached Media"),
                    processed_media=ProcessedMedia(
                        file_path=None, 
                        duration=None, 
                        size_bytes=cached.get("file_size") or 0, 
                        telegram_file_id=cached.get("file_id")
                    )
                )
            else:
                lowered_url = clean_url.lower()
                is_yt = "youtube.com" in lowered_url or "youtu.be" in lowered_url
                acquired_slot = False
                
                if is_yt:
                    if not await is_youtube_safe("youtube.com"):
                        loader_task.cancel()
                        try:
                            await processing_msg.delete()
                        except RPCError:
                            pass
                        await message.reply_text("🚦 Server busy with YouTube requests. Please wait 30s and try again.")
                        return
                    acquired_slot = True
                    
                try:
                    result = await self.pipeline.process(clean_url)
                finally:
                    if acquired_slot:
                        await release_youtube_slot()
        finally:
            loader_task.cancel()
            try:
                await processing_msg.edit_text(
                    f"<b>Delivery check</b>\n"
                    f"<code>Telegram handoff is starting now.</code>\n\n"
                    f"{msg_text}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=markup,
                )
            except (MessageNotModified, RPCError):
                pass

        try:
            if result.is_ready and result.processed_media:
                media = result.processed_media
                original_processed_path = media.file_path
                watermarked_path: str | None = None
                if (
                    not is_pro
                    and self.settings.free_watermark_enabled
                    and media.file_path
                    and "video" in media.mime_type
                ):
                    try:
                        watermark_started_at = time.perf_counter()
                        watermarked_path = await self.media_processor.apply_free_watermark(media.file_path)
                        media = ProcessedMedia(
                            file_path=watermarked_path,
                            duration=media.duration,
                            size_bytes=os.path.getsize(watermarked_path),
                            mime_type=media.mime_type,
                        )
                        result.processed_media = media
                        logger.info(
                            "[TIMING] free_watermark user=%s seconds=%.3f output_bytes=%s",
                            safe_user_id,
                            time.perf_counter() - watermark_started_at,
                            media.size_bytes,
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.error("Watermark failed: user=%s url=%s error=%s", safe_user_id, safe_url, exc)
                        await processing_msg.edit_text(
                            "Delivery paused — the free export watermark could not be applied. Please try again.",
                        )
                        return

                size_mb = media.size_bytes / (1024 * 1024)
                
                # MiB, conservative ceiling below Telegram's 2,000 MB MTProto limit
                if size_mb > 1900.0:
                    await message.reply_text(
                        f"Large file detected ({size_mb:.0f} MB) — delivering in parts."
                    )
                    from core.video_chunker import chunk_video
                    loop = asyncio.get_running_loop()
                    chunks = []
                    sent_count = 0
                    try:
                        chunks = await loop.run_in_executor(None, chunk_video, media.file_path, 45)
                        for idx, chunk_file in enumerate(chunks, 1):
                            url_line = f"\n{result.original_url}" if idx == 1 else ""
                            try:
                                chunk_progress_state: dict = {"upload_started_at": time.time()}
                                await self._send_with_delivery_timeout(
                                    client.send_video(
                                        chat_id=message.chat.id,
                                        video=chunk_file,
                                        caption=f"Part {idx} of {len(chunks)}{url_line}",
                                        supports_streaming=True,
                                        progress=self._telegram_upload_progress,
                                        progress_args=(
                                            processing_msg,
                                            msg_text,
                                            markup,
                                            chunk_progress_state,
                                        ),
                                    ),
                                    processing_msg=processing_msg,
                                    msg_text=msg_text,
                                    markup=markup,
                                    progress_state=chunk_progress_state,
                                    )
                                sent_count += 1
                            except asyncio.TimeoutError:
                                logger.error("Chunk delivery timed out: user=%s part=%s/%s", safe_user_id, idx, len(chunks))
                            except Exception as e:
                                logger.error("Chunk fail: %s", e)
                    finally:
                        for chunk_file in chunks:
                            try:
                                if os.path.exists(chunk_file):
                                    os.remove(chunk_file)
                            except Exception:
                                pass
                    if chunks and sent_count == 0:
                        await message.reply_text(
                            "Delivery failed — please try again."
                        )
                    elif chunks and sent_count < len(chunks):
                        await message.reply_text(
                            f"{len(chunks) - sent_count} of {len(chunks)} parts failed to deliver."
                        )
                    elif not is_pro and safe_user_id:
                        await asyncio.to_thread(record_free_export, "telegram", str(safe_user_id))
                    return

                try:
                    upload_started_at = time.perf_counter()
                    target_media = media.telegram_file_id or media.file_path
                    sent_msg = None
                    
                    if "video" in media.mime_type:
                        progress_state: dict = {"upload_started_at": time.time()}
                        video_kwargs = self._video_delivery_kwargs(media)
                        if not media.telegram_file_id:
                            video_kwargs.update(
                                {
                                    "progress": self._telegram_upload_progress,
                                    "progress_args": (
                                        processing_msg,
                                        msg_text,
                                        markup,
                                        progress_state,
                                    ),
                                }
                            )
                        try:
                            sent_msg = await self._send_with_delivery_timeout(
                                client.send_video(
                                    chat_id=message.chat.id,
                                    video=target_media,
                                    caption=result.user_message(),
                                    parse_mode=ParseMode.HTML,
                                    **video_kwargs,
                                ),
                                processing_msg=processing_msg,
                                msg_text=msg_text,
                                markup=markup,
                                progress_state=progress_state,
                            )
                        except asyncio.TimeoutError:
                            if media.telegram_file_id:
                                raise
                            fallback_progress_state: dict = {"upload_started_at": time.time()}
                            try:
                                await processing_msg.edit_text(
                                    "Delivery is taking too long as a video, retrying as a file attachment."
                                )
                            except (MessageNotModified, RPCError):
                                pass
                            sent_msg = await self._send_with_delivery_timeout(
                                client.send_document(
                                    chat_id=message.chat.id,
                                    document=target_media,
                                    caption=f"{result.user_message()}",
                                    parse_mode=ParseMode.HTML,
                                ),
                                processing_msg=processing_msg,
                                msg_text=msg_text,
                                markup=markup,
                                progress_state=fallback_progress_state,
                            )
                    elif "audio" in media.mime_type:
                        sent_msg = await self._send_with_delivery_timeout(
                            client.send_audio(
                                chat_id=message.chat.id,
                                audio=target_media,
                                caption=f"Audio only — {result.original_url}",
                            )
                        )
                    else:
                        title = result.candidate.title if result.candidate else "Unknown"
                        duration = int(media.duration) if media.duration else "—"
                        await message.reply_text(
                            f"Preview only\n{title}\n{duration}s · {result.original_url}"
                        )
                        
                    logger.info(
                        "Telegram upload complete: user=%s mime=%s size_bytes=%s duration_seconds=%.3f",
                        safe_user_id,
                        media.mime_type,
                        media.size_bytes,
                        time.perf_counter() - upload_started_at,
                    )
                    
                    # Cache the new file ID in the Ghost Protocol vault
                    with contextlib.suppress(RPCError):
                        await processing_msg.delete()

                    if is_pro and not media.telegram_file_id and sent_msg:
                        file_id = ""
                        if sent_msg.video: file_id = sent_msg.video.file_id
                        elif sent_msg.audio: file_id = sent_msg.audio.file_id
                        if file_id:
                            await store_ghost_pointer(clean_url, file_id, media.size_bytes, str(user_id))
                    elif not is_pro and safe_user_id:
                        await asyncio.to_thread(record_free_export, "telegram", str(safe_user_id))
                            
                except asyncio.TimeoutError:
                    logger.error("Upload timed out: user=%s url=%s", safe_user_id, safe_url)
                    await processing_msg.edit_text(
                        "Delivery timed out while Telegram was receiving the file. Please retry; the pipeline will only mark delivery complete after the clip is actually sent.",
                    )
                except RPCError as exc:
                    logger.error("Upload failed: %s", exc)
                    await processing_msg.edit_text("Upload failed during Telegram delivery. Please try again.")
                return

            # Error case
            with contextlib.suppress(RPCError):
                await processing_msg.delete()
            reply = f"Unable to process · {result.status.name}\n\n{result.user_message()}"
            await message.reply_text(reply)

            logger.info(
                "Replied to user=%s status=%s url=%s",
                safe_user_id,
                result.status,
                safe_url,
            )
        finally:
            # Ensure all artifacts are unlinked
            processed_path = result.processed_media.file_path if result.processed_media else None
            if result.processed_media and result.processed_media.file_path:
                await self.media_processor.cleanup_file(result.processed_media.file_path)
            if (
                "original_processed_path" in locals()
                and original_processed_path
                and original_processed_path != processed_path
            ):
                await self.media_processor.cleanup_file(original_processed_path)
            if (
                "watermarked_path" in locals()
                and watermarked_path
                and watermarked_path != processed_path
            ):
                await self.media_processor.cleanup_file(watermarked_path)
            if result.candidate and result.candidate.local_path:
                await self.media_processor.cleanup_file(result.candidate.local_path)

    async def menu_callback(self, client: Client, callback_query: CallbackQuery) -> None:
        query = callback_query
        if not query.data:
            return

        try:
            await query.answer()
        except: pass

        async def edit_content(new_text: str, reply_markup=None):
            try:
                if query.message.media:
                    await query.edit_message_caption(caption=new_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                else:
                    await query.edit_message_text(text=new_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            except MessageNotModified:
                pass
            except Exception as e:
                logger.error("Failed to edit menu: %s", e)

        if query.data == "menu:frisky_signal":
            await edit_content(
                "🚨 <b>Frisky Signal</b>\n\n"
                "Are you sure you want to trigger the Frisky Signal? This is for urgent support and will contact the administrative team directly.",
                reply_markup=self.frisky_signal_menu,
            )
            return

        if query.data == "pro:create_account":
            user = query.from_user
            account = await self._ensure_friskydev_account_for_user(user)
            if not account:
                await edit_content(
                    "Could not create your Pro account because Telegram did not include user identity. Please send /pro again.",
                    reply_markup=self._menu_for_chat(query.message.chat if query.message else None),
                )
                return

            account_id = _escape_html(str(account.get("friskydev_account_id") or "pending"))
            environment = _escape_html(str(account.get("friskydev_environment") or self.settings.friskydev_environment))
            status = _escape_html(str(account.get("friskydev_account_status") or "pro_pending"))
            rows = [
                [InlineKeyboardButton(f"⭐ Pay {self.settings.telegram_stars_pro_price} Stars", callback_data="pro:pay_stars")],
                [InlineKeyboardButton("🔙 Back to Main Terminal", callback_data="menu:back_to_main")],
            ]

            if self._supports_inline_miniapp(getattr(query.message.chat if query.message else None, "type", None)):
                miniapp_url = self._normalize_miniapp_url(self.settings.miniapp_url, "intent=pro")
                if miniapp_url:
                    rows.insert(1, [InlineKeyboardButton("✨ Open Pro Mini App", web_app=WebAppInfo(url=miniapp_url))])

            await edit_content(
                "✅ <b>FriskyDev account ready.</b>\n\n"
                f"<b>Environment:</b> <code>{environment}</code>\n"
                f"<b>Account:</b> <code>{account_id}</code>\n"
                f"<b>Status:</b> <code>{status}</code>\n\n"
                "Next: pay with Telegram Stars, then I’ll unlock clean clips for this Telegram account.",
                reply_markup=InlineKeyboardMarkup(rows),
            )
            return

        if query.data == "pro:pay_stars":
            user = query.from_user
            account = await self._ensure_friskydev_account_for_user(user)
            if not user or not account:
                await edit_content(
                    "Could not start Stars checkout because Telegram did not include user identity. Please send /pro again.",
                    reply_markup=self._menu_for_chat(query.message.chat if query.message else None),
                )
                return

            try:
                await send_pro_stars_invoice(
                    self.settings.telegram_bot_token,
                    user.id,
                    "telegram",
                    str(user.id),
                    self.settings.telegram_stars_pro_price,
                )
            except Exception as exc:
                logger.error("Failed to send Stars invoice: %s", exc)
                await edit_content(
                    "Stars checkout is not available yet. Please try /pro again in a moment.",
                    reply_markup=self._menu_for_chat(query.message.chat if query.message else None),
                )
                return

            await edit_content(
                "⭐ <b>Stars invoice sent.</b>\n\nApprove the Telegram Stars payment sheet. After Telegram confirms it, I’ll flip this FriskyDev account to <code>pro_active</code>.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Back to Main Terminal", callback_data="menu:back_to_main")]]
                ),
            )
            return

        if query.data == "menu:frisky_signal_confirm":
            user = query.from_user
            admin_msg = (
                "🚨 <b>FRISKY SIGNAL TRIGGERED</b>\n\n"
                f"<b>User:</b> {user.first_name} (@{user.username})\n"
                f"<b>ID:</b> <code>{user.id}</code>\n"
                "<i>Action required.</i>"
            )
            for admin_id in self.settings.telegram_admin_ids:
                try:
                    await client.send_message(admin_id, admin_msg, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.error("Failed to notify admin %s: %s", admin_id, e)

            await edit_content(
                "📡 <b>Signal Sent!</b>\n\nThe Frisky Support Team has been notified. We will reach out to you shortly.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Terminal", callback_data="menu:back_to_main")]]),
            )
            return

        if query.data == "menu:admin_controls":
            user = query.from_user
            if user and user.id in self.settings.telegram_admin_ids:
                from services.db import get_admin_stats  # pyright: ignore[reportAttributeAccessIssue]
                stats = await asyncio.to_thread(get_admin_stats)
                
                await edit_content(
                    "🔧 <b>ADMINISTRATOR TERMINAL</b>\n\n"
                    "<b>SYSTEM METRICS:</b>\n"
                    f"👥 Total Users: {stats.get('total_users', 0)}\n"
                    f"⭐️ Pro Accounts: {stats.get('total_pro', 0)}\n"
                    f"💰 Total Commission Accrued: ${stats.get('total_commissions_cents', 0) / 100:.2f}\n\n"
                    "<b>COMMAND LIST:</b>\n"
                    "• <code>/grantfree &lt;user_id&gt;</code> — Manually grant Pro status to a user ID.\n"
                    "• <i>More admin features incoming.</i>",
                    reply_markup=self._menu_for_chat(query.message.chat if query.message else None),
                )
            else:
                await edit_content(
                    "⛔ Access Denied: Administrator privileges required.",
                    reply_markup=self._menu_for_chat(query.message.chat if query.message else None),
                )
            return

        if query.data == "menu:back_to_main":
            start_msg = _START_TEXT.replace("<b>Welcome to ClipFLOW.</b>", "<b>Welcome back.</b>")
            await edit_content(
                start_msg,
                reply_markup=self._menu_for_chat(query.message.chat if query.message else None),
            )
            return

    async def grant_free_command(self, client: Client, message: Message) -> None:
        sender = message.from_user
        if not sender or sender.id not in self.settings.telegram_admin_ids:
            await message.reply_text("⛔ Access Denied.")
            return

        args = message.command[1:] if message.command else []
        if not args:
            await message.reply_text("Usage: /grantfree <telegram_user_id>")
            return

        target_id = args[0].strip()
        if not target_id.isdigit():
            await message.reply_text("telegram_user_id must be numeric.")
            return

        from services.db import set_user_pro
        await asyncio.to_thread(
            set_user_pro,
            "telegram",
            target_id,
            True,
            None,
            True,
            self.settings.referral_commission_cents,
        )
        await message.reply_text(f"◈ User {target_id} is now Elite (free grant).")

    async def raw_update(self, client: Client, update, users, chats) -> None:
        if isinstance(update, types.UpdateBotPrecheckoutQuery):
            payload = parse_pro_stars_payload(update.payload)
            if not payload or update.currency != "XTR" or update.total_amount != self.settings.telegram_stars_pro_price:
                await client.invoke(
                    functions.messages.SetBotPrecheckoutResults(
                        query_id=update.query_id,
                        error="This Stars invoice is no longer valid. Please send /pro again.",
                    )
                )
                return

            await client.invoke(
                functions.messages.SetBotPrecheckoutResults(
                    query_id=update.query_id,
                    success=True,
                )
            )
            return

        if not isinstance(update, types.UpdateNewMessage):
            return

        message = getattr(update, "message", None)
        action = getattr(message, "action", None)
        if not isinstance(action, types.MessageActionPaymentSentMe):
            return

        payload = parse_pro_stars_payload(action.payload)
        if not payload or action.currency != "XTR":
            return

        platform, platform_id = payload
        if platform != "telegram":
            return

        charge_id = getattr(action.charge, "id", "") or getattr(action.charge, "provider_charge_id", "")
        account = await asyncio.to_thread(
            mark_telegram_stars_payment,
            platform,
            platform_id,
            int(action.total_amount),
            charge_id,
            self.settings.friskydev_environment,
        )

        await client.send_message(
            int(platform_id),
            "✅ <b>Pro active.</b>\n\n"
            f"FriskyDev account <code>{_escape_html(str(account.get('friskydev_account_id')))}</code> is now <code>pro_active</code>.\n"
            "Clean clips, unlimited runs, and priority processing are unlocked.",
            parse_mode=ParseMode.HTML,
        )

    async def unknown_command(self, client: Client, message: Message) -> None:
        await message.reply_text(_UNKNOWN_COMMAND_TEXT)


def setup_handlers(app: Client, pipeline: ClipPipeline, media_processor: MediaProcessor, settings: Settings) -> None:
    """
    Register all command and message handlers ont the Pyrogram Client.
    """
    bot_handlers = BotHandlers(app, pipeline, media_processor, settings)

    app.add_handler(MessageHandler(bot_handlers.start, filters.command("start")))
    app.add_handler(MessageHandler(bot_handlers.help_command, filters.command("help")))
    app.add_handler(MessageHandler(bot_handlers.pro_command, filters.command("pro")))
    app.add_handler(MessageHandler(bot_handlers.miniapp_command, filters.command("miniapp")))
    app.add_handler(MessageHandler(bot_handlers.grant_free_command, filters.command("grantfree")))
    app.add_handler(MessageHandler(bot_handlers.handle_web_app_data, web_app_data_filter))
    app.add_handler(MessageHandler(bot_handlers.handle_link, filters.text & ~filters.regex(r"^/")))
    app.add_handler(MessageHandler(bot_handlers.unknown_command, filters.regex(r"^/")))
    app.add_handler(CallbackQueryHandler(bot_handlers.menu_callback))
    app.add_handler(RawUpdateHandler(bot_handlers.raw_update))

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
import os
import random
import time
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

from bot.ascii_art import ASCII_CONCEPTUAL_LOADERS
from config.settings import Settings
from core.pipeline import ClipPipeline
from core.url_safety import redact_url
from services.db import (
    ensure_user,
    get_user,
    mark_keyboard_installed,
)
from services.media_processor import MediaProcessor

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
        
        self.inline_menu = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🚀 Launch Elite Portal", web_app=WebAppInfo(url=self.settings.miniapp_url)),
                ],
                [
                    InlineKeyboardButton("⚙️ Admin Controls", callback_data="menu:admin_controls"),
                    InlineKeyboardButton("🚨 Frisky Signal", callback_data="menu:frisky_signal"),
                ]
            ]
        )
        self.frisky_signal_menu = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ Transmit Frisky Signal", callback_data="menu:frisky_signal_confirm")],
                [InlineKeyboardButton("❌ Abort", callback_data="menu:back_to_main")],
            ]
        )
    async def _ensure_user(self, message: Message) -> None:
        user = message.from_user
        if not user:
            return

        await asyncio.to_thread(ensure_user, "telegram", str(user.id), user.username)

    async def start(self, client: Client, message: Message) -> None:
        await self._ensure_user(message)
        
        video_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "welcome_videos")
        
        def _get_videos():
            if os.path.exists(video_dir):
                return [f for f in os.listdir(video_dir) if f.lower().endswith(('.mp4', '.mov', '.gif'))]
            return []
            
        videos = await asyncio.to_thread(_get_videos)
        
        user = message.from_user
        safe_user_name = _escape_html(user.username or user.first_name) if user else "there"
        start_msg = _START_TEXT.replace("<b>Welcome to ClipFLOW.</b>", f"<b>Welcome, {safe_user_name}.</b>")
        markup = self.inline_menu

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
            reply_markup=self.inline_menu
        )

    async def _loader_task(self, client: Client, message: Message, base_text: str, reply_markup: InlineKeyboardMarkup | None, art: str):
        """Asynchronously update the processing message with a progressive ASCII loader."""
        start_time = time.time()

        stages = [
            (0,  "Initialising"),
            (2,  "Resolving source"),
            (5,  "Retrieving media"),
            (12, "Processing stream"),
            (20, "Optimising output"),
            (26, "Preparing delivery"),
        ]

        spin_idx = 0

        while True:
            try:
                elapsed = time.time() - start_time
                stage_text = stages[0][1]
                for threshold, label in stages:
                    if elapsed >= threshold:
                        stage_text = label

                if "Retrieving" in stage_text:
                    status = f"{random.uniform(40, 120):.0f} MB/s"
                elif "Processing" in stage_text or "Optimising" in stage_text:
                    status = "transcoding"
                else:
                    status = "nominal"

                pct = min(99, int((elapsed / 30) * 100))
                filled = int(pct / 5)
                bar = "█" * filled + "░" * (20 - filled)
                spin_idx += 1

                art_html = _escape_html(glitch_string(art, intensity=random.uniform(0.005, 0.02)))

                loader_text = (
                    f"<pre>{art_html}</pre>"
                    f"<code>{bar}  {pct}%</code>\n\n"
                    f"<b>{stage_text}</b>  ·  <i>{status}</i>\n\n"
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
        """Handle any plain text message – treat it as a clip link."""
        await self._ensure_user(message)
        
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

        url = message.text.strip()
        safe_url = redact_url(url)
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
        
        if is_pro:
            msg_text = f"<b>On it, {safe_user_name}.</b>\n<i>Priority pipeline — moving fast.</i>"
        else:
            msg_text = f"<b>Processing your link, {safe_user_name}.</b>\n<i>Your clip will be ready shortly.</i>"

        markup = self.inline_menu

        art = random.choice(ASCII_CONCEPTUAL_LOADERS)
        art_html = _escape_html(glitch_string(art, intensity=0.01))

        initial_loader = (
            f"<pre>{art_html}</pre>"
            f"<code>{'░' * 20}  0%</code>\n\n"
            f"<b>Initialising</b>  ·  <i>nominal</i>\n\n"
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
            cached = await get_cached_ghost_pointer(url)
            if cached and cached.get("file_id"):
                logger.info(f"Ghost cache hit! Bypassing pipeline for {safe_url}")
                result = ClipResult(
                    status=ClipStatus.SUCCESS,
                    original_url=url,
                    candidate=MediaCandidate(url=url, title="Cached Media"),
                    processed_media=ProcessedMedia(
                        file_path=None, 
                        duration=None, 
                        size_bytes=cached.get("file_size") or 0, 
                        telegram_file_id=cached.get("file_id")
                    )
                )
            else:
                lowered_url = url.lower()
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
                    result = await self.pipeline.process(url)
                finally:
                    if acquired_slot:
                        await release_youtube_slot()
        finally:
            loader_task.cancel()
            try:
                await processing_msg.delete()
            except RPCError:
                pass

        try:
            if result.is_ready and result.processed_media:
                media = result.processed_media
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
                                await client.send_video(
                                    chat_id=message.chat.id,
                                    video=chunk_file,
                                    caption=f"Part {idx} of {len(chunks)}{url_line}"
                                )
                                sent_count += 1
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
                    return

                try:
                    upload_started_at = time.perf_counter()
                    target_media = media.telegram_file_id or media.file_path
                    sent_msg = None
                    
                    if "video" in media.mime_type:
                        sent_msg = await client.send_video(
                            chat_id=message.chat.id,
                            video=target_media,
                            caption=result.user_message(),
                            parse_mode=ParseMode.HTML,
                        )
                    elif "audio" in media.mime_type:
                        sent_msg = await client.send_audio(
                            chat_id=message.chat.id,
                            audio=target_media,
                            caption=f"Audio only — {result.original_url}",
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
                    if not media.telegram_file_id and sent_msg:
                        file_id = ""
                        if sent_msg.video: file_id = sent_msg.video.file_id
                        elif sent_msg.audio: file_id = sent_msg.audio.file_id
                        if file_id:
                            await store_ghost_pointer(url, file_id, media.size_bytes, str(user_id))
                            
                except RPCError as exc:
                    logger.error("Upload failed: %s", exc)
                    await message.reply_text("Upload failed — please try again.")
                return

            # Error case
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
            if result.processed_media and result.processed_media.file_path:
                await self.media_processor.cleanup_file(result.processed_media.file_path)
            if result.candidate and result.candidate.local_path:
                await self.media_processor.cleanup_file(result.candidate.local_path)

    async def menu_callback(self, client: Client, callback_query: CallbackQuery) -> None:
        query = callback_query
        if not query.data:
            return

        if query.data == "menu:frisky_signal":
            await query.edit_message_text(
                "🚨 <b>Frisky Signal</b>\n\n"
                "Are you sure you want to trigger the Frisky Signal? This is for urgent support and will contact the administrative team directly.",
                reply_markup=self.frisky_signal_menu,
                parse_mode=ParseMode.HTML,
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

            await query.edit_message_text(
                "📡 <b>Signal Sent!</b>\n\nThe Frisky Support Team has been notified. We will reach out to you shortly.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Terminal", callback_data="menu:back_to_main")]]),
                parse_mode=ParseMode.HTML,
            )
            return

        if query.data == "menu:admin_controls":
            user = query.from_user
            if user and user.id in self.settings.telegram_admin_ids:
                from services.db import get_admin_stats  # pyright: ignore[reportAttributeAccessIssue]
                stats = await asyncio.to_thread(get_admin_stats)
                
                await query.edit_message_text(
                    "🔧 <b>ADMINISTRATOR TERMINAL</b>\n\n"
                    "<b>SYSTEM METRICS:</b>\n"
                    f"👥 Total Users: {stats.get('total_users', 0)}\n"
                    f"⭐️ Pro Accounts: {stats.get('total_pro', 0)}\n"
                    f"💰 Total Commission Accrued: ${stats.get('total_commissions_cents', 0) / 100:.2f}\n\n"
                    "<b>COMMAND LIST:</b>\n"
                    "• <code>/grantfree &lt;user_id&gt;</code> — Manually grant Pro status to a user ID.\n"
                    "• <i>More admin features incoming.</i>",
                    reply_markup=self.inline_menu,
                    parse_mode=ParseMode.HTML,
                )
            else:
                await query.answer("⛔ Access Denied: Administrator privileges required.", show_alert=True)
            return

        if query.data == "menu:back_to_main":
            # Repaint the start screen
            start_msg = _START_TEXT.replace("<b>Welcome to ClipFLOW.</b>", "<b>Welcome back.</b>")
            await query.edit_message_text(
                start_msg,
                reply_markup=self.inline_menu,
                parse_mode=ParseMode.HTML,
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

    async def unknown_command(self, client: Client, message: Message) -> None:
        await message.reply_text(_UNKNOWN_COMMAND_TEXT)


def setup_handlers(app: Client, pipeline: ClipPipeline, media_processor: MediaProcessor, settings: Settings) -> None:
    """
    Register all command and message handlers ont the Pyrogram Client.
    """
    bot_handlers = BotHandlers(app, pipeline, media_processor, settings)

    app.add_handler(MessageHandler(bot_handlers.start, filters.command("start")))
    app.add_handler(MessageHandler(bot_handlers.help_command, filters.command("help")))
    app.add_handler(MessageHandler(bot_handlers.miniapp_command, filters.command("miniapp")))
    app.add_handler(MessageHandler(bot_handlers.grant_free_command, filters.command("grantfree")))
    app.add_handler(MessageHandler(bot_handlers.handle_link, filters.text & ~filters.regex(r"^/")))
    app.add_handler(MessageHandler(bot_handlers.unknown_command, filters.regex(r"^/")))
    app.add_handler(CallbackQueryHandler(bot_handlers.menu_callback))

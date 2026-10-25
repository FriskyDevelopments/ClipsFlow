"""
bot.batch_handlers – Telegram surface for the batch download agent.

Commands (admin-only, gated by TELEGRAM_ADMIN_IDS; empty list = denied):

    /batch <url> <url> ...   queue a batch (URLs separated by spaces/newlines)
    /batch status            show the per-item status of your latest job
    /batch cancel            cancel your running job

The Mini App batch page (apps/web/app/miniapp/batch) sends
``{"action": "batch_download", "urls": [...]}`` via ``Telegram.WebApp.sendData``;
``BotHandlers.handle_web_app_data`` forwards it to ``handle_web_app_batch``.
"""

from __future__ import annotations

import html
import logging
import re
from typing import Optional

from core.models import ClipStatus
from core.url_safety import redact_url
from services.batch_agent import (
    BatchAgent,
    BatchConfig,
    BatchError,
    BatchErrorCode,
    BatchItem,
    BatchJob,
    ItemStatus,
    is_admin,
)

logger = logging.getLogger(__name__)

_URL_SPLIT = re.compile(r"[\s,]+")

USAGE = (
    "Usage:\n"
    "/batch <url> <url> … – queue a batch\n"
    "/batch status – show your latest batch\n"
    "/batch cancel – cancel your running batch"
)


def parse_urls(text: str) -> list[str]:
    return [t for t in _URL_SPLIT.split(text or "") if t]


def render_error(err: BatchError) -> str:
    return f"⛔ [{err.code.value}] {html.escape(err.message)}"


def render_job(job: BatchJob, limit: int = 60) -> str:
    lines = [html.escape(job.summary())]
    for item in job.items[:limit]:
        line = f"{item.index}. {item.status.value} – {html.escape(redact_url(item.url))}"
        if item.error and item.status in {ItemStatus.FAILED, ItemStatus.REJECTED, ItemStatus.RETRYING}:
            line += f" ({item.error.code.value}: {html.escape(item.error.message)})"
        lines.append(line)
    if len(job.items) > limit:
        lines.append(f"… {len(job.items) - limit} more")
    return "\n".join(lines)


class BatchCommands:
    def __init__(self, pipeline, settings, agent: Optional[BatchAgent] = None) -> None:
        self.settings = settings
        self.agent = agent or BatchAgent(BatchConfig.from_settings(settings), pipeline.process)

    def _authorized(self, message) -> bool:
        user = getattr(message, "from_user", None)
        return is_admin(getattr(user, "id", None), getattr(self.settings, "telegram_admin_ids", []))

    async def batch_command(self, client, message) -> None:
        if not self._authorized(message):
            await message.reply_text(render_error(BatchError(BatchErrorCode.NOT_AUTHORIZED, "Batch jobs are admin-only.")))
            return
        args = list(message.command[1:]) if getattr(message, "command", None) else []
        if not args:
            await message.reply_text(USAGE)
            return
        sub = args[0].lower()
        owner = message.from_user.id
        if sub == "status":
            job = self.agent.get_job(owner)
            await message.reply_text(render_job(job) if job else "No batch jobs yet.")
            return
        if sub == "cancel":
            try:
                job = self.agent.cancel(owner)
            except BatchError as err:
                await message.reply_text(render_error(err))
                return
            await message.reply_text("🛑 Cancelled.\n" + render_job(job))
            return
        text = message.text or ""
        body = text.split(None, 1)[1] if len(text.split(None, 1)) > 1 else " ".join(args)
        await self._start(client, message, parse_urls(body))

    async def handle_web_app_batch(self, client, message, payload: dict) -> None:
        if not self._authorized(message):
            await message.reply_text(render_error(BatchError(BatchErrorCode.NOT_AUTHORIZED, "Batch jobs are admin-only.")))
            return
        urls = payload.get("urls")
        if isinstance(urls, str):
            urls = parse_urls(urls)
        if not isinstance(urls, list):
            urls = []
        await self._start(client, message, [str(u) for u in urls])

    async def _start(self, client, message, urls: list[str]) -> None:
        try:
            job = self.agent.create_job(message.from_user.id, urls)
        except BatchError as err:
            await message.reply_text(render_error(err))
            return
        await message.reply_text("📥 Batch queued.\n" + render_job(job))
        chat_id = message.chat.id

        async def on_update(job: BatchJob, item: BatchItem) -> None:
            if item.status == ItemStatus.DONE:
                await self._deliver(client, chat_id, item)
            elif item.status == ItemStatus.FAILED:
                await client.send_message(chat_id, f"❌ {item.index}. {html.escape(item.error.message if item.error else 'failed')}")
            if all(i.status in {ItemStatus.DONE, ItemStatus.FAILED, ItemStatus.REJECTED, ItemStatus.CANCELLED} for i in job.items):
                await client.send_message(chat_id, "✅ Batch finished.\n" + render_job(job))

        self.agent.start(job, on_update)

    async def _deliver(self, client, chat_id: int, item: BatchItem) -> None:
        result = item.result
        media = getattr(result, "processed_media", None) if result else None
        if not result or result.status != ClipStatus.SUCCESS or media is None:
            return
        caption = f"{item.index}. {redact_url(item.url)}"
        target = media.telegram_file_id or media.file_path
        if target:
            await client.send_document(chat_id, target, caption=caption)

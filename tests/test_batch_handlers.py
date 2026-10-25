import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.batch_handlers import BatchCommands, parse_urls
from core.models import ClipResult, ClipStatus, ProcessedMedia
from services.batch_agent import BatchAgent, BatchConfig, ItemStatus


def make_msg(user_id, text, command=None):
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        chat=SimpleNamespace(id=555),
        text=text,
        command=command if command is not None else text.lstrip("/").split(),
        reply_text=AsyncMock(),
    )


@pytest.fixture
def setup():
    async def process(url):
        return ClipResult(status=ClipStatus.SUCCESS, original_url=url,
                          processed_media=ProcessedMedia(file_path="/tmp/a.mp4"))

    agent = BatchAgent(BatchConfig(allowed_providers=("youtube",), min_interval_seconds=0), process)
    settings = SimpleNamespace(telegram_admin_ids=[42])
    cmds = BatchCommands(pipeline=None, settings=settings, agent=agent)
    client = SimpleNamespace(send_message=AsyncMock(), send_document=AsyncMock())
    return cmds, agent, client


def test_parse_urls():
    assert parse_urls("a b,c\nd") == ["a", "b", "c", "d"]


@pytest.mark.asyncio
async def test_non_admin_denied(setup):
    cmds, agent, client = setup
    msg = make_msg(7, "/batch https://youtu.be/a")
    await cmds.batch_command(client, msg)
    assert "not_authorized" in msg.reply_text.call_args.args[0]
    assert agent.get_job(7) is None


@pytest.mark.asyncio
async def test_empty_admin_list_denies_everyone(setup):
    cmds, agent, client = setup
    cmds.settings.telegram_admin_ids = []
    msg = make_msg(42, "/batch https://youtu.be/a")
    await cmds.batch_command(client, msg)
    assert "not_authorized" in msg.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_admin_batch_runs_and_delivers(setup):
    cmds, agent, client = setup
    msg = make_msg(42, "/batch https://youtu.be/a https://soundcloud.com/x/y")
    await cmds.batch_command(client, msg)
    job = agent.get_job(42)
    await job.task
    assert job.items[0].status == ItemStatus.DONE
    assert job.items[1].status == ItemStatus.REJECTED
    client.send_document.assert_awaited_once()
    assert "Batch finished" in client.send_message.call_args.args[1]


@pytest.mark.asyncio
async def test_status_and_cancel(setup):
    cmds, agent, client = setup
    msg = make_msg(42, "/batch status")
    await cmds.batch_command(client, msg)
    assert "No batch jobs" in msg.reply_text.call_args.args[0]
    msg = make_msg(42, "/batch cancel")
    await cmds.batch_command(client, msg)
    assert "no_active_job" in msg.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_usage(setup):
    cmds, agent, client = setup
    msg = make_msg(42, "/batch")
    await cmds.batch_command(client, msg)
    assert "Usage" in msg.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_web_app_batch(setup):
    cmds, agent, client = setup
    msg = make_msg(42, "", command=[])
    await cmds.handle_web_app_batch(client, msg, {"action": "batch_download", "urls": ["https://youtu.be/a"]})
    job = agent.get_job(42)
    await job.task
    assert job.items[0].status == ItemStatus.DONE


@pytest.mark.asyncio
async def test_bot_handlers_routes_batch_payload():
    from bot.handlers import BotHandlers
    from config.settings import Settings

    s = Settings()
    h = BotHandlers(AsyncMock(), AsyncMock(), AsyncMock(), s)
    h._ensure_user = AsyncMock()
    h.batch_commands = SimpleNamespace(handle_web_app_batch=AsyncMock())
    payload = {"action": "batch_download", "urls": ["https://youtu.be/a"]}
    msg = SimpleNamespace(web_app_data=SimpleNamespace(data=json.dumps(payload)), reply_text=AsyncMock())
    await h.handle_web_app_data(AsyncMock(), msg)
    h.batch_commands.handle_web_app_batch.assert_awaited_once()


@pytest.mark.asyncio
async def test_bot_handlers_batch_disabled_message():
    from bot.handlers import BotHandlers
    from config.settings import Settings

    h = BotHandlers(AsyncMock(), AsyncMock(), AsyncMock(), Settings())
    h._ensure_user = AsyncMock()
    msg = SimpleNamespace(web_app_data=SimpleNamespace(data=json.dumps({"action": "batch_download"})), reply_text=AsyncMock())
    await h.handle_web_app_data(AsyncMock(), msg)
    assert "not enabled" in msg.reply_text.call_args.args[0]

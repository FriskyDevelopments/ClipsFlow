import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bot.handlers import BotHandlers
from config.settings import Settings
from pyrogram.types import Message, User
import logging

@pytest.fixture
def mock_pipeline():
    pipeline = AsyncMock()
    return pipeline

@pytest.fixture
def mock_processor():
    processor = AsyncMock()
    return processor

@pytest.fixture
def mock_settings():
    s = Settings()
    s.telegram_admin_ids = [999]
    return s

@pytest.fixture
def bot_handlers(mock_pipeline, mock_processor, mock_settings):
    client = AsyncMock()
    return BotHandlers(client, mock_pipeline, mock_processor, mock_settings)

@pytest.mark.asyncio
async def test_miniapp_command(bot_handlers):
    client = AsyncMock()
    client.get_me.return_value = MagicMock(username="testbot")
    
    msg = AsyncMock()
    msg.reply_text = AsyncMock()
    msg.from_user = User(id=1, is_self=False, is_contact=False, is_mutual_contact=False, is_deleted=False, is_bot=False, is_verified=False, is_restricted=False, is_scam=False, is_fake=False, is_support=False, is_premium=False, first_name="Test")
    
    await bot_handlers.miniapp_command(client, msg)
    msg.reply_text.assert_called_once()
    assert "https://t.me/testbot/miniapp" in msg.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_grant_free_command_denied(bot_handlers):
    client = AsyncMock()
    msg = AsyncMock()
    msg.reply_text = AsyncMock()
    msg.from_user = User(id=1, is_self=False, is_contact=False, is_mutual_contact=False, is_deleted=False, is_bot=False, is_verified=False, is_restricted=False, is_scam=False, is_fake=False, is_support=False, is_premium=False, first_name="Test")
    
    await bot_handlers.grant_free_command(client, msg)
    msg.reply_text.assert_called_once_with("⛔ Access Denied.")

@pytest.mark.asyncio
async def test_grant_free_command_allowed(bot_handlers):
    client = AsyncMock()
    msg = AsyncMock()
    msg.reply_text = AsyncMock()
    msg.from_user = User(id=999, is_self=False, is_contact=False, is_mutual_contact=False, is_deleted=False, is_bot=False, is_verified=False, is_restricted=False, is_scam=False, is_fake=False, is_support=False, is_premium=False, first_name="Admin")
    msg.command = ["/grantfree", "123"]
    
    with patch("bot.handlers.asyncio.to_thread", new_callable=AsyncMock) as to_thread:
        await bot_handlers.grant_free_command(client, msg)
        msg.reply_text.assert_called_once()
        assert "is now Elite" in msg.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_link(bot_handlers):
    client = AsyncMock()
    msg = AsyncMock()
    msg.reply_text = AsyncMock()
    msg.text = "https://youtube.com/watch?v=dQw4w9WgXcQ"
    msg.from_user = User(id=1, is_self=False, is_contact=False, is_mutual_contact=False, is_deleted=False, is_bot=False, is_verified=False, is_restricted=False, is_scam=False, is_fake=False, is_support=False, is_premium=False, first_name="Test")
    
    with patch("bot.handlers.asyncio.to_thread", new_callable=AsyncMock) as to_thread:
        to_thread.return_value = {"keyboard_installed": True, "is_pro": False}
        bot_handlers.pipeline.process.return_value = MagicMock(is_ready=True, processed_media=MagicMock(size_bytes=1000))
        
        await bot_handlers.handle_link(client, msg)
        assert msg.reply_text.call_count >= 1
        assert "Processing your link" in msg.reply_text.call_args_list[0][0][0]

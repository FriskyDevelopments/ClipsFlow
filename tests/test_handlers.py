import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace
from bot.handlers import BotHandlers
from config.settings import Settings
from pyrogram.enums import ChatType
from pyrogram.types import Message, User
from pyrogram.raw import types
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
async def test_start_with_pro_payload_shows_pro_approval(bot_handlers):
    client = AsyncMock()
    msg = AsyncMock()
    msg.reply_text = AsyncMock()
    msg.command = ["/start", "pro"]
    msg.from_user = User(id=1, is_self=False, is_contact=False, is_mutual_contact=False, is_deleted=False, is_bot=False, is_verified=False, is_restricted=False, is_scam=False, is_fake=False, is_support=False, is_premium=False, first_name="Test")

    with patch("bot.handlers.asyncio.to_thread", new_callable=AsyncMock):
        await bot_handlers.start(client, msg)

    msg.reply_text.assert_called_once()
    assert "Upgrade to Pro" in msg.reply_text.call_args[0][0]
    assert "FriskyDev" in msg.reply_text.call_args[0][0]


def test_build_inline_menu_ignores_invalid_miniapp_url(bot_handlers):
    bot_handlers.settings.miniapp_url = "not a url"
    menu = bot_handlers._build_inline_menu()
    assert any(button.text == "⚙️ Admin Controls" for row in menu.inline_keyboard for button in row)


def test_build_pro_menu_adds_pro_miniapp_when_url_is_valid(bot_handlers):
    bot_handlers.settings.miniapp_url = "https://clipsflow.example/miniapp"
    menu = bot_handlers._build_pro_menu(include_miniapp_button=True)
    assert any(button.text == "✨ Open Pro Mini App" for row in menu.inline_keyboard for button in row)


def test_supports_inline_miniapp_accepts_pyrogram_private_enum(bot_handlers):
    assert bot_handlers._supports_inline_miniapp(ChatType.PRIVATE) is True
    assert bot_handlers._supports_inline_miniapp(ChatType.GROUP) is False

@pytest.mark.asyncio
async def test_pro_command_shows_friskydev_account_approval(bot_handlers):
    client = AsyncMock()
    msg = AsyncMock()
    msg.reply_text = AsyncMock()
    msg.command = ["/pro"]
    msg.from_user = User(id=1, is_self=False, is_contact=False, is_mutual_contact=False, is_deleted=False, is_bot=False, is_verified=False, is_restricted=False, is_scam=False, is_fake=False, is_support=False, is_premium=False, first_name="Test")

    with patch("bot.handlers.asyncio.to_thread", new_callable=AsyncMock):
        await bot_handlers.pro_command(client, msg)

    msg.reply_text.assert_called_once()
    assert "FriskyDev" in msg.reply_text.call_args[0][0]
    menu = msg.reply_text.call_args.kwargs["reply_markup"]
    assert any(button.text == "✅ Create FriskyDev Account" for row in menu.inline_keyboard for button in row)

@pytest.mark.asyncio
async def test_pro_create_account_callback_attaches_friskydev_account(bot_handlers):
    client = AsyncMock()
    query = AsyncMock()
    query.data = "pro:create_account"
    query.answer = AsyncMock()
    query.from_user = User(id=1, is_self=False, is_contact=False, is_mutual_contact=False, is_deleted=False, is_bot=False, is_verified=False, is_restricted=False, is_scam=False, is_fake=False, is_support=False, is_premium=False, first_name="Test")
    query.message.media = None
    query.edit_message_text = AsyncMock()

    with patch("bot.handlers.asyncio.to_thread", new_callable=AsyncMock) as to_thread:
        to_thread.return_value = {
            "friskydev_account_id": "fdev_test123",
            "friskydev_environment": "friskydev",
            "friskydev_account_status": "pro_pending",
        }
        await bot_handlers.menu_callback(client, query)

    query.edit_message_text.assert_called_once()
    text = query.edit_message_text.call_args.kwargs["text"]
    assert "FriskyDev account ready" in text
    assert "fdev_test123" in text

@pytest.mark.asyncio
async def test_pro_pay_stars_callback_sends_invoice(bot_handlers):
    client = AsyncMock()
    query = AsyncMock()
    query.data = "pro:pay_stars"
    query.answer = AsyncMock()
    query.from_user = User(id=1, is_self=False, is_contact=False, is_mutual_contact=False, is_deleted=False, is_bot=False, is_verified=False, is_restricted=False, is_scam=False, is_fake=False, is_support=False, is_premium=False, first_name="Test")
    query.message.media = None
    query.edit_message_text = AsyncMock()

    with patch("bot.handlers.asyncio.to_thread", new_callable=AsyncMock) as to_thread:
        to_thread.return_value = {
            "friskydev_account_id": "fdev_test123",
            "friskydev_environment": "friskydev",
            "friskydev_account_status": "pro_pending",
        }
        with patch("bot.handlers.send_pro_stars_invoice", new_callable=AsyncMock) as send_invoice:
            await bot_handlers.menu_callback(client, query)

    send_invoice.assert_awaited_once_with(
        bot_handlers.settings.telegram_bot_token,
        1,
        "telegram",
        "1",
        bot_handlers.settings.telegram_stars_pro_price,
    )
    text = query.edit_message_text.call_args.kwargs["text"]
    assert "Stars invoice sent" in text

@pytest.mark.asyncio
async def test_raw_precheckout_accepts_valid_stars_invoice(bot_handlers):
    client = AsyncMock()
    update = types.UpdateBotPrecheckoutQuery(
        query_id=99,
        user_id=1,
        payload=b"cfpro:telegram:1",
        currency="XTR",
        total_amount=bot_handlers.settings.telegram_stars_pro_price,
    )

    await bot_handlers.raw_update(client, update, {}, {})

    client.invoke.assert_awaited_once()
    request = client.invoke.call_args.args[0]
    assert request.query_id == 99
    assert request.success is True

@pytest.mark.asyncio
async def test_raw_precheckout_rejects_invalid_amount(bot_handlers):
    client = AsyncMock()
    update = types.UpdateBotPrecheckoutQuery(
        query_id=99,
        user_id=1,
        payload=b"cfpro:telegram:1",
        currency="XTR",
        total_amount=1,
    )

    await bot_handlers.raw_update(client, update, {}, {})

    request = client.invoke.call_args.args[0]
    assert request.query_id == 99
    assert request.error

@pytest.mark.asyncio
async def test_raw_successful_stars_payment_activates_pro(bot_handlers):
    client = AsyncMock()
    payment = types.MessageActionPaymentSentMe(
        currency="XTR",
        total_amount=bot_handlers.settings.telegram_stars_pro_price,
        payload=b"cfpro:telegram:1",
        charge=types.PaymentCharge(id="charge_123", provider_charge_id="provider_123"),
    )
    update = types.UpdateNewMessage(
        message=types.MessageService(
            id=10,
            peer_id=types.PeerUser(user_id=1),
            date=0,
            action=payment,
        ),
        pts=1,
        pts_count=1,
    )

    with patch("bot.handlers.asyncio.to_thread", new_callable=AsyncMock) as to_thread:
        to_thread.return_value = {
            "friskydev_account_id": "fdev_test123",
            "friskydev_account_status": "pro_active",
        }
        await bot_handlers.raw_update(client, update, {}, {})

    to_thread.assert_awaited_once()
    assert to_thread.call_args.args[1:5] == ("telegram", "1", bot_handlers.settings.telegram_stars_pro_price, "charge_123")
    client.send_message.assert_awaited_once()
    assert "Pro active" in client.send_message.call_args.args[1]

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
        to_thread.side_effect = [
            {"keyboard_installed": True, "is_pro": False},
            {"keyboard_installed": True, "is_pro": False},
            {"used": 0, "limit": 25, "remaining": 25, "exhausted": False},
            {"used": 1},
        ]
        bot_handlers.pipeline.process.return_value = MagicMock(is_ready=True, processed_media=MagicMock(size_bytes=1000))
        
        await bot_handlers.handle_link(client, msg)
        assert msg.reply_text.call_count >= 1
        assert "Processing your link" in msg.reply_text.call_args_list[0][0][0]


@pytest.mark.asyncio
async def test_handle_link_gently_ignores_non_url(bot_handlers):
    client = AsyncMock()
    msg = AsyncMock()
    msg.reply_text = AsyncMock()
    msg.text = "hey there"
    msg.from_user = User(id=1, is_self=False, is_contact=False, is_mutual_contact=False, is_deleted=False, is_bot=False, is_verified=False, is_restricted=False, is_scam=False, is_fake=False, is_support=False, is_premium=False, first_name="Test")

    with patch.object(bot_handlers.pipeline, "process", new_callable=AsyncMock) as process:
        await bot_handlers.handle_link(client, msg)

    assert msg.reply_text.call_count == 1
    assert "Send a video link" in msg.reply_text.call_args[0][0]
    process.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_link_does_not_repeat_non_url_prompt(bot_handlers):
    client = AsyncMock()
    msg = AsyncMock()
    msg.reply_text = AsyncMock()
    msg.text = "still not a link"
    msg.from_user = User(id=1, is_self=False, is_contact=False, is_mutual_contact=False, is_deleted=False, is_bot=False, is_verified=False, is_restricted=False, is_scam=False, is_fake=False, is_support=False, is_premium=False, first_name="Test")

    with patch.object(bot_handlers.pipeline, "process", new_callable=AsyncMock) as process:
        await bot_handlers.handle_link(client, msg)
        await bot_handlers.handle_link(client, msg)

    assert msg.reply_text.call_count == 1
    process.assert_not_awaited()

@pytest.mark.asyncio
async def test_handle_web_app_data_processes_clip_url(bot_handlers):
    client = AsyncMock()
    msg = AsyncMock()
    msg.reply_text = AsyncMock()
    msg.web_app_data = SimpleNamespace(
        data='{"action":"process_clip","url":" https://example.com/clip.mp4 "}'
    )
    msg.from_user = User(id=1, is_self=False, is_contact=False, is_mutual_contact=False, is_deleted=False, is_bot=False, is_verified=False, is_restricted=False, is_scam=False, is_fake=False, is_support=False, is_premium=False, first_name="Test")

    with patch.object(bot_handlers, "_process_url_message", new_callable=AsyncMock) as process_url:
        await bot_handlers.handle_web_app_data(client, msg)

    process_url.assert_awaited_once_with(client, msg, "https://example.com/clip.mp4")


@pytest.mark.asyncio
async def test_loader_uses_live_state_without_fake_percent(bot_handlers):
    client = AsyncMock()
    msg = AsyncMock()
    msg.edit_text = AsyncMock()

    import asyncio

    task = asyncio.create_task(
        bot_handlers._loader_task(client, msg, "Processing your link.", None, "")
    )
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    text = msg.edit_text.call_args.args[0]
    assert "%" not in text
    assert "live system" in text


@pytest.mark.asyncio
async def test_upload_progress_never_shows_late_stage_99_percent(bot_handlers):
    msg = AsyncMock()
    msg.edit_text = AsyncMock()
    msg.chat = SimpleNamespace(id=123)
    state = {"upload_started_at": 1.0}

    await bot_handlers._telegram_upload_progress(
        99,
        100,
        msg,
        "Processing your link.",
        None,
        state,
    )

    text = msg.edit_text.call_args.args[0]
    assert "99%" not in text
    assert "Telegram has the full upload" not in text
    assert "final handoff window" in text

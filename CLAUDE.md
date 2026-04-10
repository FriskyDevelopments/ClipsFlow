# ClipFLOW — CLAUDE.md

## Project Overview

ClipFLOW is a **Telegram-first clip ingestion and processing service**. It is a Python bot runtime that accepts video URLs via Telegram, resolves them through provider adapters, validates and normalises media, then returns the result to the user.

There is no web frontend in this repo. The `frisky-signal-intake/` subdirectory is a separate React/TypeScript signal intake UI (Vite + Tailwind).

## Repository Structure

```
core/           # Pipeline logic, models, URL safety, runes, media normalisation
providers/      # Provider adapters (YouTube, TikTok, Instagram, X, direct, yt-dlp)
services/       # ClipValidator, MediaProcessor, webhook
config/         # Settings and startup validation
bot/            # Telegram bot transport layer
tests/          # pytest suite (unit + async)
worker.py       # Entrypoint shim → main.py
main.py         # App bootstrap and bot startup
```

## Commands

```bash
# Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Run tests
pytest -q

# Run bot locally (with Doppler)
doppler run -- python main.py

# Run bot locally (without Doppler, needs .env)
python main.py
```

## Key Conventions

- **Config is source of truth.** `CLIP_PROVIDER` controls which provider(s) are active. Unknown providers fail fast at startup.
- **Fail fast.** Missing required env vars → `sys.exit(1)` at startup with a clear message.
- **URL redaction.** All URLs in logs must pass through `core/url_safety.py:redact_url`. Never log raw tokens or signed URLs.
- **No blocking I/O in async functions.** Use `asyncio.to_thread` or `aiofiles`.
- **Separate transport from core.** Bot/Telegram logic lives in `bot/`; pipeline logic lives in `core/` and `services/`. They must not mix.
- **Single source of truth.** Do not duplicate logic across modules. If two helpers do the same thing, unify them.

## Architecture

```
Telegram transport (bot/)
    ↓
ClipPipeline (core/pipeline.py)
    ↓ URL validation → Provider resolution → Clip validation → Media processing
ProviderRegistry (providers/registry.py)
    ↓
Provider adapters (providers/*.py)
```

## Environment Variables

| Variable | Required | Notes |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes (bot mode) | Not required for tests |
| `CLIP_PROVIDER` | Yes | Comma-separated ordered list |
| `APP_ENV` | No | `development` (default) or `production` |
| `DOPPLER_PROJECT` | Prod only | Required when `APP_ENV=production` |
| `DOPPLER_CONFIG` | Prod only | Required when `APP_ENV=production` |

## Testing

- Python 3.12, pytest + pytest-asyncio + pytest-mock
- Tests must **not** depend on real Telegram tokens
- Async tests use `@pytest.mark.asyncio`
- CI: `.github/workflows/python-ci.yml` — runs `pytest -q` on all branches

## Active Branch Context

`feature/agentic-mtproto-migration` — migrating the bot transport layer to MTProto (Pyrogram/Telethon). The orchestrator setup commit is `1299e3a`.

## Operating Protocol

Full agent operating rules are in [./.github/instructions/*.instructions.md](./.github/instructions/*.instructions.md). Key points:

- Implement, don't suggest.
- Fix related issues in the same pass when obvious.
- A change is only complete when: config matches runtime, CI passes, no duplicated logic, docs match implementation.

# Batch download agent

The batch agent lets an **admin** queue a list of links and have ClipsFlow run
each one through the normal clip pipeline (`core/pipeline.py`), one item at a
time, with per-item status, retries, rate limiting and cancellation.

It adds **no new scraping or download code**. Every item goes through
`ClipPipeline.process`, which only uses the provider adapters enabled in
`CLIP_PROVIDER`. Music-streaming and DRM services (Spotify, Apple Music,
SoundCloud, Deezer, Tidal, Amazon Music, YouTube Music) are rejected up front,
and ClipsFlow never decrypts or extracts protected media.

## Components

| Path | Role |
|---|---|
| `services/batch_agent.py` | Transport-agnostic job manager: allowlist/blocklist checks, queue, retries with exponential backoff, rate limiting, concurrency limit, cancellation, structured errors |
| `bot/batch_handlers.py` | `/batch` command and Mini App payload handling, admin gate, progress messages, delivery of finished files |
| `bot/handlers.py` | Registers `/batch` when `BATCH_AGENT_ENABLED=true`; routes `web_app_data` with `action: "batch_download"` |
| `apps/web/app/miniapp/batch/page.tsx` | Mini App batch page (textarea → `Telegram.WebApp.sendData`) |
| `config/settings.py` | `BATCH_*` settings |
| `tests/test_batch_agent.py`, `tests/test_batch_handlers.py` | Tests (no Telegram token or network needed) |

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `BATCH_AGENT_ENABLED` | `false` | Registers `/batch` and accepts Mini App batches |
| `TELEGRAM_ADMIN_IDS` | empty | Comma-separated Telegram user IDs allowed to run batches. **Empty = nobody** |
| `BATCH_ALLOWED_PROVIDERS` | empty | Provider allowlist for batch items (subset of `direct,youtube,tiktok,instagram,x`). **Empty = every URL rejected.** The provider must also be enabled in `CLIP_PROVIDER` |
| `BATCH_MAX_URLS` | `50` | Max URLs per job |
| `BATCH_CONCURRENCY` | `1` | Items processed at the same time (global) |
| `BATCH_MIN_INTERVAL_SECONDS` | `3` | Minimum gap between item starts (global) |
| `BATCH_MAX_RETRIES` | `2` | Retries for provider errors / crashes (validation errors are not retried) |
| `BATCH_RETRY_BASE_SECONDS` | `2` | Backoff base: `base * 2^(attempt-1)` capped at 30 s, plus jitter |

## Usage

```
/batch https://youtu.be/a https://www.tiktok.com/@u/video/1
/batch status
/batch cancel
```

Mini App: open `/miniapp/batch` from the bot (a keyboard `web_app` button, so
`sendData` is available). It sends:

```json
{"action": "batch_download", "urls": ["https://..."], "source": "clipsflow-miniapp-batch"}
```

Telegram caps `sendData` at 4096 bytes; the page enforces that and 50 URLs.

## Item states and errors

Items: `queued → running → (retrying →) done | failed`, or `rejected` /
`cancelled`. Errors are `{code, message}` with codes: `not_authorized`,
`batch_disabled`, `empty_batch`, `too_many_urls`, `job_already_active`,
`no_active_job`, `invalid_url`, `blocked_host`, `provider_not_allowed`,
`pipeline_error`, `cancelled`.

## Limitations

* Jobs are in memory: a restart loses running jobs (no DB table yet).
* One active job per user; concurrency and rate limits are per bot process.
* Cancel stops items that have not started; an item already running finishes.

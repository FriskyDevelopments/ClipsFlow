# ClipsFlow 🎬

ClipsFlow is a Telegram-first clip ingestion and processing service. This repository currently contains the backend bot runtime, provider adapters, and tests. There is no web frontend or Telegram Mini App code in this repo at this time.

## Production Readiness Status

Implemented in this pass:
- ✅ Doppler-oriented secret management and fail-fast startup validation
- ✅ Strict config-driven provider enablement (`ENABLED_PROVIDERS`)
- ✅ Shared URL redaction utility for safer logs
- ✅ CI workflow aligned with actual Python repository layout
- ✅ Expanded tests for secrets/config/provider-selection validation
- ✅ README and env docs aligned with real runtime behavior

Out of scope in this repository (not present in codebase):
- Web UI/UX application
- Telegram Mini App frontend/runtime flow

## Linking the `clipsflow-landing-page` Mini App to this backend

Short answer: this repository is a Telegram bot runtime, not an HTTP API server, so your mini app cannot call it directly over REST yet.

Use one of these integration patterns:

1. **Open the bot from the mini app (fastest path)**  
   From `clipsflow-landing-page`, add a CTA that opens your bot link:
   - `https://t.me/<your_bot_username>?start=from_landing`
   - or `https://t.me/<your_bot_username>?startapp=landing_v1` (for Mini App entry context)

   Then the user sends a video URL to the bot and this backend handles processing.

2. **Add a small API gateway service (recommended for richer mini app UX)**  
   Keep this repo focused on clip processing logic, but expose a separate HTTP service that:
   - accepts mini app requests
   - authenticates Telegram users (`initData`)
   - forwards jobs to ClipsFlow pipeline components
   - returns status/result payloads for frontend rendering

3. **Single-repo deployment wiring (if you still want both repos connected)**  
   - Deploy `clipsflow-landing-page` as static hosting (Vercel/Netlify/S3+CDN)
   - Deploy this repo as the bot worker process
   - Share environment values across both deployments:
     - `TELEGRAM_BOT_USERNAME`
     - public mini app URL
     - bot deep links used by landing-page buttons

### Practical checklist

- [ ] In `clipsflow-landing-page`, set a primary button to open `t.me/<bot>?startapp=...`
- [ ] In `@BotFather`, configure the Mini App URL to your landing-page deployment
- [ ] In this repo, ensure `TELEGRAM_BOT_TOKEN` is valid and bot is running (`python main.py`)
- [ ] Test end-to-end in Telegram mobile: open mini app → tap CTA → bot chat opens → send URL

If you want, I can also provide a ready-to-copy `clipsflow-landing-page` button snippet (`window.Telegram.WebApp.openTelegramLink(...)`) plus the exact BotFather command sequence.

---

## Quick Start (Local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Set at minimum:
- `TELEGRAM_BOT_TOKEN`
- `ENABLED_PROVIDERS=direct,youtube,tiktok,instagram,x` (for local testing without external APIs)

Run:

```bash
python main.py
```

---

## Configuration

All runtime configuration is loaded from environment variables in `config/settings.py` and validated during startup.

### Required startup checks

The app exits immediately (`sys.exit(1)`) when:
- A secret listed in `REQUIRED_SECRETS` is missing or set to `__REQUIRED__`
- `ENABLED_PROVIDERS` includes an unknown provider
- `APP_ENV=production` but `DOPPLER_PROJECT` or `DOPPLER_CONFIG` is missing

### Key variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `REQUIRED_SECRETS` | Yes | `TELEGRAM_BOT_TOKEN` | Comma-separated env var names that must exist |
| `TELEGRAM_BOT_TOKEN` | Yes | — | Telegram bot token |
| `ENABLED_PROVIDERS` | Yes | `direct,youtube,tiktok,instagram,x` | Comma-separated ordered list of active providers |
| `APP_ENV` | No | `development` | `development` or `production` |
| `DOPPLER_PROJECT` | Prod only | — | Required in production |
| `DOPPLER_CONFIG` | Prod only | — | Required in production |

---

## Doppler Setup

### Local development

1. Authenticate with Doppler CLI (`doppler login`).
2. Create/select a project + config that contains required secrets.
3. Start the app through Doppler so env vars are injected:

```bash
doppler run -- python main.py
```

If you prefer `.env` for local work, keep production secrets out of source control and never commit real tokens.

### Production

Inject runtime secrets with Doppler and set:
- `APP_ENV=production`
- `DOPPLER_PROJECT=<project>`
- `DOPPLER_CONFIG=<config>`

The app will fail fast at startup if required secrets or Doppler metadata are missing.

---

## Provider Behavior

Provider activation is strictly config-driven.

- `ENABLED_PROVIDERS` is parsed and validated at startup.
- Only listed providers are registered.
- There is no hidden fallback registration list.

Example:

```bash
ENABLED_PROVIDERS=direct,youtube,tiktok,instagram,x
```

This enables all launch providers in a deterministic order.

---


### Supported launch providers

ClipsFlow supports these URL sources through a unified provider registry:

- `direct`: raw downloadable media URLs (e.g. `.mp4`, `.mov`, `.webm`)
- `youtube`: `youtube.com` + `youtu.be` + YouTube Shorts
- `tiktok`: `tiktok.com` clips
- `instagram`: `instagram.com` public video/reel links
- `x`: `x.com` and `twitter.com` video posts

`ENABLED_PROVIDERS` is the runtime truth source. Order is deterministic and controls route precedence when a URL could match multiple providers. Unknown names fail fast during startup.

If a URL is from a known provider domain but that provider is disabled, ClipsFlow returns a clear "supported but disabled" validation error instead of silently falling back.

## Testing

Run full suite:

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

Async tests use `pytest-asyncio` (`@pytest.mark.asyncio`) and the suite is intentionally fail-fast if that plugin is unavailable.

The tests do not require a real Telegram token. You can run unit tests locally with default env values and provider stubs.

---

## CI

GitHub Actions workflow: `.github/workflows/python-ci.yml`
- Python 3.12 setup
- Dependency install from both `requirements.txt` and `requirements-dev.txt`
- `pytest -q` execution (including async tests through `pytest-asyncio`)

---

## STIX MΛGIC Runic System

ClipsFlow now includes a symbolic runic language for system states and transitions:

- Runtime rune primitives and CLI/log formatting in `core/runes.py`
- Pipeline + bot usage of runes for loading and state feedback
- A mini-app style animation demo at `assets/miniapp/runes_demo.html`
- Detailed system documentation in `docs/stix_magic_runes.md`

Runic flow model:

```
INPUT ⟪ → FLOW → Λ TRANSFORM → OUTPUT ◫
```

Disruption/validation channels:

```
✕ = disruption/error
⟐ = lock/validation
```

---

## Render Deployment

This repo now includes `render.yaml` with explicit phase separation:

- Build Command: `pip install -r requirements.txt`
- Start Command: `python main.py`

This avoids pip trying to resolve `python` as a package during startup.

`runtime.txt` pins Python to `3.11.9` for consistent Render runtime selection.

# ClipsFlow 🎬

ClipsFlow is a Telegram-first clip ingestion and processing service. This repository contains the backend bot runtime, provider adapters, tests, and the first production-shaped Telegram Mini App surface in `apps/web`.

## Production Readiness Status

Implemented in this pass:
- ✅ Doppler-oriented secret management and fail-fast startup validation
- ✅ Strict config-driven provider enablement (`CLIP_PROVIDER`)
- ✅ Shared URL redaction utility for safer logs
- ✅ CI workflow aligned with actual Python repository layout
- ✅ Expanded tests for secrets/config/provider-selection validation
- ✅ README and env docs aligned with real runtime behavior
- ✅ Stripe-ready Mini App upgrade flow with hosted Checkout placeholders
- ✅ Telegram Mini App `sendData` bridge into the bot processing pipeline

## Linking the `clipsflow-landing-page` Mini App to this backend

Short answer: use the Telegram Mini App bridge first. The web app submits clip requests with `window.Telegram.WebApp.sendData(...)`, and the bot receives that `web_app_data` payload and runs the existing ClipsFlow pipeline.

Use one of these integration patterns:

1. **Open the bot from the mini app (fastest path)**  
   From `clipsflow-landing-page`, add a CTA that opens your bot link:
   - `https://t.me/<your_bot_username>?start=from_landing`
   - or `https://t.me/<your_bot_username>?startapp=landing_v1` (for Mini App entry context)

   Then the user sends a video URL to the bot and this backend handles processing.

2. **Add a small API gateway service (recommended later for richer mini app UX)**
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
- [ ] Test end-to-end in Telegram mobile: open mini app → paste URL → tap Process Clip → bot chat receives the request and delivers the clip

The REST API gateway can still come later when the mini app needs live job status, hosted download URLs, or a shared entitlement store outside Telegram chat.

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
- `CLIP_PROVIDER=mock` (for local testing without external APIs)

Run:

```bash
python main.py
```

## DigitalOcean/ngrok Dev Bridge

Use this for a temporary Telegram-testable URL while dev work moves through a DigitalOcean host or an ngrok bridge. Production still stays on Google Cloud while credits are available.

The bridge builds the Next Mini App, starts it locally, opens an HTTPS ngrok tunnel, and writes the public values to `.dev-bridge.env`.

```bash
chmod +x scripts/dev-ngrok-bridge.sh
./scripts/dev-ngrok-bridge.sh
```

With the bot running in the same shell:

```bash
RUN_BOT=1 ./scripts/dev-ngrok-bridge.sh
```

Useful overrides:

| Variable | Default | Notes |
|---|---|---|
| `WEB_PORT` | `3000` | Local Next.js port exposed through ngrok |
| `BOT_HEALTH_PORT` | `8080` | Local health port used when `RUN_BOT=1` |
| `PUBLIC_URL` | empty | Set this when DigitalOcean already gives you the public ngrok URL |
| `NGROK_REGION` | `us` | Passed to `ngrok http` |
| `RUN_BOT` | `0` | Set to `1` to run `python main.py` with `MINIAPP_URL` pointed at the tunnel |

After it starts, put the printed `https://...ngrok.../miniapp` URL into BotFather for Mini App testing.

If the DigitalOcean/ngrok bridge is already online and forwarding to local port `8088`, reuse it instead:

```bash
chmod +x scripts/run-digitalocean-ngrok-bridge.sh
./scripts/run-digitalocean-ngrok-bridge.sh
```

That starts the built Mini App on `WEB_PORT` and puts a local proxy on `BRIDGE_PORT=8088`, so the existing public ngrok URL serves `/miniapp`.

---

## Configuration

All runtime configuration is loaded from environment variables in `config/settings.py` and validated during startup.

### Required startup checks

The app exits immediately (`sys.exit(1)`) when:
- A secret listed in `REQUIRED_SECRETS` is missing or set to `__REQUIRED__`
- `CLIP_PROVIDER` includes an unknown provider
- `APP_ENV=production` but `DOPPLER_PROJECT` or `DOPPLER_CONFIG` is missing

### Key variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `REQUIRED_SECRETS` | Yes | `TELEGRAM_BOT_TOKEN` | Comma-separated env var names that must exist |
| `TELEGRAM_BOT_TOKEN` | Yes | — | Telegram bot token |
| `CLIP_PROVIDER` | Yes | `mock` | Comma-separated ordered list of active providers |
| `YTDLP_IMPERSONATE` | No | — | Optional yt-dlp TLS impersonation profile when supported by the installed runtime |
| `YTDLP_COOKIE_FILE` | No | — | Path to a Netscape-format cookies file for provider-authenticated extraction |
| `YTDLP_COOKIES_B64` | No | — | Base64-encoded Netscape cookies file, useful when deploying through Secret Manager env vars |
| `APP_ENV` | No | `development` | `development` or `production` |
| `DOPPLER_PROJECT` | Prod only | — | Required in production |
| `DOPPLER_CONFIG` | Prod only | — | Required in production |

### Stripe billing placeholders

The first ClipsFlow monetization path lives in `apps/web`:

- `/` shows the lightweight pricing entry point.
- `/miniapp` keeps the upgrade CTA inside the Telegram mini app shell.
- `/api/billing/checkout` creates a Stripe Checkout Session in subscription mode.
- `/api/billing/portal` is ready for customer self-service once customer ids are stored.
- `/api/stripe/webhook` verifies Stripe signatures and logs entitlement-changing events.

Set these values before using real checkout:

| Variable | Notes |
|---|---|
| `NEXT_PUBLIC_APP_URL` | Public base URL for Checkout success/cancel redirects |
| `STRIPE_SECRET_KEY` | Stripe secret key for Checkout, Portal, and webhook verification |
| `STRIPE_WEBHOOK_SECRET` | Signing secret from the Stripe webhook endpoint |
| `STRIPE_PRICE_PRO_MONTHLY` | Recurring Price id for the ClipsFlow Pro monthly plan |

External Stripe steps still needed:

1. Create the ClipsFlow Pro Product and recurring monthly Price in Stripe.
2. Put the Price id into `STRIPE_PRICE_PRO_MONTHLY`.
3. Configure Stripe Customer Portal settings for subscription cancellation/payment updates.
4. Add a webhook endpoint pointing at `<NEXT_PUBLIC_APP_URL>/api/stripe/webhook`.
5. Subscribe the endpoint to `checkout.session.completed`, `customer.subscription.updated`, and `customer.subscription.deleted`.
6. Replace the webhook logging placeholder with durable entitlement persistence once the web app and bot share a production user store.

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

- `CLIP_PROVIDER` is parsed and validated at startup.
- Only listed providers are registered.
- There is no hidden fallback registration list.

Example:

```bash
CLIP_PROVIDER=direct,youtube,tiktok,instagram,x
```

This enables all launch providers in a deterministic order.

For YouTube links that trigger datacenter bot checks or legitimate sign-in gates, set `YTDLP_COOKIES_B64` from a Netscape-format cookies file or point `YTDLP_COOKIE_FILE` at a mounted secret. Keep that value out of git and rotate it like any other production secret.

---


### Supported launch providers

ClipsFlow supports these URL sources through a unified provider registry:

- `direct`: raw downloadable media URLs (e.g. `.mp4`, `.mov`, `.webm`)
- `youtube`: `youtube.com` + `youtu.be` + YouTube Shorts
- `tiktok`: `tiktok.com` clips
- `instagram`: `instagram.com` public video/reel links
- `x`: `x.com` and `twitter.com` video posts

`CLIP_PROVIDER` is the runtime truth source. Order is deterministic and controls route precedence when a URL could match multiple providers. Unknown names fail fast during startup.

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

## Google Cloud Production Deployment

Production should stay on Google Cloud while credits are available. The clean shape is two Cloud Run services built by Cloud Build:

- `clipsflow-bot`: Python/Pyrogram polling worker plus a small health endpoint.
- `clipsflow-web`: Next.js Telegram Mini App and Stripe billing routes.

The bot service is configured differently from a normal web app because Telegram polling needs the process to stay alive:

- `--min-instances=1`
- `--max-instances=1`
- `--no-cpu-throttling`

The web service can scale to zero and scale up normally.

### Required one-time GCP setup

Create these Secret Manager secrets before deploying:

```bash
gcloud secrets create TELEGRAM_BOT_TOKEN --replication-policy=automatic
gcloud secrets create TELEGRAM_API_ID --replication-policy=automatic
gcloud secrets create TELEGRAM_API_HASH --replication-policy=automatic
gcloud secrets create DOPPLER_PROJECT --replication-policy=automatic
gcloud secrets create DOPPLER_CONFIG --replication-policy=automatic
gcloud secrets create STRIPE_SECRET_KEY --replication-policy=automatic
gcloud secrets create STRIPE_WEBHOOK_SECRET --replication-policy=automatic
gcloud secrets create STRIPE_PRICE_PRO_MONTHLY --replication-policy=automatic
gcloud secrets create NEXT_PUBLIC_APP_URL --replication-policy=automatic
gcloud secrets create MINIAPP_URL --replication-policy=automatic
```

Then add values:

```bash
printf '%s' '<value>' | gcloud secrets versions add TELEGRAM_BOT_TOKEN --data-file=-
```

Repeat for each secret.

### Deploy

```bash
chmod +x deploy-gcloud.sh
REGION=us-central1 ./deploy-gcloud.sh
```

The script enables required APIs, creates the Artifact Registry repository if needed, and runs `cloudbuild.yaml`.

Recommended deploy modes:

```bash
IMAGE_TAG="$(git rev-parse --short HEAD)-go-live" REGION=us-central1 ./deploy-gcloud.sh
```

Notes:

- `HARD_KILL=false` is the default, so no service deletion happens during deploy.
- `HARD_KILL=true` removes both services (bot + web) before deploy if you need a full reset.
- `WAIT_FOR_BOT=false` skips revision polling if you only want a fire-and-forget deploy.
- `WAIT_FOR_WEB=false` skips public health probing and only performs a final invoker check.
- `WEB_PUBLIC_ACCESS=false` leaves web service private for controlled testing.

### Post-deploy checklist

1. Set `NEXT_PUBLIC_APP_URL` to the public `clipsflow-web` Cloud Run URL or custom domain.
2. Set the `MINIAPP_URL` secret and BotFather Mini App URL to `https://<clipsflow-web-domain>/miniapp`.
3. Add the Stripe webhook endpoint: `https://<clipsflow-web-domain>/api/stripe/webhook`.
4. Run one Telegram mobile test: open Mini App, paste a URL, tap Process Clip, confirm the bot receives and delivers it.
5. Watch Cloud Run logs for both services after the first checkout and first clip request.

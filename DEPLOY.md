# Deploying ClipsFlow

ClipsFlow runs as a single **Cloudflare Worker** that serves both the clip
REST API and the Discord bot (via HTTP Interactions). State lives in
**Cloudflare D1** (SQLite); request rate limiting uses a **Durable Object**.

> **Why Workers (not Cloud Run):** the bot is now driven by Discord's
> **HTTP Interactions** model — Discord POSTs each `/clip` invocation to the
> Worker, which verifies the Ed25519 signature and replies inline. There is no
> always-on gateway process and no local file store to mount, so the service
> deploys to the edge with no container or volume.

## Prerequisites

- A Cloudflare account and `wrangler` authenticated: `npx wrangler login`
- Node.js >= 20
- A Discord application (Developer Portal) with its **Public Key**,
  **Application ID**, and a **Bot token**

## 1. Create the D1 database

```bash
npm run db:create          # wrangler d1 create clipsflow
```

Copy the printed `database_id` into `wrangler.toml` under
`[[d1_databases]]` (replace `REPLACE_WITH_D1_DATABASE_ID`).

Apply the schema:

```bash
npm run db:migrate:local   # local dev DB
npm run db:migrate         # remote (production) DB
```

## 2. Configure secrets and vars

```bash
# Discord public key — used to verify interaction request signatures.
npx wrangler secret put DISCORD_PUBLIC_KEY
```

Rate-limit tunables live in `wrangler.toml` `[vars]`
(`RATE_LIMIT_WINDOW_MS`, `RATE_LIMIT_MAX`) — override per environment as
needed.

## 3. Register the slash command (one-time / on change)

Run locally against the Discord REST API (uses `.env`, see `.env.example`):

```bash
DISCORD_BOT_TOKEN=... DISCORD_CLIENT_ID=... npm run bot:register
```

Set `DISCORD_GUILD_ID` for instant, guild-scoped registration in dev; omit
it to register globally (can take up to ~1h to propagate).

## 4. Deploy the Worker

```bash
npm run deploy             # wrangler deploy
```

Wrangler prints the Worker URL, e.g. `https://clipsflow.<subdomain>.workers.dev`.

## 5. Point Discord at the Worker

In the Developer Portal → your app → **General Information**, set the
**Interactions Endpoint URL** to:

```
https://clipsflow.<subdomain>.workers.dev/interactions
```

Discord immediately sends a `PING`; the Worker answers with `PONG`, so the
URL is accepted only once the deploy is live and `DISCORD_PUBLIC_KEY` is set.

## Endpoints

| Path | Purpose |
|---|---|
| `GET /healthz` | Liveness probe |
| `/api/v1/clips…` | Clip CRUD REST API |
| `POST /interactions` | Discord HTTP interactions (signature-verified) |

## Local development

```bash
npm run dev                # wrangler dev — local Worker + local D1 + DO
```

`wrangler dev` runs the Worker on Cloudflare's local runtime (`workerd`)
with a local D1 instance. Apply migrations to it with
`npm run db:migrate:local` first.

## Operational notes

- **D1 is the system of record.** Clips survive redeploys; no volume to
  mount, no single-instance cap (unlike the old Cloud Run + file-store path).
- **Rate limiting** is per-client-IP via the `RateLimiter` Durable Object,
  applied to `POST /api/v1/clips`. It replaces `express-rate-limit`, whose
  in-process counter cannot work across Worker isolates.
- **Naming:** this is the ClipsFlow clip service — distinct from the sibling
  Python Telegram bot. They do not share infrastructure.

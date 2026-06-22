# Runbook

Operational quick-reference. Full detail and prerequisites are in
[`DEPLOY.md`](../DEPLOY.md).

## Services

| Service | Where | Notes |
|---|---|---|
| ClipsFlow Worker | Cloudflare Workers | Serves the REST API **and** the Discord bot (HTTP interactions) |
| `DB` (D1) | Cloudflare D1 | System of record for clips |
| `RATE_LIMITER` | Durable Object | Per-IP rate limit on `POST /api/v1/clips` |
| ClipFLOW bot | (separate repo) | The sibling **Python** Telegram bot — unrelated |

## Deploy

```bash
npm run db:migrate          # apply migrations to the remote D1
npm run deploy              # wrangler deploy
```

Verify:

```bash
curl -s https://<your-worker-url>/healthz      # {"status":"ok"}
```

## Secrets & config

```bash
npx wrangler secret put DISCORD_PUBLIC_KEY     # interaction signature verify
# Rate-limit tunables live in wrangler.toml [vars]: RATE_LIMIT_WINDOW_MS / _MAX
```

## Roll back

Wrangler keeps prior versions; roll back with:

```bash
npx wrangler deployments list
npx wrangler rollback [<version-id>]
```

## Discord command surface

After changing the `/clip` subcommands, re-register (offline, uses `.env`):

```bash
DISCORD_BOT_TOKEN=... DISCORD_CLIENT_ID=... npm run bot:register
```

If interactions stop arriving, re-check the **Interactions Endpoint URL** in
the Developer Portal points at `https://<your-worker-url>/interactions` and
that `DISCORD_PUBLIC_KEY` matches the app.

## Incident checklist

1. **API errors?** Check `/healthz`, then `npx wrangler tail` for live logs;
   roll back if a bad version is live.
2. **Bot not responding?** Verify the Interactions Endpoint URL is set and the
   PING was accepted, `DISCORD_PUBLIC_KEY` is correct, and the command is
   registered. A 401 from `/interactions` means a signature/key mismatch.
3. **Clips missing / errors on write?** Confirm migrations were applied
   (`npm run db:migrate`) and the `DB` binding `database_id` in `wrangler.toml`
   is correct; inspect with `npx wrangler d1 execute clipsflow --command "SELECT COUNT(*) FROM clips"`.

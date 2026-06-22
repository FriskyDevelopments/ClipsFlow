# Getting Started

## Requirements

- Node.js >= 20
- A Cloudflare account + `wrangler` (`npx wrangler login`)

## Install & run locally

```bash
npm ci
npm run db:create          # one-time: create the D1 DB, paste id into wrangler.toml
npm run db:migrate:local   # apply schema to the local D1
npm run dev                # wrangler dev → http://localhost:8787
curl localhost:8787/healthz   # {"status":"ok"}
```

## Wire the Discord bot

1. Create an app + bot at the
   [Discord Developer Portal](https://discord.com/developers/applications);
   copy the **Public Key**, **application (client) ID**, and **bot token**.
2. Register the slash command (offline, talks to the Discord REST API):
   ```bash
   DISCORD_BOT_TOKEN=... DISCORD_CLIENT_ID=... npm run bot:register
   ```
3. Set the Worker secret and deploy, then point Discord at the Worker:
   ```bash
   npx wrangler secret put DISCORD_PUBLIC_KEY
   npm run deploy
   # Developer Portal → Interactions Endpoint URL → https://<worker-url>/interactions
   ```

## Scripts

| Script | Description |
|---|---|
| `npm run dev` | Run the Worker locally (`wrangler dev`) |
| `npm run deploy` | Deploy the Worker |
| `npm run db:create` / `db:migrate` / `db:migrate:local` | D1 create / remote / local migrate |
| `npm run bot:register` | Register the `/clip` slash command |
| `npm run typecheck` | Type-check without emitting |
| `npm test` | Run the Vitest suite (42 tests) |

For the full config table and endpoint reference, see
[`README.md`](../README.md) and [Specification](Specification).

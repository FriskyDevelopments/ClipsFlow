# Getting Started

## Requirements

- Node.js >= 20

## Install & run the API

```bash
npm ci
cp .env.example .env   # optional — sensible defaults are built in
npm run dev            # http://localhost:3000/api/v1
curl localhost:3000/healthz   # {"status":"ok"}
```

## Run the Discord bot

1. Create an app + bot at the
   [Discord Developer Portal](https://discord.com/developers/applications);
   copy the **bot token** and **application (client) ID**.
2. Set `DISCORD_BOT_TOKEN`, `DISCORD_CLIENT_ID` (and optionally
   `DISCORD_GUILD_ID` for instant dev registration).
3. Register the command and start the bot:

```bash
npm run build
npm run bot:register   # one-time / when the command surface changes
npm run bot
```

## Scripts

| Script | Description |
|---|---|
| `npm run dev` / `npm start` | Run the API (ts-node / compiled) |
| `npm run bot` / `npm run bot:dev` | Run the Discord bot (compiled / ts-node) |
| `npm run bot:register` | Register the `/clip` slash command |
| `npm run build` / `npm run typecheck` | Compile / type-check |
| `npm test` | Run the Vitest suite (42 tests) |

For the full env table and endpoint reference, see
[`README.md`](../README.md) and [Specification](Specification).

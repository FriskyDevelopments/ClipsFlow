# ClipsFlow

A small service for managing video clip metadata, running on **Cloudflare Workers** (Hono + TypeScript). It exposes a **REST API** and a **Discord bot** that share one clip core, persisted to **Cloudflare D1** (SQLite). Request rate limiting uses a **Durable Object**; the Discord bot is driven by Discord's **HTTP Interactions**, so there is no always-on gateway process.

**Docs:** [SPEC.md](./SPEC.md) (full contract) · [DEPLOY.md](./DEPLOY.md) (deploy) · [wiki/](./wiki/Home.md) (guides & runbook)

## Requirements

- Node.js >= 20
- A Cloudflare account + `wrangler` (`npx wrangler login`)

## Getting started

```bash
npm ci
npm run db:create        # one-time: create the D1 database, paste the id into wrangler.toml
npm run db:migrate:local # apply schema to the local D1
npm run dev              # wrangler dev → http://localhost:8787
```

### Scripts

| Script | Description |
|---|---|
| `npm run dev` | Run the Worker locally on `workerd` (`wrangler dev`) |
| `npm run deploy` | Deploy the Worker (`wrangler deploy`) |
| `npm run db:create` | Create the `clipsflow` D1 database |
| `npm run db:migrate` | Apply migrations to the **remote** D1 |
| `npm run db:migrate:local` | Apply migrations to the **local** D1 |
| `npm run bot:register` | Register the `/clip` slash command with Discord |
| `npm run typecheck` | Type-check without emitting |
| `npm test` | Run the Vitest suite |

## Configuration

Runtime config lives in `wrangler.toml` and Worker secrets — not a `.env`
(the `.env` is only for the local registration script; see `.env.example`).

| Setting | Where | Notes |
|---|---|---|
| `DB` | `wrangler.toml` `[[d1_databases]]` | D1 binding (paste `database_id`) |
| `RATE_LIMITER` | `wrangler.toml` `[[durable_objects.bindings]]` | Rate-limiter DO |
| `RATE_LIMIT_WINDOW_MS` | `wrangler.toml` `[vars]` | Rate-limit window in ms (default `60000`) |
| `RATE_LIMIT_MAX` | `wrangler.toml` `[vars]` | Max requests/window per IP on `POST /api/v1/clips` |
| `DISCORD_PUBLIC_KEY` | `wrangler secret put` | Verifies Discord interaction signatures |

## API

Base path: `/api/v1`. A liveness probe is exposed at `GET /healthz`.

### `POST /clips`

Create a clip. Body:

```json
{
  "title": "Intro",
  "filePath": "/clips/intro.mp4",
  "durationSeconds": 120,
  "tags": ["intro"]
}
```

`title` and `filePath` are required non-empty strings, `durationSeconds` is a positive number ≤ 3600, and `tags` (optional) is an array of strings. Returns `201` with the created clip, or `400` with `{ "errors": [...] }`.

### `GET /clips`

List clips. Query parameters:

| Param | Default | Notes |
|---|---|---|
| `tag` | — | Return only clips whose `tags` include this value |
| `page` | `1` | 1-based page number |
| `limit` | `20` | Page size (capped at `100`) |

Returns a paginated envelope:

```json
{
  "data": [ /* clips */ ],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

### `GET /clips/:id`

Return a single clip, or `404` if not found.

### `PATCH /clips/:id`

Update a clip's `title` and/or `tags`. Returns the updated clip, `400` on validation error, or `404` if not found.

### `DELETE /clips/:id`

Delete a clip. Returns `204`, or `404` if not found.

## Discord bot

ClipsFlow ships a Discord bot as a second transport over the **same** clip
core and D1 store as the REST API. Discord delivers each command to the
Worker via **HTTP Interactions** (`POST /interactions`), which the Worker
verifies (Ed25519) and answers inline — there is no gateway connection. It
exposes a single `/clip` slash command with subcommands mirroring the API:

| Command | Action |
|---|---|
| `/clip add title:<…> file_path:<…> duration:<sec> [tags:a,b]` | Create a clip |
| `/clip list [tag:<…>] [page:<n>]` | List clips (paginated) |
| `/clip get id:<…>` | Show one clip |
| `/clip update id:<…> [title:<…>] [tags:a,b]` | Update a clip |
| `/clip delete id:<…>` | Delete a clip |

Validation errors reply privately (ephemeral) to the invoker; successes post
to the channel.

### Wiring the bot

1. Create an application + bot at the [Discord Developer Portal](https://discord.com/developers/applications)
   and copy the **Public Key**, **Application (client) ID**, and **bot token**.
2. Register the slash command (one-time, or whenever the command surface changes):
   ```bash
   DISCORD_BOT_TOKEN=... DISCORD_CLIENT_ID=... npm run bot:register
   ```
3. Set the Worker secret and deploy:
   ```bash
   npx wrangler secret put DISCORD_PUBLIC_KEY
   npm run deploy
   ```
4. In the Developer Portal, set the **Interactions Endpoint URL** to
   `https://<your-worker-url>/interactions`.

See [DEPLOY.md](./DEPLOY.md) for the full walkthrough.

## Deployment

```bash
npm run db:migrate   # apply schema to remote D1
npm run deploy       # wrangler deploy
```

See **[DEPLOY.md](./DEPLOY.md)** for D1 setup, secrets, and pointing Discord
at the Worker.

## Testing & CI

`npm test` runs validator, store, HTTP route (via Hono `app.request`), and
Discord command tests against an in-memory store. GitHub Actions
(`.github/workflows/ci.yml`) typechecks, tests, and dry-run-bundles the
Worker on every push and pull request.

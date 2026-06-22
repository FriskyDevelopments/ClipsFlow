# ClipsFlow — Specification

Status: **v0.1.0** · Last updated for the go-live branch.

ClipsFlow is a small service for managing **video clip metadata**. The same
core logic is exposed over two transports — a **REST API** and a **Discord
bot** — and runs as a single **Cloudflare Worker** backed by **Cloudflare D1**.

---

## 1. Architecture

```
                 ┌────────────────────┐
HTTP  ───────►   │  Hono API           │ ┐
                 │  (src/api.ts)       │ │
                 └────────────────────┘ │
                 ┌────────────────────┐ │   ┌──────────────┐   ┌──────────────┐
Discord ─────►   │  HTTP interactions  │ ├─► │  clip core    │─► │  ClipStore    │
(POST /…)        │  (discord/*.ts)     │ │   │ (src/clips.ts)│   │ Memory │ D1   │
                 └────────────────────┘ ┘   └──────────────┘   └──────────────┘
                                              ▲                  (store.ts / d1.ts)
                                         validation
                                       (src/validators.ts)
```

- **Single Worker, two transports.** `src/worker.ts` routes `/api/v1/*` to the
  Hono API and `POST /interactions` to the Discord handler. Both call the same
  functions in `src/clips.ts`. No business rule is duplicated across transports.
- **Storage is an injected interface.** `ClipStore` (`src/store.ts`) has two
  implementations: `MemoryStore` (tests, local) and `D1Store` (`src/d1.ts`,
  production). The core is async so a single code path serves both.
- **Single query path.** Tag filtering + pagination live behind
  `store.getAll()`; `clips.listClips()` delegates to it. The D1 store filters
  tags in SQL via `json_each`.
- **Rate limiting** is a Durable Object (`src/ratelimiter.ts`), keyed per
  client IP, applied to `POST /api/v1/clips`.
- **Discord** uses HTTP Interactions: the Worker verifies the Ed25519 request
  signature (Web Crypto) and replies inline — no gateway connection. The only
  discord.js dependency is the offline slash-command registration script.
- **Persistence** is the `clips` table in D1 (schema in `migrations/`).

---

## 2. Data model

### `Clip`

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID v4) | Server-generated |
| `title` | `string` | Trimmed; non-empty |
| `filePath` | `string` | Trimmed; non-empty |
| `durationSeconds` | `number` | Positive, finite, ≤ 3600 |
| `tags` | `string[]` | Defaults to `[]` |
| `createdAt` | `string` (ISO 8601) | Set on create |
| `updatedAt` | `string` (ISO 8601) | Set on create and every update |

---

## 3. Validation rules

### Create (`validateCreateClip`)
- `title` — required, string, non-empty after trim.
- `filePath` — required, string, non-empty after trim.
- `durationSeconds` — required, finite number, `> 0`, `≤ 3600`.
- `tags` — optional; if present, must be an array of strings.

### Update (`validateUpdateClip`)
- `title` — optional; if present, non-empty string.
- `tags` — optional; if present, array of strings.
- `filePath` and `durationSeconds` are **immutable** after creation.

Validation failures raise `ValidationError` carrying a `string[]` of messages.

---

## 4. Pagination contract

`store.getAll(query)` and `clips.listClips(query)` return a **`PaginatedClips`**
envelope, never a bare array:

```json
{ "data": [ /* Clip[] */ ], "total": 0, "page": 1, "limit": 20 }
```

- `tag` filter is applied **before** pagination, so `total` reflects the
  filtered set.
- `page` defaults to `1`; invalid/`<1` values normalize to `1`.
- `limit` defaults to `20` (`DEFAULT_PAGE_LIMIT`) and is capped at `100`
  (`MAX_PAGE_LIMIT`); invalid values fall back to the default.

---

## 5. REST API

Base path: **`/api/v1`**. Bodies and responses are JSON. A liveness probe is
served at **`GET /healthz`** → `200 {"status":"ok"}` (outside the base path).

| Method & path | Success | Errors |
|---|---|---|
| `POST /clips` | `201` → `Clip` | `400` `{errors:[]}` |
| `GET /clips` | `200` → `PaginatedClips` | — |
| `GET /clips/:id` | `200` → `Clip` | `404` `{error}` |
| `PATCH /clips/:id` | `200` → `Clip` | `400` `{errors:[]}`, `404` `{error}` |
| `DELETE /clips/:id` | `204` (no body) | `404` `{error}` |

`GET /clips` query params: `tag` (string), `page` (int), `limit` (int).

**Error envelopes:** validation → `{ "errors": ["…","…"] }`; not-found and
other handled errors → `{ "error": "…" }`; unexpected → `500
{ "error": "Internal server error" }`.

**Rate limiting:** applied to `/api/v1`. Default `100` requests / `60s` per IP
(`RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW_MS`). Standard `RateLimit-*` headers;
bypassed when `NODE_ENV=test`.

---

## 6. Discord bot

One slash command, **`/clip`**, with subcommands mirroring the API:

| Subcommand | Options | Maps to |
|---|---|---|
| `add` | `title*`, `file_path*`, `duration*`, `tags` | `createClip` |
| `list` | `tag`, `page` | `listClips` |
| `get` | `id*` | `getClip` |
| `update` | `id*`, `title`, `tags` | `updateClip` |
| `delete` | `id*` | `deleteClip` |

(`*` = required. `tags` is a comma-separated string, parsed to `string[]`.)

- Validation/not-found errors reply **ephemerally** to the invoker; successes
  post a public embed.
- Uses only the non-privileged **`Guilds`** gateway intent.
- The pure handler `runClipCommand(input)` returns a transport-neutral
  `CommandResult` and contains no discord.js types (so it is unit-tested
  without a gateway connection).

---

## 7. Configuration

| Setting | Where | Used by |
|---|---|---|
| `DB` | `wrangler.toml` `[[d1_databases]]` | Store (both transports) |
| `RATE_LIMITER` | `wrangler.toml` `[[durable_objects.bindings]]` | API rate limiting |
| `RATE_LIMIT_WINDOW_MS` | `wrangler.toml` `[vars]` | API |
| `RATE_LIMIT_MAX` | `wrangler.toml` `[vars]` | API |
| `DISCORD_PUBLIC_KEY` | Worker secret | Interaction signature verification |
| `DISCORD_BOT_TOKEN` | `.env` (registration script) | Slash-command registration |
| `DISCORD_CLIENT_ID` | `.env` (registration script) | Slash-command registration |
| `DISCORD_GUILD_ID` | `.env` (registration script) | Optional guild-scoped registration |

---

## 8. Constraints & non-goals (v0.1.0)

- **D1 consistency.** Clips persist in a single D1 database shared by both
  transports; there is no file store and no single-instance cap. Tag filtering
  relies on SQLite `json_each` over the `tags` JSON column.
- **No auth** on the API beyond rate limiting; **no per-user authorization**
  in the bot. Anyone who can reach the transport can mutate clips.
- **No clip content handling** — ClipsFlow stores *metadata* only; it does not
  upload, transcode, or stream media.

### Planned next (post-v0.1.0)
- AuthN/Z on both transports.
- A normalized `clip_tags` table (vs. JSON column) if tag queries grow.
- OpenAPI document generated from the route + spec contract.

# ClipsFlow — Specification

Status: **v0.1.0** · Last updated for the go-live branch.

ClipsFlow is a small service for managing **video clip metadata**. The same
core logic is exposed over two transports — a **REST API** and a **Discord
bot** — backed by a single JSON file store.

---

## 1. Architecture

```
                 ┌────────────────────┐
HTTP  ───────►   │  Express routes     │ ┐
                 │  (src/routes.ts)    │ │
                 └────────────────────┘ │
                 ┌────────────────────┐ │   ┌──────────────┐   ┌──────────────┐
Discord ─────►   │  /clip command      │ ├─► │  clip core    │─► │  file store   │
                 │  (src/discord/*)    │ │   │ (src/clips.ts)│   │ (src/store.ts)│
                 └────────────────────┘ ┘   └──────────────┘   └──────────────┘
                                              ▲
                                         validation
                                       (src/validators.ts)
```

- **Transport is separate from logic.** Both the HTTP routes and the Discord
  command handler call the same functions in `src/clips.ts`. No business rule
  is duplicated across transports.
- **Single query path.** Tag filtering + pagination live only in
  `store.getAll()`; `clips.listClips()` delegates to it.
- **Persistence** is a JSON file at `${CLIPS_DATA_DIR}/clips.json`.

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

| Variable | Default | Used by |
|---|---|---|
| `PORT` | `3000` | API |
| `CLIPS_DATA_DIR` | `./data` | Store (both transports) |
| `RATE_LIMIT_WINDOW_MS` | `60000` | API |
| `RATE_LIMIT_MAX` | `100` | API |
| `NODE_ENV` | — | `test` skips rate limit + port/bot boot |
| `DISCORD_BOT_TOKEN` | — | Bot |
| `DISCORD_CLIENT_ID` | — | Command registration |
| `DISCORD_GUILD_ID` | — | Optional guild-scoped registration |

---

## 8. Constraints & non-goals (v0.1.0)

- **Single-writer file store.** The JSON store is not safe across multiple
  concurrent writers. The API is therefore pinned to `max-instances=1` on
  Cloud Run, and the bot runs as a single always-on worker. If both share a
  store they must share the **same** `CLIPS_DATA_DIR`.
- **No auth** on the API beyond rate limiting; **no per-user authorization**
  in the bot. Anyone who can reach the transport can mutate clips.
- **No clip content handling** — ClipsFlow stores *metadata* only; it does not
  upload, transcode, or stream media.

### Planned next (post-v0.1.0)
- Swap the file store for Postgres (the team already runs Supabase) to lift
  the single-instance cap.
- AuthN/Z on both transports.
- OpenAPI document generated from the route + spec contract.

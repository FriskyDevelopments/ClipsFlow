# Architecture

ClipsFlow keeps **transport separate from logic**: every transport calls the
same clip core, which is the only place business rules live. It runs as one
**Cloudflare Worker** with **D1** persistence and a **Durable Object** rate
limiter.

```
   HTTP  ─►  Hono API (api.ts)        ┐
                                      ├─►  clip core  ─►  validators
 Discord ─►  HTTP interactions        ┘   (clips.ts)      (validators.ts)
            (discord/interactions.ts)          │
                                               ▼
                                        ClipStore  ─►  MemoryStore (tests/local)
                                        (store.ts)     D1Store (prod, d1.ts)
```

## Modules

| Path | Responsibility |
|---|---|
| `src/worker.ts` | Worker entry: routes `/api/v1`, `/interactions`, DO rate limit; exports `RateLimiter` |
| `src/api.ts` | Hono HTTP transport — maps requests to the core, sets status codes |
| `src/discord/interactions.ts` | Discord HTTP transport — Ed25519 verify, map interaction → core, reply |
| `src/discord/commands.ts` | Neutral `/clip` handler (`runClipCommand`) + `parseTags` — no discord.js |
| `src/discord/render.ts` | Renders a `CommandResult` to raw Discord embed JSON |
| `src/discord/schema.ts` | `/clip` SlashCommandBuilder (discord.js) — used only by registration |
| `src/discord/register.ts` | Offline script that registers the command with Discord |
| `src/clips.ts` | **Clip core** — create / list / get / update / delete; `ValidationError` |
| `src/validators.ts` | Pure validation for create/update |
| `src/store.ts` | `ClipStore` interface, `MemoryStore`, shared pagination helpers |
| `src/d1.ts` | `D1Store` — D1-backed `ClipStore` (tag filter via `json_each`) |
| `src/ratelimiter.ts` | `RateLimiter` Durable Object (per-IP fixed window) |
| `src/types.ts` | `Clip`, `ClipQuery`, `PaginatedClips`, input types |

## Key invariants

- **Storage is injected and async.** The core takes a `ClipStore`; `MemoryStore`
  serves tests/local and `D1Store` serves production behind the same interface.
- **One query path.** Tag filtering and pagination live behind `store.getAll()`.
  `clips.listClips()` and both transports delegate to it.
- **Neutral handler.** `runClipCommand()` contains no discord.js types, so the
  same business path is unit-tested and bundles into the Worker. discord.js is
  confined to the offline registration script (`schema.ts` / `register.ts`).
- **Edge-native runtime.** Discord uses HTTP Interactions (no gateway); rate
  limiting uses a Durable Object (not in-process memory). See [Runbook](Runbook).

## Request lifecycle (example: `POST /clips`)

1. `worker.ts` checks the per-IP rate limiter, then `api.ts` reads the body and
   calls `clips.createClip(store, body)`.
2. `createClip` runs `validateCreateClip`; on failure throws `ValidationError`.
3. On success it builds the `Clip` (`crypto.randomUUID()` + timestamps) and
   awaits `store.insert` (D1 in production).
4. `api.ts` returns `201` + the clip, or maps `ValidationError` → `400`.

The Discord `add` subcommand follows the same path via `runClipCommand`, then
renders the result as an embed.

For the full contract, see [Specification](Specification) /
[`SPEC.md`](../SPEC.md).

# Architecture

ClipsFlow keeps **transport separate from logic**: every transport calls the
same clip core, which is the only place business rules live.

```
   HTTP  ─►  Express routes  ┐
                             ├─►  clip core  ─►  validators
 Discord ─►  /clip command   ┘        │
                                      ▼
                                 file store  (JSON @ CLIPS_DATA_DIR/clips.json)
```

## Modules

| Path | Responsibility |
|---|---|
| `src/index.ts` | API bootstrap: JSON body, rate limit, `/healthz`, mounts `/api/v1` |
| `src/routes.ts` | HTTP transport — maps requests to the core, sets status codes |
| `src/discord/` | Discord transport — `/clip` command, handler, embed renderer, registration |
| `src/clips.ts` | **Clip core** — create / list / get / update / delete; `ValidationError` |
| `src/validators.ts` | Pure validation for create/update |
| `src/store.ts` | File persistence + the single tag-filter/pagination query path |
| `src/types.ts` | `Clip`, `ClipQuery`, `PaginatedClips`, input types |

## Key invariants

- **One query path.** Tag filtering and pagination exist only in
  `store.getAll()`. `clips.listClips()` and both transports delegate to it.
- **Neutral handler.** `runClipCommand()` (Discord) contains no discord.js
  types, so the same business path is unit-tested without a gateway.
- **Single writer.** The JSON store is not multi-writer safe → API pinned to
  one instance, bot runs as one worker. See [Runbook](Runbook) and
  [`SPEC.md` §8](../SPEC.md).

## Request lifecycle (example: `POST /clips`)

1. `routes.ts` receives the body and calls `clips.createClip(body)`.
2. `createClip` runs `validateCreateClip`; on failure throws `ValidationError`.
3. On success it builds the `Clip` (UUID + timestamps) and calls
   `store.insert`.
4. `routes.ts` returns `201` + the clip, or maps `ValidationError` → `400`.

The Discord `add` subcommand follows the same path via `runClipCommand`, then
renders the result as an embed.

For the full contract, see [Specification](Specification) /
[`SPEC.md`](../SPEC.md).

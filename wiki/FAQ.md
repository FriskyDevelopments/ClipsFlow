# FAQ

**Is ClipsFlow the same as the ClipFLOW Telegram bot?**
No. ClipFLOW (Python) ingests and processes video via Telegram. ClipsFlow
(this repo, TypeScript) is a metadata CRUD service with a REST API and a
Discord bot, running on Cloudflare Workers. They share a name only.

**Does ClipsFlow store the actual video files?**
No — it stores **metadata** only (`title`, `filePath`, `durationSeconds`,
`tags`, timestamps). `filePath` is a reference, not an upload.

**Why is `GET /clips` an object instead of an array?**
It returns a `PaginatedClips` envelope (`{ data, total, page, limit }`) so
large libraries don't return unbounded payloads. See
[Specification](Specification) §4.

**Where are clips stored?**
In **Cloudflare D1** (SQLite), the `clips` table. Tags are a JSON array column;
tag filtering runs in SQL via `json_each`. Schema lives in `migrations/`.

**How does the Discord bot work without a gateway?**
It uses Discord's **HTTP Interactions**: Discord POSTs each `/clip` invocation
to `POST /interactions` on the Worker, which verifies the Ed25519 signature
(Web Crypto) and replies inline. No always-on process, so it fits Workers.

**How is rate limiting done without `express-rate-limit`?**
A `RateLimiter` Durable Object keyed per client IP — a strongly-consistent
counter that works across isolates, which an in-process counter cannot. It
guards `POST /api/v1/clips`; tune via `RATE_LIMIT_*` in `wrangler.toml`.

**Why is `durationSeconds` limited to 3600?**
Clips are expected to be short; the validator rejects anything `> 3600`
(1 hour). Change `MAX_CLIP_DURATION_SECONDS` in `src/validators.ts` if needed.

**How do tests persist data?**
They don't — tests inject a fresh in-memory `MemoryStore` per test, so they
never touch D1 or any real data.

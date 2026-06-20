# FAQ

**Is ClipsFlow the same as the ClipFLOW Telegram bot?**
No. ClipFLOW (Python) ingests and processes video via Telegram. ClipsFlow
(this repo, TypeScript) is a metadata CRUD service with a REST API and a
Discord bot. They share a name and an Artifact Registry repo but are separate
services (`clipsflow-api` vs `clipsflow-bot`).

**Does ClipsFlow store the actual video files?**
No — it stores **metadata** only (`title`, `filePath`, `durationSeconds`,
`tags`, timestamps). `filePath` is a reference, not an upload.

**Why is `GET /clips` an object instead of an array?**
It returns a `PaginatedClips` envelope (`{ data, total, page, limit }`) so
large libraries don't return unbounded payloads. See
[Specification](Specification) §4.

**Why is the API capped at one instance?**
The store is a single JSON file and isn't safe for concurrent writers across
instances. Moving to Postgres lifts this cap — see [`SPEC.md` §8](../SPEC.md).

**Why doesn't the Discord bot run on Cloud Run?**
It keeps a persistent gateway connection and serves no inbound HTTP, so
Cloud Run's scale-to-zero model would drop it. Run it as an always-on worker
([Runbook](Runbook)).

**Why is `durationSeconds` limited to 3600?**
Clips are expected to be short; the validator rejects anything `> 3600`
(1 hour). Change `MAX_CLIP_DURATION_SECONDS` in `src/validators.ts` if needed.

**Tests write files — where do they go?**
`tests/setup.ts` points `CLIPS_DATA_DIR` at a fresh temp directory per run, so
tests never touch real data.

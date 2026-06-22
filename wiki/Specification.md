# Specification

The authoritative specification lives in the repo at
[`SPEC.md`](../SPEC.md) so it versions alongside the code.

It covers:

- **Data model** — the `Clip` shape and field rules
- **Validation** — create/update rules, immutable fields, `durationSeconds ≤ 3600`
- **Pagination contract** — the `PaginatedClips` envelope, defaults, caps
- **REST API** — every endpoint, status codes, and error envelopes
- **Discord bot** — the `/clip` subcommand surface
- **Configuration** — all environment variables
- **Constraints & non-goals** — D1-backed store, no auth, metadata-only

👉 **Read it here: [`SPEC.md`](../SPEC.md)**

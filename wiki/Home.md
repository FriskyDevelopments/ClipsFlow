# ClipsFlow Wiki

ClipsFlow is a small service for managing **video clip metadata**, exposed
over a **REST API** and a **Discord bot** that share one clip core. It runs as
a single **Cloudflare Worker** backed by **Cloudflare D1**.

## Start here

- **[Getting Started](Getting-Started)** — install, run locally, wire the bot
- **[Architecture](Architecture)** — how the pieces fit together
- **[API & command spec](Specification)** — the full contract
- **[Runbook](Runbook)** — deploy, migrate D1, roll back, health
- **[FAQ](FAQ)** — common questions and gotchas

## Canonical docs in the repo

The wiki links to the source-of-truth docs so they never drift:

| Doc | Purpose |
|---|---|
| [`README.md`](../README.md) | Quickstart, scripts, config, API + bot usage |
| [`SPEC.md`](../SPEC.md) | Formal data model, validation, API & command contract |
| [`DEPLOY.md`](../DEPLOY.md) | Workers deploy: D1, secrets, Discord interactions endpoint |

> Publishing: these pages live in `wiki/` in the repo. To push them to the
> GitHub wiki, see [`wiki/README.md`](README.md).

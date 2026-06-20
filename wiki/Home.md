# ClipsFlow Wiki

ClipsFlow is a small service for managing **video clip metadata**, exposed
over a **REST API** and a **Discord bot** that share one clip core and a JSON
file store.

## Start here

- **[Getting Started](Getting-Started)** — install, run the API, run the bot
- **[Architecture](Architecture)** — how the pieces fit together
- **[API & command spec](Specification)** — the full contract
- **[Runbook](Runbook)** — deploy, prune revisions, roll back, health
- **[FAQ](FAQ)** — common questions and gotchas

## Canonical docs in the repo

The wiki links to the source-of-truth docs so they never drift:

| Doc | Purpose |
|---|---|
| [`README.md`](../README.md) | Quickstart, scripts, env, API + bot usage |
| [`SPEC.md`](../SPEC.md) | Formal data model, validation, API & command contract |
| [`DEPLOY.md`](../DEPLOY.md) | Cloud Run deploy, Cloud Build trigger, retiring instances |

> Publishing: these pages live in `wiki/` in the repo. To push them to the
> GitHub wiki, see [`wiki/README.md`](README.md).

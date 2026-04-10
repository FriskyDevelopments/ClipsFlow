# AGENTS.md

## Repo Summary

ClipFLOW is primarily a Python backend for Telegram-first clip ingestion and processing.
The `frisky-signal-intake/` directory is a separate React/TypeScript Vite app and should be treated as an independent frontend surface.

## Architecture

Backend layout:
- `main.py` / `worker.py` — app bootstrap and runtime entrypoints
- `bot/` — Telegram transport and handlers
- `core/` — pipeline, models, routing, validation, normalization, runes
- `providers/` — provider adapters and registry wiring
- `services/` — media processing, validation, db/webhook helpers
- `config/` — environment parsing and startup validation
- `tests/` — pytest suite

Frontend layout:
- `frisky-signal-intake/` — Vite + React + TypeScript app

## Working Rules

- Inspect the real repo structure before changing code, CI, or docs.
- Keep transport logic in `bot/`; keep business logic in `core/` and `services/`.
- Treat configuration as the source of truth. Do not hardcode provider behavior that conflicts with `ENABLED_PROVIDERS`.
- Fail fast on invalid configuration or missing required environment variables.
- Do not duplicate utilities or helper logic across modules.
- Never log raw secrets, tokens, signed URLs, or unredacted sensitive URLs.
- In async code, avoid blocking I/O; use async-safe patterns or offload blocking work.
- Keep changes focused. Do not fix unrelated issues unless they are directly adjacent and obviously required.

## Configuration Expectations

- Runtime configuration lives in `config/settings.py`.
- `ENABLED_PROVIDERS` must drive provider registration and resolution.
- Unknown providers must error immediately.
- Production mode requires Doppler metadata when the app expects it.
- Tests must not require a real `TELEGRAM_BOT_TOKEN`.

## Commands

Backend setup:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Backend run:
```bash
python main.py
```

Backend tests:
```bash
pytest -q
```

Frontend setup:
```bash
cd frisky-signal-intake
npm install
```

Frontend dev server:
```bash
cd frisky-signal-intake
npm run dev
```

Frontend build:
```bash
cd frisky-signal-intake
npm run build
```

## Testing Guidance

- Prefer targeted tests first, then broader validation if needed.
- For Python changes, use the existing pytest suite under `tests/`.
- For frontend changes, use the existing npm scripts in `frisky-signal-intake/package.json`.
- Do not introduce tests that depend on live external services or real Telegram credentials.

## Documentation

- Update `README.md` when startup behavior, commands, configuration, or architecture meaningfully changes.
- Keep docs aligned with the actual codebase; do not describe services or directories that do not exist.

## Deployment Notes

- `render.yaml`, `Procfile`, `Dockerfile`, and `fly.toml` should stay aligned with the actual runtime entrypoints.
- Do not change deployment commands without confirming they match current repo behavior.

## Agent Expectations

When working in this repository:
- implement directly instead of leaving TODOs for core behavior
- prefer minimal, production-safe changes
- validate assumptions against the repository before editing
- keep docs, config, and runtime behavior consistent in the same pass

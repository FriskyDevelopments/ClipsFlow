# ClipsFlow

A small REST API for managing video clip metadata, built with Express + TypeScript. Clips are persisted to a JSON file store, so it runs with zero external dependencies.

## Requirements

- Node.js >= 20

## Getting started

```bash
npm ci
cp .env.example .env   # optional — sensible defaults are built in
npm run dev            # http://localhost:3000/api/v1
```

### Scripts

| Script | Description |
|---|---|
| `npm run dev` | Run the API with ts-node (no build step) |
| `npm run build` | Compile TypeScript to `dist/` |
| `npm start` | Run the compiled server (`dist/index.js`) |
| `npm run typecheck` | Type-check without emitting |
| `npm test` | Run the Vitest suite |

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Default | Notes |
|---|---|---|
| `PORT` | `3000` | Port the server listens on |
| `CLIPS_DATA_DIR` | `./data` | Directory for the JSON store; mount a volume in production |
| `RATE_LIMIT_WINDOW_MS` | `60000` | Rate-limit window in ms |
| `RATE_LIMIT_MAX` | `100` | Max requests per window per IP on `/api/v1` |

## API

Base path: `/api/v1`. A liveness probe is exposed at `GET /healthz`.

### `POST /clips`

Create a clip. Body:

```json
{
  "title": "Intro",
  "filePath": "/clips/intro.mp4",
  "durationSeconds": 120,
  "tags": ["intro"]
}
```

`title` and `filePath` are required non-empty strings, `durationSeconds` is a positive number ≤ 3600, and `tags` (optional) is an array of strings. Returns `201` with the created clip, or `400` with `{ "errors": [...] }`.

### `GET /clips`

List clips. Query parameters:

| Param | Default | Notes |
|---|---|---|
| `tag` | — | Return only clips whose `tags` include this value |
| `page` | `1` | 1-based page number |
| `limit` | `20` | Page size (capped at `100`) |

Returns a paginated envelope:

```json
{
  "data": [ /* clips */ ],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

### `GET /clips/:id`

Return a single clip, or `404` if not found.

### `PATCH /clips/:id`

Update a clip's `title` and/or `tags`. Returns the updated clip, `400` on validation error, or `404` if not found.

### `DELETE /clips/:id`

Delete a clip. Returns `204`, or `404` if not found.

## Deployment

A multi-stage `Dockerfile` is provided:

```bash
docker build -t clipsflow .
docker run -p 3000:3000 -v clipsflow-data:/app/data clipsflow
```

The container runs as a non-root user and persists clips to the `/app/data` volume.

## Testing & CI

`npm test` runs validator, store, and HTTP route tests (via Supertest) against an isolated temp data directory. GitHub Actions (`.github/workflows/ci.yml`) typechecks, builds, and tests on every push and pull request.

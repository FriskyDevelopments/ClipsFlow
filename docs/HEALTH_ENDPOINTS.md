# Health and readiness probes

ClipsFlow exposes operational endpoints for Cloudflare deployment validation and external monitoring.

## `GET /health`

A liveness probe. It confirms that the Worker runtime can execute without checking downstream bindings.

Aliases: `/healthz`

Expected response:

```json
{
  "status": "ok",
  "service": "clipsflow",
  "version": "<release>",
  "environment": "production",
  "request_id": "<correlation-id>"
}
```

## `GET /ready`

A readiness probe. It runs a lightweight `SELECT 1` against the configured D1 binding.

Aliases: `/readyz`

- HTTP 200: the Worker can reach D1.
- HTTP 503: the Worker is alive but not ready to receive production traffic.

## Response headers

Every Worker response includes:

- `x-request-id`: Cloudflare Ray ID, incoming request ID, or a generated UUID.
- `x-clipsflow-release`: the configured release identifier.

Set `RELEASE` to the deployed commit SHA or release identifier from the deployment workflow.

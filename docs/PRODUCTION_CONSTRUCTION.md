# ClipsFlow Production Construction Contract

This document defines the minimum conditions for calling ClipsFlow deployed, healthy, and production-ready on Cloudflare.

## Deployment target

- Frontend: Cloudflare Pages
- API and Telegram webhook handlers: Cloudflare Workers
- Async processing: Cloudflare Queues where applicable
- Storage: R2 for media artifacts
- State: D1, KV, or Durable Objects according to the existing service boundary
- Product analytics and release observation: PostHog

## Required health surface

Every production Worker must expose a lightweight `GET /health` endpoint that returns JSON without contacting optional downstream services.

```json
{
  "status": "ok",
  "service": "clipsflow",
  "version": "<git-sha-or-release>",
  "environment": "production"
}
```

A deeper `GET /ready` endpoint may test required bindings and should return a non-2xx response when the service cannot safely receive production traffic.

## Standard PostHog events

All event names use `snake_case`. Do not include secrets, raw Telegram payloads, media URLs, access tokens, or message contents.

### Product funnel

- `clipsflow_opened`
- `telegram_user_identified`
- `media_submitted`
- `media_validated`
- `processing_started`
- `processing_completed`
- `processing_failed`
- `export_started`
- `export_completed`
- `upgrade_viewed`
- `checkout_started`
- `checkout_completed`

### Operational events

- `worker_request_failed`
- `queue_job_enqueued`
- `queue_job_started`
- `queue_job_completed`
- `queue_job_failed`
- `rate_limit_triggered`
- `dependency_unavailable`

### Required properties

Use only properties that are safe and useful for diagnosis:

- `service`
- `environment`
- `release`
- `request_id`
- `telegram_user_id_hash`
- `media_type`
- `source_platform`
- `duration_ms`
- `queue_wait_ms`
- `attempt`
- `error_code`
- `plan`
- `feature_flag`

## Release gates

A production deployment is eligible for promotion only when all applicable gates pass:

1. Build and type checks succeed.
2. Worker and Pages deployment jobs succeed.
3. `/health` responds with HTTP 200.
4. Telegram webhook validation succeeds.
5. A test media submission reaches a terminal state.
6. No new high-volume exception appears in PostHog during the observation window.
7. Processing success rate remains at or above 95% for the release sample.
8. P95 request latency does not regress by more than 25% from the previous stable release.
9. Queue failure rate remains below 2%.
10. A rollback target is recorded before promotion.

## Rollback conditions

Rollback immediately when any of the following occurs after deployment:

- Health or readiness checks fail repeatedly.
- Telegram webhook delivery stops.
- Processing success rate falls below 90%.
- Queue failures exceed 5%.
- Authentication or authorization behavior regresses.
- A release exposes sensitive data to logs or analytics.
- A payment or entitlement regression grants or removes access incorrectly.

## PostHog self-driving views

The ClipsFlow PostHog project should maintain these saved views or dashboard tiles:

- Submission to completed export funnel
- Processing failures by `error_code`
- Queue wait time and processing duration percentiles
- Worker failures by release
- Conversion by plan and source platform
- Feature-flag exposure versus completion rate
- LLM or AI cost and latency, when AI processing is enabled

## Definition of done for future PRs

A feature PR is complete only when it includes:

- User-facing behavior
- Error behavior
- Analytics events
- Relevant feature flag or rollout plan
- Tests or a documented manual validation path
- Deployment impact
- Rollback notes

This contract is intentionally platform-focused. It should be updated whenever the production architecture or operational ownership changes.

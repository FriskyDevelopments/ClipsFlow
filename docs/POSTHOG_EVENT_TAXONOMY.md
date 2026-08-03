# PostHog event taxonomy

This taxonomy keeps ClipsFlow analytics consistent across Cloudflare Workers, Pages, queues, and Telegram or Discord entry points.

## Naming

- Event names use `snake_case`.
- Property names use `snake_case`.
- Never capture secrets, raw access tokens, private message contents, or media URLs.

## Funnel events

- `clipsflow_opened`
- `user_identified`
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

## Operational events

- `worker_request_failed`
- `queue_job_enqueued`
- `queue_job_started`
- `queue_job_completed`
- `queue_job_failed`
- `rate_limit_triggered`
- `dependency_unavailable`

## Safe diagnostic properties

- `service`
- `environment`
- `release`
- `request_id`
- `user_id_hash`
- `media_type`
- `source_platform`
- `duration_ms`
- `queue_wait_ms`
- `attempt`
- `error_code`
- `plan`
- `feature_flag`

## Release dimensions

All backend operational events should include `service`, `environment`, and `release`. This allows PostHog dashboards to compare behavior before and after a Cloudflare deployment.

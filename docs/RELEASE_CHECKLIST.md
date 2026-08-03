# Release validation checklist

Use this checklist for every production deployment.

- [ ] Type checks and tests pass.
- [ ] Cloudflare deployment succeeds.
- [ ] `GET /health` returns HTTP 200 and the expected release.
- [ ] `GET /ready` returns HTTP 200.
- [ ] A representative API request completes successfully.
- [ ] Discord or Telegram webhook delivery is verified when applicable.
- [ ] No sensitive data appears in logs or analytics.
- [ ] PostHog receives events tagged with the new release.
- [ ] Error volume and latency are observed after deployment.
- [ ] The previous stable deployment is available for rollback.

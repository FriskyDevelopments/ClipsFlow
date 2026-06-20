# Runbook

Operational quick-reference. Full detail and prerequisites are in
[`DEPLOY.md`](../DEPLOY.md).

## Services

| Service | Where | Notes |
|---|---|---|
| `clipsflow-api` | Cloud Run (`us-central1`) | Request-driven, scales to zero, `max-instances=1` |
| ClipsFlow bot | Always-on worker | Persistent gateway connection; **not** Cloud Run |
| `clipsflow-bot` | Cloud Run | The sibling **Python** bot — unrelated, do not redeploy with this image |

## Deploy the API

```bash
./deploy.sh                 # build + deploy + prune old revisions
./deploy.sh --no-prune      # build + deploy only
gcloud builds submit --config cloudbuild.yaml .   # via Cloud Build
```

Verify:

```bash
URL=$(gcloud run services describe clipsflow-api --region us-central1 --format='value(status.url)')
curl -s "$URL/healthz"      # {"status":"ok"}
```

## Retire old revisions

```bash
./deploy.sh --prune-only    # delete non-serving revisions of clipsflow-api
gcloud run revisions list --service clipsflow-api --region us-central1
```

To prune the **Python** bot's stale revisions safely (dry-run by default,
keeps the serving one), use the ClipFLOW repo script:

```bash
scripts/prune-cloud-run-revisions.sh            # dry run
scripts/prune-cloud-run-revisions.sh --apply    # delete
```

## Roll back the API

```bash
gcloud run revisions list --service clipsflow-api --region us-central1
gcloud run services update-traffic clipsflow-api --region us-central1 \
  --to-revisions <GOOD_REVISION>=100
```

## Deploy / restart the Discord bot

Runs as an always-on worker (Compute Engine `create-with-container` shown in
[`DEPLOY.md`](../DEPLOY.md)). After a command-surface change, re-run
`npm run bot:register`. If the bot and API are on different hosts, both must
point at the **same** `CLIPS_DATA_DIR`.

## Incident checklist

1. **API down?** Check `/healthz`, then Cloud Run logs and the serving
   revision; roll back if a bad revision is live.
2. **Bot offline?** Check the worker is running and `DISCORD_BOT_TOKEN` is
   valid; the gateway reconnects automatically once the process is up.
3. **Clips missing / inconsistent?** Confirm both transports share one
   `CLIPS_DATA_DIR` and that the data volume is mounted (else the file store
   is ephemeral).

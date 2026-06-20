# Deploying ClipsFlow

The ClipsFlow API runs as a container on **Google Cloud Run** in
`us-central1`, mirroring the conventions of the sibling ClipFLOW bot.

> **Naming:** this service is **`clipsflow-api`** — deliberately distinct
> from the Python bot's **`clipsflow-bot`** Cloud Run service. They share
> the `clipsflow` Artifact Registry repo but are separate services. Never
> deploy this image over `clipsflow-bot`.

## Architecture constraints (read first)

- ClipsFlow persists clips to a **JSON file** (`CLIPS_DATA_DIR/clips.json`).
  This is **not safe across multiple instances**, so the service is pinned
  to **`--max-instances=1`**.
- Durability is provided by a **GCS-backed Cloud Run volume** mounted at
  `/app/data` (bucket `${PROJECT_ID}-clipsflow-data`). Without it, the file
  store is ephemeral and clips are lost on every redeploy.
- `--min-instances=0`: this is a request-driven API and scales to zero when
  idle (unlike the bot, which needs a warm instance for Telegram polling).

If/when ClipsFlow outgrows the file store, swap `store.ts` for Postgres
(the team already runs Supabase) and the single-instance cap can be lifted.

## Prerequisites

- `gcloud` CLI authenticated: `gcloud auth login`
- A target project: `gcloud config set project <PROJECT_ID>`
  (the team's prod project is `gen-lang-client-0202582192`)
- APIs enabled: `run.googleapis.com`, `cloudbuild.googleapis.com`,
  `artifactregistry.googleapis.com`, `storage.googleapis.com`
- Artifact Registry repo `clipsflow` in `us-central1` (already exists for
  the bot; create with:
  `gcloud artifacts repositories create clipsflow --repository-format=docker --location=us-central1`)

## Deploy

One command — builds the image, ensures the data bucket exists, deploys,
and prunes old revisions:

```bash
./deploy.sh
```

Override defaults via env vars:

```bash
GCP_PROJECT_ID=gen-lang-client-0202582192 \
GCP_REGION=us-central1 \
GCP_SERVICE_NAME=clipsflow-api \
./deploy.sh
```

Or via Cloud Build (e.g. wired to a trigger on the go-live branch):

```bash
gcloud builds submit --config cloudbuild.yaml .
```

After a deploy, verify:

```bash
URL=$(gcloud run services describe clipsflow-api --region us-central1 --format='value(status.url)')
curl -s "$URL/healthz"     # -> {"status":"ok"}
```

## Retiring old instances / revisions

Cloud Run automatically shifts 100% of traffic to the new revision, so old
revisions stop receiving requests immediately. `./deploy.sh` then **deletes**
every revision that is no longer serving traffic. To prune without
redeploying:

```bash
./deploy.sh --prune-only
```

To inspect what would be removed first:

```bash
gcloud run revisions list --service clipsflow-api --region us-central1
```

### Other "old instances" to be aware of (NOT touched by this script)

These belong to other products in the same project. Decommission them
**deliberately**, only after confirming they're truly retired — `deploy.sh`
never touches them:

| Resource | Type | Notes |
|---|---|---|
| `clipsflow-bot` | Cloud Run service | The **live Python bot** — do not delete. |
| `clipflow-worker-prod` | Compute Engine VM | Created by `ClipFLOW/deploy-prod-gcp.sh`. |
| `ghost-api-prod` | Cloud Run service | Unrelated Ghost API. |

Manual teardown commands (run only against a confirmed-stale target):

```bash
# A stale Cloud Run service
gcloud run services delete <SERVICE> --region us-central1

# A stale Compute Engine VM
gcloud compute instances delete <NAME> --zone us-central1-a
```

## Rollback

```bash
# List revisions, then route traffic back to a known-good one
gcloud run revisions list --service clipsflow-api --region us-central1
gcloud run services update-traffic clipsflow-api --region us-central1 \
  --to-revisions <GOOD_REVISION>=100
```

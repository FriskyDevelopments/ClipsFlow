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

### Continuous deploy (Cloud Build trigger)

To auto-deploy on every push, create the trigger **once** (needs the GitHub
repo connected to Cloud Build in the GCP console, or via
`gcloud builds connections`):

```bash
gcloud builds triggers create github \
  --name=clipsflow-api-deploy \
  --repo-name=ClipsFlow \
  --repo-owner=FriskyDevelopments \
  --branch-pattern='^claude/clipsflow-go-live-1j0klh$' \
  --build-config=cloudbuild.yaml \
  --region=us-central1
```

Once merged to your production branch, repoint `--branch-pattern` (e.g.
`^main$`). Grant the Cloud Build service account the `run.admin`,
`storage.admin`, and `iam.serviceAccountUser` roles so the build step can
deploy and manage the data bucket. After that, `git push` is the deploy.

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
| `clipsflow-bot` | Cloud Run service | The **live Python bot** — do not delete. To prune only its *stale revisions* (keeps the serving one), use `scripts/prune-cloud-run-revisions.sh` in the ClipFLOW repo. |
| `clipflow-worker-prod` | Compute Engine VM | Created by `ClipFLOW/deploy-prod-gcp.sh`. |
| `ghost-api-prod` | Cloud Run service | Unrelated Ghost API. |

Manual teardown commands (run only against a confirmed-stale target):

```bash
# A stale Cloud Run service
gcloud run services delete <SERVICE> --region us-central1

# A stale Compute Engine VM
gcloud compute instances delete <NAME> --zone us-central1-a
```

## Deploying the Discord bot

The bot holds a **persistent gateway (WebSocket) connection** and has no
inbound HTTP, so it does **not** fit Cloud Run's request-driven, scale-to-zero
model — a Cloud Run service would idle the container and drop the connection.
Run it as an **always-on worker** instead, mirroring the sibling
`clipflow-worker-prod` Compute Engine pattern:

```bash
# Build/push the same image, then run it with the bot entrypoint on an
# always-on container host (Compute Engine shown; any always-on runtime works).
gcloud compute instances create-with-container clipsflow-bot-worker \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --container-image=us-central1-docker.pkg.dev/$PROJECT_ID/clipsflow/clipsflow-api:latest \
  --container-command=node \
  --container-arg=dist/discord/index.js \
  --container-env=NODE_ENV=production,CLIPS_DATA_DIR=/app/data \
  --container-env=DISCORD_BOT_TOKEN=...,DISCORD_CLIENT_ID=...
```

Prefer Secret Manager over `--container-env` for the token in production.
Register the slash command once (`npm run bot:register`, or a one-shot run of
the image with `--container-arg=dist/discord/register.js`) before/after first
boot. If the bot and API run on different hosts, point both at the **same**
shared store (e.g. the GCS-backed volume) so they see the same clips.

## Rollback

```bash
# List revisions, then route traffic back to a known-good one
gcloud run revisions list --service clipsflow-api --region us-central1
gcloud run services update-traffic clipsflow-api --region us-central1 \
  --to-revisions <GOOD_REVISION>=100
```

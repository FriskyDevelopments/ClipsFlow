#!/usr/bin/env bash
# Build and deploy the ClipsFlow API to Cloud Run, then retire old revisions.
#
# Conventions mirror the sibling ClipFLOW bot deploy (GCP, us-central1,
# Artifact Registry repo "clipsflow") but use a DISTINCT service name
# (clipsflow-api) so this never clobbers the Python bot's "clipsflow-bot".
#
# Usage:
#   ./deploy.sh            # build + deploy + prune old revisions
#   ./deploy.sh --no-prune # build + deploy only
#   ./deploy.sh --prune-only  # just retire old revisions, no build/deploy
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${GCP_REGION:-us-central1}"
SERVICE="${GCP_SERVICE_NAME:-clipsflow-api}"
REPO="${GCP_AR_REPO:-clipsflow}"
# JSON file store lives on a GCS-backed Cloud Run volume so clips survive
# restarts/redeploys. Single bucket per project by default.
BUCKET="${CLIPS_DATA_BUCKET:-${PROJECT_ID}-clipsflow-data}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}"

MODE="full"
case "${1:-}" in
  --no-prune)   MODE="no-prune" ;;
  --prune-only) MODE="prune-only" ;;
  "")           MODE="full" ;;
  *) echo "Unknown arg: $1"; exit 1 ;;
esac

require() { command -v "$1" &>/dev/null || { echo "❌ $1 is required"; exit 1; }; }
require gcloud

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "❌ Set GCP_PROJECT_ID or run: gcloud config set project <id>"
  exit 1
fi
gcloud config set project "${PROJECT_ID}" >/dev/null

# --- Retire every revision that isn't currently serving traffic ----------
prune_old_revisions() {
  echo "🧹 Pruning old (non-serving) revisions of ${SERVICE}..."
  local active
  active="$(gcloud run services describe "${SERVICE}" --region "${REGION}" \
    --format='value(status.traffic.revisionName)' 2>/dev/null | tr ';' '\n' | sort -u || true)"
  if [[ -z "${active}" ]]; then
    echo "   Service ${SERVICE} not found — nothing to prune."
    return 0
  fi
  local rev
  while read -r rev; do
    [[ -z "${rev}" ]] && continue
    if grep -qx "${rev}" <<<"${active}"; then
      echo "   keep   ${rev} (serving traffic)"
    else
      echo "   delete ${rev}"
      gcloud run revisions delete "${rev}" --region "${REGION}" --quiet || true
    fi
  done < <(gcloud run revisions list --service "${SERVICE}" --region "${REGION}" \
            --format='value(metadata.name)')
}

if [[ "${MODE}" == "prune-only" ]]; then
  prune_old_revisions
  exit 0
fi

# --- Ensure the durable data bucket exists -------------------------------
if ! gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1; then
  echo "🪣 Creating data bucket gs://${BUCKET}..."
  gcloud storage buckets create "gs://${BUCKET}" --location "${REGION}" --uniform-bucket-level-access
fi

# --- Build & push --------------------------------------------------------
echo "🏗  Building ${IMAGE}:latest ..."
gcloud builds submit --tag "${IMAGE}:latest" .

# --- Deploy --------------------------------------------------------------
# max-instances=1: the JSON file store is not safe across multiple instances.
# min-instances=0: request-driven API, scale to zero when idle (unlike the
# bot, which needs a warm instance for Telegram polling).
echo "🚀 Deploying ${SERVICE} to Cloud Run (${REGION})..."
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}:latest" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 1 \
  --cpu 1 \
  --memory 512Mi \
  --port 3000 \
  --set-env-vars "NODE_ENV=production,CLIPS_DATA_DIR=/app/data" \
  --add-volume "name=data,type=cloud-storage,bucket=${BUCKET}" \
  --add-volume-mount "volume=data,mount-path=/app/data"

URL="$(gcloud run services describe "${SERVICE}" --region "${REGION}" --format='value(status.url)')"
echo "✅ Deployed: ${URL}"
echo "   Health:   ${URL}/healthz"

# --- Retire the revisions this deploy replaced ---------------------------
if [[ "${MODE}" == "full" ]]; then
  prune_old_revisions
fi

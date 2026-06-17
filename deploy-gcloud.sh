#!/usr/bin/env bash
set -euo pipefail

REGION="${REGION:-us-central1}"
REPOSITORY="${REPOSITORY:-clipsflow}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"
TARGET_PROJECT_ID="${PROJECT_ID:-${TARGET_PROJECT_ID:-gen-lang-client-0202582192}}"
BOT_SERVICE="${BOT_SERVICE:-clipsflow-bot}"
WEB_SERVICE="${WEB_SERVICE:-clipsflow-web}"
WEB_PUBLIC_ACCESS="${WEB_PUBLIC_ACCESS:-true}"
HARD_KILL="${HARD_KILL:-false}"
WAIT_FOR_BOT="${WAIT_FOR_BOT:-true}"
WAIT_FOR_WEB="${WAIT_FOR_WEB:-true}"

ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null)"
if [[ "${ACTIVE_PROJECT}" != "${TARGET_PROJECT_ID}" ]]; then
  echo "Switching active gcloud project: ${ACTIVE_PROJECT:-<none>} -> ${TARGET_PROJECT_ID}"
  gcloud config set project "${TARGET_PROJECT_ID}" >/dev/null
  ACTIVE_PROJECT="${TARGET_PROJECT_ID}"
fi

PROJECT_ID="${ACTIVE_PROJECT}"
if [[ -z "${PROJECT_ID}" ]]; then
  echo "No active gcloud project. Run: gcloud config set project <project-id>" >&2
  exit 1
fi

BILLING_ENABLED="$(gcloud billing projects describe "${PROJECT_ID}" --format='value(billingEnabled)' 2>/dev/null || true)"
if [[ "${BILLING_ENABLED}" != "True" ]]; then
  echo "Project ${PROJECT_ID} has billing disabled (billingEnabled=${BILLING_ENABLED:-unknown})."
  echo "Enable billing before deploy, or point deploy-gcloud.sh at a billed project."
  echo "  TARGET_PROJECT_ID=<project-id> ./deploy-gcloud.sh"
  exit 1
fi

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
RUNTIME_SERVICE_ACCOUNT="${RUNTIME_SERVICE_ACCOUNT:-${PROJECT_NUMBER}-compute@developer.gserviceaccount.com}"

gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com

gcloud artifacts repositories describe "${REPOSITORY}" \
  --location="${REGION}" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "${REPOSITORY}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="ClipsFlow containers"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --condition=None >/dev/null

kill_service() {
  local service="$1"
  local status
  status="$(gcloud run services describe "${service}" \
    --platform=managed \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format='value(status.url)' 2>/dev/null || true)"

  if [[ -z "${status}" ]]; then
    echo "Pre-deploy hard-kill: service ${service} not found, skipping."
    return 0
  fi

  echo "Pre-deploy hard-kill: deleting service ${service} (all revisions/instances)..."
  gcloud run services delete "${service}" \
    --platform=managed \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet >/dev/null 2>&1 || true
}

wait_for_service() {
  local service="$1"
  local mode="${2:-revision-ready}"
  local max_attempts="${3:-20}"
  local url

  echo "Waiting for ${service} (${mode}) to become ready..."
  for attempt in $(seq 1 "${max_attempts}"); do
    if [[ "${mode}" == "http" ]]; then
      url="$(gcloud run services describe "${service}" \
        --platform=managed \
        --region="${REGION}" \
        --project="${PROJECT_ID}" \
        --format='value(status.url)' 2>/dev/null || true)"

      if [[ -n "${url}" ]]; then
        local status_code
        status_code="$(curl -sS -o /tmp/${service}-health.txt -w "%{http_code}" --max-time 10 "${url}" || true)"
        if [[ "${status_code}" == "200" || "${status_code}" == "301" || "${status_code}" == "302" || "${status_code}" == "307" ]]; then
          echo "Service ${service} is ready: ${url} (${status_code})"
          return 0
        fi
      fi
    else
      local latest_created latest_ready
      latest_created="$(gcloud run services describe "${service}" \
        --platform=managed \
        --region="${REGION}" \
        --project="${PROJECT_ID}" \
        --format='value(status.latestCreatedRevisionName)' 2>/dev/null || true)"
      latest_ready="$(gcloud run services describe "${service}" \
        --platform=managed \
        --region="${REGION}" \
        --project="${PROJECT_ID}" \
        --format='value(status.latestReadyRevisionName)' 2>/dev/null || true)"

      if [[ -n "${latest_created}" && -n "${latest_ready}" && "${latest_created}" == "${latest_ready}" ]]; then
        echo "Service ${service} is revision-ready: ${latest_ready}"
        return 0
      fi
    fi

    if (( attempt == max_attempts )); then
      echo "Timeout waiting for ${service} readiness probe."
      return 1
    fi

    sleep 6
  done
}

ensure_web_public() {
  if [[ "${WEB_PUBLIC_ACCESS}" != "true" ]]; then
    echo "Skipping public web invoker binding (WEB_PUBLIC_ACCESS=${WEB_PUBLIC_ACCESS})."
    return 0
  fi

  echo "Ensuring ${WEB_SERVICE} is publicly accessible..."
  if gcloud run services add-iam-policy-binding "${WEB_SERVICE}" \
    --platform=managed \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --member="allUsers" \
    --role="roles/run.invoker" >/dev/null; then
    echo "Public invoker binding is set on ${WEB_SERVICE}."
  else
    echo "Failed to set public invoker binding for ${WEB_SERVICE}."
    echo "Run this manually with a higher-privileged account if needed:"
    echo "  gcloud run services add-iam-policy-binding ${WEB_SERVICE} --member=allUsers --role=roles/run.invoker --region=${REGION} --project=${PROJECT_ID}"
    return 1
  fi
}

if [[ "${HARD_KILL}" == "true" ]]; then
  set +e
  kill_service "${BOT_SERVICE}"
  kill_service "${WEB_SERVICE}"
  set -e
else
  echo "Skipping hard-kill as HARD_KILL=${HARD_KILL}."
fi

gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_REGION="${REGION}",_IMAGE_TAG="${IMAGE_TAG}"

if [[ "${WAIT_FOR_BOT}" == "true" ]]; then
  if ! wait_for_service "${BOT_SERVICE}" revision-ready; then
    echo "bot service did not become ready in time."
    exit 1
  fi
fi

if [[ "${WAIT_FOR_WEB}" == "true" ]]; then
  if ! wait_for_service "${WEB_SERVICE}" revision-ready; then
    echo "web service did not become healthy in time."
    exit 1
  fi
fi

if ! ensure_web_public; then
  exit 1
fi

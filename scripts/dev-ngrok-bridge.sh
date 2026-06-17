#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
WEB_PORT="${WEB_PORT:-3000}"
BOT_HEALTH_PORT="${BOT_HEALTH_PORT:-8080}"
NGROK_REGION="${NGROK_REGION:-us}"
RUN_BOT="${RUN_BOT:-0}"
PUBLIC_URL="${PUBLIC_URL:-}"

PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
}
trap cleanup EXIT INT TERM

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local attempts="${3:-60}"

  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "Timed out waiting for $label at $url" >&2
  exit 1
}

read_ngrok_url_from_log() {
  awk -F'"url":"' '/started tunnel/ && /https:\/\// { split($2, parts, "\""); print parts[1]; exit }' "$ROOT_DIR/.ngrok-bridge.log" 2>/dev/null
}

wait_for_ngrok_url() {
  local attempts="${1:-60}"
  local url=""

  for _ in $(seq 1 "$attempts"); do
    url="$(read_ngrok_url_from_log)"
    if [ -n "$url" ]; then
      printf '%s' "${url%/}"
      return 0
    fi
    sleep 1
  done

  echo "Timed out waiting for ngrok HTTPS tunnel. See $ROOT_DIR/.ngrok-bridge.log" >&2
  exit 1
}

need_cmd curl
need_cmd npm

cd "$WEB_DIR"

if [ ! -d node_modules ]; then
  npm ci
fi

npm run build

if [ -z "$PUBLIC_URL" ]; then
  need_cmd ngrok
  : >"$ROOT_DIR/.ngrok-bridge.log"
  ngrok http "http://127.0.0.1:$WEB_PORT" --region="$NGROK_REGION" --log=stdout --log-format=json >"$ROOT_DIR/.ngrok-bridge.log" 2>&1 &
  PIDS+=("$!")
  PUBLIC_URL="$(wait_for_ngrok_url)"
fi

export NEXT_PUBLIC_APP_URL="$PUBLIC_URL"
export MINIAPP_URL="$PUBLIC_URL/miniapp"

cat >"$ROOT_DIR/.dev-bridge.env" <<EOF
NEXT_PUBLIC_APP_URL=$NEXT_PUBLIC_APP_URL
MINIAPP_URL=$MINIAPP_URL
WEB_PORT=$WEB_PORT
BOT_HEALTH_PORT=$BOT_HEALTH_PORT
EOF

PORT="$WEB_PORT" npm run start &
PIDS+=("$!")
wait_for_url "http://127.0.0.1:$WEB_PORT/miniapp" "ClipsFlow Mini App"

if [ "$RUN_BOT" = "1" ]; then
  cd "$ROOT_DIR"
  if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
  fi
  export APP_ENV="${APP_ENV:-development}"
  export PORT="$BOT_HEALTH_PORT"
  export MINIAPP_URL="$PUBLIC_URL/miniapp"
  "${PYTHON:-python3}" main.py &
  PIDS+=("$!")
  wait_for_url "http://127.0.0.1:$BOT_HEALTH_PORT" "ClipsFlow bot health endpoint"
fi

cat <<EOF

ClipsFlow DigitalOcean/ngrok bridge is live.

Local Mini App:  http://127.0.0.1:$WEB_PORT/miniapp
Public Mini App: $PUBLIC_URL/miniapp
Bridge env:      $ROOT_DIR/.dev-bridge.env
Ngrok log:       $ROOT_DIR/.ngrok-bridge.log

Use the public Mini App URL in BotFather while testing the bridge.
Press Ctrl-C to stop the bridge.
EOF

wait

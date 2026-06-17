#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
WEB_PORT="${WEB_PORT:-3001}"
BRIDGE_PORT="${BRIDGE_PORT:-8088}"
PUBLIC_URL="${PUBLIC_URL:-}"

if [ -z "$PUBLIC_URL" ]; then
  PUBLIC_URL="$(node - <<'NODE'
const res = await fetch("http://127.0.0.1:4040/api/tunnels").catch(() => null);
if (!res?.ok) process.exit(0);
const payload = await res.json();
const tunnel = payload.tunnels?.find((item) => item.proto === "https" && item.public_url);
if (tunnel?.public_url) process.stdout.write(tunnel.public_url.replace(/\/$/, ""));
NODE
)"
fi

if [ -z "$PUBLIC_URL" ]; then
  echo "PUBLIC_URL is required when an existing ngrok tunnel cannot be discovered." >&2
  exit 1
fi

cd "$WEB_DIR"
if [ ! -d node_modules ]; then
  npm ci
fi
npm run build

tmux kill-session -t clipsflow-web 2>/dev/null || true
tmux kill-session -t clipsflow-bridge 2>/dev/null || true

tmux new-session -d -s clipsflow-web "cd '$WEB_DIR' && PORT='$WEB_PORT' NEXT_PUBLIC_APP_URL='$PUBLIC_URL' npm run start"
sleep 3
curl -fsS "http://127.0.0.1:$WEB_PORT/miniapp" >/dev/null

tmux new-session -d -s clipsflow-bridge "cd '$ROOT_DIR' && BRIDGE_PORT='$BRIDGE_PORT' BRIDGE_TARGET='http://127.0.0.1:$WEB_PORT' node scripts/ngrok-proxy-bridge.mjs"
sleep 2
curl -fsS "http://127.0.0.1:$BRIDGE_PORT/bridge" >/dev/null

cat >"$ROOT_DIR/.dev-bridge.env" <<EOF
NEXT_PUBLIC_APP_URL=$PUBLIC_URL
MINIAPP_URL=$PUBLIC_URL/miniapp
WEB_PORT=$WEB_PORT
BRIDGE_PORT=$BRIDGE_PORT
EOF

cat <<EOF
ClipsFlow is running through the DigitalOcean/ngrok bridge.

Local Mini App:  http://127.0.0.1:$WEB_PORT/miniapp
Bridge status:   http://127.0.0.1:$BRIDGE_PORT/bridge
Public Mini App: $PUBLIC_URL/miniapp
Bridge env:      $ROOT_DIR/.dev-bridge.env

tmux sessions:
  clipsflow-web
  clipsflow-bridge
EOF

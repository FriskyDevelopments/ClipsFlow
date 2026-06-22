# ClipsFlow deploy — DigitalOcean "Huge" Droplet (under expiring credits, pre-July cutover)

Runs `clipsflow-bot` with an Infisical Agent sidecar that renders secrets into a
memory-backed tmpfs (`/dev/shm/secrets/.env`), plus a fast local-SSD cache for the
FFmpeg transcoding pipeline. The same compose runs unchanged on the AWS/Oracle node
after the July cutover.

## Files
- `docker-compose.clipsflow.yml` — the stack (bot + Infisical agent sidecar).
- `infisical/agent-config.yaml` — agent auth + template/sink config.
- `infisical/env.tpl` — template materializing project secrets as `KEY=VALUE` lines.
  **Replace `<WORKSPACE_ID>`** with your Infisical project/workspace ID; adjust the
  environment slug (`prod`) and path (`/`) to match your setup.

## Host prerequisites
```bash
# Fast local-SSD cache dir referenced by the bind mount
sudo mkdir -p /mnt/data/clipsflow_cache
sudo chown 1000:1000 /mnt/data/clipsflow_cache
```

## Deploy
```bash
export INFISICAL_CLIENT_ID=...        # machine identity (universal-auth)
export INFISICAL_CLIENT_SECRET=...
docker compose -f docker-compose.clipsflow.yml up -d
docker compose -f docker-compose.clipsflow.yml logs -f infisical-agent  # confirm .env rendered
```

## Notes
- The 8 GB memory limit caps the transcoding pipeline so a leak can't take down the
  Droplet. Tune to your host.
- `FFMPEG_TEMP_DIR=/var/cache/clipsflow` keeps scratch files on the bind-mounted SSD,
  not in the small tmpfs.
- The entrypoint `export $(cat .env | xargs)` word-splits on whitespace — keep secret
  values free of spaces/quotes, or swap to a `set -a; . .env; set +a` loader.

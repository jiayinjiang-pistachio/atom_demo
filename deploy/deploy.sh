#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

git pull --ff-only
docker compose build
docker compose up -d
# Caddyfile is bind-mounted; compose keeps caddy running on the old config
# when only the file changes. Reload explicitly so new routes take effect.
docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
docker image prune -f

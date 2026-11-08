#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

git pull --ff-only
docker compose build
docker compose up -d
# The whole deploy/ directory is mounted, so git pull's file replacement is
# visible inside the container. Reload anyway to apply changes immediately
# (Caddy also runs with --watch).
docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
docker image prune -f

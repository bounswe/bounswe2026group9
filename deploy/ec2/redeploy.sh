#!/usr/bin/env bash

set -euo pipefail

if [ -z "${BACKEND_IMAGE:-}" ]; then
  echo "BACKEND_IMAGE is required"
  exit 1
fi

sudo BACKEND_IMAGE="$BACKEND_IMAGE" docker compose -f /opt/sem-backend/docker-compose.prod.yml pull
sudo BACKEND_IMAGE="$BACKEND_IMAGE" docker compose -f /opt/sem-backend/docker-compose.prod.yml up -d
sudo docker image prune -f

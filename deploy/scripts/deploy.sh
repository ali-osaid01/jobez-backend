#!/usr/bin/env sh
set -eu

if [ ! -f .env.prod ]; then
  echo ".env.prod is missing" >&2
  exit 1
fi

set -a
. ./.env.prod
set +a

./deploy/scripts/render-nginx.sh https

docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml up -d postgres chromadb
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

docker compose -f docker-compose.prod.yml ps

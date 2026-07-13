#!/usr/bin/env sh
set -eu

if [ ! -f .env.prod ]; then
  echo ".env.prod is missing" >&2
  exit 1
fi

set -a
. ./.env.prod
set +a

compose() {
  docker compose --env-file .env.prod -f docker-compose.prod.yml "$@"
}

./deploy/scripts/render-nginx.sh https

compose build backend
compose up -d postgres chromadb
compose run --rm backend alembic upgrade head
compose up -d
compose up -d --force-recreate nginx
compose exec nginx nginx -s reload

compose ps

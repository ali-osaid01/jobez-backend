#!/usr/bin/env sh
set -eu

compose() {
  docker compose --env-file .env.prod -f docker-compose.prod.yml "$@"
}

compose run --rm certbot renew --webroot --webroot-path /var/www/certbot
compose exec nginx nginx -s reload

#!/usr/bin/env sh
set -eu

DOMAIN="${APP_DOMAIN:?APP_DOMAIN is required}"
EMAIL="${LETSENCRYPT_EMAIL:-admin@${DOMAIN}}"

compose() {
  docker compose --env-file .env.prod -f docker-compose.prod.yml "$@"
}

./deploy/scripts/render-nginx.sh http
compose up -d --force-recreate nginx

compose run --rm certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN"

./deploy/scripts/render-nginx.sh https
compose up -d --force-recreate nginx
compose exec nginx nginx -s reload

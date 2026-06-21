#!/usr/bin/env sh
set -eu

DOMAIN="${APP_DOMAIN:?APP_DOMAIN is required}"
EMAIL="${LETSENCRYPT_EMAIL:-admin@${DOMAIN}}"

./deploy/scripts/render-nginx.sh http
docker compose -f docker-compose.prod.yml up -d nginx

docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN"

./deploy/scripts/render-nginx.sh https
docker compose -f docker-compose.prod.yml up -d nginx
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

#!/usr/bin/env sh
set -eu

MODE="${1:-https}"
DOMAIN="${APP_DOMAIN:?APP_DOMAIN is required}"

mkdir -p deploy/nginx deploy/certbot/www deploy/certbot/conf

if [ "$MODE" = "http" ]; then
  TEMPLATE="deploy/nginx/templates/http.conf.template"
else
  TEMPLATE="deploy/nginx/templates/https.conf.template"
fi

sed "s/__DOMAIN__/${DOMAIN}/g" "$TEMPLATE" > deploy/nginx/default.conf

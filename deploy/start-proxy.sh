#!/bin/sh
set -eu
: "${PUBLIC_HOST:?Configure PUBLIC_HOST}"
case "$PUBLIC_HOST" in
  ''|*[!a-zA-Z0-9.-]*|.*|*..*) printf '%s\n' 'PUBLIC_HOST must be a DNS hostname.' >&2; exit 1 ;;
esac
: "${PUBLIC_SITE_URL:?Configure the canonical HTTPS origin}"
case "$PUBLIC_SITE_URL" in
  "https://$PUBLIC_HOST") ;;
  "https://$PUBLIC_HOST":*)
    port=${PUBLIC_SITE_URL##*:}
    case "$port" in ''|*[!0-9]*|??????*) printf '%s\n' 'Invalid HTTPS port.' >&2; exit 1 ;; esac
    if [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
      printf '%s\n' 'Invalid HTTPS port.' >&2; exit 1
    fi ;;
  *) printf '%s\n' 'PUBLIC_SITE_URL must match the HTTPS hostname.' >&2; exit 1 ;;
esac
envsubst '$PUBLIC_HOST $PUBLIC_SITE_URL' < /etc/nginx/library.conf.template > /tmp/library-nginx.conf
exec nginx -c /tmp/library-nginx.conf -g 'daemon off;'

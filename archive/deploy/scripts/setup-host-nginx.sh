#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  sudo bash deploy/scripts/setup-host-nginx.sh <domain> <certbot_email> [app_dir] [backend_port] [frontend_port] [config_name] [nginx_conf_dir] [required_nginx_version]

Examples:
  sudo bash deploy/scripts/setup-host-nginx.sh example.com ops@example.com
  sudo bash deploy/scripts/setup-host-nginx.sh example.com ops@example.com /home/ubuntu/library_app 8000 4173

Installs or upgrades Nginx and Certbot as needed, writes the host Nginx config,
requests the certificate if missing, and enables automatic renew reload hooks.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root (use sudo)." >&2
  exit 1
fi

DOMAIN="${1:-}"
CERTBOT_EMAIL="${2:-}"
APP_DIR="${3:-$HOME/library_app}"
BACKEND_PORT="${4:-8000}"
FRONTEND_PORT="${5:-4173}"
CONFIG_NAME="${6:-$DOMAIN}"
NGINX_CONF_DIR="${7:-/etc/nginx/conf.d}"
REQUIRED_NGINX_VERSION="${8:-1.29.4}"

if [[ -z "${DOMAIN}" || -z "${CERTBOT_EMAIL}" ]]; then
  usage
  exit 1
fi

print_step() {
  printf '[setup-host-nginx] %s\n' "$*"
}

ensure_nginx() {
  local current_version=""
  if command -v nginx >/dev/null 2>&1; then
    current_version="$(nginx -v 2>&1 | sed -E 's#^nginx version: nginx/##')"
  fi

  if [[ -z "${current_version}" || ( -n "${REQUIRED_NGINX_VERSION}" && "${current_version}" != "${REQUIRED_NGINX_VERSION}" ) ]]; then
    print_step "Installing nginx ${REQUIRED_NGINX_VERSION:-latest}"
    bash deploy/scripts/install-nginx.sh "${REQUIRED_NGINX_VERSION}"
  fi
}

ensure_certbot() {
  if command -v certbot >/dev/null 2>&1; then
    return
  fi

  print_step "Installing certbot"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y certbot python3-certbot-nginx
}

ensure_permissions() {
  mkdir -p "${APP_DIR}/app/backend/storage/staticfiles" "${APP_DIR}/app/backend/storage/media" /var/www/certbot "${NGINX_CONF_DIR}"

  local app_owner_home app_owner_parent
  app_owner_home="$(dirname "${APP_DIR}")"
  app_owner_parent="$(dirname "${app_owner_home}")"

  chmod o+x "${app_owner_parent}" "${app_owner_home}"
  chmod o+rx "${APP_DIR}"

  chmod -R o+rX "${APP_DIR}/app/backend/storage/staticfiles" "${APP_DIR}/app/backend/storage/media"
}

write_http_config() {
  cat >"${CONFIG_PATH}" <<EOF
server {
  listen 80;
  server_name ${DOMAIN};

  client_max_body_size 64m;

  location /.well-known/acme-challenge/ {
    root /var/www/certbot;
  }

  location /api/ {
    proxy_pass http://127.0.0.1:${BACKEND_PORT};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_read_timeout 300s;
  }

  location /admin/ {
    proxy_pass http://127.0.0.1:${BACKEND_PORT};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_read_timeout 300s;
  }

  location /static/ {
    alias ${APP_DIR}/app/backend/storage/staticfiles/;
    expires 7d;
    add_header Cache-Control "public, max-age=604800";
  }

  location /media/ {
    alias ${APP_DIR}/app/backend/storage/media/;
    expires 1h;
    add_header Cache-Control "public, max-age=3600";
  }

  location / {
    proxy_pass http://127.0.0.1:${FRONTEND_PORT};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }
}
EOF
}

write_https_config() {
  cat >"${CONFIG_PATH}" <<EOF
server {
  listen 80;
  server_name ${DOMAIN};

  location /.well-known/acme-challenge/ {
    root /var/www/certbot;
  }

  location / {
    return 301 https://\$host\$request_uri;
  }
}

server {
  listen 443 ssl;
  server_name ${DOMAIN};

  ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_session_timeout 1d;
  ssl_session_cache shared:SSL:10m;
  ssl_prefer_server_ciphers off;

  client_max_body_size 64m;

  location /.well-known/acme-challenge/ {
    root /var/www/certbot;
  }

  location /api/ {
    proxy_pass http://127.0.0.1:${BACKEND_PORT};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_read_timeout 300s;
  }

  location /admin/ {
    proxy_pass http://127.0.0.1:${BACKEND_PORT};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_read_timeout 300s;
  }

  location /static/ {
    alias ${APP_DIR}/app/backend/storage/staticfiles/;
    expires 7d;
    add_header Cache-Control "public, max-age=604800";
  }

  location /media/ {
    alias ${APP_DIR}/app/backend/storage/media/;
    expires 1h;
    add_header Cache-Control "public, max-age=3600";
  }

  location / {
    proxy_pass http://127.0.0.1:${FRONTEND_PORT};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }
}
EOF
}

ensure_certificate() {
  if certbot certificates 2>/dev/null | grep -Fq "Domains: ${DOMAIN}"; then
    print_step "Existing certificate found for ${DOMAIN}"
    return
  fi

  print_step "Requesting new certificate for ${DOMAIN}"
  certbot certonly \
    --webroot \
    -w /var/www/certbot \
    -d "${DOMAIN}" \
    --non-interactive \
    --agree-tos \
    --no-eff-email \
    -m "${CERTBOT_EMAIL}"
}

ensure_renew_hook() {
  mkdir -p /etc/letsencrypt/renewal-hooks/deploy
  cat >/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'EOF'
#!/usr/bin/env bash
systemctl reload nginx
EOF
  chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

  if systemctl list-unit-files | grep -q '^certbot.timer'; then
    systemctl enable certbot.timer
    systemctl start certbot.timer
  else
    cat >/etc/cron.d/certbot-renew <<'EOF'
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
0 */12 * * * root certbot renew --quiet
EOF
  fi
}

case "${CONFIG_NAME}" in
  *.conf) ;;
  *) CONFIG_NAME="${CONFIG_NAME}.conf" ;;
esac
CONFIG_PATH="${NGINX_CONF_DIR}/${CONFIG_NAME}"

ensure_nginx
ensure_certbot
ensure_permissions

print_step "Writing HTTP bootstrap config"
write_http_config
nginx -t
systemctl enable nginx
systemctl reload nginx

print_step "Ensuring certificate"
ensure_certificate

print_step "Writing HTTPS config"
write_https_config
nginx -t
systemctl reload nginx

ensure_renew_hook
systemctl reload nginx
nginx -v
print_step "Host nginx and certbot configured for ${DOMAIN}"

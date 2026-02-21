# 📜 Site Configuration Template (`site.conf.template`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This `site.conf.template` file is a Jinja2-like template used to generate the production Nginx site configuration (`site.conf`) at runtime. It allows for dynamic insertion of the `DOMAIN_NAME` environment variable into the Nginx configuration, making the deployment flexible across different domains.

## Purpose

The template ensures that the Nginx configuration for the production environment is correctly set up with the specific domain name, handling both HTTP (for Certbot and HTTPS redirection) and HTTPS (for the main application traffic).

## HTTP Server Block (Port 80)

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN_NAME} www.${DOMAIN_NAME};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}
```
*   **Purpose:** Primarily for Certbot's ACME challenge and redirecting all HTTP traffic to HTTPS.
*   `server_name ${DOMAIN_NAME} www.${DOMAIN_NAME};`: Uses the `DOMAIN_NAME` environment variable to dynamically set the server names.

## HTTPS Server Block (Port 443)

```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name ${DOMAIN_NAME} www.${DOMAIN_NAME};

    # === SSL ===
    ssl_certificate /etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # === Security Headers ===
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    client_max_body_size 10M;

    # Deny hidden files
    location ~ /\.(?!well-known) {
        deny all;
        access_log off;
        log_not_found off;
    }

    # === Static Files ===
    location /static/ {
        alias /app/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # === Media ===
    location /media/ {
        alias /app/media/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header Access-Control-Allow-Origin "*";
    }

    # === API → Backend ===
    location /api/ {
        limit_req zone=api_limit burst=5 nodelay;
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # === Swagger ===
    location /docs {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /openapi.json {
        proxy_pass http://backend;
    }

    # === Health ===
    location /health {
        proxy_pass http://backend/api/v1/health;
        access_log off;
    }

    # === Block attacks ===
    location ~* (phpunit|eval-stdin|cgi-bin|\.php$|wp-admin|wp-login|\.env) {
        return 444;
    }

    # === All other requests → Django Backend ===
    location / {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

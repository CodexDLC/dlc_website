# 📜 Site Configuration (`site.conf`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This `site.conf` file defines the Nginx server blocks for the production environment, handling both HTTP (for Certbot and HTTPS redirection) and HTTPS (for the main application traffic). It includes SSL certificate configuration, security headers, and detailed routing rules for various application components.

## HTTP Server Block (Port 80)

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name lily-salon.de www.lily-salon.de;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}
```
*   **Purpose:** Primarily for Certbot's ACME challenge and redirecting all HTTP traffic to HTTPS.
*   `listen 80;`: Listens for incoming HTTP connections on port 80.
*   `server_name`: Specifies the domain names this server block responds to.
*   `location /.well-known/acme-challenge/`: Configures Nginx to serve files from `/var/www/certbot` for Certbot's domain verification process.
*   `location /`: Redirects all other HTTP traffic to the HTTPS equivalent using a 301 (permanent) redirect.

## HTTPS Server Block (Port 443)

```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name lily-salon.de www.lily-salon.de;

    # === SSL ===
    ssl_certificate /etc/letsencrypt/live/lily-salon.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lily-salon.de/privkey.pem;
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

    # === Media ===
    location /media/ {
        alias /app/media/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header Access-Control-Allow-Origin "*";
    }

    # === Health ===
    location /health {
        proxy_pass http://backend;
        access_log off;
    }

    # === Block attacks ===
    location ~* (phpunit|eval-stdin|cgi-bin|\.php$|wp-admin|wp-login|\.env) {
        return 444;
    }
}

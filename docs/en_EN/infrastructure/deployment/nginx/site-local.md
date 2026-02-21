# 📜 Local Site Configuration (`site-local.conf`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This `site-local.conf` file defines the Nginx server block for the local development environment. It is configured to handle HTTP traffic only (no SSL) and provides routing for static files, media, API endpoints, and the main backend application.

## HTTP Server Block (Port 80)

```nginx
server {
    listen 80;
    server_name localhost;

    client_max_body_size 10M;

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

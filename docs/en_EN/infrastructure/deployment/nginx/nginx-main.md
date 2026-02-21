# 📜 Nginx Main Configuration (`nginx-main.conf`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This `nginx-main.conf` file defines the global Nginx configuration, including event processing, HTTP settings, logging formats, performance optimizations, Gzip compression, upstream definitions, and rate limiting zones. It serves as the core configuration for all Nginx instances.

## `events` Block

```nginx
events {
    worker_connections 1024;
}
```
*   `worker_connections 1024;`: Sets the maximum number of simultaneous connections that can be opened by a worker process.

## `http` Block

This block contains the main HTTP server configurations.

### MIME Types

```nginx
include /etc/nginx/mime.types;
default_type application/octet-stream;
```
*   `include /etc/nginx/mime.types;`: Includes a file that maps file extensions to MIME types.
*   `default_type application/octet-stream;`: Sets the default MIME type for files if Nginx cannot determine it.

### Logging Format (JSON)

```nginx
log_format json_combined escape=json
'{'
    '"time_local":"$time_local",'
    '"remote_addr":"$remote_addr",'
    '"remote_user":"$remote_user",'
    '"request":"$request",'
    '"status": "$status",'
    '"body_bytes_sent":"$body_bytes_sent",'
    '"request_time":"$request_time",'
    '"http_referrer":"$http_referer",'
    '"http_user_agent":"$http_user_agent",'
    '"upstream_addr":"$upstream_addr",'
    '"upstream_response_time":"$upstream_response_time"'
'}';
```
Defines a custom JSON format for access logs, providing detailed information about each request.

### Logging

```nginx
access_log /var/log/nginx/access.log json_combined;
error_log /var/log/nginx/error.log warn;
```
*   `access_log`: Configures the access log to use the `json_combined` format.
*   `error_log`: Sets the error log file and level (`warn`).

### Performance

```nginx
sendfile on;
tcp_nopush on;
tcp_nodelay on;
keepalive_timeout 65;
```
Optimizations for network performance.

### Gzip Compression

```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css application/json application/javascript
           text/xml application/xml application/xml+rss text/javascript
           image/svg+xml;
```
Enables Gzip compression for specified content types, reducing bandwidth usage.

### Upstream (Backend)

```nginx
upstream backend {
    server backend:8000;
}
```
Defines an upstream block named `backend` that points to the backend service running on port 8000. This allows Nginx to proxy requests to the backend container.

### Rate Limiting

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=general_limit:10m rate=30r/s;
```
Defines two rate limiting zones:
*   `api_limit`: Limits requests to 10 requests per second for API endpoints.
*   `general_limit`: Limits requests to 30 requests per second for general static content.

### Site Configurations

```nginx
include /etc/nginx/conf.d/*.conf;
```
Includes all `.conf` files from the `/etc/nginx/conf.d/` directory. This is where site-specific configurations (like `site.conf` or `default.conf`) are loaded.

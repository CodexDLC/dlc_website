# 📜 Dockerfile.local

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This Dockerfile defines how the Nginx Docker image is built for local development environments. It provides a simplified Nginx setup, primarily serving HTTP traffic without SSL, suitable for development and testing.

## Build Process

*   **Base Image:** `nginx:alpine` (a lightweight Nginx image).
*   **Remove Default Configurations:**
    *   `RUN rm /etc/nginx/conf.d/*`: Deletes all default Nginx configuration files to ensure a clean slate for custom configurations.
*   **Copy Main Nginx Configuration:**
    *   `COPY deploy/nginx/nginx-main.conf /etc/nginx/nginx.conf`: Copies the project's main Nginx configuration file, which includes global settings, upstreams, and other core directives.
*   **Copy Local Site Configuration:**
    *   `COPY deploy/nginx/site-local.conf /etc/nginx/conf.d/default.conf`: Copies the local development-specific Nginx site configuration. This configuration typically handles HTTP traffic and proxies to the backend without SSL.
*   **Exposed Ports:**
    *   `EXPOSE 80`: Informs Docker that the container listens on port 80 (HTTP).
*   **Command:**
    *   `CMD ["nginx", "-g", "daemon off;"]`: Starts the Nginx server in the foreground, which is a Docker best practice.

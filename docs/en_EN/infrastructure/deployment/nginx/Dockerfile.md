# 📜 Dockerfile

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This Dockerfile defines how the production Nginx Docker image is built. It customizes the base Nginx image by replacing default configurations with project-specific ones, setting up SSL/TLS, and enabling dynamic configuration based on environment variables.

## Build Process

*   **Base Image:** `nginx:alpine` (a lightweight Nginx image).
*   **Remove Default Configurations:**
    *   `RUN rm /etc/nginx/conf.d/*`: Deletes all default Nginx configuration files to ensure a clean slate for custom configurations.
*   **Copy Main Nginx Configuration:**
    *   `COPY deploy/nginx/nginx-main.conf /etc/nginx/nginx.conf`: Copies the project's main Nginx configuration file, which includes global settings, upstreams, and other core directives.
*   **Copy Site Configuration Template:**
    *   `COPY deploy/nginx/site.conf.template /etc/templates/site.conf.template`: Copies a template for the site-specific Nginx configuration. This template will be dynamically rendered at runtime.
*   **Create Certbot Directory:**
    *   `RUN mkdir -p /var/www/certbot`: Creates a directory used by Certbot for ACME challenges (SSL certificate issuance/renewal).
*   **Exposed Ports:**
    *   `EXPOSE 80 443`: Informs Docker that the container listens on ports 80 (HTTP) and 443 (HTTPS).
*   **Command:**
    *   `CMD ["/bin/sh", "-c", "envsubst '${DOMAIN_NAME}' < /etc/templates/site.conf.template > /etc/nginx/conf.d/site.conf && exec nginx -g 'daemon off;'"]`: This command is executed when the container starts.
        *   `envsubst '${DOMAIN_NAME}' < /etc/templates/site.conf.template > /etc/nginx/conf.d/site.conf`: Uses `envsubst` to replace the `${DOMAIN_NAME}` placeholder in `site.conf.template` with the actual value from the `DOMAIN_NAME` environment variable. The result is written to `/etc/nginx/conf.d/site.conf`, creating the final Nginx site configuration.
        *   `exec nginx -g 'daemon off;'`: Starts the Nginx server in the foreground, which is a Docker best practice.

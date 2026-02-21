FROM nginx:alpine

# Remove default configs
RUN rm /etc/nginx/conf.d/*

# Copy main nginx config
COPY deploy/nginx/nginx-main.conf /etc/nginx/nginx.conf

# Copy site config template (domain injected via envsubst at runtime)
COPY deploy/nginx/site.conf.template /etc/templates/site.conf.template

# Create Certbot directory
RUN mkdir -p /var/www/certbot

EXPOSE 80 443

# Inject DOMAIN_NAME env var into config at startup, then run nginx
CMD ["/bin/sh", "-c", "envsubst '${DOMAIN_NAME}' < /etc/templates/site.conf.template > /etc/nginx/conf.d/site.conf && exec nginx -g 'daemon off;'"]

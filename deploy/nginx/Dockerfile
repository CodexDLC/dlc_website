# DLC Montage — Nginx reverse proxy image
FROM nginx:1.27-alpine

# Copy custom Nginx configuration
COPY deploy/nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Prepare mount directories for staticfiles and media
RUN mkdir -p /app/staticfiles /app/media

EXPOSE 80

STOPSIGNAL SIGQUIT

CMD ["nginx", "-g", "daemon off;"]

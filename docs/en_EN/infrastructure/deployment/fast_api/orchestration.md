# 🎼 Orchestration

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

The project uses `docker-compose` for local development and production deployment orchestration.

## Services

### Backend (`pinlite-backend`)
- **Build Context:** `deploy/Fast_api/Dockerfile`
- **Network:** `pinlite-network`
- **Volumes:**
  - `backend/`: Mounted read-only for code hot-reloading (dev).
  - `uploads/`: Persistent storage for user media.
  - `logs/`: Persistent storage for application logs.
- **Environment Variables:**
  - `DATABASE_URL`: Connection string for PostgreSQL.
  - `SECRET_KEY`: Application secret.
  - `SITE_URL`: Public domain of the site.

### Nginx (`pinlite-nginx`)
- **Image:** `nginx:alpine`
- **Ports:** `80:80` (Host:Container)
- **Depends On:** Backend (waits for healthcheck).
- **Volumes:**
  - Config files mounted from `deploy/nginx/`.
  - Static frontend files.

## Networks

- **pinlite-network:** Bridge network allowing communication between Backend and Nginx.

## Volumes

- **uploads:** Local driver.
- **logs:** Local driver.

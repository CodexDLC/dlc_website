# 🛡️ Server Configuration

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

Nginx acts as the entry point for the application, handling SSL termination, static file serving, and reverse proxying to the backend.

## Virtual Hosts

### HTTP (Port 80)
- **Purpose:** ACME Challenge & HTTPS Redirect.
- **Rules:**
  - Serves `/.well-known/acme-challenge/` for Certbot.
  - Redirects all other traffic to HTTPS (301).

### HTTPS (Port 443)
- **Purpose:** Main application traffic.
- **SSL:**
  - Certificates: Let's Encrypt (`/etc/letsencrypt/live/pinlite.dev/`).
  - Protocols: TLSv1.2, TLSv1.3.
  - Ciphers: Strong modern cipher suite.

## Routing

| Path | Destination | Notes |
|:---|:---|:---|
| `/` | `/usr/share/nginx/html` | Serves Frontend static files (SPA). |
| `/api/` | `http://backend:8000` | Proxies to FastAPI backend. |
| `/docs`, `/openapi.json` | `http://backend:8000` | Swagger UI (proxied). |
| `/media/` | `/app/media/` | Serves uploaded user content. |

## Security Measures

1. **Headers:**
   - `Strict-Transport-Security` (HSTS)
   - `X-Frame-Options: SAMEORIGIN`
   - `X-Content-Type-Options: nosniff`
   - `X-XSS-Protection: 1; mode=block`
2. **Access Control:**
   - Hidden files (`.git`, `.env`) are denied.
   - Suspicious query strings (SQL injection patterns) are blocked.
   - PHP/CGI execution attempts are blocked (444).
3. **Rate Limiting:**
   - `api_limit`: 10 r/s (burst 5) for `/api/`.
   - `general_limit`: 30 r/s (burst 20) for static content.

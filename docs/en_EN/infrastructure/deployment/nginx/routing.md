# 🗺️ Routing Map

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

Request routing map within Nginx.

| URL Pattern | Purpose | Destination | Comment |
| :--- | :--- | :--- | :--- |
| `/api/*` | API Requests | `http://backend:8000` | Proxied to Python container. |
| `/auth/*` | Auth Requests | `http://backend:8000` | Proxied to Python container. |
| `/docs` | Swagger UI | `http://backend:8000` | FastAPI auto-generated docs. |
| `/media/*` | User Content | `file:///app/media/` | Direct file serving from disk (Alias). |
| `/` | Frontend | `file:///usr/share/nginx/html/` | Serves `index.html` and static assets. |

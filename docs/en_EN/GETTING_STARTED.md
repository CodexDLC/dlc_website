# 🚀 Getting Started

[⬅️ Back](./README.md) | [🏠 Docs Root](../../README.md)

This guide covers how to run the project locally for development and testing.

## 🐳 Docker Run (Recommended)

The easiest way to spin up the entire environment (Backend, DB, Nginx).

### Start
```bash
# Build and start in background
docker-compose up -d --build
```
- **Backend API:** `http://localhost:8000` (or via Nginx at `http://localhost`)
- **Swagger Docs:** `http://localhost:8000/docs`

### Logs
```bash
# All services
docker-compose logs -f

# Specific logic
docker-compose logs -f backend
```

### Stop
```bash
# Stop containers
docker-compose stop

# Stop and remove containers (volumes preserved)
docker-compose down
```

### Cleanup (Caution!)
```bash
# Remove containers, networks, and VOLUMES (DB data and uploads will be lost!)
docker-compose down -v
```

---

## 🐍 Local Run (Development)

If you need to debug code or run without Docker.

### 1. Database
You still need PostgreSQL. Run just the DB in Docker:
```bash
docker-compose up -d db
```
Or use an external Postgres (Neon, local). Ensure `.env` is configured correctly.

### 2. Backend
```bash
cd backend
# Activate venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run server with Hot Reload
uvicorn main:app --reload
```

### 3. Frontend
Open `frontend/index.html` in your browser or use "Live Server" in VS Code.
*   ⚠️ **Status:** API integration is in progress. Currently works on localStorage.

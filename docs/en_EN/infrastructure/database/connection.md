# 🔌 Database Connection

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

The project uses **PostgreSQL** as the primary database.

## ☁️ Neon (Serverless Postgres)
For the current stage (MVP), we use the cloud database [Neon.tech](https://neon.tech).

### Connection String
The connection string is defined in the `DATABASE_URL` environment variable in the `.env` file.

```ini
DATABASE_URL=postgresql+asyncpg://user:password@ep-host-123.aws.neon.tech/dbname?ssl=require
```

- **Driver:** `asyncpg` (required for SQLAlchemy asynchronous operations).
- **SSL:** Mandatory (`ssl=require`) for Neon connections.

## 🐍 Local Postgres
For local development without internet access, you can use the Dockerized Postgres service defined in `docker-compose.yml`.

```ini
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app_db
```

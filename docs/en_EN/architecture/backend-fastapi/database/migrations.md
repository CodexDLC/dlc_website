# 🔄 Database Migrations

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

Documentation on working with database migrations via Alembic.

## 📋 Contents

*   [Automatic Migrations](#automatic-migrations)
*   [Creating Migrations](#creating-migrations)
*   [Applying Migrations](#applying-migrations)
*   [Alembic Commands](#alembic-commands)
*   [Configuration](#configuration)

---

## Automatic Migrations

The project is configured to automatically run migrations when the application starts.

### AUTO_MIGRATE Flag

Controlled via the `AUTO_MIGRATE` environment variable in `src/backend-fastapi/core/config.py`:

```python
AUTO_MIGRATE: bool = True  # Enabled by default
```

**Behavior:**
*   `AUTO_MIGRATE=True` — migrations run automatically on app startup.
*   `AUTO_MIGRATE=False` — migrations must be run manually.

### When to Use

**✅ Enabled (True):**
*   Local development
*   Staging environment
*   Simple projects

**❌ Disabled (False):**
*   Production environment with critical data
*   When precise control over migrations is needed
*   CI/CD pipelines with a separate migration step

---

## Creating Migrations

### Autogenerate Migration

Alembic automatically detects changes in SQLAlchemy models:

```bash
# Local
docker-compose exec backend alembic revision --autogenerate -m "Description of changes"

# Production
docker compose -f docker-compose.prod.yml exec -T backend alembic revision --autogenerate -m "Description of changes"
```

### Empty Migration (for manual changes)

```bash
docker-compose exec backend alembic revision -m "Description of changes"
```

### Message Recommendations

*   Use imperative verbs: `"Add user avatar field"`, `"Remove deprecated columns"`.
*   Be specific: `"Add indexes to user.email and user.username"`.
*   Group related changes into one migration.

---

## Applying Migrations

### Automatically (when AUTO_MIGRATE=True)

Migrations are applied automatically on app startup in `src/backend-fastapi/main.py`:

```python
async def lifespan(app: FastAPI):
    logger.info("🚀 Server starting... Project: PinLite")

    if settings.AUTO_MIGRATE:
        logger.info("Running database migrations (AUTO_MIGRATE=True)...")
        await run_alembic_migrations()
    else:
        logger.warning("⚠️ AUTO_MIGRATE=False: Skipping migrations.")
```

### Manually

```bash
# Apply all migrations up to the latest
docker-compose exec backend alembic upgrade head

# Apply a specific migration
docker-compose exec backend alembic upgrade <revision_id>

# Rollback one migration
docker-compose exec backend alembic downgrade -1

# Rollback to a specific revision
docker-compose exec backend alembic downgrade <revision_id>
```

---

## Alembic Commands

### View History

```bash
# Show current revision
docker-compose exec backend alembic current

# Show migration history
docker-compose exec backend alembic history

# Show details of a specific migration
docker-compose exec backend alembic show <revision_id>
```

### Check Status

```bash
# Show list of pending migrations
docker-compose exec backend alembic heads

# Check if migrations are in sync
docker-compose exec backend alembic check
```

---

## Configuration

### File Structure

```text
src/backend-fastapi/
├── alembic/
│   ├── env.py              # Alembic environment config
│   ├── script.py.mako      # Template for new migrations
│   └── versions/           # Folder with migrations
│       └── xxxx_initial_migration.py
├── alembic.ini             # Main Alembic config
└── core/
    ├── config.py           # Contains AUTO_MIGRATE
    └── database.py         # run_alembic_migrations()
```

### alembic/env.py

Main settings:

```python
# Import project settings
from app.core.config import settings
from app.core.database import Base

# Import all models for autogeneration
import app.database.models  # noqa: F401

# Database URL from settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# SQLAlchemy Metadata
target_metadata = Base.metadata
```

### Asynchronous Execution

Migrations run asynchronously via `asyncio.to_thread()` in `src/backend-fastapi/core/database.py`:

```python
async def run_alembic_migrations() -> None:
    import asyncio
    from alembic import command
    from alembic.config import Config
    from pathlib import Path

    def _run_sync_migrations():
        try:
            alembic_cfg_path = Path(__file__).parent.parent / "alembic.ini"
            if not alembic_cfg_path.exists():
                logger.warning("alembic.ini not found")
                return
            alembic_cfg = Config(str(alembic_cfg_path))
            command.upgrade(alembic_cfg, "head")
            logger.info("Database | action=run_migrations status=success")
        except Exception as exc:
            logger.error(f"Database | action=run_migrations status=failed error={exc}")
            raise

    await asyncio.to_thread(_run_sync_migrations)
```

---

## CI/CD Integration

### GitHub Actions

In `.github/workflows/cd-release.yml`, migrations run after deploy:

```yaml
- name: Deploy and Run Migrations
  run: |
    docker compose -f docker-compose.prod.yml up -d --wait
    docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
```

### Production Recommendations

1.  **Disable AUTO_MIGRATE** in production:
    ```bash
    AUTO_MIGRATE=False
    ```

2.  **Run migrations in CI/CD** after deploy:
    ```bash
    docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
    ```

3.  **Backup** before migrations:
    ```bash
    pg_dump -U user -d database > backup_$(date +%Y%m%d_%H%M%S).sql
    ```

4.  **Test migrations** on staging environment before production.

---

## Troubleshooting

### Migrations not applying automatically

1.  Check `AUTO_MIGRATE`:
    ```bash
    docker-compose exec backend python -c "from app.core.config import settings; print(settings.AUTO_MIGRATE)"
    ```

2.  Check logs:
    ```bash
    docker-compose logs backend | grep migration
    ```

### Migration Conflicts

When working in a team, migration branch conflicts may occur:

```bash
# Merge two migration branches
docker-compose exec backend alembic merge -m "Merge migrations" <revision1> <revision2>
```

### Migration fails to apply

1.  Check current revision:
    ```bash
    docker-compose exec backend alembic current
    ```

2.  Check list of available migrations:
    ```bash
    docker-compose exec backend alembic heads
    ```

3.  Try applying a specific revision:
    ```bash
    docker-compose exec backend alembic upgrade <revision_id>
    ```

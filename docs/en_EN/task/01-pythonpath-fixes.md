# Task 01: PYTHONPATH Fixes

**Priority:** 🔴 Critical
**Status:** ⬜ Not Started
**Estimated Time:** 2-3 hours
**Dependencies:** None (start here!)

---

## Problem Summary

Projects created from this template fail to run in Docker with `ModuleNotFoundError: No module named 'src'` because:

1. Dockerfiles set incorrect PYTHONPATH values
2. docker-compose.yml generation is missing shared volume mounts
3. CI/CD workflows use wrong paths for Django management commands
4. Local development lacks PYTHONPATH configuration in pytest

**Root Cause:** Inconsistency between where files are copied (`/app/src/`) and what PYTHONPATH points to.

**Impact:** 🔴 **CRITICAL** - All Docker deployments are broken without manual intervention.

---

## Issues to Fix

### Issue #1: Django Dockerfile - Wrong PYTHONPATH

**File:** `tools/init_project/actions/docker/resources/django/Dockerfile.tpl`
**Line:** 49

**Current Code:**
```dockerfile
ENV PYTHONPATH="/app/src/backend_django:$PYTHONPATH"
```

**Problem:**
- Files are copied to `/app/src/backend_django` and `/app/src/shared`
- But PYTHONPATH `/app/src/backend_django` doesn't help imports like `from src.shared.xxx`
- Python can't find `src.shared` module

**Fix:**
```diff
- ENV PYTHONPATH="/app/src/backend_django:$PYTHONPATH"
+ ENV PYTHONPATH="/app:$PYTHONPATH"
```

**Why This Works:**
- `/app` contains the `src/` directory structure
- Python can now resolve `from src.shared.core import ...`
- Matches local development PYTHONPATH setup

---

### Issue #2: Django Dockerfile - collectstatic Path

**File:** `tools/init_project/actions/docker/resources/django/Dockerfile.tpl`
**Line:** 57

**Current Code:**
```dockerfile
RUN python /app/src/backend_django/manage.py collectstatic --noinput 2>/dev/null || true
```

**Problem:**
- Uses absolute path instead of changing directory
- Inconsistent with the CMD which uses `--chdir`
- Harder to read and maintain

**Fix:**
```diff
- RUN python /app/src/backend_django/manage.py collectstatic --noinput 2>/dev/null || true
+ RUN cd /app/src/backend_django && python manage.py collectstatic --noinput 2>/dev/null || true
```

**Why This Works:**
- Matches the pattern used in CMD (line 60)
- Makes it clear we're working in the Django directory
- Easier to adapt if directory structure changes

---

### Issue #3: Bot Dockerfile - Missing PYTHONPATH

**File:** `tools/init_project/actions/docker/resources/bot/Dockerfile.tpl`
**Line:** After line 31 (after `ENV PATH`)

**Current Code:**
```dockerfile
ENV PATH="/app/.venv/bin:$PATH"

# Start bot
CMD ["python", "-m", "src.telegram_bot.app_telegram"]
```

**Problem:**
- No PYTHONPATH set at all!
- Relies on `python -m src.xxx` to implicitly add paths
- Not explicit and can break if command changes

**Fix:**
```diff
  ENV PATH="/app/.venv/bin:$PATH"
+ ENV PYTHONPATH="/app:$PYTHONPATH"

  # Start bot
  CMD ["python", "-m", "src.telegram_bot.app_telegram"]
```

**Why This Works:**
- Makes PYTHONPATH explicit and consistent with Django
- Ensures imports work regardless of how the bot is started
- Matches the pattern in other containers

---

### Issue #4: Worker Dockerfile - Missing PYTHONPATH

**File:** `tools/init_project/actions/docker/resources/worker/Dockerfile.tpl`
**Line:** After line 31 (after `ENV PATH`)

**Current Code:**
```dockerfile
ENV PATH="/app/.venv/bin:$PATH"

# Start ARQ worker
CMD ["python", "-m", "src.telegram_bot.services.worker.bot_worker"]
```

**Problem:**
- Same as Bot Dockerfile - no explicit PYTHONPATH
- Inconsistent with other services

**Fix:**
```diff
  ENV PATH="/app/.venv/bin:$PATH"
+ ENV PYTHONPATH="/app:$PYTHONPATH"

  # Start ARQ worker
  CMD ["python", "-m", "src.telegram_bot.services.worker.bot_worker"]
```

**Why This Works:**
- Consistency across all Docker services
- Explicit is better than implicit
- Future-proof if worker code changes

---

### Issue #5: docker-compose Django Service - Missing shared Volume

**File:** `tools/init_project/actions/docker/docker.py`
**Line:** 458

**Current Code:**
```python
def _svc_django_dev(name: str) -> str:
    return dedent(f"""\
      backend:
        build:
          context: ..
          dockerfile: deploy/django/Dockerfile
        container_name: {name}-backend
        env_file: ../.env
        volumes:
          - ../src/backend_django:/app/src/backend_django
          - staticfiles:/app/staticfiles
          - logs:/app/data/logs
        expose:
          - "8000"
```

**Problem:**
- Only mounts `backend_django`, doesn't mount `shared`!
- Django can't see changes to shared code during development
- Different from bot/worker which DO mount shared

**Fix:**
```diff
        volumes:
          - ../src/backend_django:/app/src/backend_django
+         - ../src/shared:/app/src/shared:ro
          - staticfiles:/app/staticfiles
          - logs:/app/data/logs
```

**Why This Works:**
- Django can now see shared module during development
- `:ro` (read-only) prevents Django from modifying shared code
- Matches bot/worker pattern

---

### Issue #6: docker-compose Django Service - Wrong Command Path

**File:** `tools/init_project/actions/docker/docker.py`
**Line:** 464

**Current Code:**
```python
        command: >
          python /app/src/backend_django/manage.py runserver 0.0.0.0:8000
```

**Problem:**
- Uses absolute path `/app/src/...` instead of relative path
- WORKDIR is `/app`, so should use relative path from there
- Less flexible if directory structure changes

**Fix:**
```diff
-       command: >
-         python /app/src/backend_django/manage.py runserver 0.0.0.0:8000
+       command: python src/backend_django/manage.py runserver 0.0.0.0:8000
```

**Why This Works:**
- Relative path from WORKDIR `/app` is cleaner
- More maintainable if structure changes
- Matches the production CMD style
- Consistent with bot/worker commands

---

### Issue #7: CD Workflow - Migrate Command Paths

**File:** `tools/init_project/actions/docker/docker.py`
**Lines:** 280-281

**Current Code:**
```python
# Django: migrate + collectstatic before starting
migrate_step = dedent("""\
            docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python manage.py migrate --noinput
            docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python manage.py collectstatic --noinput""")
```

**Problem:**
- WORKDIR in container is `/app`, not `/app/src/backend_django`
- `python manage.py` won't find manage.py at the root
- CI/CD deployments will fail

**Fix:**
```diff
  migrate_step = dedent("""\
-             docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python manage.py migrate --noinput
-             docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python manage.py collectstatic --noinput""")
+             docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python src/backend_django/manage.py migrate --noinput
+             docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python src/backend_django/manage.py collectstatic --noinput""")
```

**Why This Works:**
- Uses full path from WORKDIR `/app`
- Matches the Dockerfile CMD pattern
- CI/CD will run successfully

---

### Issue #8: pytest Configuration - Missing pythonpath

**File:** `pyproject.toml`
**Line:** After line 105 (in `[tool.pytest.ini_options]` section)

**Current Code:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["src"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

**Problem:**
- pytest doesn't add project root to PYTHONPATH automatically
- Tests fail locally with `ModuleNotFoundError: No module named 'src'`
- Developers must manually set PYTHONPATH before running tests

**Fix:**
```diff
  [tool.pytest.ini_options]
  asyncio_mode = "auto"
  testpaths = ["src"]
  python_files = ["test_*.py"]
  python_classes = ["Test*"]
  python_functions = ["test_*"]
+ pythonpath = ["."]
```

**Why This Works:**
- pytest automatically adds `.` (project root) to PYTHONPATH
- Tests work "out of the box" without manual setup
- Consistent behavior across different developer environments

---

## Testing Instructions

After applying all fixes:

### 1. Test Template Generation

```bash
cd C:\install\progect\project-template
python -m tools.init_project --backend django --bot --project-name test_fix
```

**Verify:**
- [ ] `test_fix/deploy/django/Dockerfile` has `ENV PYTHONPATH="/app:$PYTHONPATH"` (line ~49)
- [ ] `test_fix/deploy/bot/Dockerfile` has `ENV PYTHONPATH="/app:$PYTHONPATH"` (line ~32)
- [ ] `test_fix/deploy/worker/Dockerfile` has `ENV PYTHONPATH="/app:$PYTHONPATH"` (line ~32)
- [ ] `test_fix/deploy/docker-compose.yml` Django service mounts `../src/shared:/app/src/shared:ro`
- [ ] `test_fix/deploy/docker-compose.yml` Django command uses forward slashes and relative path

### 2. Test Docker Build

```bash
cd test_fix/deploy
docker-compose build
```

**Expected:**
- ✅ All images build successfully
- ✅ No errors in build logs
- ✅ collectstatic runs without errors in Django build

### 3. Test Docker Run

```bash
docker-compose up
```

**Expected:**
- ✅ All containers start (backend, bot, worker, redis, postgres)
- ✅ No `ModuleNotFoundError` in logs
- ✅ Django: `from src.shared.core import ...` works
- ✅ Bot: Can import shared modules
- ✅ Worker: Can import shared modules

**Check logs:**
```bash
docker-compose logs backend | grep -i "ModuleNotFoundError"
docker-compose logs bot | grep -i "ModuleNotFoundError"
docker-compose logs worker | grep -i "ModuleNotFoundError"
```

Should return empty (no errors).

### 4. Test Local Pytest

```bash
cd test_fix
pytest src/
```

**Expected:**
- ✅ Tests discover modules without manual PYTHONPATH setup
- ✅ `from src.shared.xxx` imports work in tests
- ✅ No import errors

### 5. Test CI/CD Workflow (if possible)

If you have a test deployment:

1. Push generated template to GitHub
2. Trigger CD workflow (push to `release` branch)
3. Verify migrate and collectstatic steps succeed

**Check GitHub Actions logs:**
- ✅ `docker compose ... run backend python src/backend_django/manage.py migrate` succeeds
- ✅ `docker compose ... run backend python src/backend_django/manage.py collectstatic` succeeds

---

## Rollback Plan

If issues are discovered after applying fixes:

1. **Revert Dockerfile templates:**
   ```bash
   git checkout tools/init_project/actions/docker/resources/
   ```

2. **Revert docker.py:**
   ```bash
   git checkout tools/init_project/actions/docker/docker.py
   ```

3. **Revert pyproject.toml:**
   ```bash
   git checkout pyproject.toml
   ```

---

## Related Issues

- **Task 02:** [Code Quality Fixes](./02-code-quality-fixes.md) - Run linter after these changes
- **Task 03:** [Documentation Updates](./03-documentation-updates.md) - Add PYTHONPATH setup guide
- **Task 04:** [CI/CD Fixes](./04-cicd-fixes.md) - Related GitHub Actions fixes

---

## Checklist

Before marking this task complete:

- [ ] All 8 issues fixed
- [ ] Template generation tested
- [ ] Docker build tested
- [ ] Docker run tested (no import errors)
- [ ] Local pytest works without manual PYTHONPATH
- [ ] CI/CD workflow tested (if possible)
- [ ] Code changes committed to feature branch
- [ ] Tests pass: `tools/dev/check_local.ps1`

---

**Last Updated:** 2026-02-12
**Status:** ⬜ Ready for Implementation

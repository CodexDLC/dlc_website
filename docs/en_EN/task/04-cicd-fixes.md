# Task 04: CI/CD Template Fixes

**Priority:** 🟡 High
**Status:** ⬜ Not Started
**Estimated Time:** 1-2 hours
**Dependencies:** Task 01 (understanding PYTHONPATH issues helps here)

---

## Problem Summary

GitHub Actions workflows are **generated from templates** by the `docker.py` script. The generated workflows have issues:

1. **Django migrate/collectstatic paths** - Use `python manage.py` instead of `python src/backend_django/manage.py`
2. **Potential YAML indentation** - Need to verify generated YAML is valid

**Root Cause:** The `docker.py` script that generates CI/CD workflows wasn't updated when project structure changed to use `/app` WORKDIR with `src/` subdirectories.

**Impact:** 🟡 **HIGH** - Automated deployments fail. Migrations don't run. Static files aren't collected.

---

## Understanding the System

### How Workflows are Generated

**NOT like this:**
```
.github/workflows/cd-release.yml  ← Static file we edit directly
```

**But like this:**
```
tools/init_project/actions/docker/resources/github/cd-release.yml.tpl  ← Template
                    ↓ (processed by docker.py)
.github/workflows/cd-release.yml  ← Generated file in new project
```

**This means:**
- We don't edit `.github/workflows/*.yml` files directly
- We fix the `docker.py` script that generates them
- We fix the `.tpl` template files

---

## Issue #1: Django Migrate Commands - Wrong Paths

### Current Code

**File:** `tools/init_project/actions/docker/docker.py`
**Lines:** 280-281

```python
# Django: migrate + collectstatic before starting
migrate_step = dedent("""\
            docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python manage.py migrate --noinput
            docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python manage.py collectstatic --noinput""")
```

### Problem

The Docker container has:
- WORKDIR: `/app`
- Django code: `/app/src/backend_django/`
- `manage.py` location: `/app/src/backend_django/manage.py`

So `python manage.py` won't find the file. Need `python src/backend_django/manage.py`.

### Fix

```diff
  # Django: migrate + collectstatic before starting
  migrate_step = dedent("""\
-             docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python manage.py migrate --noinput
-             docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python manage.py collectstatic --noinput""")
+             docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python src/backend_django/manage.py migrate --noinput
+             docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python src/backend_django/manage.py collectstatic --noinput""")
```

### Generated Output (after fix)

The generated `cd-release.yml` will have:

```yaml
- name: SSH Deploy
  uses: appleboy/ssh-action@master
  with:
    host: ${{ secrets.HOST }}
    username: ${{ secrets.USERNAME }}
    key: ${{ secrets.SSH_KEY }}
    script: |
      cd /opt/my_project

      docker compose -f deploy/docker-compose.prod.yml pull
      docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python src/backend_django/manage.py migrate --noinput
      docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python src/backend_django/manage.py collectstatic --noinput
      docker compose -f deploy/docker-compose.prod.yml up -d --remove-orphans --wait

      docker image prune -f
```

---

## Issue #2: Django Build Step - Indentation (Verify Only)

### Current Code

**File:** `tools/init_project/actions/docker/docker.py`
**Lines:** 210-211

```python
if ctx.backend == "django":
    # ... (other code) ...
    build_steps += dedent("""\
          - name: Build Django image
            run: docker build -f deploy/django/Dockerfile -t check-backend .""")
```

### What to Check

When you run the template generator, verify the generated `ci-main.yml` has correct indentation:

```yaml
jobs:
  test:
    steps:
      - uses: actions/checkout@v4

      - name: Build Django image
        run: docker build -f deploy/django/Dockerfile -t check-backend .
```

**Look for:**
- ✅ `- name:` is aligned with `- uses:` (same indentation level)
- ✅ `run:` is indented 2 spaces from `name:`
- ❌ NOT: Extra spaces or misaligned steps

### If Indentation is Wrong

The issue is in the `dedent()` + concatenation logic. The fix would be:

```python
build_steps += dedent("""\
      - name: Build Django image
        run: docker build -f deploy/django/Dockerfile -t check-backend .""")
```

But **FIRST TEST** if it's actually wrong before changing! Generate a test project and check the YAML.

---

## Issue #3: Bot Build Step - Verify Indentation

### Current Code

**File:** `tools/init_project/actions/docker/docker.py`
**Lines:** 214-216

```python
if ctx.include_bot:
    build_steps += dedent("""\
          - name: Build Bot image
            run: docker build -f deploy/bot/Dockerfile -t check-bot .""")
```

### What to Check

Same as Issue #2 - verify the generated `ci-main.yml` has correct indentation for the Bot build step.

**Expected in generated file:**
```yaml
- name: Build Bot image
  run: docker build -f deploy/bot/Dockerfile -t check-bot .
```

---

## Implementation Steps

### Step 1: Fix Django Migrate Commands

```bash
cd C:\install\progect\project-template
# Edit tools/init_project/actions/docker/docker.py
# Apply the fix from Issue #1 (lines 280-281)
```

### Step 2: Test Template Generation

```bash
# Generate a test project
python -m tools.init_project --backend django --bot --project-name test_cicd

cd test_cicd
```

### Step 3: Verify Generated Workflows

**Check `test_cicd/.github/workflows/cd-release.yml`:**

```bash
cat .github/workflows/cd-release.yml | grep -A 2 "migrate"
```

**Expected:**
```yaml
docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python src/backend_django/manage.py migrate --noinput
docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python src/backend_django/manage.py collectstatic --noinput
```

**Check `test_cicd/.github/workflows/ci-main.yml`:**

```bash
cat .github/workflows/ci-main.yml
```

**Verify YAML is valid:**

```bash
# Use a YAML linter
yamllint .github/workflows/ci-main.yml
yamllint .github/workflows/cd-release.yml

# Or use pre-commit hook
pre-commit run check-yaml --files .github/workflows/*.yml
```

### Step 4: Verify Indentation

Look at the generated `ci-main.yml`:

```yaml
jobs:
  test:
    name: Test & Lint
    runs-on: ubuntu-latest

    services:
      # ... database service ...

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Build Django image
        run: docker build -f deploy/django/Dockerfile -t check-backend .

      - name: Build Bot image
        run: docker build -f deploy/bot/Dockerfile -t check-bot .
```

**Check:**
- ✅ All `- name:` steps are aligned
- ✅ No extra indentation
- ✅ YAML is syntactically valid

If indentation is wrong, apply fixes from Issue #2 and #3.

---

## Testing Instructions

### Test 1: Generate Fresh Project

```bash
cd C:\install\progect\project-template
python -m tools.init_project --backend django --bot --project-name test_cicd_fix

cd test_cicd_fix
```

### Test 2: Validate YAML Syntax

```bash
# Install yamllint if not installed
pip install yamllint

# Check all workflows
yamllint .github/workflows/*.yml
```

**Expected:**
- ✅ No syntax errors
- ✅ No warnings about indentation

### Test 3: Verify Paths in cd-release.yml

```bash
grep "python src/backend_django/manage.py" .github/workflows/cd-release.yml
```

**Expected output:**
```
docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python src/backend_django/manage.py migrate --noinput
docker compose -f deploy/docker-compose.prod.yml run --rm -T backend python src/backend_django/manage.py collectstatic --noinput
```

### Test 4: Check ci-main.yml Structure

```bash
cat .github/workflows/ci-main.yml
```

**Manually verify:**
- ✅ Build steps are correctly indented
- ✅ No double-spacing or misalignment
- ✅ Bot and Backend build steps (if both enabled)

### Test 5: Simulate CD Workflow Locally (Advanced)

If you have Docker and want to test the actual commands:

```bash
# Build images
cd deploy
docker-compose -f docker-compose.prod.yml build

# Test migrate command (from generated workflow)
docker compose -f docker-compose.prod.yml run --rm backend python src/backend_django/manage.py migrate --check

# Test collectstatic command
docker compose -f docker-compose.prod.yml run --rm backend python src/backend_django/manage.py collectstatic --noinput --dry-run
```

**Expected:**
- ✅ Commands run without errors
- ✅ No `FileNotFoundError: manage.py`
- ✅ No `No module named 'src'` errors

---

## Common Errors and Solutions

### Error: "FileNotFoundError: manage.py"

**Cause:** Command uses `python manage.py` instead of `python src/backend_django/manage.py`

**Solution:** Apply the fix from Issue #1

### Error: "YAML syntax error: mapping values are not allowed here"

**Cause:** Indentation is wrong in generated workflow

**Solution:**
1. Check the `build_steps +=` logic in `docker.py`
2. Ensure the `dedent()` string matches the expected indentation level
3. The `- name:` should align with other steps

### Error: "No module named 'src.shared'"

**Cause:** PYTHONPATH not set correctly in Dockerfile (Task 01 issue)

**Solution:** Fix Task 01 first, then re-test CI/CD

---

## Rollback Plan

If generated workflows have issues:

```bash
# In template directory
git checkout tools/init_project/actions/docker/docker.py

# Re-generate test project
rm -rf test_cicd_fix
python -m tools.init_project --backend django --bot --project-name test_cicd_fix
```

---

## Checklist

Before marking this task complete:

- [ ] Issue #1 fixed (lines 280-281 in docker.py)
- [ ] Test project generated
- [ ] cd-release.yml verified (correct migrate/collectstatic paths)
- [ ] ci-main.yml verified (valid YAML, correct indentation)
- [ ] yamllint passes on all workflows
- [ ] pre-commit check-yaml passes
- [ ] Local Docker test of migrate/collectstatic commands (if possible)
- [ ] Changes committed to feature branch

---

## Related Issues

- **Task 01:** [PYTHONPATH Fixes](./01-pythonpath-fixes.md) - Dockerfiles must be fixed first
- **Task 02:** [Code Quality Fixes](./02-code-quality-fixes.md) - CI workflows should pass linting
- **Task 03:** [Documentation Updates](./03-documentation-updates.md) - No direct relation

---

**Last Updated:** 2026-02-12
**Status:** ⬜ Ready for Implementation

# Task 03: Documentation Updates

**Priority:** 🟢 Medium
**Status:** ⬜ Not Started
**Estimated Time:** 2-3 hours
**Dependencies:** Task 01 (reference PYTHONPATH fixes in documentation)

---

## Problem Summary

The template lacks comprehensive documentation for:

1. **PYTHONPATH configuration** - Developers don't know how to set it up locally
2. **IDE setup** - No instructions for PyCharm or VSCode
3. **Local development workflow** - Commands are outdated or incomplete
4. **Pre-commit hooks** - Not mentioned in onboarding

**Root Cause:** Template was created with focus on Docker deployment, local development setup was assumed knowledge.

**Impact:** 🟢 **MEDIUM** - Doesn't break code but creates frustrating onboarding experience. New developers hit `ModuleNotFoundError` and don't know why.

---

## Changes Required

### Change #1: Add PYTHONPATH Setup Section to README.md

**File:** `README.md` (project template root)
**Location:** After the "Run (Local Development)" section

**Content to Add:**

```markdown
### 5. Python Path Configuration (Important!)

For correct module imports, add the project root to PYTHONPATH:

#### Linux/macOS:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

Add to your shell profile (~/.bashrc, ~/.zshrc) to make it permanent:
```bash
echo 'export PYTHONPATH="${PYTHONPATH}:$(pwd)"' >> ~/.bashrc
source ~/.bashrc
```

#### Windows (PowerShell):
```powershell
$env:PYTHONPATH = "$env:PYTHONPATH;$PWD"
```

Add to your PowerShell profile to make it permanent:
```powershell
notepad $PROFILE
# Add this line:
# $env:PYTHONPATH = "$env:PYTHONPATH;$PWD"
```

#### Windows (CMD):
```cmd
set PYTHONPATH=%PYTHONPATH%;%CD%
```

#### PyCharm:
1. File → Settings → Project → Project Structure
2. Right-click project root folder → Mark Directory as → Sources Root
3. The IDE will automatically handle PYTHONPATH

#### VSCode:
Create `.vscode/settings.json` (see IDE Configuration section below)

#### Running Tests:
```bash
# From project root - pytest will use pythonpath from pyproject.toml
pytest src/

# Or set PYTHONPATH explicitly:
# Linux/macOS:
PYTHONPATH=. pytest src/

# Windows:
$env:PYTHONPATH="."; pytest src/
```

**Why This Matters:**
Without PYTHONPATH, you'll get `ModuleNotFoundError: No module named 'src'` when:
- Running Django management commands locally
- Running the Telegram bot locally
- Running tests with pytest
- Importing from `src.shared` in any code
```

---

### Change #2: Update Run Commands

**File:** `README.md` (project template root)
**Location:** In the "Run (Local Development)" section

**Current Content (Incorrect):**
```markdown
**Telegram Bot:**
```bash
cd src/telegram_bot
# Ensure DB is running and migrations are applied
alembic upgrade head
python -m core
```
```

**Fixed Content:**
```markdown
**Django Backend:**
```bash
cd src/backend_django
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Access at: http://localhost:8000/admin/

**Telegram Bot:**
```bash
# Run from project root, not from src/telegram_bot!
python -m src.telegram_bot.app_telegram
```

**Worker (ARQ):**
```bash
# Run from project root
python -m src.telegram_bot.services.worker.bot_worker
```

**Important:** Always run bot and worker from the project root directory, not from subdirectories.
```

**Why This Matters:**
- Original commands assumed you were `cd`'d into the module directory
- New commands use Python module syntax from project root
- Matches the Docker CMD patterns
- Works consistently with PYTHONPATH setup

---

### Change #3: Add IDE Configuration Section

**File:** `README.md` (project template root)
**Location:** New section after "Python Path Configuration"

**Content to Add:**

```markdown
## IDE Configuration

### PyCharm

1. **Mark Project Root as Source:**
   - File → Settings → Project: {project_name} → Project Structure
   - Right-click on the project root folder
   - Select "Mark Directory as" → "Sources Root"

2. **Configure Python Interpreter:**
   - File → Settings → Project: {project_name} → Python Interpreter
   - Click gear icon → Add → Existing environment
   - Select `.venv/bin/python` (or `.venv\Scripts\python.exe` on Windows)

3. **Enable Django Support (if using Django):**
   - File → Settings → Languages & Frameworks → Django
   - Check "Enable Django Support"
   - Django project root: `{project_root}/src/backend_django`
   - Settings: `core/settings/dev.py`
   - Manage script: `manage.py`

### VSCode

1. **Create VSCode Settings:**

   Create `.vscode/settings.json` in project root:

   ```json
   {
       "python.analysis.extraPaths": ["${workspaceFolder}"],
       "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
       "terminal.integrated.env.linux": {
           "PYTHONPATH": "${workspaceFolder}:${env:PYTHONPATH}"
       },
       "terminal.integrated.env.osx": {
           "PYTHONPATH": "${workspaceFolder}:${env:PYTHONPATH}"
       },
       "terminal.integrated.env.windows": {
           "PYTHONPATH": "${workspaceFolder};${env:PYTHONPATH}"
       },
       "[python]": {
           "editor.formatOnSave": true,
           "editor.codeActionsOnSave": {
               "source.organizeImports": "explicit"
           }
       },
       "python.analysis.typeCheckingMode": "basic"
   }
   ```

2. **Install Recommended Extensions:**
   - Python (Microsoft)
   - Pylance (Microsoft)
   - Ruff (Astral)
   - Docker (Microsoft) - for docker-compose files

3. **Select Python Interpreter:**
   - Ctrl+Shift+P (Cmd+Shift+P on macOS)
   - Type "Python: Select Interpreter"
   - Choose the `.venv/bin/python` from your project

### VS Code Launch Configuration (Optional)

Create `.vscode/launch.json` for debugging:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Django: runserver",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/src/backend_django/manage.py",
            "args": ["runserver"],
            "django": true,
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        },
        {
            "name": "Telegram Bot",
            "type": "debugpy",
            "request": "launch",
            "module": "src.telegram_bot.app_telegram",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```
```

---

### Change #4: Create .vscode/settings.json Template

**File:** `.vscode/settings.json` (NEW FILE)
**Location:** Project root

**Content:**

```json
{
    "python.analysis.extraPaths": ["${workspaceFolder}"],
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "terminal.integrated.env.linux": {
        "PYTHONPATH": "${workspaceFolder}:${env:PYTHONPATH}"
    },
    "terminal.integrated.env.osx": {
        "PYTHONPATH": "${workspaceFolder}:${env:PYTHONPATH}"
    },
    "terminal.integrated.env.windows": {
        "PYTHONPATH": "${workspaceFolder};${env:PYTHONPATH}"
    },
    "[python]": {
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
        }
    },
    "python.analysis.typeCheckingMode": "basic",
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/.mypy_cache": true,
        "**/.pytest_cache": true,
        "**/.ruff_cache": true
    }
}
```

**Why Include This:**
- VSCode users get correct configuration out-of-the-box
- PYTHONPATH is automatically set in integrated terminal
- Pylance can find imports
- Format-on-save works with Ruff

---

### Change #5: Update .gitignore for .vscode

**File:** `.gitignore`
**Location:** Root of template

**Add these lines:**

```gitignore
# IDE
.idea/
.vscode/*
!.vscode/settings.json
!.vscode/launch.json
.DS_Store
```

**Why:**
- Ignore most VSCode files (user-specific)
- Keep `settings.json` and `launch.json` (project-wide)
- Ignore PyCharm files (`.idea/`)
- Ignore macOS files (`.DS_Store`)

---

### Change #6: Add Pre-commit Setup to README

**File:** `README.md`
**Location:** New section after "Install Dependencies"

**Content to Add:**

```markdown
### 3. Install Pre-commit Hooks (Recommended)

Pre-commit hooks automatically check code quality before each commit:

```bash
# Install pre-commit hooks
pre-commit install

# Test that hooks work
pre-commit run --all-files
```

**What the hooks do:**
- ✅ Remove trailing whitespace
- ✅ Fix end-of-file newlines
- ✅ Check YAML syntax
- ✅ Format Python code (Ruff)
- ✅ Lint Python code (Ruff)
- ✅ Check for large files (>500KB)
- ✅ Check for merge conflicts

**Manual check:**
You can run all checks manually without committing:
```bash
# Linux/macOS:
./tools/dev/check_local.sh

# Windows:
.\tools\dev\check_local.ps1
```

This runs the same checks as pre-commit plus mypy and pytest.
```

---

## Implementation Steps

### 1. Update README.md

```bash
cd C:\install\progect\project-template
# Edit README.md with all changes from Change #1-3 and #6
```

**Sections to add/update:**
- [ ] Add "Python Path Configuration" section
- [ ] Update "Run (Local Development)" commands
- [ ] Add "IDE Configuration" section
- [ ] Add "Pre-commit Hooks" section

### 2. Create .vscode/settings.json

```bash
mkdir .vscode
# Create .vscode/settings.json with content from Change #4
```

### 3. Update .gitignore

```bash
# Edit .gitignore, add IDE section from Change #5
```

### 4. Verify Documentation Accuracy

Test each documented command:

```bash
# PYTHONPATH setup (Linux):
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python -c "from src.shared.core.config import CommonSettings; print('OK')"

# Django command:
cd src/backend_django
python manage.py check

# Bot command (from root):
cd ../..
python -m src.telegram_bot.app_telegram --help

# Pre-commit:
pre-commit run --all-files

# Local check script:
.\tools\dev\check_local.ps1
```

All commands should work as documented.

---

## Testing Instructions

### 1. Fresh Project Onboarding Simulation

Pretend you're a new developer:

```bash
# Clone template
cd C:\install\progect
python -m tools.init_project.cli --backend django --bot --project-name test_docs

cd test_docs
```

**Follow the README step by step:**

1. ✅ Install dependencies: `poetry install`
2. ✅ Install pre-commit: `pre-commit install`
3. ✅ Set up PYTHONPATH (follow README instructions)
4. ✅ Configure IDE (follow README instructions)
5. ✅ Run Django: `cd src/backend_django && python manage.py check`
6. ✅ Run bot: `python -m src.telegram_bot.app_telegram --help`
7. ✅ Run tests: `pytest src/`

**Expected:**
- All commands work as documented
- No `ModuleNotFoundError`
- IDE autocomplete works

### 2. Verify VSCode Configuration

```bash
cd test_docs
code .
```

In VSCode:
1. ✅ Open terminal - PYTHONPATH should be set
2. ✅ Type `from src.shared` - should autocomplete
3. ✅ Open a Python file - no import errors in Problems panel
4. ✅ Save a file - Ruff formatting should apply

### 3. Verify PyCharm Configuration

In PyCharm:
1. ✅ Open project
2. ✅ Follow "Mark Project Root as Source" instructions
3. ✅ Type `from src.shared` - should autocomplete
4. ✅ No import errors in editor

### 4. Verify Pre-commit Hooks

```bash
echo "test  " > test.py  # Trailing spaces
git add test.py
git commit -m "test"
```

**Expected:**
- ✅ Pre-commit runs
- ✅ Trailing whitespace is removed
- ✅ Commit succeeds

---

## Checklist

Before marking this task complete:

- [ ] README.md updated with all sections
- [ ] PYTHONPATH setup instructions added (all platforms)
- [ ] Run commands updated (Django, Bot, Worker)
- [ ] IDE configuration section added
- [ ] Pre-commit hooks section added
- [ ] `.vscode/settings.json` created
- [ ] `.gitignore` updated for IDE files
- [ ] All documented commands tested and work
- [ ] Fresh project test (onboarding simulation) passes
- [ ] VSCode configuration tested
- [ ] PyCharm configuration tested
- [ ] Pre-commit hooks tested
- [ ] Changes committed to feature branch

---

## Related Issues

- **Task 01:** [PYTHONPATH Fixes](./01-pythonpath-fixes.md) - These docs explain how to use the fixes
- **Task 02:** [Code Quality Fixes](./02-code-quality-fixes.md) - Pre-commit hooks section relates to this
- **Task 04:** [CI/CD Fixes](./04-cicd-fixes.md) - No direct relation

---

**Last Updated:** 2026-02-12
**Status:** ⬜ Ready for Implementation

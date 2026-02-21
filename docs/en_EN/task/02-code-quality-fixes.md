# Task 02: Code Quality Fixes

**Priority:** 🟡 High
**Status:** ⬜ Not Started
**Estimated Time:** 3-4 hours
**Dependencies:** Task 01 (PYTHONPATH fixes should be done first)

---

## Problem Summary

The template contains multiple code quality issues that should be fixed before propagating to new projects:

1. **Linting errors** - Ruff finds multiple violations (TC001, B027, UP038, F841)
2. **Formatting issues** - Trailing whitespace, missing EOF newlines
3. **Pre-commit integration** - Local check script doesn't use pre-commit hooks
4. **Inconsistent checks** - Local checks differ from pre-commit checks

**Root Cause:** Template was created before strict linting was enforced, and `check_local.ps1` was written before pre-commit hooks were added.

**Impact:** 🟡 **HIGH** - Doesn't break functionality but creates technical debt in every new project.

---

## Step 1: Update check_local.ps1 Script

### Current Approach (Suboptimal)

**File:** `tools/dev/check_local.ps1`

The current script directly calls `ruff check`, `mypy`, and `pytest`. This creates inconsistency:
- Local checks might use different tool versions than pre-commit
- Local checks might have different configurations
- Developers can pass checks locally but fail pre-commit

### New Approach (from lily_website)

**Source:** `lily_website/tools/dev/check_local.ps1`

The improved script uses `pre-commit run` for most checks, ensuring:
- ✅ Same tool versions as pre-commit
- ✅ Same configurations as pre-commit
- ✅ Consistency between local and commit-time checks

### Action Required

**Copy the file:**
```bash
cp "C:\install\progect\lily_website\tools\dev\check_local.ps1" "C:\install\progect\project-template\tools\dev\check_local.ps1"
```

**Changes in the new script:**

1. **Pre-commit check added:**
   ```powershell
   # Check for pre-commit installation
   Write-Host "`n⚙️ Checking for pre-commit installation..." -ForegroundColor Yellow
   try {
       pre-commit --version | Out-Null
       Write-Host "✅ pre-commit is installed." -ForegroundColor Green
   } catch {
       Write-Host "❌ pre-commit is not installed. Please install it: pip install pre-commit" -ForegroundColor Red
       exit 1
   }
   ```

2. **Helper function for pre-commit hooks:**
   ```powershell
   function Run-PreCommitHook {
       param (
           [string]$HookName,
           [string]$Message
       )
       Write-Host "`n🔍 $Message..." -ForegroundColor Yellow
       try {
           pre-commit run $HookName --all-files
           if ($LASTEXITCODE -ne 0) { throw "$HookName failed" }
           Write-Host "✅ $HookName passed!" -ForegroundColor Green
       } catch {
           Write-Host "❌ $HookName failed!" -ForegroundColor Red
           exit 1
       }
   }
   ```

3. **Pre-commit hooks integrated:**
   ```powershell
   Run-PreCommitHook -HookName "trailing-whitespace" -Message "Checking for trailing whitespace"
   Run-PreCommitHook -HookName "end-of-file-fixer" -Message "Fixing end of files"
   Run-PreCommitHook -HookName "check-yaml" -Message "Checking YAML syntax"
   Run-PreCommitHook -HookName "ruff-format" -Message "Formatting code (Ruff Format)"
   Run-PreCommitHook -HookName "ruff" -Message "Linting code (Ruff)"
   ```

4. **Mypy cache clearing:**
   ```powershell
   # Очищаем кэш для свежей проверки
   if (Test-Path ".mypy_cache") {
       Write-Host "   Clearing mypy cache..." -ForegroundColor Gray
       Remove-Item -Recurse -Force .mypy_cache
   }
   ```

5. **Pytest with SECRET_KEY:**
   ```powershell
   # Устанавливаем фейковый ключ, если его нет в .env
   $env:SECRET_KEY = "local_test_key"
   ```

---

## Step 2: Fix Ruff Linting Errors

After updating the script, run it to find all linting errors:

```powershell
cd C:\install\progect\project-template
.\tools\dev\check_local.ps1
```

The script will identify the following categories of errors:

### Category A: TC001 - Type Checking Imports

**Error:** `Move import ... into a type-checking block`

**Why:** Runtime imports used only for type hints waste memory. Python's `TYPE_CHECKING` constant is `False` at runtime.

**Files Affected:**
1. `tools/init_project/actions/poetry/poetry.py`
2. `tools/init_project/actions/scaffolder/scaffolder.py`
3. `tools/init_project/installers/fastapi_installer.py`
4. `tools/init_project/installers/shared_installer.py`
5. `tools/init_project/runner.py`
6. `tools/init_project/installers/base.py`
7. `tools/init_project/installers/bot_installer.py`

**Pattern to Fix:**

**Before:**
```python
from tools.init_project.config import InstallContext
from tools.init_project.installers.base import BaseInstaller

class MyInstaller(BaseInstaller):
    def install(self, ctx: InstallContext) -> None:
        pass
```

**After:**
```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.init_project.config import InstallContext

from tools.init_project.installers.base import BaseInstaller

class MyInstaller(BaseInstaller):
    def install(self, ctx: InstallContext) -> None:
        pass
```

**Key Points:**
- Add `from __future__ import annotations` at the top (enables forward references)
- Add `from typing import TYPE_CHECKING`
- Move type-only imports into `if TYPE_CHECKING:` block
- Keep base class imports outside (needed at runtime)
- `InstallContext` is only used in type hints, so it goes inside the block

---

### Category B: B027 - Abstract Method Implementation

**Error:** `Empty method in abstract base class; consider using abstract method decorator or adding "pass"`

**File:** `tools/init_project/installers/base.py`
**Lines:** 24, 33

**Why:** Empty methods in abstract classes should explicitly return `None` or be marked `@abstractmethod`.

**Current Code:**
```python
class BaseInstaller(ABC):
    """Базовый интерфейс installer-плагина."""

    name: str = "BaseInstaller"

    def pre_install(self, ctx: InstallContext) -> None:
        """Фаза 1: проверки и подготовка. Override при необходимости."""
        pass

    @abstractmethod
    def install(self, ctx: InstallContext) -> None:
        """Фаза 2: основная установка. Обязательна к реализации."""
        ...

    def post_install(self, ctx: InstallContext) -> None:
        """Фаза 3: валидация и чистка. Override при необходимости."""
        pass
```

**Fixed Code:**
```python
class BaseInstaller(ABC):
    """Базовый интерфейс installer-плагина."""

    name: str = "BaseInstaller"

    def pre_install(self, ctx: InstallContext) -> None:
        """Фаза 1: проверки и подготовка. Override при необходимости."""
        return None

    @abstractmethod
    def install(self, ctx: InstallContext) -> None:
        """Фаза 2: основная установка. Обязательна к реализации."""
        ...

    def post_install(self, ctx: InstallContext) -> None:
        """Фаза 3: валидация и чистка. Override при необходимости."""
        return None
```

**Why:** Explicit `return None` makes it clear these methods are optional stubs, not incomplete implementations.

---

### Category C: F841 - Unused Variable

**Error:** `Local variable 'remaining' is assigned but never used`

**File:** `tools/init_project/actions/cleaner/cleaner.py`
**Line:** ~58

**Current Code:**
```python
# Очистка пустых deploy/ если всё удалено
deploy_path = ctx.project_root / "deploy"
if deploy_path.exists():
    remaining = [
        p for p in deploy_path.iterdir()
        if p.name != "README.md" and not p.name.startswith(".")
    ]
    if not remaining:
        safe_rmtree(deploy_path)
        print("    🗑️  Removed: deploy/ (empty)")
```

**Fixed Code:**
```python
# Очистка пустых deploy/ если всё удалено
deploy_path = ctx.project_root / "deploy"
if deploy_path.exists():
    remaining = [
        p for p in deploy_path.iterdir()
        if p.name != "README.md" and not p.name.startswith(".")
    ]
    if not remaining:
        safe_rmtree(deploy_path)
        print("    🗑️  Removed: deploy/ (empty)")
```

**Wait, this looks the same!** Let me check the actual issue...

**Actually, the variable IS used in `if not remaining:`, so this might be a false positive or the code might be different. When implementing, check the actual line and either:**
1. Remove the variable if truly unused
2. Verify the code is correct and suppress the warning if needed

---

### Category D: UP038 - Modern isinstance Syntax

**Error:** `Use `X | Y` in isinstance call instead of `(X, Y)`

**Files:** (Need to run the script to find them, but based on REPORT.md examples from lily_website)
- May exist in some init_project files

**Pattern to Fix:**

**Before:**
```python
if isinstance(value, (str, int)):
    ...
```

**After:**
```python
if isinstance(value, str | int):
    ...
```

**Why:** Modern Python (3.10+) supports union types directly. More readable and concise.

---

### Category E: Formatting Issues

**Error:**
- `trailing-whitespace`: Lines end with spaces
- `end-of-file-fixer`: Files missing final newline

**Fix:** The `check_local.ps1` script will auto-fix these when you run it with pre-commit hooks:

```powershell
.\tools\dev\check_local.ps1
```

Pre-commit will automatically:
- Remove trailing whitespace
- Add missing final newlines
- Show which files were fixed

---

## Step 3: Update .pre-commit-config.yaml (Optional)

**File:** `.pre-commit-config.yaml`

**Current Setting:**
```yaml
- id: check-added-large-files
  args: ['--maxkb=500']
```

**From lily_website:**
```yaml
- id: check-added-large-files
  args: ['--maxkb=2000']
```

**Decision:** Keep `500` for the template to be strict. Projects can increase if needed. This is NOT a bug.

---

## Implementation Steps

### 1. Backup Current State

```bash
cd C:\install\progect\project-template
git checkout -b fix/code-quality
git add -A
git commit -m "Checkpoint: Before code quality fixes"
```

### 2. Copy Improved Script

```bash
cp "C:\install\progect\lily_website\tools\dev\check_local.ps1" "C:\install\progect\project-template\tools\dev\check_local.ps1"
```

### 3. Run Script to Find Issues

```powershell
.\tools\dev\check_local.ps1
```

Take note of all errors. The script will stop at the first failure.

### 4. Fix Issues One by One

**Order of fixes:**

1. **Formatting (automatic):**
   ```powershell
   pre-commit run trailing-whitespace --all-files
   pre-commit run end-of-file-fixer --all-files
   ```

2. **TC001 errors (manual):**
   - Edit each file
   - Move imports into `if TYPE_CHECKING:` blocks
   - Test: `pre-commit run ruff --all-files`

3. **B027 error (manual):**
   - Edit `base.py`
   - Change `pass` to `return None`
   - Test: `pre-commit run ruff --all-files`

4. **F841 error (manual):**
   - Edit `cleaner.py`
   - Remove or use the variable
   - Test: `pre-commit run ruff --all-files`

5. **UP038 errors (automatic):**
   ```powershell
   ruff check --fix src/ tools/
   ```

### 5. Verify All Checks Pass

```powershell
.\tools\dev\check_local.ps1
```

Should output:
```
🎉 ALL CHECKS PASSED! You are ready to push.
```

### 6. Commit Changes

```bash
git add -A
git commit -m "fix: Apply code quality improvements

- Update check_local.ps1 to use pre-commit hooks
- Fix TC001: Move type-only imports to TYPE_CHECKING blocks
- Fix B027: Use explicit 'return None' in abstract base class
- Fix F841: Remove unused variables
- Fix UP038: Use modern isinstance syntax (X | Y)
- Fix formatting: Remove trailing whitespace, add EOF newlines

Closes: Task 02"
```

---

## Testing Instructions

### 1. Verify Script Works

```powershell
cd C:\install\progect\project-template
.\tools\dev\check_local.ps1
```

**Expected:**
- ✅ All checks pass
- ✅ No errors in output
- ✅ Green success message at the end

### 2. Test Pre-commit Hooks

```bash
git add .
git commit -m "test"
```

**Expected:**
- ✅ Pre-commit runs automatically
- ✅ All hooks pass
- ✅ Commit succeeds

### 3. Test Individual Hooks

```bash
pre-commit run trailing-whitespace --all-files
pre-commit run end-of-file-fixer --all-files
pre-commit run check-yaml --all-files
pre-commit run ruff-format --all-files
pre-commit run ruff --all-files
```

**Expected:**
- ✅ All pass with "Passed" status
- ✅ No files modified

### 4. Verify Imports Work

```bash
cd C:\install\progect\project-template
python -c "from tools.init_project.runner import run; print('OK')"
```

**Expected:**
- ✅ No import errors
- ✅ Prints "OK"

---

## Checklist

Before marking this task complete:

- [ ] `check_local.ps1` copied from lily_website
- [ ] All TC001 errors fixed (7+ files)
- [ ] B027 error fixed (`base.py`)
- [ ] F841 error fixed (`cleaner.py`)
- [ ] UP038 errors fixed (if any)
- [ ] All formatting issues fixed (automatic)
- [ ] `.\tools\dev\check_local.ps1` passes completely
- [ ] Pre-commit hooks work on commit
- [ ] All imports still work (no runtime errors)
- [ ] Changes committed to feature branch

---

## Related Issues

- **Task 01:** [PYTHONPATH Fixes](./01-pythonpath-fixes.md) - Should be done before this
- **Task 03:** [Documentation Updates](./03-documentation-updates.md) - Add pre-commit setup to docs
- **Task 04:** [CI/CD Fixes](./04-cicd-fixes.md) - CI workflows should also pass linting

---

**Last Updated:** 2026-02-12
**Status:** ⬜ Ready for Implementation

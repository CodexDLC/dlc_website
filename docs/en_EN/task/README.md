# Template Improvement Tasks

## Overview

This directory contains detailed task documentation for improving the `project-template` based on issues discovered during the `lily_website` project development.

**Source Documents:**
- `lily_website/REPORT.md` - Code quality and pre-commit hook issues
- `lily_website/TEMPLATE_IMPROVEMENTS.md` - Detailed PYTHONPATH problems with fixes

**Status:** 📝 Documentation Complete | ⏳ Awaiting Implementation

---

## Task Summary

| # | Task | Priority | Status | Files Affected |
|---|------|----------|--------|----------------|
| 01 | [PYTHONPATH Fixes](./01-pythonpath-fixes.md) | 🔴 Critical | ⬜ Not Started | 3 Dockerfiles, 1 Python, 1 Config |
| 02 | [Code Quality Fixes](./02-code-quality-fixes.md) | 🟡 High | ⬜ Not Started | 8+ Python files, 1 Script |
| 03 | [Documentation Updates](./03-documentation-updates.md) | 🟢 Medium | ⬜ Not Started | README.md, VSCode config |
| 04 | [CI/CD Template Fixes](./04-cicd-fixes.md) | 🟡 High | ⬜ Not Started | 1 Python file (docker.py) |

**Legend:**
- 🔴 Critical - Breaks functionality, must fix first
- 🟡 High - Important improvements, fix soon
- 🟢 Medium - Nice to have, can be delayed
- ⬜ Not Started | 🔄 In Progress | ✅ Complete

---

## Quick Start

### For Implementers

1. **Start with Task 01** (PYTHONPATH Fixes) - This is critical and blocks other work
2. **Then Task 02** (Code Quality) - Ensures template code meets standards
3. **Follow with Task 04** (CI/CD) - Fixes automated workflows
4. **Finish with Task 03** (Documentation) - Makes everything discoverable

### Task Dependencies

```
Task 01 (PYTHONPATH)
    ↓
Task 02 (Code Quality) ← Task 04 (CI/CD)
    ↓
Task 03 (Documentation)
```

---

## Detailed Tasks

### Task 01: PYTHONPATH Fixes 🔴

**File:** [01-pythonpath-fixes.md](./01-pythonpath-fixes.md)

**Summary:** Fix critical PYTHONPATH configuration issues in Docker templates and generation logic that cause `ModuleNotFoundError` in all deployed projects.

**Key Issues:**
- Django Dockerfile has wrong PYTHONPATH (`/app/src/backend_django` instead of `/app`)
- Bot and Worker Dockerfiles missing PYTHONPATH entirely
- docker-compose generation missing `shared` volume mount
- Incorrect path separators (Windows backslashes instead of Unix forward slashes)
- CI/CD migrate commands using wrong paths

**Impact:** 🔴 **CRITICAL** - Projects fail to run in Docker without manual fixes

**Files to Fix:** 6 files
- 3 Dockerfile templates
- 1 Python generation script (docker.py)
- 1 Config file (pyproject.toml)
- Generated docker-compose.yml

---

### Task 02: Code Quality Fixes 🟡

**File:** [02-code-quality-fixes.md](./02-code-quality-fixes.md)

**Summary:** Improve code quality by fixing Ruff linting errors, formatting issues, and updating the local check script to use pre-commit hooks.

**Key Issues:**
- TC001: Import type hints should be in `if TYPE_CHECKING:` blocks (7+ files)
- B027: Empty methods in abstract class should return None
- F841: Unused variables
- UP038: Use modern `X | Y` syntax instead of `(X, Y)` in isinstance
- Formatting: trailing whitespace, missing EOF newlines
- check_local.ps1 doesn't use pre-commit hooks

**Impact:** 🟡 **HIGH** - Code quality issues, but doesn't break functionality

**Files to Fix:** 9+ files

---

### Task 03: Documentation Updates 🟢

**File:** [03-documentation-updates.md](./03-documentation-updates.md)

**Summary:** Add comprehensive documentation for PYTHONPATH configuration, IDE setup, and local development workflow.

**Key Issues:**
- No PYTHONPATH setup instructions for developers
- No IDE configuration guide (PyCharm, VSCode)
- Missing .vscode/settings.json template
- Outdated run commands in README

**Impact:** 🟢 **MEDIUM** - Affects developer onboarding experience

**Files to Create/Update:** 3 files
- README.md sections
- .vscode/settings.json (new)
- .gitignore update

---

### Task 04: CI/CD Template Fixes 🟡

**File:** [04-cicd-fixes.md](./04-cicd-fixes.md)

**Summary:** Fix GitHub Actions workflow generation logic to produce valid YAML with correct paths for Django management commands.

**Key Issues:**
- Migrate command uses `python manage.py` instead of `python src/backend_django/manage.py`
- Same for collectstatic command
- Potential YAML indentation issues in generated workflows

**Impact:** 🟡 **HIGH** - Breaks automated deployments

**Files to Fix:** 1 file
- `tools/init_project/actions/docker/docker.py` (lines 280-281, 210-211)

---

## Implementation Guidelines

### Before Starting

1. ✅ Read ALL task files thoroughly
2. ✅ Understand dependencies between tasks
3. ✅ Review the source documents (REPORT.md, TEMPLATE_IMPROVEMENTS.md)
4. ✅ Backup the template or work in a feature branch

### During Implementation

1. 📝 Update task status in this README as you progress
2. 🧪 Test each fix in isolation before moving to the next
3. ✅ Check off items in individual task files
4. 🔗 Update cross-references if you discover new related issues

### After Completion

1. 🚀 Test the full init flow: `python -m tools.init_project --backend django --bot`
2. 🐳 Verify Docker builds and runs without errors
3. ✨ Run `tools/dev/check_local.ps1` - should pass all checks
4. 📦 Create a test project and verify it works end-to-end

---

## Testing Checklist

After implementing all fixes, verify:

- [ ] Run `python -m tools.init_project --backend django --bot --project-name test_project`
- [ ] Generated Dockerfiles have correct PYTHONPATH (`/app`)
- [ ] Generated docker-compose.yml includes shared volume mount
- [ ] Run `cd test_project && cd deploy && docker-compose build` - no errors
- [ ] Run `cd test_project && cd deploy && docker-compose up` - all services start
- [ ] Check container logs - no `ModuleNotFoundError`
- [ ] Run `cd test_project && tools/dev/check_local.ps1` - all checks pass
- [ ] Django admin accessible at http://localhost:8000/admin/
- [ ] Bot container connects without import errors

---

## Additional Resources

### Related Documentation
- [PYTHONPATH Best Practices](../infrastructure/project_structure/README.md)
- [Docker Setup Guide](../infrastructure/README.md)
- [Pre-commit Hooks Configuration](../infrastructure/dependencies/README.md)

### Original Issue Reports
- [`lily_website/REPORT.md`](C:\install\progect\lily_website\REPORT.md) - Full technical report
- [`lily_website/TEMPLATE_IMPROVEMENTS.md`](C:\install\progect\lily_website\TEMPLATE_IMPROVEMENTS.md) - Detailed fixes

### Contact
If you have questions or discover additional issues:
1. Check if the issue is already documented in one of the task files
2. Review the original reports for more context
3. Create a new task file following the same format if needed

---

**Last Updated:** 2026-02-12
**Version:** 1.0
**Status:** 📝 Documentation Complete - Ready for Implementation

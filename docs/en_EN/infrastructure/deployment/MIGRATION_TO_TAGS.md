# 🔄 Migration Guide: From Release Branch to Tags

[⬅️ Back](./README.md) | [🏠 Docs Root](../../README.md)

---

## 📋 Overview

This guide explains how to migrate from the old `release` branch workflow to tag-based deployment.

**Goal:** Remove the `release` branch, enable tag-based deployments via `v*` tags.

---

## ✅ Pre-Migration Checklist

- [ ] No active deployments in progress
- [ ] All pending PRs to `release` branch merged or closed
- [ ] Team notified about workflow change
- [ ] Latest code from `release` synced to `main` and `develop`

---

## 🚀 Migration Steps

### Step 1: Archive or Delete Release Branch

```bash
# Option A: Archive (recommended)
git branch -m release release-archive
git push origin release-archive
git push origin --delete release

# Option B: Delete completely
git branch -D release
git push origin --delete release
```

### Step 2: Remove Old Workflows

```bash
git checkout develop
git rm .github/workflows/cd-release.yml
git rm .github/workflows/check-release-source.yml
git commit -m "chore(ci): remove release branch workflows, migrate to tag-based deployment"
git push origin develop
```

### Step 3: Update GitHub Branch Protection Rules

**Settings → Branches:**
- Delete protection rule for `release` branch
- Keep protection for `main` (requires PR + CI) and `develop` (requires linters)

### Step 4: Test Tag-Based Deployment

```bash
git checkout main
git pull origin main

git tag -a v1.0.0-test -m "Test tag-based deployment"
git push origin v1.0.0-test

# Verify GitHub Actions triggered and passed, then clean up:
git tag -d v1.0.0-test
git push origin :refs/tags/v1.0.0-test
```

### Step 5: First Production Release

```bash
git checkout main
git pull origin main

git tag -a v1.0.0 -m "Release 1.0.0: First tag-based production release"
git push origin v1.0.0
```

---

## 🔍 Verification After Migration

```bash
# Workflows — should have:
ls .github/workflows/
# ✅ ci-develop.yml
# ✅ ci-main.yml
# ✅ cd-release.yml  (tag-based, configured per project)

# Branches — should have:
git branch -a
# ✅ develop
# ✅ main
# ❌ release (deleted)
```

---

## 🛠️ Rollback Plan

```bash
# Restore release branch from archive:
git checkout release-archive
git branch -m release-archive release
git push origin release
```

---

## 📚 Related Documentation

- **[Tag-Based Releases Guide](./releases_via_tags.md)**
- **[CI/CD Documentation](./ci_cd/README.md)**

---

**Status:** Migration Guide (one-time use)

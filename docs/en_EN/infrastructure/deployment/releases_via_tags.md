# 🏷️ Tag-Based Production Releases

[⬅️ Back](./README.md) | [🏠 Docs Root](../../README.md)

---

## 📋 Overview

This document describes the **tag-based release workflow** for deploying to production. Instead of merging to a long-lived `release` branch, we use **git tags** to trigger deployments.

### Branch Strategy

```bash
develop → main (PR) → create tag v1.2.3 → automatic deploy 🚀
```

### Benefits

✅ **No reverse merging** — eliminates back-merging `release` into `main` and `develop`
✅ **Clean history** — tags clearly mark released versions
✅ **Easy rollbacks** — revert to any version: `git checkout v1.2.2`
✅ **Fewer branches** — only `develop` and `main`
✅ **Faster releases** — simplified workflow reduces manual steps

---

## 🚀 How to Release: Step-by-Step

### Step 1: Verify develop branch

```bash
git checkout develop
git pull origin develop
git log --oneline -10
```

### Step 2: Run local checks

```bash
python tools/dev/check.py
```

Must pass:
- ✅ Ruff format & lint
- ✅ Mypy (type checking)
- ✅ Pytest unit tests

### Step 3: Merge develop → main

Open a Pull Request from `develop` to `main` on GitHub.

**GitHub Actions will automatically run:**
- 🧪 Full test suite + Docker build verification

**Only merge after CI passes!**

### Step 4: Create release tag

```bash
git checkout main
git pull origin main

git tag -a v1.2.3 -m "Release 1.2.3: short description"
git push origin v1.2.3
```

**Version Format:** `vMAJOR.MINOR.PATCH`

- **MAJOR** — incompatible API changes
- **MINOR** — new features (backward compatible)
- **PATCH** — bug fixes

### Step 5: Automatic Deployment

Once you push the tag, **GitHub Actions automatically**:

1. 🐳 Builds Docker images for all services
2. 📦 Tags images: `latest`, `v1.2.3`, `<git-sha>`
3. 🚢 Pushes images to GitHub Container Registry (GHCR)
4. 🚀 Deploys to production server (configure in `cd-release.yml`)

### Step 6: Verify Deployment

```bash
# Check containers on server:
docker ps

# Backend logs:
docker logs <project_name>-backend --tail 50

# Bot logs:
docker logs <project_name>-bot --tail 50
```

---

## 🛠️ Advanced Scenarios

### Hotfix (urgent production fix)

```bash
git checkout main
git pull origin main
git checkout -b hotfix/short-description

# fix the bug, then:
git add .
git commit -m "fix: short description"
git push origin hotfix/short-description

# After merging PR to main:
git checkout main
git pull origin main
git tag -a v1.2.4 -m "Hotfix 1.2.4: short description"
git push origin v1.2.4

# Backport to develop:
git checkout develop
git cherry-pick <commit-hash>
git push origin develop
```

### Rollback to Previous Version

```bash
git checkout main
git reset --hard v1.2.2

git tag -a v1.2.4 -m "Rollback to v1.2.2"
git push origin v1.2.4 --force
```

### View Changes Between Versions

```bash
git log v1.2.0..v1.2.3 --oneline
git diff --name-only v1.2.0 v1.2.3
```

---

## 📝 Tag Naming Convention

✅ `v1.0.0` — first major release
✅ `v1.2.3` — regular release
✅ `v1.2.4-hotfix` — hotfix (optional suffix)

❌ `1.2.3` — missing `v` prefix
❌ `v1.2` — missing PATCH number

---

## 🔍 Troubleshooting

### Deployment didn't trigger

```bash
# Verify tag starts with 'v':
git tag -l

# Delete incorrect tag and recreate:
git tag -d wrong-tag
git push origin :refs/tags/wrong-tag
git tag -a v1.2.3 -m "Release 1.2.3"
git push origin v1.2.3
```

### Cannot create tag (already exists)

```bash
git tag -d v1.2.3
git push origin :refs/tags/v1.2.3
git tag -a v1.2.4 -m "Release 1.2.4"
git push origin v1.2.4
```

---

## 🔐 Required GitHub Secrets

Configure in repository Settings → Secrets:

| Secret | Description |
|:---|:---|
| `HOST` | Production server IP |
| `USERNAME` | SSH user on server |
| `SSH_KEY` | Private SSH key |
| `ENV_FILE` | Contents of `.env` for production |
| `DOMAIN_NAME` | Your domain name |

---

## 🎯 Pre-Release Checklist

- [ ] All features tested locally
- [ ] `python tools/dev/check.py` passed
- [ ] PR from `develop` to `main` created and CI passed
- [ ] PR merged to `main`
- [ ] Tag created: `git tag -a v1.2.3 -m "..."`
- [ ] Tag pushed: `git push origin v1.2.3`
- [ ] GitHub Actions workflow completed successfully
- [ ] Production site verified
- [ ] Logs checked for errors

---

**Author:** CodexDLC | **License:** MIT

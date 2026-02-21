# 🌿 Branching Strategy

> `docs/en_EN/infrastructure/devops/` · [README](README.md) → Branching

---

## Branch Structure

```
main (production via tags)
└── develop (active work)
    ├── feature/user-auth
    ├── feature/payments
    └── fix/login-bug
```

**Note:** The `release` branch has been removed. Production releases now use git tags (e.g., `v1.2.3`).

See: [Tag-Based Releases Guide](../deployment/releases_via_tags.md)

---

## Flow

### Daily Development
```
1. Create feature branch from develop:
   git checkout develop
   git checkout -b feature/my-feature

2. Work on feature, commit, push

3. Create PR: feature/my-feature → develop
   - CI Develop runs (lint)
   - Code review
   - Merge
```

### Release Cycle (Tag-Based)
```
1. Create PR: develop → main
   - CI Main runs (full tests + docker build)
   - Code review
   - Merge

2. Create release tag:
   git checkout main
   git pull origin main
   git tag -a v1.2.3 -m "Release 1.2.3: Description"
   git push origin v1.2.3

3. GitHub Actions automatically:
   - Builds Docker images
   - Pushes to GHCR
   - Deploys to production VPS
```

Full guide: [Releases via Tags](../deployment/releases_via_tags.md)

---

## Branch Rules

| Branch | Direct Push | PR Required | CI Required | Deployment |
|:---|:---|:---|:---|:---|
| `develop` | ✅ Yes | Optional | Lint on push | No |
| `main` | ❌ No | ✅ Yes | Tests must pass | Via tags only |

---

## GitHub Branch Protection Setup

### main branch:
- ✅ Require pull request before merging
- ✅ Require status checks to pass (ci-main / tests)
- ✅ Require branches to be up to date

### develop branch:
- ⚠️ Optional: Require PR (recommended for teams)
- ✅ Require status checks to pass (ci-develop / lint)

---

## Migration from Release Branch

The project previously used a `release` branch for production deployments. This has been replaced with tag-based releases for:
- ✅ Simpler workflow (no reverse merging)
- ✅ Clear version history
- ✅ Easy rollbacks

Migration guide: [MIGRATION_TO_TAGS.md](../deployment/MIGRATION_TO_TAGS.md)

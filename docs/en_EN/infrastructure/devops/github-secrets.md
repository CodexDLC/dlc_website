# 🔐 GitHub Secrets Configuration

> `docs/en_EN/infrastructure/devops/` · [README](README.md) → Secrets

---

## Required Secrets

Configure these in: **GitHub → Repository → Settings → Secrets and variables → Actions**

### Deployment Secrets

| Secret | Description | Example |
|:---|:---|:---|
| `HOST` | VPS IP address or hostname | `123.456.789.0` |
| `USERNAME` | SSH user on VPS | `deploy` |
| `SSH_KEY` | Private SSH key (RSA/Ed25519) | Full key content |
| `ENV_FILE` | Full .env file content for production | See below |

### ENV_FILE Example

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/dbname
POSTGRES_DB=dbname
POSTGRES_USER=user
POSTGRES_PASSWORD=strongpassword

# Security
SECRET_KEY=your-secret-key-here

# FastAPI
DEBUG=False
ALLOWED_ORIGINS=["https://yourdomain.dev"]
SITE_URL=https://yourdomain.dev

# Telegram Bot
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
BACKEND_API_URL=http://backend:8000
BACKEND_API_KEY=your-api-key

# Redis
REDIS_URL=redis://redis:6379/0
```

### Auto-provided Secrets

These are provided by GitHub automatically:

| Secret | Description |
|:---|:---|
| `GITHUB_TOKEN` | Auto-generated, used for GHCR login |
| `github.actor` | Username of the person who triggered the workflow |

---

## Setup Steps

1. **Generate SSH key** for deployment:
   ```bash
   ssh-keygen -t ed25519 -C "github-deploy" -f deploy_key
   ```

2. **Add public key** to VPS `~/.ssh/authorized_keys`

3. **Add private key** as `SSH_KEY` secret in GitHub

4. **Create .env** content and add as `ENV_FILE` secret

5. **Create deploy directory** on VPS:
   ```bash
   sudo mkdir -p /opt/your-project
   sudo chown deploy:deploy /opt/your-project
   ```

---

## Security Notes

- Never commit `.env` files to the repository
- Rotate secrets periodically
- Use separate deploy user with limited permissions
- SSH key should be passwordless (for CI automation)

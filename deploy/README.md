# 🐳 Deploy

This directory is populated by the installer (`python -m tools.init_project`).

Based on your module selection, the following will be generated:

```
deploy/
├── fastapi/Dockerfile        # If FastAPI selected
├── bot/Dockerfile            # If Bot selected
├── worker/Dockerfile         # If Bot selected (ARQ worker)
├── nginx/                    # If any backend
│   ├── Dockerfile
│   ├── nginx-main.conf
│   ├── site.conf             # Production (SSL)
│   └── site-local.conf       # Development
├── docker-compose.yml        # Development
└── docker-compose.prod.yml   # Production (GHCR images)
```

Templates are stored in: `tools/init_project/actions/docker/resources/`

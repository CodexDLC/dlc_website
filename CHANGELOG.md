# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-07

### Added

- Base project structure: src/, deploy/, docs/, scripts/, tools/.
- CI/CD workflows: ci-develop, ci-main, cd-release, check-release-source.
- Docker configs: multi-stage Dockerfile, docker-compose (local + prod), Nginx.
- Documentation: Twin Realms structure (en_EN + ru_RU), documentation standards.
- MIT License, README (EN + RU), .gitignore, .env.example.

### Added (FastAPI)

- Clean Architecture backend: core, database, features (users, media), dependencies.
- JWT authentication with refresh tokens.
- Media CAS storage with de-duplication.
- Alembic migrations setup.
- Pydantic v2 schemas, Loguru logging.

### Added (Telegram Bot)

- Bot architecture: handlers, orchestrators, services, middlewares.
- Director pattern for feature navigation.
- Animation service (progress bars, polling loops).
- ViewSender for message lifecycle management.
- DI container with API client integration.
- Security middleware (session validation, rate limiting, user validation).

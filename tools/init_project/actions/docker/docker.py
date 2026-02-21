"""
Docker Action — генерация Docker файлов на основе выбора пользователя.

Читает .tpl шаблоны из resources/, подставляет переменные,
записывает готовые файлы в deploy/ и корень проекта.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from tools.init_project.config import InstallContext, safe_rmtree

# Путь к ресурсам относительно этого файла
RESOURCES = Path(__file__).parent / "resources"

PYTHON_VERSION = "3.13"


class DockerAction:
    """Генерация Docker-инфраструктуры из шаблонов."""

    def execute(self, ctx: InstallContext) -> None:
        deploy = ctx.project_root / "deploy"

        # Очищаем старый deploy (из шаблона-донора)
        if deploy.exists():
            safe_rmtree(deploy)
        deploy.mkdir(parents=True)

        # Переменные для подстановки
        variables = {
            "{{PROJECT_NAME}}": ctx.project_name,
            "{{PYTHON_VERSION}}": PYTHON_VERSION,
            "{{DOMAIN}}": f"{ctx.project_name}.dev",  # default, user поменяет
        }

        # ── Dockerfiles ──
        if ctx.backend == "fastapi":
            self._render_template(
                RESOURCES / "fastapi" / "Dockerfile.tpl",
                deploy / "fastapi" / "Dockerfile",
                variables,
            )
            print("    📄 Generated: deploy/fastapi/Dockerfile")

        if ctx.backend == "django":
            self._render_template(
                RESOURCES / "django" / "Dockerfile.tpl",
                deploy / "django" / "Dockerfile",
                variables,
            )
            print("    📄 Generated: deploy/django/Dockerfile")

        if ctx.include_bot:
            self._render_template(
                RESOURCES / "bot" / "Dockerfile.tpl",
                deploy / "bot" / "Dockerfile",
                variables,
            )
            print("    📄 Generated: deploy/bot/Dockerfile")

            self._render_template(
                RESOURCES / "worker" / "Dockerfile.tpl",
                deploy / "worker" / "Dockerfile",
                variables,
            )
            print("    📄 Generated: deploy/worker/Dockerfile")

        # ── Nginx (только если есть бэкенд) ──
        if ctx.backend:
            nginx_dir = deploy / "nginx"
            nginx_dir.mkdir(parents=True, exist_ok=True)

            self._render_template(
                RESOURCES / "nginx" / "Dockerfile.tpl",
                nginx_dir / "Dockerfile",
                variables,
            )
            self._render_template(
                RESOURCES / "nginx" / "nginx-main.conf.tpl",
                nginx_dir / "nginx-main.conf",
                variables,
            )
            # site.conf.tpl → site.conf.template: домен подставляется envsubst при старте контейнера
            self._render_template(
                RESOURCES / "nginx" / "site.conf.tpl",
                nginx_dir / "site.conf.template",
                variables,
            )
            self._render_template(
                RESOURCES / "nginx" / "site-local.conf.tpl",
                nginx_dir / "site-local.conf",
                variables,
            )
            print("    📄 Generated: deploy/nginx/ (4 files)")

        # ── docker-compose ──
        self._generate_compose_dev(ctx, deploy, variables)
        self._generate_compose_prod(ctx, deploy, variables)

        # ── .dockerignore ──
        self._render_template(
            RESOURCES / "dockerignore.tpl",
            ctx.project_root / ".dockerignore",
            variables,
        )
        print("    📄 Generated: .dockerignore")

        # ── Root .env ──
        self._render_template(
            RESOURCES / "env.tpl",
            ctx.project_root / ".env",
            variables,
        )
        self._render_template(
            RESOURCES / "env.example.tpl",
            ctx.project_root / ".env.example",
            variables,
        )
        print("    📄 Generated: .env + .env.example")

        # ── CI/CD Workflows ──
        self._generate_workflows(ctx, variables)

    # ─────────────────────────────────────────
    # CI/CD generation
    # ─────────────────────────────────────────

    def _generate_workflows(self, ctx: InstallContext, variables: dict[str, str]) -> None:
        """Генерирует GitHub Actions workflows."""
        workflows_dir = ctx.project_root / ".github" / "workflows"

        # Удаляем старые workflows
        if workflows_dir.exists():
            safe_rmtree(workflows_dir)
        workflows_dir.mkdir(parents=True, exist_ok=True)

        # Общие переменные для CI
        extras: list[str] = []
        lint_paths: list[str] = []
        if ctx.backend == "fastapi":
            extras.append("fastapi")
            lint_paths.append("src/backend_fastapi/")
        if ctx.backend == "django":
            extras.append("django")
            lint_paths.append("src/backend_django/")
        if ctx.include_bot:
            extras.append("bot")
            lint_paths.append("src/telegram_bot/")
        lint_paths.append("src/shared/")

        install_extras = "," + ",".join(extras) if extras else ""

        ci_vars = {
            **variables,
            "{{INSTALL_EXTRAS}}": install_extras,
            "{{LINT_PATHS}}": " ".join(lint_paths),
        }

        # ci-develop.yml
        self._render_template(
            RESOURCES / "github" / "ci-develop.yml.tpl",
            workflows_dir / "ci-develop.yml",
            ci_vars,
        )

        # ci-main.yml — нужны динамические блоки
        test_env = '          SECRET_KEY: "test_secret_key_for_ci"\n          ENVIRONMENT: "testing"'
        build_check_steps: list[str] = []

        if ctx.backend == "fastapi":
            test_env += "\n          DATABASE_URL: postgresql+asyncpg://postgres:test_password@localhost:5432/test_db"
            build_check_steps.append(
                dedent("""\
              - name: Build Backend image
                uses: docker/build-push-action@v5
                with:
                  context: .
                  file: deploy/fastapi/Dockerfile
                  push: false
                  tags: check-backend:latest
                  cache-from: type=gha,scope=backend
                  cache-to: type=gha,mode=max,scope=backend""")
            )

        if ctx.backend == "django":
            test_env += "\n          DATABASE_URL: postgres://postgres:test_password@localhost:5432/test_db"
            build_check_steps.append(
                dedent("""\
              - name: Build Backend image
                uses: docker/build-push-action@v5
                with:
                  context: .
                  file: deploy/django/Dockerfile
                  push: false
                  tags: check-backend:latest
                  cache-from: type=gha,scope=backend
                  cache-to: type=gha,mode=max,scope=backend""")
            )

        if ctx.include_bot:
            build_check_steps.append(
                dedent("""\
              - name: Build Bot image
                uses: docker/build-push-action@v5
                with:
                  context: .
                  file: deploy/bot/Dockerfile
                  push: false
                  tags: check-bot:latest
                  cache-from: type=gha,scope=bot
                  cache-to: type=gha,mode=max,scope=bot""")
            )
            build_check_steps.append(
                dedent("""\
              - name: Build Worker image
                uses: docker/build-push-action@v5
                with:
                  context: .
                  file: deploy/worker/Dockerfile
                  push: false
                  tags: check-worker:latest
                  cache-from: type=gha,scope=worker
                  cache-to: type=gha,mode=max,scope=worker""")
            )

        if ctx.backend:
            build_check_steps.append(
                dedent("""\
              - name: Build Nginx image
                uses: docker/build-push-action@v5
                with:
                  context: .
                  file: deploy/nginx/Dockerfile
                  push: false
                  tags: check-nginx:latest
                  cache-from: type=gha,scope=nginx
                  cache-to: type=gha,mode=max,scope=nginx""")
            )

        # Отступ 6 пробелов под steps:
        build_check_block = "\n\n".join(
            "\n".join(f"      {line}" for line in step.splitlines()) for step in build_check_steps
        )

        main_vars = {
            **ci_vars,
            "{{TEST_ENV_VARS}}": test_env,
            "{{BUILD_CHECK_STEPS}}": build_check_block,
        }
        self._render_template(
            RESOURCES / "github" / "ci-main.yml.tpl",
            workflows_dir / "ci-main.yml",
            main_vars,
        )

        # deploy-production-tag.yml — build+push + SSH deploy
        build_push_steps: list[str] = []
        docker_image_envs: list[str] = []
        docker_image_env_names: list[str] = []
        update_var_calls: list[str] = []

        def _add_image(svc_label: str, dockerfile: str, image_suffix: str) -> None:
            env_var = f"DOCKER_IMAGE_{svc_label.upper()}"
            build_push_steps.append(
                dedent(f"""\
              - name: Build and Push {svc_label.capitalize()}
                uses: docker/build-push-action@v5
                with:
                  context: .
                  file: {dockerfile}
                  push: true
                  tags: |
                    ghcr.io/${{{{ env.REPO_LOWER }}}}{image_suffix}:latest
                    ghcr.io/${{{{ env.REPO_LOWER }}}}{image_suffix}:${{{{ env.VERSION }}}}
                    ghcr.io/${{{{ env.REPO_LOWER }}}}{image_suffix}:${{{{ github.sha }}}}
                  cache-from: type=registry,ref=ghcr.io/${{{{ env.REPO_LOWER }}}}{image_suffix}:buildcache
                  cache-to: type=registry,ref=ghcr.io/${{{{ env.REPO_LOWER }}}}{image_suffix}:buildcache,mode=max""")
            )
            docker_image_envs.append(f"          {env_var}: ${{{{ secrets.{env_var} }}}}")
            docker_image_env_names.append(env_var)
            update_var_calls.append(f'            update_var "{env_var}" "${env_var}"')

        if ctx.backend == "fastapi":
            _add_image("backend", "deploy/fastapi/Dockerfile", "-backend")
            _add_image("nginx", "deploy/nginx/Dockerfile", "-nginx")

        if ctx.backend == "django":
            _add_image("backend", "deploy/django/Dockerfile", "-backend")
            _add_image("nginx", "deploy/nginx/Dockerfile", "-nginx")

        if ctx.include_bot:
            _add_image("bot", "deploy/bot/Dockerfile", "-bot")
            _add_image("worker", "deploy/worker/Dockerfile", "-worker")

        build_push_block = "\n\n".join(
            "\n".join(f"      {line}" for line in step.splitlines()) for step in build_push_steps
        )

        if ctx.backend == "django":
            migration_steps = dedent("""\
            echo "🔄 Running migrations..."
            if ! docker compose -f docker-compose.prod.yml run --rm -T backend python manage.py migrate --noinput; then
              echo "❌ Migration failed! Aborting deployment."
              exit 1
            fi

            echo "📦 Collecting static files..."
            docker compose -f docker-compose.prod.yml run --rm -T backend python manage.py collectstatic --noinput""")
        elif ctx.backend == "fastapi":
            migration_steps = dedent("""\
            echo "🔄 Running migrations..."
            if ! docker compose -f docker-compose.prod.yml run --rm -T backend alembic upgrade head; then
              echo "❌ Migration failed! Aborting deployment."
              exit 1
            fi""")
        else:
            migration_steps = ""

        indented_migrations = "\n".join(
            f"            {line}" if line.strip() else "" for line in migration_steps.splitlines()
        )

        deploy_vars = {
            **variables,
            "{{BUILD_PUSH_STEPS}}": build_push_block,
            "{{DOCKER_IMAGE_ENVS}}": "\n".join(docker_image_envs),
            "{{DOCKER_IMAGE_ENV_NAMES}}": ",".join(docker_image_env_names),
            "{{UPDATE_VAR_CALLS}}": "\n".join(update_var_calls),
            "{{MIGRATION_STEPS}}": indented_migrations,
        }
        self._render_template(
            RESOURCES / "github" / "deploy-production-tag.yml.tpl",
            workflows_dir / "deploy-production-tag.yml",
            deploy_vars,
        )

        print("    📄 Generated: .github/workflows/ (3 files)")

    # ─────────────────────────────────────────
    # Compose generation — секционная сборка
    # ─────────────────────────────────────────

    def _generate_compose_dev(self, ctx: InstallContext, deploy: Path, variables: dict[str, str]) -> None:
        """Генерирует docker-compose.yml для dev."""
        services: list[str] = []
        volumes: list[str] = []
        net = ctx.project_name

        if ctx.backend == "fastapi":
            services.append(self._svc_fastapi_dev(ctx.project_name))
            volumes.extend(["uploads:\n    driver: local", "logs:\n    driver: local"])

        if ctx.backend == "django":
            services.append(self._svc_django_dev(ctx.project_name))
            volumes.extend(["staticfiles:\n    driver: local", "logs:\n    driver: local"])

        if ctx.include_bot:
            services.append(self._svc_bot_dev(ctx.project_name))
            services.append(self._svc_worker_dev(ctx.project_name))

        # Redis — если бот (FSM storage + ARQ)
        if ctx.include_bot:
            services.append(self._svc_redis(ctx.project_name))
            volumes.append("redis-data:\n    driver: local")

        # Postgres — если есть бэкенд
        if ctx.backend:
            services.append(self._svc_postgres(ctx.project_name))
            volumes.append("postgres-data:\n    driver: local")

        # Nginx — если бэкенд
        if ctx.backend:
            services.append(self._svc_nginx_dev(ctx.project_name))

        compose = self._assemble_compose(services, volumes, net)
        (deploy / "docker-compose.yml").write_text(compose, encoding="utf-8")
        print("    📄 Generated: deploy/docker-compose.yml")

    def _generate_compose_prod(self, ctx: InstallContext, deploy: Path, variables: dict[str, str]) -> None:
        """Генерирует docker-compose.prod.yml."""
        services: list[str] = []
        volumes: list[str] = []
        net = ctx.project_name

        if ctx.backend == "fastapi":
            services.append(self._svc_fastapi_prod(ctx.project_name))
            volumes.extend(["uploads:\n    driver: local", "logs:\n    driver: local"])

        if ctx.backend == "django":
            services.append(self._svc_django_prod(ctx.project_name))
            volumes.extend(["staticfiles:\n    driver: local", "logs:\n    driver: local"])

        if ctx.include_bot:
            services.append(self._svc_bot_prod(ctx.project_name))
            services.append(self._svc_worker_prod(ctx.project_name))

        if ctx.include_bot:
            services.append(self._svc_redis(ctx.project_name))
            volumes.append("redis-data:\n    driver: local")

        if ctx.backend:
            services.append(self._svc_nginx_prod(ctx.project_name))
            volumes.extend(
                [
                    "certs_volume:\n    driver: local",
                    "certbot_challenge_volume:\n    driver: local",
                ]
            )

        compose = self._assemble_compose(services, volumes, net)
        (deploy / "docker-compose.prod.yml").write_text(compose, encoding="utf-8")
        print("    📄 Generated: deploy/docker-compose.prod.yml")

    @staticmethod
    def _assemble_compose(services: list[str], volumes: list[str], network_name: str) -> str:
        """Собирает docker-compose из блоков."""
        compose = "services:\n"
        compose += "\n\n".join(services)
        compose += "\n\nvolumes:\n"
        if volumes:
            compose += "\n".join(f"  {v}" for v in volumes)
        else:
            compose += "  {}"
        compose += f"\n\nnetworks:\n  {network_name}-network:\n    driver: bridge\n"
        return compose

    # ─────────────────────────────────────────
    # Service blocks — dev
    # ─────────────────────────────────────────

    @staticmethod
    def _svc_fastapi_dev(name: str) -> str:
        return dedent(f"""\
          backend:
            build:
              context: ..
              dockerfile: deploy/fastapi/Dockerfile
            container_name: {name}-backend
            env_file: ../.env
            volumes:
              - ../src/backend_fastapi:/app/src/backend_fastapi:ro
              - ../src/shared:/app/src/shared:ro
              - uploads:/app/data/uploads
              - logs:/app/data/logs
            expose:
              - "8000"
            healthcheck:
              test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
              interval: 30s
              timeout: 10s
              retries: 3
              start_period: 40s
            restart: unless-stopped
            depends_on:
              postgres:
                condition: service_healthy
            networks:
              - {name}-network""")

    @staticmethod
    def _svc_django_dev(name: str) -> str:
        return dedent(f"""\
          backend:
            build:
              context: ..
              dockerfile: deploy/django/Dockerfile
            container_name: {name}-backend
            env_file: ../.env
            volumes:
              - ../src/backend_django:/app/src/backend_django
              - ../src/shared:/app/src/shared:ro
              - staticfiles:/app/staticfiles
              - logs:/app/data/logs
            expose:
              - "8000"
            command: python src/backend_django/manage.py runserver 0.0.0.0:8000
            healthcheck:
              test: ["CMD", "curl", "-f", "http://localhost:8000/"]
              interval: 30s
              timeout: 10s
              retries: 3
              start_period: 40s
            restart: unless-stopped
            depends_on:
              postgres:
                condition: service_healthy
            networks:
              - {name}-network""")

    @staticmethod
    def _svc_bot_dev(name: str) -> str:
        return dedent(f"""\
          bot:
            build:
              context: ..
              dockerfile: deploy/bot/Dockerfile
            container_name: {name}-bot
            env_file: ../.env
            volumes:
              - ../src/telegram_bot:/app/src/telegram_bot:ro
              - ../src/shared:/app/src/shared:ro
            restart: unless-stopped
            depends_on:
              - redis
            networks:
              - {name}-network""")

    @staticmethod
    def _svc_worker_dev(name: str) -> str:
        return dedent(f"""\
          worker:
            build:
              context: ..
              dockerfile: deploy/worker/Dockerfile
            container_name: {name}-worker
            env_file: ../.env
            volumes:
              - ../src/workers:/app/src/workers:ro
              - ../src/shared:/app/src/shared:ro
            restart: unless-stopped
            depends_on:
              - redis
            networks:
              - {name}-network""")

    @staticmethod
    def _svc_redis(name: str) -> str:
        return dedent(f"""\
          redis:
            image: redis:7-alpine
            container_name: {name}-redis
            command: redis-server --appendonly yes
            volumes:
              - redis-data:/data
            expose:
              - "6379"
            healthcheck:
              test: ["CMD", "redis-cli", "ping"]
              interval: 10s
              timeout: 5s
              retries: 3
            restart: unless-stopped
            networks:
              - {name}-network""")

    @staticmethod
    def _svc_postgres(name: str) -> str:
        return dedent(f"""\
          postgres:
            image: postgres:16-alpine
            container_name: {name}-postgres
            environment:
              POSTGRES_DB: ${{POSTGRES_DB:-{name}}}
              POSTGRES_USER: ${{POSTGRES_USER:-postgres}}
              POSTGRES_PASSWORD: ${{POSTGRES_PASSWORD:-postgres}}
            volumes:
              - postgres-data:/var/lib/postgresql/data
            expose:
              - "5432"
            healthcheck:
              test: ["CMD-SHELL", "pg_isready -U postgres"]
              interval: 10s
              timeout: 5s
              retries: 5
            restart: unless-stopped
            networks:
              - {name}-network""")

    @staticmethod
    def _svc_nginx_dev(name: str) -> str:
        return dedent(f"""\
          nginx:
            build:
              context: ..
              dockerfile: deploy/nginx/Dockerfile.local
            container_name: {name}-nginx
            ports:
              - "8080:80"
            volumes:
              - ../src/backend_django/media:/app/media:ro
              - staticfiles:/app/staticfiles:ro
            depends_on:
              backend:
                condition: service_healthy
            restart: unless-stopped
            networks:
              - {name}-network""")

    # ─────────────────────────────────────────
    # Service blocks — prod
    # ─────────────────────────────────────────

    @staticmethod
    def _svc_fastapi_prod(name: str) -> str:
        return dedent(f"""\
          backend:
            image: ${{DOCKER_IMAGE_BACKEND}}
            container_name: {name}-backend
            env_file: .env
            volumes:
              - uploads:/app/data/uploads
              - logs:/app/data/logs
            expose:
              - "8000"
            restart: always
            networks:
              - {name}-network""")

    @staticmethod
    def _svc_django_prod(name: str) -> str:
        return dedent(f"""\
          backend:
            image: ${{DOCKER_IMAGE_BACKEND}}
            container_name: {name}-backend
            env_file: .env
            volumes:
              - staticfiles:/app/staticfiles
              - logs:/app/data/logs
            expose:
              - "8000"
            restart: always
            networks:
              - {name}-network""")

    @staticmethod
    def _svc_bot_prod(name: str) -> str:
        return dedent(f"""\
          bot:
            image: ${{DOCKER_IMAGE_BOT}}
            container_name: {name}-bot
            env_file: .env
            restart: always
            depends_on:
              - redis
            networks:
              - {name}-network""")

    @staticmethod
    def _svc_worker_prod(name: str) -> str:
        return dedent(f"""\
          worker:
            image: ${{DOCKER_IMAGE_WORKER}}
            container_name: {name}-worker
            env_file: .env
            restart: always
            depends_on:
              - redis
            networks:
              - {name}-network""")

    @staticmethod
    def _svc_nginx_prod(name: str) -> str:
        return dedent(f"""\
          nginx:
            image: ${{DOCKER_IMAGE_NGINX}}
            container_name: {name}-nginx
            ports:
              - "80:80"
              - "443:443"
            environment:
              - DOMAIN_NAME=${{DOMAIN_NAME}}
            volumes:
              - ./nginx/nginx-main.conf:/etc/nginx/nginx.conf:ro
              - uploads:/app/media:ro
              - certs_volume:/etc/letsencrypt:ro
              - certbot_challenge_volume:/var/www/certbot:ro
            depends_on:
              - backend
            restart: always
            networks:
              - {name}-network
            logging:
              driver: "json-file"
              options:
                max-size: "10m"
                max-file: "3"

          certbot:
            image: certbot/certbot:v2.11.0
            container_name: {name}-certbot
            volumes:
              - certs_volume:/etc/letsencrypt
              - certbot_challenge_volume:/var/www/certbot
            entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait ${{{{!}}}}; done;'"
            networks:
              - {name}-network""")

    # ─────────────────────────────────────────
    # Template rendering
    # ─────────────────────────────────────────

    @staticmethod
    def _render_template(template_path: Path, output_path: Path, variables: dict[str, str]) -> None:
        """Читает .tpl, подставляет переменные, записывает результат."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = template_path.read_text(encoding="utf-8")
        for marker, value in variables.items():
            content = content.replace(marker, value)
        output_path.write_text(content, encoding="utf-8")

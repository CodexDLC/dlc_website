# Installer (init_project)

> [Tools](README.md) / Installer

The modular project installer that transforms the template into a working project.

## Run

```bash
python -m tools.init_project
```

Interactive CLI prompts for: project name, backend (FastAPI/Django/none), Telegram Bot (yes/no), git init (yes/no).

## Architecture

```
InstallContext (dataclass)
    ├── project_root: Path
    ├── project_name: str
    ├── backend: "fastapi" | "django" | None
    ├── include_bot: bool
    └── init_git: bool

Pipeline:
    PoetryAction        → install deps, remove unused extras
    ScaffolderAction     → generate CI/CD from .tpl templates
    DockerAction         → Dockerfiles, docker-compose, .env
    BackendInstaller     → DjangoInstaller or FastApiInstaller
    BotInstaller         → configure telegram_bot module
    CleanerAction        → remove unused src/, deploy/, docs/
    RenamerAction        → replace "project-template" marker
    FinalizerAction      → git commits, generate project README
```

## Config (`config.py`)

Central registry of modules and their paths:

```python
MODULES = {
    "fastapi": ModuleConfig(
        name="FastAPI Backend",
        src_dirs=["src/backend_fastapi"],
        deploy_dirs=["deploy/Fast_api"],
        doc_dirs=["docs/en_EN/architecture/backend_fastapi", ...],
    ),
    "django": ModuleConfig(...),
    "telegram_bot": ModuleConfig(...),
}
```

Used by: CleanerAction, add_module, remove_module.

## Actions

Each action is a class with `execute(ctx: InstallContext)` method, stored in its own folder with `resources/` for templates.

| Action | Purpose | Resources |
|:-------|:--------|:----------|
| PoetryAction | Install dependencies, remove unused groups | — |
| ScaffolderAction | Generate `.github/workflows/` from `.tpl` | `scaffolder/resources/` |
| DockerAction | Dockerfiles, compose, `.env` for each backend | `docker/resources/{django,fastapi,bot,nginx}/` |
| CleanerAction | Delete unused module directories | — |
| RenamerAction | Replace `project-template` → project name | — |
| FinalizerAction | Two git commits + project README | — |

## Two-Commit Flow

1. **Install** — snapshot of all template files (hash saved to `.template_install_hash`)
2. **Activate** — clean project state after cleanup

The Install commit enables `add_module` to restore removed modules later.

## Backend Installers

### DjangoInstaller

Creates Django structure from `.tpl` templates:
- `core/` — settings (base/dev/prod), urls, wsgi, asgi
- `api/` — Django Ninja with versioned routers
- `features/main/` — views, selectors, admin, translation
- `features/system/` — mixins, base models
- `static/`, `templates/`, `locale/`
- `manage.py`, `.env`, `.env.example`

### FastApiInstaller

FastAPI backend is pre-built in `src/backend_fastapi/` — installer only verifies structure.

## Extending

To add a new Action:

1. Create `tools/init_project/actions/my_action/my_action.py`
2. Implement `execute(ctx: InstallContext)` method
3. Add to pipeline in `__main__.py`
4. Put templates in `my_action/resources/` if needed

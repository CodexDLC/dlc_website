# Tools

> [Infrastructure](../README.md) / Tools

Development utilities that ship with the template. The `tools/` directory is **not deleted** after installation — it stays in the project for ongoing use.

## Overview

| Tool | Path | Description | Run |
|:-----|:-----|:------------|:----|
| **Installer** | `tools/init_project/` | Modular project installer (Actions + Installers) | `python -m tools.init_project` |
| **Add Module** | `tools/init_project/add_module.py` | Restore a removed module from git history | `python -m tools.init_project.add_module bot` |
| **Remove Module** | `tools/init_project/remove_module.py` | Delete a module (src + deploy + docs) | `python -m tools.init_project.remove_module bot` |
| **Image Converter** | `tools/media/convert_to_webp.py` | PNG/JPG → WebP with 5 modes | `python tools/media/convert_to_webp.py` |
| **QR Generator** | `tools/media/qr_generator.py` | GUI for styled QR codes + style class export | `python tools/media/qr_generator.py` |
| **Migration Agent** | `tools/migration_agent.py` | Migrate existing project to template structure | `python tools/migration_agent.py /path` |

## Detailed Docs

- [Installer (init_project)](init_project.md) — architecture, actions, config, extensibility
- [Media Tools](media.md) — image converter, QR generator, style export
- [Module Management](add_remove_module.md) — add/remove modules via git
- [Migration Agent](migration_agent.md) — migrate existing projects

## Directory Structure

```
tools/
├── init_project/
│   ├── __main__.py              # Entry point
│   ├── config.py                # MODULES registry, InstallContext
│   ├── add_module.py            # Restore module from Install commit
│   ├── remove_module.py         # Delete module directories
│   ├── actions/                 # Pipeline actions
│   │   ├── poetry/              # Dependency management
│   │   ├── docker/              # Dockerfile + compose generation
│   │   ├── scaffolder/          # CI/CD templates
│   │   ├── cleaner/             # Remove unused modules
│   │   ├── renamer/             # Replace project-template marker
│   │   └── finalizer/           # Git commits + README generation
│   └── installers/              # Per-framework installers
│       ├── base.py              # BaseInstaller ABC
│       ├── django_installer.py  # Django structure builder
│       └── django/resources/    # Django .tpl templates
├── media/
│   ├── convert_to_webp.py       # Image converter (5 modes)
│   ├── qr_generator.py          # QR code GUI
│   └── qr_style.py              # Generated: project QR style singleton
├── dev/                         # Developer utilities
└── migration_agent.py           # Project migration tool
```

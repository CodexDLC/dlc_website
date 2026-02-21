# Module Management

> [Tools](README.md) / Module Management

Add or remove modules (backends, bot) after initial installation.

## Add Module (`add_module.py`)

Restores a previously removed module from the Install commit in git history.

### Run

```bash
python -m tools.init_project.add_module bot        # alias for telegram_bot
python -m tools.init_project.add_module fastapi
python -m tools.init_project.add_module django

# Show available modules:
python -m tools.init_project.add_module
```

### How It Works

1. Reads the Install commit hash from `.template_install_hash` (or searches git log)
2. Gets all paths for the module from `MODULES` in `config.py` (src + deploy + docs)
3. Runs `git checkout <install-hash> -- <path>` for each path
4. Skips paths that already exist

### What Gets Restored

Each module has three path categories:

| Module | src | deploy | docs |
|:-------|:----|:-------|:-----|
| `fastapi` | `src/backend_fastapi` | `deploy/Fast_api` | `docs/.../backend_fastapi` |
| `django` | `src/backend_django` | `deploy/Django` | `docs/.../backend_django` |
| `telegram_bot` | `src/telegram_bot` | — | `docs/.../telegram_bot` |

### Aliases

- `bot` → `telegram_bot`

### After Restoring

You'll need to manually:
- Update `pyproject.toml` dependencies (add the module's extras)
- Update Docker configuration if needed
- Run `poetry install`

---

## Remove Module (`remove_module.py`)

Deletes all directories belonging to a module and creates a git commit.

### Run

```bash
python -m tools.init_project.remove_module bot
python -m tools.init_project.remove_module fastapi
python -m tools.init_project.remove_module django

# Skip auto-commit:
python -m tools.init_project.remove_module bot --no-commit

# Show available modules:
python -m tools.init_project.remove_module
```

### How It Works

1. Prompts for confirmation (y/N)
2. Gets all paths from `MODULES` in `config.py`
3. Deletes each directory using `safe_rmtree` (Windows-compatible)
4. Creates a git commit (unless `--no-commit`)
5. Prints restore command for reference

### Reverting

After removal, you can always restore with:

```bash
python -m tools.init_project.add_module <module>
```

---

## Config: MODULES Registry

Both tools use `MODULES` from `tools/init_project/config.py` as the single source of truth for module paths. Adding new modules or changing paths only requires editing `config.py`.

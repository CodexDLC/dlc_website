# Project Structure Documentation

This folder explains the organization of the codebase and root directories:

- Purpose of each root directory
- Key configuration files
- Module organization within `src/`
- Where to find specific logic

## Root Directory Map

| Folder | Purpose |
|-------|-----------|
| `deploy/` | Docker-compose, Nginx configs, CI/CD pipelines |
| `src/` | Source code of all modules (monorepo) |
| `scripts/` | DevOps scripts: migrations, linters, generators |
| `docs/` | All project documentation |
| `tools/` | Custom developer tools |

## Key Files

- `pyproject.toml` - Poetry dependencies
- `.gitignore` - What NOT to commit
- `LICENSE` - MIT License

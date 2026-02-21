# Migration Agent

> [Tools](README.md) / Migration Agent

Migrates an existing project into the template structure.

## Run

```bash
python tools/migration_agent.py /path/to/existing-project
```

## What It Does

1. **Analyzes** the existing project structure (detect framework, find source files)
2. **Creates** standard template directories (src/, tools/, deploy/, docs/)
3. **Transfers** detected modules into the template structure
4. **Generates** a TODO report listing manual steps needed to complete migration

## When to Use

When you have an existing Django/FastAPI/Bot project and want to adopt the template's:
- Modular monorepo structure
- Docker + CI/CD pipeline
- PostgreSQL schema isolation
- Documentation structure

## Output

The agent creates a report file with:
- What was detected and moved automatically
- What needs manual intervention (config adjustments, dependency merging, etc.)

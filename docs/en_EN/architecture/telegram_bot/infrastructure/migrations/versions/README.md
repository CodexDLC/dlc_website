# 📂 Versions

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../../../README.md)

This directory contains individual Alembic migration script files. Each file represents a specific change to the database schema, generated either automatically by Alembic or manually written.

## Purpose

Each file in this directory is a Python script that defines `upgrade()` and `downgrade()` functions.
*   The `upgrade()` function describes how to apply the schema change.
*   The `downgrade()` function describes how to revert that change.

These files are executed in a specific order by Alembic to manage the evolution of the database schema.

## Naming Convention

Migration files are typically named with a timestamp prefix (e.g., `xxxxxxxxxxxx_migration_name.py`), which Alembic uses to determine the order of execution.

## Contents

This directory will contain files like:
*   `xxxxxxxxxxxx_initial_schema.py`
*   `yyyyyyyyyyyy_add_new_table.py`
*   `zzzzzzzzzzzz_alter_column.py`

*(Note: The actual migration files are generated dynamically and will appear here as schema changes are made.)*

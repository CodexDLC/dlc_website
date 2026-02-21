name: CI Develop (Fast Quality Check)

on:
  push:
    branches: [ develop ]
  pull_request:
    branches: [ develop ]

jobs:
  lint:
    name: Linting & Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "{{PYTHON_VERSION}}"

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: latest

      - name: Configure Poetry
        run: |
          poetry config virtualenvs.create true
          poetry config virtualenvs.in-project true

      - name: Load cached venv
        id: cached-poetry-dependencies
        uses: actions/cache@v4
        with:
          path: .venv
          key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}

      - name: Install dependencies
        if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
        run: poetry install --no-interaction --no-root --all-extras

      - name: Run Ruff (lint)
        run: poetry run ruff check src/

      - name: Run Ruff (format check)
        run: poetry run ruff format src/ --check

      - name: Run Mypy
        run: poetry run mypy src/

name: CI Main (Quality & Testing)

on:
  pull_request:
    branches: [ main ]

jobs:
  quality-and-tests:
    name: Linting, Types & Tests
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

      - name: Run Pytest
        env:
          SECRET_KEY: "test_secret_key_for_ci"
          ENVIRONMENT: "testing"
        run: poetry run pytest

  build-check:
    name: Docker Build Verification
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

{{BUILD_CHECK_STEPS}}
